# Netra Apex - Enterprise AI Optimization Platform

**Production-ready AI workload optimization platform delivering 10-40% cost reduction through intelligent multi-agent analysis.**

## 💰 Business Value & ROI

Netra Apex creates and captures value proportional to customer AI/LLM/Agent spend:

| Segment | Monthly AI Spend | Cost Reduction | Pricing Model | Time to Value |
|---------|-----------------|----------------|---------------|---------------|
| **Free** | < $1K | 10-15% | Free (conversion focus) | < 24 hours |
| **Early** | $1K - $10K | 15-20% | 15% of savings | < 3 days |
| **Mid** | $10K - $100K | 20-30% | 20% of savings | < 5 days |
| **Enterprise** | > $100K | 30-40% | Custom SLA | < 7 days |

**Key Metrics:**
- **Average ROI:** 5:1 (save $5 for every $1 spent on Netra)
- **Payback Period:** < 30 days
- **Customer Retention:** 95% annual retention (Enterprise)


## 🎯 Core Features

### Multi-Agent AI Optimization System
- **Apex Optimizer Agent:** 40+ specialized tools for cost, performance, and efficiency analysis
- **Supervisor Agent:** Orchestrates sub-agent delegation and task management
- **Triage Agent:** Initial analysis and routing of optimization requests
- **Data Analysis Agent:** Deep analytics on usage patterns and anomalies
- **Reporting Agent:** Comprehensive report generation with actionable insights

### Key Capabilities
- **Real-time Cost Analysis:** Track AI spend across providers (OpenAI, Anthropic, Google, etc.)
- **Performance Optimization:** Reduce latency by 40-60% through intelligent caching and routing
- **Usage Pattern Detection:** Identify inefficient patterns and suggest optimizations
- **KV Cache Optimization:** Advanced key-value cache management for 30% memory reduction
- **Supply Catalog Search:** Find optimal model/provider combinations for workloads

## 🚀 Developer Guidelines

📖 **[CLAUDE.md](CLAUDE.md)** - Principal engineering philosophy and AI factory patterns
🧪 **[TESTING.md](TESTING.md)** - Comprehensive testing guide and unified test runner
🔧 **[TOOLING INDEX](TOOLING_INDEX.md)** - AI Native centric tools
📚 **[LLM INDEX.md](LLM_MASTER_INDEX.md)** - Complete file navigation index
🔍 **[SPEC/](SPEC/)** - Living source of truth (XML specifications)
🏭 **[AI Native Meta Process](SPEC/ai_native_meta_process.md)** - AI factory methodology for 99.99% correctness

**Core Development Principles:**
- **Business Value Justification (BVJ):** Every feature must demonstrate ROI
- **Architecture Standards:** 500-line modules, 25-line functions, high cohesion
- **Test-Driven Correction (TDC):** Bug fixes require failing test first
- **AI-Augmented Development:** Leverage specialized agents as force multipliers
- **String Literal Index:** 35,000+ indexed constants to prevent hallucination

## 📊 System Health & Compliance

### Architecture Compliance
```bash
# Check 500-line module and 25-line function limits
python scripts/check_architecture_compliance.py

# Generate comprehensive WIP status report
python scripts/generate_wip_report.py

# Validate string literals (prevent hallucination)
python scripts/query_string_literals.py validate "your_string"

# Update string literals index after changes
python scripts/scan_string_literals.py
```

### Critical Specifications
| Spec | Purpose | When to Check |
|------|---------|---------------|
| [`type_safety.xml`](SPEC/type_safety.xml) | Single source of truth, no duplication | Before any code |
| [`conventions.xml`](SPEC/conventions.xml) | Code standards and patterns | Before implementation |
| [`learnings/index.xml`](SPEC/learnings/index.xml) | System learnings and insights | Before starting work |
| [`string_literals_index.xml`](SPEC/string_literals_index.xml) | Platform constants index | Before using literals |
| [`staging_deployment_testing.xml`](SPEC/staging_deployment_testing.xml) | Staging validation | Before deployment |

## 🏃 Quick Start

### Prerequisites
- **Python:** 3.9+ (3.11+ recommended for performance)
- **Node.js:** 18+ (for frontend)
- **PostgreSQL:** 14+ (optional, SQLite for dev)
- **Redis:** 7+ (optional, for caching)
- **ClickHouse:** 23+ (optional, for analytics)

### Installation

```bash
# Clone repository
git clone https://github.com/netra-systems/netra-apex.git
cd netra-core-generation-1

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 🚀 Development Launcher

The dev launcher is the recommended way to start all services with proper configuration:

```bash
# Default start (all services with optimal settings)
python scripts/dev_launcher.py

