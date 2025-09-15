"""
Unit Tests for Agent Execution Message Validation - Context and Security Validation

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All (Free/Early/Mid/Enterprise/Platform) - Security and Compliance Foundation
- Business Goal: Ensure secure agent execution through proper message validation for Golden Path
- Value Impact: Message validation protects $500K+ ARR by preventing security vulnerabilities
- Strategic Impact: Security foundation that enables enterprise customer trust and compliance
- Revenue Protection: Without proper validation, security breaches could destroy customer trust -> churn

PURPOSE: This test suite validates the message validation functionality that ensures
agent execution contexts are properly validated and secure during the Golden Path
user flow. Message validation is critical security infrastructure that protects
both user data and system integrity during AI interactions.

KEY COVERAGE:
1. User execution context validation
2. Message authentication and authorization
3. Input sanitization and validation
4. Context isolation between users
5. Security policy enforcement
6. Performance requirements for validation
7. Error handling for invalid contexts

GOLDEN PATH PROTECTION:
Tests ensure message validation properly authenticates users, validates execution
contexts, and enforces security policies that protect the entire $500K+ ARR
AI interaction pipeline from security vulnerabilities and data breaches.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Import user context for validation testing
from netra_backend.app.services.user_execution_context import UserExecutionContext


class ValidationResult(Enum):
    """Message validation results"""
    VALID = "valid"
    INVALID = "invalid"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


class SecurityLevel(Enum):
    """Security levels for validation"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high" 
    ENTERPRISE = "enterprise"


@dataclass
class ValidationReport:
    """Represents a message validation report"""
    validation_id: str
    result: ValidationResult
    security_level: SecurityLevel
    user_id: str
    message_id: str
    validation_time: float
    violations: List[str]
    context_validated: bool
    auth_validated: bool
    input_sanitized: bool
    metadata: Dict[str, Any]


