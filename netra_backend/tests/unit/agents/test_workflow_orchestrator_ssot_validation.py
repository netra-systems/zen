"""Test WorkflowOrchestrator SSOT Compliance - P0 Failing Tests.

This test module validates that WorkflowOrchestrator ONLY accepts the SSOT 
UserExecutionEngine and REJECTS deprecated execution engines.

EXPECTED BEHAVIOR (BEFORE REMEDIATION):
- These tests should FAIL because WorkflowOrchestrator currently accepts any execution engine
- After remediation: Tests should PASS when WorkflowOrchestrator enforces SSOT compliance

TEST PURPOSE: Prove SSOT violation exists and validate fix effectiveness.

Business Value: Prevents user isolation vulnerabilities caused by deprecated engines.
"""

import pytest
import asyncio
import unittest
from unittest.mock import Mock, MagicMock
from typing import TYPE_CHECKING

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine


class TestWorkflowOrchestratorSSotValidation(SSotBaseTestCase, unittest.TestCase):
    """Test that WorkflowOrchestrator enforces SSOT UserExecutionEngine compliance.
    
    These tests should FAIL initially, proving the SSOT violation exists.
    After remediation, they should PASS to validate the fix.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        # Mock dependencies (real agents not needed for interface validation)
        self.mock_agent_registry = Mock()
        self.mock_websocket_manager = Mock()
        self.mock_user_context = Mock()
        
        # Create valid SSOT UserExecutionEngine for positive tests
        self.valid_user_engine = Mock(spec=UserExecutionEngine)
        self.valid_user_engine.__class__.__name__ = "UserExecutionEngine"
        
    def test_workflow_orchestrator_accepts_user_execution_engine(self):
        """Test that WorkflowOrchestrator accepts SSOT UserExecutionEngine.
        
        This test should PASS even before remediation.
        """
        # Should not raise any exception
        orchestrator = WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=self.valid_user_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=self.mock_user_context
        )
        
        assert orchestrator.execution_engine == self.valid_user_engine
        assert orchestrator.agent_registry == self.mock_agent_registry
        
    def test_workflow_orchestrator_rejects_deprecated_execution_engine(self):
        """Test that WorkflowOrchestrator REJECTS deprecated ExecutionEngine.
        
        EXPECTED: This test should FAIL before remediation because WorkflowOrchestrator
        currently accepts any execution engine type without validation.
        
        AFTER REMEDIATION: Should PASS when proper validation is added.
        """
        # Create deprecated ExecutionEngine mock
        deprecated_engine = Mock()
        deprecated_engine.__class__.__name__ = "ExecutionEngine"
        
        # This should raise an exception after remediation
        with pytest.raises(ValueError, match="deprecated.*ExecutionEngine.*not allowed"):
            WorkflowOrchestrator(
                agent_registry=self.mock_agent_registry,
                execution_engine=deprecated_engine,
                websocket_manager=self.mock_websocket_manager,
                user_context=self.mock_user_context
            )
            
    def test_workflow_orchestrator_rejects_consolidated_execution_engine(self):
        """Test that WorkflowOrchestrator REJECTS deprecated ExecutionEngineConsolidated.
        
        EXPECTED: This test should FAIL before remediation.
        AFTER REMEDIATION: Should PASS when proper validation is added.
        """
        # Create deprecated ExecutionEngineConsolidated mock
        deprecated_consolidated = Mock()
        deprecated_consolidated.__class__.__name__ = "ExecutionEngineConsolidated"
        
        # This should raise an exception after remediation
        with pytest.raises(ValueError, match="deprecated.*ExecutionEngineConsolidated.*not allowed"):
            WorkflowOrchestrator(
                agent_registry=self.mock_agent_registry,
                execution_engine=deprecated_consolidated,
                websocket_manager=self.mock_websocket_manager,
                user_context=self.mock_user_context
            )
            
    def test_workflow_orchestrator_rejects_generic_execution_engine(self):
        """Test that WorkflowOrchestrator REJECTS generic execution engines.
        
        EXPECTED: This test should FAIL before remediation.
        AFTER REMEDIATION: Should PASS when proper validation is added.
        """
        # Create generic execution engine mock (not UserExecutionEngine)
        generic_engine = Mock()
        generic_engine.__class__.__name__ = "SomeOtherExecutionEngine"
        
        # This should raise an exception after remediation
        with pytest.raises(ValueError, match="Only UserExecutionEngine.*allowed.*SSOT"):
            WorkflowOrchestrator(
                agent_registry=self.mock_agent_registry,
                execution_engine=generic_engine,
                websocket_manager=self.mock_websocket_manager,
                user_context=self.mock_user_context
            )
            
    def test_workflow_orchestrator_validates_execution_engine_interface(self):
        """Test that WorkflowOrchestrator validates execution engine interface compliance.
        
        EXPECTED: This test should FAIL before remediation.
        AFTER REMEDIATION: Should PASS when interface validation is added.
        """
        # Create engine that claims to be UserExecutionEngine but missing required methods
        fake_user_engine = Mock()
        fake_user_engine.__class__.__name__ = "UserExecutionEngine"
        
        # Remove a critical method to make interface invalid
        del fake_user_engine.execute_agent
        
        # This should raise an exception after remediation
        with pytest.raises(ValueError, match="UserExecutionEngine.*missing required.*execute_agent"):
            WorkflowOrchestrator(
                agent_registry=self.mock_agent_registry,
                execution_engine=fake_user_engine,
                websocket_manager=self.mock_websocket_manager,
                user_context=self.mock_user_context
            )
            
    def test_workflow_orchestrator_logs_ssot_compliance_warning(self):
        """Test that WorkflowOrchestrator logs SSOT compliance status.
        
        EXPECTED: This test should FAIL before remediation (no logging).
        AFTER REMEDIATION: Should PASS when compliance logging is added.
        """
        with self.assertLogs("netra_backend.app.agents.supervisor.workflow_orchestrator", level="INFO") as log:
            WorkflowOrchestrator(
                agent_registry=self.mock_agent_registry,
                execution_engine=self.valid_user_engine,
                websocket_manager=self.mock_websocket_manager,
                user_context=self.mock_user_context
            )
            
        # Should log SSOT compliance validation
        self.assertIn("SSOT UserExecutionEngine compliance validated", log.output[0])
        
    def test_workflow_orchestrator_provides_helpful_migration_message(self):
        """Test that WorkflowOrchestrator provides helpful migration guidance.
        
        EXPECTED: This test should FAIL before remediation.
        AFTER REMEDIATION: Should PASS when helpful error messages are added.
        """
        deprecated_engine = Mock()
        deprecated_engine.__class__.__name__ = "ExecutionEngine"
        
        with pytest.raises(ValueError) as exc_info:
            WorkflowOrchestrator(
                agent_registry=self.mock_agent_registry,
                execution_engine=deprecated_engine,
                websocket_manager=self.mock_websocket_manager,
                user_context=self.mock_user_context
            )
            
        error_message = str(exc_info.value)
        self.assertIn("UserExecutionEngine", error_message)
        self.assertIn("migration", error_message.lower())
        self.assertIn("user_execution_engine.py", error_message)


class TestWorkflowOrchestratorSSotIntegration(SSotBaseTestCase, unittest.TestCase):
    """Integration tests for WorkflowOrchestrator SSOT compliance with real dependencies."""
    
    def test_workflow_orchestrator_with_real_user_execution_engine_interface(self):
        """Test WorkflowOrchestrator works with real UserExecutionEngine interface.
        
        This validates the interface contract works correctly.
        """
        # This would use a real UserExecutionEngine instance in integration test
        # For now, mock with proper interface
        real_user_engine = Mock(spec=UserExecutionEngine)
        real_user_engine.__class__.__name__ = "UserExecutionEngine"
        
        # Add required methods
        real_user_engine.execute_agent = Mock()
        real_user_engine.cleanup = Mock() 
        real_user_engine.get_state = Mock()
        
        orchestrator = WorkflowOrchestrator(
            agent_registry=Mock(),
            execution_engine=real_user_engine,
            websocket_manager=Mock(),
            user_context=Mock()
        )
        
        # Verify the engine is properly set and interface is valid
        assert orchestrator.execution_engine == real_user_engine
        assert hasattr(orchestrator.execution_engine, 'execute_agent')
        assert hasattr(orchestrator.execution_engine, 'cleanup')
        
    def test_workflow_orchestrator_ssot_validation_runtime_check(self):
        """Test that SSOT validation occurs at runtime during execution.
        
        EXPECTED: This test should FAIL before remediation.
        AFTER REMEDIATION: Should PASS when runtime validation is added.
        """
        # Start with valid engine
        valid_engine = Mock(spec=UserExecutionEngine)
        valid_engine.__class__.__name__ = "UserExecutionEngine"
        valid_engine.execute_agent = Mock()
        
        orchestrator = WorkflowOrchestrator(
            agent_registry=Mock(),
            execution_engine=valid_engine,
            websocket_manager=Mock(),
            user_context=Mock()
        )
        
        # Simulate engine being swapped to deprecated type at runtime (security issue)
        deprecated_engine = Mock()
        deprecated_engine.__class__.__name__ = "ExecutionEngine"
        orchestrator.execution_engine = deprecated_engine
        
        # Runtime validation should catch this and raise exception
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.agents.state import DeepAgentState
        
        mock_context = Mock(spec=ExecutionContext)
        mock_state = Mock(spec=DeepAgentState)
        
        with pytest.raises(ValueError, match="Runtime SSOT validation failed.*deprecated engine detected"):
            # This should trigger runtime validation that catches the engine swap
            asyncio.run(orchestrator._execute_workflow_step(mock_context, Mock()))