# With additional options
python scripts/dev_launcher.py --dynamic --no-backend-reload --load-secrets

# Show all available options
python scripts/dev_launcher.py --help
```

**Dev Launcher Features:**
- ✅ Automatic service discovery and startup
- ✅ Health monitoring with visual indicators
- ✅ Secret management integration
- ✅ Database initialization
- ✅ Port conflict resolution
- ✅ Crash recovery
- ✅ Performance optimization

**Launches:**
Ports may be dynamic.
- Backend API: http://localhost:8000
- Frontend UI: http://localhost:3000
- WebSocket: ws://localhost:8000/ws
- API Docs: http://localhost:8000/docs

### Development Database Setup

```bash
# Option 1: Quick setup with Terraform (recommended)
cd terraform-dev-postgres
powershell -ExecutionPolicy Bypass -File quick-start.ps1  # Windows
./quick-start.sh  # macOS/Linux

# Creates: PostgreSQL, Redis, ClickHouse
# Auto-generates: .env.development.local

# Option 2: Use SQLite (no setup required)
# Dev launcher will auto-create SQLite database
```

### 🧪 Testing

**📖 See [TESTING.md](TESTING.md) for comprehensive testing documentation**

#### Quick Start

```bash
# Pre-commit smoke test (<30s)
python unified_test_runner.py --level smoke

# Default integration tests (3-5min)
python unified_test_runner.py --level integration

# Service-specific tests
python unified_test_runner.py --service backend
python unified_test_runner.py --service frontend
python unified_test_runner.py --service auth

# With coverage
python unified_test_runner.py --coverage
```

#### Test Levels

| Level | Duration | Purpose | Command |
|-------|----------|---------|---------|
| **smoke** | <30s | Pre-commit validation | `--level smoke` |
| **unit** | 1-2min | Component testing | `--level unit` |
| **integration** | 3-5min | Feature validation | `--level integration` |
| **comprehensive** | 30-45min | Full coverage | `--level comprehensive` |
| **critical** | 1-2min | Business-critical paths | `--level critical` |
| **agents** | 2-3min | Agent testing with LLMs | `--level agents --real-llm` |

#### Advanced Testing

```bash
# Real LLM testing
python unified_test_runner.py --real-llm

# Staging environment
python unified_test_runner.py --env staging

# Parallel execution
python unified_test_runner.py --parallel --workers 8

# Pattern matching
python unified_test_runner.py --pattern "test_auth"
```

**Key Features:**
- 🎯 **Unified Interface:** Single command for all services
- ⚡ **Smart Parallelization:** Optimal test distribution
- 📊 **Coverage Reports:** HTML and terminal reports
- 🔄 **Test Isolation:** Prevent test pollution
- 📈 **Performance Tracking:** Monitor test execution times
- 🎭 **Mock/Real Toggle:** Switch between mocked and real services

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js 14 + React 18)            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │  Auth Guard  │  │   Chat UI    │  │  Enhanced WebSocket │    │
│  │  & Context   │  │  Components  │  │     Provider       │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │            Zustand State Management + API Client         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │ WebSocket + REST API
┌─────────────────────────────┴───────────────────────────────────┐
│                        Backend (FastAPI + SQLAlchemy)            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Multi-Agent Optimization System             │    │
│  │  ┌────────────────┐     ┌─────────────────────────┐    │    │
│  │  │ Apex Optimizer │────▶│ 40+ Specialized Tools   │    │    │
│  │  │     Agent      │     │ (Cost, Perf, KV Cache) │    │    │
│  │  └────────────────┘     └─────────────────────────┘    │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐         │    │
│  │  │Supervisor│──▶│  Triage  │──▶│Data Analysis│         │    │
│  │  │  Agent   │  │  Agent   │  │    Agent     │         │    │
│  │  └──────────┘  └──────────┘  └──────────────┘         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │          Core Services & Infrastructure                   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │  Auth/JWT    │  │  WebSocket   │  │  Rate Limit  │   │  │
│  │  │  Service     │  │   Manager    │  │   Service    │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│                    Data Layer & External Services                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  PostgreSQL  │  │  ClickHouse  │  │    Redis Cache      │  │
│  │  (Primary)   │  │  (Analytics) │  │   (Sessions/Data)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         External LLM Providers (OpenAI, Anthropic)       │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Tech Stack

**Backend Technologies:**
- **Framework:** FastAPI (async Python web framework)
- **ORM:** SQLAlchemy 2.0 with async support
- **Validation:** Pydantic V2 for data validation
- **Migration:** Alembic for database migrations
- **Task Queue:** Celery with Redis broker (optional)

**Frontend Technologies:**
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript 5.x
- **State:** Zustand for global state management
- **Styling:** TailwindCSS + Shadcn/ui components
- **WebSocket:** Custom enhanced provider with auto-reconnect

**Data Layer:**
- **Primary DB:** PostgreSQL 14+ (users, sessions, threads)
- **Analytics DB:** ClickHouse 23+ (metrics, logs, events)
- **Cache:** Redis 7+ (sessions, rate limiting, temporary data)
- **Vector DB:** Planned - for semantic search

**Infrastructure & DevOps:**
- **Containerization:** Docker + Docker Compose
- **Orchestration:** Kubernetes-ready with Helm charts
- **CI/CD:** GitHub Actions with matrix testing
- **Monitoring:** Prometheus + Grafana + OpenTelemetry
- **Logging:** Structured JSON logging with correlation IDs

## 🔤 String Literals Index System

**Critical system preventing LLM hallucination - 35,000+ indexed platform constants**

```bash
# ALWAYS validate strings before use
python scripts/query_string_literals.py validate "redis_url"

