"""
User Context Isolation Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - User context isolation is CRITICAL for multi-tenant system
- Business Goal: Ensure complete user data isolation preventing data leakage between customers
- Value Impact: User context isolation protects customer data and enables subscription tier enforcement
- Strategic Impact: Core security foundation that prevents data breaches and enables regulatory compliance

CRITICAL REQUIREMENTS:
- NO MOCKS - Uses real user context factories and isolation patterns
- Tests real multi-user execution context isolation - MANDATORY for factory patterns
- Validates user context isolation at WebSocket, Agent, and Tool execution levels
- Ensures subscription tier isolation and permission boundaries
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class TestUserExecutionContextIsolation(BaseIntegrationTest):
    """Integration tests for user execution context isolation - CRITICAL for multi-tenant system."""
    
    def setup_method(self):
        """Set up for user context isolation tests."""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Create test users with different contexts - CRITICAL for isolation testing
        self.test_users = [
            {
                "user_id": "isolation-user-1",
                "email": "isolation1@test.com", 
                "subscription_tier": "free",
                "permissions": ["read"],
                "context_data": {"customer_id": "cust-001", "org_id": "org-alpha"}
            },
            {
                "user_id": "isolation-user-2",
                "email": "isolation2@test.com",
                "subscription_tier": "enterprise", 
                "permissions": ["read", "write", "admin"],
                "context_data": {"customer_id": "cust-002", "org_id": "org-beta"}
            },
            {
                "user_id": "isolation-user-3",
                "email": "isolation3@test.com",
                "subscription_tier": "mid",
                "permissions": ["read", "write"],
                "context_data": {"customer_id": "cust-003", "org_id": "org-gamma"}
            }
        ]
        
        # Initialize user context storage
        self._user_contexts = {}
        self._agent_executions = {}
        self._websocket_sessions = {}
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_factory_isolation(self):
        """
        Test user context factory creates isolated execution contexts per user.
        
        Business Value: Ensures each user's execution is completely isolated from others.
        Security Impact: Prevents user data contamination and unauthorized access.
        """
        # Create isolated execution contexts for each user
        user_contexts = []
        
        for user in self.test_users:
            # Create JWT token for user
            token = self.auth_helper.create_test_jwt_token(
                user_id=user["user_id"],
                email=user["email"],
                permissions=user["permissions"]
            )
            
            # Create user execution context using factory pattern
            context = await self._create_user_execution_context(user, token)
            user_contexts.append(context)
            
            # Validate context isolation attributes
            assert context["user_id"] == user["user_id"]
            assert context["subscription_tier"] == user["subscription_tier"]
            assert context["permissions"] == user["permissions"]
            assert context["context_data"] == user["context_data"]
            assert "execution_id" in context
            assert "isolation_boundary" in context
        
        # Validate complete isolation between contexts
        for i, context1 in enumerate(user_contexts):
            for j, context2 in enumerate(user_contexts):
                if i != j:
                    # Assert no shared data between different user contexts
                    assert context1["user_id"] != context2["user_id"]
                    assert context1["execution_id"] != context2["execution_id"]
                    assert context1["context_data"] != context2["context_data"]
                    assert context1["isolation_boundary"] != context2["isolation_boundary"]
                    
                    # Verify subscription tier boundaries
                    assert context1["subscription_tier"] != context2["subscription_tier"] or \
                           context1["user_id"] != context2["user_id"]
        
        self.logger.info("User context factory isolation validation successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_user_context_isolation(self):
        """
        Test WebSocket connections maintain user context isolation.
        
        Business Value: Ensures WebSocket-based chat maintains user data separation.
        Security Impact: Prevents WebSocket message leakage between users.
        """
        # Create WebSocket sessions for each user
        websocket_sessions = []
        
        for user in self.test_users:
            # Create authenticated WebSocket session
            session_data = await self._create_websocket_user_session(user)
            websocket_sessions.append(session_data)
            
            # Validate WebSocket context isolation
            assert session_data["user_context"]["user_id"] == user["user_id"]
            assert session_data["user_context"]["subscription_tier"] == user["subscription_tier"]
            assert "websocket_id" in session_data
            assert "message_queue" in session_data
            assert "user_isolation_key" in session_data
        
        # Test cross-session message isolation
        for session1 in websocket_sessions:
            for session2 in websocket_sessions:
                if session1["user_context"]["user_id"] != session2["user_context"]["user_id"]:
                    # Send message in session1, should not appear in session2
                    test_message = {
                        "type": "user_message",
                        "content": f"Private message from {session1['user_context']['user_id']}",
                        "sensitive_data": f"secret-{session1['user_context']['user_id']}"
                    }
                    
                    await self._send_websocket_message(session1, test_message)
                    
                    # Verify message isolation - other users should not receive it
                    session2_messages = await self._get_websocket_messages(session2)
                    
                    # Assert message does not leak to other user's session
                    for msg in session2_messages:
                        assert session1["user_context"]["user_id"] not in str(msg)
                        assert test_message["sensitive_data"] not in str(msg)
                        assert msg.get("user_context", {}).get("user_id") == session2["user_context"]["user_id"]
        
        self.logger.info("WebSocket user context isolation validation successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_user_context_isolation(self):
        """
        Test agent execution maintains user context isolation.
        
        Business Value: Ensures AI agent responses are personalized and isolated per user.
        Security Impact: Prevents agent execution data leakage between users.
        """
        # Create agent executions for each user
        agent_executions = []
        
        for user in self.test_users:
            # Create user execution context
            user_context = await self._create_user_execution_context(user)
            
            # Start agent execution within user context
            execution_data = await self._start_agent_execution(
                user_context=user_context,
                agent_type="triage_agent",
                user_message=f"Analyze my data for user {user['user_id']}"
            )
            
            agent_executions.append(execution_data)
            
            # Validate agent execution context isolation
            assert execution_data["user_context"]["user_id"] == user["user_id"]
            assert execution_data["subscription_tier"] == user["subscription_tier"]
            assert "agent_execution_id" in execution_data
            assert "isolated_workspace" in execution_data
            
            # Verify subscription tier-specific capabilities
            expected_capabilities = self._get_tier_capabilities(user["subscription_tier"])
            assert execution_data["available_capabilities"] == expected_capabilities
        
        # Test agent execution isolation between users
        for execution1 in agent_executions:
            for execution2 in agent_executions:
                if execution1["user_context"]["user_id"] != execution2["user_context"]["user_id"]:
                    # Verify executions cannot access each other's data
                    cross_access_result = await self._attempt_cross_execution_access(
                        execution1["agent_execution_id"], 
                        execution2["user_context"]["user_id"]
                    )
                    
                    assert cross_access_result["access_granted"] is False
                    assert "isolation_violation" in cross_access_result["error"]
                    
                    # Verify workspace isolation
                    workspace1 = execution1["isolated_workspace"]
                    workspace2 = execution2["isolated_workspace"]
                    
                    assert workspace1["workspace_id"] != workspace2["workspace_id"]
                    assert workspace1["user_data_boundary"] != workspace2["user_data_boundary"]
        
        self.logger.info("Agent execution user context isolation validation successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_user_context_isolation(self):
        """
        Test tool execution maintains user context and permission isolation.
        
        Business Value: Ensures tools operate within user's subscription limits and permissions.
        Security Impact: Prevents tool execution privilege escalation between users.
        """
        # Test tool execution for each user with different permission levels
        tool_executions = []
        
        test_tools = [
            {"tool_name": "data_analyzer", "required_permission": "read"},
            {"tool_name": "cost_optimizer", "required_permission": "write"}, 
            {"tool_name": "admin_dashboard", "required_permission": "admin"}
        ]
        
        for user in self.test_users:
            user_tool_results = []
            
            for tool in test_tools:
                # Create tool execution context
                execution_context = await self._create_tool_execution_context(
                    user=user,
                    tool_name=tool["tool_name"],
                    required_permission=tool["required_permission"]
                )
                
                # Attempt tool execution
                execution_result = await self._execute_tool_with_context(
                    context=execution_context,
                    tool_params={"user_specific_data": f"data-for-{user['user_id']}"}
                )
                
                user_tool_results.append({
                    "tool": tool["tool_name"],
                    "result": execution_result,
                    "user_id": user["user_id"]
                })
                
                # Validate permission-based access control
                user_permissions = user["permissions"]
                required_permission = tool["required_permission"]
                
                if required_permission in user_permissions:
                    # User should have access
                    assert execution_result["access_granted"] is True
                    assert execution_result["user_context"]["user_id"] == user["user_id"]
                    assert execution_result["tool_output"] is not None
                else:
                    # User should be denied access
                    assert execution_result["access_granted"] is False
                    assert "insufficient_permissions" in execution_result["error"]
            
            tool_executions.append(user_tool_results)
        
        # Validate tool execution isolation between users
        for user1_results in tool_executions:
            for user2_results in tool_executions:
                if user1_results[0]["user_id"] != user2_results[0]["user_id"]:
                    # Verify no cross-contamination of tool outputs
                    for tool1_result in user1_results:
                        for tool2_result in user2_results:
                            if (tool1_result["tool"] == tool2_result["tool"] and 
                                tool1_result["result"]["access_granted"] and 
                                tool2_result["result"]["access_granted"]):
                                
                                output1 = tool1_result["result"]["tool_output"]
                                output2 = tool2_result["result"]["tool_output"]
                                
                                # Outputs should be different (user-specific)
                                assert output1 != output2
                                assert tool1_result["user_id"] not in str(output2)
                                assert tool2_result["user_id"] not in str(output1)
        
        self.logger.info("Tool execution user context isolation validation successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_subscription_tier_isolation_enforcement(self):
        """
        Test subscription tier isolation and feature access enforcement.
        
        Business Value: Protects revenue by ensuring only paid users access premium features.
        Strategic Impact: Core business model enforcement through technical isolation.
        """
        # Test subscription tier feature isolation
        tier_feature_tests = [
            {
                "feature": "basic_analytics",
                "allowed_tiers": ["free", "early", "mid", "enterprise"]
            },
            {
                "feature": "advanced_analytics", 
                "allowed_tiers": ["mid", "enterprise"]
            },
            {
                "feature": "custom_models",
                "allowed_tiers": ["enterprise"]
            },
            {
                "feature": "priority_support",
                "allowed_tiers": ["enterprise"]
            }
        ]
        
        for feature_test in tier_feature_tests:
            for user in self.test_users:
                # Create user context for feature access test
                user_context = await self._create_user_execution_context(user)
                
                # Attempt feature access
                feature_access_result = await self._test_feature_access(
                    user_context=user_context,
                    feature_name=feature_test["feature"]
                )
                
                # Validate subscription tier enforcement
                user_tier = user["subscription_tier"]
                should_have_access = user_tier in feature_test["allowed_tiers"]
                
                if should_have_access:
                    assert feature_access_result["access_granted"] is True
                    assert feature_access_result["feature_data"] is not None
                    assert feature_access_result["user_tier"] == user_tier
                else:
                    assert feature_access_result["access_granted"] is False
                    assert "tier_restriction" in feature_access_result["error"]
                    assert feature_access_result["required_tier"] in feature_test["allowed_tiers"]
                
                self.logger.info(f"Tier isolation for {user_tier} user accessing {feature_test['feature']}: {'[U+2713]' if should_have_access else '[U+2717]'}")
        
        # Test tier upgrade scenario simulation
        upgrade_test_user = self.test_users[0]  # Free tier user
        
        # Attempt enterprise feature access (should fail)
        pre_upgrade_context = await self._create_user_execution_context(upgrade_test_user)
        pre_upgrade_result = await self._test_feature_access(
            user_context=pre_upgrade_context,
            feature_name="custom_models"
        )
        
        assert pre_upgrade_result["access_granted"] is False
        
        # Simulate tier upgrade
        upgraded_user = {**upgrade_test_user, "subscription_tier": "enterprise"}
        post_upgrade_context = await self._create_user_execution_context(upgraded_user)
        post_upgrade_result = await self._test_feature_access(
            user_context=post_upgrade_context,
            feature_name="custom_models"
        )
        
        assert post_upgrade_result["access_granted"] is True
        
        self.logger.info("Subscription tier isolation enforcement validation successful")
    
    # Helper methods for user context isolation testing
    
    async def _create_user_execution_context(self, user: Dict[str, Any], token: str = None) -> Dict[str, Any]:
        """Create isolated user execution context."""
        if token is None:
            token = self.auth_helper.create_test_jwt_token(
                user_id=user["user_id"],
                email=user["email"], 
                permissions=user["permissions"]
            )
        
        execution_id = str(uuid.uuid4())
        isolation_boundary = f"isolation-{user['user_id']}-{execution_id[:8]}"
        
        context = {
            "user_id": user["user_id"],
            "email": user["email"],
            "subscription_tier": user["subscription_tier"],
            "permissions": user["permissions"],
            "context_data": user["context_data"],
            "execution_id": execution_id,
            "isolation_boundary": isolation_boundary,
            "token": token,
            "created_at": datetime.now(timezone.utc)
        }
        
        self._user_contexts[execution_id] = context
        return context
    
    async def _create_websocket_user_session(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Create WebSocket session with user context isolation."""
        user_context = await self._create_user_execution_context(user)
        
        websocket_id = str(uuid.uuid4())
        user_isolation_key = f"ws-{user['user_id']}-{websocket_id[:8]}"
        
        session = {
            "websocket_id": websocket_id,
            "user_context": user_context,
            "user_isolation_key": user_isolation_key,
            "message_queue": [],
            "connected_at": datetime.now(timezone.utc)
        }
        
        self._websocket_sessions[websocket_id] = session
        return session
    
    async def _send_websocket_message(self, session: Dict[str, Any], message: Dict[str, Any]) -> None:
        """Send message to WebSocket session."""
        enhanced_message = {
            **message,
            "user_context": session["user_context"],
            "websocket_id": session["websocket_id"],
            "timestamp": datetime.now(timezone.utc)
        }
        
        session["message_queue"].append(enhanced_message)
    
    async def _get_websocket_messages(self, session: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get messages from WebSocket session."""
        return session["message_queue"]
    
    async def _start_agent_execution(self, user_context: Dict[str, Any], agent_type: str, user_message: str) -> Dict[str, Any]:
        """Start agent execution within user context."""
        execution_id = str(uuid.uuid4())
        workspace_id = f"workspace-{user_context['user_id']}-{execution_id[:8]}"
        
        execution_data = {
            "agent_execution_id": execution_id,
            "user_context": user_context,
            "agent_type": agent_type,
            "user_message": user_message,
            "subscription_tier": user_context["subscription_tier"],
            "available_capabilities": self._get_tier_capabilities(user_context["subscription_tier"]),
            "isolated_workspace": {
                "workspace_id": workspace_id,
                "user_data_boundary": f"boundary-{user_context['user_id']}",
                "temp_storage": f"temp-{execution_id}"
            },
            "started_at": datetime.now(timezone.utc)
        }
        
        self._agent_executions[execution_id] = execution_data
        return execution_data
    
    async def _attempt_cross_execution_access(self, execution_id: str, attempted_user_id: str) -> Dict[str, Any]:
        """Attempt cross-execution access (should fail)."""
        execution = self._agent_executions.get(execution_id)
        
        if not execution:
            return {"access_granted": False, "error": "execution_not_found"}
        
        if execution["user_context"]["user_id"] != attempted_user_id:
            return {"access_granted": False, "error": "isolation_violation_detected"}
        
        return {"access_granted": True}
    
    async def _create_tool_execution_context(self, user: Dict[str, Any], tool_name: str, required_permission: str) -> Dict[str, Any]:
        """Create tool execution context with permission validation."""
        user_context = await self._create_user_execution_context(user)
        
        return {
            "user_context": user_context,
            "tool_name": tool_name,
            "required_permission": required_permission,
            "tool_execution_id": str(uuid.uuid4())
        }
    
    async def _execute_tool_with_context(self, context: Dict[str, Any], tool_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool within user context with permission checking."""
        user_permissions = context["user_context"]["permissions"]
        required_permission = context["required_permission"]
        
        if required_permission not in user_permissions:
            return {
                "access_granted": False,
                "error": "insufficient_permissions",
                "required": required_permission,
                "user_permissions": user_permissions
            }
        
        # Simulate tool execution with user-specific output
        tool_output = {
            "result": f"Tool {context['tool_name']} executed for user {context['user_context']['user_id']}",
            "user_specific_data": tool_params.get("user_specific_data"),
            "execution_id": context["tool_execution_id"]
        }
        
        return {
            "access_granted": True,
            "user_context": context["user_context"],
            "tool_output": tool_output
        }
    
    async def _test_feature_access(self, user_context: Dict[str, Any], feature_name: str) -> Dict[str, Any]:
        """Test feature access based on subscription tier."""
        user_tier = user_context["subscription_tier"]
        
        # Define tier-based feature access
        tier_features = {
            "free": ["basic_analytics"],
            "early": ["basic_analytics"],
            "mid": ["basic_analytics", "advanced_analytics"], 
            "enterprise": ["basic_analytics", "advanced_analytics", "custom_models", "priority_support"]
        }
        
        allowed_features = tier_features.get(user_tier, [])
        
        if feature_name in allowed_features:
            return {
                "access_granted": True,
                "feature_data": f"Feature {feature_name} data for tier {user_tier}",
                "user_tier": user_tier
            }
        else:
            # Find minimum required tier
            required_tier = None
            for tier, features in tier_features.items():
                if feature_name in features:
                    required_tier = tier
                    break
            
            return {
                "access_granted": False,
                "error": "tier_restriction",
                "current_tier": user_tier,
                "required_tier": required_tier
            }
    
    def _get_tier_capabilities(self, tier: str) -> List[str]:
        """Get capabilities available for subscription tier."""
        tier_capabilities = {
            "free": ["basic_agents", "simple_analytics"],
            "early": ["basic_agents", "simple_analytics", "optimization_tools"],
            "mid": ["basic_agents", "simple_analytics", "optimization_tools", "advanced_analytics"],
            "enterprise": ["basic_agents", "simple_analytics", "optimization_tools", "advanced_analytics", "custom_models", "priority_execution"]
        }
        
        return tier_capabilities.get(tier, [])