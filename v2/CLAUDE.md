# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Netra AI Optimization Platform - The world's best, highest quality, most intelligent system for optimizing AI workloads including AI tools and Agents. Used by top startups, F100, OpenAI, and Anthropic.

## Essential Commands

### Quick Test Commands (Most Commonly Used)
```bash
# RECOMMENDED: Run quick tests before any commit
python test_runner.py --mode quick

# Run specific category of tests
python scripts/test_backend.py --category unit    # Backend unit tests
python scripts/test_frontend.py --category components  # Frontend component tests

# Run with coverage
python test_runner.py --mode comprehensive

# Run failed tests first (after fixing issues)
python scripts/test_backend.py --failed-first
```

### Specifications
XML specifications are in `SPEC/*.xml`

### Backend Development (Windows)

```bash
# Setup virtual environment
python -m venv venv
venv\Scripts\activate  # Windows activation

# Install dependencies
pip install -r requirements.txt

# Database setup
python create_db.py
python run_migrations.py

# Run backend server
python run_server.py
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev      # Development server
npm run build    # Production build
npm run test     # Run tests
npm run lint     # Run linter
```

### Testing

#### Quick Start - Unified Test Runner
```bash
# Run quick smoke tests (< 1 minute)
python test_runner.py --mode quick

# Run standard test suite (~ 5 minutes)
python test_runner.py --mode standard

# Run comprehensive tests with coverage (~ 10 minutes)
python test_runner.py --mode comprehensive

# Full CI/CD pipeline (~ 15 minutes)
python test_runner.py --mode ci --parallel
```

#### Backend Testing
```bash
# Using the comprehensive backend test runner
python scripts/test_backend.py                  # Run all backend tests
python scripts/test_backend.py --category unit  # Run unit tests only
python scripts/test_backend.py --category agent # Run agent tests
python scripts/test_backend.py --coverage       # Run with coverage reporting
python scripts/test_backend.py --parallel auto  # Run tests in parallel
python scripts/test_backend.py --fail-fast      # Stop on first failure

# Test categories available:
# - smoke: Quick health checks
# - unit: Unit tests for services and utilities
# - integration: API endpoint tests
# - agent: Agent system tests
# - websocket: WebSocket connection tests
# - auth: Authentication tests
# - database: Database repository tests
# - critical: Critical path tests

# Direct pytest usage (fallback)
pytest                                # Run all tests
pytest app/tests/test_auth.py       # Run specific test file
pytest -k "test_login"               # Run tests matching pattern
pytest --cov=app --cov-report=html  # Generate coverage report
```

#### Frontend Testing
```bash
# Using the comprehensive frontend test runner
python scripts/test_frontend.py                    # Run all Jest tests
python scripts/test_frontend.py --category components  # Test components only
python scripts/test_frontend.py --coverage        # Run with coverage
python scripts/test_frontend.py --lint            # Run ESLint
python scripts/test_frontend.py --type-check      # TypeScript checking
python scripts/test_frontend.py --e2e             # Run Cypress E2E tests
python scripts/test_frontend.py --cypress-open    # Open Cypress GUI

# Test categories available:
# - smoke: Quick critical tests
# - unit: Unit tests
# - components: Component tests
# - hooks: React hooks tests
# - store: State management tests
# - websocket: WebSocket provider tests
# - auth: Authentication flow tests
# - e2e: End-to-end Cypress tests

# Direct npm usage (fallback)
cd frontend
npm test                  # Run Jest tests
npm run lint             # Run ESLint
npm run cypress:open     # Interactive Cypress
npm run cy:run          # Headless Cypress tests
```

#### Test Configurations

##### Coverage Requirements
- Backend minimum coverage: 70%
- Frontend minimum coverage: 60%
- Coverage reports: `reports/coverage/html/index.html`

##### Environment Setup
Tests automatically configure these environment variables:
- `TESTING=1`
- `DATABASE_URL=sqlite+aiosqlite:///:memory:`
- `REDIS_URL=redis://localhost:6379/1`
- `SECRET_KEY=test-secret-key-for-testing-only`

