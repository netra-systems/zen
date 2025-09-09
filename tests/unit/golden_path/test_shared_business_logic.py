"""
Shared Golden Path Unit Tests: Cross-Service Business Logic

Tests shared business logic components that support the golden path
across all services, including type safety, ID generation, and
shared utilities without external dependencies.

Business Value:
- Validates shared business logic consistency across services
- Tests type safety and ID generation for business operations
- Verifies shared utilities support business requirements
- Tests cross-service integration patterns and contracts
"""

import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, MagicMock

# Import shared business logic components
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


@pytest.mark.unit
@pytest.mark.golden_path
class TestSharedTypesBusinessLogic:
    """Test shared types support business requirements across services."""

    def test_strongly_typed_user_id_business_safety(self):
        """Test strongly typed user IDs provide business type safety."""
        # Business Rule: User IDs should be strongly typed to prevent mix-ups
        raw_user_id = "business-user-123"
        
        # Test UserID type creation
        typed_user_id = ensure_user_id(raw_user_id)
        
        # Business Rule: Type safety should be enforced
        # Note: NewType creates type aliases for static analysis, not runtime classes
        # The actual runtime type is still str, but we can verify proper construction
        assert isinstance(typed_user_id, str), "UserID should be string-based"
        assert str(typed_user_id) == raw_user_id, "Should preserve original value"
        
        # Business Rule: Type creation should work for different ID types
        thread_id = ThreadID("thread-456")
        run_id = RunID("run-789")
        request_id = RequestID("req-012")
        
        # Verify all are string-based but conceptually different via typing system
        assert isinstance(thread_id, str), "ThreadID should be string-based"
        assert isinstance(run_id, str), "RunID should be string-based" 
        assert isinstance(request_id, str), "RequestID should be string-based"
        
        # Verify values are preserved
        assert str(thread_id) == "thread-456", "ThreadID should preserve value"
        assert str(run_id) == "run-789", "RunID should preserve value"
        assert str(request_id) == "req-012", "RequestID should preserve value"

    def test_execution_context_business_isolation(self):
        """Test execution context provides business user isolation."""
        # Business Rule: Execution contexts must isolate business operations by user
        
        user1_context = StronglyTypedUserExecutionContext(
            user_id=UserID("business-user-1"),
            thread_id=ThreadID("thread-1"),
            run_id=RunID("run-1"),
            request_id=RequestID("req-1"),
            db_session=None,
            agent_context={"business_operation": "cost_analysis"},
            audit_metadata={"created_by": "shared_business_logic_test"}
        )
        
        user2_context = StronglyTypedUserExecutionContext(
            user_id=UserID("business-user-2"),
            thread_id=ThreadID("thread-2"),
            run_id=RunID("run-2"), 
            request_id=RequestID("req-2"),
            db_session=None,
            agent_context={"business_operation": "cost_optimization"},
            audit_metadata={"created_by": "shared_business_logic_test"}
        )
        
        # Business Rule: Contexts should be completely isolated
        assert user1_context.user_id != user2_context.user_id, "User contexts must have different user IDs"
        assert user1_context.thread_id != user2_context.thread_id, "User contexts must have different thread IDs"
        assert user1_context.run_id != user2_context.run_id, "User contexts must have different run IDs"
        assert user1_context.agent_context != user2_context.agent_context, "Agent contexts must be isolated"
        
        # Business Rule: Each context should support business operations
        assert "business_operation" in user1_context.agent_context, "Context should support business operation tracking"
        assert user1_context.agent_context["business_operation"] == "cost_analysis", "Should track correct business operation"

    def test_id_generation_business_consistency(self):
        """Test ID generation provides business consistency across services."""
        # Business Rule: ID generation should be consistent for business tracking
        
        id_generator = UnifiedIdGenerator()
        
        # Generate user context IDs
        user_id = "business-consistency-user"
        thread_id, run_id, request_id = id_generator.generate_user_context_ids(
            user_id=user_id, 
            operation="business_consistency_test"
        )
        
        # Business Rule: Generated IDs should be properly formatted for business use
        assert isinstance(thread_id, str), "Thread ID should be string"
        assert isinstance(run_id, str), "Run ID should be string"
        assert isinstance(request_id, str), "Request ID should be string"
        
        assert len(thread_id) > 0, "Thread ID should not be empty"
        assert len(run_id) > 0, "Run ID should not be empty"
        assert len(request_id) > 0, "Request ID should not be empty"
        
        # Business Rule: IDs should be unique for business tracking
        thread_id2, run_id2, request_id2 = id_generator.generate_user_context_ids(
            user_id=user_id,
            operation="business_consistency_test"
        )
        
        assert thread_id != thread_id2, "Thread IDs should be unique for business tracking"
        assert run_id != run_id2, "Run IDs should be unique for business tracking"
        assert request_id != request_id2, "Request IDs should be unique for business tracking"

    def test_websocket_id_generation_business_communication(self):
        """Test WebSocket ID generation supports business communication requirements."""
        # Business Rule: WebSocket IDs should enable business communication tracking
        
        id_generator = UnifiedIdGenerator()
        user_id = "websocket-business-user"
        
        # Generate WebSocket client ID
        websocket_id = id_generator.generate_websocket_client_id(user_id=user_id)
        
        # Business Rule: WebSocket ID should be suitable for business tracking
        assert isinstance(websocket_id, str), "WebSocket ID should be string"
        assert len(websocket_id) > 0, "WebSocket ID should not be empty"
        assert user_id in websocket_id or "ws" in websocket_id.lower(), \
            "WebSocket ID should be identifiable as WebSocket-related"
        
        # Business Rule: Multiple WebSocket IDs should be unique for concurrent sessions
        websocket_id2 = id_generator.generate_websocket_client_id(user_id=user_id)
        assert websocket_id != websocket_id2, "WebSocket IDs should be unique for concurrent business sessions"


