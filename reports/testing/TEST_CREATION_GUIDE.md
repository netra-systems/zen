# 🚀 Netra Test Creation Guide

## 🚨 CRITICAL: READ THIS FIRST

**This is the AUTHORITATIVE guide for creating tests in Netra.** Before writing ANY test, understand:

1. **Business Value > Real System > Tests** - Tests exist to serve the working system
2. **Real Services > Mocks** - ALWAYS use real services when possible
3. **User Context Isolation is MANDATORY** - Multi-user system requires factory patterns
4. **WebSocket Events are MISSION CRITICAL** - All 5 agent events must be sent

## Related Documentation

- **[Test Architecture Visual Overview](tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md)** - Complete visual guide to test infrastructure
- **[Staging E2E Test Index](../../tests/e2e/STAGING_E2E_TEST_INDEX.md)** - Comprehensive index of all staging-ready E2E tests
- **[CLAUDE.md](CLAUDE.md)** - Prime directives for development and testing
- **[User Context Architecture](USER_CONTEXT_ARCHITECTURE.md)** - Factory patterns and isolation (MANDATORY)
- **[Docker Orchestration](docs/docker_orchestration.md)** - Docker management and Alpine containers
- **[Unified Test Runner](tests/unified_test_runner.py)** - Central test execution script

## 📋 Table of Contents