##### Test Reports
After running tests, find reports in:
- `reports/test_report.json` - JSON test results
- `reports/test_report.md` - Markdown summary
- `reports/coverage/` - Backend coverage reports
- `reports/frontend-coverage/` - Frontend coverage reports
- `reports/tests/` - Detailed test reports

#### Common Testing Tasks

```bash
# Quick validation before commit
python test_runner.py --mode quick

# Full test suite with coverage
python test_runner.py --mode comprehensive

# Test only authentication flows
python scripts/test_backend.py --category auth
python scripts/test_frontend.py --category auth

# Test agent system
python scripts/test_backend.py --category agent

# Run failed tests first
python scripts/test_backend.py --failed-first

# Debug specific test
pytest app/tests/test_main.py::test_specific_function -vv

# Update Jest snapshots
python scripts/test_frontend.py --update-snapshots

# Run tests in watch mode (development)
python scripts/test_frontend.py --watch
```

#### Test Troubleshooting & Common Issues

##### Backend Test Issues
1. **Missing Dependencies**: Ensure all required packages are installed
   ```bash
   pip install sqlalchemy aiosqlite asyncpg psycopg2-binary
   ```

2. **Database Test Failures**: Tests use in-memory SQLite by default
   - Check `TESTING=1` environment variable is set
   - Verify `conftest.py` fixtures are working

##### Frontend Test Issues
1. **WebSocket Hook Tests**: Always wrap `useWebSocket` tests with WebSocketProvider
   ```typescript
   const wrapper = ({ children }: { children: React.ReactNode }) => (
     <WebSocketProvider>{children}</WebSocketProvider>
   );
   const { result } = renderHook(() => useWebSocket(), { wrapper });
   ```

2. **Fetch Mock Issues**: Use `mockImplementationOnce` for async responses
   ```typescript
   // ❌ Wrong - may not work correctly
   (fetch as jest.Mock).mockResolvedValueOnce({ ok: true, json: async () => data });
   
   // ✅ Correct - reliable async handling
   (fetch as jest.Mock).mockImplementationOnce(async () => ({
     ok: true,
     json: async () => data,
   }));
   ```

3. **Date.now Mock Issues**: Already handled in `jest.setup.ts` - preserves original function
   ```typescript
   // Automatically restored after each test
   const originalDateNow = Date.now;
   beforeEach(() => { Date.now = originalDateNow; });
   afterEach(() => { Date.now = originalDateNow; });
   ```

4. **Hook API Mismatches**: Check actual hook implementation before testing
   ```typescript
   // Example: useError hook actual API
   const { error, setError, clearError, isError } = useError();
   // NOT: addError, validateApplicationState, processStateUpdate, etc.
   ```

5. **Test Timeouts**: Increase timeout for complex integration tests
   ```typescript
   it('should handle complex flow', async () => {
     // test code
   }, 10000); // 10 second timeout
   ```

##### Quick Test Fix Checklist
- [ ] All dependencies installed (backend: SQLAlchemy, frontend: npm packages)
- [ ] Mock implementations match actual API signatures
- [ ] React hooks wrapped with appropriate providers
- [ ] Async operations use proper mock implementations
- [ ] Test timeouts adequate for operations being tested
- [ ] Environment variables properly set (TESTING=1, etc.)

## Architecture Overview

### Core Components

