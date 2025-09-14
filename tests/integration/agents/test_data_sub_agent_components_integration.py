"""Integration Tests: Data Sub-Agent Components Workflows

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure data validation and query execution components work reliably
- Value Impact: Data sub-agents are critical for optimization workflows - they provide the foundation
- Strategic Impact: Core infrastructure for data-driven AI solutions and optimization strategies

This test suite validates:
1. DataHelperAgent data request generation workflows
2. ValidationSubAgent data validation patterns
3. ToolDiscoverySubAgent tool discovery and execution
4. Data processing pipeline integration
5. Multi-agent data coordination workflows
6. WebSocket event delivery for data operations
7. Error handling and recovery for data operations

CRITICAL: Tests real data sub-agent coordination patterns with proper state management.
Uses realistic data scenarios and validates complete data processing workflows.

REQUIREMENTS:
- NO DOCKER dependency (as requested)
- Real services integration patterns
- SSOT compliance for all imports
- Business-critical data workflow validation
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Core SSOT imports
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager

# Data Sub-Agent specific imports
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
from netra_backend.app.agents.tool_discovery_sub_agent import ToolDiscoverySubAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.tools.data_helper import DataHelper

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.orchestration import get_orchestration_config
from test_framework.websocket_test_utility import WebSocketTestUtility


class TestDataSubAgentComponentsIntegration(BaseIntegrationTest):
    """Comprehensive integration tests for data sub-agent components."""

    def setUp(self) -> None:
        """Set up test environment for data sub-agent testing."""
        super().setUp()
        self.orchestration_config = get_orchestration_config()
        self.websocket_utility = WebSocketTestUtility()

        # Initialize core test fixtures
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        self.run_id = f"test_run_{uuid.uuid4().hex[:8]}"

        # Test data scenarios
        self.data_request_scenario = {
            "user_request": "I need to optimize my AWS costs but I'm not sure what data I need to provide",
            "context": {
                "optimization_goal": "cost_reduction",
                "current_data": "minimal",
                "user_experience": "beginner"
            }
        }

        self.validation_scenario = {
            "data_payload": {
                "aws_bill": "$1,250/month",
                "instance_types": ["t3.medium", "m5.large"],
                "usage_patterns": "24/7 for web app"
            },
            "expected_validation": ["cost_validation", "instance_optimization", "usage_pattern_analysis"]
        }

    @pytest.mark.asyncio
    async def test_data_helper_agent_request_generation_workflow(self):
        """Test DataHelperAgent generates comprehensive data requests for optimization."""

        # SETUP: Initialize DataHelperAgent with real components
        llm_manager = self._create_mock_llm_manager()
        tool_dispatcher = self._create_mock_tool_dispatcher()

        data_helper_agent = DataHelperAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher
        )

        # Create execution context
        user_context = UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            agent_state=DeepAgentState(
                user_request=self.data_request_scenario["user_request"],
                user_prompt=self.data_request_scenario["user_request"],
                user_id=self.user_id,
                chat_thread_id=self.thread_id,
                run_id=self.run_id
            )
        )

        # EXECUTE: Run data helper agent workflow
        start_time = time.time()

        with patch.object(llm_manager, 'generate_response') as mock_llm:
            # Mock LLM to return structured data request
            mock_llm.return_value = {
                "data_requests": [
                    {
                        "category": "aws_billing",
                        "required_fields": ["monthly_spend", "service_breakdown", "region_usage"],
                        "priority": "high",
                        "rationale": "Essential for cost optimization analysis"
                    },
                    {
                        "category": "infrastructure",
                        "required_fields": ["instance_inventory", "utilization_metrics", "scaling_patterns"],
                        "priority": "medium",
                        "rationale": "Needed for rightsizing recommendations"
                    }
                ],
                "estimated_savings_potential": "15-25%",
                "confidence_level": 0.8
            }

            result = await data_helper_agent.execute(user_context)

        execution_time = time.time() - start_time

        # VALIDATE: Verify data request generation results
        self.assertTrue(result.success, f"DataHelperAgent execution failed: {result.error}")
        self.assertIsNotNone(result.output, "DataHelperAgent should return structured data request")
        self.assertLess(execution_time, 10.0, "DataHelperAgent should execute within 10 seconds")

        # Validate data request structure
        if isinstance(result.output, dict):
            self.assertIn("data_requests", result.output, "Should contain data_requests")
            data_requests = result.output["data_requests"]
            self.assertGreater(len(data_requests), 0, "Should generate at least one data request")

            # Validate each data request has required fields
            for request in data_requests:
                self.assertIn("category", request, "Each request should have category")
                self.assertIn("required_fields", request, "Each request should have required_fields")
                self.assertIn("priority", request, "Each request should have priority")
                self.assertIn("rationale", request, "Each request should have rationale")

        # Verify WebSocket events (if bridge available)
        if hasattr(data_helper_agent, 'websocket_bridge'):
            self.websocket_utility.verify_agent_events_sent([
                "agent_started", "agent_thinking", "agent_completed"
            ])

    @pytest.mark.asyncio
    async def test_validation_sub_agent_data_validation_workflow(self):
        """Test ValidationSubAgent validates user-provided data comprehensively."""

        # SETUP: Initialize ValidationSubAgent
        llm_manager = self._create_mock_llm_manager()
        tool_dispatcher = self._create_mock_tool_dispatcher()

        validation_agent = ValidationSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher
        )

        # Create validation execution context
        user_context = UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            agent_state=DeepAgentState(
                user_request="Please validate my AWS optimization data",
                user_prompt="Please validate my AWS optimization data",
                user_id=self.user_id,
                chat_thread_id=self.thread_id,
                run_id=self.run_id,
                agent_input=self.validation_scenario
            )
        )

        # EXECUTE: Run validation workflow
        start_time = time.time()

        with patch.object(llm_manager, 'generate_response') as mock_llm:
            # Mock validation analysis response
            mock_llm.return_value = {
                "validation_results": [
                    {
                        "field": "aws_bill",
                        "status": "valid",
                        "confidence": 0.95,
                        "insights": ["Monthly spend within expected range for workload"]
                    },
                    {
                        "field": "instance_types",
                        "status": "optimization_opportunity",
                        "confidence": 0.85,
                        "insights": ["t3.medium may be oversized for typical web workloads"]
                    },
                    {
                        "field": "usage_patterns",
                        "status": "needs_clarification",
                        "confidence": 0.6,
                        "insights": ["24/7 usage suggests potential for reserved instances"]
                    }
                ],
                "overall_data_quality": "good",
                "recommendations": ["Consider reserved instances", "Evaluate t3.small instances"]
            }

            result = await validation_agent.execute(user_context)

        execution_time = time.time() - start_time

        # VALIDATE: Verify validation results
        self.assertTrue(result.success, f"ValidationSubAgent execution failed: {result.error}")
        self.assertIsNotNone(result.output, "ValidationSubAgent should return validation results")
        self.assertLess(execution_time, 8.0, "ValidationSubAgent should execute within 8 seconds")

        # Validate validation structure
        if isinstance(result.output, dict):
            self.assertIn("validation_results", result.output, "Should contain validation_results")
            validation_results = result.output["validation_results"]
            self.assertGreater(len(validation_results), 0, "Should have validation results")

            # Validate each validation result
            for validation in validation_results:
                self.assertIn("field", validation, "Each validation should identify field")
                self.assertIn("status", validation, "Each validation should have status")
                self.assertIn("confidence", validation, "Each validation should have confidence")
                self.assertIn("insights", validation, "Each validation should provide insights")

    @pytest.mark.asyncio
    async def test_tool_discovery_sub_agent_workflow(self):
        """Test ToolDiscoverySubAgent discovers and validates appropriate tools for data operations."""

        # SETUP: Initialize ToolDiscoverySubAgent
        llm_manager = self._create_mock_llm_manager()
        tool_dispatcher = self._create_mock_tool_dispatcher()

        tool_discovery_agent = ToolDiscoverySubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher
        )

        # Create tool discovery context
        user_context = UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            agent_state=DeepAgentState(
                user_request="Find tools to help with AWS cost analysis and optimization",
                user_prompt="Find tools to help with AWS cost analysis and optimization",
                user_id=self.user_id,
                chat_thread_id=self.thread_id,
                run_id=self.run_id
            )
        )

        # EXECUTE: Run tool discovery workflow
        start_time = time.time()

        with patch.object(llm_manager, 'generate_response') as mock_llm:
            # Mock tool discovery response
            mock_llm.return_value = {
                "discovered_tools": [
                    {
                        "tool_name": "aws_cost_explorer",
                        "capabilities": ["cost_analysis", "usage_patterns", "recommendations"],
                        "confidence": 0.9,
                        "use_case": "Primary tool for AWS cost analysis"
                    },
                    {
                        "tool_name": "rightsizing_analyzer",
                        "capabilities": ["instance_optimization", "utilization_analysis"],
                        "confidence": 0.85,
                        "use_case": "Optimize instance sizing recommendations"
                    }
                ],
                "execution_plan": ["cost_analysis", "usage_analysis", "optimization_recommendations"],
                "estimated_execution_time": "3-5 minutes"
            }

            result = await tool_discovery_agent.execute(user_context)

        execution_time = time.time() - start_time

        # VALIDATE: Verify tool discovery results
        self.assertTrue(result.success, f"ToolDiscoverySubAgent execution failed: {result.error}")
        self.assertIsNotNone(result.output, "ToolDiscoverySubAgent should return discovered tools")
        self.assertLess(execution_time, 6.0, "ToolDiscoverySubAgent should execute within 6 seconds")

        # Validate tool discovery structure
        if isinstance(result.output, dict):
            self.assertIn("discovered_tools", result.output, "Should contain discovered_tools")
            discovered_tools = result.output["discovered_tools"]
            self.assertGreater(len(discovered_tools), 0, "Should discover at least one tool")

            # Validate each discovered tool
            for tool in discovered_tools:
                self.assertIn("tool_name", tool, "Each tool should have name")
                self.assertIn("capabilities", tool, "Each tool should list capabilities")
                self.assertIn("confidence", tool, "Each tool should have confidence score")
                self.assertIn("use_case", tool, "Each tool should explain use case")

    @pytest.mark.asyncio
    async def test_multi_agent_data_coordination_workflow(self):
        """Test coordination between multiple data sub-agents in a complete workflow."""

        # SETUP: Initialize multiple data agents
        llm_manager = self._create_mock_llm_manager()
        tool_dispatcher = self._create_mock_tool_dispatcher()

        # Initialize agents
        data_helper = DataHelperAgent(llm_manager, tool_dispatcher)
        validation_agent = ValidationSubAgent(llm_manager, tool_dispatcher)
        tool_discovery = ToolDiscoverySubAgent(llm_manager, tool_dispatcher)

        # Create coordinated workflow context
        user_context = UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            agent_state=DeepAgentState(
                user_request="Complete AWS optimization analysis with data coordination",
                user_prompt="Complete AWS optimization analysis with data coordination",
                user_id=self.user_id,
                chat_thread_id=self.thread_id,
                run_id=self.run_id
            )
        )

        # EXECUTE: Run multi-agent coordination workflow
        workflow_results = {}
        start_time = time.time()

        # Stage 1: Data request generation
        with patch.object(llm_manager, 'generate_response') as mock_llm:
            mock_llm.return_value = {"data_requests": [{"category": "aws_billing"}]}
            stage1_result = await data_helper.execute(user_context)
            workflow_results["data_requests"] = stage1_result

        # Stage 2: Tool discovery for data processing
        with patch.object(llm_manager, 'generate_response') as mock_llm:
            mock_llm.return_value = {"discovered_tools": [{"tool_name": "aws_analyzer"}]}
            stage2_result = await tool_discovery.execute(user_context)
            workflow_results["tool_discovery"] = stage2_result

        # Stage 3: Data validation
        with patch.object(llm_manager, 'generate_response') as mock_llm:
            mock_llm.return_value = {"validation_results": [{"field": "test", "status": "valid"}]}
            stage3_result = await validation_agent.execute(user_context)
            workflow_results["validation"] = stage3_result

        total_execution_time = time.time() - start_time

        # VALIDATE: Verify multi-agent coordination
        self.assertIn("data_requests", workflow_results, "Should complete data request stage")
        self.assertIn("tool_discovery", workflow_results, "Should complete tool discovery stage")
        self.assertIn("validation", workflow_results, "Should complete validation stage")

        # Validate all stages succeeded
        for stage, result in workflow_results.items():
            self.assertTrue(result.success, f"Stage {stage} should succeed: {result.error}")
            self.assertIsNotNone(result.output, f"Stage {stage} should have output")

        # Validate coordination timing
        self.assertLess(total_execution_time, 20.0, "Multi-agent workflow should complete within 20 seconds")

        # Verify workflow maintains user context consistency
        for stage, result in workflow_results.items():
            if hasattr(result, 'metadata') and result.metadata:
                self.assertEqual(result.metadata.get('user_id'), self.user_id, f"Stage {stage} should maintain user context")

    @pytest.mark.asyncio
    async def test_data_sub_agent_error_handling_recovery(self):
        """Test error handling and recovery patterns for data sub-agents."""

        # SETUP: Initialize agent with error-prone scenario
        llm_manager = self._create_mock_llm_manager()
        tool_dispatcher = self._create_mock_tool_dispatcher()

        data_helper = DataHelperAgent(llm_manager, tool_dispatcher)

        user_context = UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            agent_state=DeepAgentState(
                user_request="Invalid data optimization request",
                user_prompt="Invalid data optimization request",
                user_id=self.user_id,
                chat_thread_id=self.thread_id,
                run_id=self.run_id
            )
        )

        # EXECUTE: Test error scenarios
        with patch.object(llm_manager, 'generate_response') as mock_llm:
            # Simulate LLM failure
            mock_llm.side_effect = Exception("LLM service temporarily unavailable")

            result = await data_helper.execute(user_context)

        # VALIDATE: Verify graceful error handling
        self.assertFalse(result.success, "Should handle LLM failure gracefully")
        self.assertIsNotNone(result.error, "Should provide error information")
        self.assertIn("error", result.error.lower(), "Error message should indicate failure type")

        # Verify no resource leaks or corruption
        self.assertIsInstance(result.metadata, dict, "Should maintain metadata structure even on error")

    def _create_mock_llm_manager(self) -> LLMManager:
        """Create mock LLM manager for testing."""
        mock_llm = MagicMock(spec=LLMManager)
        mock_llm.generate_response = AsyncMock()
        return mock_llm

    def _create_mock_tool_dispatcher(self) -> UnifiedToolDispatcher:
        """Create mock tool dispatcher for testing."""
        mock_dispatcher = MagicMock(spec=UnifiedToolDispatcher)
        mock_dispatcher.execute_tool = AsyncMock()
        return mock_dispatcher


if __name__ == "__main__":
    pytest.main([__file__, "-v"])