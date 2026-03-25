# Backend - AI Personal Assistant API

FastAPI-based backend for the AI Personal Assistant agent system.

## 🚀 Quick Start

```bash
# Setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your configuration

# Run
uvicorn app.main:app --reload

# Access API docs
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

## 🔒 Security Features (Agent D)

### Authentication & Authorization
- **JWT Tokens** with revocation support (JTI blacklist)
- **OAuth 2.0** (Google, GitHub)
- **Token Refresh** mechanism
- **Secure Scopes** for fine-grained permissions

### Secrets Management
- Environment variables (dev/staging)
- Vault integration ready (AWS/HashiCorp)
- Encrypted credential storage
- Automatic token encryption

### Audit Logging
- Comprehensive action tracking (25+ types)
- Approval workflow logging
- Immutable audit trail in database
- User activity history

### CI/CD Security
- SAST (Bandit)
- Dependency scanning (pip-audit, safety)
- Automated security tests
- Docker image scanning

## 📁 Project Structure

```
app/
├── core/              # Core functionality
│   ├── config.py      # Settings & environment
│   ├── auth.py        # JWT & OAuth (NEW)
│   ├── security.py    # Secrets & crypto (NEW)
│   └── audit.py       # Audit logging (NEW)
├── api/               # API routes
│   └── v1/
│       ├── router.py
│       └── endpoints/
├── db/                # Database
│   ├── config.py
│   └── migrations/    # Alembic (NEW)
└── schemas/           # Data models

tests/
├── conftest.py        # Pytest fixtures (NEW)
├── unit/
│   └── test_auth.py   # Auth tests (NEW)
└── integration/
```

## ⚙️ Configuration

**Environment Variables** (see `.env.example`):
- Application (debug, origins, etc.)
- Database (PostgreSQL)
- Cache (Redis)
- Authentication (JWT, OAuth)
- External APIs (Groq, Gmail, Calendar)
- Logging & Monitoring
- Feature Flags

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# By marker
pytest -m unit -v           # Unit tests
pytest -m security -v       # Security tests
pytest -m integration -v    # Integration tests
```

**Coverage:** 80%+ for core auth/security modules

## 🔗 Dependencies Installed

- **Framework**: FastAPI, Uvicorn
- **Database**: SQLAlchemy, Alembic, psycopg2
- **Cache**: Redis
- **Auth**: PyJWT, cryptography, passlib
- **LLM**: LangChain, LangGraph, Groq
- **External APIs**: Google API client
- **Testing**: pytest, pytest-cov, pytest-asyncio
- **Security**: bandit, pip-audit, safety
- **Code Quality**: black, isort, ruff, mypy

## 🐳 Docker

```bash
# Build
docker build -t ai-assistant-api:latest .

# Run
docker run -p 8000:8000 -e DATABASE_URL=postgresql://... ai-assistant-api:latest

# Or use docker-compose
docker-compose up backend
```

## 📚 Documentation

- **[SECURITY_DEVOPS.md](../SECURITY_DEVOPS.md)** - Complete security guide
- **[TESTING.md](../TESTING.md)** - Testing strategy
- **[AGENT_D_COMPLETION.md](../AGENT_D_COMPLETION.md)** - Delivery summary
- **[.env.example](.env.example)** - Configuration template

## Repository Tracking Policy

This repository currently ignores most auxiliary artifacts at the root policy level:
- Markdown files except `README.md`/`readme.md`
- Test files and test directories
- Shell scripts (`*.sh`)
- YAML files (`*.yml`, `*.yaml`)
- `SETUP_SCRIPTS/`
