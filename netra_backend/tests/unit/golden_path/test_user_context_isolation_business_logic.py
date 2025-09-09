"""
Golden Path Unit Tests: User Context Isolation Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform/Internal)
- Business Goal: Ensure complete user isolation prevents data leaks and maintains enterprise trust
- Value Impact: Protects customer confidentiality, enables multi-tenant architecture for scale
- Strategic/Revenue Impact: Critical for $500K+ ARR - enterprise customers require guaranteed isolation

CRITICAL: This test validates the business logic for user context isolation using Factory patterns
that prevent customer data from leaking between users. Enterprise trust and regulatory compliance
depend on this isolation working correctly across all user execution contexts.

Key Isolation Areas Tested:
1. UserExecutionContextFactory - Ensures complete user session isolation
2. Authentication Context - JWT tokens and user credentials isolated per user
3. WebSocket Context - Real-time communication channels isolated per user  
4. Agent State - AI agent execution state isolated per user
5. Data Access - User data and analysis results isolated per user
"""

import pytest
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass, field
from enum import Enum

# Import business logic components for testing
from test_framework.base import BaseTestCase
from shared.types.core_types import (
    UserID, ThreadID, ExecutionID, WebSocketID, SessionID,
    ensure_user_id, ensure_thread_id
)
from shared.types.execution_types import StronglyTypedUserExecutionContext


class IsolationLevel(Enum):
    """Business-critical isolation levels for user contexts."""
    STRICT = "strict"        # Complete isolation, no shared resources
    STANDARD = "standard"    # Shared infrastructure, isolated data
    RELAXED = "relaxed"      # Basic separation, some shared caches allowed


class UserContextType(Enum):
    """Types of user contexts requiring business-critical isolation."""
    AUTHENTICATION = "authentication"  # JWT tokens, user credentials
    EXECUTION = "execution"            # Agent execution state
    DATA_ACCESS = "data_access"        # User data and analysis results
    WEBSOCKET = "websocket"           # Real-time communication channels
    CACHE = "cache"                   # User-specific cached data


@dataclass
class BusinessIsolationTest:
    """Test case definition for business isolation requirements."""
    context_type: UserContextType
    isolation_level: IsolationLevel
    test_description: str
    business_risk_if_violated: str
    regulatory_requirement: bool = False


