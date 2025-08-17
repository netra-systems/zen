# 🤖 LLM MASTER INDEX - Netra Apex Navigation Guide

## 🔴 CRITICAL: File Location Reference

This index helps LLMs quickly locate and understand the purpose of files in the Netra Apex codebase.
**USE THIS FIRST** when searching for functionality or making changes.

---

## 📍 COMMONLY CONFUSED FILES & LOCATIONS

### Configuration Files (Multiple Similar Names)
| File | Location | Purpose | Common Confusion |
|------|----------|---------|------------------|
| `config.py` | `/app/config.py` | Main FastAPI app config | Often confused with scripts/config_setup_core.py |
| `config_setup_core.py` | `/scripts/config_setup_core.py` | Development setup script | NOT the main config |
| `.env` | `/` (root) | Environment variables | Check here for secrets |
| `settings.json` | `/frontend/settings.json` | Frontend settings | Different from backend config |

### Database Files (Similar Names, Different DBs)
| File | Location | Purpose | Key Functions |
|------|----------|---------|---------------|
| `clickhouse.py` | `/app/db/clickhouse.py` | ClickHouse connection | get_clickhouse_client() |
| `postgres.py` | `/app/db/postgres.py` | PostgreSQL connection | get_postgres_db() |
| `clickhouse_operations.py` | `/app/agents/data_sub_agent/clickhouse_operations.py` | ClickHouse data operations | Agent-specific queries |
| `models_auth.py` | `/app/db/models_auth.py` | Auth database models | User, Team, Session |
| `models_corpus.py` | `/app/db/models_corpus.py` | Corpus database models | CorpusData, CorpusEntry |
| `models_metrics.py` | `/app/db/models_metrics.py` | Metrics database models | MetricsData |

### Authentication & Security (Multiple Layers)
| File | Location | Purpose | Key Components |
|------|----------|---------|----------------|
| `auth.py` (routes) | `/app/routes/auth/auth.py` | Auth API endpoints | login, logout, register |
| `auth.py` (core) | `/app/auth/auth.py` | Auth logic & JWT | verify_token, create_access_token |
| `secret_manager.py` (app) | `/app/core/secret_manager.py` | Production secrets | get_secret, SecretManager class |
| `secret_manager.py` (dev) | `/dev_launcher/secret_manager.py` | Dev secrets only | Development environment only |
| `security.py` | `/app/auth/security.py` | Security utilities | Password hashing, validation |

### WebSocket Files (Complex Structure)
| File | Location | Purpose | Key Functions |
|------|----------|---------|---------------|
| `websockets.py` | `/app/routes/websockets.py` | WebSocket endpoints | websocket_endpoint() |
| `connection.py` | `/app/websocket/connection.py` | Connection management | ConnectionManager class |
| `quality_message_handler.py` | `/app/services/websocket/quality_message_handler.py` | Message quality handling | QualityMessageHandler |
| `websocket_types.py` | `/app/schemas/websocket_types.py` | WebSocket type definitions | WSMessage, WSResponse |
| `rate_limiter.py` | `/app/websocket/rate_limiter.py` | Rate limiting | RateLimiter class |
| `validation.py` | `/app/websocket/validation.py` | Message validation | validate_message() |

### Agent Files (Multi-Agent System)
| Agent Type | Location | Main File | Purpose |
|------------|----------|-----------|---------|
| Supervisor | `/app/agents/supervisor/` | `supervisor.py` | Main orchestrator agent |
| Data Sub-Agent | `/app/agents/data_sub_agent/` | `data_agent.py` | Data processing & insights |
| Triage Sub-Agent | `/app/agents/triage_sub_agent/` | `triage_agent.py` | Request classification |
| Admin Tool Dispatcher | `/app/agents/admin_tool_dispatcher/` | `dispatcher.py` | Admin tool routing |
| Corpus Admin | `/app/agents/corpus_admin/` | `corpus_agent.py` | Corpus management |
| Supply Researcher | `/app/agents/supply_researcher/` | `researcher.py` | Supply chain research |

### Test Files (Multiple Test Types)
| Test Type | Location | Pattern | Run Command |
|-----------|----------|---------|-------------|
| Unit Tests | `/app/tests/unit/` | `test_*.py` | `python test_runner.py --level unit` |
| E2E Tests | `/app/tests/e2e/` | `test_e2e_*.py` | `python test_runner.py --level e2e` |
| Real Agent Tests | `/app/tests/` | `test_real_agent_services.py` | Direct test file |
| Frontend Tests | `/frontend/__tests__/` | `*.test.tsx` | `npm test` |

---

## 🗂️ MAIN ENTRY POINTS

### Backend Entry Points
- **Main App**: `/app/main.py` - FastAPI application entry
- **Dev Launcher**: `/scripts/dev_launcher.py` - Development server starter
- **Test Runner**: `/scripts/test_runner.py` - Test execution entry

### Frontend Entry Points
- **Next.js App**: `/frontend/app/page.tsx` - Main page component
- **Layout**: `/frontend/app/layout.tsx` - App layout wrapper
- **Package.json**: `/frontend/package.json` - Frontend dependencies & scripts

