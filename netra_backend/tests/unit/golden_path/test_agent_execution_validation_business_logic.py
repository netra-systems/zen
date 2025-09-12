"""
Unit Tests for Agent Execution Validation Business Logic

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Revenue Protection - Validates $500K+ ARR agent execution workflows
- Value Impact: Agent execution is core differentiator - AI-powered problem solving
- Strategic Impact: Unit tests ensure reliable agent orchestration without external dependencies

CRITICAL: These are GOLDEN PATH tests that validate core business logic for agent execution.
They test business rules and validation without requiring real LLM calls or external services.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List
import uuid

# SSOT Imports - Absolute imports as per CLAUDE.md requirement
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.agent_types import AgentExecutionRequest, AgentExecutionResult, AgentValidationResult
from netra_backend.app.agents.supervisor.agent_execution_validator import AgentExecutionValidator
from netra_backend.app.agents.supervisor.agent_execution_context_manager import AgentExecutionContextManager
from netra_backend.app.agents.base.agent_business_rules import AgentBusinessRuleValidator
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.golden_path
@pytest.mark.unit
class TestAgentExecutionValidationBusinessLogic(SSotBaseTestCase):
    """
    Golden Path Unit Tests for Agent Execution Validation Business Logic.
    
    These tests validate the core business rules for agent execution validation
    without external dependencies. They ensure agent execution follows business
    requirements for all customer segments.
    """

    def test_agent_execution_request_validation_success(self):
        """
        Test Case: Valid agent execution request passes all business validations.
        
        Business Value: Ensures legitimate user requests are processed correctly.
        Expected: Valid requests pass validation with proper context creation.
        """
        # Arrange
        user_id = str(uuid.uuid4())
        request_data = {
            "user_input": "Optimize my database queries for better performance",
            "agent_type": "database_optimization",
            "context": {"current_db": "postgresql", "table_count": 15},
            "priority": "normal"
        }
        
        execution_request = AgentExecutionRequest(
            user_id=ensure_user_id(user_id),
            thread_id=ThreadID(f"thread_{uuid.uuid4().hex[:12]}"),
            request_data=request_data,
            timestamp=datetime.now(timezone.utc),
            user_permissions=["read", "write", "agent_execution"]
        )
        
        validator = AgentExecutionValidator()
        
        # Act
        validation_result = validator.validate_execution_request(execution_request)
        
        # Assert
        assert isinstance(validation_result, AgentValidationResult)
        assert validation_result.is_valid is True
        assert validation_result.error_message is None
        assert str(validation_result.user_id) == user_id
        assert validation_result.validation_passed["request_format"] is True
        assert validation_result.validation_passed["user_permissions"] is True
        assert validation_result.validation_passed["agent_type"] is True
        
        print(" PASS:  Agent execution request validation success test passed")

    def test_agent_execution_request_validation_failure_insufficient_permissions(self):
        """
        Test Case: Agent execution fails for users without proper permissions.
        
        Business Value: Enforces customer tier restrictions (Free vs Paid features).
        Expected: Users without agent permissions cannot execute premium agents.
        """
        # Arrange
        free_tier_user_id = str(uuid.uuid4())
        premium_request_data = {
            "user_input": "Run advanced AI optimization analysis",
            "agent_type": "premium_optimization",  # Premium-only agent
            "context": {"advanced_features": True},
            "priority": "high"
        }
        
        execution_request = AgentExecutionRequest(
            user_id=ensure_user_id(free_tier_user_id),
            thread_id=ThreadID(f"thread_{uuid.uuid4().hex[:12]}"),
            request_data=premium_request_data,
            timestamp=datetime.now(timezone.utc),
            user_permissions=["read"]  # Free tier permissions only
        )
        
        validator = AgentExecutionValidator()
        
        # Act
        validation_result = validator.validate_execution_request(execution_request)
        
        # Assert
        assert isinstance(validation_result, AgentValidationResult)
        assert validation_result.is_valid is False
        assert validation_result.error_message is not None
        assert "permission" in validation_result.error_message.lower()
        assert validation_result.validation_passed["user_permissions"] is False
        
        print(" PASS:  Agent execution permission failure test passed")

    def test_agent_execution_context_creation_with_isolation(self):
        """
        Test Case: Agent execution context provides proper user isolation.
        
        Business Value: Ensures multi-tenant security - users can't access each other's data.
        Expected: Each execution context is completely isolated per user.
        """
        # Arrange
        users = [
            {"user_id": str(uuid.uuid4()), "permissions": ["read", "write"]},
            {"user_id": str(uuid.uuid4()), "permissions": ["read", "write", "premium"]},
            {"user_id": str(uuid.uuid4()), "permissions": ["read"]}
        ]
        
        context_manager = AgentExecutionContextManager()
        created_contexts = []
        
        # Act
        for user in users:
            execution_context = StronglyTypedUserExecutionContext(
                user_id=ensure_user_id(user["user_id"]),
                thread_id=ThreadID(f"thread_{uuid.uuid4().hex[:12]}"),
                run_id=RunID(f"run_{uuid.uuid4().hex[:12]}"),
                request_id=RequestID(f"req_{uuid.uuid4().hex[:12]}"),
                db_session=None,
                agent_context={
                    "permissions": user["permissions"],
                    "isolation_boundary": user["user_id"]
                }
            )
            created_contexts.append(execution_context)
        
        # Assert - Each context is properly isolated
        user_ids = [str(ctx.user_id) for ctx in created_contexts]
        thread_ids = [str(ctx.thread_id) for ctx in created_contexts]
        
        # All user IDs should be unique
        assert len(set(user_ids)) == len(users)
        # All thread IDs should be unique
        assert len(set(thread_ids)) == len(users)
        
        # Context isolation validation
        for ctx in created_contexts:
            # Each context should have its own isolated boundary
            isolation_boundary = ctx.agent_context["isolation_boundary"]
            assert isolation_boundary == str(ctx.user_id)
            
            # Permissions should match user tier
            permissions = ctx.agent_context["permissions"] 
            assert isinstance(permissions, list)
            assert len(permissions) > 0
        
        print(" PASS:  Agent execution context isolation test passed")

    def test_agent_execution_business_rule_validation(self):
        """
        Test Case: Agent execution follows business rules for different customer tiers.
        
        Business Value: Enforces monetization boundaries and feature access control.
        Expected: Different tiers have appropriate agent execution limits and capabilities.
        """
        # Arrange
        business_rule_validator = AgentBusinessRuleValidator()
        
        test_scenarios = [
            {
                "user_tier": "free",
                "permissions": ["read"],
                "agent_type": "basic_analysis",
                "expected_allowed": True,
                "expected_features": ["basic_optimization", "query_analysis"]
            },
            {
                "user_tier": "early",
                "permissions": ["read", "write"],
                "agent_type": "advanced_analysis", 
                "expected_allowed": True,
                "expected_features": ["advanced_optimization", "multi_table_analysis"]
            },
            {
                "user_tier": "enterprise",
                "permissions": ["read", "write", "admin", "premium"],
                "agent_type": "premium_optimization",
                "expected_allowed": True,
                "expected_features": ["ai_powered_optimization", "custom_agents", "priority_execution"]
            },
            {
                "user_tier": "free",
                "permissions": ["read"],
                "agent_type": "premium_optimization",  # Premium agent for free user
                "expected_allowed": False,
                "expected_features": []
            }
        ]
        
        # Act & Assert
        for scenario in test_scenarios:
            validation_result = business_rule_validator.validate_agent_access(
                user_permissions=scenario["permissions"],
                agent_type=scenario["agent_type"],
                user_tier=scenario["user_tier"]
            )
            
            assert validation_result.allowed == scenario["expected_allowed"]
            
            if scenario["expected_allowed"]:
                # Check available features match tier
                available_features = validation_result.available_features
                for expected_feature in scenario["expected_features"]:
                    assert expected_feature in available_features
                    
            print(f" PASS:  Business rule validation test passed for {scenario['user_tier']} tier")

    def test_agent_execution_input_sanitization_security(self):
        """
        Test Case: Agent execution input is properly sanitized for security.
        
        Business Value: Prevents injection attacks and ensures system security.
        Expected: Malicious inputs are sanitized or rejected with clear errors.
        """
        # Arrange
        validator = AgentExecutionValidator()
        
        malicious_inputs = [
            {
                "name": "sql_injection_attempt",
                "user_input": "'; DROP TABLE users; --",
                "should_be_sanitized": True
            },
            {
                "name": "script_injection_attempt", 
                "user_input": "<script>alert('xss')</script>",
                "should_be_sanitized": True
            },
            {
                "name": "command_injection_attempt",
                "user_input": "$(rm -rf /)",
                "should_be_sanitized": True
            },
            {
                "name": "legitimate_technical_input",
                "user_input": "SELECT * FROM performance_metrics WHERE cpu_usage > 80%",
                "should_be_sanitized": False  # Legitimate SQL query in context
            }
        ]
        
        # Act & Assert
        for test_case in malicious_inputs:
            sanitized_input = validator.sanitize_user_input(
                user_input=test_case["user_input"],
                context_type="database_optimization"
            )
            
            if test_case["should_be_sanitized"]:
                # Malicious content should be removed or escaped
                assert sanitized_input != test_case["user_input"]
                # Should not contain dangerous patterns
                dangerous_patterns = ["DROP", "script>", "$(", "rm -rf"]
                for pattern in dangerous_patterns:
                    assert pattern not in sanitized_input
            else:
                # Legitimate input should pass through
                assert sanitized_input == test_case["user_input"]
                
            print(f" PASS:  Input sanitization test passed for {test_case['name']}")

    def test_agent_execution_result_structure_validation(self):
        """
        Test Case: Agent execution results follow required structure for business value.
        
        Business Value: Ensures consistent result format for frontend integration.
        Expected: All execution results contain required fields for user value delivery.
        """
        # Arrange
        user_id = str(uuid.uuid4())
        
        # Create mock execution result
        execution_result = AgentExecutionResult(
            user_id=ensure_user_id(user_id),
            thread_id=ThreadID(f"thread_{uuid.uuid4().hex[:12]}"),
            run_id=RunID(f"run_{uuid.uuid4().hex[:12]}"),
            success=True,
            result_data={
                "optimization_recommendations": [
                    {"type": "index", "table": "users", "column": "email", "impact": "high"},
                    {"type": "query", "suggestion": "Use LIMIT clause", "impact": "medium"}
                ],
                "performance_metrics": {
                    "execution_time": "250ms",
                    "improvement_estimate": "35%"
                }
            },
            execution_metadata={
                "agent_type": "database_optimization",
                "execution_duration": 2.5,
                "tokens_used": 1250,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        validator = AgentExecutionValidator()
        
        # Act
        structure_validation = validator.validate_result_structure(execution_result)
        
        # Assert - Required fields for business value delivery
        assert structure_validation.is_valid is True
        assert execution_result.user_id is not None
        assert execution_result.success is not None
        assert execution_result.result_data is not None
        
        # Business value fields
        result_data = execution_result.result_data
        assert "optimization_recommendations" in result_data
        assert "performance_metrics" in result_data
        assert len(result_data["optimization_recommendations"]) > 0
        
        # Each recommendation should have business value fields
        for recommendation in result_data["optimization_recommendations"]:
            assert "type" in recommendation
            assert "impact" in recommendation  # Business impact assessment
            
        # Performance metrics for user value
        metrics = result_data["performance_metrics"]
        assert "execution_time" in metrics
        assert "improvement_estimate" in metrics
        
        print(" PASS:  Agent execution result structure validation test passed")

    def test_agent_execution_timeout_business_requirements(self):
        """
        Test Case: Agent execution respects timeout business requirements.
        
        Business Value: Ensures responsive user experience - no hanging requests.
        Expected: Different tiers have appropriate timeout limits.
        """
        # Arrange
        validator = AgentExecutionValidator()
        
        timeout_scenarios = [
            {"user_tier": "free", "expected_timeout": 30, "agent_type": "basic"},
            {"user_tier": "early", "expected_timeout": 60, "agent_type": "standard"}, 
            {"user_tier": "enterprise", "expected_timeout": 300, "agent_type": "premium"}
        ]
        
        # Act & Assert
        for scenario in timeout_scenarios:
            calculated_timeout = validator.calculate_execution_timeout(
                user_tier=scenario["user_tier"],
                agent_type=scenario["agent_type"]
            )
            
            assert calculated_timeout == scenario["expected_timeout"]
            
            # Timeout should be reasonable for user experience
            assert calculated_timeout <= 300  # Max 5 minutes even for enterprise
            assert calculated_timeout >= 10   # Min 10 seconds for any operation
            
            print(f" PASS:  Timeout validation test passed for {scenario['user_tier']} tier ({calculated_timeout}s)")

    def test_agent_execution_queue_prioritization_business_logic(self):
        """
        Test Case: Agent execution queue follows business prioritization rules.
        
        Business Value: Ensures paying customers get priority service.
        Expected: Premium users get higher priority in execution queue.
        """
        # Arrange
        execution_requests = [
            {
                "user_id": str(uuid.uuid4()),
                "user_tier": "free", 
                "permissions": ["read"],
                "expected_priority": 1
            },
            {
                "user_id": str(uuid.uuid4()),
                "user_tier": "enterprise",
                "permissions": ["read", "write", "premium"],
                "expected_priority": 5
            },
            {
                "user_id": str(uuid.uuid4()), 
                "user_tier": "early",
                "permissions": ["read", "write"],
                "expected_priority": 3
            }
        ]
        
        validator = AgentExecutionValidator()
        
        # Act & Assert
        calculated_priorities = []
        for request in execution_requests:
            priority = validator.calculate_execution_priority(
                user_tier=request["user_tier"],
                user_permissions=request["permissions"]
            )
            calculated_priorities.append({
                "user_tier": request["user_tier"],
                "priority": priority,
                "expected": request["expected_priority"]
            })
            
            assert priority == request["expected_priority"]
        
        # Business rule: Enterprise > Early > Free
        enterprise_priority = next(p["priority"] for p in calculated_priorities if p["user_tier"] == "enterprise")
        early_priority = next(p["priority"] for p in calculated_priorities if p["user_tier"] == "early") 
        free_priority = next(p["priority"] for p in calculated_priorities if p["user_tier"] == "free")
        
        assert enterprise_priority > early_priority > free_priority
        
        print(" PASS:  Agent execution queue prioritization test passed")

    def test_agent_execution_resource_limits_per_tier(self):
        """
        Test Case: Agent execution respects resource limits per customer tier.
        
        Business Value: Prevents resource abuse while enabling appropriate usage per tier.
        Expected: Each tier has appropriate resource limits for sustainable business.
        """
        # Arrange
        validator = AgentExecutionValidator()
        
        tier_scenarios = [
            {
                "user_tier": "free",
                "expected_daily_limit": 10,
                "expected_concurrent_limit": 1,
                "expected_memory_limit_mb": 256
            },
            {
                "user_tier": "early", 
                "expected_daily_limit": 100,
                "expected_concurrent_limit": 3,
                "expected_memory_limit_mb": 512
            },
            {
                "user_tier": "enterprise",
                "expected_daily_limit": 1000,
                "expected_concurrent_limit": 10,
                "expected_memory_limit_mb": 2048
            }
        ]
        
        # Act & Assert
        for scenario in tier_scenarios:
            resource_limits = validator.get_resource_limits(scenario["user_tier"])
            
            assert resource_limits["daily_execution_limit"] == scenario["expected_daily_limit"]
            assert resource_limits["concurrent_execution_limit"] == scenario["expected_concurrent_limit"]
            assert resource_limits["memory_limit_mb"] == scenario["expected_memory_limit_mb"]
            
            # Business validation - limits should be reasonable
            assert resource_limits["daily_execution_limit"] > 0
            assert resource_limits["concurrent_execution_limit"] > 0
            assert resource_limits["memory_limit_mb"] >= 128  # Minimum for any operation
            
            print(f" PASS:  Resource limits test passed for {scenario['user_tier']} tier")

    def test_agent_execution_error_recovery_business_logic(self):
        """
        Test Case: Agent execution failures provide business-friendly error recovery.
        
        Business Value: Maintains user trust through graceful error handling.
        Expected: Errors provide actionable recovery suggestions.
        """
        # Arrange
        validator = AgentExecutionValidator()
        
        error_scenarios = [
            {
                "error_type": "insufficient_permissions",
                "user_tier": "free",
                "expected_recovery": "upgrade_to_early_tier",
                "expected_message_contains": ["upgrade", "premium", "contact"]
            },
            {
                "error_type": "resource_limit_exceeded",
                "user_tier": "early", 
                "expected_recovery": "wait_for_reset_or_upgrade",
                "expected_message_contains": ["limit", "reset", "tomorrow", "upgrade"]
            },
            {
                "error_type": "agent_timeout",
                "user_tier": "enterprise",
                "expected_recovery": "retry_with_simpler_request",
                "expected_message_contains": ["timeout", "retry", "simplify", "support"]
            }
        ]
        
        # Act & Assert
        for scenario in error_scenarios:
            error_response = validator.create_business_friendly_error(
                error_type=scenario["error_type"],
                user_tier=scenario["user_tier"]
            )
            
            assert error_response["recovery_action"] == scenario["expected_recovery"]
            assert error_response["user_message"] is not None
            
            # Check message contains business-friendly language
            user_message_lower = error_response["user_message"].lower()
            for expected_word in scenario["expected_message_contains"]:
                assert expected_word in user_message_lower
                
            # Should not contain technical jargon
            technical_jargon = ["exception", "stack trace", "null pointer", "segmentation fault"]
            for jargon in technical_jargon:
                assert jargon not in user_message_lower
                
            print(f" PASS:  Error recovery test passed for {scenario['error_type']}")

    def test_agent_execution_audit_trail_compliance(self):
        """
        Test Case: Agent execution maintains proper audit trail for compliance.
        
        Business Value: Ensures regulatory compliance and security auditing.
        Expected: All executions are properly logged with required metadata.
        """
        # Arrange
        user_id = str(uuid.uuid4())
        execution_request = AgentExecutionRequest(
            user_id=ensure_user_id(user_id),
            thread_id=ThreadID(f"thread_{uuid.uuid4().hex[:12]}"),
            request_data={
                "user_input": "Optimize database performance",
                "agent_type": "database_optimization"
            },
            timestamp=datetime.now(timezone.utc),
            user_permissions=["read", "write"]
        )
        
        validator = AgentExecutionValidator()
        
        # Act
        audit_metadata = validator.create_audit_metadata(execution_request)
        
        # Assert - Required audit fields
        required_fields = [
            "user_id", "timestamp", "request_type", "user_permissions",
            "request_hash", "ip_address", "user_agent", "session_id"
        ]
        
        for field in required_fields:
            assert field in audit_metadata, f"Missing required audit field: {field}"
            assert audit_metadata[field] is not None
        
        # Business compliance requirements
        assert audit_metadata["user_id"] == user_id
        assert isinstance(audit_metadata["timestamp"], str)  # ISO format
        assert audit_metadata["request_type"] == "agent_execution"
        assert audit_metadata["user_permissions"] == ["read", "write"]
        
        # Security audit requirements
        assert len(audit_metadata["request_hash"]) > 0  # Request fingerprint
        assert audit_metadata["session_id"] is not None  # Session tracking
        
        print(" PASS:  Agent execution audit trail compliance test passed")


if __name__ == "__main__":
    # Run tests with business value reporting
    pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "-x"  # Stop on first failure for fast feedback
    ])