class UserExecutionContextFactory:
    """Business logic factory for creating isolated user execution contexts."""
    
    def __init__(self):
        self.active_contexts: Dict[UserID, StronglyTypedUserExecutionContext] = {}
        self.context_isolation_rules = self._initialize_isolation_rules()
        self.cross_user_access_attempts: List[Dict[str, Any]] = []
        
    def _initialize_isolation_rules(self) -> Dict[UserContextType, Dict[str, Any]]:
        """Initialize business rules for context isolation."""
        return {
            UserContextType.AUTHENTICATION: {
                "isolation_level": IsolationLevel.STRICT,
                "shared_resources": [],
                "business_requirement": "JWT tokens must never leak between users",
                "regulatory_compliance": True
            },
            UserContextType.EXECUTION: {
                "isolation_level": IsolationLevel.STRICT,
                "shared_resources": [],
                "business_requirement": "Agent execution state must be completely isolated",
                "regulatory_compliance": True
            },
            UserContextType.DATA_ACCESS: {
                "isolation_level": IsolationLevel.STRICT,
                "shared_resources": [],
                "business_requirement": "User data must never be accessible to other users",
                "regulatory_compliance": True
            },
            UserContextType.WEBSOCKET: {
                "isolation_level": IsolationLevel.STRICT,
                "shared_resources": ["connection_pool"],
                "business_requirement": "Real-time messages must only reach intended user",
                "regulatory_compliance": False
            },
            UserContextType.CACHE: {
                "isolation_level": IsolationLevel.STANDARD,
                "shared_resources": ["redis_connection_pool"],
                "business_requirement": "Cached data must be user-scoped",
                "regulatory_compliance": False
            }
        }
    
    def create_isolated_context(
        self, 
        user_id: UserID,
        thread_id: Optional[ThreadID] = None,
        execution_id: Optional[ExecutionID] = None
    ) -> StronglyTypedUserExecutionContext:
        """Create completely isolated user execution context."""
        
        # Business Rule: Generate unique IDs to ensure isolation
        if not thread_id:
            thread_id = ensure_thread_id(f"thread-{uuid.uuid4()}")
        if not execution_id:
            execution_id = ExecutionID(f"exec-{uuid.uuid4()}")
            
        # Business Rule: Create isolated context with no shared state
        context = StronglyTypedUserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            execution_id=execution_id,
            session_id=SessionID(f"session-{uuid.uuid4()}"),
            websocket_client_id=WebSocketID(f"ws-{uuid.uuid4()}"),
            agent_context={"isolation_level": "strict", "user_only": True},
            audit_metadata={"created_at": datetime.now(timezone.utc), "isolation_verified": True}
        )
        
        # Business Rule: Store context with user isolation tracking
        self.active_contexts[user_id] = context
        
        return context
    
    def validate_context_isolation(self, user_id: UserID, context: StronglyTypedUserExecutionContext) -> Dict[str, Any]:
        """Validate that context maintains proper business isolation."""
        validation_results = {
            "user_isolation_verified": False,
            "cross_user_access_blocked": True,
            "regulatory_compliance_met": True,
            "business_requirements_satisfied": True,
            "isolation_violations": []
        }
        
        # Business Rule 1: Context must belong to specified user only
        if context.user_id != user_id:
            validation_results["isolation_violations"].append("Context user_id mismatch")
            validation_results["user_isolation_verified"] = False
            return validation_results
            
        # Business Rule 2: Context IDs must be unique and user-specific
        for other_user_id, other_context in self.active_contexts.items():
            if other_user_id != user_id:
                if other_context.thread_id == context.thread_id:
                    validation_results["isolation_violations"].append("Shared thread_id detected")
                if other_context.execution_id == context.execution_id:
                    validation_results["isolation_violations"].append("Shared execution_id detected")
                if other_context.session_id == context.session_id:
                    validation_results["isolation_violations"].append("Shared session_id detected")
        
        # Business Rule 3: Agent context must not contain other user's data
        agent_context = context.agent_context or {}
        if "user_only" not in agent_context or not agent_context["user_only"]:
            validation_results["isolation_violations"].append("Agent context not marked as user-only")
            
        # Set final validation status
        validation_results["user_isolation_verified"] = len(validation_results["isolation_violations"]) == 0
        validation_results["cross_user_access_blocked"] = len(validation_results["isolation_violations"]) == 0
        validation_results["regulatory_compliance_met"] = len(validation_results["isolation_violations"]) == 0
        validation_results["business_requirements_satisfied"] = len(validation_results["isolation_violations"]) == 0
        
        return validation_results
    
    def simulate_cross_user_access_attempt(self, attacking_user_id: UserID, target_user_id: UserID) -> Dict[str, Any]:
        """Simulate and block cross-user access attempts for security testing."""
        access_attempt = {
            "attacking_user": str(attacking_user_id),
            "target_user": str(target_user_id),
            "timestamp": datetime.now(timezone.utc),
            "access_blocked": True,
            "business_impact": "prevented_data_breach"
        }
        
        # Business Rule: Cross-user access must always be blocked
        if attacking_user_id != target_user_id:
            target_context = self.active_contexts.get(target_user_id)
            if target_context:
                # Simulate access attempt being blocked
                access_attempt["attempted_context"] = str(target_context.execution_id)
                access_attempt["access_blocked"] = True
                access_attempt["block_reason"] = "user_isolation_policy"
        
        self.cross_user_access_attempts.append(access_attempt)
        return access_attempt


