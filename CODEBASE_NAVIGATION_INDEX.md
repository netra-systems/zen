# 🗺️ Netra Apex Codebase Navigation Index

## 📁 Project Overview

**Netra Apex AI Optimization Platform** - Enterprise AI workload optimization platform with multi-agent architecture designed to help companies reduce AI/LLM costs while maintaining or improving quality.

### Key Statistics
- **Language**: Python (Backend), TypeScript/React (Frontend)
- **Architecture**: Microservices (Main Backend, Auth Service, Frontend)
- **Databases**: PostgreSQL (main data), ClickHouse (analytics), Redis (caching)
- **AI Integration**: Multi-LLM support (OpenAI, Anthropic, Google, etc.)

## 🏗️ Architecture Overview

```
netra-core-generation-1/
├── app/                    # Main backend application (FastAPI)
├── auth_service/          # Independent auth microservice
├── frontend/              # Next.js React frontend
├── tests/                 # Test suites
├── scripts/               # Development & deployment scripts
├── SPEC/                  # Specifications & documentation
├── terraform-gcp/         # Infrastructure as code
└── dev_launcher/          # Development environment manager
```

## 🎯 Quick Navigation Guide

### For Different Tasks:

#### 🔧 "I need to fix a bug"
1. Check `/SPEC/learnings/` for known issues
2. Use `/LLM_MASTER_INDEX.md` for file locations
3. Run tests: `python test_runner.py`
4. Check compliance: `python scripts/check_architecture_compliance.py`

#### ➕ "I need to add a feature"
1. Review `/CLAUDE.md` for principles
2. Check `/SPEC/conventions.xml` for standards
3. Find similar code in `/app/services/` or `/app/agents/`
4. Follow the 300-line file / 8-line function limits

#### 🔍 "I need to understand how something works"
1. Start with `/LLM_MASTER_INDEX.md`
2. Check `/app/routes/` for API endpoints
3. Look in `/app/services/` for business logic
4. Review `/app/agents/` for AI components

## 📂 Core Directories

### `/app` - Main Backend Application

#### Structure:
```
app/
├── agents/              # AI agent implementations
│   ├── supervisor/      # Main orchestrator agent
│   ├── data_sub_agent/  # Data analysis agent
│   ├── triage_sub_agent/# Intent detection agent
│   └── corpus_admin/    # Content management agent
├── routes/              # API endpoints
├── services/            # Business logic services
├── db/                  # Database connections & models
├── core/                # Core utilities & abstractions
├── schemas/             # Pydantic models & types
├── websocket/           # WebSocket management
└── llm/                 # LLM client & management
```

#### Key Files:
- `main.py` - FastAPI application entry point
- `config.py` - Application configuration
- `dependencies.py` - Dependency injection
- `startup_checks.py` - System health validation

### `/auth_service` - Authentication Microservice

**CRITICAL**: All authentication MUST use `/app/auth_integration/` for shared auth.

#### Structure:
```
auth_service/
├── main.py              # Auth service entry
├── services/            # Auth business logic
├── models/              # Auth data models
└── routes/              # Auth endpoints
```

### `/frontend` - Next.js React Application

#### Structure:
```
frontend/
├── app/                 # Next.js app directory
├── components/          # React components
├── types/               # TypeScript definitions
├── hooks/               # Custom React hooks
├── lib/                 # Utility libraries
└── public/              # Static assets
```

#### Key Files:
- `app/page.tsx` - Main page component
- `app/layout.tsx` - Root layout
- `package.json` - Dependencies & scripts

### `/tests` - Testing Infrastructure

#### Test Categories:
```
tests/
├── unified/             # E2E integration tests
├── e2e/                 # End-to-end tests
├── integration/         # Integration tests
└── conftest.py          # Pytest configuration
```

#### Running Tests:
```bash
# Quick test
python test_runner.py --level integration --no-coverage --fast-fail

# Full test suite
python test_runner.py --level all --real-llm

# Specific category
python test_runner.py --level e2e
```

