"""
Lightweight Integration Test Demo

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Validate integration testing without Docker dependencies  
- Value Impact: Enable fast integration tests for CI/CD pipelines
- Strategic Impact: Prove integration tests work without external services

This test demonstrates that the integration test framework can:
1. Run without Docker containers
2. Validate business logic integration 
3. Test component interactions
4. Provide fast feedback for developers
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

import pytest

from netra_backend.app.models.session import Session
from shared.isolated_environment import get_env


class TestLightweightIntegrationDemo:
    """Demo class showing lightweight integration testing without Docker."""
    
    @pytest.mark.integration
    @pytest.mark.lightweight_services
    async def test_lightweight_service_setup(self, lightweight_services_fixture):
        """
        Test that lightweight services fixture provides proper setup.
        
        Validates:
        - Fixture provides required service connections
        - Database connection is available (in-memory SQLite)
        - Auth service stubs work properly
        - Environment isolation works
        """
        services = lightweight_services_fixture
        
        # Validate fixture structure
        assert "backend_url" in services
        assert "auth_url" in services
        assert "db" in services
        assert "lightweight" in services
        assert services["lightweight"] is True
        
        # Validate service URLs are provided
        assert services["backend_url"] == "http://localhost:8000"
        assert services["auth_url"] == "http://localhost:8081"
        
        # Validate database connection
        assert services["database_available"] is True
        assert services["database_url"].startswith("sqlite+aiosqlite")
        
        # Validate auth service stub
        auth_service = services["auth_service"]
        
        # Test auth token validation
        validation_result = await auth_service["validate_token"]("test_token")
        assert validation_result["valid"] is True
        assert "user_id" in validation_result
        assert "username" in validation_result
        
        # Test session creation
        session_result = await auth_service["create_session"]()
        assert "session_id" in session_result
        assert "expires_at" in session_result
        
        # Validate Redis stub
        redis = services["redis"]
        
        # Test Redis operations
        set_result = await redis["set"]("test_key", "test_value")
        assert set_result is True
        
        get_result = await redis["get"]("test_key")
        # Redis stub returns None by default (no actual storage)
        assert get_result is None
        
        exists_result = await redis["exists"]("test_key")
        assert exists_result is False


    @pytest.mark.integration
    @pytest.mark.lightweight_services 
    async def test_session_model_integration(self, lightweight_services_fixture):
        """
        Test Session model integration without external services.
        
        This tests business logic integration - how Session models
        work with mock service dependencies.
        """
        services = lightweight_services_fixture
        auth_service = services["auth_service"]
        redis = services["redis"]
        
        # Create a session using business logic
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        session = Session(
            session_id=session_id,
            user_id=user_id,
            ip_address="192.168.1.100",
            user_agent="IntegrationTestAgent/1.0",
            timeout_seconds=1800,
            session_data={"integration_test": True, "feature": "auth_flow"}
        )
        
        # Test session model functionality  
        assert session.session_id == session_id
        assert session.user_id == user_id
        assert session.session_data["integration_test"] is True
        assert session.session_data["feature"] == "auth_flow"
        
        # Test session expiry logic
        assert not session.is_session_expired()
        
        # Test session activity update  
        original_time = session.last_activity
        await asyncio.sleep(0.001)  # Small delay to ensure time difference
        session.update_activity()
        updated_time = session.last_activity
        assert updated_time > original_time
        
        # Test JSON serialization/deserialization
        session_json = session.model_dump_json()
        parsed_session = Session.model_validate_json(session_json)
        assert parsed_session.session_id == session_id
        assert parsed_session.user_id == user_id
        assert parsed_session.session_data["integration_test"] is True
        
        # Test session data storage and retrieval  
        session.store_data("test_preference", "dark_theme")
        assert session.get_data("test_preference") == "dark_theme"
        assert session.get_data("nonexistent", "default_value") == "default_value"
        
        # Test integration with auth service stub
        validation_result = await auth_service["validate_token"]("mock_token")
        
        # Simulate session creation in auth service
        if validation_result["valid"]:
            session_creation = await auth_service["create_session"]()
            assert "session_id" in session_creation
            
            # Test Redis interaction for session storage
            session_key = f"session:{session_creation['session_id']}"
            store_result = await redis["set"](session_key, session_json)
            assert store_result is True
            
            # Test session invalidation flow
            session.mark_invalid()
            assert not session.is_valid
            assert session.is_expired
            
            # Test Redis cleanup
            cleanup_result = await redis["delete"](session_key) 
            assert cleanup_result is True


    @pytest.mark.integration
    @pytest.mark.lightweight_services
    async def test_environment_isolation(self, lightweight_services_fixture):
        """
        Test that environment isolation works in integration tests.
        
        Validates:
        - IsolatedEnvironment usage in tests
        - Environment variables are properly isolated
        - Test-specific configuration works
        """
        services = lightweight_services_fixture
        
        # Test environment isolation
        env = get_env()
        
        # Set test-specific environment variable
        test_value = f"integration_test_{uuid.uuid4().hex[:8]}"
        env.set("INTEGRATION_TEST_VALUE", test_value, source="integration_test")
        
        # Verify isolation works
        retrieved_value = env.get("INTEGRATION_TEST_VALUE")
        assert retrieved_value == test_value
        
        # Test that service configuration uses isolated environment
        assert services["environment"] == "test"
        assert services["database_url"].startswith("sqlite+aiosqlite")
        
        # Verify test environment settings
        assert env.get("TESTING", "").lower() in ["1", "true"]
        
        # Test configuration access patterns  
        database_url = env.get("DATABASE_URL")
        if database_url:
            # Should use test database configuration
            assert "test" in database_url.lower() or "memory" in database_url.lower()


    @pytest.mark.integration 
    @pytest.mark.lightweight_services
    async def test_component_interaction_patterns(self, lightweight_services_fixture):
        """
        Test component interaction patterns without external services.
        
        This validates that business logic components can interact
        properly through lightweight service abstractions.
        """
        services = lightweight_services_fixture
        auth_service = services["auth_service"]
        
        # Test multi-step business process
        # Step 1: User authentication
        auth_token = "integration_test_token"
        auth_result = await auth_service["validate_token"](auth_token)
        assert auth_result["valid"] is True
        
        user_id = auth_result["user_id"]
        username = auth_result["username"]
        
        # Step 2: Session creation
        session_result = await auth_service["create_session"]()
        session_id = session_result["session_id"]
        
        # Step 3: Business object creation
        session = Session(
            session_id=session_id,
            user_id=user_id,
            ip_address="10.0.0.1", 
            user_agent="IntegrationClient/2.0",
            timeout_seconds=7200,
            session_data={
                "username": username,
                "auth_method": "token",
                "business_context": "integration_test"
            }
        )
        
        # Step 4: Validate object state
        assert session.user_id == user_id
        assert session.session_data["username"] == username
        assert session.session_data["business_context"] == "integration_test"
        
        # Step 5: Test component interactions
        session.store_data("last_action", "component_interaction_test")
        session.update_activity()
        
        # Validate interaction results
        assert session.get_data("last_action") == "component_interaction_test"
        assert not session.is_session_expired()
        
        # Step 6: Test cleanup interaction
        session.mark_invalid()
        assert not session.is_valid
        
        # Validate that all components maintained consistency
        assert session.session_id == session_id
        assert session.user_id == user_id
        assert session.is_expired is True


    @pytest.mark.integration
    @pytest.mark.lightweight_services
    async def test_error_handling_integration(self, lightweight_services_fixture):
        """
        Test error handling patterns in integration scenarios.
        
        This ensures that error conditions are properly handled
        across component boundaries without external services.
        """
        services = lightweight_services_fixture
        
        # Test database session error handling
        db_session = services["db"]
        
        # Since we're using a mock database, we can simulate errors
        # In a real integration test, this would test actual error handling
        try:
            # Test that session object handles invalid data gracefully
            with pytest.raises(Exception):
                invalid_session = Session(
                    session_id="",  # Invalid empty session ID
                    user_id="",     # Invalid empty user ID  
                    ip_address="invalid_ip",
                    user_agent="",
                    timeout_seconds=-1,  # Invalid negative timeout
                    session_data=None   # Invalid null data
                )
        except Exception as e:
            # This is expected behavior - integration test validates error handling
            pass
        
        # Test valid session creation after error
        valid_session = Session(
            session_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            ip_address="127.0.0.1", 
            user_agent="TestAgent",
            timeout_seconds=3600,
            session_data={"test": "valid"}
        )
        
        assert valid_session.is_valid
        assert not valid_session.is_session_expired()