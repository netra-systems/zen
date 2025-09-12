"""SSOT Test Suite for Correct UserExecutionContext Patterns (Issue #346)

This test suite demonstrates the CORRECT patterns for using UserExecutionContext
in tests, serving as a template and reference for migrating the 192 failing test
files from Mock objects to proper security-compliant patterns.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Infrastructure
- Business Goal: Development Velocity & Security Compliance
- Value Impact: Enables 192 test files to migrate from insecure Mock patterns
- Revenue Impact: Unblocks Golden Path testing protecting $500K+ ARR

Migration Strategy:
1. Factory patterns for creating test contexts
2. Reusable context builders for different scenarios
3. Validation patterns for context integrity
4. Integration patterns with existing test infrastructure

SSOT Compliance:
- Inherits from SSotAsyncTestCase (unified test infrastructure)
- Demonstrates real UserExecutionContext usage (no mocks)
- Provides migration templates for systematic conversion
- Documents security-compliant testing patterns
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    InvalidContextError, 
    ContextIsolationError
)
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, 
    AgentExecutionResult
)
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
from shared.types.core_types import UserID, ThreadID, RunID


class UserExecutionContextFactory:
    """Factory for creating test UserExecutionContext objects with proper patterns.
    
    This factory provides standardized methods for creating UserExecutionContext
    objects in tests, ensuring consistency and security compliance across all
    test implementations.
    """

    @staticmethod
    def create_basic_context(
        user_id: str = "factory_user_123",
        thread_id: str = "factory_thread_456", 
        run_id: str = "factory_run_789"
    ) -> UserExecutionContext:
        """Create basic UserExecutionContext for simple tests.
        
        Args:
            user_id: Unique user identifier
            thread_id: Unique thread identifier  
            run_id: Unique run identifier
            
        Returns:
            UserExecutionContext: Properly configured context
        """
        return UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=f"req_{user_id[-3:]}_{thread_id[-3:]}",
            websocket_client_id=f"ws_{user_id[-3:]}"
        )

    @staticmethod
    def create_websocket_context(
        user_id: str = "ws_user_123",
        websocket_client_id: str = "ws_client_789"
    ) -> UserExecutionContext:
        """Create UserExecutionContext for WebSocket testing.
        
        Args:
            user_id: Unique user identifier
            websocket_client_id: WebSocket connection identifier
            
        Returns:
            UserExecutionContext: WebSocket-enabled context
        """
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"ws_thread_{user_id[-3:]}",
            run_id=f"ws_run_{user_id[-3:]}",
            websocket_client_id=websocket_client_id,
            agent_context={"websocket_enabled": True},
            audit_metadata={"test_type": "websocket"}
        )

    @staticmethod
    def create_agent_context(
        user_id: str = "agent_user_123",
        agent_name: str = "TestAgent",
        agent_data: Optional[Dict[str, Any]] = None
    ) -> UserExecutionContext:
        """Create UserExecutionContext for agent execution testing.
        
        Args:
            user_id: Unique user identifier
            agent_name: Name of agent being tested
            agent_data: Optional agent-specific data
            
        Returns:
            UserExecutionContext: Agent-ready context
        """
        agent_context = {"agent_name": agent_name}
        if agent_data:
            agent_context.update(agent_data)
            
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"agent_thread_{user_id[-3:]}",
            run_id=f"agent_run_{user_id[-3:]}",
            agent_context=agent_context,
            audit_metadata={
                "test_type": "agent_execution",
                "agent_name": agent_name
            }
        )

    @staticmethod
    def create_child_context(
        parent_context: UserExecutionContext,
        operation_name: str = "child_operation"
    ) -> UserExecutionContext:
        """Create child UserExecutionContext for nested operations.
        
        Args:
            parent_context: Parent context to derive from
            operation_name: Name of child operation
            
        Returns:
            UserExecutionContext: Child context with proper isolation
        """
        return UserExecutionContext(
            user_id=parent_context.user_id,
            thread_id=parent_context.thread_id,
            run_id=f"child_{parent_context.run_id}_{operation_name}",
            parent_request_id=parent_context.request_id,
            operation_depth=parent_context.operation_depth + 1,
            websocket_client_id=parent_context.websocket_client_id,
            agent_context={**parent_context.agent_context, "child_op": operation_name},
            audit_metadata={
                **parent_context.audit_metadata,
                "parent_request": parent_context.request_id,
                "operation": operation_name
            }
        )


class TestUserExecutionContextCorrectPatterns(SSotAsyncTestCase):
    """Test suite demonstrating correct UserExecutionContext usage patterns.
    
    This test class provides executable examples of how to properly use
    UserExecutionContext in tests, serving as migration templates for
    converting Mock-based tests to security-compliant patterns.
    """

    def setup_method(self, method=None):
        """Set up test fixtures with proper UserExecutionContext patterns."""
        super().setup_method(method)
        
        # Create real components (no mocks for core infrastructure)
        self.execution_tracker = AgentExecutionTracker()
        self.agent_core = AgentExecutionCore(tracker=self.execution_tracker)
        
        # Create standard test contexts using factory
        self.basic_context = UserExecutionContextFactory.create_basic_context()
        self.websocket_context = UserExecutionContextFactory.create_websocket_context()
        self.agent_context = UserExecutionContextFactory.create_agent_context()

    def test_basic_user_execution_context_creation(self):
        """Test basic UserExecutionContext creation and validation.
        
        This test demonstrates the simplest correct pattern for creating
        UserExecutionContext objects in tests.
        """
        # Create context using factory (CORRECT PATTERN)
        context = UserExecutionContextFactory.create_basic_context(
            user_id="basic_test_user_001",
            thread_id="basic_test_thread_001",
            run_id="basic_test_run_001"
        )
        
        # Validate context is properly created
        self.assertIsInstance(context, UserExecutionContext)
        self.assertEqual(context.user_id, "basic_test_user_001")
        self.assertEqual(context.thread_id, "basic_test_thread_001")
        self.assertEqual(context.run_id, "basic_test_run_001")
        self.assertIsNotNone(context.request_id)
        self.assertIsInstance(context.created_at, datetime)
        
        # Log successful pattern
        self.test_logger.info(
            f" PASS:  BASIC PATTERN: UserExecutionContext created successfully: "
            f"user_id={context.user_id}, thread_id={context.thread_id}"
        )

    def test_websocket_user_execution_context_pattern(self):
        """Test WebSocket-enabled UserExecutionContext pattern.
        
        This demonstrates the correct pattern for tests involving WebSocket
        functionality, replacing Mock WebSocket connections.
        """
        # Create WebSocket context (CORRECT PATTERN for WebSocket tests)
        ws_context = UserExecutionContextFactory.create_websocket_context(
            user_id="websocket_test_user_001",
            websocket_client_id="ws_test_client_001"
        )
        
        # Validate WebSocket-specific features
        self.assertEqual(ws_context.websocket_client_id, "ws_test_client_001")
        self.assertTrue(ws_context.agent_context.get("websocket_enabled"))
        self.assertEqual(ws_context.audit_metadata.get("test_type"), "websocket")
        
        # Test WebSocket context validation
        validated_context = self.agent_core._validate_user_execution_context(
            AgentExecutionContext(
                run_id=ws_context.run_id,
                thread_id=ws_context.thread_id,
                user_id=ws_context.user_id,
                agent_name="WebSocketTestAgent"
            ),
            ws_context
        )
        
        self.assertIsInstance(validated_context, UserExecutionContext)
        self.assertEqual(validated_context.websocket_client_id, "ws_test_client_001")
        
        # Log WebSocket pattern success
        self.test_logger.info(
            f" PASS:  WEBSOCKET PATTERN: WebSocket context validated: "
            f"ws_client_id={validated_context.websocket_client_id}"
        )

    def test_agent_execution_context_pattern(self):
        """Test agent-specific UserExecutionContext pattern.
        
        This demonstrates the correct pattern for tests involving agent
        execution, replacing Mock agent objects and state.
        """
        # Create agent context with specific agent data
        agent_context = UserExecutionContextFactory.create_agent_context(
            user_id="agent_test_user_001",
            agent_name="DataHelperAgent",
            agent_data={
                "data_requirements": ["user_metrics", "performance_data"],
                "optimization_level": "high"
            }
        )
        
        # Validate agent-specific context data
        self.assertEqual(agent_context.agent_context["agent_name"], "DataHelperAgent")
        self.assertIn("data_requirements", agent_context.agent_context)
        self.assertEqual(agent_context.agent_context["optimization_level"], "high")
        self.assertEqual(agent_context.audit_metadata["agent_name"], "DataHelperAgent")
        
        # Test agent context validation
        agent_exec_context = AgentExecutionContext(
            run_id=agent_context.run_id,
            thread_id=agent_context.thread_id,
            user_id=agent_context.user_id,
            agent_name="DataHelperAgent"
        )
        
        validated_context = self.agent_core._validate_user_execution_context(
            agent_exec_context,
            agent_context
        )
        
        self.assertIsInstance(validated_context, UserExecutionContext)
        self.assertEqual(validated_context.agent_context["agent_name"], "DataHelperAgent")
        
        # Log agent pattern success
        self.test_logger.info(
            f" PASS:  AGENT PATTERN: Agent context validated: "
            f"agent={validated_context.agent_context['agent_name']}"
        )

    def test_child_context_creation_pattern(self):
        """Test child context creation for nested operations.
        
        This demonstrates the correct pattern for creating child contexts
        in tests involving nested agent operations or sub-agent calls.
        """
        # Create parent context
        parent_context = UserExecutionContextFactory.create_basic_context(
            user_id="parent_user_001",
            thread_id="parent_thread_001",
            run_id="parent_run_001"
        )
        
        # Create child context (CORRECT PATTERN for nested operations)
        child_context = UserExecutionContextFactory.create_child_context(
            parent_context=parent_context,
            operation_name="sub_agent_execution"
        )
        
        # Validate child context properties
        self.assertEqual(child_context.user_id, parent_context.user_id)
        self.assertEqual(child_context.thread_id, parent_context.thread_id)
        self.assertIn("child_", child_context.run_id)
        self.assertEqual(child_context.parent_request_id, parent_context.request_id)
        self.assertEqual(child_context.operation_depth, 1)
        self.assertEqual(child_context.agent_context["child_op"], "sub_agent_execution")
        
        # Log child context pattern success
        self.test_logger.info(
            f" PASS:  CHILD PATTERN: Child context created: "
            f"parent_id={child_context.parent_request_id}, depth={child_context.operation_depth}"
        )

    async def test_agent_execution_with_real_context_pattern(self):
        """Test complete agent execution with real UserExecutionContext.
        
        This demonstrates the full pattern for testing agent execution
        without Mock objects, using real UserExecutionContext throughout.
        """
        # Create real execution context
        user_context = UserExecutionContextFactory.create_agent_context(
            user_id="execution_test_user_001",
            agent_name="ExecutionTestAgent",
            agent_data={"test_mode": True, "validation": "enabled"}
        )
        
        # Create agent execution context
        agent_exec_context = AgentExecutionContext(
            run_id=user_context.run_id,
            thread_id=user_context.thread_id,
            user_id=user_context.user_id,
            agent_name="ExecutionTestAgent",
            timeout=30
        )
        
        # Mock only the agent registry (not the context or core components)
        with patch.object(self.agent_core, 'agent_registry') as mock_registry:
            # Configure agent mock to return test result
            mock_agent = AsyncMock()
            mock_agent.run.return_value = {
                "result": "Agent execution successful",
                "data": {"processed": True, "validation": "passed"}
            }
            mock_registry.get_agent.return_value = mock_agent
            
            # Execute with real UserExecutionContext (CORRECT PATTERN)
            result = await self.agent_core.execute_agent(
                context=agent_exec_context,
                user_context=user_context,
                timeout=30.0
            )
            
            # Validate execution result
            self.assertIsInstance(result, AgentExecutionResult)
            self.assertTrue(result.success)
            self.assertEqual(result.agent_name, "ExecutionTestAgent")
            self.assertIsNotNone(result.duration)
            
            # Verify agent was called with correct context
            mock_agent.run.assert_called_once()
            
            # Log execution pattern success
            self.test_logger.info(
                f" PASS:  EXECUTION PATTERN: Agent executed successfully: "
                f"success={result.success}, duration={result.duration:.3f}s"
            )

    def test_context_isolation_validation_pattern(self):
        """Test context isolation validation patterns.
        
        This demonstrates how to test that contexts maintain proper isolation
        without using Mock objects that could bypass security checks.
        """
        # Create multiple isolated contexts
        context1 = UserExecutionContextFactory.create_basic_context(
            user_id="isolation_user_001",
            thread_id="isolation_thread_001"
        )
        
        context2 = UserExecutionContextFactory.create_basic_context(
            user_id="isolation_user_002", 
            thread_id="isolation_thread_002"
        )
        
        # Validate contexts are properly isolated
        self.assertNotEqual(context1.user_id, context2.user_id)
        self.assertNotEqual(context1.thread_id, context2.thread_id)
        self.assertNotEqual(context1.run_id, context2.run_id)
        self.assertNotEqual(context1.request_id, context2.request_id)
        
        # Test that contexts maintain independent agent_context
        context1.agent_context["user_specific_data"] = "user1_data"
        context2.agent_context["user_specific_data"] = "user2_data"
        
        self.assertEqual(context1.agent_context["user_specific_data"], "user1_data")
        self.assertEqual(context2.agent_context["user_specific_data"], "user2_data")
        
        # Log isolation validation success
        self.test_logger.info(
            f" PASS:  ISOLATION PATTERN: Context isolation validated: "
            f"context1_user={context1.user_id}, context2_user={context2.user_id}"
        )

    def test_context_validation_error_handling_pattern(self):
        """Test proper error handling for context validation.
        
        This demonstrates how to test error conditions with real contexts
        instead of Mock objects that might not trigger proper validation.
        """
        # Test various validation scenarios with real contexts
        
        # Empty user_id should fail validation
        with pytest.raises(ValueError) as exc_info:
            UserExecutionContext(
                user_id="",
                thread_id="valid_thread",
                run_id="valid_run"
            )
        self.assertIn("Invalid user_id", str(exc_info.value))
        
        # Placeholder values should fail validation
        with pytest.raises(ValueError) as exc_info:
            UserExecutionContext(
                user_id="test_user",  # Placeholder pattern
                thread_id="valid_thread",
                run_id="valid_run"
            )
        self.assertIn("placeholder or test value detected", str(exc_info.value))
        
        # Log validation error pattern success
        self.test_logger.info(" PASS:  ERROR PATTERN: Context validation errors properly handled")

    def test_migration_documentation_patterns(self):
        """Test that provides migration documentation for common patterns.
        
        This test serves as executable documentation for migrating from
        Mock-based tests to UserExecutionContext-based tests.
        """
        # OLD PATTERN (Mock-based - DO NOT USE):
        # mock_context = Mock()
        # mock_context.user_id = "test_user"
        # mock_context.thread_id = "test_thread"
        # mock_context.run_id = "test_run"
        
        # NEW PATTERN (UserExecutionContext-based - CORRECT):
        real_context = UserExecutionContextFactory.create_basic_context(
            user_id="migration_example_user",
            thread_id="migration_example_thread", 
            run_id="migration_example_run"
        )
        
        # Validate new pattern works correctly
        self.assertIsInstance(real_context, UserExecutionContext)
        self.assertEqual(real_context.user_id, "migration_example_user")
        
        # OLD PATTERN (Mock WebSocket - DO NOT USE):
        # mock_websocket = Mock()
        # mock_websocket.client_id = "ws_123"
        
        # NEW PATTERN (Real WebSocket context - CORRECT):
        ws_context = UserExecutionContextFactory.create_websocket_context(
            user_id="ws_migration_user",
            websocket_client_id="ws_migration_123"
        )
        
        self.assertEqual(ws_context.websocket_client_id, "ws_migration_123")
        
        # Log migration patterns
        self.test_logger.info(
            " PASS:  MIGRATION PATTERNS: All migration examples validated successfully"
        )


if __name__ == "__main__":
    # Run tests with proper SSOT test runner
    pytest.main([__file__, "-v", "--tb=short"])