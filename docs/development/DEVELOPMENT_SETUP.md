# Netra Apex Development Setup - Revenue-Driven Development

## 🔴 CRITICAL: Business-First Development

**Every feature must justify its Business Value (BVJ) before implementation.**

## Table of Contents
- [Development Philosophy](#development-philosophy) **← READ FIRST**
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Module Development (300/8 Rule)](#module-development) **← MANDATORY**
- [Configuration](#configuration)
- [Development Workflow](#development-workflow)
- [Testing Requirements](#testing-requirements) **← 97% Coverage**
- [Troubleshooting](#troubleshooting)

## Development Philosophy

### Business Value Justification (BVJ) Template

**REQUIRED for every feature/PR:**

```markdown
## Business Value Justification

1. **Customer Segment**: [Free/Early/Mid/Enterprise]
2. **Business Goal**: [Increase savings/conversion/retention]
3. **Value Impact**: [Estimated % improvement]
4. **Revenue Impact**: [Estimated MRR increase]
5. **Implementation Cost**: [Dev hours]
6. **ROI**: [Revenue Impact / Implementation Cost]
```

### Module Development (300/8 Rule)

```python
# MANDATORY COMPLIANCE CHECK
# Run before EVERY commit:
python scripts/check_architecture_compliance.py

# Results must show:
# ✓ All files ≤ 300 lines
# ✓ All functions ≤ 8 lines
# ✓ No violations found
```

## Prerequisites

### Required Software
- **Python 3.9+** (3.11+ recommended for best performance)
- **Node.js 18+** (for frontend development)
- **Git** (for version control)

### Optional Services (with fallbacks)
- **PostgreSQL 14+** - Primary database (falls back to SQLite if unavailable)
- **Redis 7+** - Caching layer (disabled if unavailable)
- **ClickHouse** - Analytics database (limited analytics if unavailable)

### Development Tools
- **VS Code** or **PyCharm** (recommended IDEs)
- **Docker** (optional, for containerized development)
- **Postman** or **Insomnia** (for API testing)

## Quick Start

### 🚀 Recommended Developer Setup

```bash
# 1. Clone repository
git clone https://github.com/netra-systems/netra-apex.git
cd netra-core-generation-1

# 2. Read critical docs FIRST
cat CLAUDE.md  # Business requirements
cat SPEC/type_safety.xml  # Type safety rules
cat SPEC/conventions.xml  # 300/8 rule

# 3. Run automated setup
# Windows:
python scripts/setup.py

# 4. Start with OPTIMAL configuration
python scripts/dev_launcher.py --dynamic --no-backend-reload --load-secrets

# 5. Verify compliance
python scripts/check_architecture_compliance.py

# 6. Run unit tests (DEFAULT)
python test_runner.py --level unit
```

The automated installer will:
- ✅ Check all prerequisites
- ✅ Create Python virtual environment
- ✅ Install Python dependencies
- ✅ Install Node.js packages
- ✅ Setup databases (with fallbacks)
- ✅ Configure environment variables
- ✅ Create startup scripts
- ✅ Run verification tests

## Detailed Setup

### 1. Clone Repository
```bash
git clone https://github.com/netra-systems/netra-apex.git
cd netra-core-generation-1
```

### 2. Python Environment Setup

#### Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### Install Dependencies
```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt

# Optional: Install in editable mode
pip install -e .
```

### 3. Frontend Setup

#### Install Node Packages
```bash
cd frontend
npm install

# Or with yarn
yarn install

# Return to root
cd ..
```

#### Build Frontend Assets
```bash
cd frontend
npm run build
cd ..
```

### 4. Database Setup

#### PostgreSQL (Primary)
```sql
-- Create database
CREATE DATABASE netra_db;

-- Create user (optional)
CREATE USER netra_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE netra_db TO netra_user;
```

#### Run Migrations
```bash
# Using Alembic
alembic upgrade head

# Or using the setup script
python database_scripts/run_migrations.py
```

#### SQLite Fallback (Automatic)
If PostgreSQL is not available, the system automatically uses SQLite:
```bash
# SQLite database created at: ./netra.db
```

### 5. Redis Setup (Optional)

#### Install Redis
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Windows (WSL or Docker recommended)
docker run -d -p 6379:6379 redis:7-alpine
```

#### Verify Redis
```bash
redis-cli ping
# Should return: PONG
```

### 6. ClickHouse Setup (Optional)

#### Install ClickHouse
```bash
# Docker (recommended)
docker run -d \
  --name clickhouse \
  -p 9000:9000 \
  -p 8123:8123 \
  clickhouse/clickhouse-server

# Or native installation
# See: https://clickhouse.com/docs/en/install
```

#### Create Analytics Tables
```sql
-- Connect to ClickHouse
clickhouse-client

-- Create database
CREATE DATABASE IF NOT EXISTS netra_analytics;

-- Create tables
USE netra_analytics;

CREATE TABLE workload_events (
    timestamp DateTime,
    user_id UInt32,
    event_type String,
    event_data String,
    INDEX idx_user_id user_id TYPE minmax GRANULARITY 8192
) ENGINE = MergeTree()
ORDER BY timestamp;
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Core Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database URLs
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/netra_db
# Fallback: DATABASE_URL=sqlite+aiosqlite:///./netra.db

# Optional Services
REDIS_URL=redis://localhost:6379
CLICKHOUSE_URL=clickhouse://localhost:9000/netra_analytics

# Security Keys (generate secure keys for production)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
FERNET_KEY=generate-with-python-cryptography-fernet
SECRET_KEY=your-application-secret-key

# OAuth Configuration
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
FRONTEND_URL=http://localhost:3000

# LLM API Keys (for local development only)
# Note: In staging/production, these are loaded from Google Secret Manager
GEMINI_API_KEY=your-gemini-api-key  # Required - Primary LLM
OPENAI_API_KEY=your-openai-key      # Optional - OpenAI models
ANTHROPIC_API_KEY=your-anthropic-key # Optional - Anthropic models

# Development Options
DEV_MODE_DISABLE_REDIS=false
DEV_MODE_DISABLE_CLICKHOUSE=false
DEV_MODE_DISABLE_LLM=false

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### Generate Security Keys

```python
# Generate JWT Secret
import secrets
print(secrets.token_urlsafe(64))

# Generate Fernet Key
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())

# Generate Secret Key
import secrets
print(secrets.token_hex(32))
```

## Staging Environment

### Overview
Every pull request automatically gets its own staging environment with:
- Isolated database and Redis namespace
- Unique URLs: `https://pr-{number}.staging.netrasystems.ai`
- Automatic secret management with `-staging` suffix
- Complete isolation from production

### Accessing Your Staging Environment

When you create a PR:
1. **Automatic Deployment**: GitHub Actions deploys your branch
2. **URLs Posted**: Bot comments with your staging URLs
3. **Live Updates**: Push commits to update staging automatically

### Staging Secrets

**Important**: Staging uses Google Secret Manager with `-staging` suffix:

| Local Env Var | Staging Secret Name | Required |
|--------------|---------------------|----------|
| `GEMINI_API_KEY` | `gemini-api-key-staging` | ✅ Yes |
| `JWT_SECRET_KEY` | `jwt-secret-key-staging` | ✅ Yes |
| `FERNET_KEY` | `fernet-key-staging` | ✅ Yes |
| `OPENAI_API_KEY` | `openai-api-key-staging` | ❌ Optional |

### Testing in Staging

```bash
# View staging logs
gcloud run services logs read backend-pr-{number} --project=netra-staging

# Connect to staging database
gcloud sql connect staging-shared-postgres \
  --user=user_pr_{number} \
  --database=netra_pr_{number} \
  --project=netra-staging

# Test staging API
curl https://pr-{number}-api.staging.netrasystems.ai/health
```

### Environment Detection

The app automatically detects staging:
```python
# Staging is detected when:
# 1. ENVIRONMENT=staging
# 2. K_SERVICE exists (Cloud Run)
# 3. PR_NUMBER is set
```

### Staging vs Local Development

| Feature | Local Development | Staging Environment |
|---------|------------------|--------------------|
| **Database** | Local PostgreSQL/SQLite | Cloud SQL (isolated) |
| **Redis** | Local Redis | Shared Redis (isolated DB) |
| **Secrets** | `.env` file | Google Secret Manager |
| **LLM Keys** | Environment vars | Secret Manager with `-staging` |
| **URL** | `localhost:3000` | `pr-{number}.staging.netrasystems.ai` |
| **Hot Reload** | Yes | No (containerized) |
| **Persistence** | Until stopped | 7 days (auto-cleanup) |

## Development Workflow

### Starting Development Servers

#### Recommended: Unified Launcher
```bash
# Best configuration for development
python dev_launcher.py --dynamic --no-backend-reload --load-secrets

# What this does:
# - Finds free ports automatically
# - 30-50% faster without backend reload
# - Loads secrets from cloud if configured
# - Starts both frontend and backend
# - Shows clear status messages
```

#### Alternative Configurations
```bash
# With hot reload (slower but auto-refreshes)
python dev_launcher.py --dynamic

# Maximum performance (no reload at all)
python dev_launcher.py --dynamic --no-reload

# Custom ports
python dev_launcher.py --backend-port 8080 --frontend-port 3001

# Backend only
python dev_launcher.py --backend-only

# Frontend only
python dev_launcher.py --frontend-only
```

#### Manual Start (Traditional)
```bash
# Terminal 1: Backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Running Tests

#### Unified Test Runner (Recommended)
```bash
# Quick validation (< 30s)
python test_runner.py --level smoke

# Development testing (1-2 min)
python test_runner.py --level unit

# Feature validation (3-5 min)
python test_runner.py --level integration

# Full suite with coverage (10-15 min)
python test_runner.py --level comprehensive

# Critical paths only (1-2 min)
python test_runner.py --level critical
```

#### Traditional Testing
```bash
# Backend tests
pytest
pytest --cov=app --cov-report=html

# Frontend tests
cd frontend
npm test
npm run test:coverage

# E2E tests
npm run cypress:open
```

### Code Quality

#### Linting
```bash
# Python
ruff check app/
black app/ --check
mypy app/

# JavaScript/TypeScript
cd frontend
npm run lint
npm run typecheck
```

#### Formatting
```bash
# Python
black app/
isort app/

# JavaScript/TypeScript
cd frontend
npm run format
```

### Database Operations

#### Create New Migration
```bash
alembic revision --autogenerate -m "Description of change"
```

#### Apply Migrations
```bash
alembic upgrade head
```

#### Rollback Migration
```bash
alembic downgrade -1
```

#### Reset Database
```bash
# Drop and recreate
python database_scripts/reset_db.py

# Fresh migration
alembic upgrade head
```

## Troubleshooting

### Common Issues and Solutions

#### Port Already in Use
```bash
# Find process using port
# Windows
netstat -ano | findstr :8000

# macOS/Linux
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use dynamic ports
python dev_launcher.py --dynamic
```

#### Database Connection Errors
```bash
# Check PostgreSQL is running
pg_isready

# Verify connection string
psql postgresql://user:pass@localhost:5432/netra_db

# Use SQLite fallback
export DATABASE_URL=sqlite+aiosqlite:///./netra.db
```

#### Missing Dependencies
```bash
# Python dependencies
pip install -r requirements.txt --force-reinstall

# Node dependencies
cd frontend && rm -rf node_modules package-lock.json
npm install
```

#### Import Errors
```bash
# Ensure virtual environment is activated
which python  # Should show venv path

# Reinstall in editable mode
pip install -e .

# Update import tests
python test_runner.py --level smoke
```

#### LLM API Errors
```bash
# Disable LLM for development
export DEV_MODE_DISABLE_LLM=true

# Or mock responses
export LLM_MOCK_MODE=true
```

### Windows-Specific Issues

#### Unicode Errors
```bash
# Set encoding
set PYTHONIOENCODING=utf-8
chcp 65001
```

#### Path Length Limitations
```bash
# Enable long paths in Windows
# Run as Administrator:
reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1
```

#### Permission Errors
```bash
# Run as Administrator or use:
python -m pip install --user -r requirements.txt
```

## IDE Setup

### VS Code

#### Recommended Extensions
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)
- GitLens (eamodio.gitlens)
- Thunder Client (rangav.vscode-thunder-client)

#### Settings (.vscode/settings.json)
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

#### Launch Configuration (.vscode/launch.json)
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI Backend",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8000"],
      "jinja": true,
      "justMyCode": false
    },
    {
      "name": "Next.js Frontend",
      "type": "node",
      "request": "launch",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "cwd": "${workspaceFolder}/frontend",
      "console": "integratedTerminal"
    },
    {
      "name": "Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

### PyCharm

#### Configuration
1. Set Project Interpreter to venv
2. Mark `app` as Sources Root
3. Mark `frontend` as Resource Root
4. Configure Run Configurations:
   - FastAPI: Module `uvicorn`, Parameters `app.main:app --reload`
   - Next.js: npm script `dev` in `frontend` directory
   - Tests: pytest with project root as working directory

## Advanced Development

### Using Docker

#### Docker Compose Development
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  backend:
    build: .
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/netra_db
    depends_on:
      - db
      - redis
    command: uvicorn app.main:app --reload --host 0.0.0.0

  frontend:
    build: ./frontend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=netra_db
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

#### Start Docker Development
```bash
docker-compose -f docker-compose.dev.yml up
```

### Performance Profiling

#### Backend Profiling
```python
# Add to app/main.py for profiling
from pyinstrument import Profiler

profiler = Profiler()
profiler.start()
# ... application code ...
profiler.stop()
print(profiler.output_text(unicode=True, color=True))
```

#### Frontend Profiling
```bash
# React DevTools Profiler
npm run dev -- --profile

# Bundle analysis
cd frontend
npm run analyze
```

### Debugging

#### Backend Debugging
```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or with ipdb (better interface)
import ipdb; ipdb.set_trace()

# Or with VS Code/PyCharm debugger
# Set breakpoints in IDE
```

#### Frontend Debugging
```javascript
// Chrome DevTools
debugger;

// Console logging with groups
console.group('Agent Response');
console.log('Data:', data);
console.groupEnd();

// React DevTools
// Install browser extension
```

## Next Steps

1. **Run Tests**: Verify setup with `python test_runner.py --level smoke`
2. **Explore Codebase**: Review `SPEC/` directory for specifications
3. **Try Examples**: Check `SPEC/exampleNetraPrompts.xml` for sample queries
4. **Read Architecture**: See `docs/ARCHITECTURE.md` for system design
5. **Join Development**: Create feature branch and start coding!

## Support

- Documentation: `docs/` directory
- Specifications: `SPEC/` directory
- Issues: GitHub Issues
- Discord: [Join our Discord](https://discord.gg/netra-ai)

---

**Last Updated**: December 2025  
**Document Version**: 2.1  
**Development Status**: All Development Environments Operational  
**System Health**: 87% (EXCELLENT)  

## Current Development Environment Status (2025-12-09)

- **Local Development**: ✅ Dev launcher with dynamic port discovery
- **Staging Environment**: ✅ PR-based staging deployments active
- **Test Infrastructure**: ✅ 120+ mission critical tests operational
- **Docker Support**: ✅ Multi-environment containerization
- **Authentication**: ✅ OAuth + dev login fully functional
- **Database Support**: ✅ PostgreSQL + SQLite fallback
- **Business Value Focus**: ✅ BVJ template enforced for all features

## Getting Started Checklist

1. ✅ **Read CLAUDE.md** - Business requirements and development principles
2. ✅ **Run setup script** - `python scripts/setup.py`
3. ✅ **Start services** - `python scripts/dev_launcher.py --dynamic`
4. ✅ **Verify compliance** - `python scripts/check_architecture_compliance.py`
5. ✅ **Run tests** - `python test_runner.py --level unit`