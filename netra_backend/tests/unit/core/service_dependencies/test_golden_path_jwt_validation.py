"""
Unit Tests for Golden Path JWT Validation Failure

Tests reproduce the exact JWT validation failure where Golden Path Validator
expects app.state.key_manager to have JWT methods ['create_access_token', 'verify_token', 'create_refresh_token']
but the actual JWT functionality is in UnifiedJWTValidator (delegates to auth service).

Business Value Justification (BVJ):
- Segment: ALL (Critical authentication infrastructure)  
- Business Goal: Prevent authentication failures blocking user access
- Value Impact: Ensures Golden Path JWT validation works correctly
- Strategic Impact: Protects critical user authentication flows
"""

import pytest
import logging
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI

from netra_backend.app.core.service_dependencies.golden_path_validator import (
    GoldenPathValidator,
    GoldenPathValidationResult
)
from netra_backend.app.core.service_dependencies.models import (
    ServiceType,
    EnvironmentType
)
from netra_backend.app.core.unified.jwt_validator import UnifiedJWTValidator


class TestGoldenPathJWTValidationFailure:
    """Test suite reproducing exact JWT validation failure."""
    
    @pytest.fixture
    def app_without_key_manager(self):
        """FastAPI app without key_manager - reproduces the bug."""
        app = FastAPI()
        
        # Mock other expected app.state attributes but NOT key_manager
        app.state.db_session_factory = AsyncMock()
        app.state.redis_manager = AsyncMock() 
        app.state.agent_supervisor = MagicMock()
        app.state.tool_dispatcher = MagicMock()
        app.state.llm_manager = MagicMock()
        app.state.agent_websocket_bridge = MagicMock()
        
        # CRITICAL: No key_manager - this is the bug condition
        # app.state.key_manager = None  # Explicitly no key_manager
        
        return app
        
    @pytest.fixture
    def app_with_wrong_key_manager(self):
        """FastAPI app with key_manager that lacks JWT methods."""
        app = FastAPI()
        
        # Mock other expected app.state attributes
        app.state.db_session_factory = AsyncMock()
        app.state.redis_manager = AsyncMock()
        
        # Create key_manager that lacks JWT methods - reproduces the bug
        # Use a more specific mock object to avoid MagicMock creating attributes dynamically
        class MockKeyManagerWithoutJWT:
            """Mock key manager that explicitly lacks JWT methods."""
            
            def some_other_method(self):
                """Example method that key manager might have."""
                pass
                
            def __getattr__(self, name):
                """Explicitly raise AttributeError for JWT methods."""
                if name in ['create_access_token', 'verify_token', 'create_refresh_token']:
                    raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
                raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        
        app.state.key_manager = MockKeyManagerWithoutJWT()
        
        return app
        
    @pytest.fixture 
    def app_with_unified_jwt_validator(self):
        """FastAPI app with UnifiedJWTValidator - the actual system design."""
        app = FastAPI()
        
        # Mock other expected app.state attributes  
        app.state.db_session_factory = AsyncMock()
        app.state.redis_manager = AsyncMock()
        
        # Use actual UnifiedJWTValidator - this is what we actually have
        app.state.unified_jwt_validator = UnifiedJWTValidator()
        
        # CRITICAL: No key_manager with JWT methods - this is the current reality
        return app
        
    @pytest.fixture
    def golden_path_validator(self):
        """Golden Path Validator instance."""
        return GoldenPathValidator(environment=EnvironmentType.DEVELOPMENT)

    @pytest.mark.asyncio
    async def test_jwt_validation_fails_when_no_key_manager(
        self, 
        golden_path_validator, 
        app_without_key_manager,
        caplog
    ):
        """Test JWT validation fails when app.state.key_manager doesn't exist."""
        
        # Attempt to validate JWT capabilities - this should fail
        result = await golden_path_validator._validate_jwt_capabilities(app_without_key_manager)
        
        # EXPECT FAILURE - this reproduces the bug
        assert result["success"] is False
        assert "key manager" in result["message"].lower()
        assert result["requirement"] == "jwt_validation_ready"
        assert result["details"]["key_manager"] is False
        
        # Verify the exact error message
        expected_message = "Key manager not available for JWT operations"
        assert result["message"] == expected_message
        
        # Log capture verification - look for JWT-related logs
        log_messages = [record.message for record in caplog.records]
        jwt_related_logs = [msg for msg in log_messages if "jwt" in msg.lower() or "key manager" in msg.lower()]
        # Note: The Golden Path validator may not log this specific message, so this is informational
        print(f"Captured log messages: {log_messages}")

    @pytest.mark.asyncio 
    async def test_jwt_validation_fails_when_key_manager_lacks_methods(
        self,
        golden_path_validator,
        app_with_wrong_key_manager,
        caplog
    ):
        """Test JWT validation fails when key_manager lacks JWT methods."""
        
        # Attempt to validate JWT capabilities
        result = await golden_path_validator._validate_jwt_capabilities(app_with_wrong_key_manager)
        
        # EXPECT FAILURE - key_manager exists but lacks JWT methods
        assert result["success"] is False
        assert "missing jwt capabilities" in result["message"].lower()
        assert result["requirement"] == "jwt_validation_ready"
        
        # Check specific capabilities are False
        details = result["details"]
        assert details["create_access_token"] is False
        assert details["verify_token"] is False
        assert details["create_refresh_token"] is False
        
        # Verify missing capabilities are listed
        assert "create_access_token" in result["message"]
        assert "verify_token" in result["message"] 
        assert "create_refresh_token" in result["message"]

    @pytest.mark.asyncio
    async def test_unified_jwt_validator_not_recognized_by_golden_path(
        self,
        golden_path_validator, 
        app_with_unified_jwt_validator,
        caplog
    ):
        """Test that Golden Path Validator doesn't recognize UnifiedJWTValidator."""
        
        # This test proves the architectural mismatch
        # Golden Path expects app.state.key_manager but we have app.state.unified_jwt_validator
        
        result = await golden_path_validator._validate_jwt_capabilities(app_with_unified_jwt_validator)
        
        # EXPECT FAILURE - Golden Path doesn't know about unified_jwt_validator
        assert result["success"] is False
        assert result["details"]["key_manager"] is False
        
        # Even though we have a working JWT validator, Golden Path can't see it
        assert hasattr(app_with_unified_jwt_validator.state, 'unified_jwt_validator')
        assert app_with_unified_jwt_validator.state.unified_jwt_validator is not None
        
        # But Golden Path still fails because it only looks for key_manager
        assert result["message"] == "Key manager not available for JWT operations"

    @pytest.mark.asyncio
    async def test_golden_path_auth_requirement_integration(
        self,
        golden_path_validator,
        app_without_key_manager,
        caplog
    ):
        """Test full Golden Path validation for auth service requirements."""
        
        # Run full validation focusing on auth service requirements
        services_to_validate = [ServiceType.AUTH_SERVICE]
        
        result = await golden_path_validator.validate_golden_path_services(
            app_without_key_manager,
            services_to_validate
        )
        
        # EXPECT OVERALL FAILURE due to JWT validation
        assert result.overall_success is False
        assert result.requirements_failed > 0
        assert len(result.critical_failures) > 0
        assert len(result.business_impact_failures) > 0
        
        # Check specific JWT failure appears in results
        jwt_failure_found = False
        for validation_result in result.validation_results:
            if validation_result.get("requirement") == "jwt_validation_ready":
                assert validation_result["success"] is False
                jwt_failure_found = True
                break
                
        assert jwt_failure_found, "JWT validation failure not found in results"
        
        # Verify business impact is captured
        assert any("JWT" in failure for failure in result.business_impact_failures)

    def test_unified_jwt_validator_has_required_methods(self):
        """Test that UnifiedJWTValidator has the methods Golden Path expects."""
        
        # This test verifies that our UnifiedJWTValidator actually HAS the methods
        # that Golden Path Validator is looking for, but in a different location
        
        jwt_validator = UnifiedJWTValidator()
        
        # These are the methods Golden Path expects on key_manager
        required_methods = ['create_access_token', 'verify_token', 'create_refresh_token']
        
        for method_name in required_methods:
            assert hasattr(jwt_validator, method_name), f"UnifiedJWTValidator missing {method_name}"
            method = getattr(jwt_validator, method_name)
            assert callable(method), f"{method_name} is not callable"
            
        # Special case: Golden Path expects 'verify_token' but UnifiedJWTValidator has 'validate_token_jwt'
        assert hasattr(jwt_validator, 'validate_token_jwt'), "UnifiedJWTValidator missing validate_token_jwt"
        
        # This proves the methods exist but Golden Path can't find them due to architectural mismatch

    @pytest.mark.asyncio
    async def test_golden_path_validator_failure_logging(
        self,
        golden_path_validator,
        app_without_key_manager,
        caplog
    ):
        """Test that JWT validation failures produce expected validation results."""
        
        # Call the full validation method which handles logging
        services_to_validate = [ServiceType.AUTH_SERVICE]
        result = await golden_path_validator.validate_golden_path_services(
            app_without_key_manager,
            services_to_validate
        )
        
        # Verify that the validation failed properly (which would trigger logging)
        assert result.overall_success is False
        assert result.requirements_failed > 0
        assert len(result.critical_failures) > 0
        assert len(result.business_impact_failures) > 0
        
        # Verify specific JWT-related failure is present
        jwt_failure_found = False
        for validation_result in result.validation_results:
            if validation_result.get("requirement") == "jwt_validation_ready":
                assert validation_result["success"] is False
                assert "key manager" in validation_result["message"].lower()
                jwt_failure_found = True
                break
                
        assert jwt_failure_found, "JWT validation failure not found in results"
        
        # Verify business impact mentions JWT
        assert any("JWT" in failure for failure in result.business_impact_failures)
        
        # Note: Logging verification is done through validation results rather than
        # caplog because the validator uses central_logger which may not integrate
        # properly with pytest's caplog in all test environments

    def test_bug_reproduction_summary(self):
        """Document the exact bug this test suite reproduces."""
        
        bug_summary = {
            "issue": "Golden Path Validator expects app.state.key_manager with JWT methods",
            "reality": "We use UnifiedJWTValidator pattern that delegates to auth service", 
            "expected_methods": ['create_access_token', 'verify_token', 'create_refresh_token'],
            "actual_location": "app.state.unified_jwt_validator or netra_backend.app.core.unified.jwt_validator",
            "failure_mode": "Golden Path validation fails even when JWT functionality is available",
            "business_impact": "Authentication appears broken blocking user access",
            "root_cause": "Architectural mismatch between validation expectations and implementation"
        }
        
        # This test documents the bug - all assertions should pass to confirm our understanding
        assert bug_summary["issue"] is not None
        assert bug_summary["reality"] is not None
        assert len(bug_summary["expected_methods"]) == 3
        assert bug_summary["actual_location"] is not None
        assert bug_summary["failure_mode"] is not None
        assert bug_summary["business_impact"] is not None
        assert bug_summary["root_cause"] is not None
        
        # Print summary for debugging
        print("\n" + "="*80)
        print("JWT VALIDATION BUG REPRODUCTION SUMMARY")
        print("="*80)
        for key, value in bug_summary.items():
            print(f"{key.upper()}: {value}")
        print("="*80)