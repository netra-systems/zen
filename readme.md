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
├── app/                      # Backend application
│   ├── agents/              # Multi-agent system (consolidated modules)
│   │   ├── supervisor_consolidated.py  # Enhanced supervisor with hooks
│   │   ├── triage_sub_agent.py
│   │   ├── optimizations_core_sub_agent.py
│   │   ├── actions_to_meet_goals_sub_agent.py
│   │   ├── reporting_sub_agent.py
│   │   ├── corpus_admin_sub_agent.py
│   │   ├── supply_researcher_sub_agent.py
│   │   ├── synthetic_data_sub_agent.py
│   │   └── tool_dispatcher.py
│   ├── routes/              # API endpoints
│   │   ├── auth/           # OAuth and JWT authentication
│   │   ├── websockets.py   # WebSocket with heartbeat
│   │   ├── agent_route.py  # Agent execution
│   │   ├── threads_route.py # Thread management
│   │   └── health.py       # Health checks
│   ├── services/            # Business logic
│   │   ├── agent_service.py
│   │   ├── apex_optimizer_agent/  # 30+ optimization tools
│   │   │   ├── tools/      # Individual tool implementations
│   │   │   └── tool_builder.py
│   │   ├── database/       # Repository pattern
│   │   ├── websocket/      # Message handling
│   │   └── state/          # State persistence
│   ├── schemas/            # Pydantic models
│   ├── db/                 # Database models
│   │   ├── models_postgres.py
│   │   └── models_clickhouse.py
│   ├── core/               # Core utilities
│   │   ├── exceptions.py   # Error handling
│   │   └── error_context.py # Trace IDs
│   └── main.py             # App entry with auto-migration
├── frontend/               # Frontend application
│   ├── app/               # Next.js 14 app router
│   │   ├── chat/          # Main chat interface
│   │   ├── auth/          # OAuth pages
│   │   └── (other pages)
│   ├── components/        # React components
│   │   ├── chat/         # Chat UI components
│   │   │   ├── MessageItem.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   └── ThinkingIndicator.tsx
│   │   └── ui/           # shadcn/ui components
│   ├── providers/        # Context providers
│   │   └── WebSocketProvider.tsx
│   ├── hooks/            # Custom hooks
│   │   ├── useWebSocket.ts
│   │   └── useAgent.ts
│   ├── store/            # Zustand state stores
│   │   ├── chat.ts
│   │   └── authStore.ts
│   └── types/            # TypeScript definitions
├── tests/                 # Backend test suite
│   ├── agents/           # Agent tests
│   ├── routes/           # API tests
│   └── services/         # Service tests
├── app/tests/            # Comprehensive test suite
│   ├── auth_integration/ # Auth integration tests
│   ├── config/          # Test configuration
│   ├── critical/        # Critical path tests
│   ├── integration/     # Integration tests
│   └── unit/            # Unit tests
├── agent_to_agent/       # Agent communication reports
├── agent_to_agent_status_updates/ # Agent status reports
│   ├── STARTUP/         # Startup fix reports
│   └── TESTS/           # Test fix reports
├── docs/                  # Documentation
├── SPEC/                  # XML specifications
│   └── learnings/       # Modular learnings by category
│       ├── index.xml    # Master learnings index
│       ├── testing.xml  # Testing-related learnings
│       ├── startup.xml  # Startup insights
│       └── *.xml        # Category-specific learnings
├── scripts/              # Utility scripts
├── config/               # Configuration files
├── database_scripts/     # Database setup & migrations
├── deployment_docs/      # Deployment guides
├── test_scripts/         # Test runners & utilities
├── test_reports/         # Test results & coverage
└── marketing_materials/  # Marketing & investor docs
```


## 📚 API Documentation

### REST Endpoints

#### Authentication
- `POST /api/auth/login` - User login with email/password
- `POST /api/auth/logout` - User logout and session cleanup
- `GET /api/auth/me` - Get current authenticated user
- `GET /api/auth/google/authorize` - Initiate Google OAuth flow
- `GET /api/auth/google/callback` - Handle OAuth callback

#### Agent Operations
- `WebSocket /ws` - Real-time agent execution via WebSocket
- `GET /api/agent/status/{run_id}` - Get run status
- `GET /api/agent/history` - Get execution history

#### Thread Management
- `POST /api/threads` - Create new conversation thread
- `GET /api/threads` - List user's threads
- `DELETE /api/threads/{thread_id}` - Delete thread
- `PUT /api/threads/{thread_id}/switch` - Switch active thread

#### Supply Catalog
- `GET /api/supply/catalog` - Get available models/providers
- `POST /api/supply/estimate` - Estimate optimization costs

#### Content Generation
- `POST /api/generation/start` - Start content generation
- `GET /api/generation/status/{job_id}` - Check generation status

#### Business Metrics Integration
- `GET /api/metrics/savings/{user_id}` - Get user savings analytics
- `POST /api/metrics/track` - Track optimization events
- `GET /api/metrics/roi` - Calculate return on investment
- `GET /api/metrics/tier/{tier}/limits` - Get tier-specific limits

#### Tier-Specific Endpoints

##### Free Tier
- `GET /api/free/demo` - Demo optimization features
- `POST /api/free/sample-analysis` - Limited sample analysis
- `GET /api/free/conversion-triggers` - Conversion opportunities

##### Early/Mid Tier
- `GET /api/tier/usage` - Current usage vs limits
- `POST /api/tier/optimize` - Full optimization suite
- `GET /api/tier/savings-report` - Detailed savings report

##### Enterprise Tier
- `GET /api/enterprise/custom-integrations` - Custom integration options
- `POST /api/enterprise/bulk-optimization` - Bulk workload optimization
- `GET /api/enterprise/sla-compliance` - SLA compliance metrics
- `GET /api/enterprise/dedicated-support` - Support channel access

#### Health & Monitoring
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness with dependency checks
- `GET /health/dependencies` - Detailed dependency status

### WebSocket Events

```typescript
// Connection with JWT authentication
ws://localhost:8000/ws?token={jwt_token}

// Message Types
interface WebSocketMessage {
  type: 'agent_started' | 'sub_agent_update' | 'agent_completed' | 
        'tool_call' | 'tool_result' | 'agent_log' | 'error' | 
        'connection_established' | 'heartbeat';
  data: any;
  metadata?: {
    thread_id?: string;
    run_id?: string;
    agent_name?: string;
    timestamp: string;
  };
}

// Example: Start agent execution
{
  "action": "start_agent",
  "data": {
    "message": "Optimize my AI workload costs",
    "thread_id": "thread-123"
  }
}

// Example: Receive sub-agent status
{
  "type": "sub_agent_update",
  "data": {
    "agent_name": "TriageSubAgent",
    "status": "thinking",
    "message": "Analyzing request and determining optimization approach..."
  },
  "metadata": {
    "thread_id": "thread-123",
    "run_id": "run-456",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}

// Example: Tool execution
{
  "type": "tool_call",
  "data": {
    "tool_name": "cost_analyzer",
    "parameters": {...}
  }
}
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