### `/SPEC` - Specifications & Documentation

#### Priority Specs:
1. `type_safety.xml` - Type safety requirements
2. `conventions.xml` - Coding standards
3. `learnings/index.xml` - Lessons learned
4. `code_changes.xml` - Change checklist

#### Domain Specs:
- `websockets.xml` - WebSocket patterns
- `clickhouse.xml` - ClickHouse usage
- `postgres.xml` - PostgreSQL patterns
- `security.xml` - Security requirements

## 🔌 API Routes & Endpoints

### Core Routes (`/app/routes/`)

| Route File | Path Prefix | Purpose |
|------------|-------------|---------|
| `agent_route.py` | `/api/v1/agent` | Agent interactions |
| `websockets.py` | `/ws` | WebSocket connections |
| `users.py` | `/api/v1/users` | User management |
| `auth_routes/` | `/api/v1/auth` | Authentication |
| `demo.py` | `/api/v1/demo` | Demo features |
| `health.py` | `/api/v1/health` | Health checks |
| `corpus.py` | `/api/v1/corpus` | Content management |
| `synthetic_data.py` | `/api/v1/synthetic` | Data generation |
| `threads_route.py` | `/api/v1/threads` | Thread management |
| `monitoring.py` | `/api/v1/monitoring` | System monitoring |

## 🤖 Agent System

### Agent Hierarchy:
```
SupervisorAgent (Orchestrator)
├── TriageSubAgent (Intent Detection)
├── DataSubAgent (Analytics)
├── ActionsSubAgent (Action Planning)
├── CorpusAdminAgent (Content Management)
├── ReportingSubAgent (Report Generation)
├── OptimizationsAgent (Optimization)
└── SyntheticDataAgent (Data Generation)
```

### Key Agent Files:
- `/app/agents/supervisor_consolidated.py` - Main orchestrator
- `/app/agents/base.py` - Base agent class
- `/app/agents/state.py` - Agent state management
- `/app/agents/tool_dispatcher.py` - Tool execution

## 💾 Database Architecture

### PostgreSQL (Main Database)
- **Models**: `/app/db/models_postgres.py`
- **Connection**: `/app/db/postgres.py`
- **Session**: `/app/db/postgres_session.py`

### ClickHouse (Analytics)
- **Client**: `/app/db/clickhouse.py`
- **Operations**: `/app/agents/data_sub_agent/clickhouse_operations.py`
- **Query Fixer**: `/app/db/clickhouse_query_fixer.py`

### Redis (Caching)
- **Manager**: `/app/redis_manager.py`
- **WebSocket State**: `/app/ws_manager.py`

## 🔐 Authentication & Security

### Shared Authentication (MANDATORY)
- **Integration**: `/app/auth_integration/auth.py`
- **Functions**: `get_current_user()`, `validate_token()`
- **Models**: `/app/auth_integration/models.py`

### Security Components:
- **Secret Manager**: `/app/core/secret_manager.py`
- **Middleware**: `/app/middleware/security_middleware.py`
- **Headers**: `/app/middleware/security_headers.py`

## 🌐 WebSocket System

### Core Components:
- **Routes**: `/app/routes/websockets.py`
- **Manager**: `/app/websocket/connection_manager.py`
- **Broadcasting**: `/app/websocket/broadcast.py`
- **Rate Limiting**: `/app/websocket/rate_limiter.py`
- **Validation**: `/app/websocket/validation.py`

### Message Flow:
1. Client connects → `websocket_endpoint()`
2. Authentication → `get_current_user()`
3. Message handling → `message_handler.py`
4. Broadcasting → `broadcast_manager.py`

## 🛠️ Development Tools

### Essential Scripts:
```bash
# Start development environment
python scripts/dev_launcher.py

# Run tests
python test_runner.py

# Check code compliance
python scripts/check_architecture_compliance.py

# Deploy to staging
./deploy-staging-reliable.ps1
```

