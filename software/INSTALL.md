# Sentinel3 Installation Guide

## Prerequisites

- Python 3.10+
- Windows 10/11
- PostgreSQL 14+ (for production; SQLite is used automatically for tests)

## Quick Start (SQLite — no PostgreSQL required)

```bash
# 1. Clone the repository
git clone <repo-url> sentinel3
cd sentinel3/software

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4a. Run with SQLite (development only):
$env:SENTINEL_DB_BACKEND = "sqlite"
streamlit run main_.py
```

## Production Setup (PostgreSQL)

```bash
# 1. Install PostgreSQL 14+ and create a database:
#    createdb sentinel
#    createuser sentinel -P   # set password

# 2. Set environment variables:
$env:SENTINEL_DB_BACKEND = "postgres"
$env:SENTINEL_PG_HOST = "localhost"
$env:SENTINEL_PG_PORT = "5432"
$env:SENTINEL_PG_DB = "sentinel"
$env:SENTINEL_PG_USER = "sentinel"
$env:SENTINEL_PG_PASSWORD = "<your-password>"

# 3. Run the application (schema auto-creates on first use):
streamlit run main_.py
```

## Configuration

The app auto-generates a Fernet encryption key on first run (saved to `software/.env`).
All journal entries and clinical notes are encrypted at rest with this key.
**Keep `.env` secure — never commit it. If lost, encrypted data cannot be recovered.**

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SENTINEL_DB_BACKEND` | No | `postgres` | `postgres` or `sqlite` |
| `SENTINEL_PG_HOST` | No | `localhost` | PostgreSQL host |
| `SENTINEL_PG_PORT` | No | `5432` | PostgreSQL port |
| `SENTINEL_PG_DB` | No | `sentinel` | PostgreSQL database name |
| `SENTINEL_PG_USER` | No | `sentinel` | PostgreSQL user |
| `SENTINEL_PG_PASSWORD` | Yes* | — | PostgreSQL password (*required for postgres backend) |
| `SENTINEL_PG_MIN_CONN` | No | `2` | Min connection pool size |
| `SENTINEL_PG_MAX_CONN` | No | `20` | Max connection pool size |
| `SENTINEL_PASSWORD_SALT` | No | fixed string | PBKDF2 salt for password hashing |
| `SENTINEL_ENCRYPTION_KEY` | No | auto-generated | Fernet encryption key |
| `SENTINEL_DB_PATH` | No | `data/sentinel.db` | SQLite database path (sqlite backend only) |
| `SENTINEL_EMAIL` | No | — | SMTP sender email for crisis alerts |
| `SENTINEL_EMAIL_PASSWORD` | No | — | SMTP password |
| `SENTINEL_RECEIVER` | No | — | SMTP receiver for crisis alerts |
| `GROQ_API_KEY` | No | — | Groq API key for AI features (falls back to Ollama) |

### Demo Credentials

- **Patients:** alice / pass123, bob / pass123, charlie / pass123
- **Psychologists:** dr.sarah / doc123, dr.james / doc123

## AI Backend (Optional)

By default the app uses Ollama (local) or Groq API for AI features.
- Install Ollama: https://ollama.com — run `ollama pull mistral`
- Or set `GROQ_API_KEY` to use Groq cloud API

## Running Tests

Tests always use the SQLite backend (no PostgreSQL required):

```bash
cd software
pytest tests/ -v
```

To run stress tests:

```bash
cd software
python stress_test.py