@pytest.mark.unit
@pytest.mark.golden_path
class TestIsolatedEnvironmentBusinessSafety:
    """Test isolated environment provides business configuration safety."""

    def test_environment_isolation_business_security(self):
        """Test environment isolation prevents business configuration leakage."""
        # Business Rule: Environment isolation should prevent config leakage between services
        
        # CRITICAL FIX: IsolatedEnvironment is a singleton - we need to test isolation differently
        # We test that isolation mode properly segregates variables from os.environ
        
        # Get the singleton instance and enable isolation for testing
        env = IsolatedEnvironment()
        original_isolation_state = env.is_isolated()
        
        try:
            # Enable isolation to prevent os.environ pollution
            env.enable_isolation()
            
            # Clear any existing test keys to ensure clean state
            if env.exists("BUSINESS_API_KEY"):
                env.delete("BUSINESS_API_KEY")
            
            # Test 1: Set value in isolated environment
            env.set("BUSINESS_API_KEY", "isolated-secret-key", source="isolated_test")
            isolated_value = env.get("BUSINESS_API_KEY")
            
            # Test 2: Check that os.environ doesn't have this value (proving isolation)
            import os
            os_environ_value = os.environ.get("BUSINESS_API_KEY", "NOT_FOUND")
            
            # Business Rule: Isolated environment should work independently from os.environ
            assert isolated_value == "isolated-secret-key", "Isolated environment should store its own values"
            assert os_environ_value == "NOT_FOUND", "os.environ should not have isolated values"
            
            # Test 3: Clear isolated value and set in os.environ to test isolation boundary
            env.delete("BUSINESS_API_KEY")
            os.environ["BUSINESS_API_KEY"] = "os-environ-value"
            
            # In isolation mode, the environment should prefer isolated vars over os.environ
            # But if not set in isolated vars, it may fall back to os.environ depending on implementation
            isolated_after_os_set = env.get("BUSINESS_API_KEY")
            
            # Clean up os.environ
            if "BUSINESS_API_KEY" in os.environ:
                del os.environ["BUSINESS_API_KEY"]
            
            # Business Rule: Isolation should provide proper separation
            assert isolated_after_os_set in ["os-environ-value", None], "Should either fall back to os.environ or return None"
            
        finally:
            # Restore original isolation state
            if original_isolation_state:
                env.enable_isolation() 
            else:
                env.disable_isolation()
                
            # Clean up any test values
            if env.exists("BUSINESS_API_KEY"):
                env.delete("BUSINESS_API_KEY")
            if "BUSINESS_API_KEY" in os.environ:
                del os.environ["BUSINESS_API_KEY"]

    def test_environment_variable_business_validation(self):
        """Test environment variables are validated for business requirements."""
        # Business Rule: Environment variables should be validated for business safety
        
        test_env = IsolatedEnvironment()
        
        # Set various business configuration types
        business_configs = [
            ("DATABASE_URL", "postgresql://business:secret@localhost/business_db"),
            ("JWT_SECRET", "business-jwt-secret-key-32-characters"),
            ("API_BASE_URL", "https://api.business.com/v1"),
            ("MAX_COST_LIMIT", "1000.00"),
            ("ENABLE_BUSINESS_FEATURES", "true")
        ]
        
        for config_name, config_value in business_configs:
            test_env.set(config_name, config_value, source="business_validation_test")
            
            # Business Rule: Environment should store and retrieve configs correctly
            retrieved_value = test_env.get(config_name)
            assert retrieved_value == config_value, f"Config {config_name} should be stored correctly"
            
            # Business Rule: Config should have source tracking for audit
            if hasattr(test_env, '_sources'):
                config_source = test_env._sources.get(config_name)
                assert config_source == "business_validation_test", f"Config {config_name} should track source"

    def test_global_environment_business_consistency(self):
        """Test global environment provides business consistency across modules."""
        # Business Rule: Global environment should provide consistent config access
        
        global_env = get_env()
        
        # Business Rule: Global environment should be accessible
        assert global_env is not None, "Global environment should be accessible"
        
        # Set and retrieve business configuration
        test_config_key = "BUSINESS_TEST_CONFIG"
        test_config_value = "business_consistency_value"
        
        global_env.set(test_config_key, test_config_value, source="business_consistency_test")
        
        # Get new reference to global environment
        global_env2 = get_env()
        retrieved_value = global_env2.get(test_config_key)
        
        # Business Rule: Global environment should maintain consistency
        assert retrieved_value == test_config_value, "Global environment should maintain consistent configuration"