---

## 📦 SCHEMA & TYPE DEFINITIONS

### Backend Schemas (`/app/schemas/`)
| Category | Files | Purpose |
|----------|-------|---------|
| LLM Types | `llm_types.py`, `llm_request.py`, `llm_response.py` | LLM communication types |
| Admin Types | `admin_types.py`, `admin_request.py` | Admin functionality types |
| WebSocket | `websocket_types.py`, `websocket_messages.py` | WebSocket message types |
| Auth | `auth_schemas.py` | Authentication schemas |
| Metrics | `metrics_schemas.py` | Metrics data schemas |

### Frontend Types (`/frontend/types/`)
| File | Purpose |
|------|---------|
| `index.ts` | Main type exports |
| `websocket.ts` | WebSocket types |
| `auth.ts` | Authentication types |
| `admin.ts` | Admin panel types |

---

## 🔧 UTILITY & HELPER FILES

### Core Utilities (`/app/core/`)
| File | Purpose | Key Functions |
|------|---------|---------------|
| `exceptions_base.py` | Base exception classes | NetraException |
| `exceptions_auth.py` | Auth exceptions | AuthenticationError |
| `exceptions_db.py` | Database exceptions | DatabaseError |
| `interfaces_base.py` | Base interfaces | BaseInterface |
| `interfaces_agent.py` | Agent interfaces | AgentInterface |
| `system_health_monitor.py` | System monitoring | HealthMonitor class |
| `fallback_coordinator.py` | Fallback handling | FallbackCoordinator |
| `memory_recovery_strategies.py` | Memory management | Recovery strategies |

### Scripts (`/scripts/`)
| Script | Purpose | When to Use |
|--------|---------|-------------|
| `check_architecture_compliance.py` | Check 300-line limit | Before commits |
| `reset_clickhouse.py` | Reset ClickHouse DB | Development reset |
| `setup_oauth_local.py` | Setup OAuth locally | Initial setup |
| `config_setup_core.py` | Core config setup | Development setup |

---

## 🎯 BUSINESS-CRITICAL FILES

### Revenue & Monetization
- `/app/services/billing/` - Billing service modules
- `/app/services/usage_tracking/` - Usage monitoring
- `/app/routes/pricing.py` - Pricing endpoints
- `/app/schemas/billing_types.py` - Billing type definitions

### Customer Segments
- `/app/services/segments/` - Customer segmentation
- `/app/db/models_customer.py` - Customer models
- `/app/routes/customers.py` - Customer endpoints

---

## 📋 SPECIFICATION FILES (`/SPEC/`)

### Priority Specs (Check First)
1. `type_safety.xml` - Type safety rules
2. `conventions.xml` - Coding standards & 300-line limit
3. `code_changes.xml` - Change checklist
4. `learnings/index.xml` - Past issues & solutions

### Domain-Specific Specs
- `websockets.xml` - WebSocket implementation
- `clickhouse.xml` - ClickHouse patterns
- `postgres.xml` - PostgreSQL patterns
- `security.xml` - Security requirements
- `testing.xml` - Testing standards

---

## 🚨 COMMON PITFALLS & SOLUTIONS

### Issue: "Can't find config file"
- **Check**: `/app/config.py` for app config
- **NOT**: `/scripts/config_setup_core.py` (setup script)

### Issue: "Database connection error"
- **ClickHouse**: Check `/app/db/clickhouse.py`
- **PostgreSQL**: Check `/app/db/postgres.py`
- **Env vars**: Check `.env` file

### Issue: "Authentication not working"
- **Routes**: `/app/routes/auth/auth.py`
- **Logic**: `/app/auth/auth.py`
- **Models**: `/app/db/models_auth.py`

### Issue: "WebSocket connection issues"
- **Endpoint**: `/app/routes/websockets.py`
- **Manager**: `/app/websocket/connection.py`
- **Types**: `/app/schemas/websocket_types.py`

### Issue: "Tests failing"
- **Runner**: `/scripts/test_runner.py`
- **Unit tests**: `/app/tests/unit/`
- **E2E tests**: `/app/tests/e2e/`

---

## 🔍 QUICK SEARCH PATTERNS

### Finding functionality:
1. Check this index first
2. Use `Grep` for specific function names
3. Check `/SPEC/learnings/` for past solutions
4. Look in `/app/services/` for business logic
5. Check `/app/routes/` for API endpoints

### Making changes:
1. Read relevant spec files first
2. Check for existing implementations
3. Follow 300-line module limit
4. Run tests before and after
5. Update specs if learning something new

---

## 📝 NOTES FOR LLMs

- **ALWAYS** check this index before searching
- **NEVER** confuse `/app/config.py` with `/scripts/config_setup_core.py`
- **ALWAYS** check `/SPEC/learnings/` for past issues
- **Files over 300 lines** must be split into modules
- **Functions over 8 lines** must be split into smaller functions
- **Type safety** is the #1 priority - check `type_safety.xml`

---

Last Updated: Check git history for latest changes