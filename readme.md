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
📚 **[LLM_MASTER_INDEX.md](LLM_MASTER_INDEX.md)** - Complete file navigation index
🔍 **[SPEC/](SPEC/)** - Living source of truth (XML specifications)

**Core Development Principles:**
- **Business Value Justification (BVJ):** Every feature must demonstrate ROI
- **Architecture Standards:** 500-line modules, 25-line functions, high cohesion
- **Test-Driven Correction (TDC):** Bug fixes require failing test first
- **AI-Augmented Development:** Leverage specialized agents as force multipliers
- **String Literal Index:** 35,000+ indexed constants to prevent hallucination

## 📊 System Status

```bash
# Check compliance
python scripts/check_architecture_compliance.py

# Update status report
python scripts/generate_wip_report.py

# Validate string literals
python scripts/query_string_literals.py validate
```

**Key Reports:**
- [MASTER_WIP_STATUS.md](MASTER_WIP_STATUS.md) - System health
- [SPEC/learnings/index.xml](SPEC/learnings/index.xml) - All learnings
- [SPEC/string_literals_index.xml](SPEC/string_literals_index.xml) - Platform constants

## 🏃 Quick Start

### Prerequisites
- Python 3.9+ (3.11+ recommended)
- Node.js 18+
- PostgreSQL 14+ (optional, can use SQLite for development)
- Redis 7+ (optional, for caching)

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

### 🧪 Testing Quick Start

```bash
# Run default test suite (fast feedback)
python -m test_framework.test_runner

# With specific options
python -m test_framework.test_runner --level integration --no-coverage --fast-fail

# Test specific areas
python -m test_framework.test_runner --level agents        # Agent tests
python -m test_framework.test_runner --level websocket     # WebSocket tests
python -m test_framework.test_runner --level auth          # Auth tests

# With real LLM (for agent testing)
python -m test_framework.test_runner --level agents --real-llm

# Before production release (comprehensive)
python -m test_framework.test_runner --level integration --real-llm --env staging
```

**Test Runner Features:**
- 🎯 Smart test discovery and categorization
- ⚡ Parallel execution with optimal sharding
- 📊 Coverage reporting (target: 97%)
- 🔄 Automatic retry for flaky tests
- 📈 Performance baselines
- 🎭 Mock/Real LLM switching

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │    Auth     │  │   Chat UI    │  │  WebSocket      │    │
│  │   Context   │  │  Components  │  │   Provider      │    │
│  └─────────────┘  └──────────────┘  └─────────────────┘    │
└────────────────────────────┬────────────────────────────────┘
                             │ WebSocket + REST API
┌────────────────────────────┴────────────────────────────────┐
│                      Backend (FastAPI)                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               Multi-Agent System                     │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐      │    │
│  │  │Supervisor│──▶│  Triage  │──▶│Data Analysis│      │    │
│  │  │  Agent   │  │  Agent   │  │    Agent     │      │    │
│  │  └──────────┘  └──────────┘  └──────────────┘      │    │
│  │       │                                              │    │
│  │       ▼                                              │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐      │    │
│  │  │Optimize  │──▶│ Actions  │──▶│  Reporting   │      │    │
│  │  │  Agent   │  │  Agent   │  │    Agent     │      │    │
│  │  └──────────┘  └──────────┘  └──────────────┘      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Services   │  │    Routes    │  │   Schemas    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │              Databases                   │
        │  ┌──────────────┐  ┌──────────────┐    │
        │  │  PostgreSQL  │  │  ClickHouse  │    │
        │  └──────────────┘  └──────────────┘    │
        └──────────────────────────────────────────┘
```

### Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic, Alembic
- **Frontend**: Next.js 14, React 18, TypeScript, Zustand, TailwindCSS
- **Databases**: PostgreSQL (primary), ClickHouse (analytics)
- **Communication**: WebSockets, REST API
- **Authentication**: OAuth 2.0, JWT
- **Testing**: Pytest, Jest, Cypress
- **Infrastructure**: Docker, Kubernetes-ready

## 🔤 String Literals Index

**Prevents LLM hallucination with 35,000+ indexed platform constants**

```bash
# Validate before use
python scripts/query_string_literals.py validate "your_string"