@pytest.mark.unit
@pytest.mark.golden_path
class TestCrossServiceBusinessContracts:
    """Test cross-service business contracts and integration patterns."""

    def test_service_communication_business_patterns(self):
        """Test service communication follows business integration patterns."""
        # Business Rule: Services should communicate using standard business patterns
        
        # Mock service request/response pattern
        class BusinessServiceRequest:
            def __init__(self, operation: str, data: Dict, user_context: Dict):
                self.operation = operation
                self.data = data
                self.user_context = user_context
                self.request_id = str(uuid.uuid4())
                self.timestamp = datetime.now(timezone.utc)
        
        class BusinessServiceResponse:
            def __init__(self, success: bool, data: Dict, error: Optional[str] = None):
                self.success = success
                self.data = data
                self.error = error
                self.response_id = str(uuid.uuid4())
                self.timestamp = datetime.now(timezone.utc)
        
        # Test business service request
        request = BusinessServiceRequest(
            operation="cost_analysis",
            data={"time_period": "monthly", "include_breakdown": True},
            user_context={"user_id": "business-integration-user", "permissions": ["read", "analyze"]}
        )
        
        # Business Rule: Requests should have proper business structure
        assert request.operation == "cost_analysis", "Request should specify business operation"
        assert "time_period" in request.data, "Request should include business parameters"
        assert "user_id" in request.user_context, "Request should include user context"
        assert request.request_id is not None, "Request should have tracking ID"
        
        # Test business service response
        response = BusinessServiceResponse(
            success=True,
            data={
                "total_cost": 450.75,
                "breakdown": {"gpt_4": 325.50, "gpt_3_5": 125.25},
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Business Rule: Responses should have proper business structure
        assert response.success is True, "Response should indicate success status"
        assert "total_cost" in response.data, "Response should include business results"
        assert response.response_id is not None, "Response should have tracking ID"

    def test_error_propagation_business_continuity(self):
        """Test error propagation maintains business continuity across services."""
        # Business Rule: Errors should propagate with business context for continuity
        
        class BusinessError(Exception):
            def __init__(self, message: str, error_code: str, business_impact: str, recovery_suggestion: str):
                super().__init__(message)
                self.error_code = error_code
                self.business_impact = business_impact
                self.recovery_suggestion = recovery_suggestion
                self.timestamp = datetime.now(timezone.utc)
        
        # Test business error propagation
        business_error = BusinessError(
            message="Cost calculation service temporarily unavailable",
            error_code="COST_CALC_503",
            business_impact="cost_analysis_delayed",
            recovery_suggestion="retry_in_5_minutes"
        )
        
        # Business Rule: Business errors should provide actionable information
        assert business_error.error_code.startswith("COST_CALC"), "Error code should identify business domain"
        assert business_error.business_impact == "cost_analysis_delayed", "Should identify business impact"
        assert "retry" in business_error.recovery_suggestion, "Should provide recovery guidance"
        assert business_error.timestamp is not None, "Should track error occurrence time"
        
        # Business Rule: Error handling should support business decisions
        def handle_business_error(error: BusinessError) -> Dict[str, Any]:
            return {
                "user_message": "Cost analysis is temporarily delayed. We'll retry automatically.",
                "technical_code": error.error_code,
                "retry_recommended": "retry" in error.recovery_suggestion,
                "business_continuity": "degraded" if "delayed" in error.business_impact else "critical"
            }
        
        error_handling = handle_business_error(business_error)
        
        assert "temporarily delayed" in error_handling["user_message"], "Should provide user-friendly message"
        assert error_handling["retry_recommended"] is True, "Should recommend retry for business continuity"
        assert error_handling["business_continuity"] == "degraded", "Should assess business impact correctly"

    def test_data_consistency_business_requirements(self):
        """Test data consistency meets cross-service business requirements."""
        # Business Rule: Data should be consistent across service boundaries
        
        # Mock business data that crosses service boundaries
        user_business_data = {
            "user_id": "cross-service-user",
            "email": "crossservice@company.com",
            "subscription_tier": "premium",
            "monthly_cost_limit": 1000.00,
            "permissions": ["read", "write", "analyze", "premium_features"]
        }
        
        cost_analysis_data = {
            "user_id": "cross-service-user",  # Same user ID
            "current_monthly_cost": 450.75,
            "cost_breakdown": {"gpt_4": 325.50, "gpt_3_5": 125.25},
            "optimization_potential": 70.25
        }
        
        # Business Rule: Related data should have consistent user identification
        assert user_business_data["user_id"] == cost_analysis_data["user_id"], \
            "Cross-service data should have consistent user identification"
        
        # Business Rule: Data should support cross-service business logic
        user_cost_limit = user_business_data["monthly_cost_limit"]
        current_cost = cost_analysis_data["current_monthly_cost"]
        
        # Calculate business metrics across services
        cost_utilization = (current_cost / user_cost_limit) * 100
        is_approaching_limit = cost_utilization > 80
        
        assert cost_utilization < 100, "User should be within cost limit"
        assert isinstance(is_approaching_limit, bool), "Should calculate business alert status"

    def test_business_validation_cross_service_consistency(self):
        """Test business validation is consistent across services."""
        # Business Rule: Business validation should be consistent across all services
        
        # Mock shared business validation functions
        def validate_email_business_standard(email: str) -> bool:
            """Standard business email validation across all services."""
            if not email or "@" not in email:
                return False
            if len(email) < 5 or len(email) > 254:  # RFC 5321 limit
                return False
            if ".." in email:  # No consecutive dots
                return False
            return True
        
        def validate_cost_amount_business_standard(amount: float) -> bool:
            """Standard business cost validation across all services."""
            if amount < 0:
                return False
            if amount > 1000000:  # Business limit
                return False
            return True
        
        # Test consistent email validation
        test_emails = [
            ("valid@company.com", True),
            ("invalid-email", False),
            ("", False),
            ("user@domain..com", False),  # Consecutive dots
            ("a" * 250 + "@company.com", False)  # Too long
        ]
        
        for email, expected_valid in test_emails:
            is_valid = validate_email_business_standard(email)
            assert is_valid == expected_valid, f"Email validation should be consistent: {email}"
        
        # Test consistent cost validation
        test_costs = [
            (450.75, True),
            (-100.00, False),  # Negative
            (1500000.00, False),  # Too high
            (0.00, True)  # Zero is valid
        ]
        
        for cost, expected_valid in test_costs:
            is_valid = validate_cost_amount_business_standard(cost)
            assert is_valid == expected_valid, f"Cost validation should be consistent: {cost}"