# Netra Platform Testing Guide

Comprehensive testing documentation for the Netra AI Optimization Platform, covering backend, frontend, integration, and end-to-end testing strategies.

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Backend Testing](#backend-testing)
3. [Frontend Testing](#frontend-testing)
4. [Integration Testing](#integration-testing)
5. [End-to-End Testing](#end-to-end-testing)
6. [Test Coverage](#test-coverage)
7. [CI/CD Testing](#cicd-testing)
8. [Performance Testing](#performance-testing)

## Testing Overview

The Netra platform employs a comprehensive testing strategy across multiple layers:

### Testing Stack

- **Backend**: Pytest, pytest-asyncio, pytest-cov, httpx
- **Frontend**: Jest, React Testing Library, Cypress
- **WebSocket**: Jest WebSocket Mock, pytest-asyncio
- **Performance**: Locust, k6
- **Coverage**: 80%+ target coverage

### Test Categories

| Category | Purpose | Tools | Location |
|----------|---------|-------|----------|
| Unit Tests | Individual component testing | Pytest, Jest | `tests/`, `__tests__/` |
| Integration Tests | Service interaction testing | Pytest, RTL | `tests/integration/` |
| E2E Tests | Full workflow testing | Cypress | `cypress/e2e/` |
| Performance Tests | Load and stress testing | Locust | `tests/performance/` |

## Backend Testing

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-mock httpx

# Setup test database
export TEST_DATABASE_URL="postgresql://test_user:password@localhost:5432/netra_test"
python create_db.py --test
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_auth.py

# Run tests matching pattern
pytest -k "test_login"

# Run with verbose output
pytest -v

# Run async tests
pytest tests/test_websocket.py -v

# Run in parallel
pytest -n 4
```

### Test Structure

```
tests/
├── agents/                      # Agent system tests
│   ├── test_supervisor_agent.py
│   ├── test_supervisor_orchestration.py
│   ├── test_subagent_workflow.py
│   └── test_agent_e2e_critical.py
├── routes/                      # API endpoint tests
│   ├── test_auth_flow.py
│   ├── test_websocket_connection.py
│   ├── test_websocket_advanced.py
│   ├── test_threads_route.py
│   └── test_health_route.py
├── services/                    # Service layer tests
│   ├── test_agent_service.py
│   ├── test_generation_service.py
│   ├── test_security_service.py
│   ├── test_state_persistence.py
│   └── apex_optimizer_agent/
│       ├── test_tool_builder.py
│       └── tools/
│           ├── test_cost_analyzer.py
│           ├── test_latency_optimizer.py
│           └── test_policy_simulator.py
├── core/                        # Core functionality tests
│   ├── test_config_manager.py
│   ├── test_error_handling.py
│   └── test_service_interfaces.py
├── conftest.py                  # Shared fixtures
└── test_helpers.py              # Test utilities
```

### Key Test Files

#### Agent System Tests

```python
# tests/agents/test_supervisor_agent.py
import pytest
from app.agents.supervisor import SupervisorAgent
from app.schemas.Agent import AgentRequest

@pytest.mark.asyncio
async def test_supervisor_orchestration():
    """Test the complete supervisor orchestration flow"""
    supervisor = SupervisorAgent()
    request = AgentRequest(
        message="Optimize my AI workload",
        thread_id="test-thread"
    )
    
    result = await supervisor.execute(request)
    
    assert result.status == "completed"
    assert len(result.sub_agent_results) == 5
    assert result.final_report is not None
```

#### WebSocket Tests

```python
# tests/routes/test_websocket_advanced.py
import pytest
import json
from httpx import AsyncClient
from app.ws_manager import WebSocketManager

@pytest.mark.asyncio
async def test_websocket_agent_execution(
    async_client: AsyncClient,
    authenticated_websocket
):
    """Test complete agent execution via WebSocket"""
    
    # Send agent start message
    await authenticated_websocket.send_json({
        "action": "start_agent",
        "data": {
            "message": "Test optimization request",
            "thread_id": "test-thread"
        }
    })
    
    # Collect all messages
    messages = []
    async for message in authenticated_websocket:
        data = json.loads(message)
        messages.append(data)
        
        if data["type"] == "agent_completed":
            break
    
    # Verify message sequence
    message_types = [msg["type"] for msg in messages]
    assert "agent_started" in message_types
    assert "sub_agent_update" in message_types
    assert "agent_completed" in message_types
```

#### Database Repository Tests

```python
# tests/services/test_database_repositories.py
import pytest
from app.services.database.thread_repository import ThreadRepository
from app.services.database.unit_of_work import UnitOfWork

@pytest.mark.asyncio
async def test_thread_repository_crud():
    """Test thread repository CRUD operations"""
    async with UnitOfWork() as uow:
        repo = ThreadRepository(uow.session)
        
        # Create
        thread = await repo.create(
            user_id=1,
            title="Test Thread"
        )
        assert thread.id is not None
        
        # Read
        fetched = await repo.get(thread.id)
        assert fetched.title == "Test Thread"
        
        # Update
        await repo.update(thread.id, title="Updated Thread")
        updated = await repo.get(thread.id)
        assert updated.title == "Updated Thread"
        
        # Delete
        await repo.delete(thread.id)
        deleted = await repo.get(thread.id)
        assert deleted is None
```

### Test Fixtures

```python
# tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from httpx import AsyncClient
from app.main import app
from app.db.models_postgres import Base
from app.auth.auth import create_access_token

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db():
    """Create test database"""
    engine = create_async_engine(
        "postgresql+asyncpg://test_user:password@localhost/netra_test"
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def async_client(test_db):
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def auth_token():
    """Generate test authentication token"""
    return create_access_token(
        data={"sub": "test@example.com", "user_id": 1}
    )

@pytest.fixture
async def authenticated_client(async_client, auth_token):
    """Create authenticated test client"""
    async_client.headers["Authorization"] = f"Bearer {auth_token}"
    return async_client
```

### Mock Data Factories

```python
# tests/test_helpers.py
from datetime import datetime
from app.schemas.User import UserCreate
from app.schemas.Thread import ThreadCreate
from app.schemas.Message import MessageCreate

def create_test_user(email="test@example.com"):
    """Factory for test user"""
    return UserCreate(
        email=email,
        password="SecurePassword123!",
        name="Test User"
    )

def create_test_thread(user_id=1):
    """Factory for test thread"""
    return ThreadCreate(
        user_id=user_id,
        title="Test Thread",
        metadata={"test": True}
    )

def create_test_message(thread_id, role="user"):
    """Factory for test message"""
    return MessageCreate(
        thread_id=thread_id,
        role=role,
        content="Test message content",
        created_at=datetime.utcnow()
    )
```

## Frontend Testing

### Setup

```bash
cd frontend

# Install dependencies
npm install

# Install additional test dependencies
npm install --save-dev @testing-library/react-hooks
npm install --save-dev @testing-library/user-event
npm install --save-dev jest-websocket-mock
npm install --save-dev msw
```

### Running Tests

```bash
# Run all tests
npm test

# Run in watch mode
npm test -- --watch

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test ChatInterface

# Update snapshots
npm test -- -u

# Debug mode
npm test -- --detectOpenHandles
```

### Test Structure

```
frontend/__tests__/
├── components/               # Component tests
│   ├── chat/
│   │   ├── ChatHeader.test.tsx
│   │   ├── MessageItem.test.tsx
│   │   ├── MessageInput.test.tsx
│   │   └── MainChat.test.tsx
│   ├── ui/
│   │   └── select.test.tsx
│   ├── ChatInterface.test.tsx
│   ├── SubAgentStatus.test.tsx
│   └── ThreadList.test.tsx
├── hooks/                   # Hook tests
│   ├── useWebSocket.test.ts
│   ├── useAgent.test.ts
│   └── useChatWebSocket.test.ts
├── store/                   # Store tests
│   ├── chatStore.test.ts
│   ├── authStore.test.ts
│   └── threadStore.test.ts
├── services/               # Service tests
│   ├── webSocketService.test.ts
│   └── messageService.test.ts
├── critical/               # Critical path tests
│   ├── AuthenticationFlow.test.tsx
│   ├── AgentInteraction.test.tsx
│   ├── WebSocketResilience.test.tsx
│   └── ErrorHandling.test.tsx
└── test-utils/            # Test utilities
    └── mockProviders.tsx
```

### Key Test Examples

#### Component Tests

```typescript
// __tests__/components/chat/MessageItem.test.tsx
import { render, screen } from '@testing-library/react';
import { MessageItem } from '@/components/chat/MessageItem';

describe('MessageItem', () => {
  it('renders user message correctly', () => {
    const message = {
      id: '1',
      role: 'user',
      content: 'Test message',
      timestamp: new Date().toISOString()
    };
    
    render(<MessageItem message={message} />);
    
    expect(screen.getByText('Test message')).toBeInTheDocument();
    expect(screen.getByText('You')).toBeInTheDocument();
  });
  
  it('renders agent message with thinking indicator', () => {
    const message = {
      id: '2',
      role: 'assistant',
      content: 'Processing...',
      metadata: { thinking: true }
    };
    
    render(<MessageItem message={message} />);
    
    expect(screen.getByTestId('thinking-indicator')).toBeInTheDocument();
  });
});
```

#### Hook Tests

```typescript
// __tests__/hooks/useWebSocket.test.ts
import { renderHook, act } from '@testing-library/react';
import WS from 'jest-websocket-mock';
import { useWebSocket } from '@/hooks/useWebSocket';

describe('useWebSocket', () => {
  let server: WS;
  
  beforeEach(() => {
    server = new WS('ws://localhost:8000/ws');
  });
  
  afterEach(() => {
    WS.clean();
  });
  
  it('connects to WebSocket server', async () => {
    const { result } = renderHook(() => useWebSocket());
    
    await server.connected;
    
    expect(result.current.connected).toBe(true);
  });
  
  it('handles reconnection on disconnect', async () => {
    const { result } = renderHook(() => useWebSocket());
    
    await server.connected;
    
    // Simulate disconnect
    server.close();
    
    // Wait for reconnection attempt
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 1000));
    });
    
    expect(result.current.reconnectAttempts).toBeGreaterThan(0);
  });
});
```

#### Store Tests

```typescript
// __tests__/store/chatStore.test.ts
import { act } from '@testing-library/react';
import { useChatStore } from '@/store/chat';

describe('ChatStore', () => {
  beforeEach(() => {
    useChatStore.setState({ messages: [], currentThread: null });
  });
  
  it('adds message to store', () => {
    const message = {
      id: '1',
      content: 'Test',
      role: 'user',
      timestamp: new Date().toISOString()
    };
    
    act(() => {
      useChatStore.getState().addMessage(message);
    });
    
    expect(useChatStore.getState().messages).toHaveLength(1);
    expect(useChatStore.getState().messages[0]).toEqual(message);
  });
  
  it('clears messages', () => {
    act(() => {
      useChatStore.getState().addMessage({ id: '1', content: 'Test' });
      useChatStore.getState().clearMessages();
    });
    
    expect(useChatStore.getState().messages).toHaveLength(0);
  });
});
```

### Mock Providers

```typescript
// __tests__/test-utils/mockProviders.tsx
import { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

export const createMockProviders = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });
  
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

// Usage in tests
const wrapper = createMockProviders();
const { result } = renderHook(() => useCustomHook(), { wrapper });
```

## Integration Testing

### API Integration Tests

```python
# tests/integration/test_api_integration.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_complete_user_flow(async_client: AsyncClient):
    """Test complete user flow from registration to agent execution"""
    
    # 1. Register user
    register_response = await async_client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "password": "SecurePass123!",
        "name": "New User"
    })
    assert register_response.status_code == 201
    
    # 2. Login
    login_response = await async_client.post("/api/auth/login", json={
        "email": "newuser@example.com",
        "password": "SecurePass123!"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # 3. Create thread
    headers = {"Authorization": f"Bearer {token}"}
    thread_response = await async_client.post(
        "/api/threads",
        json={"title": "Test Thread"},
        headers=headers
    )
    assert thread_response.status_code == 201
    thread_id = thread_response.json()["id"]
    
    # 4. Execute agent via WebSocket (mocked)
    # ... WebSocket testing code
```

### Database Integration Tests

```python
# tests/integration/test_database_integration.py
import pytest
from app.services.database.unit_of_work import UnitOfWork
from app.services.agent_service import AgentService

@pytest.mark.asyncio
async def test_agent_state_persistence():
    """Test agent state persistence across executions"""
    
    async with UnitOfWork() as uow:
        service = AgentService(uow)
        
        # First execution
        run_id_1 = await service.start_execution(
            user_id=1,
            message="First request",
            thread_id="test-thread"
        )
        
        # Save state
        await service.save_state(run_id_1, {"step": 1})
        
        # Second execution in same thread
        run_id_2 = await service.start_execution(
            user_id=1,
            message="Second request",
            thread_id="test-thread"
        )
        
        # Load previous state
        state = await service.load_state("test-thread")
        assert state["step"] == 1
```

## End-to-End Testing

### Cypress Setup

```bash
cd frontend

# Install Cypress
npm install --save-dev cypress

# Open Cypress
npm run cypress:open

# Run headless
npm run cy:run
```

### E2E Test Structure

```
cypress/
├── e2e/
│   ├── auth.cy.ts
│   ├── chat.cy.ts
│   ├── apex_optimizer_agent_v3.cy.ts
│   ├── demo-chat-optimization.cy.ts
│   └── demo-roi-calculation.cy.ts
├── fixtures/
│   └── example.json
├── support/
│   ├── commands.ts
│   └── e2e.ts
└── screenshots/
```

### Key E2E Tests

```typescript
// cypress/e2e/chat.cy.ts
describe('Chat Flow', () => {
  beforeEach(() => {
    cy.login('test@example.com', 'password');
    cy.visit('/chat');
  });
  
  it('completes full optimization workflow', () => {
    // Type message
    cy.get('[data-cy=message-input]')
      .type('Optimize my GPU workload for cost efficiency');
    
    // Send message
    cy.get('[data-cy=send-button]').click();
    
    // Wait for agent to start
    cy.get('[data-cy=agent-status]')
      .should('contain', 'TriageSubAgent')
      .and('contain', 'thinking');
    
    // Wait for completion
    cy.get('[data-cy=agent-completed]', { timeout: 30000 })
      .should('be.visible');
    
    // Verify results
    cy.get('[data-cy=optimization-results]')
      .should('contain', 'Recommendations')
      .and('contain', 'Cost Savings');
  });
  
  it('handles WebSocket reconnection', () => {
    // Disconnect WebSocket
    cy.window().then(win => {
      win.wsConnection.close();
    });
    
    // Should show reconnecting
    cy.get('[data-cy=connection-status]')
      .should('contain', 'Reconnecting');
    
    // Should reconnect automatically
    cy.get('[data-cy=connection-status]', { timeout: 10000 })
      .should('contain', 'Connected');
  });
});
```

### Custom Cypress Commands

```typescript
// cypress/support/commands.ts
Cypress.Commands.add('login', (email: string, password: string) => {
  cy.request('POST', 'http://localhost:8000/api/auth/login', {
    email,
    password
  }).then(response => {
    window.localStorage.setItem('auth_token', response.body.access_token);
  });
});

Cypress.Commands.add('createThread', (title: string) => {
  cy.request({
    method: 'POST',
    url: 'http://localhost:8000/api/threads',
    headers: {
      Authorization: `Bearer ${window.localStorage.getItem('auth_token')}`
    },
    body: { title }
  });
});
```

## Test Coverage

### Backend Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Frontend Coverage

```bash
# Generate coverage report
npm test -- --coverage --watchAll=false

# View coverage
open coverage/lcov-report/index.html
```

### Coverage Requirements

| Component | Target | Current |
|-----------|--------|---------|
| Backend Core | 90% | 87% |
| Agent System | 85% | 82% |
| API Routes | 95% | 93% |
| Frontend Components | 85% | 81% |
| Hooks & Services | 90% | 88% |
| E2E Critical Paths | 100% | 100% |

## CI/CD Testing

### GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: warp-custom-default
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/netra_test
          REDIS_URL: redis://localhost:6379
        run: |
          pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
  
  frontend-tests:
    runs-on: warp-custom-default
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci
      
      - name: Run tests
        working-directory: ./frontend
        run: npm test -- --coverage --watchAll=false
      
      - name: Run E2E tests
        working-directory: ./frontend
        run: npm run cy:run
```

## Performance Testing

### Locust Setup

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import json

class NetraUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and get token"""
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def get_threads(self):
        """Get user threads"""
        self.client.get("/api/threads", headers=self.headers)
    
    @task(1)
    def create_thread(self):
        """Create new thread"""
        self.client.post("/api/threads", 
            json={"title": "Load test thread"},
            headers=self.headers
        )
    
    @task(5)
    def health_check(self):
        """Check health endpoint"""
        self.client.get("/health")
```

### Running Performance Tests

```bash
# Install Locust
pip install locust

# Run load test
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Run with specific parameters
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users=100 \
  --spawn-rate=10 \
  --run-time=60s \
  --headless
```

## Testing Best Practices

### 1. Test Isolation
- Each test should be independent
- Use fixtures for setup/teardown
- Mock external dependencies

### 2. Test Data Management
- Use factories for test data creation
- Clean up test data after tests
- Use separate test database

### 3. Async Testing
- Use pytest-asyncio for async tests
- Properly handle event loops
- Test timeout scenarios

### 4. WebSocket Testing
- Mock WebSocket connections
- Test reconnection logic
- Verify message ordering

### 5. Error Scenarios
- Test error handling paths
- Verify error messages
- Test recovery mechanisms

### 6. Performance Considerations
- Set appropriate timeouts
- Test under load conditions
- Monitor resource usage

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Reset test database
dropdb netra_test
createdb netra_test
python run_migrations.py --database=test
```

#### WebSocket Test Failures
```python
# Increase timeout for slow tests
@pytest.mark.timeout(30)
async def test_long_running_agent():
    # Test code
```

#### Frontend Test Failures
```bash
# Clear Jest cache
npm test -- --clearCache

# Update snapshots
npm test -- -u

# Debug specific test
npm test -- --detectOpenHandles ChatInterface
```

## Continuous Improvement

### Test Metrics to Track

1. **Coverage Percentage**: Aim for 80%+ overall
2. **Test Execution Time**: Keep under 5 minutes for CI
3. **Flaky Test Rate**: Should be < 1%
4. **Test Maintenance Cost**: Track time spent fixing tests

### Regular Reviews

- Weekly: Review failing tests
- Monthly: Update test data and fixtures
- Quarterly: Refactor test structure
- Annually: Review testing strategy

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [Cypress Documentation](https://docs.cypress.io/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Locust Documentation](https://docs.locust.io/)