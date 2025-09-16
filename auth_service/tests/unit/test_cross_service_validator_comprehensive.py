"""
Cross-Service Validator Comprehensive Unit Tests

Tests critical cross-service authorization logic for business value protection.
Focuses on security gaps identified in coverage analysis for Issue #718.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - critical security infrastructure
- Business Goal: Protect $500K+ ARR through secure cross-service communication
- Value Impact: Ensures users can only access authorized resources across services
- Strategic Impact: Maintains platform security and compliance across service boundaries
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import Mock, patch

from auth_service.auth_core.security.cross_service_validator import (
    CrossServiceValidator,
    CrossServiceValidationResult
)
from auth_service.auth_core.auth_environment import AuthEnvironment


class CrossServiceValidatorTests:
    """Comprehensive unit tests for cross-service validation security logic."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Set up test environment for each test."""
        # Create mock auth environment
        self.mock_auth_env = Mock()
        self.validator = CrossServiceValidator(self.mock_auth_env)

        # Test data templates
        self.base_service_request = {
            "requesting_service": "backend",
            "target_resource": "user_data",
            "user_context": {
                "user_id": "test_user_123",
                "tier": "early",
                "subscription": "early"
            },
            "operation": "read"
        }

    def test_validate_authorized_backend_read_operation(self):
        """Test that authorized backend read operations are allowed."""
        request = self.base_service_request.copy()
        result = self.validator.validate_cross_service_request(request)

        self.assertTrue(result.is_authorized)
        self.assertEqual(result.allowed_operations, ["read"])
        self.assertEqual(result.user_context["user_id"], "test_user_123")
        self.assertEqual(result.user_context["tier"], "early")

    def test_validate_authorized_backend_write_operation(self):
        """Test that authorized backend write operations are allowed for early tier."""
        request = self.base_service_request.copy()
        request["operation"] = "write"

        result = self.validator.validate_cross_service_request(request)

        self.assertTrue(result.is_authorized)
        self.assertEqual(result.allowed_operations, ["write"])

    def test_validate_enterprise_user_delete_operation(self):
        """Test that enterprise users can perform delete operations."""
        request = self.base_service_request.copy()
        request["user_context"]["tier"] = "enterprise"
        request["operation"] = "delete"

        result = self.validator.validate_cross_service_request(request)

        self.assertTrue(result.is_authorized)
        self.assertEqual(result.allowed_operations, ["delete"])

    def test_deny_free_tier_write_operation(self):
        """Test that free tier users cannot perform write operations."""
        request = self.base_service_request.copy()
        request["user_context"]["tier"] = "free"
        request["operation"] = "write"

        result = self.validator.validate_cross_service_request(request)

        self.assertFalse(result.is_authorized)
        self.assertIn("free tier cannot perform write", result.denial_reason)
        self.assertEqual(result.allowed_operations, ["read"])

    def test_deny_frontend_write_operation(self):
        """Test that frontend service cannot perform write operations."""
        request = self.base_service_request.copy()
        request["requesting_service"] = "frontend"
        request["operation"] = "write"

        result = self.validator.validate_cross_service_request(request)

        self.assertFalse(result.is_authorized)
        self.assertIn("restricted for service frontend", result.denial_reason)
        self.assertEqual(result.allowed_operations, ["read"])

    def test_deny_unknown_service(self):
        """Test that unknown services are denied access."""
        request = self.base_service_request.copy()
        request["requesting_service"] = "unknown_service"

        result = self.validator.validate_cross_service_request(request)

        self.assertFalse(result.is_authorized)
        self.assertIn("Unknown requesting service: unknown_service", result.denial_reason)
        self.assertEqual(result.allowed_operations, [])

    def test_deny_invalid_resource_access(self):
        """Test that services cannot access resources outside their allowed targets."""
        request = self.base_service_request.copy()
        request["requesting_service"] = "frontend"
        request["target_resource"] = "admin_data"  # Not in frontend allowed_targets

        result = self.validator.validate_cross_service_request(request)

        self.assertFalse(result.is_authorized)
        self.assertIn("frontend cannot access resource admin_data", result.denial_reason)

    def test_deny_restricted_operation_for_service(self):
        """Test that services cannot perform restricted operations."""
        request = self.base_service_request.copy()
        request["requesting_service"] = "frontend"
        request["operation"] = "admin"  # Restricted for frontend

        result = self.validator.validate_cross_service_request(request)

        self.assertFalse(result.is_authorized)
        self.assertIn("admin is restricted for service frontend", result.denial_reason)

    def test_validate_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        incomplete_requests = [
            {"requesting_service": "", "target_resource": "user_data", "user_context": {}, "operation": "read"},
            {"requesting_service": "backend", "target_resource": "", "user_context": {}, "operation": "read"},
            {"requesting_service": "backend", "target_resource": "user_data", "user_context": {}, "operation": ""},
            {"requesting_service": "backend", "target_resource": "user_data", "operation": "read"}  # Missing user_context
        ]

        for request in incomplete_requests:
            result = self.validator.validate_cross_service_request(request)
            self.assertFalse(result.is_authorized)
            self.assertIn("Missing required fields", result.denial_reason)

    def test_validate_unknown_user_tier(self):
        """Test handling of unknown user tiers."""
        request = self.base_service_request.copy()
        request["user_context"]["tier"] = "unknown_tier"

        result = self.validator.validate_cross_service_request(request)

        self.assertFalse(result.is_authorized)
        self.assertIn("Unknown user tier: unknown_tier", result.denial_reason)
        self.assertEqual(result.allowed_operations, ["read"])  # Default to minimal permissions

    def test_tier_resource_limits_free_tier(self):
        """Test that free tier users are limited to specific resources."""
        request = self.base_service_request.copy()
        request["user_context"]["tier"] = "free"
        request["target_resource"] = "agent_data"  # Not allowed for free tier

        result = self.validator.validate_cross_service_request(request)

        self.assertFalse(result.is_authorized)
        self.assertIn("agent_data not available for free tier", result.denial_reason)

    def test_tier_resource_limits_enterprise_no_limits(self):
        """Test that enterprise tier has no resource limits."""
        request = self.base_service_request.copy()
        request["user_context"]["tier"] = "enterprise"
        request["target_resource"] = "any_resource"  # Enterprise has no limits
        request["operation"] = "delete"

        result = self.validator.validate_cross_service_request(request)

        self.assertTrue(result.is_authorized)
        self.assertEqual(result.allowed_operations, ["delete"])

    def test_auth_service_permissions(self):
        """Test that auth service has broader permissions including delete."""
        request = self.base_service_request.copy()
        request["requesting_service"] = "auth"
        request["target_resource"] = "auth_data"
        request["operation"] = "delete"

        result = self.validator.validate_cross_service_request(request)

        self.assertTrue(result.is_authorized)
        self.assertEqual(result.allowed_operations, ["delete"])

    def test_error_handling_exception_safety(self):
        """Test that validation handles unexpected exceptions gracefully."""
        # Create a validator with a mock that raises an exception
        with patch.object(self.validator, '_validate_tier_permissions', side_effect=Exception("Test error")):
            request = self.base_service_request.copy()
            result = self.validator.validate_cross_service_request(request)

            self.assertFalse(result.is_authorized)
            self.assertIn("Validation error: Test error", result.denial_reason)
            self.assertEqual(result.allowed_operations, [])

    def test_service_permissions_validation_success(self):
        """Test successful service permissions validation."""
        service_validation = self.validator._validate_service_permissions("backend", "user_data", "read")

        self.assertTrue(service_validation["allowed"])
        self.assertEqual(service_validation["reason"], "Service permissions validated successfully")
        self.assertIn("permissions", service_validation)

    def test_service_permissions_validation_failure(self):
        """Test service permissions validation failure scenarios."""
        # Unknown service
        result = self.validator._validate_service_permissions("unknown", "user_data", "read")
        self.assertFalse(result["allowed"])
        self.assertIn("Unknown requesting service", result["reason"])

        # Invalid target resource
        result = self.validator._validate_service_permissions("backend", "invalid_resource", "read")
        self.assertFalse(result["allowed"])
        self.assertIn("cannot access resource", result["reason"])

        # Restricted operation
        result = self.validator._validate_service_permissions("frontend", "user_profile", "delete")
        self.assertFalse(result["allowed"])
        self.assertIn("is restricted for service", result["reason"])

    def test_tier_permissions_validation_success(self):
        """Test successful tier permissions validation."""
        tier_validation = self.validator._validate_tier_permissions("early", "user_data", "read")

        self.assertTrue(tier_validation["allowed"])
        self.assertEqual(tier_validation["reason"], "Tier permissions validated successfully")
        self.assertIn("read", tier_validation["allowed_operations"])

    def test_tier_permissions_validation_failure(self):
        """Test tier permissions validation failure scenarios."""
        # Unknown tier
        result = self.validator._validate_tier_permissions("unknown", "user_data", "read")
        self.assertFalse(result["allowed"])
        self.assertIn("Unknown user tier", result["reason"])

        # Insufficient privileges
        result = self.validator._validate_tier_permissions("free", "user_data", "write")
        self.assertFalse(result["allowed"])
        self.assertIn("free tier cannot perform write", result["reason"])

        # Resource not available for tier
        result = self.validator._validate_tier_permissions("free", "agent_data", "read")
        self.assertFalse(result["allowed"])
        self.assertIn("agent_data not available for free tier", result["reason"])

    def test_get_allowed_operations_intersection(self):
        """Test that allowed operations are correctly calculated as intersection."""
        # Test intersection of service and tier permissions
        allowed_ops = self.validator._get_allowed_operations_for_context("backend", "early", "user_data")

        # Backend allows read,write; early tier allows read,write; intersection should be read,write
        expected_operations = ["read", "write"]
        self.assertEqual(sorted(allowed_ops), sorted(expected_operations))

    def test_get_allowed_operations_limited_intersection(self):
        """Test intersection when tier has fewer permissions than service."""
        # Frontend service (read only) with enterprise tier (read,write,delete)
        allowed_ops = self.validator._get_allowed_operations_for_context("frontend", "enterprise", "user_profile")

        # Should be limited to frontend's read-only permissions
        self.assertEqual(allowed_ops, ["read"])

    def test_security_business_value_protection(self):
        """Test that security violations are properly blocked to protect business value."""
        # Test scenario: Malicious attempt to escalate privileges
        malicious_request = {
            "requesting_service": "frontend",  # Limited service
            "target_resource": "admin_data",   # Restricted resource
            "user_context": {
                "user_id": "malicious_user",
                "tier": "free"                # Lowest tier
            },
            "operation": "delete"             # Destructive operation
        }

        result = self.validator.validate_cross_service_request(malicious_request)

        # Should be completely blocked
        self.assertFalse(result.is_authorized)
        self.assertEqual(result.allowed_operations, ["read"])  # Only safe operations
        # Should fail at multiple validation layers
        self.assertTrue(
            "cannot access resource" in result.denial_reason or
            "free tier cannot perform" in result.denial_reason or
            "restricted for service" in result.denial_reason
        )

    def test_multi_user_isolation_security(self):
        """Test that different users get proper isolation in validation."""
        # User 1: Enterprise user
        enterprise_request = self.base_service_request.copy()
        enterprise_request["user_context"] = {
            "user_id": "enterprise_user_456",
            "tier": "enterprise"
        }
        enterprise_request["operation"] = "delete"

        # User 2: Free user
        free_request = self.base_service_request.copy()
        free_request["user_context"] = {
            "user_id": "free_user_789",
            "tier": "free"
        }
        free_request["operation"] = "delete"

        enterprise_result = self.validator.validate_cross_service_request(enterprise_request)
        free_result = self.validator.validate_cross_service_request(free_request)

        # Enterprise user should be authorized, free user should not
        self.assertTrue(enterprise_result.is_authorized)
        self.assertFalse(free_result.is_authorized)

        # Ensure user contexts are preserved correctly
        self.assertEqual(enterprise_result.user_context["user_id"], "enterprise_user_456")
        self.assertEqual(free_result.user_context["user_id"], "free_user_789")

    def test_validation_result_structure(self):
        """Test that validation results have proper structure and data."""
        request = self.base_service_request.copy()
        result = self.validator.validate_cross_service_request(request)

        # Verify all required fields are present
        self.assertIsInstance(result, CrossServiceValidationResult)
        self.assertIsInstance(result.is_authorized, bool)
        self.assertIsInstance(result.allowed_operations, list)
        self.assertIsInstance(result.denial_reason, str)

        if result.is_authorized:
            self.assertIsNotNone(result.user_context)
            self.assertIsNotNone(result.service_permissions)

        # Test denied result structure
        denied_request = self.base_service_request.copy()
        denied_request["user_context"]["tier"] = "free"
        denied_request["operation"] = "delete"
        denied_result = self.validator.validate_cross_service_request(denied_request)

        self.assertFalse(denied_result.is_authorized)
        self.assertTrue(len(denied_result.denial_reason) > 0)
        self.assertIsInstance(denied_result.allowed_operations, list)


