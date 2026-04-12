import os
import asyncpg
from groq import Groq
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
DB_URL = os.getenv("DATABASE_URL")
APP_DB_URL = os.getenv("APP_DATABASE_URL")

async def get_schema() -> str:
    """Fetch the live schema directly from Postgres."""
    conn = await asyncpg.connect(DB_URL)
    rows = await conn.fetch("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)
    await conn.close()

    schema = {}
    for row in rows:
        t = row["table_name"]
        if t not in schema:
            schema[t] = []
        schema[t].append(f"  {row['column_name']} ({row['data_type']})")

    return "\n".join(
        f"Table: {t}\n" + "\n".join(cols)
        for t, cols in schema.items()
    )

def generate_sql(question: str, schema: str) -> str:
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are an expert SQL query generator for PostgreSQL.
Given a database schema and a plain English question, return ONLY the SQL query.
- No explanations, no markdown, no backticks
- Use exact table and column names from the schema
- Always use SELECT (never INSERT, UPDATE, DELETE, DROP)
- Limit results to 500 rows max using LIMIT
- Use table aliases for readability"""
            },
            {
                "role": "user",
                "content": f"Schema:\n{schema}\n\nQuestion: {question}"
            }
        ]
    )
    return response.choices[0].message.content.strip()




async def run_query(sql: str) -> dict:
    """Execute the SQL and return columns + rows."""
    conn = await asyncpg.connect(DB_URL)
    try:
        rows = await conn.fetch(sql)
        if not rows:
            return {"columns": [], "rows": []}
        columns = list(rows[0].keys())
        data = [list(row.values()) for row in rows]
        return {"columns": columns, "rows": data}
    finally:
        await conn.close()

async def save_history(question: str, sql: str, row_count: int, was_fixed: bool):
    """Save a successful query to history."""
    conn = await asyncpg.connect(APP_DB_URL)
    try:
        await conn.execute(
            "INSERT INTO query_history (question, sql_query, row_count, was_fixed) VALUES ($1, $2, $3, $4)",
            question, sql, row_count, was_fixed
        )
    finally:
        await conn.close()


class QueryRequest(BaseModel):
    question: str


def fix_sql(bad_sql: str, error: str, question: str, schema: str) -> str:
    """Ask the LLM to fix a broken SQL query."""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are an expert SQL debugger for PostgreSQL.
You will be given a SQL query that failed, the error message, and the original question.
Return ONLY the corrected SQL query.
- No explanations, no markdown, no backticks
- Fix the exact error described
- Keep the query as close to the original as possible"""
            },
            {
                "role": "user",
                "content": f"Schema:\n{schema}\n\nOriginal question: {question}\n\nFailed SQL:\n{bad_sql}\n\nError: {error}"
            }
        ]
    )
    return response.choices[0].message.content.strip()

def summarise_results(question: str, sql: str, columns: list, rows: list) -> str:
    """Ask the LLM to summarise the query results in plain English."""
    # Only send first 20 rows to avoid token limits
    preview = rows[:20]
    rows_text = "\n".join([", ".join(str(v) for v in row) for row in preview])
    
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are a data analyst assistant. 
Given a question, the SQL query that was run, and the results, write a 2-3 sentence plain English summary of what the data shows.
Be specific — mention actual numbers, names, or patterns from the data.
Do not mention SQL or technical details."""
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nSQL:\n{sql}\n\nColumns: {', '.join(columns)}\n\nResults:\n{rows_text}"
            }
        ]
    )
    return response.choices[0].message.content.strip()


@app.post("/query")
async def query(req: QueryRequest):
    try:
        schema = await get_schema()
        sql = generate_sql(req.question, schema)

        try:
            results = await run_query(sql)
            summary = summarise_results(req.question, sql, results["columns"], results["rows"]) if results["rows"] else "No results found for this query."
            await save_history(req.question, sql, len(results["rows"]), False)
            return {"sql": sql, "results": results, "fixed": False, "summary": summary}
        except asyncpg.PostgresError as e:
            # First attempt failed — ask LLM to fix it
            fixed_sql = fix_sql(str(sql), str(e), req.question, schema)
            try:
                results = await run_query(fixed_sql)
                summary = summarise_results(req.question, sql, results["columns"], results["rows"]) if results["rows"] else "No results found for this query."
                await save_history(req.question, fixed_sql, len(results["rows"]), True)
                return {"sql": fixed_sql, "results": results, "fixed": True, "summary": summary}
            except asyncpg.PostgresError as e2:
                raise HTTPException(status_code=400, detail=f"SQL error after retry: {str(e2)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/history")
async def history():
    conn = await asyncpg.connect(APP_DB_URL)
    try:
        rows = await conn.fetch(
            "SELECT id, question, sql_query, row_count, was_fixed, created_at FROM query_history ORDER BY created_at DESC LIMIT 20"
        )
        return {"history": [dict(r) for r in rows]}
    finally:
        await conn.close()

@app.get("/schema")
async def schema():
    return {"schema": await get_schema()}