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


class QueryRequest(BaseModel):
    question: str


@app.post("/query")
async def query(req: QueryRequest):
    try:
        schema = await get_schema()
        sql = generate_sql(req.question, schema)
        results = await run_query(sql)
        return {"sql": sql, "results": results}
    except asyncpg.PostgresError as e:
        raise HTTPException(status_code=400, detail=f"SQL error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/schema")
async def schema():
    return {"schema": await get_schema()}