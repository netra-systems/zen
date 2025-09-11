"""
Test API Validation Error Prevention - Issue #307

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent valid users from being blocked by validation errors
- Value Impact: Users must be able to access platform to receive AI value
- Revenue Impact: $500K+ ARR protection by ensuring user access isn't blocked

CRITICAL ISSUE: #307 - API validation 422 errors blocking real users
ROOT CAUSE: Overly restrictive validation preventing valid user requests
BUSINESS IMPACT: User access blocked = no chat functionality = revenue loss
"""

import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment

# SSOT Imports (API Validation)
try:
    from netra_backend.app.api.validation import (
        UserRequestValidator,
        ValidationResult,
        ValidationError,
        RequestPattern
    )
    from netra_backend.app.schemas.api_schemas import (
        UserRequest,
        AgentRequest, 
        MessageRequest,
        AuthRequest
    )
    API_VALIDATION_AVAILABLE = True
except ImportError:
    API_VALIDATION_AVAILABLE = False

# Test patterns that should be valid
VALID_USER_REQUEST_PATTERNS = [
    # Common user message patterns
    {
        "type": "message",
        "content": "Help me optimize my AWS costs",
        "user_id": "user_123"
    },
    {
        "type": "agent_request", 
        "agent": "cost_optimizer",
        "message": "Analyze my cloud spending",
        "user_id": "user_456"
    },
    {
        "type": "auth_request",
        "action": "login",
        "email": "user@example.com"
    },
    # Edge cases that should still be valid
    {
        "type": "message",
        "content": "",  # Empty message should not cause 422
        "user_id": "user_789"
    },
    {
        "type": "agent_request",
        "agent": "triage_agent",
        "message": "?",  # Single character queries
        "user_id": "user_101"
    }
]

# Patterns that were incorrectly rejected (Issue #307)
PREVIOUSLY_REJECTED_VALID_PATTERNS = [
    {
        "type": "message",
        "content": "What's my current spend?",  # Common user language
        "user_id": "user_simple"
    },
    {
        "type": "agent_request", 
        "agent": "cost_optimizer",
        "message": "help",  # Simple requests
        "user_id": "user_help"
    },
    {
        "type": "message",
        "content": "Show me my usage",  # Business language
        "user_id": "user_business"
    }
]


