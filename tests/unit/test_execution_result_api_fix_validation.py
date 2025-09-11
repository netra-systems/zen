"""Fix validation test for ExecutionResult API Issue #261.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Reliability
- Value Impact: Validates P0 CRITICAL fix enables $500K+ ARR Golden Path validation  
- Strategic Impact: Ensures SSOT ExecutionResult API compliance restores business value testing

This test suite validates that the ExecutionResult API fix correctly resolves Issue #261
by ensuring SupervisorAgent.execute() returns SSOT-compliant format that Golden Path tests expect.
"""

import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core imports for validation
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
from netra_backend.app.llm.llm_manager import LLMManager


class TestExecutionResultAPIFixValidation(SSotAsyncTestCase):
    """Validate that the ExecutionResult API fix resolves Issue #261 correctly."""

    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        # Create mock LLM manager
        self.mock_llm_manager = MagicMock()
        self.mock_llm_manager.get_default_client = MagicMock()
        self.mock_llm_manager.get_default_client.return_value = MagicMock()
        
        # Test identifiers
        self.test_user_id = str(uuid.uuid4())
        self.test_thread_id = str(uuid.uuid4())
        self.test_run_id = str(uuid.uuid4())
        self.test_request_id = str(uuid.uuid4())

    async def test_supervisor_agent_returns_ssot_format_after_fix(self):
        """FIXED BEHAVIOR: Validate SupervisorAgent returns SSOT ExecutionResult format.
        
        This test should PASS after the API fix is implemented, demonstrating
        that the ExecutionResult API now complies with SSOT format expected by Golden Path tests.
        """
        
        # Setup supervisor agent
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            db_session=MagicMock(),
            agent_context={
                "message": "Test message for SSOT format validation",
                "request_type": "optimization_analysis"
            }
        )
        
        # Mock successful execution to test the happy path
        with patch('netra_backend.app.agents.supervisor_ssot.UserExecutionEngine') as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine_class.return_value = mock_engine
            
            mock_execution_result = AgentExecutionResult(
                success=True,
                agent_name="supervisor_orchestration",
                duration=1.5,
                metadata={
                    'user_id': self.test_user_id,
                    'execution_successful': True,
                    'agents_executed': ['triage', 'data_helper', 'optimizer']
                },
                data={'optimization_recommendations': ['scale_cpu', 'reduce_memory']}
            )
            mock_engine.execute_agent_pipeline.return_value = mock_execution_result
            mock_engine.cleanup.return_value = None
            
            # Execute supervisor agent
            result = await supervisor.execute(context=user_context)
        
        print(f"\n=== SSOT FORMAT VALIDATION ===")
        print(f"Result after fix: {result}")
        print(f"Result keys: {list(result.keys())}")
        
        # CRITICAL: These are the exact assertions that Golden Path tests require
        # test_agent_orchestration_execution_comprehensive.py:304-305
        self.assertIn("status", result, "Golden Path requirement: 'status' field must be present")
        self.assertEqual(result["status"], "completed", "Golden Path requirement: status must be 'completed'")
        
        # Additional SSOT format requirements
        self.assertIn("data", result, "SSOT requirement: 'data' field must contain execution results")
        self.assertIn("request_id", result, "SSOT requirement: 'request_id' field must be present")
        
        # Validate status uses proper ExecutionStatus enum value
        valid_statuses = [status.value for status in ExecutionStatus]
        self.assertIn(result["status"], valid_statuses, "Status must be valid ExecutionStatus enum value")
        
        # Validate request_id propagation from UserExecutionContext
        self.assertEqual(result["request_id"], user_context.request_id, 
                        "Request ID must match UserExecutionContext.request_id")
        
        # Validate data field structure
        self.assertIsInstance(result["data"], dict, "Data field must be a dictionary")
        
        # Validate no legacy non-SSOT fields remain
        self.assertNotIn("supervisor_result", result, "Legacy 'supervisor_result' field should be removed")
        self.assertNotIn("results", result, "Legacy 'results' field should be moved to 'data'")
        
        print("✅ SSOT ExecutionResult format validation PASSED - API fix is working correctly!")

    async def test_failed_execution_returns_ssot_format(self):
        """Validate that failed executions also return SSOT format."""
        
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            db_session=MagicMock()
        )
        
        # Mock failed execution
        with patch('netra_backend.app.agents.supervisor_ssot.UserExecutionEngine') as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine_class.return_value = mock_engine
            
            mock_execution_result = AgentExecutionResult(
                success=False,
                error="Test execution failure for validation",
                duration=0.5,
                metadata={'error_type': 'validation_error'}
            )
            mock_engine.execute_agent_pipeline.return_value = mock_execution_result
            mock_engine.cleanup.return_value = None
            
            # Execute
            result = await supervisor.execute(context=user_context)
        
        # Failed executions should also follow SSOT format
        self.assertIn("status", result)
        self.assertIn("data", result)
        self.assertIn("request_id", result)
        
        # Status should indicate failure
        self.assertEqual(result["status"], ExecutionStatus.FAILED.value)
        
        # Error information should be in data field
        self.assertIn("error", result["data"])
        
        print("✅ Failed execution SSOT format validation PASSED")

    async def test_golden_path_compatibility_after_fix(self):
        """Validate specific Golden Path test compatibility after API fix."""
        
        # This replicates the exact setup from Golden Path test
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            db_session=MagicMock(),
            agent_context={
                "message": "Analyze my AI costs and suggest optimizations",
                "request_type": "optimization_analysis"
            }
        )
        
        # Mock WebSocket bridge like Golden Path test
        mock_websocket_bridge = AsyncMock()
        supervisor.websocket_bridge = mock_websocket_bridge
        
        with patch('netra_backend.app.agents.supervisor_ssot.UserExecutionEngine') as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine_class.return_value = mock_engine
            
            mock_execution_result = AgentExecutionResult(
                success=True,
                agent_name="supervisor_orchestration",
                duration=2.0,
                metadata={'orchestration_completed': True}
            )
            mock_engine.execute_agent_pipeline.return_value = mock_execution_result
            mock_engine.cleanup.return_value = None
            
            # Execute with stream_updates like Golden Path test
            result = await supervisor.execute(context=user_context, stream_updates=True)
        
        # These are the EXACT assertions from Golden Path test that were failing
        # test_agent_orchestration_execution_comprehensive.py:302-305
        self.assertIsNotNone(result)
        self.assertIn("status", result)  # Line 304: CRITICAL ASSERTION
        self.assertEqual(result["status"], "completed")  # Line 305: CRITICAL ASSERTION
        
        # Verify WebSocket events were triggered (Golden Path requirement)
        mock_websocket_bridge.notify_agent_started.assert_called()
        mock_websocket_bridge.notify_agent_completed.assert_called()
        
        print("✅ Golden Path test compatibility validation PASSED")

    async def test_execution_status_enum_value_correctness(self):
        """Validate ExecutionStatus enum values are used correctly in API responses."""
        
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            db_session=MagicMock()
        )
        
        # Test different execution outcomes
        test_cases = [
            (True, ExecutionStatus.COMPLETED),
            (False, ExecutionStatus.FAILED)
        ]
        
        for success, expected_status in test_cases:
            with patch('netra_backend.app.agents.supervisor_ssot.UserExecutionEngine') as mock_engine_class:
                mock_engine = AsyncMock()
                mock_engine_class.return_value = mock_engine
                
                mock_execution_result = AgentExecutionResult(
                    success=success,
                    duration=1.0,
                    error=None if success else "Test error"
                )
                mock_engine.execute_agent_pipeline.return_value = mock_execution_result
                mock_engine.cleanup.return_value = None
                
                result = await supervisor.execute(context=user_context)
            
            # Validate correct ExecutionStatus enum value is used
            self.assertEqual(result["status"], expected_status.value)
            
        print("✅ ExecutionStatus enum value correctness validation PASSED")

    async def test_data_field_contains_legacy_information(self):
        """Validate that 'data' field contains all necessary execution information."""
        
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            db_session=MagicMock()
        )
        
        with patch('netra_backend.app.agents.supervisor_ssot.UserExecutionEngine') as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine_class.return_value = mock_engine
            
            mock_execution_result = AgentExecutionResult(
                success=True,
                agent_name="supervisor_orchestration",
                duration=1.5,
                metadata={'test_metadata': 'value'},
                data={'execution_data': 'test_data'}
            )
            mock_engine.execute_agent_pipeline.return_value = mock_execution_result
            mock_engine.cleanup.return_value = None
            
            result = await supervisor.execute(context=user_context)
        
        # Validate data field contains all execution information
        data = result["data"]
        
        # Should contain supervisor execution results
        self.assertIn("supervisor_result", data)
        self.assertEqual(data["supervisor_result"], "completed")
        
        # Should contain orchestration status
        self.assertIn("orchestration_successful", data)
        
        # Should contain user isolation verification
        self.assertIn("user_isolation_verified", data)
        
        # Should contain execution results/data
        self.assertIn("execution_results", data)
        
        # Should contain user context information
        self.assertIn("user_id", data)
        self.assertIn("run_id", data)
        
        print("✅ Data field structure validation PASSED")

    async def test_backward_compatibility_maintained(self):
        """Validate that legacy access patterns can still work with adaptation."""
        
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            db_session=MagicMock()
        )
        
        with patch('netra_backend.app.agents.supervisor_ssot.UserExecutionEngine') as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine_class.return_value = mock_engine
            
            mock_execution_result = AgentExecutionResult(success=True, duration=1.0)
            mock_engine.execute_agent_pipeline.return_value = mock_execution_result
            mock_engine.cleanup.return_value = None
            
            result = await supervisor.execute(context=user_context)
        
        # Legacy code that might access supervisor_result can still work
        # through the data field
        legacy_supervisor_result = result["data"]["supervisor_result"]
        self.assertEqual(legacy_supervisor_result, "completed")
        
        # Status information is now in the standard location
        standard_status = result["status"]
        self.assertEqual(standard_status, "completed")
        
        print("✅ Backward compatibility validation PASSED")

    async def test_request_id_propagation_correctness(self):
        """Validate that request_id is correctly propagated from UserExecutionContext."""
        
        supervisor = SupervisorAgent(llm_manager=self.mock_llm_manager)
        
        # Test with specific request_id
        test_request_id = "test_request_123456"
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=test_request_id,  # Specific test value
            db_session=MagicMock()
        )
        
        with patch('netra_backend.app.agents.supervisor_ssot.UserExecutionEngine') as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine_class.return_value = mock_engine
            
            mock_execution_result = AgentExecutionResult(success=True, duration=1.0)
            mock_engine.execute_agent_pipeline.return_value = mock_execution_result
            mock_engine.cleanup.return_value = None
            
            result = await supervisor.execute(context=user_context)
        
        # Validate exact request_id propagation
        self.assertEqual(result["request_id"], test_request_id)
        
        print("✅ Request ID propagation validation PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])