# Netra Apex - AI Optimization Platform

**Enterprise AI spend optimization platform delivering measurable ROI through intelligent workload analysis and cost reduction.**

## 💰 Business Value Proposition

Netra Apex captures value proportional to customer AI spend by delivering:
- **10-40% reduction** in AI infrastructure costs
- **Real-time optimization** of model selection and routing
- **Performance-based pricing** aligned with customer savings
- **Enterprise-grade** security and compliance

### 🎯 Customer Segments & Value Creation

| Segment | Monthly AI Spend | Value Proposition | Pricing Model |
|---------|-----------------|-------------------|---------------|
| **Free** | < $1K | Try core features, see potential savings | Free (conversion focus) |
| **Early** | $1K - $10K | 15-20% cost reduction | 20% of savings |
| **Mid** | $10K - $100K | 20-30% cost reduction + advanced analytics | 20% of savings + platform fee |
| **Enterprise** | > $100K | 30-40% reduction + custom integrations | Negotiated % + SLA |

### Key Features

- **Multi-Agent Intelligence**: Seven specialized sub-agents for comprehensive optimization
- **Intelligent Model Routing**: Automatic selection of optimal LLM for each task
- **Cost Analytics Dashboard**: Real-time spend tracking and optimization metrics
- **Usage Pattern Analysis**: ML-driven insights into AI workload patterns
- **Performance Monitoring**: Latency, throughput, and quality metrics
- **Enterprise Integration**: API-first design for seamless integration
- **Compliance & Security**: SOC2, GDPR ready with audit trails
- **ROI Calculator**: Transparent savings tracking and reporting

## 📋 Table of Contents