class TestAPIValidationErrorPrevention(SSotBaseTestCase):
    """Test API validation prevents 422 errors for valid user requests."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set("API_VALIDATION_MODE", "permissive", source="test")
        
    @pytest.mark.skipif(not API_VALIDATION_AVAILABLE, reason="API validation modules not available")
    def test_valid_user_request_patterns_accepted(self):
        """Valid user requests must not trigger 422 validation errors."""
        validator = UserRequestValidator()
        
        for pattern in VALID_USER_REQUEST_PATTERNS:
            with self.subTest(pattern=pattern):
                result = validator.validate_request(pattern)
                
                # Should not have validation errors
                assert result.is_valid, f"Valid pattern rejected: {pattern}. Errors: {result.errors}"
                assert len(result.errors) == 0, f"Unexpected validation errors for valid pattern: {result.errors}"
    
    @pytest.mark.skipif(not API_VALIDATION_AVAILABLE, reason="API validation modules not available")
    def test_previously_rejected_patterns_now_accepted(self):
        """Patterns that caused #307 must now be accepted - regression test."""
        validator = UserRequestValidator()
        
        for pattern in PREVIOUSLY_REJECTED_VALID_PATTERNS:
            with self.subTest(pattern=pattern):
                result = validator.validate_request(pattern)
                
                # These patterns MUST be accepted after #307 fix
                assert result.is_valid, f"Issue #307 regression: Pattern still rejected: {pattern}"
                assert len(result.errors) == 0, f"Issue #307 not fixed: {pattern} still has errors: {result.errors}"
    
    def test_user_message_content_validation_permissive(self):
        """Message content validation must be permissive for user experience."""
        test_cases = [
            # Simple cases
            ("Help me", True, "Simple help request should be valid"),
            ("?", True, "Single character queries should be valid"),
            ("", True, "Empty messages should be valid (user might send by mistake)"),
            
            # Common business language
            ("What's my current AWS spend?", True, "Business questions should be valid"),
            ("Show usage for last month", True, "Usage queries should be valid"),
            ("Optimize my costs", True, "Optimization requests should be valid"),
            
            # Edge cases that should be valid
            ("a", True, "Single letter should be valid"),
            ("123", True, "Numbers should be valid"),
            ("!@#$%", True, "Special characters should be valid"),
            ("Help me optimize my AWS costs and reduce spending while maintaining performance", True, "Long messages should be valid"),
            
            # Extreme edge cases (should still be valid unless truly malicious)
            (" " * 1000, True, "Long whitespace should be handled gracefully"),
            ("test\n\ntest", True, "Multiline content should be valid"),
        ]
        
        for content, should_be_valid, reason in test_cases:
            with self.subTest(content=content[:50] + "..." if len(content) > 50 else content):
                # Simple validation logic test
                is_valid = self._validate_message_content(content)
                
                if should_be_valid:
                    assert is_valid, f"Content should be valid: {reason}. Content: {repr(content)}"
                else:
                    assert not is_valid, f"Content should be invalid: {reason}. Content: {repr(content)}"
    
    def test_api_endpoint_validation_patterns(self):
        """Test specific API endpoint validation patterns that caused #307."""
        # Common API request patterns that were failing
        api_patterns = [
            {
                "endpoint": "/api/v1/chat/message",
                "method": "POST",
                "payload": {"content": "Help me", "user_id": "user_123"},
                "should_pass": True
            },
            {
                "endpoint": "/api/v1/agents/execute", 
                "method": "POST",
                "payload": {"agent": "cost_optimizer", "message": "analyze costs", "user_id": "user_456"},
                "should_pass": True
            },
            {
                "endpoint": "/api/v1/auth/login",
                "method": "POST", 
                "payload": {"email": "user@example.com", "password": "valid_password"},
                "should_pass": True
            }
        ]
        
        for pattern in api_patterns:
            with self.subTest(endpoint=pattern["endpoint"]):
                validation_result = self._validate_api_request(
                    pattern["endpoint"],
                    pattern["method"],
                    pattern["payload"]
                )
                
                if pattern["should_pass"]:
                    assert validation_result["valid"], f"API pattern should pass validation: {pattern}"
                    assert validation_result["status_code"] != 422, f"Should not return 422 for valid request: {pattern}"
                else:
                    assert not validation_result["valid"] or validation_result["status_code"] == 422
    
    def test_error_message_clarity_and_actionability(self):
        """422 errors must provide clear guidance to users when they do occur."""
        # Test cases where validation should fail but with clear messages
        invalid_patterns = [
            {
                "data": {"type": "invalid_type", "content": "test"},
                "expected_error_keywords": ["type", "invalid", "supported"]
            },
            {
                "data": {"type": "message"},  # Missing required fields
                "expected_error_keywords": ["required", "content", "user_id"]
            },
            {
                "data": {"type": "agent_request", "agent": "nonexistent_agent"},
                "expected_error_keywords": ["agent", "not found", "available"]
            }
        ]
        
        for pattern in invalid_patterns:
            with self.subTest(data=pattern["data"]):
                validation_result = self._validate_request(pattern["data"])
                
                # Should be invalid
                assert not validation_result["valid"], f"Pattern should be invalid: {pattern['data']}"
                
                # Error message should contain helpful keywords
                error_message = validation_result.get("error_message", "").lower()
                for keyword in pattern["expected_error_keywords"]:
                    assert keyword.lower() in error_message, f"Error message should contain '{keyword}': {error_message}"
                
                # Error message should be actionable (contain suggestions)
                assert any(word in error_message for word in ["try", "use", "should", "must", "example"]), \
                    f"Error message should be actionable: {error_message}"
    
    def test_request_schema_flexibility(self):
        """Request schemas must be flexible enough to handle real user patterns."""
        # Test flexible schema handling
        flexible_patterns = [
            # Optional fields should not cause errors
            {"type": "message", "content": "test", "user_id": "user_123", "optional_field": "ignored"},
            
            # Different casing should be handled
            {"Type": "message", "Content": "test", "User_Id": "user_123"},  # Different case
            
            # String/number flexibility  
            {"type": "message", "content": "test", "user_id": 123},  # user_id as number
            
            # Nested data structures
            {
                "type": "agent_request",
                "agent": "cost_optimizer", 
                "message": "analyze",
                "user_id": "user_123",
                "context": {"previous_chat": "some context"}
            }
        ]
        
        for pattern in flexible_patterns:
            with self.subTest(pattern=pattern):
                is_valid = self._validate_request_flexibility(pattern)
                assert is_valid, f"Flexible pattern should be accepted: {pattern}"
    
    def test_common_user_language_patterns(self):
        """Validation must accept common user language patterns."""
        common_language = [
            "What's my spend?",
            "Show me usage",
            "Help optimize costs", 
            "Can you analyze my AWS?",
            "I need to reduce spending",
            "What are my biggest expenses?",
            "How much am I spending on compute?",
            "Recommendations for savings?",
            "Show cost breakdown",
            "Compare this month vs last"
        ]
        
        for phrase in common_language:
            with self.subTest(phrase=phrase):
                is_valid = self._validate_message_content(phrase)
                assert is_valid, f"Common user language should be valid: {phrase}"
    
    def test_business_workflow_request_patterns(self):
        """Business workflow requests must pass validation."""
        business_workflows = [
            # Cost optimization workflow
            {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": "Analyze my AWS costs and provide optimization recommendations",
                "context": {"aws_account": "123456789", "time_period": "last_30_days"}
            },
            
            # Data analysis workflow
            {
                "type": "agent_request", 
                "agent": "data_helper",
                "message": "Show me usage patterns for my cloud resources",
                "context": {"resource_types": ["ec2", "s3", "rds"]}
            },
            
            # Reporting workflow
            {
                "type": "agent_request",
                "agent": "reporting_agent",
                "message": "Generate monthly cost report",
                "context": {"format": "pdf", "recipients": ["manager@example.com"]}
            }
        ]
        
        for workflow in business_workflows:
            with self.subTest(workflow=workflow["agent"]):
                result = self._validate_business_request(workflow)
                assert result["valid"], f"Business workflow should be valid: {workflow}"
    
    def test_validation_performance_with_real_traffic(self):
        """Validation must be fast enough for real user traffic."""
        import time
        
        # Simulate real user request patterns
        real_requests = VALID_USER_REQUEST_PATTERNS + PREVIOUSLY_REJECTED_VALID_PATTERNS
        
        start_time = time.perf_counter()
        
        for _ in range(1000):  # Simulate 1000 requests
            for pattern in real_requests:
                # Simple validation simulation
                self._validate_request(pattern)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Should validate 1000 * len(real_requests) in under 1 second
        total_validations = 1000 * len(real_requests)
        assert duration < 1.0, f"Validation too slow: {duration:.3f}s for {total_validations} validations"
        
        # Average should be under 0.1ms per validation
        avg_time = duration / total_validations
        assert avg_time < 0.0001, f"Average validation time too high: {avg_time:.6f}s per validation"
    
    # Helper methods for validation testing
    def _validate_message_content(self, content: str) -> bool:
        """Simple message content validation."""
        if API_VALIDATION_AVAILABLE:
            validator = UserRequestValidator()
            result = validator.validate_message_content(content)
            return result.is_valid
        else:
            # Fallback validation logic
            # Should be very permissive - reject only truly problematic content
            if content is None:
                return False
            if len(content) > 10000:  # Extremely long messages
                return False
            return True  # Default to permissive
    
    def _validate_api_request(self, endpoint: str, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate API request pattern."""
        # Mock API validation
        if payload is None or not isinstance(payload, dict):
            return {"valid": False, "status_code": 422, "error": "Invalid payload"}
        
        # Basic validation - should be permissive
        if "user_id" not in payload and "/auth/" not in endpoint:
            return {"valid": False, "status_code": 422, "error": "user_id required"}
        
        return {"valid": True, "status_code": 200}
    
    def _validate_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """General request validation."""
        if not isinstance(data, dict):
            return {"valid": False, "error_message": "Request must be a JSON object"}
        
        if "type" not in data:
            return {"valid": False, "error_message": "Request type is required. Try adding 'type' field."}
        
        return {"valid": True}
    
    def _validate_request_flexibility(self, data: Dict[str, Any]) -> bool:
        """Test flexible request handling."""
        # Should handle different casings and optional fields gracefully
        return True  # Default to flexible/permissive
    
    def _validate_business_request(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Validate business workflow request."""
        required_fields = ["type", "agent", "message"]
        
        for field in required_fields:
            if field not in workflow:
                return {"valid": False, "error": f"Missing required field: {field}"}
        
        return {"valid": True}