1. [Test Philosophy](#test-philosophy)
2. [Test Categories & When to Use](#test-categories--when-to-use)
3. [Creating Your First Test](#creating-your-first-test)
4. [Using the Unified Test Runner](#using-the-unified-test-runner)
5. [SSOT: Ports & Configuration](#ssot-ports--configuration)
6. [SSOT: Shared Test Utilities](#ssot-shared-test-utilities)
7. [What NOT to Do](#what-not-to-do)
8. [Examples & Patterns](#examples--patterns)
9. [Troubleshooting](#troubleshooting)

## Test Philosophy

### Core Principles

```python
# GOOD: Real services, real value
async def test_user_can_send_message_to_agent():
    """Test that delivers REAL business value."""
    # Uses real WebSocket, real agent, real database
    async with real_websocket_client() as client:
        response = await client.send_agent_message("Help me optimize costs")
        assert response.contains_actionable_insights()

# BAD: Mocked everything, no real value
def test_message_handler_calls_function():
    """Test that proves nothing about real system."""
    mock_handler = Mock()
    mock_handler.handle_message(Mock())
    mock_handler.handle_message.assert_called_once()  # Useless!
```

### Test Hierarchy

```
Real E2E with Real LLM (BEST - Maximum Business Value)
    ↓
Integration with Real Services (GOOD - Validates System)
    ↓
Unit with Minimal Mocks (ACCEPTABLE - Fast Feedback)
    ↓
Pure Mocks (FORBIDDEN - No Value)
```

## Test Categories & When to Use

### 1. Unit Tests (`unit/`)
**When:** Testing pure business logic, data models, utilities
**Infrastructure:** None required
**Mocks:** Allowed for external dependencies ONLY

```python
# netra_backend/tests/unit/test_cost_calculator.py
def test_calculate_token_cost():
    """Pure logic test - no infrastructure needed."""
    cost = calculate_token_cost(tokens=1000, model="gpt-4")
    assert cost == 0.03  # Business logic validation
```

### 2. Integration Tests (`integration/`)
**When:** Testing service interactions, database operations, API endpoints
**Infrastructure:** Local services (PostgreSQL, Redis)
**Mocks:** External APIs only (LLM, OAuth)

```python
# netra_backend/tests/integration/test_user_session.py
async def test_user_session_persistence(real_db, real_redis):
    """Test with REAL database and cache."""
    user = await create_user(real_db, email="test@example.com")
    session = await create_session(real_redis, user_id=user.id)
    assert await get_session(real_redis, session.id) is not None
```

### 3. E2E Tests (`e2e/`)
**When:** Testing complete user journeys, agent workflows
**Infrastructure:** Full Docker stack + Real LLM
**Mocks:** NONE - Everything must be real

```python
# netra_backend/tests/e2e/test_complete_agent_flow.py
async def test_agent_optimization_workflow(real_services, real_llm):
    """Complete business value delivery test."""
    # Real user, real WebSocket, real agent, real LLM
    user = await create_real_user()
    async with WebSocketClient(user.token) as client:
        # Send real optimization request
        await client.send_message({
            "type": "agent_request",
            "agent": "cost_optimizer",
            "message": "Analyze my AWS spend"
        })
        
        # Verify all 5 critical WebSocket events
        events = await client.collect_events(timeout=30)
        assert_websocket_events_sent(events, [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ])
        
        # Verify business value delivered
        result = events[-1]["data"]["result"]
        assert "cost_savings" in result
        assert result["cost_savings"]["amount"] > 0
```

### 4. Mission Critical Tests (`mission_critical/`)
**When:** Testing business-critical paths that MUST work
**Infrastructure:** Full Docker stack
**Special:** Run on EVERY commit, NEVER skip

```python
# tests/mission_critical/test_websocket_agent_events.py
async def test_all_websocket_events_sent():
    """CRITICAL: WebSocket events enable chat value."""
    # This test MUST pass or the system has no value
```

## Creating Your First Test

### Step 1: Determine Test Category

```python
"""
Decision Tree:
1. Does it need a database? → Integration or E2E
2. Does it test user workflow? → E2E
3. Does it validate business logic? → Unit or Integration
4. Is it critical for revenue? → Mission Critical
"""
```

### Step 2: Create Test File

```python
# Location: {service}/tests/{category}/test_{feature}.py
# Example: netra_backend/tests/integration/test_agent_execution.py

"""
Test Agent Execution Pipeline

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agents deliver value
- Value Impact: Agents must execute correctly to provide insights
- Strategic Impact: Core platform functionality
"""

import pytest
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

class TestAgentExecution(BaseIntegrationTest):
    """Test agent execution with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_executes_with_real_database(self, real_services_fixture):
        """Test agent execution with real PostgreSQL and Redis."""
        # Your test here
```

### Step 3: Use Proper Fixtures

```python
# SSOT: test_framework/real_services_test_fixtures.py
from test_framework.real_services_test_fixtures import (
    real_services_fixture,  # Provides all real services
    real_db_fixture,        # Just PostgreSQL
    real_redis_fixture,     # Just Redis
    real_llm_fixture,       # Real LLM API
)

# SSOT: test_framework/isolated_environment_fixtures.py
from test_framework.isolated_environment_fixtures import (
    isolated_env,           # Isolated environment for test
    test_config,           # Test-specific configuration
)
```

### Step 4: Add to Test Runner

Tests are automatically discovered! Just follow naming conventions:
- File must be named `test_*.py`
- Test functions must start with `test_`
- Use proper category markers: `@pytest.mark.{category}`

## Using the Unified Test Runner

### Basic Usage

```bash
# Run specific category
python tests/unified_test_runner.py --category integration

# Run with real services (Docker starts automatically)
python tests/unified_test_runner.py --real-services

# Run E2E with real LLM
python tests/unified_test_runner.py --category e2e --real-llm

# Fast feedback mode (2-minute cycle)
python tests/unified_test_runner.py --execution-mode fast_feedback

# Run mission critical tests
python tests/mission_critical/test_websocket_agent_events_suite.py
```

### Advanced Options

```bash
# Parallel execution
python tests/unified_test_runner.py --parallel --workers 4

# With coverage report
python tests/unified_test_runner.py --coverage --coverage-threshold 80

# Fail fast on first error
python tests/unified_test_runner.py --fast-fail

# Alpine containers (50% faster)
python tests/unified_test_runner.py --real-services  # Alpine is default

# Specific test file
python tests/unified_test_runner.py --test-file netra_backend/tests/integration/test_agent.py
```

## SSOT: Ports & Configuration

### Test Environment Ports (NEVER CHANGE)

```python
# SSOT: These ports are used EVERYWHERE in tests
TEST_PORTS = {
    "postgresql": 5434,    # Test PostgreSQL
    "redis": 6381,         # Test Redis  
    "backend": 8000,       # Backend service
    "auth": 8081,          # Auth service
    "frontend": 3000,      # Frontend
    "clickhouse": 8123,    # ClickHouse
    "analytics": 8002,     # Analytics service
}

# Alpine test environment (optimized)
ALPINE_TEST_PORTS = {
    "postgresql": 5434,    # Same as regular
    "redis": 6382,        # Different for Alpine
    # Others same as TEST_PORTS
}

# Development ports (different from test)
DEV_PORTS = {
    "postgresql": 5432,    # Dev PostgreSQL
    "redis": 6379,        # Dev Redis
    # Services use same ports as test
}
```

### Environment Configuration

```python
# SSOT: shared/isolated_environment.py
from shared.isolated_environment import IsolatedEnvironment, get_env

# In tests, ALWAYS use IsolatedEnvironment
def test_with_isolated_env():
    env = get_env()
    env.set("API_KEY", "test_key", source="test")
    
# NEVER use os.environ directly!
# BAD: os.environ["API_KEY"] = "test"
# GOOD: env.set("API_KEY", "test", source="test")
```

## SSOT: Shared Test Utilities

### Core Test Base Classes

```python
# SSOT: test_framework/base_integration_test.py
from test_framework.base_integration_test import BaseIntegrationTest

class MyIntegrationTest(BaseIntegrationTest):
    """Provides setup/teardown, logging, common mocks."""
    pass

# SSOT: test_framework/base_e2e_test.py  
from test_framework.base_e2e_test import BaseE2ETest

class MyE2ETest(BaseE2ETest):
    """Provides WebSocket client, real services, assertions."""
    pass
```

### Docker Management

```python
# SSOT: test_framework/unified_docker_manager.py
from test_framework.unified_docker_manager import UnifiedDockerManager

# This is used by test runner - rarely need direct access
manager = UnifiedDockerManager()
env_info = manager.acquire_environment("test", use_alpine=True)
# ... run tests ...
manager.release_environment("test")
```

### WebSocket Testing

```python
# SSOT: test_framework/websocket_helpers.py
from test_framework.websocket_helpers import (
    WebSocketTestClient,
    assert_websocket_events,
    wait_for_agent_completion,
)

async def test_websocket_flow():
    async with WebSocketTestClient(token=user_token) as client:
        await client.send_json({"type": "message", "content": "test"})
        response = await client.receive_json()
        assert_websocket_events(response, ["agent_started"])
```

### Agent Testing

```python
# SSOT: test_framework/agent_test_helpers.py
from test_framework.agent_test_helpers import (
    create_test_agent,
    mock_llm_response,
    assert_agent_execution,
)

async def test_agent():
    agent = create_test_agent("cost_optimizer")
    result = await agent.execute("Optimize my costs")
    assert_agent_execution(result, expected_tools=["analyze_costs"])
```

## Handling Legacy Tests

### When Encountering Really Bad Legacy Tests

When you encounter a legacy test that is fundamentally flawed (e.g., testing mocks instead of real behavior, violating SSOT principles, or not providing business value), follow this process:

1. **Capture Intent** - Understand what the legacy test was TRYING to validate
2. **Create ALL NEW Test** - Write a completely new test file following current standards:
   - Use real services and real system behavior
   - Follow latest CLAUDE.md standards
   - Implement proper SSOT patterns from test_framework/
   - Ensure the test validates actual business value
3. **Delete Legacy Test** - Remove the old test file entirely
   - Use the deleted file ONLY as inspiration for general intent
   - Do NOT copy any code patterns from the legacy test

**Example:**
```python
# LEGACY TEST (to be deleted): tests/old_test_mock_agent.py
def test_agent_mock():  # BAD: Tests mocks, not real system
    mock_agent = Mock()
    mock_agent.execute.return_value = "mocked"
    assert mock_agent.execute() == "mocked"  # Proves nothing!

# NEW TEST (complete replacement): tests/integration/test_agent_execution.py  
async def test_agent_delivers_business_value(real_services_fixture):
    """Test agent provides real optimization insights."""
    # Real agent, real database, real value
    agent = await create_real_agent("cost_optimizer")
    result = await agent.execute_with_context(
        message="Analyze costs",
        user_context=real_user_context
    )
    assert result.contains_actionable_insights()
    assert result.potential_savings > 0  # Real business value!
```

## What NOT to Do

### ❌ FORBIDDEN Patterns

```python
# 1. NEVER use mocks in E2E tests
@pytest.mark.e2e
def test_e2e_with_mocks():  # WRONG!
    with patch("database.connect"):  # FORBIDDEN!
        pass

# 2. NEVER access os.environ directly  
def test_with_environ():
    os.environ["TEST_VAR"] = "value"  # WRONG!
    # Use IsolatedEnvironment instead

# 3. NEVER hardcode ports
def test_with_hardcoded_port():
    client = HttpClient("localhost:5432")  # WRONG!
    # Use TEST_PORTS constants

# 4. NEVER skip WebSocket events in agent tests
async def test_agent_without_events():
    result = await agent.execute()  # WRONG!
    # Must verify all 5 WebSocket events

# 5. NEVER create random test files
# BAD: fix_test_issues.py, temp_test.py
# GOOD: test_framework/utilities.py

# 6. NEVER mix test categories
@pytest.mark.unit
@pytest.mark.e2e  # WRONG! Pick one!
def test_confused_category():
    pass

# 7. NEVER use sleep for synchronization
async def test_with_sleep():
    await asyncio.sleep(5)  # WRONG!
    # Use proper wait conditions

# 8. NEVER ignore test failures
@pytest.mark.skip("Failing sometimes")  # WRONG!
def test_flaky():
    # Fix the test, don't skip it!
    pass
```

### ✅ CORRECT Patterns

```python
# 1. Use real services in integration/E2E
@pytest.mark.integration
async def test_with_real_services(real_services_fixture):
    # Real database, real Redis, real APIs
    pass

# 2. Use IsolatedEnvironment
def test_with_isolated_env(isolated_env):
    isolated_env.set("TEST_VAR", "value", source="test")

# 3. Use configuration constants
from test_framework.test_config import TEST_PORTS
client = HttpClient(f"localhost:{TEST_PORTS['postgresql']}")

# 4. Verify WebSocket events
async def test_agent_with_events(websocket_client):
    events = await execute_and_collect_events()
    assert_websocket_events(events, ALL_FIVE_EVENTS)

# 5. Use proper test organization
# test_framework/shared_utility.py - Shared code
# netra_backend/tests/integration/test_feature.py - Tests

# 6. Clear test categorization
@pytest.mark.integration  # One category
async def test_database_operation():
    pass

# 7. Use proper wait conditions
async def test_with_wait():
    await wait_for_condition(
        lambda: service.is_ready(),
        timeout=10,
        interval=0.5
    )

# 8. Fix flaky tests
@pytest.mark.integration
@pytest.mark.flaky(reruns=3)  # Temporary while fixing
async def test_being_fixed():
    # Document why it's flaky and fix plan
    pass
```

## Examples & Patterns

### Example 1: Complete Integration Test

```python
"""
Test User Thread Management

Business Value Justification (BVJ):
- Segment: All
- Business Goal: Enable conversation continuity
- Value Impact: Users can maintain context across sessions
- Strategic Impact: Core chat functionality
"""

import pytest
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.models import User, Thread

class TestThreadManagement(BaseIntegrationTest):
    """Test thread management with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_create_and_retrieve_thread(self, real_services_fixture):
        """Test thread creation and retrieval with real database."""
        # Setup
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create user
        user = User(email="test@example.com", name="Test User")
        db.add(user)
        await db.commit()
        
        # Create thread
        thread = Thread(
            user_id=user.id,
            title="Cost Optimization Discussion"
        )
        db.add(thread)
        await db.commit()
        
        # Cache in Redis
        await redis.set(f"thread:{thread.id}", thread.to_json())
        
        # Retrieve and verify
        cached_thread = await redis.get(f"thread:{thread.id}")
        assert cached_thread is not None
        
        db_thread = await db.get(Thread, thread.id)
        assert db_thread.title == "Cost Optimization Discussion"
        assert db_thread.user_id == user.id
```

### Example 2: Complete E2E Test

```python
"""
Test Complete Agent Optimization Flow

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise
- Business Goal: Deliver optimization insights
- Value Impact: Users receive actionable cost savings
- Strategic Impact: Core value proposition
"""

import pytest
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient

class TestAgentOptimizationE2E(BaseE2ETest):
    """Test complete agent optimization flow."""
    
    @pytest.mark.e2e
    @pytest.mark.real_llm
    @pytest.mark.mission_critical
    async def test_cost_optimization_flow(self, real_services, real_llm):
        """Test complete cost optimization with real LLM."""
        # Create real user
        user = await self.create_test_user(
            email="enterprise@example.com",
            subscription="enterprise"
        )
        
        # Connect WebSocket
        async with WebSocketTestClient(
            token=user.token,
            base_url=real_services["backend_url"]
        ) as client:
            
            # Send optimization request
            await client.send_json({
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": "Analyze my AWS costs for last month",
                "context": {
                    "aws_account_id": "123456789",
                    "monthly_spend": 50000
                }
            })
            
            # Collect all events
            events = []
            async for event in client.receive_events(timeout=60):
                events.append(event)
                if event["type"] == "agent_completed":
                    break
            
            # Verify all critical events sent
            event_types = [e["type"] for e in events]
            assert "agent_started" in event_types
            assert "agent_thinking" in event_types
            assert "tool_executing" in event_types
            assert "tool_completed" in event_types
            assert "agent_completed" in event_types
            
            # Verify business value delivered
            final_event = events[-1]
            assert final_event["type"] == "agent_completed"
            
            result = final_event["data"]["result"]
            assert "recommendations" in result
            assert len(result["recommendations"]) > 0
            assert "potential_savings" in result
            assert result["potential_savings"]["monthly_amount"] > 0
            
            # Verify data persistence
            thread_id = final_event["data"]["thread_id"]
            thread = await self.get_thread(thread_id)
            assert thread is not None
            assert len(thread.messages) > 0
```

### Example 3: Mission Critical Test

```python
"""
Test WebSocket Event Delivery

MISSION CRITICAL: Without these events, chat has no value!
"""

import pytest
from tests.mission_critical.base import MissionCriticalTest

class TestWebSocketEventDelivery(MissionCriticalTest):
    """Ensure WebSocket events are always delivered."""
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip  # NEVER skip this
    async def test_all_five_events_sent(self):
        """All 5 events MUST be sent for every agent execution."""
        # This test MUST pass or deployment is blocked
        
        result = await self.execute_agent_with_monitoring(
            agent="triage_agent",
            message="Simple test query"
        )
        
        # These assertions are NON-NEGOTIABLE
        assert result.events["agent_started"] > 0
        assert result.events["agent_thinking"] > 0  
        assert result.events["tool_executing"] >= 0  # May be 0 for simple queries
        assert result.events["tool_completed"] >= 0  # May be 0 for simple queries
        assert result.events["agent_completed"] > 0
        
        # Verify events in correct order
        assert result.event_order == [
            "agent_started",
            "agent_thinking",
            # tool events optional in middle
            "agent_completed"
        ]
```

## Troubleshooting

### Common Issues & Solutions

#### 1. Docker Containers Won't Start

```bash
# Solution: Use unified Docker manager's cleanup
python scripts/docker_manual.py clean
python scripts/docker_manual.py start

# Or let test runner handle it
python tests/unified_test_runner.py --real-services --force-recreate
```

#### 2. Port Conflicts

```bash
# Check what's using the port
lsof -i :5434  # macOS/Linux
netstat -ano | findstr :5434  # Windows

# Solution: Stop conflicting service or use dynamic ports
python tests/unified_test_runner.py --dynamic-ports
```

#### 3. Test Failures in CI but Pass Locally

```python
# Add environment detection
import pytest
from shared.isolated_environment import get_env

@pytest.mark.skipif(
    get_env().get("CI") == "true" and not has_llm_credentials(),
    reason="LLM credentials not available in CI"
)
async def test_requiring_llm():
    pass
```

#### 4. Flaky WebSocket Tests

```python
# Use proper retry and wait strategies
from test_framework.websocket_helpers import wait_for_websocket_ready

async def test_websocket():
    async with WebSocketTestClient() as client:
        await wait_for_websocket_ready(client)  # Wait for connection
        # Now safe to send messages
```

#### 5. Database State Pollution

```python
# Use proper cleanup in fixtures
@pytest.fixture
async def clean_database(real_db):
    """Ensure clean database state."""
    yield real_db
    # Cleanup after test
    await real_db.execute("TRUNCATE users CASCADE")
    await real_db.commit()
```

## Quick Reference Card

```bash
# Most Common Commands
python tests/unified_test_runner.py --category integration  # Run integration tests
python tests/unified_test_runner.py --real-services        # With Docker
python tests/unified_test_runner.py --execution-mode fast_feedback  # Quick validation
python tests/mission_critical/test_websocket_agent_events_suite.py  # Critical tests

# Test Markers
@pytest.mark.unit          # No infrastructure needed
@pytest.mark.integration   # Needs database/Redis
@pytest.mark.e2e          # Full stack required
@pytest.mark.real_services # Needs Docker
@pytest.mark.real_llm     # Needs LLM API
@pytest.mark.mission_critical  # MUST pass

# Key Imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestClient
from shared.isolated_environment import get_env
```

## Final Checklist

Before submitting your test:

- [ ] Test follows naming convention: `test_*.py`
- [ ] Test is in correct category directory
- [ ] Test has BVJ (Business Value Justification) comment
- [ ] Test uses real services (not mocks) where possible
- [ ] Test uses IsolatedEnvironment (not os.environ)
- [ ] Test uses SSOT utilities from test_framework/
- [ ] Test verifies WebSocket events (if testing agents)
- [ ] Test has proper pytest markers
- [ ] Test passes with `--real-services` flag
- [ ] Test is added to appropriate test suite

## Remember

**The point of tests is to ensure the REAL SYSTEM delivers BUSINESS VALUE.**

Every test should validate that our platform helps users optimize their AI operations. If a test doesn't connect to that goal, it shouldn't exist.

---

*Last Updated: 2024*
*Authoritative Guide - Supersedes all other test documentation*