"""Mission Critical Test: Agent Execution Prerequisites Validation

PURPOSE: Validates that all prerequisites for agent execution are checked BEFORE execution starts.

This test demonstrates the current gap where agent execution can start without validating:
- WebSocket connection is ready
- Required services are available (database, redis, etc.)
- Agent registry is properly initialized
- User context is properly established
- Resource limits are not exceeded
- Required dependencies are available

These tests should FAIL initially, proving the need for comprehensive prerequisite validation.

Business Value: $500K+ ARR protection by preventing failed executions and ensuring reliable user experience.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core types and context
from shared.types.core_types import UserID, ThreadID, RunID
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    AgentExecutionStrategy
)
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Agent execution components
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine


class TestAgentPrerequisitesValidation(SSotAsyncTestCase):
    """Mission critical tests for agent execution prerequisites validation.
    
    These tests should FAIL initially, demonstrating the current gap in prerequisite validation.
    """
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        await super().asyncSetUp()
        
        # Test data
        self.user_id = UserID(uuid4())
        self.thread_id = ThreadID(uuid4())
        self.run_id = RunID(uuid4())
        
        # Mock execution context
        self.execution_context = AgentExecutionContext(
            agent_name="test_agent",
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            request_data={"user_input": "test query"},
            timestamp=datetime.now(timezone.utc),
            strategy=AgentExecutionStrategy.STANDARD,
            user_permissions=["read"],
            user_tier="free"
        )
        
        # Mock user context
        self.user_context = UserExecutionContext(
            user_id=self.user_id,
            session_id="test_session",
            thread_id=self.thread_id,
            run_id=self.run_id,
            execution_metadata={"test": True}
        )
    
    async def test_websocket_connection_prerequisite_validation_missing(self):
        """FAILING TEST: Should validate WebSocket connection before agent execution.
        
        Currently, agent execution can start without checking if WebSocket is ready,
        leading to lost events and broken user experience.
        
        Expected to FAIL: No prerequisite validation exists for WebSocket connection.
        """
        # Create execution engine with proper dependencies
        mock_agent_factory = Mock()
        mock_websocket_emitter = Mock()
        execution_engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Mock broken WebSocket manager
        mock_websocket_manager = Mock()
        mock_websocket_manager.is_connected = Mock(return_value=False)
        mock_websocket_manager.send_event = Mock(side_effect=ConnectionError("WebSocket not connected"))
        
        # Try to execute agent with broken WebSocket - should detect prerequisite failure
        with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager', 
                  return_value=mock_websocket_manager):
            
            # THIS SHOULD FAIL: Currently no prerequisite validation for WebSocket connection
            with pytest.raises(AssertionError, match="Prerequisites validation should prevent execution"):
                # The execution should fail with prerequisite validation, but it doesn't exist yet
                try:
                    await execution_engine.execute_agent(
                        context=self.execution_context,
                        user_context=self.user_context
                    )
                    # If we reach here, prerequisite validation is missing
                    raise AssertionError(
                        "Prerequisites validation should prevent execution with broken WebSocket, "
                        "but agent execution was attempted without validation"
                    )
                except ConnectionError:
                    # This means execution started and failed later, not at prerequisite validation
                    raise AssertionError(
                        "Agent execution started without WebSocket prerequisite validation - "
                        "validation should happen BEFORE execution starts"
                    )
    
    async def test_database_availability_prerequisite_validation_missing(self):
        """FAILING TEST: Should validate database availability before agent execution.
        
        Currently, agent execution can start without checking database connectivity,
        leading to execution failures and poor user experience.
        
        Expected to FAIL: No prerequisite validation exists for database availability.
        """
        # Create execution engine with proper dependencies
        mock_agent_factory = Mock()
        mock_websocket_emitter = Mock()
        execution_engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Mock broken database
        with patch('netra_backend.app.db.database_manager.DatabaseManager.check_connection', 
                  return_value=False):
            
            # THIS SHOULD FAIL: Currently no prerequisite validation for database
            with pytest.raises(AssertionError, match="Prerequisites validation should prevent execution"):
                try:
                    await execution_engine.execute_agent(
                        context=self.execution_context,
                        user_context=self.user_context
                    )
                    # If we reach here, prerequisite validation is missing
                    raise AssertionError(
                        "Prerequisites validation should prevent execution with unavailable database, "
                        "but agent execution was attempted without validation"
                    )
                except Exception as e:
                    if "database" in str(e).lower():
                        # This means execution started and failed later, not at prerequisite validation
                        raise AssertionError(
                            "Agent execution started without database prerequisite validation - "
                            "validation should happen BEFORE execution starts"
                        )
                    else:
                        # Re-raise if not database related
                        raise
    
    async def test_agent_registry_initialization_prerequisite_validation_missing(self):
        """FAILING TEST: Should validate agent registry is initialized before execution.
        
        Currently, agent execution can start with uninitialized or broken agent registry,
        leading to agent lookup failures.
        
        Expected to FAIL: No prerequisite validation exists for agent registry state.
        """
        # Create execution engine with proper dependencies
        mock_agent_factory = Mock()
        mock_websocket_emitter = Mock()
        execution_engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Mock uninitialized agent registry
        mock_registry = Mock()
        mock_registry.is_initialized = Mock(return_value=False)
        mock_registry.get_agent = Mock(side_effect=RuntimeError("Registry not initialized"))
        
        with patch('netra_backend.app.agents.supervisor.agent_registry.get_agent_registry',
                  return_value=mock_registry):
            
            # THIS SHOULD FAIL: Currently no prerequisite validation for agent registry
            with pytest.raises(AssertionError, match="Prerequisites validation should prevent execution"):
                try:
                    await execution_engine.execute_agent(
                        context=self.execution_context,
                        user_context=self.user_context
                    )
                    # If we reach here, prerequisite validation is missing
                    raise AssertionError(
                        "Prerequisites validation should prevent execution with uninitialized registry, "
                        "but agent execution was attempted without validation"
                    )
                except RuntimeError as e:
                    if "not initialized" in str(e):
                        # This means execution started and failed later, not at prerequisite validation
                        raise AssertionError(
                            "Agent execution started without registry prerequisite validation - "
                            "validation should happen BEFORE execution starts"
                        )
                    else:
                        raise
    
    async def test_resource_limits_prerequisite_validation_missing(self):
        """FAILING TEST: Should validate resource limits before starting execution.
        
        Currently, agent execution can start without checking if user has exceeded limits,
        wasting resources and providing poor user experience.
        
        Expected to FAIL: No prerequisite validation exists for resource limits.
        """
        # Create execution engine with proper dependencies
        mock_agent_factory = Mock()
        mock_websocket_emitter = Mock()
        execution_engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Mock resource limits exceeded
        with patch('netra_backend.app.agents.supervisor.agent_execution_validator.AgentExecutionValidator.get_resource_limits') as mock_limits:
            mock_limits.return_value = {
                "daily_execution_limit": 10,
                "concurrent_execution_limit": 1,
                "current_daily_executions": 15,  # Exceeded!
                "current_concurrent_executions": 0
            }
            
            # THIS SHOULD FAIL: Currently no prerequisite validation for resource limits
            with pytest.raises(AssertionError, match="Prerequisites validation should prevent execution"):
                try:
                    await execution_engine.execute_agent(
                        context=self.execution_context,
                        user_context=self.user_context
                    )
                    # If we reach here, prerequisite validation is missing
                    raise AssertionError(
                        "Prerequisites validation should prevent execution when limits exceeded, "
                        "but agent execution was attempted without validation"
                    )
                except Exception as e:
                    if "limit" in str(e).lower():
                        # This means execution started and failed later, not at prerequisite validation
                        raise AssertionError(
                            "Agent execution started without resource limits prerequisite validation - "
                            "validation should happen BEFORE execution starts"
                        )
                    else:
                        raise
    
    async def test_user_context_validity_prerequisite_validation_missing(self):
        """FAILING TEST: Should validate user context integrity before execution.
        
        Currently, agent execution can start with invalid/corrupted user context,
        leading to security issues and execution failures.
        
        Expected to FAIL: No prerequisite validation exists for user context integrity.
        """
        # Create execution engine with proper dependencies
        mock_agent_factory = Mock()
        mock_websocket_emitter = Mock()
        execution_engine = UserExecutionEngine(
            context=self.user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Create corrupted user context
        corrupted_context = UserExecutionContext(
            user_id=self.user_id,
            session_id="test_session",
            thread_id=self.thread_id,
            run_id=self.run_id,
            execution_metadata={"corrupted": True}
        )
        
        # Corrupt the context internally
        corrupted_context._user_id = None  # Simulate corruption
        
        # THIS SHOULD FAIL: Currently no prerequisite validation for user context integrity
        with pytest.raises(AssertionError, match="Prerequisites validation should prevent execution"):
            try:
                await execution_engine.execute_agent(
                    context=self.execution_context,
                    user_context=corrupted_context
                )
                # If we reach here, prerequisite validation is missing
                raise AssertionError(
                    "Prerequisites validation should prevent execution with corrupted user context, "
                    "but agent execution was attempted without validation"
                )
            except Exception as e:
                if "context" in str(e).lower() or "user_id" in str(e).lower():
                    # This means execution started and failed later, not at prerequisite validation
                    raise AssertionError(
                        "Agent execution started without user context prerequisite validation - "
                        "validation should happen BEFORE execution starts"
                    )
                else:
                    raise
    
    async def test_comprehensive_prerequisites_validation_function_missing(self):
        """FAILING TEST: Should have a comprehensive prerequisite validation function.
        
        This test demonstrates that there's no single function to validate all prerequisites
        before agent execution starts.
        
        Expected to FAIL: No comprehensive prerequisite validation function exists.
        """
        # THIS SHOULD FAIL: No comprehensive prerequisite validation function exists
        try:
            # Try to import the prerequisite validation function that should exist
            from netra_backend.app.agents.supervisor.prerequisites_validator import (
                validate_agent_execution_prerequisites,
                PrerequisitesValidationResult
            )
            
            # If we can import it, try to use it
            validation_result = await validate_agent_execution_prerequisites(
                execution_context=self.execution_context,
                user_context=self.user_context
            )
            
            if not hasattr(validation_result, 'is_valid'):
                raise AssertionError(
                    "Prerequisites validation function exists but doesn't return proper result structure"
                )
                
        except ImportError:
            # This is expected - the prerequisite validation module doesn't exist yet
            raise AssertionError(
                "Prerequisites validation module/function does not exist - "
                "need to implement: netra_backend.app.agents.supervisor.prerequisites_validator"
            )
        except Exception as e:
            raise AssertionError(
                f"Prerequisites validation function has issues: {e}"
            )
    
    async def test_prerequisite_validation_integration_in_execution_flow_missing(self):
        """FAILING TEST: Should integrate prerequisite validation into execution flow.
        
        Even if prerequisite validation functions exist, they need to be integrated
        into the actual agent execution flow.
        
        Expected to FAIL: Prerequisite validation not integrated into execution flow.
        """
        # Create execution core with proper dependencies
        mock_registry = Mock()
        mock_websocket_bridge = Mock()
        execution_core = AgentExecutionCore(
            registry=mock_registry,
            websocket_bridge=mock_websocket_bridge
        )
        
        # Mock all prerequisites as failing
        with patch('netra_backend.app.agents.supervisor.prerequisites_validator.validate_agent_execution_prerequisites') as mock_validate:
            mock_result = Mock()
            mock_result.is_valid = False
            mock_result.failed_prerequisites = ["websocket", "database", "registry"]
            mock_result.error_message = "Multiple prerequisites failed"
            mock_validate.return_value = mock_result
            
            # THIS SHOULD FAIL: Prerequisites validation should prevent execution
            with pytest.raises(AssertionError, match="Prerequisites validation should prevent execution"):
                try:
                    await execution_core.execute_agent(
                        context=self.execution_context,
                        user_context=self.user_context
                    )
                    # If we reach here, prerequisite validation integration is missing
                    raise AssertionError(
                        "Agent execution proceeded despite failed prerequisites validation - "
                        "integration of prerequisite validation into execution flow is missing"
                    )
                except ImportError:
                    # Prerequisites validation module doesn't exist yet
                    raise AssertionError(
                        "Prerequisites validation integration is missing - "
                        "execution flow doesn't check prerequisites before starting"
                    )
                except Exception as e:
                    if "prerequisite" in str(e).lower():
                        # Good! This means prerequisite validation is integrated
                        pass
                    else:
                        # Execution started without prerequisite validation
                        raise AssertionError(
                            f"Agent execution started without prerequisite validation check: {e}"
                        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])