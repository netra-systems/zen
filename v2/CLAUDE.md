# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Netra AI Optimization Platform - The world's best, highest quality, most intelligent system for optimizing AI workloads including AI tools and Agents. Used by top startups, F100, OpenAI, and Anthropic.

## Essential Commands

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
```bash
# Backend tests
pytest                    # Run all tests
pytest tests/test_auth.py # Run specific test file
pytest -k "test_login"    # Run tests matching pattern

# Frontend
cd frontend
npm test                  # Jest tests
npm run cypress:open      # Interactive Cypress tests
npm run cy:run           # Headless Cypress tests
```

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
   - **Supervisor**: Orchestrates sub-agents and manages workflow
   - **Sub-agents**: Specialized agents for different tasks
   - **Tool Dispatcher**: Routes tool calls to appropriate handlers
   - **Tool Registry**: Dynamic tool registration system
   - **State Management**: Shared state across agent conversations
   - **Apex Optimizer Agent**: Advanced optimization agent with specialized tools

### Key Design Patterns

1. **WebSocket Communication**: Real-time bidirectional communication for agent interactions
2. **Dependency Injection**: Services injected via FastAPI dependency system
3. **Async/Await**: Pervasive async patterns for scalability
4. **Type Safety**: Pydantic models for request/response validation
5. **Multi-Agent Orchestration**: Supervisor pattern for coordinating specialized agents
6. **Repository Pattern**: Database access through repositories with unit of work
7. **Error Context**: Comprehensive error tracking with trace IDs
8. **OAuth Integration**: Support for OAuth authentication flows

### Database Schema

- **PostgreSQL Tables**: 
  - `users` - User accounts and authentication
  - `threads` - Conversation threads
  - `messages` - Chat messages
  - `runs` - Agent execution runs
  - `references` - Document references
  - `supply_catalog` - Supply catalog data
- **ClickHouse Tables**: 
  - `workload_events` - Time-series log data

### Authentication Flow

1. **Standard Login**:
   - Frontend sends login request to `/api/auth/login`
   - Backend validates credentials against PostgreSQL
   - JWT token generated and returned
   - Frontend stores token and includes in subsequent requests

2. **OAuth Flow**:
   - User initiates OAuth login
   - Redirected to provider for authorization
   - Callback processes authorization code
   - JWT token issued for authenticated session

3. **WebSocket Authentication**:
   - Connections authenticated via JWT token
   - Token validated on connection establishment

### Agent Workflow

1. User message received via WebSocket
2. Message queued in WebSocket message handler
3. Supervisor agent triages request
4. Appropriate sub-agent(s) selected based on task
5. Sub-agents use tools to gather data and perform analysis
6. Results aggregated and sent back via WebSocket
7. State persisted for conversation continuity

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
- `SECRET_KEY` - Application secret key
- `ANTHROPIC_API_KEY` - Anthropic API key for LLM
- `OPENAI_API_KEY` - OpenAI API key (if used)
- `ENVIRONMENT` - Environment (development/staging/production)

## Testing Strategy

### Backend Testing
- Unit tests for services and utilities
- Integration tests for API endpoints
- Agent system tests for sub-agents and supervisor
- WebSocket connection tests
- Database repository tests

### Frontend Testing
- Component tests with Jest
- Integration tests with Cypress
- WebSocket provider tests
- Store tests for state management
- Hook tests for custom hooks

## Deployment

### Docker
- `Dockerfile` - Main container configuration
- `Dockerfile.backend` - Backend-specific container

### Terraform (GCP)
- `terraform-gcp/` - GCP deployment configuration
- Includes scripts for deployment automation

### GCP Deployment
See `GCP_DEPLOYMENT_README.md` for detailed deployment instructions