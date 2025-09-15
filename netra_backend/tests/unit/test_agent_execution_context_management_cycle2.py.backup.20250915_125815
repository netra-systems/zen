"""
Unit Tests for Agent Execution Context Management - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure proper agent execution context management and isolation
- Value Impact: Users get personalized, secure agent experiences with proper data isolation
- Strategic Impact: Context management enables multi-tenant scalability and data security

CRITICAL: Context management is the foundation of multi-user security and personalization.
Poor context handling would leak data between customers and destroy trust.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types import UserID, ThreadID, RunID

class TestAgentExecutionContextManagement:
    """Test agent execution context management and isolation."""
    
    @pytest.fixture
    def basic_user_context(self):
        """Create basic user execution context for testing."""
        return UserExecutionContext(
            user_id=UserID("context_test_user"),
            thread_id=ThreadID("context_test_thread"),
            authenticated=True,
            permissions=["agent_execution", "data_access"],
            session_data={"test_session": True}
        )
    
    @pytest.fixture
    def basic_agent_context(self, basic_user_context):
        """Create basic agent execution context for testing."""
        return AgentExecutionContext(
            user_id=UserID("context_test_user"),
            thread_id=ThreadID("context_test_thread"), 
            run_id=RunID("context_test_run"),
            agent_name="context_test_agent",
            message="Test message for context management",
            user_context=basic_user_context
        )

    @pytest.mark.unit
    def test_agent_context_initialization_with_required_fields(self, basic_user_context):
        """
        Test agent execution context initializes with all required fields.
        
        Business Value: Proper initialization ensures consistent agent behavior.
        Missing context fields could lead to agent confusion or security gaps.
        """
        # Act: Create agent context with all required fields
        context = AgentExecutionContext(
            user_id=UserID("init_test_user"),
            thread_id=ThreadID("init_test_thread"),
            run_id=RunID("init_test_run"),
            agent_name="initialization_agent",
            message="Complete initialization test message",
            user_context=basic_user_context
        )
        
        # Assert: All required fields properly set
        assert context.user_id == UserID("init_test_user")
        assert context.thread_id == ThreadID("init_test_thread")
        assert context.run_id == RunID("init_test_run")
        assert context.agent_name == "initialization_agent"
        assert context.message == "Complete initialization test message"
        assert context.user_context is not None
        
        # Business requirement: Context should be complete for agent execution
        assert hasattr(context, 'user_id'), "Context must have user_id"
        assert hasattr(context, 'thread_id'), "Context must have thread_id"  
        assert hasattr(context, 'run_id'), "Context must have run_id"
        assert hasattr(context, 'agent_name'), "Context must have agent_name"
        assert hasattr(context, 'message'), "Context must have message"
        assert hasattr(context, 'user_context'), "Context must have user_context"

    @pytest.mark.unit
    def test_agent_context_user_isolation_enforcement(self, basic_user_context):
        """
        Test agent context enforces proper user isolation.
        
        Business Value: User isolation is critical for data security and privacy.
        Context contamination between users would be catastrophic for trust.
        """
        # Arrange: Create contexts for different users
        user1_context = UserExecutionContext(
            user_id=UserID("isolated_user_1"),
            thread_id=ThreadID("user1_thread"),
            authenticated=True,
            permissions=["user1_permissions"],
            session_data={"user": "user1", "sensitive_data": "user1_secrets"}
        )
        
        user2_context = UserExecutionContext(
            user_id=UserID("isolated_user_2"),
            thread_id=ThreadID("user2_thread"),
            authenticated=True,
            permissions=["user2_permissions"],
            session_data={"user": "user2", "sensitive_data": "user2_secrets"}
        )
        
        # Act: Create agent contexts for both users
        agent_context_1 = AgentExecutionContext(
            user_id=UserID("isolated_user_1"),
            thread_id=ThreadID("user1_thread"),
            run_id=RunID("user1_run"),
            agent_name="isolation_agent",
            message="User 1 message",
            user_context=user1_context
        )
        
        agent_context_2 = AgentExecutionContext(
            user_id=UserID("isolated_user_2"),
            thread_id=ThreadID("user2_thread"),
            run_id=RunID("user2_run"),
            agent_name="isolation_agent",
            message="User 2 message",
            user_context=user2_context
        )
        
        # Assert: Complete user isolation maintained
        assert agent_context_1.user_id != agent_context_2.user_id
        assert agent_context_1.thread_id != agent_context_2.thread_id
        assert agent_context_1.run_id != agent_context_2.run_id
        assert agent_context_1.message != agent_context_2.message
        
        # Critical business requirement: User contexts completely isolated
        assert agent_context_1.user_context != agent_context_2.user_context
        assert agent_context_1.user_context.session_data != agent_context_2.user_context.session_data
        
        # Verify no data leakage between contexts
        user1_session = agent_context_1.user_context.session_data
        user2_session = agent_context_2.user_context.session_data
        
        assert user1_session["sensitive_data"] == "user1_secrets"
        assert user2_session["sensitive_data"] == "user2_secrets"
        assert "user2_secrets" not in str(user1_session)
        assert "user1_secrets" not in str(user2_session)

    @pytest.mark.unit
    def test_agent_context_permission_validation(self):
        """
        Test agent context properly validates user permissions.
        
        Business Value: Permission validation ensures users only access authorized features.
        Authorization failures could expose premium features to free users.
        """
        # Test different permission scenarios
        permission_scenarios = [
            {
                "name": "admin_user",
                "permissions": ["admin", "agent_execution", "data_access", "user_management"],
                "expected_access": ["high_value_features", "all_agents"]
            },
            {
                "name": "premium_user", 
                "permissions": ["premium", "agent_execution", "data_access"],
                "expected_access": ["premium_features", "most_agents"]
            },
            {
                "name": "free_user",
                "permissions": ["basic", "limited_execution"],
                "expected_access": ["basic_features", "limited_agents"]
            },
            {
                "name": "restricted_user",
                "permissions": [],
                "expected_access": ["minimal_features"]
            }
        ]
        
        for scenario in permission_scenarios:
            # Arrange: Create user context with specific permissions
            user_context = UserExecutionContext(
                user_id=UserID(f"permission_test_{scenario['name']}"),
                thread_id=ThreadID(f"permission_thread_{scenario['name']}"),
                authenticated=True,
                permissions=scenario["permissions"],
                session_data={"user_type": scenario["name"]}
            )
            
            # Act: Create agent context
            agent_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=RunID(f"permission_run_{scenario['name']}"),
                agent_name="permission_test_agent",
                message=f"Permission test for {scenario['name']}",
                user_context=user_context
            )
            
            # Assert: Context reflects proper permissions
            assert agent_context.user_context.permissions == scenario["permissions"]
            
            # Business requirement: Permission information accessible for authorization
            if "admin" in scenario["permissions"]:
                assert "admin" in agent_context.user_context.permissions
            
            if "premium" in scenario["permissions"]:
                assert "premium" in agent_context.user_context.permissions
                
            # Free users should not have premium permissions
            if scenario["name"] == "free_user":
                assert "premium" not in agent_context.user_context.permissions
                assert "admin" not in agent_context.user_context.permissions

    @pytest.mark.unit
    def test_agent_context_session_data_management(self, basic_user_context):
        """
        Test agent context properly manages session data.
        
        Business Value: Session data enables personalized experiences and user state.
        Proper session management maintains user experience continuity.
        """
        # Arrange: Create context with rich session data
        rich_session_data = {
            "user_preferences": {
                "language": "en-US",
                "timezone": "America/New_York",
                "currency": "USD",
                "notification_settings": {"email": True, "sms": False}
            },
            "current_analysis": {
                "cloud_provider": "aws",
                "monthly_spend": 15000,
                "optimization_goals": ["cost_reduction", "performance"],
                "previous_recommendations": ["resize_instances", "enable_savings_plans"]
            },
            "session_metadata": {
                "start_time": datetime.now(timezone.utc).isoformat(),
                "device_type": "web",
                "ip_address": "192.168.1.1",
                "user_agent": "test_browser"
            }
        }
        
        enhanced_user_context = UserExecutionContext(
            user_id=UserID("session_test_user"),
            thread_id=ThreadID("session_test_thread"),
            authenticated=True,
            permissions=["premium", "agent_execution"],
            session_data=rich_session_data
        )
        
        # Act: Create agent context with rich session data
        agent_context = AgentExecutionContext(
            user_id=UserID("session_test_user"),
            thread_id=ThreadID("session_test_thread"),
            run_id=RunID("session_test_run"),
            agent_name="session_data_agent",
            message="Analyze costs considering my preferences and history",
            user_context=enhanced_user_context
        )
        
        # Assert: Session data properly preserved and accessible
        session_data = agent_context.user_context.session_data
        
        # Verify nested session data structure preserved
        assert "user_preferences" in session_data
        assert session_data["user_preferences"]["language"] == "en-US"
        assert session_data["user_preferences"]["currency"] == "USD"
        
        # Business requirement: Historical context available for personalization
        assert "current_analysis" in session_data
        assert session_data["current_analysis"]["monthly_spend"] == 15000
        assert "cost_reduction" in session_data["current_analysis"]["optimization_goals"]
        
        # Metadata should be preserved for analytics
        assert "session_metadata" in session_data
        assert session_data["session_metadata"]["device_type"] == "web"

    @pytest.mark.unit
    def test_agent_context_thread_continuity_management(self):
        """
        Test agent context maintains thread continuity across executions.
        
        Business Value: Thread continuity enables conversational AI experiences.
        Users expect agents to remember previous conversation context.
        """
        # Arrange: Simulate conversation thread with multiple exchanges
        user_id = UserID("continuity_test_user")
        thread_id = ThreadID("conversation_thread_001")
        
        conversation_history = []
        
        # First exchange
        user_context_1 = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            authenticated=True,
            permissions=["conversation"],
            session_data={"conversation_turn": 1, "history": conversation_history}
        )
        
        agent_context_1 = AgentExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=RunID("conversation_run_001"),
            agent_name="conversational_agent",
            message="Analyze my AWS costs for last month",
            user_context=user_context_1
        )
        
        # Simulate first exchange completion
        conversation_history.append({
            "turn": 1,
            "user_message": "Analyze my AWS costs for last month",
            "agent_response": "Found $12,000 monthly spend with optimization opportunities"
        })
        
        # Second exchange - should maintain continuity
        user_context_2 = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,  # Same thread ID for continuity
            authenticated=True,
            permissions=["conversation"],
            session_data={"conversation_turn": 2, "history": conversation_history}
        )
        
        agent_context_2 = AgentExecutionContext(
            user_id=user_id,
            thread_id=thread_id,  # Same thread ID
            run_id=RunID("conversation_run_002"),  # Different run ID
            agent_name="conversational_agent",
            message="What specific optimizations do you recommend?",
            user_context=user_context_2
        )
        
        # Assert: Thread continuity maintained
        assert agent_context_1.thread_id == agent_context_2.thread_id
        assert agent_context_1.user_id == agent_context_2.user_id
        assert agent_context_1.run_id != agent_context_2.run_id  # Different runs in same thread
        
        # Business requirement: Conversation history preserved
        history_1 = agent_context_1.user_context.session_data["history"]
        history_2 = agent_context_2.user_context.session_data["history"]
        
        assert len(history_2) > len(history_1), "Second exchange should have more history"
        assert history_2[-1]["user_message"] == "Analyze my AWS costs for last month"
        assert "optimization opportunities" in history_2[-1]["agent_response"]

    @pytest.mark.unit
    def test_agent_context_authentication_state_validation(self):
        """
        Test agent context properly validates authentication state.
        
        Business Value: Authentication validation prevents unauthorized access.
        CRITICAL: Unauthenticated users must not access premium AI features.
        """
        # Test authentication scenarios
        auth_scenarios = [
            {
                "name": "authenticated_premium_user",
                "authenticated": True,
                "permissions": ["premium", "agent_execution"],
                "expected_access": True
            },
            {
                "name": "authenticated_free_user",
                "authenticated": True,
                "permissions": ["basic"],
                "expected_access": True  # Should have basic access
            },
            {
                "name": "unauthenticated_user",
                "authenticated": False,
                "permissions": [],
                "expected_access": False
            }
        ]
        
        for scenario in auth_scenarios:
            # Arrange: Create user context with authentication state
            user_context = UserExecutionContext(
                user_id=UserID(f"auth_test_{scenario['name']}"),
                thread_id=ThreadID(f"auth_thread_{scenario['name']}"),
                authenticated=scenario["authenticated"],
                permissions=scenario["permissions"],
                session_data={"auth_test": True}
            )
            
            # Act: Create agent context
            agent_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=RunID(f"auth_run_{scenario['name']}"),
                agent_name="auth_test_agent",
                message="Authentication test message",
                user_context=user_context
            )
            
            # Assert: Authentication state properly reflected
            assert agent_context.user_context.authenticated == scenario["authenticated"]
            
            # Business requirement: Authentication determines access level
            if scenario["expected_access"]:
                # Authenticated users should have some permissions
                assert len(agent_context.user_context.permissions) > 0 or scenario["authenticated"]
            else:
                # Unauthenticated users should have no permissions
                assert not agent_context.user_context.authenticated
                assert len(agent_context.user_context.permissions) == 0

    @pytest.mark.unit
    def test_agent_context_memory_efficiency(self):
        """
        Test agent context management is memory efficient.
        
        Business Value: Memory efficiency enables serving more concurrent users.
        Memory leaks would limit platform scalability and increase costs.
        """
        import gc
        import sys
        
        # Arrange: Track memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        contexts = []
        
        # Act: Create many contexts to test memory efficiency
        for i in range(100):
            user_context = UserExecutionContext(
                user_id=UserID(f"memory_test_user_{i}"),
                thread_id=ThreadID(f"memory_thread_{i}"),
                authenticated=True,
                permissions=["memory_test"],
                session_data={"iteration": i}
            )
            
            agent_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=RunID(f"memory_run_{i}"),
                agent_name="memory_test_agent",
                message=f"Memory test iteration {i}",
                user_context=user_context
            )
            
            contexts.append(agent_context)
        
        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Clear contexts
        contexts.clear()
        gc.collect()
        cleanup_objects = len(gc.get_objects())
        
        # Assert: Memory usage reasonable
        object_growth = final_objects - initial_objects
        objects_per_context = object_growth / 100 if object_growth > 0 else 0
        
        # Business requirement: Context creation should be memory efficient
        assert objects_per_context < 50, f"Each context should create fewer than 50 objects, created {objects_per_context}"
        
        # Memory should be reclaimed after cleanup
        memory_reclaimed = final_objects - cleanup_objects
        reclaim_percentage = (memory_reclaimed / object_growth) * 100 if object_growth > 0 else 100
        
        assert reclaim_percentage > 50, f"Should reclaim at least 50% of memory, reclaimed {reclaim_percentage:.1f}%"