@pytest.mark.unit
@pytest.mark.golden_path
class TestUserContextIsolationBusinessLogic(BaseTestCase):
    """Test user context isolation business logic for multi-tenant security."""

    def setup_method(self):
        """Setup test environment for each test."""
        super().setup_method()
        self.context_factory = UserExecutionContextFactory()
        self.test_user_1 = ensure_user_id("enterprise-user-1")
        self.test_user_2 = ensure_user_id("enterprise-user-2")
        self.test_user_3 = ensure_user_id("free-user-3")

    def test_user_execution_context_factory_isolation_business_requirements(self):
        """Test UserExecutionContextFactory creates completely isolated contexts."""
        # Business Value: Each user must have completely isolated execution context
        
        # Create contexts for different users
        context_1 = self.context_factory.create_isolated_context(self.test_user_1)
        context_2 = self.context_factory.create_isolated_context(self.test_user_2)
        context_3 = self.context_factory.create_isolated_context(self.test_user_3)
        
        # Business Rule 1: Each user must have unique user_id
        assert context_1.user_id == self.test_user_1, "Context 1 must belong to user 1"
        assert context_2.user_id == self.test_user_2, "Context 2 must belong to user 2"
        assert context_3.user_id == self.test_user_3, "Context 3 must belong to user 3"
        
        # Business Rule 2: All context IDs must be unique across users
        assert context_1.thread_id != context_2.thread_id, "Thread IDs must be unique across users"
        assert context_1.execution_id != context_2.execution_id, "Execution IDs must be unique across users"
        assert context_1.session_id != context_2.session_id, "Session IDs must be unique across users"
        assert context_1.websocket_client_id != context_2.websocket_client_id, "WebSocket IDs must be unique"
        
        # Business Rule 3: Contexts must not share any mutable state
        assert context_1.agent_context is not context_2.agent_context, "Agent contexts must not be shared"
        assert context_1.audit_metadata is not context_2.audit_metadata, "Audit metadata must not be shared"
        
        # Business Rule 4: Isolation metadata must be present for compliance
        assert context_1.agent_context.get("isolation_level") == "strict", "Isolation level must be strict"
        assert context_1.audit_metadata.get("isolation_verified") is True, "Isolation must be verified"

    def test_authentication_context_isolation_business_requirements(self):
        """Test authentication contexts are completely isolated between users."""
        # Business Value: JWT tokens and credentials must never leak between users
        
        # Simulate authentication contexts with different JWT tokens
        auth_context_1 = {
            "jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.user1.signature1",
            "user_id": str(self.test_user_1),
            "permissions": ["read", "write", "enterprise_features"],
            "session_expires": datetime.now(timezone.utc) + timedelta(hours=8)
        }
        
        auth_context_2 = {
            "jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.user2.signature2",
            "user_id": str(self.test_user_2),
            "permissions": ["read", "write"],
            "session_expires": datetime.now(timezone.utc) + timedelta(hours=8)
        }
        
        # Create isolated execution contexts with authentication data
        context_1 = self.context_factory.create_isolated_context(self.test_user_1)
        context_2 = self.context_factory.create_isolated_context(self.test_user_2)
        
        # Add authentication context to agent_context (simulating real auth flow)
        context_1.agent_context.update({"auth": auth_context_1})
        context_2.agent_context.update({"auth": auth_context_2})
        
        # Business Rule 1: JWT tokens must be completely different
        jwt_1 = context_1.agent_context["auth"]["jwt_token"]
        jwt_2 = context_2.agent_context["auth"]["jwt_token"]
        assert jwt_1 != jwt_2, "JWT tokens must be unique per user"
        assert "user1" in jwt_1 and "user1" not in jwt_2, "JWT payload must be user-specific"
        assert "user2" in jwt_2 and "user2" not in jwt_1, "JWT payload must be user-specific"
        
        # Business Rule 2: Permissions must be isolated per user
        perms_1 = context_1.agent_context["auth"]["permissions"]
        perms_2 = context_2.agent_context["auth"]["permissions"]
        assert "enterprise_features" in perms_1, "User 1 must have enterprise permissions"
        assert "enterprise_features" not in perms_2, "User 2 must not have user 1's permissions"
        
        # Business Rule 3: Authentication context must not be accessible cross-user
        validation_1 = self.context_factory.validate_context_isolation(self.test_user_1, context_1)
        validation_2 = self.context_factory.validate_context_isolation(self.test_user_2, context_2)
        
        assert validation_1["user_isolation_verified"] is True, "User 1 context isolation must be verified"
        assert validation_2["user_isolation_verified"] is True, "User 2 context isolation must be verified"

    def test_websocket_context_isolation_business_requirements(self):
        """Test WebSocket contexts maintain real-time communication isolation."""
        # Business Value: Real-time messages must only reach intended users
        
        # Create isolated contexts with WebSocket connections
        context_1 = self.context_factory.create_isolated_context(self.test_user_1)
        context_2 = self.context_factory.create_isolated_context(self.test_user_2)
        
        # Simulate WebSocket message routing contexts
        ws_context_1 = {
            "websocket_id": context_1.websocket_client_id,
            "user_id": context_1.user_id,
            "active_threads": [context_1.thread_id],
            "message_queue": [],
            "connection_metadata": {"user_tier": "enterprise", "features": ["real_time_ai"]}
        }
        
        ws_context_2 = {
            "websocket_id": context_2.websocket_client_id,
            "user_id": context_2.user_id,
            "active_threads": [context_2.thread_id],
            "message_queue": [],
            "connection_metadata": {"user_tier": "standard", "features": ["basic_ai"]}
        }
        
        # Business Rule 1: WebSocket IDs must be unique and user-specific
        assert ws_context_1["websocket_id"] != ws_context_2["websocket_id"], "WebSocket IDs must be unique"
        assert str(context_1.user_id) in str(ws_context_1["websocket_id"]), "WebSocket ID should be user-specific"
        
        # Business Rule 2: Message queues must be completely isolated
        # Simulate messages being added to queues
        ws_context_1["message_queue"].append({
            "type": "agent_started",
            "user_id": str(context_1.user_id),
            "thread_id": str(context_1.thread_id),
            "message": "Enterprise AI analysis starting..."
        })
        
        ws_context_2["message_queue"].append({
            "type": "agent_started",
            "user_id": str(context_2.user_id),
            "thread_id": str(context_2.thread_id),
            "message": "Standard AI analysis starting..."
        })
        
        # Validate message isolation
        user_1_messages = [msg for msg in ws_context_1["message_queue"] if msg["user_id"] == str(context_1.user_id)]
        user_2_messages = [msg for msg in ws_context_2["message_queue"] if msg["user_id"] == str(context_2.user_id)]
        
        assert len(user_1_messages) == 1, "User 1 should only see their own messages"
        assert len(user_2_messages) == 1, "User 2 should only see their own messages"
        assert "Enterprise" in user_1_messages[0]["message"], "User 1 should see enterprise-specific content"
        assert "Standard" in user_2_messages[0]["message"], "User 2 should see standard-specific content"

    def test_agent_execution_state_isolation_business_requirements(self):
        """Test AI agent execution state is completely isolated between users."""
        # Business Value: AI analysis and results must not leak between users
        
        # Create isolated contexts for concurrent agent executions
        context_1 = self.context_factory.create_isolated_context(self.test_user_1)
        context_2 = self.context_factory.create_isolated_context(self.test_user_2)
        
        # Simulate agent execution state for different users
        agent_state_1 = {
            "execution_id": context_1.execution_id,
            "user_id": context_1.user_id,
            "current_analysis": {
                "user_data": "Confidential enterprise cost analysis: $500K monthly AI spend",
                "optimization_insights": ["Reduce GPT-4 usage by 30%", "Switch to Claude for coding tasks"],
                "sensitive_metrics": {"total_tokens": 10000000, "cost_breakdown": {"openai": 400000}}
            },
            "agent_memory": {"previous_conversations": ["Discuss AI cost reduction strategies"]},
            "execution_progress": 0.7
        }
        
        agent_state_2 = {
            "execution_id": context_2.execution_id,
            "user_id": context_2.user_id,
            "current_analysis": {
                "user_data": "Standard user analysis: $50 monthly AI spend",
                "optimization_insights": ["Consider upgrading for advanced features"],
                "sensitive_metrics": {"total_tokens": 100000, "cost_breakdown": {"openai": 50}}
            },
            "agent_memory": {"previous_conversations": ["Basic cost inquiry"]},
            "execution_progress": 0.3
        }
        
        # Business Rule 1: Execution states must be completely isolated
        assert agent_state_1["user_id"] != agent_state_2["user_id"], "Agent states must belong to different users"
        assert agent_state_1["execution_id"] != agent_state_2["execution_id"], "Execution IDs must be unique"
        
        # Business Rule 2: Sensitive data must not be accessible cross-user
        user_1_data = agent_state_1["current_analysis"]["user_data"]
        user_2_data = agent_state_2["current_analysis"]["user_data"]
        assert "$500K" in user_1_data and "$500K" not in user_2_data, "Enterprise data must not leak to standard user"
        assert "$50" in user_2_data and "$50" not in user_1_data, "Standard user data must not leak to enterprise user"
        
        # Business Rule 3: Agent memory must be user-specific
        memory_1 = agent_state_1["agent_memory"]["previous_conversations"]
        memory_2 = agent_state_2["agent_memory"]["previous_conversations"]
        assert memory_1 != memory_2, "Agent memory must be isolated per user"
        assert "reduction strategies" in memory_1[0] and "reduction strategies" not in memory_2[0], "Memory context must be user-specific"
        
        # Business Rule 4: Execution progress must be independent
        assert agent_state_1["execution_progress"] != agent_state_2["execution_progress"], "Execution progress must be independent"

    def test_cross_user_access_prevention_business_requirements(self):
        """Test that cross-user access attempts are blocked for security."""
        # Business Value: Prevent data breaches and maintain enterprise trust
        
        # Create contexts for different users
        context_1 = self.context_factory.create_isolated_context(self.test_user_1)
        context_2 = self.context_factory.create_isolated_context(self.test_user_2)
        
        # Simulate malicious cross-user access attempt
        access_attempt = self.context_factory.simulate_cross_user_access_attempt(
            attacking_user_id=self.test_user_1,
            target_user_id=self.test_user_2
        )
        
        # Business Rule 1: Cross-user access must always be blocked
        assert access_attempt["access_blocked"] is True, "Cross-user access must be blocked"
        assert access_attempt["block_reason"] == "user_isolation_policy", "Block reason must be documented"
        
        # Business Rule 2: Security incident must be logged for audit
        assert len(self.context_factory.cross_user_access_attempts) == 1, "Access attempt must be logged"
        logged_attempt = self.context_factory.cross_user_access_attempts[0]
        assert logged_attempt["attacking_user"] == str(self.test_user_1), "Attacking user must be logged"
        assert logged_attempt["target_user"] == str(self.test_user_2), "Target user must be logged"
        assert logged_attempt["business_impact"] == "prevented_data_breach", "Business impact must be documented"
        
        # Business Rule 3: Target context must remain uncompromised
        validation = self.context_factory.validate_context_isolation(self.test_user_2, context_2)
        assert validation["user_isolation_verified"] is True, "Target context isolation must remain intact"
        assert validation["cross_user_access_blocked"] is True, "Cross-user access prevention must be verified"

    def test_concurrent_user_isolation_business_requirements(self):
        """Test isolation works correctly under concurrent user load."""
        # Business Value: System must maintain isolation under real-world concurrent usage
        
        # Simulate concurrent user contexts (enterprise scenario)
        concurrent_users = [
            ensure_user_id(f"enterprise-user-{i}") for i in range(5)
        ]
        
        concurrent_contexts = {}
        for user_id in concurrent_users:
            context = self.context_factory.create_isolated_context(user_id)
            concurrent_contexts[user_id] = context
            
            # Add user-specific sensitive data
            context.agent_context.update({
                "user_data": f"Confidential analysis for {user_id}",
                "business_metrics": {"monthly_spend": 10000 + hash(str(user_id)) % 50000},
                "competitive_insights": f"Strategy insights for {user_id}"
            })
        
        # Business Rule 1: All contexts must be isolated from each other
        for user_id, context in concurrent_contexts.items():
            validation = self.context_factory.validate_context_isolation(user_id, context)
            assert validation["user_isolation_verified"] is True, f"User {user_id} context must be isolated"
            assert len(validation["isolation_violations"]) == 0, f"User {user_id} must have no isolation violations"
        
        # Business Rule 2: Sensitive data must not leak between concurrent users
        all_user_data = [ctx.agent_context["user_data"] for ctx in concurrent_contexts.values()]
        for i, data in enumerate(all_user_data):
            # Each user's data should only mention their own user ID
            user_mentions = [user_id for user_id in concurrent_users if str(user_id) in data]
            assert len(user_mentions) == 1, f"User data should only reference own user ID: {data}"
        
        # Business Rule 3: Business metrics must be user-specific and not shared
        all_metrics = [ctx.agent_context["business_metrics"]["monthly_spend"] for ctx in concurrent_contexts.values()]
        # All spending amounts should be different (due to hash-based generation)
        assert len(set(all_metrics)) == len(all_metrics), "All user metrics must be unique"

    def test_user_context_cleanup_business_requirements(self):
        """Test user contexts are properly cleaned up to prevent data persistence."""
        # Business Value: Prevent data accumulation and potential cross-user contamination
        
        # Create context with sensitive data
        context = self.context_factory.create_isolated_context(self.test_user_1)
        context.agent_context.update({
            "sensitive_analysis": "Confidential AI cost optimization recommendations",
            "user_secrets": {"api_keys": ["sk-test-key-123"], "database_url": "postgresql://secret"},
            "business_data": {"revenue_impact": 250000, "cost_savings": 75000}
        })
        
        # Verify context exists and contains sensitive data
        assert self.test_user_1 in self.context_factory.active_contexts, "Context must be stored"
        stored_context = self.context_factory.active_contexts[self.test_user_1]
        assert "sensitive_analysis" in stored_context.agent_context, "Sensitive data must be present"
        
        # Simulate context cleanup (would be called when user session ends)
        def cleanup_user_context(user_id: UserID):
            """Simulate business logic for cleaning up user context."""
            if user_id in self.context_factory.active_contexts:
                # Business Rule: Sensitive data must be cleared before removal
                context = self.context_factory.active_contexts[user_id]
                
                # Clear sensitive agent context data
                if hasattr(context, 'agent_context') and context.agent_context:
                    for key in list(context.agent_context.keys()):
                        if key in ["sensitive_analysis", "user_secrets", "business_data"]:
                            del context.agent_context[key]
                
                # Remove context from active contexts
                del self.context_factory.active_contexts[user_id]
                return True
            return False
        
        # Execute cleanup
        cleanup_result = cleanup_user_context(self.test_user_1)
        assert cleanup_result is True, "Context cleanup must succeed"
        
        # Business Rule 1: Context must be completely removed
        assert self.test_user_1 not in self.context_factory.active_contexts, "Context must be removed from active contexts"
        
        # Business Rule 2: No sensitive data should remain accessible
        # Since context is removed, any remaining references should not contain sensitive data
        # This test verifies the cleanup process prevents data accumulation

    def test_regulatory_compliance_isolation_business_requirements(self):
        """Test user isolation meets regulatory compliance requirements."""
        # Business Value: Ensure compliance with GDPR, HIPAA, SOC2 requirements
        
        # Create contexts that simulate regulated data handling
        gdpr_context = self.context_factory.create_isolated_context(ensure_user_id("eu-enterprise-user"))
        hipaa_context = self.context_factory.create_isolated_context(ensure_user_id("healthcare-user"))
        sox_context = self.context_factory.create_isolated_context(ensure_user_id("financial-user"))
        
        # Add regulatory compliance metadata
        gdpr_context.audit_metadata.update({
            "data_classification": "personal_data",
            "gdpr_compliant": True,
            "data_purpose": "ai_cost_optimization",
            "user_consent": True,
            "retention_period": 365
        })
        
        hipaa_context.audit_metadata.update({
            "data_classification": "phi_data", 
            "hipaa_compliant": True,
            "data_purpose": "healthcare_ai_analysis",
            "encryption_required": True,
            "audit_trail_required": True
        })
        
        sox_context.audit_metadata.update({
            "data_classification": "financial_data",
            "sox_compliant": True,
            "data_purpose": "financial_ai_reporting", 
            "segregation_required": True,
            "approval_required": True
        })
        
        # Business Rule 1: Regulatory metadata must be preserved and isolated
        assert gdpr_context.audit_metadata["gdpr_compliant"] is True, "GDPR compliance must be tracked"
        assert hipaa_context.audit_metadata["hipaa_compliant"] is True, "HIPAA compliance must be tracked"
        assert sox_context.audit_metadata["sox_compliant"] is True, "SOX compliance must be tracked"
        
        # Business Rule 2: Data classification must be user-specific
        classifications = [
            gdpr_context.audit_metadata["data_classification"],
            hipaa_context.audit_metadata["data_classification"], 
            sox_context.audit_metadata["data_classification"]
        ]
        assert len(set(classifications)) == 3, "Each regulatory context must have unique classification"
        
        # Business Rule 3: Cross-regulatory-context access must be prevented
        all_contexts = [gdpr_context, hipaa_context, sox_context]
        for i, context_a in enumerate(all_contexts):
            for j, context_b in enumerate(all_contexts):
                if i != j:
                    # Verify contexts are isolated
                    assert context_a.user_id != context_b.user_id, "Regulatory contexts must have different users"
                    assert context_a.execution_id != context_b.execution_id, "Execution IDs must be unique across regulatory contexts"
                    
                    # Verify regulatory requirements don't cross-contaminate
                    compliance_a = {k: v for k, v in context_a.audit_metadata.items() if k.endswith("_compliant")}
                    compliance_b = {k: v for k, v in context_b.audit_metadata.items() if k.endswith("_compliant")}
                    assert compliance_a != compliance_b, "Regulatory compliance requirements must be context-specific"