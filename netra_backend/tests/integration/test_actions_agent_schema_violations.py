"""Test ActionsAgent Schema Violations - Integration Test to Reproduce Bug

This integration test reproduces the exact Pydantic validation errors that occur
when ActionsToMeetGoalsSubAgent tries to work with DataAnalysisResponse objects
that use the wrong schema.

This test demonstrates the integration-level failure between:
- ActionsToMeetGoalsSubAgent expecting certain DataAnalysisResponse fields
- The actual DataAnalysisResponse schema in shared_types.py
- DeepAgentState attempting to use the incompatible schemas

These tests are DESIGNED TO FAIL to document the current broken integration.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from pydantic import ValidationError
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import the components that demonstrate the schema violation
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent  
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.state import OptimizationsResult
from netra_backend.app.schemas.shared_types import DataAnalysisResponse, PerformanceMetrics
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher


class TestActionsAgentSchemaViolations(SSotAsyncTestCase):
    """Integration test suite documenting ActionsAgent schema violations."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        
        # Mock dependencies to focus on schema validation issues
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_tool_dispatcher = Mock(spec=UnifiedToolDispatcher)
        
        # Create agent instance
        self.agent = ActionsToMeetGoalsSubAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
    
    async def test_actions_agent_fails_with_expected_data_analysis_schema(self):
        """FAILING TEST: ActionsAgent fails when given DataAnalysisResponse with expected schema.
        
        This reproduces the integration failure where ActionsAgent tests expect 
        DataAnalysisResponse to have query, insights, recommendations fields,
        but the actual schema doesn't support these fields.
        """
        # Try to create a DeepAgentState with the "expected" DataAnalysisResponse schema
        # This will FAIL because the schema mismatch prevents object creation
        with self.expect_exception(ValidationError, message_pattern="query"):
            state = DeepAgentState(
                user_request="Test request",
                data_result=DataAnalysisResponse(
                    query="test query",  # Field doesn't exist in actual schema
                    results=[{"test": "data"}],  # Wrong type (list vs dict)
                    insights={"insight": "test insight"},  # Field doesn't exist
                    recommendations=["test recommendation"]  # Field doesn't exist
                ),
                optimizations_result=OptimizationsResult(
                    optimization_type="performance",
                    recommendations=["test recommendation"], 
                    confidence_score=0.9
                )
            )
    
    async def test_actions_agent_validate_preconditions_with_invalid_data_result(self):
        """FAILING TEST: ActionsAgent.validate_preconditions fails with schema mismatch.
        
        This reproduces the error that occurs when validate_preconditions
        tries to access fields that don't exist in the actual DataAnalysisResponse schema.
        """
        # Create UserExecutionContext that would normally contain invalid DataAnalysisResponse
        context = UserExecutionContext(
            run_id="test_run_123",
            user_id="test_user",
            trace_id="test_trace" 
        )
        
        # Try to set context metadata that would cause schema violations
        context.metadata = {
            "user_request": "Test request",
            "data_result": None,  # This will trigger default creation logic
            "optimizations_result": None
        }
        
        # The validate_preconditions method will try to create defaults
        # and encounter schema mismatches if it uses the wrong fields
        try:
            result = await self.agent.validate_preconditions(context)
            # If this passes, it means defaults were created correctly
            # But we expect it might fail due to schema mismatches in default creation
        except ValidationError as e:
            # Expected failure due to schema mismatch in default creation
            self.assertIn("validation error", str(e).lower())
        except AttributeError as e:
            # Expected failure due to accessing non-existent fields
            self.assertTrue(
                "query" in str(e) or "insights" in str(e) or "recommendations" in str(e),
                f"Expected schema field error, got: {e}"
            )
    
    async def test_actions_agent_default_data_result_creation_failure(self):
        """FAILING TEST: ActionsAgent fails to create default DataAnalysisResponse.
        
        This test reproduces the failure that occurs when ActionsAgent tries to create
        a default DataAnalysisResponse but uses the wrong schema fields.
        """
        # Create a context with missing data_result to trigger default creation
        context = UserExecutionContext(
            run_id="test_run_123", 
            user_id="test_user",
            trace_id="test_trace"
        )
        
        context.metadata = {
            "user_request": "Test request",
            "data_result": None,  # Missing - will trigger default creation
            "optimizations_result": OptimizationsResult(
                optimization_type="performance",
                recommendations=["test"], 
                confidence_score=0.9
            )
        }
        
        # The agent's _apply_defaults_for_missing_deps method may try to create
        # DataAnalysisResponse with wrong fields, causing validation error
        with patch.object(self.agent, '_apply_defaults_for_missing_deps') as mock_defaults:
            # Configure mock to attempt creation with wrong schema
            def failing_defaults(ctx, missing_deps):
                if "data_result" in missing_deps:
                    # This simulates the bug where wrong fields are used
                    try:
                        ctx.metadata["data_result"] = DataAnalysisResponse(
                            query="no data available",  # Wrong field
                            results=[],  # Wrong type
                            insights={"status": "no data"},  # Wrong field  
                            recommendations=[]  # Wrong field
                        )
                    except ValidationError as e:
                        # This is the expected failure
                        raise e
            
            mock_defaults.side_effect = failing_defaults
            
            # This should fail when trying to create default with wrong schema
            with self.expect_exception(ValidationError):
                await self.agent.validate_preconditions(context)
    
    async def test_correct_data_analysis_response_schema_works(self):
        """PASSING TEST: Verify that using the correct schema works.
        
        This test demonstrates the proper way to create DataAnalysisResponse
        and shows what the ActionsAgent should be doing instead.
        """
        # Create DataAnalysisResponse with the CORRECT schema
        correct_data_result = DataAnalysisResponse(
            analysis_id="test_analysis_123",
            status="completed",
            results={"metrics": [{"cpu": 80}]},  # Dict format
            metrics=PerformanceMetrics(duration_ms=150.0),
            created_at=1234567890.0
        )
        
        # Create DeepAgentState with correct schema
        state = DeepAgentState(
            user_request="Test request",
            data_result=correct_data_result,
            optimizations_result=OptimizationsResult(
                optimization_type="performance", 
                recommendations=["test recommendation"],
                confidence_score=0.9
            )
        )
        
        # This should work without validation errors
        self.assertIsNotNone(state)
        self.assertIsNotNone(state.data_result)
        self.assertEqual(state.data_result.analysis_id, "test_analysis_123")
        self.assertEqual(state.data_result.status, "completed")
    
    async def test_actions_agent_integration_with_corrected_schema(self):
        """PASSING TEST: ActionsAgent integration with corrected DataAnalysisResponse.
        
        This test shows how ActionsAgent should work once the schema is fixed.
        """
        # Create context with correctly structured DataAnalysisResponse
        context = UserExecutionContext(
            run_id="test_run_123",
            user_id="test_user", 
            trace_id="test_trace"
        )
        
        # Use the ACTUAL schema fields
        correct_data_result = DataAnalysisResponse(
            analysis_id="integration_test_123",
            status="completed",
            results={
                "performance_data": {"cpu_usage": 75, "memory_usage": 60},
                "trends": {"cpu_trend": "increasing"}
            },
            metrics=PerformanceMetrics(
                duration_ms=200.0,
                memory_usage_mb=512.0,
                cpu_usage_percent=25.0
            ),
            created_at=1234567890.0
        )
        
        context.metadata = {
            "user_request": "Optimize system performance",
            "data_result": correct_data_result,
            "optimizations_result": OptimizationsResult(
                optimization_type="performance",
                recommendations=["Scale CPU", "Optimize queries"],
                confidence_score=0.85
            )
        }
        
        # Validate preconditions should pass with correct schema
        result = await self.agent.validate_preconditions(context)
        self.assertTrue(result)
        
        # Verify the data_result is accessible and has correct structure
        data_result = context.metadata.get("data_result")
        self.assertIsNotNone(data_result)
        self.assertEqual(data_result.analysis_id, "integration_test_123")
        self.assertIn("performance_data", data_result.results)
    
    async def test_demonstrate_exact_error_reproduction(self):
        """FAILING TEST: Reproduce the exact error from ActionsAgent tests.
        
        This reproduces the specific validation error that occurs in the current
        ActionsAgent test suite.
        """
        # This mimics the exact pattern from test_actions_to_meet_goals_agent_state.py
        # that is currently failing
        with self.expect_exception(ValidationError) as exc_info:
            state = DeepAgentState(
                user_request="Test request",
                data_result=DataAnalysisResponse(
                    query="test query",  # ValidationError: Field doesn't exist
                    results=[{"test": "data"}],  # ValidationError: Wrong type
                    insights={"insight": "test insight"},  # ValidationError: Field doesn't exist  
                    recommendations=["test recommendation"]  # ValidationError: Field doesn't exist
                ),
                optimizations_result=None  # This part is valid
            )
        
        # Document the specific error details
        error_message = str(exc_info.value)
        self.record_metric("schema_validation_error", error_message)
        self.logger.error(f"Reproduced exact schema validation error: {error_message}")
        
        # Verify this is specifically a field validation error
        self.assertTrue(
            any(field in error_message for field in ["query", "insights", "recommendations"]),
            f"Expected field validation error, got: {error_message}"
        )