# Search for existing strings
python scripts/query_string_literals.py search "websocket"

# Update index after adding new constants
python scripts/scan_string_literals.py

# Query specific categories
python scripts/query_string_literals.py list --category configuration
```

**Indexed Categories:**
- `configuration`: Config keys, settings (e.g., "redis_url", "max_retries")
- `paths`: API endpoints, file paths (e.g., "/api/v1/threads", "/websocket")
- `identifiers`: Service names, agent types (e.g., "supervisor_agent")
- `database`: Table/column names (e.g., "threads", "created_at")
- `events`: Event names, message types (e.g., "thread_created")
- `metrics`: Metric names and labels
- `environment`: Environment variables (e.g., "NETRA_API_KEY")
- `states`: Status values, conditions (e.g., "pending", "active")


## 🏗 Project Structure

```
netra-core-generation-1/
├── app/                        # Main Backend Service (FastAPI)
│   ├── agents/                # Multi-agent system implementations
│   ├── auth_integration/      # MANDATORY shared auth module
│   ├── core/                  # Core utilities and base classes
│   ├── db/                    # Database models and connections
│   ├── routes/                # API endpoints and WebSocket
│   ├── schemas/               # Pydantic models and types
│   ├── services/              # Business logic and services
│   │   └── apex_optimizer_agent/  # 40+ optimization tools
│   └── websocket/             # WebSocket infrastructure
│
├── auth_service/              # Independent Auth Microservice
│   └── main.py               # OAuth/JWT service
│
├── frontend/                  # Frontend Application (Next.js 14)
│   ├── app/                  # App router pages
│   ├── components/           # React components
│   ├── providers/            # Context providers
│   ├── services/             # API clients and services
│   └── __tests__/            # Frontend test suites
│
├── SPEC/                      # Living Documentation (XML)
│   ├── learnings/            # System insights and patterns
│   ├── generated/            # Auto-generated indexes
│   └── *.xml                 # Specification files
│
├── test_framework/            # Unified Testing Infrastructure
│   ├── test_runner.py        # Main test orchestrator
│   ├── bad_test_detector.py  # Flaky test detection
│   └── coverage_analyzer.py  # Coverage reporting
│
├── scripts/                   # Development & Operations
│   ├── dev_launcher.py       # Development environment starter
│   ├── compliance/           # Architecture compliance checking
│   └── query_string_literals.py  # String validation tool
│
├── tests/                     # Legacy test directory
│   └── e2e/                  # End-to-end test suites
│
└── organized_root/            # Deployment configurations
    └── deployment_configs/    # Staging/production deploy scripts
```

## 🧪 Testing Strategy

### Test Coverage Requirements
- **Target Coverage:** 97% (enforced in CI/CD)
- **Critical Paths:** 100% coverage required
- **Agent Systems:** Real LLM testing mandatory

### Bad Test Detection System
```bash
# View flaky test report
python -m test_framework.bad_test_reporter

# View specific test history
python -m test_framework.bad_test_reporter --test "test_name"

# Reset bad test tracking
python -m test_framework.bad_test_reporter --reset
```

### Testing Best Practices
1. **Before Commits:** Run integration tests with fast-fail
2. **After Agent Changes:** Test with real LLM providers
3. **Before Deployment:** Full staging validation suite
4. **Performance Changes:** Run performance baseline tests

**Reference:** [SPEC/test_runner_guide.xml](SPEC/test_runner_guide.xml)

## 🚀 Deployment

### Staging Environment (GCP)

```bash
# Pre-deployment validation
python unified_test_runner.py --level staging --env staging

# Deploy to staging
python organized_root/deployment_configs/deploy_staging.py

