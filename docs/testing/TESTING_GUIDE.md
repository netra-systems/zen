# Netra Apex Testing Guide - 97% Coverage Target

## 🔴 CRITICAL: Revenue-Critical Path Testing

**MANDATORY**: 97% test coverage for all revenue-generating features.

## Table of Contents

1. [Business-Critical Testing](#business-critical-testing) **← Revenue Path Coverage**
2. [Feature Flags & TDD](#feature-flags--tdd) **← NEW: TDD without breaking CI/CD**
3. [Testing Overview](#testing-overview)
4. [Backend Testing](#backend-testing)
5. [Frontend Testing](#frontend-testing)
6. [Integration Testing](#integration-testing)
7. [End-to-End Testing](#end-to-end-testing)
8. [Test Coverage Requirements](#test-coverage-requirements) **← 97% Target**
9. [CI/CD Testing](#cicd-testing)
10. [Performance Testing](#performance-testing)

## Business-Critical Testing

### Revenue Path Test Coverage

| Revenue Component | Required Coverage | Current Status | Priority |
|------------------|------------------|----------------|----------|
| **Savings Calculator** | 100% | 98% | P0 - CRITICAL |
| **Model Router** | 100% | 95% | P0 - CRITICAL |
| **Usage Tracking** | 100% | 97% | P0 - CRITICAL |
| **Billing Integration** | 100% | 92% | P0 - CRITICAL |
| **Free→Paid Conversion** | 97% | 89% | P1 - HIGH |
| **Analytics Dashboard** | 95% | 88% | P1 - HIGH |
| **API Rate Limiting** | 95% | 94% | P2 - MEDIUM |

### Test Categories by Business Impact

```python
# Revenue-Critical Tests (MUST PASS)
@pytest.mark.revenue_critical
def test_savings_calculation():
    """Verify accurate savings calculation for billing."""
    assert calculate_savings(100000, 70000) == {
        'savings': 30000,
        'percentage': 30.0,
        'netra_fee': 6000,  # 20% of savings
        'net_benefit': 24000
    }

@pytest.mark.revenue_critical
def test_usage_metering():
    """Ensure accurate usage tracking for billing."""
    # Test implementation
    pass
```

## Feature Flags & TDD

### Test-Driven Development Without Breaking CI/CD

**CRITICAL**: Use feature flags to write tests before implementation while maintaining 100% CI/CD pass rate.

#### Quick Start

```python
from test_framework.decorators import feature_flag, tdd_test

# Write test before implementation
@tdd_test("new_payment_system", expected_to_fail=True)
def test_payment_processing():
    """Test written before feature implementation."""
    result = process_payment(100)
    assert result.status == "success"

# Feature-gated test
@feature_flag("roi_calculator")
def test_roi_calculation():
    """Skipped if feature not enabled."""
    assert calculate_roi(10000) > 0
```

#### Feature Status Configuration

Configure in `test_feature_flags.json`:
```json
{
  "features": {
    "new_payment_system": {
      "status": "in_development",  // or: enabled, disabled, experimental
      "owner": "payments-team",
      "target_release": "v1.2.0"
    }
  }
}
```

#### TDD Workflow

1. **Write Test First** (status: `in_development`)
   - Test is skipped in CI
   - Can run locally with override

2. **Implement Feature**
   - Test remains skipped during development
   - Use `TEST_FEATURE_NAME=enabled` to test locally

3. **Enable Feature** (status: `enabled`)
   - Test now runs in CI
   - Must pass for deployment

#### Available Decorators

| Decorator | Purpose | When to Use |
|-----------|---------|------------|
| `@feature_flag(name)` | Skip if not enabled | Features that may not be ready |
| `@tdd_test(name)` | TDD with expected failure | Writing tests before code |
| `@requires_feature(*names)` | Multiple features required | Complex integrations |
| `@experimental_test()` | Opt-in experimental | Research/prototype features |
| `@performance_test(ms)` | Performance threshold | Critical path optimization |

#### Environment Overrides

```bash
# Enable feature for local testing
TEST_FEATURE_NEW_PAYMENT_SYSTEM=enabled python test_runner.py

# Run experimental tests
ENABLE_EXPERIMENTAL_TESTS=true python test_runner.py
```

#### Frontend Testing

```typescript
import { describeFeature, testTDD } from '@/test-utils/feature-flags';

describeFeature('roi_calculator', 'ROI Calculator Tests', () => {
  testTDD('roi_calculator', 'should calculate savings', () => {
    expect(calculateSavings(10000)).toBeGreaterThan(0);
  });
});
```

#### Business Benefits

- **50% Faster Development**: Write tests immediately, implement later
- **100% CI/CD Pass Rate**: Only enabled features tested in production
- **Clear Progress Tracking**: Feature status visible in test output
- **Risk Mitigation**: Test complex features without breaking builds

See [TESTING_WITH_FEATURE_FLAGS.md](TESTING_WITH_FEATURE_FLAGS.md) for complete documentation.

## Testing Overview

The Netra platform employs a comprehensive testing strategy across multiple layers:

### Testing Stack

- **Backend**: Pytest, pytest-asyncio, pytest-cov, httpx
- **Frontend**: Jest, React Testing Library
- **WebSocket**: Jest WebSocket Mock, pytest-asyncio
- **Performance**: Locust, k6
- **Coverage**: **97% MANDATORY** for revenue paths, 90%+ overall

### Test Levels (Use test_runner.py)

| Level | Duration | Coverage | When to Run | Command |
|-------|----------|----------|-------------|---------|  
| **Smoke** | <30s | Critical paths | Before commits | `python test_runner.py --level smoke --fast-fail` |
| **Unit** | 1-2min | Components | Development | `python test_runner.py --level unit --no-coverage --fast-fail` |
| **Agents** | 2-3min | Agent systems | Agent changes | `python test_runner.py --level agents` |
| **Integration** | 3-5min | Services | DEFAULT - Feature validation | `python test_runner.py --level integration --no-coverage --fast-fail` |
| **Critical** | 1-2min | Revenue paths | Pre-deployment | `python test_runner.py --level critical` |
| **Real E2E** | 15-20min | With real LLMs | Before releases | `python test_runner.py --level real_e2e --real-llm` |
| **Comprehensive** | 30-45min | Full coverage | Release | `python test_runner.py --level comprehensive` |

### Comprehensive Test Categories (10-15min each)

| Category | Purpose | Command |
|----------|---------|---------|  
| **Backend** | Full backend validation | `python test_runner.py --level comprehensive-backend` |
| **Frontend** | Full frontend validation | `python test_runner.py --level comprehensive-frontend` |
| **Core** | Core components deep test | `python test_runner.py --level comprehensive-core` |
| **Agents** | Multi-agent system validation | `python test_runner.py --level comprehensive-agents` |
| **WebSocket** | WebSocket deep validation | `python test_runner.py --level comprehensive-websocket` |
| **Database** | Database operations validation | `python test_runner.py --level comprehensive-database` |
| **API** | API endpoints validation | `python test_runner.py --level comprehensive-api` |

### Speed Optimization Options

#### Safe Optimizations (Recommended for CI/CD)
```bash
# CI Mode - All safe optimizations enabled
python test_runner.py --level unit --ci

# Individual safe optimizations
python test_runner.py --level unit --no-warnings    # Suppress warnings
python test_runner.py --level unit --no-coverage    # Skip coverage collection (30-50% faster)
python test_runner.py --level unit --fast-fail      # Stop on first failure

# Combined safe optimizations (DEFAULT RECOMMENDATION)
python test_runner.py --level integration --no-coverage --fast-fail
```

#### Aggressive Optimizations (Use with Caution)
```bash
# Speed mode - WARNING: May skip slow tests
python test_runner.py --level unit --speed

# Control parallelism
python test_runner.py --level unit --parallel 1      # Sequential (for debugging)
python test_runner.py --level unit --parallel auto   # Auto-detect optimal
python test_runner.py --level unit --parallel 4      # Custom worker count

# Real LLM Testing (CRITICAL for agent changes)
python test_runner.py --level agents --real-llm
python test_runner.py --level integration --real-llm --llm-model gemini-2.5-flash
python test_runner.py --level real_e2e --real-llm --llm-timeout 60
```

### Bad Test Detection System

The test framework includes automatic bad test detection to identify consistently failing tests:

#### Features
- **Automatic Tracking**: Monitors test failures across runs with `{test}:{failure_count}` tracking
- **Persistent Storage**: Saves failure history to `test_reports/bad_tests.json`
- **Smart Detection**: Identifies tests failing 5+ times consecutively or with >70% failure rate
- **Recommendations**: Suggests tests for immediate fix or deletion

#### Usage
```bash
# Tests run with detection enabled by default
python test_runner.py --level unit

# Disable bad test detection
python scripts/test_backend.py --no-bad-test-detection

# View bad test reports
python -m test_framework.bad_test_reporter          # Full report
python -m test_framework.bad_test_reporter --summary # Summary only
python -m test_framework.bad_test_reporter --details # With histories
python -m test_framework.bad_test_reporter --test "test_name" # Specific test history

# Reset bad test data
python -m test_framework.bad_test_reporter --reset  # Reset all data
python -m test_framework.bad_test_reporter --reset --reset-test "test_name" # Reset specific test
```

#### Detection Criteria
- **Consistently Failing**: 5+ consecutive failures → Recommended for immediate fix
- **High Failure Rate**: >70% failure rate with 10+ total failures → Consider refactoring
- **Very High Failure Rate**: >90% failure rate → Recommended for deletion/rewrite

### Test Categories by Priority

| Category | Business Impact | Required Coverage | Failure Action |
|----------|----------------|-------------------|----------------|
| **Revenue Critical** | Direct revenue impact | 100% | Block deployment |
| **Customer Critical** | Customer experience | 97% | Block deployment |
| **Core Features** | Primary functionality | 95% | Fix required |
| **Supporting Features** | Secondary features | 90% | Fix in next sprint |

## Backend Testing

### Setup

```bash
# RECOMMENDED: Use test runner for consistent environment setup
python test_runner.py --level integration --no-coverage --fast-fail

# Manual setup (if needed)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install test dependencies  
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-mock httpx

# Setup test database
export TEST_DATABASE_URL="postgresql://test_user:password@localhost:5432/netra_test"
python database_scripts/create_db.py --test
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
from netra_backend.app.agents.supervisor import SupervisorAgent
from netra_backend.app.schemas.Agent import AgentRequest

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
from netra_backend.app.ws_manager import WebSocketManager

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
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.services.database.unit_of_work import UnitOfWork

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
from netra_backend.app.main import app
from netra_backend.app.db.models_postgres import Base
from netra_backend.app.auth.auth import create_access_token

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
from netra_backend.app.schemas.User import UserCreate
from netra_backend.app.schemas.Thread import ThreadCreate
from netra_backend.app.schemas.Message import MessageCreate

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

For complete frontend testing documentation including Windows-specific instructions, see `SPEC/frontend_testing_guide.xml`.

### Frontend Test Suite Organization

Frontend tests are organized into parallel-executable suites for optimal performance:

| Suite | Description | Priority | Weight | Timeout |
|-------|-------------|----------|--------|---------|
| **components** | Component unit tests | 1 | 0.8 | 5s |
| **chat** | Chat-related components | 2 | 0.8 | 8s |
| **hooks** | React hooks tests | 1 | 0.6 | 5s |
| **auth** | Authentication tests | 2 | 0.4 | 8s |
| **integration-basic** | Basic integration tests | 3 | 0.5 | 15s |
| **integration-advanced** | Advanced integration tests | 3 | 0.6 | 20s |
| **integration-comprehensive** | Comprehensive integration | 4 | 0.8 | 25s |
| **integration-critical** | Critical path tests | 4 | 0.8 | 20s |
| **system** | System-level tests | 3 | 0.4 | 15s |
| **imports** | Import verification (sequential) | 1 | 0.2 | 5s |
| **core** | Core unified tests | 2 | 0.4 | 10s |

### Quick Start

```bash
# Run all test suites in parallel (recommended)
cd frontend && npm run test:suites

# Run specific test suite
npm run test:suites:components
npm run test:suites:chat
npm run test:suites:hooks

# Run by priority level (fast/medium/slow)
npm run test:suites:fast     # Priority 1 tests only
npm run test:suites:medium   # Priority 1-2 tests
npm run test:suites:slow     # All tests including heavy integration

# Run all integration tests
npm run test:suites:integration

# Control parallelization
npm run test:suites:parallel    # Max 8 parallel suites
npm run test:suites:sequential  # Run sequentially

# Watch mode for development
npm run test:suites:watch

# Generate coverage report
npm run test:suites:coverage

# Using unified test runner
python test_runner.py --frontend-only

# Using the test suite runner directly
cd frontend
node test-suite-runner.js --all              # Run all suites
node test-suite-runner.js components hooks   # Run specific suites
node test-suite-runner.js --priority 1       # Run priority 1 tests
node test-suite-runner.js --max-parallel 4   # Limit parallel execution
```

### Parallel Execution Strategy

The test suite runner intelligently manages parallel execution based on:

1. **Priority Groups**: Tests run in priority order (1-4)
2. **Resource Weights**: Heavy tests get fewer parallel slots
3. **CPU Optimization**: Uses 75% of available CPU cores by default
4. **Smart Chunking**: Groups compatible tests for parallel execution

Example execution flow:
```
Priority 1 (Fast) → components, hooks, imports (parallel)
Priority 2 (Medium) → chat, auth, core (parallel)  
Priority 3 (Slower) → integration-basic, system (parallel)
Priority 4 (Heavy) → integration-comprehensive, critical (limited parallel)
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
from netra_backend.app.services.database.unit_of_work import UnitOfWork
from netra_backend.app.services.agent_service import AgentService

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
# RECOMMENDED: Generate coverage with test runner
python test_runner.py --level comprehensive  # Includes coverage report

# Traditional coverage generation
pytest --cov=app --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Coverage reports are automatically generated in test_reports/ directory
open test_reports/coverage/index.html  # View unified coverage report
```

### Frontend Coverage

See `SPEC/frontend_testing_guide.xml` for frontend coverage configuration.

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

## Architecture Compliance Testing

### CRITICAL: 450-line and 25-line Limits

**MANDATORY**: All code must pass architecture compliance checks:

```bash
# Check architecture compliance (run before commits)
python scripts/check_architecture_compliance.py

# Include in test suite
python test_runner.py --level comprehensive  # Includes compliance checks

# Generate compliance report
python scripts/check_architecture_compliance.py --report --output test_reports/
```

**Compliance Requirements**:
- Every file ≤300 lines (no exceptions)
- Every function ≤8 lines (no exceptions)  
- Modular design with clear interfaces
- Single responsibility per module/function

## Testing Best Practices

### 1. Architecture-First Testing
- **Always check compliance first**: Run architecture checks before functional tests
- **Module isolation**: Each 450-line module should be independently testable
- **Function composition**: Test 25-line functions in combination and isolation

### 2. Test Isolation
- Each test should be independent
- Use fixtures for setup/teardown
- Mock external dependencies

### 3. Test Data Management
- Use factories for test data creation
- Clean up test data after tests
- Use separate test database

### 4. Async Testing
- Use pytest-asyncio for async tests
- Properly handle event loops
- Test timeout scenarios

### 5. WebSocket Testing
- Mock WebSocket connections
- Test reconnection logic
- Verify message ordering

### 6. Error Scenarios
- Test error handling paths
- Verify error messages
- Test recovery mechanisms

### 7. Performance Considerations
- Set appropriate timeouts
- Test under load conditions
- Monitor resource usage

### 8. Compliance Verification
- **Pre-commit**: Always run compliance checks
- **CI/CD Integration**: Fail builds on compliance violations
- **Regular Audits**: Weekly architecture compliance reviews

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