class MockAgentExecutionValidator:
    """Mock agent execution message validator for testing validation logic"""
    
    def __init__(self):
        self.validation_reports = []
        self.security_policies = self._initialize_security_policies()
        self.validation_metrics = {
            "total_validations": 0,
            "valid_messages": 0,
            "invalid_messages": 0,
            "blocked_messages": 0,
            "security_violations": 0
        }
        self.blocked_users = set()
        self.rate_limits = {}
        
    def _initialize_security_policies(self) -> Dict[str, Any]:
        """Initialize security validation policies"""
        return {
            "max_message_length": 10000,
            "max_payload_size_bytes": 50000,
            "allowed_message_types": [
                "user_request", "optimization_request", "data_query", 
                "agent_started", "agent_thinking", "tool_executing",
                "tool_completed", "agent_completed", "agent_error"
            ],
            "blocked_patterns": [
                r"<script[^>]*>.*?</script>",
                r"DROP\s+TABLE",
                r"eval\s*\(",
                r"exec\s*\(",
                r"__import__",
                r"subprocess",
                r"os\.system"
            ],
            "rate_limit_per_minute": 100,
            "enterprise_rate_limit_per_minute": 500,
            "required_context_fields": [
                "user_id", "thread_id", "run_id", "request_id"
            ]
        }
    
    async def validate_agent_execution_message(
        self,
        message: Dict[str, Any],
        context: UserExecutionContext,
        security_level: SecurityLevel = SecurityLevel.MEDIUM
    ) -> ValidationReport:
        """Validate agent execution message with comprehensive security checks"""
        
        validation_start = time.time()
        validation_id = f"val_{int(time.time() * 1000)}_{len(self.validation_reports)}"
        violations = []
        
        # Initialize validation state
        context_validated = False
        auth_validated = False
        input_sanitized = False
        
        try:
            # 1. Context Validation
            context_result = await self._validate_execution_context(context, security_level)
            if context_result["valid"]:
                context_validated = True
            else:
                violations.extend(context_result["violations"])
            
            # 2. Authentication Validation
            auth_result = await self._validate_authentication(message, context, security_level)
            if auth_result["valid"]:
                auth_validated = True
            else:
                violations.extend(auth_result["violations"])
            
            # 3. Message Structure Validation
            structure_result = self._validate_message_structure(message)
            if not structure_result["valid"]:
                violations.extend(structure_result["violations"])
            
            # 4. Input Sanitization
            sanitization_result = self._validate_and_sanitize_input(message)
            if sanitization_result["safe"]:
                input_sanitized = True
            else:
                violations.extend(sanitization_result["violations"])
            
            # 5. Rate Limiting Check
            rate_limit_result = self._check_rate_limits(context.user_id, security_level)
            if not rate_limit_result["within_limits"]:
                violations.extend(rate_limit_result["violations"])
            
            # 6. Security Policy Enforcement
            policy_result = self._enforce_security_policies(message, context, security_level)
            if not policy_result["compliant"]:
                violations.extend(policy_result["violations"])
            
            # Determine final validation result
            if len(violations) == 0:
                result = ValidationResult.VALID
            elif any("CRITICAL" in v for v in violations):
                result = ValidationResult.BLOCKED
            elif any("SUSPICIOUS" in v for v in violations):
                result = ValidationResult.SUSPICIOUS
            else:
                result = ValidationResult.INVALID
            
            # Create validation report
            validation_time = time.time() - validation_start
            report = ValidationReport(
                validation_id=validation_id,
                result=result,
                security_level=security_level,
                user_id=context.user_id,
                message_id=message.get("id", "unknown"),
                validation_time=validation_time,
                violations=violations,
                context_validated=context_validated,
                auth_validated=auth_validated,
                input_sanitized=input_sanitized,
                metadata={
                    "message_type": message.get("type"),
                    "payload_size": len(json.dumps(message)),
                    "user_tier": getattr(context, "user_tier", "free")
                }
            )
            
            # Update metrics
            self.validation_metrics["total_validations"] += 1
            if result == ValidationResult.VALID:
                self.validation_metrics["valid_messages"] += 1
            elif result == ValidationResult.BLOCKED:
                self.validation_metrics["blocked_messages"] += 1
                self.blocked_users.add(context.user_id)
            else:
                self.validation_metrics["invalid_messages"] += 1
            
            if violations:
                self.validation_metrics["security_violations"] += 1
            
            # Store report
            self.validation_reports.append(report)
            
            return report
            
        except Exception as e:
            # Handle validation errors
            error_report = ValidationReport(
                validation_id=validation_id,
                result=ValidationResult.BLOCKED,
                security_level=security_level,
                user_id=context.user_id if context else "unknown",
                message_id=message.get("id", "unknown"),
                validation_time=time.time() - validation_start,
                violations=[f"CRITICAL: Validation error - {str(e)}"],
                context_validated=False,
                auth_validated=False,
                input_sanitized=False,
                metadata={"error": str(e)}
            )
            
            self.validation_reports.append(error_report)
            self.validation_metrics["blocked_messages"] += 1
            
            return error_report
    
    async def _validate_execution_context(
        self, 
        context: UserExecutionContext, 
        security_level: SecurityLevel
    ) -> Dict[str, Any]:
        """Validate user execution context"""
        
        violations = []
        
        # Check required fields
        required_fields = self.security_policies["required_context_fields"]
        for field in required_fields:
            if not hasattr(context, field) or not getattr(context, field):
                violations.append(f"Missing required context field: {field}")
        
        # Validate user ID format
        if hasattr(context, "user_id"):
            user_id = context.user_id
            if len(user_id) < 3 or len(user_id) > 50:
                violations.append("Invalid user_id length")
            if not user_id.replace("_", "").replace("-", "").isalnum():
                violations.append("Invalid user_id format")
        
        # Check for blocked users
        if hasattr(context, "user_id") and context.user_id in self.blocked_users:
            violations.append("CRITICAL: User is blocked")
        
        # Enterprise security checks
        if security_level == SecurityLevel.ENTERPRISE:
            if not hasattr(context, "user_tier") or context.user_tier != "enterprise":
                violations.append("Enterprise security required but user not enterprise")
        
        return {
            "valid": len(violations) == 0,
            "violations": violations
        }
    
    async def _validate_authentication(
        self,
        message: Dict[str, Any],
        context: UserExecutionContext,
        security_level: SecurityLevel
    ) -> Dict[str, Any]:
        """Validate message authentication"""
        
        violations = []
        
        # Check user ID consistency
        message_user_id = message.get("user_id")
        context_user_id = getattr(context, "user_id", None)
        
        if message_user_id and context_user_id:
            if message_user_id != context_user_id:
                violations.append("CRITICAL: User ID mismatch between message and context")
        
        # Validate timestamp freshness (prevent replay attacks)
        message_timestamp = message.get("timestamp")
        if message_timestamp:
            current_time = time.time()
            if isinstance(message_timestamp, (int, float)):
                age_seconds = current_time - message_timestamp
                if age_seconds > 300:  # 5 minute maximum age
                    violations.append("SUSPICIOUS: Message timestamp too old (possible replay attack)")
                elif age_seconds < -60:  # 1 minute maximum future
                    violations.append("SUSPICIOUS: Message timestamp in future")
        
        # Check for required authentication fields
        if security_level in [SecurityLevel.HIGH, SecurityLevel.ENTERPRISE]:
            if not message.get("thread_id"):
                violations.append("Missing thread_id for high security level")
            if not message.get("run_id"):
                violations.append("Missing run_id for high security level")
        
        return {
            "valid": len(violations) == 0,
            "violations": violations
        }
    
    def _validate_message_structure(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Validate message structure and format"""
        
        violations = []
        
        # Check required fields
        if not message.get("type"):
            violations.append("Missing message type")
        
        # Check message type is allowed
        message_type = message.get("type")
        if message_type and message_type not in self.security_policies["allowed_message_types"]:
            violations.append(f"SUSPICIOUS: Unknown message type: {message_type}")
        
        # Check message size
        message_json = json.dumps(message)
        if len(message_json) > self.security_policies["max_payload_size_bytes"]:
            violations.append(f"CRITICAL: Message exceeds size limit ({len(message_json)} bytes)")
        
        # Check content length if present
        content = message.get("content", "")
        if isinstance(content, str) and len(content) > self.security_policies["max_message_length"]:
            violations.append(f"Content exceeds length limit ({len(content)} characters)")
        
        return {
            "valid": len(violations) == 0,
            "violations": violations
        }
    
    def _validate_and_sanitize_input(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize input content"""
        
        violations = []
        
        # Check content for suspicious patterns
        content = str(message.get("content", ""))
        payload = json.dumps(message.get("payload", {}))
        
        import re
        
        for pattern in self.security_policies["blocked_patterns"]:
            if re.search(pattern, content, re.IGNORECASE) or re.search(pattern, payload, re.IGNORECASE):
                violations.append(f"CRITICAL: Blocked pattern detected: {pattern}")
        
        # Check for common injection attempts
        dangerous_strings = [
            "javascript:", "data:", "vbscript:", "onload=", "onerror=",
            "../", "..\\", "/etc/passwd", "cmd.exe", "powershell"
        ]
        
        combined_text = (content + " " + payload).lower()
        for dangerous in dangerous_strings:
            if dangerous in combined_text:
                violations.append(f"SUSPICIOUS: Potentially dangerous string: {dangerous}")
        
        return {
            "safe": len([v for v in violations if "CRITICAL" in v]) == 0,
            "violations": violations
        }
    
    def _check_rate_limits(self, user_id: str, security_level: SecurityLevel) -> Dict[str, Any]:
        """Check rate limiting for user"""
        
        violations = []
        current_time = time.time()
        
        # Initialize rate limit tracking for user
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = {
                "requests": [],
                "last_reset": current_time
            }
        
        user_limits = self.rate_limits[user_id]
        
        # Clean old requests (older than 1 minute)
        minute_ago = current_time - 60
        user_limits["requests"] = [t for t in user_limits["requests"] if t > minute_ago]
        
        # Add current request
        user_limits["requests"].append(current_time)
        
        # Check limits based on security level
        if security_level == SecurityLevel.ENTERPRISE:
            limit = self.security_policies["enterprise_rate_limit_per_minute"]
        else:
            limit = self.security_policies["rate_limit_per_minute"]
        
        if len(user_limits["requests"]) > limit:
            violations.append(f"CRITICAL: Rate limit exceeded ({len(user_limits['requests'])} > {limit} per minute)")
        
        return {
            "within_limits": len(violations) == 0,
            "violations": violations
        }
    
    def _enforce_security_policies(
        self,
        message: Dict[str, Any], 
        context: UserExecutionContext,
        security_level: SecurityLevel
    ) -> Dict[str, Any]:
        """Enforce additional security policies"""
        
        violations = []
        
        # Enterprise-specific policies
        if security_level == SecurityLevel.ENTERPRISE:
            # Require encrypted payloads for enterprise (simulated check)
            if not message.get("encrypted") and message.get("sensitive_data"):
                violations.append("Enterprise policy: Sensitive data must be encrypted")
        
        # Check for data exfiltration attempts
        content = str(message.get("content", "")).lower()
        if any(term in content for term in ["download", "export", "backup", "dump"]):
            if not message.get("authorized_export"):
                violations.append("SUSPICIOUS: Potential data exfiltration attempt")
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations
        }
    
    def get_validation_metrics(self) -> Dict[str, Any]:
        """Get validation performance metrics"""
        return self.validation_metrics.copy()
    
    def get_validation_reports_for_user(self, user_id: str) -> List[ValidationReport]:
        """Get validation reports for specific user"""
        return [report for report in self.validation_reports if report.user_id == user_id]


