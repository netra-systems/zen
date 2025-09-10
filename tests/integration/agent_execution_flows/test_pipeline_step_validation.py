"""
Test Pipeline Step Validation Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure pipeline step validation prevents invalid workflow configurations
- Value Impact: Maintains system integrity and prevents agent execution failures
- Strategic Impact: Enables reliable multi-step agent workflows that deliver consistent business value

Tests the pipeline step validation system including dependency checking,
step ordering validation, and configuration validation for agent pipelines.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
from netra_backend.app.agents.supervisor.execution_context import (
    PipelineStep,
    PipelineValidationError,
    DependencyValidationError
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestPipelineStepValidation(BaseIntegrationTest):
    """Integration tests for pipeline step validation."""

    @pytest.mark.integration
    @pytest.mark.pipeline_validation
    async def test_pipeline_dependency_validation(self, real_services_fixture):
        """Test validation of pipeline step dependencies."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_400",
            thread_id="thread_700",
            session_id="session_1000", 
            workspace_id="workspace_300"
        )
        
        pipeline_executor = PipelineExecutor(user_context=user_context)
        
        # Valid pipeline with proper dependencies
        valid_pipeline = [
            PipelineStep(
                step_name="data_collection",
                agent_type="data_helper",
                dependencies=[]
            ),
            PipelineStep(
                step_name="analysis", 
                agent_type="triage",
                dependencies=["data_collection"]
            ),
            PipelineStep(
                step_name="optimization",
                agent_type="apex_optimizer",
                dependencies=["analysis"]
            )
        ]
        
        # Invalid pipeline with missing dependency
        invalid_pipeline = [
            PipelineStep(
                step_name="optimization",
                agent_type="apex_optimizer", 
                dependencies=["missing_step"]  # This step doesn't exist
            ),
            PipelineStep(
                step_name="data_collection",
                agent_type="data_helper",
                dependencies=[]
            )
        ]
        
        # Act & Assert - Valid pipeline should pass
        validation_result = await pipeline_executor.validate_pipeline(valid_pipeline)
        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0
        
        # Invalid pipeline should fail
        with pytest.raises(DependencyValidationError) as exc_info:
            await pipeline_executor.validate_pipeline(invalid_pipeline)
        
        assert "missing_step" in str(exc_info.value)

    @pytest.mark.integration
    @pytest.mark.pipeline_validation
    async def test_circular_dependency_detection(self, real_services_fixture):
        """Test detection of circular dependencies in pipeline steps."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_401",
            thread_id="thread_701",
            session_id="session_1001",
            workspace_id="workspace_301"
        )
        
        pipeline_executor = PipelineExecutor(user_context=user_context)
        
        # Pipeline with circular dependency: A -> B -> C -> A
        circular_pipeline = [
            PipelineStep(
                step_name="step_a",
                agent_type="data_helper",
                dependencies=["step_c"]  # Creates circle
            ),
            PipelineStep(
                step_name="step_b",
                agent_type="triage",
                dependencies=["step_a"]
            ),
            PipelineStep(
                step_name="step_c",
                agent_type="apex_optimizer",
                dependencies=["step_b"]
            )
        ]
        
        # Act & Assert - Should detect circular dependency
        with pytest.raises(PipelineValidationError) as exc_info:
            await pipeline_executor.validate_pipeline(circular_pipeline)
        
        error_message = str(exc_info.value).lower()
        assert "circular" in error_message or "cycle" in error_message

    @pytest.mark.integration
    @pytest.mark.pipeline_validation
    async def test_agent_type_compatibility_validation(self, real_services_fixture):
        """Test validation of agent type compatibility within pipeline steps."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_402",
            thread_id="thread_702",
            session_id="session_1002",
            workspace_id="workspace_302"
        )
        
        pipeline_executor = PipelineExecutor(user_context=user_context)
        
        # Pipeline with incompatible agent types
        incompatible_pipeline = [
            PipelineStep(
                step_name="data_collection",
                agent_type="data_helper",
                dependencies=[],
                output_type="dataset"
            ),
            PipelineStep(
                step_name="image_processing", 
                agent_type="image_analyzer",
                dependencies=["data_collection"],
                required_input_type="image"  # Incompatible with dataset output
            )
        ]
        
        # Compatible pipeline
        compatible_pipeline = [
            PipelineStep(
                step_name="data_collection",
                agent_type="data_helper",
                dependencies=[],
                output_type="dataset"
            ),
            PipelineStep(
                step_name="data_analysis",
                agent_type="triage",
                dependencies=["data_collection"],
                required_input_type="dataset"  # Compatible with dataset output
            )
        ]
        
        # Act & Assert - Incompatible should fail
        with pytest.raises(PipelineValidationError) as exc_info:
            await pipeline_executor.validate_pipeline(incompatible_pipeline)
        
        assert "incompatible" in str(exc_info.value).lower() or "mismatch" in str(exc_info.value).lower()
        
        # Compatible should pass
        validation_result = await pipeline_executor.validate_pipeline(compatible_pipeline)
        assert validation_result.is_valid is True

    @pytest.mark.integration
    @pytest.mark.pipeline_validation
    async def test_pipeline_resource_requirement_validation(self, real_services_fixture):
        """Test validation of resource requirements across pipeline steps."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_403",
            thread_id="thread_703", 
            session_id="session_1003",
            workspace_id="workspace_303"
        )
        
        pipeline_executor = PipelineExecutor(
            user_context=user_context,
            max_memory_mb=1000,  # Limited memory for testing
            max_cpu_cores=2
        )
        
        # Pipeline exceeding resource limits
        resource_heavy_pipeline = [
            PipelineStep(
                step_name="heavy_analysis",
                agent_type="apex_optimizer",
                dependencies=[],
                resource_requirements={
                    "memory_mb": 800,
                    "cpu_cores": 1
                }
            ),
            PipelineStep(
                step_name="parallel_processing",
                agent_type="data_helper", 
                dependencies=["heavy_analysis"],
                resource_requirements={
                    "memory_mb": 600,  # Total would be 1400MB > 1000MB limit
                    "cpu_cores": 2
                }
            )
        ]
        
        # Pipeline within resource limits
        efficient_pipeline = [
            PipelineStep(
                step_name="light_analysis",
                agent_type="triage",
                dependencies=[],
                resource_requirements={
                    "memory_mb": 200,
                    "cpu_cores": 1
                }
            ),
            PipelineStep(
                step_name="simple_processing",
                agent_type="data_helper",
                dependencies=["light_analysis"], 
                resource_requirements={
                    "memory_mb": 300,  # Total 500MB < 1000MB limit
                    "cpu_cores": 1
                }
            )
        ]
        
        # Act & Assert - Resource heavy should fail
        with pytest.raises(PipelineValidationError) as exc_info:
            await pipeline_executor.validate_pipeline(resource_heavy_pipeline)
        
        assert "resource" in str(exc_info.value).lower() or "memory" in str(exc_info.value).lower()
        
        # Efficient should pass
        validation_result = await pipeline_executor.validate_pipeline(efficient_pipeline)
        assert validation_result.is_valid is True

    @pytest.mark.integration
    @pytest.mark.pipeline_validation 
    async def test_pipeline_execution_order_validation(self, real_services_fixture):
        """Test validation of pipeline execution order and topological sorting."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_404",
            thread_id="thread_704",
            session_id="session_1004", 
            workspace_id="workspace_304"
        )
        
        pipeline_executor = PipelineExecutor(user_context=user_context)
        
        # Unordered pipeline that needs sorting
        unordered_pipeline = [
            PipelineStep(
                step_name="final_report",
                agent_type="reporting",
                dependencies=["optimization", "validation"]
            ),
            PipelineStep(
                step_name="data_collection", 
                agent_type="data_helper",
                dependencies=[]
            ),
            PipelineStep(
                step_name="optimization",
                agent_type="apex_optimizer",
                dependencies=["analysis"]
            ),
            PipelineStep(
                step_name="validation",
                agent_type="triage",
                dependencies=["optimization"]
            ),
            PipelineStep(
                step_name="analysis",
                agent_type="triage",
                dependencies=["data_collection"]
            )
        ]
        
        # Act - Validate and get execution order
        validation_result = await pipeline_executor.validate_pipeline(unordered_pipeline)
        assert validation_result.is_valid is True
        
        # Get topologically sorted order
        execution_order = await pipeline_executor.get_execution_order(unordered_pipeline)
        
        # Assert - Verify correct execution order
        step_names = [step.step_name for step in execution_order]
        
        # data_collection should come first
        assert step_names.index("data_collection") < step_names.index("analysis")
        # analysis should come before optimization
        assert step_names.index("analysis") < step_names.index("optimization") 
        # optimization should come before validation
        assert step_names.index("optimization") < step_names.index("validation")
        # both optimization and validation should come before final_report
        assert step_names.index("optimization") < step_names.index("final_report")
        assert step_names.index("validation") < step_names.index("final_report")

    @pytest.mark.integration
    @pytest.mark.pipeline_validation
    async def test_conditional_pipeline_branch_validation(self, real_services_fixture):
        """Test validation of conditional pipeline branches and decision points."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="test_user_405",
            thread_id="thread_705",
            session_id="session_1005",
            workspace_id="workspace_305"
        )
        
        pipeline_executor = PipelineExecutor(user_context=user_context)
        
        # Conditional pipeline with valid branches
        conditional_pipeline = [
            PipelineStep(
                step_name="initial_triage",
                agent_type="triage",
                dependencies=[]
            ),
            PipelineStep(
                step_name="complex_analysis", 
                agent_type="apex_optimizer",
                dependencies=["initial_triage"],
                condition="priority == 'high'"
            ),
            PipelineStep(
                step_name="simple_response",
                agent_type="data_helper",
                dependencies=["initial_triage"],
                condition="priority == 'low'"
            ),
            PipelineStep(
                step_name="final_report",
                agent_type="reporting",
                dependencies=["complex_analysis", "simple_response"],
                dependency_type="any"  # Only needs one of the branches
            )
        ]
        
        # Invalid conditional pipeline (missing decision step)
        invalid_conditional_pipeline = [
            PipelineStep(
                step_name="complex_analysis",
                agent_type="apex_optimizer", 
                dependencies=[],
                condition="priority == 'high'"  # Condition without decision step
            )
        ]
        
        # Act & Assert - Valid conditional pipeline should pass
        validation_result = await pipeline_executor.validate_pipeline(conditional_pipeline)
        assert validation_result.is_valid is True
        
        # Invalid should fail
        with pytest.raises(PipelineValidationError) as exc_info:
            await pipeline_executor.validate_pipeline(invalid_conditional_pipeline)
        
        assert "condition" in str(exc_info.value).lower() or "decision" in str(exc_info.value).lower()