1. **Backend (FastAPI)** - `app/`
   - **Entry Point**: `app/main.py` - Initializes FastAPI app, middleware, OAuth, and routes
   - **Routes**: `app/routes/` - API endpoints
     - `auth/` - Authentication endpoints (login, OAuth)
     - `websockets.py` - WebSocket connections
     - `agent_route.py` - Agent interactions
     - `threads_route.py` - Thread management
     - `generation.py` - Content generation
     - `llm_cache.py` - LLM cache management
     - `synthetic_data.py` - Synthetic data generation
     - `corpus.py` - Corpus management
     - `config.py` - Configuration endpoints
     - `supply.py` - Supply catalog
     - `references.py` - Reference management
     - `health.py` - Health checks
     - `admin.py` - Admin functions
   - **Services**: `app/services/` - Business logic layer
     - `agent_service.py` - Main agent service
     - `apex_optimizer_agent/` - Specialized optimization agent with 30+ tools
     - `database/` - Repository pattern implementations
     - `websocket/` - WebSocket message handling
     - `core/` - Core service containers
     - `cache/` - LLM caching services
     - `state/` - State management and persistence
   - **Agents**: `app/agents/` - Multi-agent system
     - `supervisor.py` - Main supervisor agent
     - `supervisor_consolidated.py` - Consolidated supervisor logic
     - `orchestration/` - Agent orchestration components
     - `base.py` - Base agent class
     - Sub-agents:
       - `triage_sub_agent.py` - Request triage
       - `data_sub_agent.py` - Data analysis
       - `optimizations_core_sub_agent.py` - Core optimizations
       - `reporting_sub_agent.py` - Report generation
       - `actions_to_meet_goals_sub_agent.py` - Goal-oriented actions
   - **Database**: Dual database system
     - PostgreSQL: User data, configurations, persistent state
     - ClickHouse: Time-series log data and analytics
   - **Supporting Systems**:
     - Redis: Caching and session management
     - Background Task Manager: Async task processing

2. **Frontend (Next.js)** - `frontend/`
   - **Pages**: `frontend/app/` - Next.js app router pages
     - `chat/` - Main chat interface
     - `auth/` - Authentication pages
     - `corpus/` - Corpus management UI
     - `synthetic-data-generation/` - Data generation UI
     - `demo/` - Demo features
     - `enterprise-demo/` - Enterprise demo
   - **Components**: `frontend/components/` - React components
     - `chat/` - Chat-specific components
     - `ui/` - Reusable UI components
     - `demo/` - Demo components
   - **State**: `frontend/store/` - Zustand state management
   - **Hooks**: `frontend/hooks/` - Custom React hooks
   - **Services**: `frontend/services/` - API client services
   - **WebSocket**: Real-time communication with backend

3. **Agent System Architecture**
   - **Supervisor**: Dual implementation with legacy and consolidated versions
     - Consolidated supervisor includes hooks, execution strategies, and retry logic
   - **Sub-agents**: Five specialized agents for triage, data, optimization, actions, and reporting
   - **Tool Dispatcher**: Dynamic routing with 30+ optimization tools
   - **Tool Registry**: Service-based dynamic tool registration
   - **State Management**: Database-backed persistence with recovery
   - **Apex Optimizer Agent**: Production-ready optimizer with:
     - Cost analysis and simulation tools
     - Latency bottleneck identification
     - KV cache optimization
     - Performance prediction
     - Policy simulation and optimization

### Key Design Patterns

1. **WebSocket Communication**: Advanced WebSocket manager with:
   - Connection pooling and per-user tracking
   - Heartbeat mechanism (30s intervals, 60s timeout)
   - Automatic retry with exponential backoff
   - Comprehensive statistics and monitoring
2. **Dependency Injection**: Services injected via FastAPI dependency system
3. **Async/Await**: Pervasive async patterns for scalability
4. **Type Safety**: Pydantic models with auto-generated TypeScript types
5. **Multi-Agent Orchestration**: Pipeline-based execution with hooks
6. **Repository Pattern**: Database access through repositories with unit of work
7. **Error Context**: Trace IDs with middleware-based tracking
8. **OAuth Integration**: Complete Google OAuth2 implementation

### Database Schema

- **PostgreSQL Tables**: 
  - `userbase` - User accounts and authentication (renamed from users)
  - `threads` - Conversation threads with user association
  - `messages` - Chat messages with role and metadata
  - `runs` - Agent execution runs with detailed tracking
  - `thread_runs` - Association between threads and runs
  - `agent_runs` - Individual agent execution records
  - `agent_reports` - Generated reports from agents
  - `references` - Document references with embedding support
  - `supply_catalog` - Model and provider catalog
  - `user_secrets` - Encrypted user API keys
  - `oauth_secrets` - OAuth provider configurations
