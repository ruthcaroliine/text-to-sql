# Text-to-SQL

A natural language interface for querying a PostgreSQL database using AI.

## How it works
1. Type a question in plain English
2. The app generates a SQL query using an LLM
3. The query runs on a PostgreSQL database
4. Results are displayed in a table

## Tech Stack
- **Frontend:** Plain HTML/JS
- **Backend:** Python + FastAPI
- **Database:** PostgreSQL
- **AI:** Groq (LLaMA 3.3)

## Setup

1. Clone the repo
2. Create `backend/.env` with your keys:
```
GROQ_API_KEY=your_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```
3. Install dependencies:
```
pip install -r backend/requirements.txt
```
4. Run the server:
```
cd backend
python -m uvicorn main:app --reload
```
5. Open `index.html` in your browser