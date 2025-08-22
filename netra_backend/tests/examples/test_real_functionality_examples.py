"""
Real Functionality Testing Examples

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Platform/Internal - All tiers benefit from quality test examples
2. **Business Goal**: Accelerate development with proven test patterns
3. **Value Impact**: Reduces time to write quality tests, improves test reliability
4. **Revenue Impact**: Better tests = fewer bugs = higher customer satisfaction
5. **Platform Stability**: Examples prevent copy-paste of bad test patterns

This file demonstrates the correct way to write tests that test REAL functionality
instead of mocks. Use these patterns as templates for new tests.

Examples include:
- Proper unit test with minimal mocking
- Integration test using real child components  
- E2E test with real backend
- Correct external API mocking techniques

All examples follow CLAUDE.md requirements: ≤8 lines per function, ≤300 lines per file.
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest
from database.database_manager import get_database_session
from logging_config import central_logger

from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.models.thread import Thread

# Add project root to path
# Real imports - not mocked unless external API
from netra_backend.app.models.user import User
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.services.user_service import UserService
from netra_backend.app.websocket.connection import ConnectionInfo

logger = central_logger.get_logger(__name__)


# =============================================================================
# UNIT TEST EXAMPLE - Minimal Mocking
# =============================================================================

class TestUnitTestMinimalMocking:
    """Example of proper unit tests with minimal mocking.
    
    GOOD PATTERNS:
    - Test individual functions with real implementations
    - Mock only external APIs (database, HTTP requests)
    - Test actual logic, not mocks
    - Keep functions ≤8 lines
    """
    
    def test_user_validation_real_logic(self):
        """Test real user validation logic, not mocks."""
        user = User(email="test@example.com", name="Test User")
        # Tests the actual validation logic in User class
        assert user.is_valid_email()
        assert user.get_display_name() == "Test User"
    
    def test_thread_creation_with_real_data(self):
        """Test thread creation with real data structures."""
        thread = Thread(title="Test Thread", user_id=123)
        thread.add_message("Hello world", "user")
        # Tests real Thread methods
        assert len(thread.messages) == 1
        assert thread.get_latest_message().content == "Hello world"
    
    @pytest.mark.asyncio
    @patch('app.database.database_manager.get_session')
    async def test_user_service_with_mocked_db(self, mock_db):
        """Example: Mock external database, test real service logic."""
        # Mock ONLY the external database dependency
        mock_session = AsyncMock()
        mock_db.return_value = mock_session
        
        service = UserService()  # Real service instance
        result = await service.create_user("test@example.com", "Test")
        # Test real service behavior with mocked external dependency
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


# =============================================================================
# INTEGRATION TEST EXAMPLE - Real Child Components
# =============================================================================

class TestIntegrationRealComponents:
    """Example of integration tests using real child components.
    
    GOOD PATTERNS:
    - Use real child components, not mocks
    - Mock only external APIs
    - Test actual component interaction
    - Verify real data flow
    """
    
    @pytest.mark.asyncio
    @patch('app.services.external_api.make_request')
    async def test_thread_service_integration(self, mock_api):
        """Integration test with real components, mocked external API only."""
        # Mock ONLY external API
        mock_api.return_value = {"status": "success"}
        
        # Use REAL services - no mocking internal components
        user_service = UserService()
        thread_service = ThreadService()
        
        # Test real integration between services
        user = await user_service.create_user("test@example.com", "Test")
        thread = await thread_service.create_thread(user.id, "Test Thread")
        
        assert thread.user_id == user.id
        assert thread.title == "Test Thread"
    
    @pytest.mark.asyncio
    @patch('app.database.database_manager.get_session')
    async def test_websocket_message_flow_integration(self, mock_db):
        """Test WebSocket message handling with real components."""
        # Mock database only
        mock_session = AsyncMock()
        mock_db.return_value = mock_session
        
        # Real WebSocket components - no mocking
        connection = ConnectionInfo(user_id=123, session_id="test")
        message_handler = MessageHandler()  # Real handler
        
        # Test real integration
        result = await message_handler.process_message(connection, {
            "type": "thread_message",
            "content": "Hello world"
        })
        
        assert result["status"] == "success"
        mock_session.add.assert_called()


# =============================================================================
# E2E TEST EXAMPLE - Real Backend
# =============================================================================

class TestE2ERealBackend:
    """Example of E2E tests with real backend services.
    
    GOOD PATTERNS:
    - Use real database (test database)
    - Use real agent system
    - Mock only external third-party APIs
    - Test complete user journeys
    """
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @patch('app.agents.external.openai_client.make_request')
    async def test_complete_agent_workflow_e2e(self, mock_openai):
        """E2E test of complete agent workflow with real backend."""
        # Mock ONLY external LLM API
        mock_openai.return_value = {
            "choices": [{"message": {"content": "AI response"}}]
        }
        
        # Use REAL backend components
        async with get_database_session() as session:
            user = User(email="test@example.com", name="Test")
            session.add(user)
            await session.commit()
            
            # Real agent system - no mocking
            agent = SupervisorAgent()  # Real agent
            
            result = await agent.process_message(
                user_id=user.id,
                message="Analyze my AI costs"
            )
            
            # Verify real end-to-end flow
            assert result.status == "completed"
            assert "cost analysis" in result.response.lower()
            mock_openai.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.integration  
    async def test_user_thread_creation_e2e(self):
        """E2E test of user creating thread with no external APIs."""
        # No mocking needed - pure internal functionality
        async with get_database_session() as session:
            user_service = UserService()
            thread_service = ThreadService()
            
            # Complete real workflow
            user = await user_service.create_user("test@example.com", "Test")
            thread = await thread_service.create_thread(user.id, "My Thread")
            message = await thread_service.add_message(thread.id, "Hello")
            
            # Verify real data persistence
            assert thread.user_id == user.id
            assert message.thread_id == thread.id


# =============================================================================
# EXTERNAL API MOCKING EXAMPLES - Correct Techniques
# =============================================================================

class TestExternalAPIMocking:
    """Examples of correctly mocking external APIs.
    
    GOOD PATTERNS:
    - Mock at the boundary (HTTP clients, database connections)
    - Keep mock behavior realistic
    - Test error handling with mocks
    - Use real internal logic
    """
    
    @pytest.mark.asyncio
    @patch('app.services.openai_service.OpenAIClient.chat_completion')
    async def test_llm_response_handling(self, mock_openai):
        """Mock external LLM API, test real response handling."""
        # Realistic mock response
        mock_openai.return_value = {
            "id": "chatcmpl-123",
            "choices": [{
                "message": {"role": "assistant", "content": "Cost is $100/month"}
            }],
            "usage": {"total_tokens": 50}
        }
        
        # Real agent logic
        agent = CostAnalysisAgent()  # Real agent, not mocked
        result = await agent.analyze_costs({"monthly_requests": 1000})
        
        # Test real processing of mocked API response
        assert "100" in result.analysis
        assert result.confidence > 0.8
    
    @pytest.mark.asyncio
    @patch('app.database.clickhouse.ClickHouseClient.execute')
    async def test_analytics_query_with_mocked_db(self, mock_clickhouse):
        """Mock external ClickHouse, test real analytics logic."""
        # Realistic mock data
        mock_clickhouse.return_value = [
            {"date": "2025-01-01", "cost": 10.50, "requests": 100},
            {"date": "2025-01-02", "cost": 12.30, "requests": 120}
        ]
        
        # Real analytics service
        analytics = AnalyticsService()  # Real service
        report = await analytics.generate_cost_report("2025-01")
        
        # Test real calculation logic
        assert report.total_cost == 22.80
        assert report.avg_cost_per_request == 0.1036
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_webhook_delivery_with_error_handling(self, mock_http):
        """Test real error handling with mocked HTTP failures."""
        # Mock HTTP failure
        mock_http.side_effect = Exception("Connection timeout")
        
        # Real webhook service
        webhook_service = WebhookService()  # Real service
        
        # Test real error handling logic
        result = await webhook_service.send_notification({
            "event": "thread_created",
            "thread_id": 123
        })
        
        assert result.success is False
        assert "timeout" in result.error_message.lower()


# =============================================================================
# ANTI-PATTERN EXAMPLES - What NOT to Do
# =============================================================================

class TestAntiPatternsWhatNotToDo:
    """Examples of BAD test patterns - for educational purposes only.
    
    These are ANTI-PATTERNS that violate real test requirements.
    DO NOT use these patterns in actual tests.
    """
    
    def test_example_of_circular_testing_antipattern(self):
        """❌ BAD: Tests the mock instead of real functionality."""
        # This is an ANTI-PATTERN example - don't do this!
        
        # BAD: Creating mock implementation inside test
        class MockUserService:
            def create_user(self, email, name):
                return {"id": 123, "email": email, "name": name}
        
        # BAD: Testing the mock we just created
        mock_service = MockUserService()
        result = mock_service.create_user("test@example.com", "Test")
        
        # This assertion tests our mock, not the real UserService!
        assert result["email"] == "test@example.com"
        # This test provides ZERO confidence about real functionality
    
    def test_example_of_excessive_mocking_antipattern(self):
        """❌ BAD: Mocking everything including internal components."""
        # This is an ANTI-PATTERN example - don't do this!
        
        # BAD: Mocking internal components (>30% of imports)
        with patch('app.models.user.User'), \
             patch('app.models.thread.Thread'), \
             patch('app.services.user_service.UserService'), \
             patch('app.services.thread_service.ThreadService'), \
             patch('app.utils.validation.validate_email'), \
             patch('app.utils.formatting.format_name'):
            
            # With everything mocked, this test tells us nothing
            # about whether the real system works
            pass
    
    def test_example_of_integration_without_integration(self):
        """❌ BAD: Integration test that mocks all children."""
        # This is an ANTI-PATTERN example - don't do this!
        
        # BAD: Integration test with all components mocked
        with patch('app.services.user_service.UserService'), \
             patch('app.services.thread_service.ThreadService'), \
             patch('app.models.user.User'), \
             patch('app.models.thread.Thread'):
            
            # This isn't testing integration at all!
            # All components are mocked, so no real interaction is tested
            pass


# =============================================================================
# HELPER FUNCTIONS - Real Utilities for Testing
# =============================================================================

def create_test_user(**kwargs) -> User:
    """Helper to create test user with real User class."""
    defaults = {
        "email": "test@example.com",
        "name": "Test User"
    }
    defaults.update(kwargs)
    return User(**defaults)

def create_test_thread(user_id: int, **kwargs) -> Thread:
    """Helper to create test thread with real Thread class."""
    defaults = {
        "title": "Test Thread",
        "user_id": user_id
    }
    defaults.update(kwargs)
    return Thread(**defaults)

async def setup_test_data() -> Dict[str, Any]:
    """Setup real test data for integration tests."""
    async with get_database_session() as session:
        user = create_test_user()
        session.add(user)
        await session.commit()
        
        thread = create_test_thread(user.id)
        session.add(thread)
        await session.commit()
        
        return {
            "user": user,
            "thread": thread,
            "session": session
        }


# =============================================================================
# FIXTURES - Real Data Factories
# =============================================================================

@pytest.fixture
async def real_user():
    """Fixture providing real User instance."""
    return create_test_user(email="fixture@example.com")

@pytest.fixture
async def real_thread_with_user():
    """Fixture providing real Thread with real User."""
    user = create_test_user()
    thread = create_test_thread(user.id)
    return {"user": user, "thread": thread}

@pytest.fixture
async def database_session():
    """Fixture providing real database session for E2E tests."""
    async with get_database_session() as session:
        yield session
        # Cleanup happens automatically with async context manager


# =============================================================================
# SUMMARY COMMENTS
# =============================================================================

"""
KEY TAKEAWAYS FROM THESE EXAMPLES:

✅ GOOD PATTERNS:
1. Mock only external APIs (HTTP, database, third-party services)  
2. Use real internal components (services, models, utilities)
3. Test actual business logic, not mock behavior
4. Keep functions ≤8 lines per CLAUDE.md requirements
5. Integration tests use real child components
6. E2E tests use real backend with test database

❌ BAD PATTERNS TO AVOID:
1. Creating mock components inside test files
2. Mocking more than 30% of imports
3. Integration tests that mock all children
4. Testing mock behavior instead of real functionality
5. Circular testing (test creates mock, then tests the mock)

🔧 ENFORCEMENT:
- Run: python scripts/compliance/real_test_linter.py
- Linter will flag violations and suggest fixes
- Integrate into CI/CD to prevent regressions

📚 REFERENCES:
- SPEC/testing.xml - Real test requirements specification
- SPEC/learnings/real_test_requirements.xml - Detailed guidance
- CLAUDE.md - Function/file size limits (8 lines/300 lines)

Use these patterns as templates when writing new tests!
"""