class TestAgentExecutionMessageValidation(SSotAsyncTestCase):
    """Unit tests for agent execution message validation
    
    This test class validates the critical message validation capabilities that
    ensure secure agent execution in the Golden Path user flow. These tests
    focus on security validation logic without requiring complex
    infrastructure dependencies.
    
    Tests MUST ensure validation can:
    1. Validate user execution contexts properly
    2. Detect and block malicious message content
    3. Enforce authentication and authorization
    4. Apply rate limiting and security policies
    5. Maintain performance requirements for validation
    6. Handle validation errors gracefully
    """
    
    def setup_method(self, method=None):
        """Setup for each test with proper isolation"""
        super().setup_method(method)
        
        # Create isolated user context for this test
        self.user_context = SSotMockFactory.create_mock_user_context(
            user_id=f"test_user_{self.get_test_context().test_id}",
            thread_id=f"test_thread_{self.get_test_context().test_id}",
            run_id=f"test_run_{self.get_test_context().test_id}",
            request_id=f"test_req_{self.get_test_context().test_id}"
        )
        
        # Create enterprise user context
        self.enterprise_context = SSotMockFactory.create_mock_user_context(
            user_id="enterprise_user",
            thread_id="enterprise_thread",
            run_id="enterprise_run"
        )
        self.enterprise_context.user_tier = "enterprise"
        
        # Create message validator instance
        self.validator = MockAgentExecutionValidator()
    
    # ========================================================================
    # CONTEXT VALIDATION TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_valid_execution_context_validation(self):
        """Test validation of valid user execution context
        
        Business Impact: Ensures legitimate users can execute agents
        without validation blocking their Golden Path experience.
        """
        # Create valid agent execution message
        valid_message = {
            "id": "msg_valid_001",
            "type": "user_request",
            "content": "Help me optimize my AI costs",
            "user_id": self.user_context.user_id,
            "thread_id": self.user_context.thread_id,
            "run_id": self.user_context.run_id,
            "timestamp": time.time()
        }
        
        # Validate message
        validation_start = time.time()
        report = await self.validator.validate_agent_execution_message(
            valid_message, self.user_context, SecurityLevel.MEDIUM
        )
        validation_time = time.time() - validation_start
        
        # Verify successful validation
        assert report.result == ValidationResult.VALID
        assert report.context_validated is True
        assert report.auth_validated is True
        assert report.input_sanitized is True
        assert len(report.violations) == 0
        
        # Verify validation metadata
        assert report.user_id == self.user_context.user_id
        assert report.security_level == SecurityLevel.MEDIUM
        assert report.validation_time > 0
        
        # Verify performance
        assert validation_time < 0.01, f"Validation took {validation_time:.4f}s, should be < 0.01s"
        
        self.record_metric("valid_context_validation_time", validation_time)
        self.record_metric("valid_context_validated_successfully", True)
    
    @pytest.mark.unit
    async def test_invalid_execution_context_validation(self):
        """Test validation of invalid user execution context
        
        Business Impact: Prevents unauthorized access and protects system
        security by blocking invalid execution contexts.
        """
        # Create context with missing required fields
        invalid_context = SSotMockFactory.create_mock_user_context(
            user_id="",  # Invalid empty user ID
            thread_id="",  # Invalid empty thread ID
            run_id=self.user_context.run_id
        )
        
        invalid_message = {
            "id": "msg_invalid_001",
            "type": "user_request",
            "content": "Test with invalid context",
            "timestamp": time.time()
        }
        
        # Validate message with invalid context
        report = await self.validator.validate_agent_execution_message(
            invalid_message, invalid_context, SecurityLevel.HIGH
        )
        
        # Verify validation failure
        assert report.result in [ValidationResult.INVALID, ValidationResult.BLOCKED]
        assert report.context_validated is False
        assert len(report.violations) > 0
        
        # Verify specific violations
        violation_text = " ".join(report.violations)
        assert "user_id" in violation_text.lower()
        assert "thread_id" in violation_text.lower()
        
        self.record_metric("invalid_context_blocked", True)
        self.record_metric("context_violations_detected", len(report.violations))
    
    @pytest.mark.unit
    async def test_enterprise_security_level_validation(self):
        """Test validation with enterprise security level
        
        Business Impact: Ensures enterprise customers receive enhanced
        security validation appropriate for their security requirements.
        """
        # Create enterprise-level message
        enterprise_message = {
            "id": "msg_enterprise_001",
            "type": "optimization_request",
            "content": "Enterprise cost optimization analysis",
            "user_id": self.enterprise_context.user_id,
            "thread_id": self.enterprise_context.thread_id,
            "run_id": self.enterprise_context.run_id,
            "timestamp": time.time(),
            "sensitive_data": True,
            "encrypted": True  # Enterprise requirement
        }
        
        # Validate with enterprise security level
        report = await self.validator.validate_agent_execution_message(
            enterprise_message, self.enterprise_context, SecurityLevel.ENTERPRISE
        )
        
        # Verify enterprise validation success
        assert report.result == ValidationResult.VALID
        assert report.security_level == SecurityLevel.ENTERPRISE
        assert report.context_validated is True
        
        # Test enterprise validation failure (missing encryption)
        unencrypted_message = enterprise_message.copy()
        unencrypted_message["encrypted"] = False
        
        report2 = await self.validator.validate_agent_execution_message(
            unencrypted_message, self.enterprise_context, SecurityLevel.ENTERPRISE
        )
        
        # Should detect enterprise policy violation
        assert report2.result != ValidationResult.VALID
        assert len(report2.violations) > 0
        assert any("encrypt" in v.lower() for v in report2.violations)
        
        self.record_metric("enterprise_validation_enforced", True)
    
    # ========================================================================
    # AUTHENTICATION VALIDATION TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_user_id_mismatch_detection(self):
        """Test detection of user ID mismatches
        
        Business Impact: Prevents user impersonation attacks that could
        compromise user data and system security.
        """
        # Create message with mismatched user ID
        mismatched_message = {
            "id": "msg_mismatch_001",
            "type": "user_request",
            "content": "Attempt with wrong user ID",
            "user_id": "different_user_id",  # Doesn't match context
            "thread_id": self.user_context.thread_id,
            "timestamp": time.time()
        }
        
        # Validate message with mismatched user ID
        report = await self.validator.validate_agent_execution_message(
            mismatched_message, self.user_context, SecurityLevel.HIGH
        )
        
        # Verify mismatch detection
        assert report.result == ValidationResult.BLOCKED
        assert report.auth_validated is False
        assert len(report.violations) > 0
        
        # Check for specific user ID mismatch violation
        mismatch_violations = [v for v in report.violations if "mismatch" in v.lower()]
        assert len(mismatch_violations) > 0
        assert "CRITICAL" in mismatch_violations[0]
        
        self.record_metric("user_id_mismatch_detected", True)
    
    @pytest.mark.unit
    async def test_timestamp_freshness_validation(self):
        """Test message timestamp freshness validation
        
        Business Impact: Prevents replay attacks that could compromise
        system security by reusing old authenticated messages.
        """
        current_time = time.time()
        
        # Test old timestamp (replay attack)
        old_message = {
            "id": "msg_old_001",
            "type": "user_request", 
            "content": "Old message test",
            "user_id": self.user_context.user_id,
            "timestamp": current_time - 600  # 10 minutes old
        }
        
        report_old = await self.validator.validate_agent_execution_message(
            old_message, self.user_context, SecurityLevel.HIGH
        )
        
        # Should detect old timestamp
        assert report_old.result in [ValidationResult.SUSPICIOUS, ValidationResult.INVALID]
        timestamp_violations = [v for v in report_old.violations if "timestamp" in v.lower()]
        assert len(timestamp_violations) > 0
        
        # Test future timestamp
        future_message = {
            "id": "msg_future_001",
            "type": "user_request",
            "content": "Future message test",
            "user_id": self.user_context.user_id,
            "timestamp": current_time + 120  # 2 minutes in future
        }
        
        report_future = await self.validator.validate_agent_execution_message(
            future_message, self.user_context, SecurityLevel.HIGH
        )
        
        # Should detect future timestamp
        assert report_future.result in [ValidationResult.SUSPICIOUS, ValidationResult.INVALID]
        
        # Test valid timestamp
        valid_message = {
            "id": "msg_valid_time_001",
            "type": "user_request",
            "content": "Valid timestamp test",
            "user_id": self.user_context.user_id,
            "timestamp": current_time - 30  # 30 seconds old (valid)
        }
        
        report_valid = await self.validator.validate_agent_execution_message(
            valid_message, self.user_context, SecurityLevel.MEDIUM
        )
        
        # Should accept valid timestamp
        timestamp_violations_valid = [v for v in report_valid.violations if "timestamp" in v.lower()]
        assert len(timestamp_violations_valid) == 0
        
        self.record_metric("timestamp_validation_working", True)
    
    # ========================================================================
    # INPUT SANITIZATION TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_malicious_script_detection(self):
        """Test detection of malicious script content
        
        Business Impact: Protects against XSS and script injection attacks
        that could compromise user data or system security.
        """
        # Test various malicious script patterns
        malicious_messages = [
            {
                "id": "msg_xss_001",
                "type": "user_request",
                "content": "<script>alert('xss')</script>help me",
                "user_id": self.user_context.user_id,
                "timestamp": time.time()
            },
            {
                "id": "msg_eval_001", 
                "type": "user_request",
                "content": "eval('malicious code')",
                "user_id": self.user_context.user_id,
                "timestamp": time.time()
            },
            {
                "id": "msg_exec_001",
                "type": "user_request",
                "content": "exec('import os; os.system(\"rm -rf /\")')",
                "user_id": self.user_context.user_id,
                "timestamp": time.time()
            }
        ]
        
        blocked_count = 0
        for malicious_msg in malicious_messages:
            report = await self.validator.validate_agent_execution_message(
                malicious_msg, self.user_context, SecurityLevel.HIGH
            )
            
            # Should be blocked or marked suspicious
            assert report.result in [ValidationResult.BLOCKED, ValidationResult.SUSPICIOUS]
            assert report.input_sanitized is False
            assert len(report.violations) > 0
            
            # Check for critical violations
            critical_violations = [v for v in report.violations if "CRITICAL" in v]
            if len(critical_violations) > 0:
                blocked_count += 1
        
        # At least one should be blocked outright
        assert blocked_count > 0
        
        self.record_metric("malicious_scripts_detected", len(malicious_messages))
        self.record_metric("malicious_scripts_blocked", blocked_count)
    
    @pytest.mark.unit
    async def test_sql_injection_detection(self):
        """Test detection of SQL injection attempts
        
        Business Impact: Protects against database attacks that could
        compromise user data or system integrity.
        """
        sql_injection_messages = [
            {
                "id": "msg_sql_001",
                "type": "user_request",
                "content": "'; DROP TABLE users; --",
                "user_id": self.user_context.user_id,
                "timestamp": time.time()
            },
            {
                "id": "msg_sql_002",
                "type": "user_request", 
                "content": "1' OR '1'='1",
                "user_id": self.user_context.user_id,
                "timestamp": time.time()
            }
        ]
        
        for sql_msg in sql_injection_messages:
            report = await self.validator.validate_agent_execution_message(
                sql_msg, self.user_context, SecurityLevel.HIGH
            )
            
            # Should detect SQL injection patterns
            assert report.result != ValidationResult.VALID
            assert len(report.violations) > 0
            
            # Check for blocked pattern detection
            pattern_violations = [v for v in report.violations if "pattern" in v.lower()]
            assert len(pattern_violations) > 0
        
        self.record_metric("sql_injection_attempts_detected", len(sql_injection_messages))
    
    # ========================================================================
    # RATE LIMITING TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_rate_limiting_enforcement(self):
        """Test rate limiting enforcement
        
        Business Impact: Prevents abuse and DoS attacks that could
        degrade system performance for all users.
        """
        # Simulate rapid requests from same user
        rapid_requests = []
        for i in range(15):  # Exceed normal rate limit
            message = {
                "id": f"msg_rapid_{i}",
                "type": "user_request",
                "content": f"Rapid request {i}",
                "user_id": self.user_context.user_id,
                "timestamp": time.time()
            }
            rapid_requests.append(message)
        
        # Process requests and check rate limiting
        valid_count = 0
        blocked_count = 0
        
        for msg in rapid_requests:
            report = await self.validator.validate_agent_execution_message(
                msg, self.user_context, SecurityLevel.MEDIUM
            )
            
            if report.result == ValidationResult.VALID:
                valid_count += 1
            elif report.result == ValidationResult.BLOCKED:
                blocked_count += 1
                # Check for rate limit violation
                rate_violations = [v for v in report.violations if "rate" in v.lower()]
                if len(rate_violations) > 0:
                    assert "CRITICAL" in rate_violations[0]
        
        # Should allow some requests but block excessive ones
        assert valid_count > 0, "Should allow some requests"
        assert blocked_count > 0, "Should block excessive requests"
        
        self.record_metric("requests_allowed", valid_count)
        self.record_metric("requests_blocked_by_rate_limit", blocked_count)
    
    @pytest.mark.unit
    async def test_enterprise_rate_limit_differences(self):
        """Test different rate limits for enterprise users
        
        Business Impact: Ensures enterprise customers get higher rate
        limits appropriate for their business usage patterns.
        """
        # Test enterprise user gets higher limits
        enterprise_requests = []
        for i in range(20):  # More than standard limit
            message = {
                "id": f"msg_enterprise_rapid_{i}",
                "type": "optimization_request",
                "content": f"Enterprise request {i}",
                "user_id": self.enterprise_context.user_id,
                "timestamp": time.time()
            }
            enterprise_requests.append(message)
        
        enterprise_valid = 0
        enterprise_blocked = 0
        
        for msg in enterprise_requests:
            report = await self.validator.validate_agent_execution_message(
                msg, self.enterprise_context, SecurityLevel.ENTERPRISE
            )
            
            if report.result == ValidationResult.VALID:
                enterprise_valid += 1
            elif report.result == ValidationResult.BLOCKED:
                enterprise_blocked += 1
        
        # Enterprise should allow more requests than standard users
        assert enterprise_valid > 15, "Enterprise should get higher rate limits"
        
        self.record_metric("enterprise_rate_limit_higher", True)
        self.record_metric("enterprise_requests_allowed", enterprise_valid)
    
    # ========================================================================
    # PERFORMANCE TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_validation_performance_requirements(self):
        """Test validation performance requirements
        
        Business Impact: Fast validation is critical to avoid adding
        latency to Golden Path user interactions.
        """
        test_message = {
            "id": "msg_perf_001",
            "type": "user_request",
            "content": "Performance test message for validation",
            "user_id": self.user_context.user_id,
            "thread_id": self.user_context.thread_id,
            "timestamp": time.time()
        }
        
        # Measure validation times
        validation_times = []
        for i in range(20):
            start_time = time.time()
            report = await self.validator.validate_agent_execution_message(
                test_message, self.user_context, SecurityLevel.MEDIUM
            )
            end_time = time.time()
            
            assert report.result == ValidationResult.VALID
            validation_times.append(end_time - start_time)
        
        # Calculate performance metrics
        avg_time = sum(validation_times) / len(validation_times)
        max_time = max(validation_times)
        
        # Performance requirements for validation
        assert avg_time < 0.005, f"Average validation time {avg_time:.6f}s should be < 0.005s"
        assert max_time < 0.02, f"Max validation time {max_time:.6f}s should be < 0.02s"
        
        self.record_metric("average_validation_time", avg_time)
        self.record_metric("max_validation_time", max_time)
        self.record_metric("validation_performance_meets_requirements", True)
    
    @pytest.mark.unit
    async def test_concurrent_validation_performance(self):
        """Test concurrent validation performance
        
        Business Impact: System must handle multiple simultaneous
        validations without performance degradation.
        """
        # Create concurrent validation tasks
        concurrent_messages = []
        contexts = []
        
        for i in range(10):
            message = {
                "id": f"msg_concurrent_{i}",
                "type": "user_request",
                "content": f"Concurrent validation test {i}",
                "user_id": f"concurrent_user_{i}",
                "timestamp": time.time()
            }
            context = SSotMockFactory.create_mock_user_context(
                user_id=f"concurrent_user_{i}",
                thread_id=f"concurrent_thread_{i}",
                run_id=f"concurrent_run_{i}"
            )
            concurrent_messages.append(message)
            contexts.append(context)
        
        # Process validations concurrently
        start_time = time.time()
        tasks = [
            self.validator.validate_agent_execution_message(msg, ctx, SecurityLevel.MEDIUM)
            for msg, ctx in zip(concurrent_messages, contexts)
        ]
        reports = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start_time
        
        # Verify all validations successful
        successful_validations = sum(1 for r in reports if r.result == ValidationResult.VALID)
        assert successful_validations == len(concurrent_messages)
        
        # Verify concurrent performance
        assert concurrent_time < 0.1, f"Concurrent validation took {concurrent_time:.3f}s, should be < 0.1s"
        
        self.record_metric("concurrent_validations_completed", successful_validations)
        self.record_metric("concurrent_validation_time", concurrent_time)
    
    def teardown_method(self, method=None):
        """Cleanup after each test"""
        # Record final test metrics
        metrics = self.get_all_metrics()
        
        # Get validation metrics
        validation_metrics = self.validator.get_validation_metrics()
        
        # Calculate comprehensive coverage metrics
        security_tests = sum(1 for key in metrics.keys() 
                           if any(term in key for term in ["detected", "blocked", "validated"]))
        
        self.record_metric("security_validation_tests_completed", security_tests)
        self.record_metric("total_validations_performed", validation_metrics["total_validations"])
        self.record_metric("security_violations_caught", validation_metrics["security_violations"])
        self.record_metric("message_validation_complete", True)
        
        # Call parent teardown
        super().teardown_method(method)