class CrossServiceValidatorEdgeCasesTests:
    """Test edge cases and security scenarios for cross-service validation."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Set up test environment for edge case testing."""
        self.mock_auth_env = Mock()
        self.validator = CrossServiceValidator(self.mock_auth_env)

    def test_empty_request_handling(self):
        """Test handling of completely empty requests."""
        empty_request = {}
        result = self.validator.validate_cross_service_request(empty_request)

        self.assertFalse(result.is_authorized)
        self.assertIn("Missing required fields", result.denial_reason)

    def test_null_user_context_handling(self):
        """Test handling of null user context."""
        request = {
            "requesting_service": "backend",
            "target_resource": "user_data",
            "user_context": None,
            "operation": "read"
        }

        result = self.validator.validate_cross_service_request(request)
        self.assertFalse(result.is_authorized)

    def test_malformed_user_context(self):
        """Test handling of malformed user context data."""
        request = {
            "requesting_service": "backend",
            "target_resource": "user_data",
            "user_context": "not_a_dict",
            "operation": "read"
        }

        result = self.validator.validate_cross_service_request(request)
        self.assertFalse(result.is_authorized)

    def test_case_sensitivity_handling(self):
        """Test that service names and tiers are handled case-insensitively."""
        request = {
            "requesting_service": "BACKEND",  # Uppercase
            "target_resource": "user_data",
            "user_context": {
                "user_id": "test_user",
                "tier": "EARLY"  # Uppercase
            },
            "operation": "read"
        }

        result = self.validator.validate_cross_service_request(request)
        self.assertTrue(result.is_authorized)

    def test_special_characters_in_user_id(self):
        """Test handling of special characters in user IDs."""
        request = {
            "requesting_service": "backend",
            "target_resource": "user_data",
            "user_context": {
                "user_id": "user@example.com",  # Email format
                "tier": "early"
            },
            "operation": "read"
        }

        result = self.validator.validate_cross_service_request(request)
        self.assertTrue(result.is_authorized)
        self.assertEqual(result.user_context["user_id"], "user@example.com")

    def test_concurrent_validation_safety(self):
        """Test that validator is safe for concurrent access."""
        import threading
        import time

        results = []

        def validate_request(user_id):
            request = {
                "requesting_service": "backend",
                "target_resource": "user_data",
                "user_context": {
                    "user_id": f"user_{user_id}",
                    "tier": "early"
                },
                "operation": "read"
            }
            result = self.validator.validate_cross_service_request(request)
            results.append((user_id, result.is_authorized, result.user_context["user_id"]))

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=validate_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all validations succeeded and user IDs are correct
        self.assertEqual(len(results), 10)
        for user_id, authorized, returned_user_id in results:
            self.assertTrue(authorized)
            self.assertEqual(returned_user_id, f"user_{user_id}")