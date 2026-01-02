# AI PR Code Reviewer - Backend

A FastAPI backend for AI-powered Pull Request code review analysis.

## Features

- ✅ Accept GitHub PR URLs (public repos) or uploaded diff text
- ✅ Fetch PR metadata, diff, and changed files from GitHub API
- ✅ AI-powered analysis using OpenAI (with heuristics fallback)
- ✅ Structured review output: summary, findings, risk matrix, test plan
- ✅ Merge readiness score
- ✅ GitHub comment posting (optional)
- ✅ SQLite/PostgreSQL persistence

## Quick Start

### 1. Install dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings (OPENAI_API_KEY for AI analysis)
```

### 3. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Access the API

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze` | Submit a PR for analysis |
| GET | `/api/runs/{run_id}` | Get analysis run status |
| GET | `/api/runs/{run_id}/result` | Get analysis results |
| GET | `/api/runs` | List recent analysis runs |

### GitHub Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/github/post-comment` | Post review to PR as comment |
| GET | `/api/github/validate-url` | Validate a PR URL |

## Example Usage

### Analyze a PR

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/123"}'
```

Response:
```json
{
  "run_id": 1,
  "status": "pending",
  "message": "Analysis started. Use GET /api/runs/{run_id} to check status."
}
```

### Check Status

```bash
curl http://localhost:8000/api/runs/1
```

### Get Results

```bash
curl http://localhost:8000/api/runs/1/result
```

## Output Format

The analysis produces a structured JSON review:

```json
{
  "pr_summary": {
    "what_changed": "...",
    "why_it_changed": "...",
    "key_files": ["..."]
  },
  "findings": [
    {
      "title": "Potential auth bypass in middleware",
      "severity": "high",
      "confidence": 0.74,
      "file": "api/auth/middleware.py",
      "evidence": "...",
      "recommendation": "..."
    }
  ],
  "risk_matrix": {
    "security": "high",
    "performance": "medium",
    "breaking_change": "low",
    "maintainability": "medium"
  },
  "test_plan": {
    "unit_tests": ["..."],
    "integration_tests": ["..."],
    "edge_cases": ["..."]
  },
  "merge_readiness": {
    "score": 78,
    "blockers": ["..."],
    "notes": "..."
  }
}
```

## Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | Database connection string | No (defaults to SQLite) |
| `OPENAI_API_KEY` | OpenAI API key for AI analysis | No (uses heuristics) |
| `GITHUB_TOKEN` | GitHub token for private repos/posting | No |
| `LLM_MODEL` | OpenAI model to use | No (defaults to gpt-4o-mini) |

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── config.py         # Settings and configuration
│   ├── models/           # SQLAlchemy models
│   │   ├── database.py
│   │   ├── user.py
│   │   └── analysis.py
│   ├── schemas/          # Pydantic schemas
│   │   ├── analysis.py
│   │   └── github.py
│   ├── routers/          # API routes
│   │   ├── analyze.py
│   │   ├── github.py
│   │   └── health.py
│   └── services/         # Business logic
│       ├── github.py     # GitHub API integration
│       └── analyzer.py   # Analysis engine
├── requirements.txt
├── .env.example
└── README.md
```

## Development

### Run tests

```bash
pytest
```

### Database migrations (if using Alembic)

```bash
alembic upgrade head
```

## Deployment

Recommended platforms:
- **Render** - Easy Python deployment
- **Fly.io** - Global edge deployment
- **Railway** - Simple containerized deployment

For production, use PostgreSQL instead of SQLite:

```
DATABASE_URL=postgresql://user:password@host:5432/dbname
```