# Update index after changes
python scripts/scan_string_literals.py
```

**Categories:** configuration, paths, identifiers, database, events, metrics, environment, states
**Reference:** [SPEC/string_literals_index.xml](SPEC/string_literals_index.xml)


## 🏗 Architecture

```
├── app/                    # Backend (FastAPI)
│   ├── agents/            # Multi-agent system
│   ├── routes/            # API endpoints  
│   ├── services/          # Business logic
│   └── db/                # Database models
├── frontend/              # Frontend (Next.js 14)
│   ├── app/              # App router
│   └── components/       # React components
├── SPEC/                  # XML specifications
│   └── learnings/        # System learnings
├── scripts/              # Utility scripts
└── tests/                # Test suites
```


## 📚 API Documentation

### Core Endpoints

**Authentication:** `/api/auth/login`, `/api/auth/google/authorize`  
**WebSocket:** `ws://localhost:8000/ws?token={jwt_token}`  
**Threads:** `/api/threads` (CRUD operations)  
**Metrics:** `/api/metrics/savings/{user_id}`, `/api/metrics/roi`  
**Health:** `/health/ready`, `/health/dependencies`

### WebSocket Message Types
```typescript
type MessageType = 'agent_started' | 'sub_agent_update' | 'agent_completed' | 
                   'tool_call' | 'tool_result' | 'error' | 'heartbeat';
```

## 🧪 Testing

```bash
# Default (before commits)
python -m test_framework.test_runner --level integration --no-coverage --fast-fail

# Agent changes
python -m test_framework.test_runner --level agents --real-llm

# Before releases (includes staging)
python -m test_framework.test_runner --level integration --real-llm --env staging
```

**Target:** 97% coverage
**Guide:** [SPEC/test_runner_guide.xml](SPEC/test_runner_guide.xml)

## 🚀 Deployment

### GCP Staging
```bash
python organized_root/deployment_configs/deploy_staging.py

# Auth issues
python organized_root/deployment_configs/setup_staging_auth.py --force-new-key
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

**Guides:**
- [SPEC/learnings/deployment_staging.xml](SPEC/learnings/deployment_staging.xml)
- [docs/deployment/PRODUCTION_DEPLOYMENT.md](docs/deployment/PRODUCTION_DEPLOYMENT.md)


## 📊 Performance Monitoring

### SLOs
| Metric | Target |
|--------|--------|
| API Latency (p99) | < 2000ms |
| WebSocket Connection | < 500ms |
| Agent Response | < 30s |
| Availability | 99.9% |

**Stack:** Prometheus, Grafana, OpenTelemetry
**Guide:** [docs/operations/MONITORING_GUIDE.md](docs/operations/MONITORING_GUIDE.md)



## 🔗 Key Resources

### Development
- [CLAUDE.md](CLAUDE.md) - Engineering principles
- [LLM_MASTER_INDEX.md](LLM_MASTER_INDEX.md) - Navigation index
- [MASTER_WIP_STATUS.md](MASTER_WIP_STATUS.md) - System health
- [SPEC/learnings/index.xml](SPEC/learnings/index.xml) - All learnings

### Specifications
- [SPEC/type_safety.xml](SPEC/type_safety.xml) - Type safety rules
- [SPEC/conventions.xml](SPEC/conventions.xml) - Code standards
- [SPEC/string_literals_index.xml](SPEC/string_literals_index.xml) - Platform constants
- [SPEC/test_runner_guide.xml](SPEC/test_runner_guide.xml) - Testing guide

### Documentation
- [docs/deployment/PRODUCTION_DEPLOYMENT.md](docs/deployment/PRODUCTION_DEPLOYMENT.md) - Production guide
- [docs/operations/MONITORING_GUIDE.md](docs/operations/MONITORING_GUIDE.md) - Monitoring
- [GitHub Issues](https://github.com/netrasystems/netra-core/issues)

---

© 2024 Netra Systems - Proprietary Software