- **ClickHouse Tables**: 
  - `workload_events` - Time-series log data with structured event tracking

### Authentication Flow

1. **Standard Login**:
   - Frontend sends login request to `/api/auth/login`
   - Backend validates credentials using bcrypt hashing
   - JWT token generated with user context
   - Frontend stores token in localStorage/cookies
   - Token included in Authorization header for API calls

2. **Google OAuth Flow**:
   - User clicks Google login button
   - Redirected to Google OAuth consent screen
   - Callback to `/api/auth/google/callback` with authorization code
   - Backend exchanges code for user info
   - Creates/updates user in database
   - JWT token issued and returned to frontend
   - Session management with secure cookies

3. **WebSocket Authentication**:
   - JWT token passed as query parameter on connection
   - Token validated and user context established
   - Connection tracked in WebSocket manager
   - Automatic cleanup on disconnection

### Agent Workflow

1. User message received via WebSocket with authentication
2. Message validated and queued in handler with rate limiting
3. Thread context loaded or created for conversation
4. Supervisor agent initialized with state recovery
5. Sequential execution of sub-agents:
   - TriageSubAgent analyzes request and determines approach
   - DataSubAgent collects relevant data and context
   - OptimizationsCoreSubAgent generates optimization recommendations
   - ActionsToMeetGoalsSubAgent creates action plans
   - ReportingSubAgent compiles final report
6. Each agent streams updates via WebSocket events
7. State persisted to database after each agent
8. Final report sent with markdown formatting
9. Thread and run records updated in database

### Error Handling

- **NetraException**: Custom exception class for application errors
- **Error Context**: Trace IDs for request tracking
- **Middleware**: Error context middleware for request tracing
- **Handlers**: Specific handlers for different exception types

## Development Guidelines

1. **Async First**: Use async/await for all I/O operations
2. **Type Annotations**: Always include type hints for function parameters and returns
3. **Pydantic Models**: Define schemas for all API requests/responses
4. **Error Handling**: Use NetraException and proper error context
5. **Logging**: Use central_logger for consistent logging across the application
6. **Testing**: Write tests for new functionality, maintain existing test coverage
7. **Repository Pattern**: Use repositories for database access
8. **State Management**: Use state persistence service for agent state

## Common Tasks

### Adding a New API Endpoint
1. Create route handler in `app/routes/`
2. Define Pydantic schemas in `app/schemas/`
3. Implement business logic in `app/services/`
4. Add repository if database access needed in `app/services/database/`
5. Add tests in `tests/routes/`

### Creating a New Sub-Agent
1. Create agent class in `app/agents/` extending BaseAgent
2. Define agent prompts in `app/agents/prompts.py`
3. Register agent with supervisor in `app/agents/supervisor.py`
4. Add agent-specific tools if needed
5. Update tool dispatcher if new tools added

### Database Migrations
```bash
# Create new migration
alembic revision -m "Description of change"

# Apply migrations
python run_migrations.py
# or automatically on startup
python run_server.py  # Migrations run automatically
```

### WebSocket Event Handling
1. Define event type in `app/schemas/WebSocket.py`
2. Add handler in `app/services/websocket/message_handler.py`
3. Update `app/routes/websockets.py` if needed
4. Update frontend WebSocket provider to handle new event type

### Working with Apex Optimizer Agent
1. Tools located in `app/services/apex_optimizer_agent/tools/`
2. Each tool extends base class in `tools/base.py`
3. Tool builder in `tool_builder.py` manages tool lifecycle
4. Register new tools in tool dispatcher

## Important Files to Know

### Core Configuration
- `app/config.py` - Application configuration and settings
- `app/config.yaml` - YAML configuration file
- `alembic.ini` - Database migration configuration