- [Business Value & Monetization](#-business-value--monetization)
- [Developer Guidelines](#-developer-guidelines) **← Revenue-Driven Development**
- [Quick Start](#-quick-start)
- [Architecture](#-architecture) **← Module-Based (300 lines max)**
- [Installation](#-installation)
- [Development](#-development)
- [API Documentation](#-api-documentation)
- [Testing](#-testing) **← 97% Coverage Target**
- [Deployment](#-deployment)
- [Contributing](#-contributing)

## 💰 Business Value & Monetization

### Revenue Model
- **Performance-Based Pricing**: 20% of demonstrated AI cost savings
- **Platform Fees**: Monthly SaaS fees for Mid/Enterprise tiers
- **Professional Services**: Custom integrations and optimization consulting

### Value Metrics
- **Savings Delta**: Measurable reduction in AI spend
- **Optimization Rate**: Percentage of workloads optimized
- **Time to Value**: < 7 days from signup to first savings

## 🚀 Developer Guidelines

### 🔴 CRITICAL: Revenue-Driven Development

**Every line of code must justify its business value:**

1. **Business Value Justification (BVJ)** required for all features
2. **Customer Segment** targeting (Free → Paid conversion focus)  
3. **Revenue Impact** estimation before implementation
4. **300-line modules, 8-line functions** for maintainability

📖 **[Read CLAUDE.md →](CLAUDE.md)** for complete development philosophy

## 🏃 Quick Start

### Prerequisites

- Python 3.9+ (3.11+ recommended)
- Node.js 18+
- Git
- PostgreSQL 14+ (optional - will use SQLite if not available)
- Redis 7+ (optional - for caching)
- ClickHouse (optional - for analytics)

### 🎯 One-Command Installation (Recommended for New Developers)

#### Windows
```bash
# Clone the repository
git clone https://github.com/netra-systems/netra-apex.git
cd netra-core-generation-1

# Run the automated installer
scripts\setup.bat
```

#### macOS/Linux
```bash
# Clone the repository
git clone https://github.com/netra-systems/netra-apex.git
cd netra-core-generation-1

# Run the automated installer
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The installer will automatically:
✅ Check all prerequisites
✅ Create Python virtual environment
✅ Install all Python packages
✅ Install all frontend dependencies
✅ Set up databases (PostgreSQL/SQLite)
✅ Configure environment variables
✅ Create startup scripts
✅ Run verification tests

### 🚀 Starting the Development Environment

After installation, start everything with one command:

#### Windows
```bash
start_dev.bat
```

#### macOS/Linux
```bash
./start_dev.sh
```

This will launch:
- Backend API at http://localhost:8000
- Frontend UI at http://localhost:3000

### 🐳 Terraform-Managed Development Database (Recommended)

For a consistent development environment, use our Terraform configuration to automatically set up PostgreSQL, Redis, and ClickHouse:

#### Quick Setup
```bash
# Navigate to terraform directory
cd terraform-dev-postgres

# Run quick start script
# Windows:
powershell -ExecutionPolicy Bypass -File quick-start.ps1

# macOS/Linux:
chmod +x quick-start.sh
./quick-start.sh
```

This creates:
- ✅ PostgreSQL 14 on port 5432 (with test database)
- ✅ Redis 7 on port 6379
- ✅ ClickHouse on ports 8123/9000
- ✅ Auto-generated `.env.development.local` with secure passwords
- ✅ Persistent data volumes

The dev_launcher automatically uses `.env.development.local` if it exists.

#### Database Management
```bash
cd terraform-dev-postgres

# Status check
./manage.ps1 status     # Windows
./manage.sh status      # macOS/Linux

# Connect to databases
./manage.ps1 connect    # Interactive connection menu

# Stop databases
./manage.ps1 stop

# View logs
./manage.ps1 logs
```

See [terraform-dev-postgres/README.md](terraform-dev-postgres/README.md) for detailed documentation.

### Alternative: Manual Setup

If you prefer manual control or the installer encounters issues:

```bash
# 1. Set up Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 3. Configure environment
cp config/.env.example .env  # Edit with your settings

# 4. Set up databases
python database_scripts/create_db.py
python database_scripts/run_migrations.py

# 5. Start services (RECOMMENDED CONFIGURATION)
python scripts/dev_launcher.py --dynamic --no-backend-reload --load-secrets
```

### 🔧 Local Development Mode (Without External Services)

You can run Netra in local development mode without external services (ClickHouse, Redis, LLM providers):

1. **Configure environment variables** in `.env`:
```bash
# Disable external services
DEV_MODE_DISABLE_REDIS=true
DEV_MODE_DISABLE_CLICKHOUSE=true
DEV_MODE_DISABLE_LLM=true

# Use local PostgreSQL
DATABASE_URL=postgresql+asyncpg://yourusername@localhost/netra

# Add encryption key
FERNET_KEY=<generate-with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
```

2. **Set up local PostgreSQL**:
```bash
# Create database (uses current system user, no postgres superuser needed)
python database_scripts/create_db.py

# Run migrations (automatically uses current user)
python database_scripts/run_migrations.py
```

3. **Start services**:
```bash
# Frontend
cd frontend && npm run dev

# Backend (in separate terminal)
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 🔧 Troubleshooting

If the installer fails:
1. Ensure Python 3.9+ is installed and in PATH
2. Ensure Node.js 18+ is installed
3. On Windows, you may need to run as Administrator
4. Check `scripts/install_dev_env.py` output for specific errors

For database issues:
- PostgreSQL: The installer will use SQLite if PostgreSQL is unavailable
- Redis: Optional for development (caching will be disabled)
- ClickHouse: Optional for development (analytics will be limited)

For local development mode:
- Services can be disabled via `DEV_MODE_DISABLE_*` environment variables
- LLM features will be unavailable when `DEV_MODE_DISABLE_LLM=true`
- Caching will be disabled when `DEV_MODE_DISABLE_REDIS=true`
- Analytics will be limited when `DEV_MODE_DISABLE_CLICKHOUSE=true`

## 🏗 Architecture

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

## 💾 Installation

### Automated Installation

The project includes a comprehensive installer (`scripts/install_dev_env.py`) that handles all setup automatically:

**Features:**
- 🔍 Detects operating system (Windows/macOS/Linux)
- ✅ Checks and validates prerequisites
- 📦 Installs all dependencies
- 🗄️ Sets up databases (with fallbacks)
- 🔧 Configures environment variables
- 🚀 Creates startup scripts
- 🧪 Runs verification tests

**What it installs:**
- Python virtual environment with all packages
- Frontend Node.js dependencies
- PostgreSQL (or falls back to SQLite)
- Redis (optional, for caching)
- ClickHouse (optional, for analytics)

Run the installer directly:
```bash
python scripts/install_dev_env.py
```

### Environment Configuration

The installer creates a `.env` file automatically. You can also create it manually:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/netra_db
CLICKHOUSE_URL=clickhouse://localhost:9000/netra_analytics
REDIS_URL=redis://localhost:6379

# Authentication
SECRET_KEY=your-secret-key-here
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
FRONTEND_URL=http://localhost:3000

# API Keys
GEMINI_API_KEY=your-gemini-key  # Primary LLM provider
OPENAI_API_KEY=your-openai-key  # Optional
ANTHROPIC_API_KEY=your-anthropic-key  # Optional

# Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Database Pool
MAX_CONNECTIONS=10
POOL_SIZE=5

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Database Setup

#### PostgreSQL

```sql
-- Create database
CREATE DATABASE netra_db;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE netra_db TO your_user;
```

Run migrations:
```bash
python database_scripts/run_migrations.py
```

#### ClickHouse (Optional)

```sql
-- Create database
CREATE DATABASE netra_analytics;

-- Create workload_events table
CREATE TABLE netra_analytics.workload_events (
    timestamp DateTime,
    user_id UInt32,
    event_type String,
    event_data String,
    INDEX idx_user_id user_id TYPE minmax GRANULARITY 8192
) ENGINE = MergeTree()
ORDER BY timestamp;
```

## 🔧 Development

### Project Structure

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

### Development Commands

#### Unified Development Environment (Recommended)

##### 🎯 First-Time Developer? Use This:
```bash
# BEST CONFIGURATION FOR NEW DEVELOPERS
# Single command that handles everything optimally
python scripts/dev_launcher.py --dynamic --no-backend-reload --load-secrets

# What this does:
# ✅ Finds free ports automatically (no conflicts)
# ✅ Runs 30-50% faster without backend hot reload
# ✅ Loads secrets from Google Cloud (if configured)
# ✅ Starts both frontend and backend together
# ✅ Shows clear status and error messages
```

##### Other Useful Configurations:
```bash
# Development with hot reload (slower but auto-refreshes)
python scripts/dev_launcher.py --dynamic

# Maximum performance (no hot reload at all)
python scripts/dev_launcher.py --dynamic --no-reload

# Custom ports
python scripts/dev_launcher.py --backend-port 8080 --frontend-port 3001

# Check service status
python scripts/service_discovery.py status
```

#### Traditional Development Commands
```bash
# Backend development with auto-reload
uvicorn app.main:app --reload --port 8000
# Or with dynamic port
python scripts/run_server.py --dynamic-port

# Frontend development with hot-reload
cd frontend && npm run dev
# Or with backend discovery
cd frontend && node scripts/start_with_discovery.js

# Run linters
npm run lint           # Frontend
ruff check app/        # Backend

# Format code
npm run format         # Frontend
black app/             # Backend

# Type checking
npm run typecheck      # Frontend
mypy app/              # Backend
```

### Code Style Guidelines

- **Python**: Follow PEP 8, use type hints, async/await for I/O
- **TypeScript**: Use strict mode, define interfaces for all data structures
- **React**: Functional components with hooks, proper component composition
- **Testing**: Target 97% coverage, comprehensive test suite with 5 levels

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

### Unified Test Runner (RECOMMENDED)

```bash
# Quick smoke tests (< 30 seconds) - Use before commits
python test_runner.py --level smoke --fast-fail

# Unit tests (1-2 minutes) - Development validation
python test_runner.py --level unit --no-coverage --fast-fail

# Integration tests (3-5 minutes) - Feature validation (DEFAULT for features)
python test_runner.py --level integration --no-coverage --fast-fail

# Comprehensive tests with coverage (30-45 minutes)
python test_runner.py --level comprehensive

# Critical path tests only (1-2 minutes)
python test_runner.py --level critical

# Simple fallback runner if main runner has issues
python test_runner.py --simple
```

### Traditional Backend Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run tests matching pattern
pytest -k "test_login"

# Run with verbose output
pytest -v
```

### Frontend Testing

```bash
# Unit tests with Jest
npm test

# Watch mode
npm test -- --watch

# Coverage report
npm test -- --coverage

# E2E tests with Cypress
npm run cypress:open    # Interactive
npm run cypress:run     # Headless
```

### Test Structure

```
tests/
├── unit/              # Unit tests
├── integration/       # Integration tests
├── e2e/              # End-to-end tests
└── fixtures/         # Test data
```

## 🚀 Deployment

### Docker Deployment

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Configuration

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  backend:
    image: netra/backend:latest
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
    
  frontend:
    image: netra/frontend:latest
    environment:
      - NEXT_PUBLIC_API_URL=https://api.netrasystems.ai
      - NEXT_PUBLIC_WS_URL=wss://api.netrasystems.ai/ws
    ports:
      - "3000:3000"
    
  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=netra_db
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
  clickhouse:
    image: clickhouse/clickhouse-server
    volumes:
      - clickhouse_data:/var/lib/clickhouse
    
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  clickhouse_data:
  redis_data:
```

### Environment Variables

Production environment variables:

```env
# Production URLs
API_URL=https://api.netrasystems.ai
FRONTEND_URL=https://app.netrasystems.ai

# Security
JWT_SECRET_KEY=<strong-secret-key>
ALLOWED_ORIGINS=https://app.netrasystems.ai

# Database
DATABASE_URL=postgresql://user:pass@db:5432/netra_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
```

## 🤝 Contributing

### Development Workflow

1. Clone repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest && npm test`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Commit Guidelines

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code restructuring
- `test:` Tests
- `chore:` Maintenance

### Code Review Process

1. All PRs require at least one review
2. CI/CD must pass (tests, linting, type checking)
3. Documentation must be updated
4. Breaking changes require migration guide

## 📄 License

This project is proprietary software owned by Netra Systems.

## 🔗 Links

- **[Developer Welcome Guide](DEVELOPER_WELCOME_GUIDE.md)** - Essential reading for AI-native development
- [Documentation](docs/)
- [Deployment Guides](deployment_docs/)
- [API Reference](docs/API_REFERENCE.md)
- [Testing Guide](docs/TESTING_GUIDE.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [WebSocket Implementation](docs/WEBSOCKET_IMPLEMENTATION.md)
- [Issue Tracker](https://github.com/netrasystems/netra-core/issues)


---

Built with ❤️ by the Netra Systems team