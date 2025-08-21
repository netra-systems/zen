# Netra Apex - AI Optimization Platform

**Enterprise AI spend optimization platform delivering measurable ROI through intelligent workload analysis.**

## 💰 Business Value

Netra Apex captures value proportional to customer AI spend:
- **10-40% reduction** in AI infrastructure costs
- **Performance-based pricing** (20% of demonstrated savings)
- **< 7 days** from signup to first savings

| Segment | Monthly AI Spend | Value Proposition |
|---------|-----------------|-------------------|
| **Free** | < $1K | Core features, conversion focus |
| **Early** | $1K - $10K | 15-20% cost reduction |
| **Mid** | $10K - $100K | 20-30% reduction + analytics |
| **Enterprise** | > $100K | 30-40% reduction + custom SLA |


## 🚀 Developer Guidelines

📖 **[CLAUDE.md](CLAUDE.md)** - Complete development philosophy
📊 **[MASTER_WIP_STATUS.md](MASTER_WIP_STATUS.md)** - System health dashboard
📚 **[LLM_MASTER_INDEX.md](LLM_MASTER_INDEX.md)** - Navigation index

**Core Principles:**
- Business Value Justification (BVJ) for all features
- 500-line modules, 25-line functions
- Test-Driven Correction (TDC) for bug fixes
- Multi-agent collaboration for complex tasks

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
- PostgreSQL 14+ (optional)
- Redis 7+ (optional)

### Installation & Start

```bash
# Clone and install
git clone https://github.com/netra-systems/netra-apex.git
cd netra-core-generation-1

# Windows
scripts\setup.bat
start_dev.bat

# macOS/Linux
./scripts/setup.sh
./start_dev.sh
```

**Launches:**
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

### Development Database Setup

```bash
# Quick setup with Terraform
cd terraform-dev-postgres
powershell -ExecutionPolicy Bypass -File quick-start.ps1  # Windows
./quick-start.sh  # macOS/Linux

# Creates: PostgreSQL, Redis, ClickHouse
# Auto-generates: .env.development.local
```

### Development Commands

```bash
# Recommended start (optimal configuration)
python scripts/dev_launcher.py --dynamic --no-backend-reload --load-secrets

# Test runner (before commits)
python -m test_framework.test_runner --level integration --no-coverage --fast-fail

# Agent changes
python -m test_framework.test_runner --level agents --real-llm
```

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