# Verify deployment
python scripts/test_staging_startup.py

# Rollback if needed
python organized_root/deployment_configs/rollback_staging.py --version previous
```

### Production Deployment

```bash
# Build production images
docker build -t netra-backend:prod -f Dockerfile.prod .
docker build -t netra-frontend:prod -f frontend/Dockerfile.prod .

# Run with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Kubernetes deployment
kubectl apply -f k8s/production/
```

### Environment Variables
Required for production:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `CLICKHOUSE_URL`: ClickHouse connection
- `JWT_SECRET`: JWT signing key
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key

**Deployment Guides:**
- [SPEC/staging_deployment_testing.xml](SPEC/staging_deployment_testing.xml)
- [SPEC/learnings/deployment_staging.xml](SPEC/learnings/deployment_staging.xml)


## 📊 Performance Monitoring & SLAs

### Service Level Objectives (SLOs)

| Metric | Target | Alert Threshold | Business Impact |
|--------|--------|-----------------|-----------------|
| **API Latency (p99)** | < 2000ms | > 3000ms | User experience degradation |
| **WebSocket Connection** | < 500ms | > 1000ms | Real-time features fail |
| **Agent Response** | < 30s | > 45s | Customer frustration |
| **Availability** | 99.9% | < 99.5% | Revenue loss |
| **Error Rate** | < 0.1% | > 0.5% | Data integrity risk |

### Monitoring Stack

**Metrics Collection:**
- **Prometheus:** Time-series metrics database
- **Grafana:** Visualization and dashboards
- **OpenTelemetry:** Distributed tracing

**Key Dashboards:**
1. **Business Metrics:** ROI, cost savings, usage
2. **System Health:** CPU, memory, disk, network
3. **Application Performance:** Response times, throughput
4. **Agent Performance:** Tool usage, completion rates
5. **WebSocket Health:** Connection pool, message rates

### Alerting Rules

```yaml
# Critical alerts (PagerDuty)
- API down for > 2 minutes
- Database connection pool exhausted
- Agent system failure rate > 10%

# Warning alerts (Slack)
- Memory usage > 80%
- Response time degradation > 20%
- WebSocket disconnection rate > 5%
```



## 🔐 Security & Compliance

### Security Features
- **Authentication:** OAuth 2.0 + JWT with refresh tokens
- **Authorization:** Role-based access control (RBAC)
- **Encryption:** TLS 1.3 for transit, AES-256 for rest
- **Secret Management:** HashiCorp Vault integration
- **Audit Logging:** Complete audit trail for compliance

### Compliance
- **SOC 2 Type II:** In progress
- **GDPR:** Data privacy controls implemented
- **HIPAA:** Healthcare data isolation available
- **ISO 27001:** Security management system

## 🔧 Troubleshooting

### Common Issues

**WebSocket Connection Failures:**
```bash
# Check WebSocket health
curl http://localhost:8000/health/websocket

# View connection logs
tail -f logs/websocket.log | grep ERROR
```

**Agent System Issues:**
```bash
# Test agent connectivity
python scripts/test_agent_system.py

# Check LLM provider status
python scripts/check_llm_providers.py
```

**Database Connection Issues:**
```bash
# Test database connectivity
python scripts/test_db_connection.py

# Reset connection pool
python scripts/reset_db_pool.py
```

## 🔗 Key Resources

### Essential Documentation
- **[CLAUDE.md](CLAUDE.md)** - Principal engineering philosophy
- **[LLM_MASTER_INDEX.md](LLM_MASTER_INDEX.md)** - Complete file navigation
- **[SPEC/learnings/index.xml](SPEC/learnings/index.xml)** - System learnings

### Critical Specifications
- **[SPEC/type_safety.xml](SPEC/type_safety.xml)** - Type safety enforcement
- **[SPEC/conventions.xml](SPEC/conventions.xml)** - Code standards
- **[SPEC/string_literals_index.xml](SPEC/string_literals_index.xml)** - Constant validation
- **[SPEC/test_runner_guide.xml](SPEC/test_runner_guide.xml)** - Testing strategy
- **[SPEC/independent_services.xml](SPEC/independent_services.xml)** - Service boundaries

### Support & Community
- **GitHub Issues:** [github.com/netra-systems/netra-core/issues](https://github.com/netra-systems/netra-core/issues)
- **Documentation:** [docs.netrasystems.ai](https://docs.netrasystems.ai)
- **Status Page:** [status.netrasystems.ai](https://status.netrasystems.ai)

---

**© 2025 Netra Systems** - Enterprise AI Optimization Platform
*Delivering measurable ROI through intelligent workload analysis*