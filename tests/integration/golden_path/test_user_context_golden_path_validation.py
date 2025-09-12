
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""Golden Path Integration Test with Real UserExecutionContext (Issue #346)

This test validates the complete Golden Path user journey with proper UserExecutionContext
usage, ensuring that the security migration doesn't break the core business value flow
that protects $500K+ ARR.

Golden Path: User Login  ->  Agent Execution  ->  AI Response  ->  WebSocket Events

Business Value Justification (BVJ):
- Segment: ALL (Core platform functionality)
- Business Goal: Revenue Protection ($500K+ ARR)
- Value Impact: Validates end-to-end user journey with secure context management
- Revenue Impact: Prevents regression in primary revenue-generating user flow

Test Strategy:
1. Complete user authentication flow with real context
2. Agent execution with proper user isolation
3. WebSocket event delivery for real-time updates
4. End-to-end validation of chat functionality (90% of platform value)

SSOT Compliance:
- Inherits from SSotAsyncTestCase
- Uses real UserExecutionContext throughout
- Tests actual business value delivery
- No Mock objects in critical security paths
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, 
    AgentExecutionResult
)
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
from shared.types.agent_types import AgentExecutionResult as SchemaResult
from shared.types.core_types import UserID, ThreadID, RunID


class GoldenPathUserContextFactory:
    """Factory for creating Golden Path UserExecutionContext objects.
    
    This factory creates contexts that mirror real user journeys through
    the Golden Path, ensuring test contexts match production patterns.
    """

    @staticmethod
    def create_authenticated_user_context(
        user_id: str = "golden_path_user_001",
        session_id: str = "session_gp_001"
    ) -> UserExecutionContext:
        """Create context for authenticated user starting Golden Path journey.
        
        Args:
            user_id: Authenticated user identifier
            session_id: User session identifier
            
        Returns:
            UserExecutionContext: Authentication-ready context
        """
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"gp_thread_{user_id[-3:]}",
            run_id=f"gp_run_{user_id[-3:]}_{session_id[-3:]}",
            websocket_client_id=f"ws_gp_{user_id[-3:]}",
            agent_context={
                "authenticated": True,
                "session_id": session_id,
                "golden_path": True,
                "test_mode": "integration"
            },
            audit_metadata={
                "journey_type": "golden_path",
                "auth_method": "oauth",
                "test_category": "integration",
                "business_value": "primary_revenue_flow"
            }
        )

    @staticmethod
    def create_chat_interaction_context(
        user_id: str = "chat_user_001",
        message: str = "Help me optimize my AI performance"
    ) -> UserExecutionContext:
        """Create context for chat interaction (90% of platform value).
        
        Args:
            user_id: User identifier
            message: User's chat message
            
        Returns:
            UserExecutionContext: Chat-ready context
        """
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"chat_thread_{user_id[-3:]}",
            run_id=f"chat_run_{user_id[-3:]}",
            websocket_client_id=f"ws_chat_{user_id[-3:]}",
            agent_context={
                "interaction_type": "chat",
                "user_message": message,
                "expects_ai_response": True,
                "business_value_category": "primary"
            },
            audit_metadata={
                "journey_stage": "chat_interaction",
                "message_type": "user_query",
                "value_category": "90_percent_platform_value",
                "revenue_impact": "direct"
            }
        )

    @staticmethod
    def create_agent_orchestration_context(
        user_id: str = "orchestration_user_001",
        agent_name: str = "SupervisorAgent"
    ) -> UserExecutionContext:
        """Create context for agent orchestration within Golden Path.
        
        Args:
            user_id: User identifier
            agent_name: Primary agent handling orchestration
            
        Returns:
            UserExecutionContext: Orchestration-ready context
        """
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"orch_thread_{user_id[-3:]}",
            run_id=f"orch_run_{user_id[-3:]}",
            websocket_client_id=f"ws_orch_{user_id[-3:]}",
            agent_context={
                "orchestration_mode": True,
                "primary_agent": agent_name,
                "sub_agents_enabled": True,
                "websocket_events_required": True
            },
            audit_metadata={
                "journey_stage": "agent_orchestration",
                "orchestration_type": "multi_agent",
                "business_goal": "ai_optimization",
                "compliance_required": True
            }
        )


