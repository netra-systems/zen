# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Netra AI Workload Optimization Platform - An intelligent system for optimizing AI workloads by routing requests to the most suitable AI models based on cost, performance, and quality trade-offs.

## Essential Commands

### Backend Development
```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

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

# Frontend tests
cd frontend
npm test                  # Jest tests
npm run cypress:open      # Interactive Cypress tests
npm run cy:run           # Headless Cypress tests
```

## Architecture Overview

### Core Components

1. **Backend (FastAPI)** - `app/`
   - **Entry Point**: `app/main.py` - Initializes FastAPI app, middleware, and routes
   - **Routes**: `app/routes/` - API endpoints (auth, websockets, generation, etc.)
   - **Services**: `app/services/` - Business logic layer
   - **Agents**: `app/agents/` - Multi-agent system with supervisor pattern
   - **Database**: Dual database system
     - PostgreSQL: User data, configurations, persistent state
     - ClickHouse: Time-series log data and analytics

2. **Frontend (Next.js)** - `frontend/`
   - **Pages**: `frontend/app/` - Next.js app router pages
   - **Components**: `frontend/components/` - React components
   - **State**: `frontend/store/` - Zustand state management
   - **WebSocket**: Real-time communication with backend

3. **Agent System Architecture**
   - **Supervisor**: Orchestrates sub-agents and manages workflow
   - **Sub-agents**: Specialized agents for different tasks (triage, data analysis, optimization)
   - **Tool Dispatcher**: Routes tool calls to appropriate handlers
   - **State Management**: Shared state across agent conversations

### Key Design Patterns

1. **WebSocket Communication**: Real-time bidirectional communication for agent interactions
2. **Dependency Injection**: Services injected via FastAPI dependency system
3. **Async/Await**: Pervasive async patterns for scalability
4. **Type Safety**: Pydantic models for request/response validation
5. **Multi-Agent Orchestration**: Supervisor pattern for coordinating specialized agents

### Database Schema

- **PostgreSQL Tables**: users, threads, messages, runs, references, supply_catalog
- **ClickHouse Tables**: workload_events (time-series log data)

### Authentication Flow

1. Frontend sends login request to `/api/auth/login`
2. Backend validates credentials against PostgreSQL
3. JWT token generated and returned
4. Frontend stores token and includes in subsequent requests
5. WebSocket connections authenticated via token

### Agent Workflow

1. User message received via WebSocket
2. Supervisor agent triages request
3. Appropriate sub-agent(s) selected based on task
4. Sub-agents use tools to gather data and perform analysis
5. Results aggregated and sent back via WebSocket

## Development Guidelines

1. **Async First**: Use async/await for all I/O operations
2. **Type Annotations**: Always include type hints for function parameters and returns
3. **Pydantic Models**: Define schemas for all API requests/responses
4. **Error Handling**: Use proper exception handling and return meaningful error messages
5. **Logging**: Use central_logger for consistent logging across the application
6. **Testing**: Write tests for new functionality, maintain existing test coverage

## Common Tasks

### Adding a New API Endpoint
1. Create route handler in `app/routes/`
2. Define Pydantic schemas in `app/schemas/`
3. Implement business logic in `app/services/`
4. Add tests in `tests/routes/`

### Creating a New Sub-Agent
1. Create agent class in `app/agents/` extending BaseAgent
2. Define agent prompts in `app/agents/prompts.py`
3. Register agent with supervisor
4. Add agent-specific tools if needed

### Database Migrations
```bash
# Create new migration
alembic revision -m "Description of change"

# Apply migrations
python run_migrations.py
```

### WebSocket Event Handling
1. Define event type in `app/schemas/WebSocket.py`
2. Add handler in `app/routes/websockets.py`
3. Update frontend WebSocket provider to handle new event type

## Important Files to Know

- `app/config.py` - Application configuration and settings
- `app/agents/supervisor.py` - Main agent orchestration logic
- `app/services/agent_service.py` - Agent service layer
- `app/routes/websockets.py` - WebSocket connection handling
- `frontend/providers/WebSocketProvider.tsx` - Frontend WebSocket management
- `frontend/hooks/useAgent.ts` - React hook for agent interactions