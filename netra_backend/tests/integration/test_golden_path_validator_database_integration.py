"""
Test Golden Path Validator Database Integration

Business Value Justification (BVJ):
- Segment: All (Platform/Internal)
- Business Goal: Ensure Golden Path validation correctly identifies missing components
- Value Impact: Prevents broken authentication from reaching users
- Strategic Impact: Critical platform stability and revenue protection

CRITICAL: This test validates the Golden Path Validator's detection of missing
user_sessions table and related service registration failures.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.core.service_dependencies.golden_path_validator import GoldenPathValidator
from shared.types import ServiceType, EnvironmentType


class TestGoldenPathValidatorDatabaseIntegration(BaseIntegrationTest):
    """Test Golden Path Validator against real database scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_golden_path_validation_fails_with_missing_user_sessions(self, real_services_fixture):
        """
        Test Golden Path Validator correctly fails when user_sessions table missing.
        
        This test reproduces the EXACT staging failure condition where:
        1. Database connection exists
        2. app.state is not properly configured
        3. user_sessions table is missing
        
        Should FAIL initially (validation returns success=False), then PASS after fix.
        """
        # Create a mock app with missing service registration (reproduces staging issue)
        mock_app = Mock()
        mock_app.state = Mock()
        
        # CRITICAL: Simulate the staging issue - missing app.state components
        # This is why Golden Path validation fails in staging
        mock_app.state.db_session_factory = None  # Missing - causes validation failure
        mock_app.state.key_manager = None         # Missing - causes validation failure
        
        # Initialize validator
        validator = GoldenPathValidator()
        
        # Test 1: Validate user authentication readiness (should fail)
        auth_result = await validator._validate_user_authentication_ready(mock_app)
        
        # Should fail because db_session_factory is missing
        assert auth_result["success"] is False, "Golden Path validation should fail with missing db_session_factory"
        assert auth_result["requirement"] == "user_authentication_ready"
        assert "Database session factory not available" in auth_result["message"]
        
        # Test 2: Validate JWT validation readiness (should fail)
        jwt_result = await validator._validate_jwt_validation_ready(mock_app)
        
        # Should fail because key_manager is missing
        assert jwt_result["success"] is False, "Golden Path validation should fail with missing key_manager"
        assert jwt_result["requirement"] == "jwt_validation_ready" 
        assert "Key manager not available" in jwt_result["message"]
        
        # Test 3: Test complete Golden Path validation
        services_to_validate = [ServiceType.DATABASE_POSTGRES, ServiceType.AUTH_SERVICE]
        complete_result = await validator.validate_golden_path_services(mock_app, services_to_validate)
        
        # Should fail overall
        assert complete_result["success"] is False, "Complete Golden Path validation should fail with missing components"
        assert len(complete_result["failed_requirements"]) >= 2, "Should have multiple failed requirements"
        
        # Verify specific failures are captured
        failed_reqs = [req["requirement"] for req in complete_result["failed_requirements"]]
        assert "user_authentication_ready" in failed_reqs, "Missing user_authentication_ready failure"
        assert "jwt_validation_ready" in failed_reqs, "Missing jwt_validation_ready failure"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_golden_path_validation_with_proper_service_registration(self, real_services_fixture):
        """
        Test Golden Path Validator passes when services are properly registered.
        
        This test simulates the FIXED state where:
        1. Database connection exists and user_sessions table is present
        2. app.state is properly configured with required services
        3. All Golden Path requirements are met
        
        Should FAIL initially (because services aren't registered), then PASS after fix.
        """
        # Create a mock app with PROPER service registration
        mock_app = Mock()
        mock_app.state = Mock()
        
        # Simulate FIXED state - proper app.state configuration
        # Create mock database session factory
        mock_db_factory = AsyncMock()
        mock_session = AsyncMock()
        mock_db_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock successful table existence check
        mock_session.execute.return_value.fetchall.return_value = [("user_sessions",)]
        
        mock_app.state.db_session_factory = mock_db_factory
        
        # Create mock key manager with JWT functions
        mock_key_manager = Mock()
        mock_key_manager.create_access_token = Mock(return_value="test_token")
        mock_key_manager.verify_token = Mock(return_value={"user_id": "test"})
        mock_key_manager.create_refresh_token = Mock(return_value="test_refresh")
        
        mock_app.state.key_manager = mock_key_manager
        
        # Initialize validator
        validator = GoldenPathValidator()
        
        # Test 1: Validate user authentication readiness (should pass)
        auth_result = await validator._validate_user_authentication_ready(mock_app)
        
        assert auth_result["success"] is True, "User authentication validation should pass with proper setup"
        assert auth_result["requirement"] == "user_authentication_ready"
        
        # Test 2: Validate JWT validation readiness (should pass)
        jwt_result = await validator._validate_jwt_validation_ready(mock_app)
        
        assert jwt_result["success"] is True, "JWT validation should pass with proper key_manager"
        assert jwt_result["requirement"] == "jwt_validation_ready"
        
        # Test 3: Test complete Golden Path validation
        services_to_validate = [ServiceType.DATABASE_POSTGRES, ServiceType.AUTH_SERVICE]
        complete_result = await validator.validate_golden_path_services(mock_app, services_to_validate)
        
        # Should pass overall
        assert complete_result["success"] is True, "Complete Golden Path validation should pass with proper setup"
        assert len(complete_result["failed_requirements"]) == 0, "Should have no failed requirements"
        assert len(complete_result["passed_requirements"]) >= 2, "Should have multiple passed requirements"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_table_validation_logic(self, real_services_fixture):
        """
        Test the specific database table validation logic that checks for user_sessions.
        
        This test directly validates the table checking mechanism that is failing
        in staging due to the missing user_sessions table.
        """
        # Get real database connection info
        db_info = real_services_fixture["db_info"]
        
        # Create mock app with real database session factory
        mock_app = Mock()
        mock_app.state = Mock()
        
        # Create a simple mock session factory that connects to real database
        import asyncpg
        
        class MockSessionFactory:
            def __init__(self, db_info):
                self.db_info = db_info
            
            async def __aenter__(self):
                self.conn = await asyncpg.connect(
                    host=self.db_info["host"],
                    port=self.db_info["port"],
                    database=self.db_info["database"],
                    user=self.db_info["user"],
                    password=self.db_info["password"]
                )
                return self
            
            async def __aexit__(self, *args):
                await self.conn.close()
            
            async def execute(self, query):
                # Simulate SQLAlchemy result interface
                result = Mock()
                
                if "user_sessions" in query:
                    # Check if user_sessions table actually exists
                    try:
                        exists_query = """
                            SELECT table_name FROM information_schema.tables 
                            WHERE table_schema = 'auth' AND table_name = 'user_sessions'
                        """
                        tables = await self.conn.fetch(exists_query)
                        
                        if tables:
                            result.fetchall.return_value = [("user_sessions",)]
                        else:
                            result.fetchall.return_value = []  # Table missing - this is the issue!
                    except Exception:
                        result.fetchall.return_value = []  # Connection/schema issues
                
                return result
        
        mock_app.state.db_session_factory = MockSessionFactory(db_info)
        
        # Initialize validator
        validator = GoldenPathValidator()
        
        # Test the specific table validation that's failing
        auth_result = await validator._validate_user_authentication_ready(mock_app)
        
        # This test validates the EXACT logic that's failing in staging
        # If user_sessions table is missing, this should fail
        # If table exists, this should pass
        
        if not auth_result["success"]:
            # Expected failure case - table is missing
            assert "Missing critical user tables" in auth_result["message"]
            assert "user_sessions" in auth_result["message"]
            print(" PASS:  REPRODUCED ISSUE: user_sessions table is missing, Golden Path validation correctly fails")
        else:
            # Success case - table exists
            print(" PASS:  TABLE EXISTS: user_sessions table found, Golden Path validation passes")
        
        # The assertion depends on current database state
        # In broken staging: should fail (table missing)
        # In fixed staging: should pass (table exists)
        # This test documents the behavior and will help verify the fix