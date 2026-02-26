# ODC Agentic AI - Inventory and Business SQL Chat API

## Overview

This repository implements an AI-powered backend built with `FastAPI` that converts natural-language business and inventory questions into **safe read-only SQL**, executes the query on `PostgreSQL / Supabase`, and returns:

- A grounded natural-language answer
- The exact SQL query that was executed
- Query result metadata (`row_count`, `rows_preview`)
- Latency and token usage

This is not a generic chatbot. It is a **database-grounded analytics assistant**.

## What Problem It Solves

Business users often need answers such as:

- What is the total sales for last month?
- Which vendors have the highest bill totals?
- How many active assets exist per site?
- Which items are purchased most frequently?

Normally, answering these questions requires:

- Understanding the database schema
- Writing correct SQL
- Knowing joins, filters, and aggregations

This project removes that friction by translating natural language into SQL and executing it safely through a controlled backend pipeline.

## Core Features

- `FastAPI` chat API for natural-language analytics
- SQL generation using `Cohere` via `LangChain`
- SQL execution using `SQLAlchemy` on PostgreSQL/Supabase
- Read-only SQL validation before execution
- Multi-statement blocking
- Statement timeout protection for generated queries
- Result-grounded summarization (post-query)
- Transparent response includes executed SQL
- Rich inventory/business schema (customers, vendors, assets, bills, PO/SO, etc.)
- `Faker`-based dummy data generator for demos and testing

## High-Level Architecture

```text
Client (Web/Mobile/Postman)
        |
        v
FastAPI /chat endpoint
        |
        v
chat_service.process_chat()
        |
        +--> LLM Prompt (schema + rules) --> Cohere --> SQL (JSON/text)
        |
        +--> Parser/Repair Layer --> extract sql_query
        |
        +--> SQL Validator (read-only + single statement)
        |
        +--> SQL Runner (SQLAlchemy Session -> PostgreSQL/Supabase)
        |
        +--> rows + row_count
        |
        +--> LLM Result Summarizer (grounded on rows_preview)
        |
        v
ChatResponse (answer + sql + preview + usage + latency)
```

## Critical Flow: Chatbot to DB (Query Send and Result Receive)

This is the most important part of the project and it is implemented as a clear pipeline.

### 1) Receive the user question

`POST /chat/` accepts a payload with:

- `session_id`
- `message`
- `context` (optional metadata such as role)

Validation is handled by `Pydantic` in `app/schemas/chat.py`.

### 2) Build a strict SQL-generation prompt

`app/services/chat_service.py` builds a prompt using:

- A large system prompt from `app/prompts/chat_sql_prompt.py`
- The user question
- `context` serialized as JSON

The prompt includes:

- SQL safety rules
- Performance/indexing guidance
- The authoritative schema
- A strict JSON output contract (`natural_language_answer`, `sql_query`)

This significantly improves SQL quality and reduces model hallucination.

### 3) Call the LLM (Cohere)

The service invokes `ChatCohere` and receives raw output that may be:

- Valid JSON
- Slightly malformed JSON
- SQL inside a fenced code block
- Mixed text and SQL

### 4) Parse and repair the model output

`app/services/chat/parsers.py` contains robust extraction logic:

- Parse the first JSON object if possible
- Repair invalid control characters inside JSON strings
- Fallback regex extraction for `sql_query`
- Final fallback to the first `SELECT/WITH` statement

This is essential because model formatting is not always perfectly compliant.

### 5) Validate SQL before touching the database

`app/services/chat/sql_runner.py` enforces application-level safety:

- Query must start with `SELECT` or `WITH`
- Blocks write/DDL keywords such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`
- Rejects multiple statements in one payload

Result: the backend only executes read-only SQL.

### 6) Send the query to the DB (actual execution)

After validation succeeds:

- SQL is passed to `run_sql_query()`
- A SQLAlchemy session is opened (`SessionLocal`)
- `SET LOCAL statement_timeout` is attempted (best-effort protection)
- `session.execute(text(sql))` runs the query
- Results are read with `result.mappings().all()`

Data is converted into JSON-safe values:

- `Decimal` -> `float`
- `date` / `datetime` -> ISO strings

### 7) Receive the result from the DB

`run_sql_query()` returns a dict containing:

- `sql` (normalized SQL that actually ran)
- `row_count`
- `rows`

Then `chat_service`:

- Reads `row_count`
- Trims `rows_preview` to the first 20 rows

### 8) Build a grounded natural-language answer

The project does a second LLM call to summarize the **actual query results**, not just the model's initial assumptions.

Why this matters:

- Reduces hallucination
- Makes answers verifiable
- Improves trust in the system

### 9) Return the final API response

`ChatResponse` returns:

- `natural_language_answer`
- `sql_query`
- `row_count`
- `rows_preview`
- `latency_ms`
- `token_usage`
- `provider`
- `model`
- `status`

This makes the API suitable for dashboards, admin tools, analytics assistants, and debugging workflows.

## Project Structure

```text
.
├── app/
│   ├── api/routes/chat.py                # Chat endpoint
│   ├── core/config.py                    # Settings / env loading
│   ├── db/
│   │   ├── base.py                       # SQLAlchemy Declarative Base
│   │   ├── engine.py                     # Engine + SessionLocal
│   │   ├── schema.py                     # ORM schema (inventory/business domain)
│   │   ├── init_db.py                    # create_all + triggers/indexes SQL
│   │   ├── trigger.py                    # updated_at triggers + indexes
│   │   └── dummy_data.py                 # Faker-based seeding script
│   ├── prompts/
│   │   ├── chat_sql_prompt.py            # System prompt for SQL generation
│   │   └── tools.py                      # Tool schema (currently not wired in runtime)
│   ├── schemas/chat.py                   # Request/Response models
│   ├── services/
│   │   ├── chat_service.py               # Orchestration (LLM -> SQL -> DB -> summary)
│   │   └── chat/
│   │       ├── parsers.py                # Parse/repair/extract SQL from LLM output
│   │       └── sql_runner.py             # SQL validation + execution
│   └── main.py                           # FastAPI app entrypoint
├── alembic/                              # Alembic config and revisions
├── supabase/                             # Supabase local config + SQL migration snapshots
├── test/                                 # Test scaffolding (in progress)
├── requirements.txt
└── README.md
```

## Domain Model

The schema models a realistic business and inventory domain, including:

- `customers`
- `vendors`
- `sites`
- `locations` (hierarchical)
- `items`
- `assets`
- `asset_transactions`
- `bills`
- `purchase_orders` + `purchase_order_lines`
- `sales_orders` + `sales_order_lines`

This makes the project suitable for procurement, sales, asset movement, and site-level analytics questions.

## Why These Technologies

### FastAPI

Why it fits:

- Fast API development
- Native `Pydantic` integration
- Automatic OpenAPI generation
- Good async support

Strength in this project:

- Clean endpoint design
- Easy API docs exposure (`/scalar`)
- Good foundation for auth/rate limiting later

### Pydantic + pydantic-settings

Why it fits:

- Validates request/response contracts
- Reduces payload errors
- Clean environment configuration handling (`database_url`, API keys)

Strength in this project:

- Strong API contracts
- Clear examples embedded in schema definitions

### SQLAlchemy

Why it fits:

- ORM for schema modeling
- Still supports raw SQL execution (critical for LLM-generated SQL)

Strength in this project:

- Session and pooling management
- Flexible local/Postgres/Supabase integration

### PostgreSQL / Supabase

Why it fits:

- PostgreSQL is strong for analytical queries and joins
- Supabase provides managed/local developer tooling
- Good support for RLS and production-ready features

Strength in this project:

- Excellent base for SaaS analytics assistants and operational reporting

### LangChain + Cohere

Why it fits:

- `LangChain` simplifies prompt orchestration and metadata handling
- `Cohere` is effective for structured text generation and SQL tasks with deterministic settings

Strength in this project:

- Fast prototyping
- Future provider flexibility (response schema already hints at `groq`)

### Faker

Why it fits:

- Generates realistic demo/test data quickly
- Helps stress-test query generation across varied scenarios

Strength in this project:

- Better demos and more meaningful QA than static seed rows

## Available API Endpoints

### `GET /test_api`

Simple health-style endpoint to verify the app is running.

### `POST /chat/`

Main endpoint for natural-language-to-SQL query generation, execution, and grounded response generation.

### `GET /scalar`

Scalar-based API docs UI for exploring the OpenAPI schema.

## Example Request / Response

### Request

```json
{
  "session_id": "11",
  "message": "what is the total sales for last month?",
  "context": {
    "role": "analyst"
  }
}
```

### Response (example)

```json
{
  "natural_language_answer": "Total sales for last month were 154320.75 USD based on the returned rows.",
  "sql_query": "SELECT COALESCE(SUM(sol.quantity * sol.unit_price), 0) AS total_sales FROM sales_orders so INNER JOIN sales_order_lines sol ON so.so_id = sol.so_id WHERE so.so_date >= date_trunc('month', CURRENT_DATE) - interval '1 month' AND so.so_date < date_trunc('month', CURRENT_DATE);",
  "token_usage": {
    "prompt_tokens": 1200,
    "completion_tokens": 260,
    "total_tokens": 1460
  },
  "latency_ms": 1840,
  "provider": "cohere",
  "model": "command-a-03-2025",
  "status": "ok",
  "row_count": 1,
  "rows_preview": [
    {
      "total_sales": 154320.75
    }
  ]
}
```

## Local Setup

### Prerequisites

- Python 3.10+ (3.11+ recommended)
- PostgreSQL or Supabase project/database
- Cohere API key for the chat flow

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or via the alias file:

```bash
pip install -r Requirements
```

### Environment Variables (`.env`)

Create a `.env` file in the project root with at least:

```env
database_url=postgresql://USER:PASSWORD@HOST:PORT/DBNAME
COHERE_API_KEY=your_cohere_api_key
LANGCHAIN_API_KEY=optional_if_tracing_enabled
LANGCHAIN_TRACING_V2=false
```

Notes:

- `database_url` is required for SQL execution
- `COHERE_API_KEY` is required for `/chat`
- `LANGCHAIN_*` is optional unless you want tracing

### Run the Application

```bash
uvicorn app.main:app --reload
```

After startup:

- API: `http://127.0.0.1:8000`
- Scalar Docs: `http://127.0.0.1:8000/scalar`