### Configuration Files:
- `.env` - Environment variables
- `config.yaml` - Application config
- `pytest.ini` - Test configuration
- `alembic.ini` - Database migrations

## 📊 Monitoring & Observability

### Components:
- **Metrics**: `/app/monitoring/metrics_collector.py`
- **Alerts**: `/app/monitoring/alert_manager.py`
- **Dashboard**: `/app/monitoring/dashboard.py`
- **Performance**: `/app/monitoring/performance_monitor.py`

### Health Checks:
- `/api/v1/health` - Basic health
- `/api/v1/health/extended` - Detailed health
- `/api/v1/health/dependencies` - Service dependencies

## 🚀 Deployment

### Environments:
- **Local**: `python scripts/dev_launcher.py`
- **Staging**: GCP Cloud Run (terraform-gcp/)
- **Production**: Not yet deployed

### CI/CD:
- **GitHub Actions**: `.github/workflows/`
- **Terraform**: `terraform-gcp/`
- **Docker**: `Dockerfile.*` files

## 📈 Business Logic

### Core Services (`/app/services/`)

| Service | Purpose |
|---------|---------|
| `agent_service.py` | Agent orchestration |
| `quality_gate_service.py` | Quality validation |
| `synthetic_data_service.py` | Data generation |
| `corpus_service.py` | Content management |
| `thread_service.py` | Conversation threads |
| `generation_service.py` | Content generation |
| `user_service.py` | User management |

## 🔍 Common Tasks

### Finding Code:
1. Use `/LLM_MASTER_INDEX.md` first
2. Search with `Grep` tool
3. Check `/SPEC/learnings/` for patterns
4. Look in similar components

### Making Changes:
1. Check specs in `/SPEC/`
2. Follow 300-line/8-line limits
3. Run tests before committing
4. Update documentation if needed

### Debugging:
1. Check logs: `/app/logging_config.py`
2. Review error handlers: `/app/core/error_handlers.py`
3. Check circuit breakers: `/app/core/circuit_breaker.py`
4. Review recovery strategies: `/app/core/error_recovery.py`

## 📝 Code Standards

### Must Follow:
- **300-line limit** per file
- **8-line limit** per function
- **Type safety** (no Any types)
- **Single source of truth** (no duplicates)
- **No test stubs** in production

### Checking Compliance:
```bash
python scripts/check_architecture_compliance.py
```

## 🎓 Learning Resources

### Key Documentation:
- `/CLAUDE.md` - Engineering principles
- `/LLM_MASTER_INDEX.md` - File location guide
- `/SPEC/learnings/` - Lessons learned
- `/SPEC/ai_factory_patterns.xml` - AI patterns

### Test Documentation:
- `/tests/README.md` - Test guide
- `/test_framework/README.md` - Framework guide
- `/test_reports/` - Test results

## 🔗 Quick Links

### Most Used Files:
1. `/app/logging_config.py` - Logging (495 uses)
2. `/app/agents/state.py` - Agent state (114 uses)
3. `/app/llm/llm_manager.py` - LLM management (87 uses)
4. `/app/db/models_postgres.py` - Database models (73 uses)
5. `/app/core/exceptions_base.py` - Exceptions (66 uses)

### Critical Integrations:
- **Auth**: `/app/auth_integration/auth.py`
- **WebSocket**: `/app/ws_manager.py`
- **Redis**: `/app/redis_manager.py`
- **Config**: `/app/config.py`

## 🚨 Important Notes

1. **NEVER** duplicate auth logic - use `/app/auth_integration/`
2. **ALWAYS** check `/SPEC/learnings/` before fixing issues
3. **FOLLOW** 300-line file and 8-line function limits
4. **USE** type safety - no Any types allowed
5. **TEST** before committing changes

---

*Last Updated: 2025-08-19*
*Use `/LLM_MASTER_INDEX.md` for detailed file locations*