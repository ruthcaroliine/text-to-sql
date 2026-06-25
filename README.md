# Text-to-SQL Natural Language Interface

> Ask questions in plain English. Get answers from your database instantly.

A full-stack web app that converts natural language questions into SQL queries using **LLaMA 3.3-70b**, executes them against a live **PostgreSQL** database, and returns results with a plain English summary — fully containerised with **Docker**.

---


## Features

- **Natural language to SQL** — powered by Groq's LLaMA 3.3-70b-versatile model
- **Auto-correction loop** — if the generated SQL fails, the error is sent back to the LLM with context and retried silently. Users never see a raw Postgres error.
- **Plain English summary** — after results return, the LLM writes a 2-3 sentence summary of what the data actually shows, with specific numbers and patterns called out
- **Query history** — every successful query is saved to the database and viewable/re-runnable from the UI
- **Auto chart detection** — results are automatically visualised as a bar or line chart where appropriate, using Chart.js
- **Live schema awareness** — the LLM is given the real database schema on every request, so it generates accurate SQL without hallucinating column names
- **Fully Dockerised** — the entire stack (FastAPI + PostgreSQL) spins up with a single command

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | HTML, CSS, JavaScript | Lightweight, no build step, easy to demo |
| Backend | Python, FastAPI | Async-first, fast to build, clean OpenAPI docs |
| Database | PostgreSQL 17 | Production-grade, full SQL support |
| LLM | Groq — LLaMA 3.3-70b | Free tier, extremely fast inference |
| DB driver | asyncpg | Non-blocking async Postgres driver |
| Containers | Docker + Docker Compose | Reproducible environment, one-command setup |

---

## How It Works

```
User question
     │
     ▼
FastAPI /query endpoint
     │
     ├── Fetches live schema from information_schema
     │
     ├── Sends question + schema to LLaMA 3.3 → generates SQL
     │
     ├── Runs SQL on PostgreSQL via asyncpg
     │        │
     │        ├── Success → summarise results → save to history → return
     │        │
     │        └── Failure → send error back to LLM → fix SQL → retry once
     │
     └── Returns: SQL + results + plain English summary
```

The auto-correction loop is the most interesting engineering piece — rather than surfacing a raw Postgres error, the app sends the error message and original SQL back to the LLM with instructions to fix it. This silently handles the majority of failures (wrong column names, bad joins, syntax errors).

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- A free [Groq API key](https://console.groq.com)

### 1. Clone the repo

```bash
git clone https://github.com/ruthcaroliine/text-to-sql.git
cd text-to-sql
```

### 2. Add your environment variables

Create `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://readonly_user:yourpassword@db:5432/texttosql
APP_DATABASE_URL=postgresql://app_user:yourapppassword@db:5432/texttosql
```

### 3. Run

```bash
docker-compose up --build
```

Then open `index.html` in your browser. The backend is available at `http://localhost:8000`.

That's it. Docker handles PostgreSQL, the schema, the users, and all dependencies automatically.

---

## Project Structure

```
text-to-sql/
├── index.html                  # Frontend (single file)
├── docker-compose.yml          # Orchestrates app + db containers
├── init.sql                    # DB schema, users, permissions, seed data
├── README.md
└── backend/
    ├── main.py                 # FastAPI app — all endpoints
    ├── Dockerfile              # Python 3.12 slim image
    ├── requirements.txt
    └── .env                    # Not committed — see setup above
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/schema` | Returns live schema from `information_schema` |
| `POST` | `/query` | Takes a question, returns SQL + results + summary |
| `GET` | `/history` | Returns last 20 queries from `query_history` |

---

## Database Design

Two database users are configured following the principle of least privilege:

| User | Permissions | Used for |
|---|---|---|
| `readonly_user` | `SELECT` on all tables | Running generated SQL queries |
| `app_user` | `SELECT` on all tables + `INSERT`/`SELECT` on `query_history` | Saving query history |

This means even if the LLM generates a destructive query (`DROP`, `DELETE`, `UPDATE`), the `readonly_user` connection will reject it at the database level.

---

## Security Notes

- Generated SQL runs as `readonly_user` — no write access possible
- `.env` is gitignored — API keys and passwords never touch version control
- CORS is open for local development — lock this down before any public deployment

---

## If I Were Scaling This

- **Caching** — cache identical questions with Redis to avoid redundant LLM + DB calls
- **Auth** — API key middleware or OAuth before any public exposure
- **Rate limiting** — per-user limits on `/query` to control LLM API costs
- **CI/CD** — GitHub Actions to build and push the Docker image on every push to `main`
- **Model fallback** — if Groq is down, fall back to another provider automatically

---