## Database Setup Paths (Current Repository State)

This repo currently contains more than one schema/migration path. That is acceptable during development, but it should be documented clearly.

### Path 1: SQLAlchemy schema + `init_db`

Uses:

- `app/db/schema.py`
- `app/db/init_db.py`
- `app/db/trigger.py`

Purpose:

- Create tables from ORM models
- Apply common `updated_at` triggers and indexes

Note:

- `init_db()` exists but is not enabled automatically on startup (safer default)

### Path 2: Supabase migrations

Uses:

- `supabase/config.toml`
- `supabase/migrations/*.sql`

Purpose:

- Local Supabase development
- SQL snapshots/experiments

Note:

- `supabase/config.toml` references `./seed.sql`, but that file is not currently present

### Path 3: Alembic (prepared, not fully implemented yet)

Alembic is wired to ORM metadata, but the current revision is still a placeholder with empty `upgrade()` / `downgrade()`.

Purpose:

- Production-style schema versioning in future iterations

## Dummy Data Generation

`app/db/dummy_data.py` is a strong utility for demos and testing. It generates realistic linked data using `Faker`.

Example usage:

```bash
python app/db/dummy_data.py --reset
```

```bash
python app/db/dummy_data.py --reset --customers 500 --vendors 100 --sales-orders 800 --purchase-orders 700
```

Why it is useful:

- Adjustable dataset sizes via CLI arguments
- Realistic cross-table relations
- Supports `TRUNCATE + RESTART IDENTITY` via `--reset`

## Security and SQL Safety

The project already includes a solid application-level safety layer:

- Read-only SQL enforcement (`SELECT` / `WITH` only)
- Blocks common DDL/DML operations
- Multi-statement protection
- Query timeout guard (`statement_timeout`)
- Controlled error responses (`status="error"`)

### Production Recommendations

- Use a DB user with read-only permissions for the chat query path
- Add structured logging (`app/core/logging.py` is a good future place)
- Add rate limiting on `/chat`
- Add authentication and authorization
- Monitor token usage and query latency/cost

## Current Engineering Status (Important Notes)

This is a strong MVP/prototype, but the repository is still in active development. Key points:

- Some files are placeholders (`user_service.py`, `models/user.py`, `core/logging.py`)
- `Dockerfile` and `Docker-compose.yaml` are empty placeholders
- Tests are mostly scaffolding; comprehensive test cases are not implemented yet
- Multiple migration paths exist (`Supabase` + `Alembic`) and should eventually converge on one source of truth
- The runtime DB schema must match the schema expected by the prompt and ORM, otherwise generated SQL may fail at execution time

## Why This Is a Strong Graduation / SaaS Foundation Project

It combines several important engineering areas in one practical system:

- Backend engineering
- Database design and relational modeling
- LLM orchestration
- Safety controls around generated code (SQL)
- Basic observability (latency and token usage)
- Clear path to production hardening

It can evolve into:

- AI Analytics Assistant
- ERP Chat Assistant
- Inventory Intelligence Bot
- Natural Language to SQL API service

## Suggested Next Steps (Roadmap)

- Add authentication and role-based access control
- Implement real conversation memory using `session_id`
- Switch to direct tool-calling flow (using `app/prompts/tools.py`) instead of relying on text parsing
- Add runtime schema introspection or an allowlist layer
- Add caching for repeated questions
- Add unit/integration tests for parsing, SQL validation, and execution
- Add Dockerization and a consistent local runtime
- Add CI/CD, linting, and formatting

## Quick Troubleshooting

If `/chat` fails:

- Verify `database_url`
- Verify `COHERE_API_KEY`
- Verify tables/columns exist with expected names
- Verify the live database schema matches the prompt/ORM assumptions

---

If you want, a next iteration can include:

- ERD section (entity relationship diagram)
- Example business questions by domain
- Arabic and English sample prompts
- Comparison between text parsing vs function-calling approaches