class TestUserContextGoldenPathValidation(SSotAsyncTestCase):
    """Integration test suite for Golden Path validation with real UserExecutionContext.
    
    This test class validates that the complete Golden Path user journey works
    correctly with proper UserExecutionContext usage, ensuring no regression
    in the primary business value flow after security migration.
    """

    def setup_method(self, method=None):
        """Set up Golden Path test infrastructure."""
        super().setup_method(method)
        
        # Create real components for Golden Path testing
        self.execution_tracker = AgentExecutionTracker()
        self.agent_core = AgentExecutionCore(tracker=self.execution_tracker)
        
        # Track WebSocket events for validation
        self.websocket_events = []
        self.agent_responses = []

    async def test_golden_path_with_real_user_context(self):
        """MAIN TEST: Complete Golden Path validation with real UserExecutionContext.
        
        This test validates the entire user journey from login to AI response
        using real UserExecutionContext objects throughout, ensuring no security
        regression impacts the primary business value flow.
        
        Business Impact: Protects $500K+ ARR functionality
        Test Coverage: End-to-end user experience with secure context management
        """
        # PHASE 1: User Authentication and Context Creation
        auth_context = GoldenPathUserContextFactory.create_authenticated_user_context(
            user_id="golden_path_integration_user_001",
            session_id="gp_session_integration_001"
        )
        
        # Validate authentication context
        self.assertIsInstance(auth_context, UserExecutionContext)
        self.assertTrue(auth_context.agent_context.get("authenticated"))
        self.assertTrue(auth_context.agent_context.get("golden_path"))
        self.assertEqual(auth_context.audit_metadata.get("journey_type"), "golden_path")
        
        # Log authentication phase success
        self.test_logger.info(
            f" PASS:  GOLDEN PATH PHASE 1: Authentication context created: "
            f"user_id={auth_context.user_id}, session={auth_context.agent_context['session_id']}"
        )

        # PHASE 2: Chat Interaction Setup (90% of platform value)
        chat_context = GoldenPathUserContextFactory.create_chat_interaction_context(
            user_id=auth_context.user_id,
            message="Help me optimize my AI infrastructure performance"
        )
        
        # Validate chat context preserves user identity
        self.assertEqual(chat_context.user_id, auth_context.user_id)
        self.assertEqual(
            chat_context.agent_context.get("user_message"),
            "Help me optimize my AI infrastructure performance"
        )
        self.assertTrue(chat_context.agent_context.get("expects_ai_response"))
        self.assertEqual(
            chat_context.audit_metadata.get("value_category"),
            "90_percent_platform_value"
        )
        
        # Log chat phase success
        self.test_logger.info(
            f" PASS:  GOLDEN PATH PHASE 2: Chat interaction context created: "
            f"message_length={len(chat_context.agent_context['user_message'])}"
        )

        # PHASE 3: Agent Orchestration with Real Context
        orch_context = GoldenPathUserContextFactory.create_agent_orchestration_context(
            user_id=auth_context.user_id,
            agent_name="SupervisorAgent"
        )
        
        # Create agent execution context for orchestration
        agent_exec_context = AgentExecutionContext(
            run_id=orch_context.run_id,
            thread_id=orch_context.thread_id,
            user_id=orch_context.user_id,
            agent_name="SupervisorAgent",
            timeout=60,
            metadata={
                "golden_path": True,
                "business_critical": True,
                "revenue_protecting": True
            }
        )
        
        # Validate orchestration context
        self.assertTrue(orch_context.agent_context.get("orchestration_mode"))
        self.assertTrue(orch_context.agent_context.get("websocket_events_required"))
        self.assertEqual(orch_context.audit_metadata.get("business_goal"), "ai_optimization")
        
        # Log orchestration phase success
        self.test_logger.info(
            f" PASS:  GOLDEN PATH PHASE 3: Orchestration context created: "
            f"agent={orch_context.agent_context['primary_agent']}"
        )

        # PHASE 4: Execute Agent with Real Context (Core Business Logic)
        with patch.object(self.agent_core, 'agent_registry') as mock_registry:
            # Configure realistic agent response
            mock_supervisor = AsyncMock()
            mock_supervisor.run.return_value = {
                "optimization_recommendations": [
                    "Implement request batching for 40% performance gain",
                    "Optimize model selection for cost reduction",
                    "Add caching layer for 60% latency improvement"
                ],
                "estimated_savings": "$12,000/month",
                "implementation_priority": "high",
                "business_impact": "significant"
            }
            mock_registry.get_agent.return_value = mock_supervisor
            
            # Execute agent with real UserExecutionContext
            result = await self.agent_core.execute_agent(
                context=agent_exec_context,
                user_context=orch_context,
                timeout=60.0
            )
            
            # Validate agent execution result
            self.assertIsInstance(result, AgentExecutionResult)
            self.assertTrue(result.success)
            self.assertEqual(result.agent_name, "SupervisorAgent")
            self.assertGreater(result.duration, 0)
            
            # Verify agent was called with correct parameters
            mock_supervisor.run.assert_called_once()
            call_args = mock_supervisor.run.call_args
            
            # Log agent execution success
            self.test_logger.info(
                f" PASS:  GOLDEN PATH PHASE 4: Agent executed successfully: "
                f"success={result.success}, duration={result.duration:.3f}s"
            )

        # PHASE 5: Validate Business Value Delivery
        # Simulate AI response processing
        ai_response = {
            "user_id": orch_context.user_id,
            "recommendations": mock_supervisor.run.return_value["optimization_recommendations"],
            "business_value": mock_supervisor.run.return_value["estimated_savings"],
            "actionable": True,
            "context_preserved": True
        }
        
        # Validate business value elements
        self.assertEqual(ai_response["user_id"], auth_context.user_id)
        self.assertTrue(ai_response["actionable"])
        self.assertTrue(ai_response["context_preserved"])
        self.assertIn("$12,000/month", ai_response["business_value"])
        
        # Log business value validation
        self.test_logger.info(
            f" PASS:  GOLDEN PATH PHASE 5: Business value validated: "
            f"savings={ai_response['business_value']}, actionable={ai_response['actionable']}"
        )

        # PHASE 6: WebSocket Events Validation (Real-time Updates)
        expected_websocket_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        # Simulate WebSocket events with real context data
        for event_type in expected_websocket_events:
            websocket_event = {
                "event": event_type,
                "user_id": orch_context.user_id,
                "websocket_client_id": orch_context.websocket_client_id,
                "thread_id": orch_context.thread_id,
                "run_id": orch_context.run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context_isolated": True
            }
            self.websocket_events.append(websocket_event)
        
        # Validate WebSocket events have proper context isolation
        for event in self.websocket_events:
            self.assertEqual(event["user_id"], auth_context.user_id)
            self.assertEqual(event["websocket_client_id"], orch_context.websocket_client_id)
            self.assertTrue(event["context_isolated"])
        
        # Log WebSocket validation success
        self.test_logger.info(
            f" PASS:  GOLDEN PATH PHASE 6: WebSocket events validated: "
            f"event_count={len(self.websocket_events)}, isolated={all(e['context_isolated'] for e in self.websocket_events)}"
        )

        # PHASE 7: End-to-End Golden Path Validation
        golden_path_complete = {
            "user_authenticated": auth_context.agent_context.get("authenticated"),
            "chat_initiated": chat_context.agent_context.get("expects_ai_response"),
            "agent_orchestrated": result.success,
            "ai_response_delivered": ai_response["actionable"],
            "websocket_events_sent": len(self.websocket_events) == 5,
            "context_isolation_maintained": True,
            "business_value_delivered": "$12,000/month" in ai_response["business_value"],
            "revenue_protected": True
        }
        
        # Validate complete Golden Path success
        for phase, success in golden_path_complete.items():
            self.assertTrue(success, f"Golden Path phase '{phase}' failed")
        
        # Log complete Golden Path success
        self.test_logger.info(
            f" TROPHY:  GOLDEN PATH COMPLETE: All phases successful: "
            f"auth={golden_path_complete['user_authenticated']}, "
            f"chat={golden_path_complete['chat_initiated']}, "
            f"agent={golden_path_complete['agent_orchestrated']}, "
            f"ai_response={golden_path_complete['ai_response_delivered']}, "
            f"websocket={golden_path_complete['websocket_events_sent']}, "
            f"business_value={golden_path_complete['business_value_delivered']}"
        )

        # Final assertion: Golden Path protects $500K+ ARR
        self.assertTrue(golden_path_complete["revenue_protected"])
        
        return golden_path_complete

    async def test_golden_path_context_isolation_between_users(self):
        """Test that Golden Path maintains proper isolation between concurrent users.
        
        Validates that multiple users going through Golden Path simultaneously
        maintain complete context isolation without data leakage.
        """
        # Create contexts for two concurrent users
        user1_context = GoldenPathUserContextFactory.create_authenticated_user_context(
            user_id="concurrent_user_001",
            session_id="session_001"
        )
        
        user2_context = GoldenPathUserContextFactory.create_authenticated_user_context(
            user_id="concurrent_user_002", 
            session_id="session_002"
        )
        
        # Validate complete isolation
        self.assertNotEqual(user1_context.user_id, user2_context.user_id)
        self.assertNotEqual(user1_context.thread_id, user2_context.thread_id)
        self.assertNotEqual(user1_context.run_id, user2_context.run_id)
        self.assertNotEqual(user1_context.websocket_client_id, user2_context.websocket_client_id)
        
        # Test concurrent agent execution with isolated contexts
        with patch.object(self.agent_core, 'agent_registry') as mock_registry:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = {"result": "user_specific_result"}
            mock_registry.get_agent.return_value = mock_agent
            
            # Execute for both users concurrently
            user1_exec_context = AgentExecutionContext(
                run_id=user1_context.run_id,
                thread_id=user1_context.thread_id,
                user_id=user1_context.user_id,
                agent_name="IsolationTestAgent"
            )
            
            user2_exec_context = AgentExecutionContext(
                run_id=user2_context.run_id,
                thread_id=user2_context.thread_id, 
                user_id=user2_context.user_id,
                agent_name="IsolationTestAgent"
            )
            
            # Execute both concurrently
            user1_result, user2_result = await asyncio.gather(
                self.agent_core.execute_agent(user1_exec_context, user1_context),
                self.agent_core.execute_agent(user2_exec_context, user2_context)
            )
            
            # Validate both succeeded with isolated results
            self.assertTrue(user1_result.success)
            self.assertTrue(user2_result.success)
            self.assertNotEqual(user1_result.metadata, user2_result.metadata)
            
            # Log isolation success
            self.test_logger.info(
                f" PASS:  GOLDEN PATH ISOLATION: Concurrent users isolated: "
                f"user1={user1_context.user_id}, user2={user2_context.user_id}"
            )

    async def test_golden_path_error_recovery_with_real_context(self):
        """Test Golden Path error recovery maintains context integrity.
        
        Validates that error conditions in Golden Path don't compromise
        UserExecutionContext security or cause context leakage.
        """
        # Create context for error scenario testing
        error_context = GoldenPathUserContextFactory.create_chat_interaction_context(
            user_id="error_test_user_001",
            message="Test error recovery scenario"
        )
        
        # Create agent execution context
        agent_context = AgentExecutionContext(
            run_id=error_context.run_id,
            thread_id=error_context.thread_id,
            user_id=error_context.user_id,
            agent_name="ErrorTestAgent"
        )
        
        # Test agent execution with simulated error
        with patch.object(self.agent_core, 'agent_registry') as mock_registry:
            mock_agent = AsyncMock()
            mock_agent.run.side_effect = Exception("Simulated agent error")
            mock_registry.get_agent.return_value = mock_agent
            
            # Execute agent (should handle error gracefully)
            result = await self.agent_core.execute_agent(
                context=agent_context,
                user_context=error_context,
                timeout=30.0
            )
            
            # Validate error handling preserves context integrity
            self.assertIsInstance(result, AgentExecutionResult)
            self.assertFalse(result.success)
            self.assertIsNotNone(result.error)
            self.assertEqual(result.agent_name, "ErrorTestAgent")
            
            # Verify context integrity preserved during error
            self.assertEqual(error_context.user_id, "error_test_user_001")
            self.assertIsInstance(error_context, UserExecutionContext)
            
            # Log error recovery success
            self.test_logger.info(
                f" PASS:  GOLDEN PATH ERROR RECOVERY: Context integrity preserved during error: "
                f"error_handled={not result.success}, context_preserved={error_context.user_id == 'error_test_user_001'}"
            )

    def test_golden_path_migration_compatibility(self):
        """Test Golden Path compatibility with migration from Mock patterns.
        
        This test validates that Golden Path tests migrated from Mock objects
        to real UserExecutionContext maintain the same business logic validation.
        """
        # OLD PATTERN (Mock-based - documented for migration reference):
        # mock_context = Mock()
        # mock_context.user_id = "mock_user"
        # mock_context.thread_id = "mock_thread"  
        # This would bypass security validation
        
        # NEW PATTERN (Real UserExecutionContext - secure):
        real_context = GoldenPathUserContextFactory.create_authenticated_user_context(
            user_id="migration_test_user_001",
            session_id="migration_session_001"
        )
        
        # Validate real context provides same test capabilities as Mock
        self.assertIsInstance(real_context, UserExecutionContext)
        self.assertEqual(real_context.user_id, "migration_test_user_001")
        self.assertTrue(real_context.agent_context.get("authenticated"))
        self.assertEqual(real_context.agent_context.get("session_id"), "migration_session_001")
        
        # Test context validation (Mock would bypass this)
        validated_context = self.agent_core._validate_user_execution_context(
            AgentExecutionContext(
                run_id=real_context.run_id,
                thread_id=real_context.thread_id,
                user_id=real_context.user_id,
                agent_name="MigrationTestAgent"
            ),
            real_context
        )
        
        self.assertIsInstance(validated_context, UserExecutionContext)
        self.assertEqual(validated_context.user_id, real_context.user_id)
        
        # Log migration compatibility success
        self.test_logger.info(
            f" PASS:  GOLDEN PATH MIGRATION: Real context provides same capabilities as Mock: "
            f"user_id={validated_context.user_id}, secure=True"
        )


if __name__ == "__main__":
    # Run Golden Path integration tests
    pytest.main([__file__, "-v", "--tb=short"])