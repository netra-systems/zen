# Netra AI Optimization Platform apex-v1

**The world's best, highest quality, most intelligent system for optimizing AI workloads including AI tools and Agents.**

## 🚀 Overview

Netra is a sophisticated AI optimization platform that leverages a multi-agent system to intelligently analyze and optimize AI workloads. Built with a modern tech stack combining FastAPI, Next.js, and dual-database architecture, it provides real-time optimization recommendations through an intuitive chat-based interface.

### Key Features

- **Multi-Agent Intelligence**: Seven specialized sub-agents orchestrated by advanced supervisor
- **Real-Time Communication**: WebSocket manager with heartbeat, retry logic, and connection pooling
- **Dual Database System**: PostgreSQL for transactional data, ClickHouse for time-series analytics
- **Enterprise Security**: Google OAuth 2.0 integration with JWT tokens and secure session management
- **Modern UI/UX**: Next.js 14 chat interface with real-time agent status and thinking indicators
- **Apex Optimizer Agent**: 30+ specialized optimization tools for cost, latency, and performance analysis
- **State Persistence**: Database-backed conversation continuity and recovery
- **Scalable Architecture**: Async-first design with repository pattern and dependency injection

## 📋 Table of Contents

- [Developer Welcome Guide](#-developer-welcome-guide) **← Start Here for AI-Native Development**
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Development](#-development)
- [API Documentation](#-api-documentation)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)

## 🚀 Developer Welcome Guide

**New to Netra?** Start with our comprehensive [Developer Welcome Guide](DEVELOPER_WELCOME_GUIDE.md) to understand:
- **AI-Native Development Philosophy**: How we use AI agents as first-class citizens in development
- **Specification-Driven Development**: Why specifications, not code, are our source of truth
- **Ultra-Thinking Capabilities**: Deep AI analysis for intelligent code generation
- **Autonomous Improvement Cycles**: How the system self-optimizes with 97% test coverage targets

📖 **[Read the Developer Welcome Guide →](DEVELOPER_WELCOME_GUIDE.md)**

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
python dev_launcher.py --dynamic --no-backend-reload --load-secrets
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
│   ├── agents/              # Multi-agent system
│   │   ├── supervisor.py    # Legacy supervisor
│   │   ├── supervisor_consolidated.py  # Enhanced supervisor with hooks
│   │   ├── orchestration/   # Orchestration components
│   │   ├── triage_sub_agent.py
│   │   ├── data_sub_agent.py
│   │   ├── optimizations_core_sub_agent.py
│   │   ├── actions_to_meet_goals_sub_agent.py
│   │   ├── reporting_sub_agent.py
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
├── docs/                  # Documentation
├── SPEC/                  # XML specifications
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
python test_runner.py --level smoke

# Unit tests (1-2 minutes) - Development validation
python test_runner.py --level unit

# Integration tests (3-5 minutes) - Feature validation
python test_runner.py --level integration

# Comprehensive tests with coverage (10-15 minutes)
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