### Agent System
- `app/agents/supervisor.py` - Main agent orchestration logic
- `app/agents/orchestration/` - Orchestration components
- `app/services/agent_service.py` - Agent service layer
- `app/agents/tool_dispatcher.py` - Tool routing logic
- `app/services/tool_registry.py` - Dynamic tool registration

### WebSocket & Real-time
- `app/routes/websockets.py` - WebSocket connection handling
- `app/ws_manager.py` - WebSocket connection manager
- `app/services/websocket/message_handler.py` - Message processing
- `frontend/providers/WebSocketProvider.tsx` - Frontend WebSocket management
- `frontend/hooks/useWebSocket.ts` - WebSocket React hook

### Database & State
- `app/db/postgres.py` - PostgreSQL configuration
- `app/db/clickhouse.py` - ClickHouse configuration
- `app/services/database/` - Repository implementations
- `app/services/state/` - State management services
- `app/redis_manager.py` - Redis connection manager

### Authentication & Security
- `app/auth/auth.py` - Authentication logic
- `app/auth/auth_dependencies.py` - Auth dependencies
- `app/services/security_service.py` - Security services
- `app/services/key_manager.py` - API key management

### Error Handling & Logging
- `app/core/exceptions.py` - Custom exceptions
- `app/core/error_handlers.py` - Error handlers
- `app/core/error_context.py` - Error context management
- `app/logging_config.py` - Centralized logging configuration

### Frontend Core
- `frontend/hooks/useAgent.ts` - React hook for agent interactions
- `frontend/store/` - Zustand stores
- `frontend/services/` - API client services
- `frontend/types/` - TypeScript type definitions

## Environment Variables

Key environment variables to configure:
- `DATABASE_URL` - PostgreSQL connection string
- `CLICKHOUSE_URL` - ClickHouse connection string  
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Application secret key for JWT signing
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude models
- `OPENAI_API_KEY` - OpenAI API key (optional)
- `ENVIRONMENT` - Environment (development/staging/production)
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `FRONTEND_URL` - Frontend URL for OAuth redirects
- `LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)
- `MAX_CONNECTIONS` - Database connection pool size
- `CORS_ORIGINS` - Allowed CORS origins (comma-separated)

## Testing Strategy

### Backend Testing (`app/tests/`)
- **Agent Tests**: End-to-end agent workflows, supervisor orchestration
- **Route Tests**: API endpoint validation, authentication flows
- **Service Tests**: Business logic, agent service, generation service
- **Core Tests**: Configuration, error handling, service interfaces
- **WebSocket Tests**: Connection lifecycle, message handling, error recovery
- **Database Tests**: Repository pattern, unit of work, migrations
- **Performance Tests**: Load testing, optimization validation

### Frontend Testing (`frontend/__tests__/`)
- **Component Tests**: React components with React Testing Library
- **Critical Path Tests**: Authentication, chat, WebSocket resilience
- **Hook Tests**: Custom React hooks (useWebSocket, useAgent, etc.)
- **Store Tests**: Zustand state management and updates
- **Integration Tests**: API client services, WebSocket provider
- **E2E Tests**: Cypress tests for complete user flows
- **Accessibility Tests**: WCAG compliance validation

## Deployment

### Docker
- `Dockerfile` - Multi-stage build for production
- `Dockerfile.backend` - Backend-only container for microservices
- Environment-specific configurations
- Health check endpoints configured

### Terraform (GCP)
- `terraform-gcp/main.tf` - Infrastructure as code
- `terraform-gcp/variables.tf` - Configuration variables
- `terraform-gcp/deploy.sh` - Deployment automation script
- Includes Cloud Run, Cloud SQL, Redis setup

### Production Deployment
- See `GCP_DEPLOYMENT_README.md` for GCP deployment
- Database migrations run automatically on startup
- WebSocket connections via Cloud Run WebSockets
- Monitoring via Cloud Logging and Cloud Monitoring
- Secrets managed via Secret Manager