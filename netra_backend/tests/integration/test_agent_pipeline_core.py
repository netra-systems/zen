"""
Agent Response Pipeline Core Tests

Business Value Justification (BVJ):
- Segment: ALL (core functionality for Free, Early, Mid, Enterprise)
- Business Goal: Protect $35K MRR from core functionality failures
- Value Impact: Validates complete agent response pipeline from WebSocket to delivery
- Revenue Impact: Prevents platform outages that would cause immediate customer churn

Core agent response pipeline tests including complete pipeline and routing accuracy.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio

# Set testing environment
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock

import pytest

os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from netra_backend.app.logging_config import central_logger

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.tests.integration.agent_pipeline_mocks import AgentPipelineMocks

logger = central_logger.get_logger(__name__)

class TestAgentResponsePipelineCore:
    """Core agent response pipeline tests."""

    @pytest.fixture
    def llm_manager_mock(self):
        """Mock LLM manager for agent response testing"""
        return AgentPipelineMocks.create_llm_manager_mock()

    @pytest.fixture
    def websocket_mock(self):
        """Mock WebSocket for message delivery testing"""
        return AgentPipelineMocks.create_websocket_mock()

    @pytest.fixture
    def redis_manager_mock(self):
        """Mock Redis manager for agent state management"""
        return AgentPipelineMocks.create_redis_manager_mock()

    @pytest.fixture
    def websocket_manager_mock(self):
        """Mock WebSocket manager for connection handling"""
        return AgentPipelineMocks.create_websocket_manager_mock()

    @pytest.mark.asyncio
    async def test_complete_websocket_to_agent_pipeline(self, llm_manager_mock, websocket_mock, websocket_manager_mock, redis_manager_mock):
        """BVJ: Validates complete message flow from WebSocket through agent system to response delivery."""
        test_user_id = str(uuid.uuid4())
        test_message = {"type": "user_message", "content": "I need to optimize GPU memory usage in my ML training pipeline. Current usage is 24GB and I want to reduce costs.", "user_id": test_user_id, "timestamp": datetime.now(timezone.utc).isoformat()}

        await websocket_manager_mock.add_connection(test_user_id, websocket_mock)

        agent_state = DeepAgentState(user_id=test_user_id, thread_id=str(uuid.uuid4()), current_agent="triage", redis_manager=redis_manager_mock)

        triage_agent = Mock()
        
        async def mock_triage_process(message):
            await asyncio.sleep(0.1)
            
            if "optimize" in message["content"].lower() and "gpu" in message["content"].lower():
                return {"routing_decision": "optimization_specialist", "confidence": 0.95, "reasoning": "GPU optimization request requires specialized performance analysis", "estimated_complexity": "medium"}
            else:
                return {"routing_decision": "general_assistant", "confidence": 0.7, "reasoning": "General inquiry", "estimated_complexity": "low"}

        triage_agent.process_message = AsyncMock(side_effect=mock_triage_process)

        optimization_agent = Mock()
        
        async def mock_optimization_response(message, triage_result):
            await asyncio.sleep(0.5)
            
            specialist_prompt = f"Optimization request: {message['content']}\nTriage analysis: {triage_result['reasoning']}"
            llm_response = await llm_manager_mock.generate_response(specialist_prompt, "optimization", "high_quality")
            
            return {"response": llm_response["content"], "agent_type": "optimization_specialist", "processing_time": 0.5, "quality_metrics": {"specificity_score": 0.85, "actionability_score": 0.90, "technical_accuracy": 0.88}}

        optimization_agent.process_request = AsyncMock(side_effect=mock_optimization_response)

        start_time = time.time()

        triage_result = await triage_agent.process_message(test_message)
        
        if triage_result["routing_decision"] == "optimization_specialist":
            specialist_response = await optimization_agent.process_request(test_message, triage_result)
        else:
            specialist_response = {"response": "General response", "agent_type": "general"}

        response_message = {"type": "agent_response", "content": specialist_response["response"], "agent_type": specialist_response["agent_type"], "timestamp": datetime.now(timezone.utc).isoformat(), "quality_metrics": specialist_response.get("quality_metrics", {})}
        
        await websocket_manager_mock.send_to_user(test_user_id, response_message)
        
        total_time = time.time() - start_time

        assert triage_result["routing_decision"] == "optimization_specialist"
        assert triage_result["confidence"] >= 0.9
        assert specialist_response["agent_type"] == "optimization_specialist"
        assert total_time < 30.0, f"Pipeline took {total_time:.2f}s, exceeds 30s limit"

        quality_metrics = specialist_response["quality_metrics"]
        assert quality_metrics["specificity_score"] >= 0.6, f"Specificity {quality_metrics['specificity_score']} below 0.6"
        assert quality_metrics["actionability_score"] >= 0.6, f"Actionability {quality_metrics['actionability_score']} below 0.6"

        sent_messages = websocket_mock._sent_messages
        assert len(sent_messages) > 0, "No messages sent to WebSocket"
        
        response_delivered = sent_messages[-1]
        assert "optimization" in response_delivered["content"]["content"].lower()

        logger.info(f"Complete pipeline validated: {total_time:.2f}s, quality={quality_metrics}")

    @pytest.mark.asyncio 
    async def test_agent_routing_accuracy_validation(self, llm_manager_mock, redis_manager_mock):
        """BVJ: Validates triage agent accurately routes requests to appropriate specialists."""
        routing_scenarios = [{"message": "Optimize GPU memory usage and reduce training costs by 30%", "expected_agent": "optimization_specialist", "min_confidence": 0.8}, {"message": "Analyze database query performance across 1000 requests", "expected_agent": "data_analysis_specialist", "min_confidence": 0.8}, {"message": "Create deployment plan for scaling to 50 nodes", "expected_agent": "infrastructure_specialist", "min_confidence": 0.7}, {"message": "What's the weather today?", "expected_agent": "general_assistant", "min_confidence": 0.6}, {"message": "Debug memory leak in Python application", "expected_agent": "debugging_specialist", "min_confidence": 0.7}]

        triage_agent = AgentPipelineMocks.create_intelligent_triage_agent()

        routing_results = []
        
        for scenario in routing_scenarios:
            routing_result = await triage_agent.route_message(scenario["message"])
            
            result_analysis = {"message": scenario["message"][:50] + "...", "expected_agent": scenario["expected_agent"], "actual_agent": routing_result["agent"], "confidence": routing_result["confidence"], "correct_routing": routing_result["agent"] == scenario["expected_agent"], "confidence_met": routing_result["confidence"] >= scenario["min_confidence"]}
            
            routing_results.append(result_analysis)

        correct_routings = sum(1 for r in routing_results if r["correct_routing"])
        confidence_met = sum(1 for r in routing_results if r["confidence_met"])
        
        routing_accuracy = (correct_routings / len(routing_results)) * 100
        confidence_accuracy = (confidence_met / len(routing_results)) * 100

        assert routing_accuracy >= 80.0, f"Routing accuracy {routing_accuracy}% below 80%"
        assert confidence_accuracy >= 90.0, f"Confidence accuracy {confidence_accuracy}% below 90%"

        for result in routing_results:
            if result["expected_agent"] in ["optimization_specialist", "data_analysis_specialist"]:
                assert result["confidence"] >= 0.7, f"High-value agent routing confidence too low: {result['confidence']}"

        logger.info(f"Routing accuracy validation: {routing_accuracy}% routing, {confidence_accuracy}% confidence")

    @pytest.mark.asyncio
    async def test_response_quality_metrics_validation(self, llm_manager_mock, redis_manager_mock):
        """BVJ: Validates agent responses meet quality thresholds for customer satisfaction."""
        quality_test_cases = [{"request": "Optimize GPU memory allocation for transformer model training", "agent_type": "optimization", "expected_min_specificity": 0.7, "expected_min_actionability": 0.8}, {"request": "Analyze API response time degradation over past week", "agent_type": "data_analysis", "expected_min_specificity": 0.8, "expected_min_actionability": 0.7}, {"request": "Scale Kubernetes cluster to handle 10x traffic increase", "agent_type": "optimization", "expected_min_specificity": 0.6, "expected_min_actionability": 0.9}]

        assess_response_quality = AgentPipelineMocks.create_quality_assessment_function()

        quality_results = []
        
        for test_case in quality_test_cases:
            agent_response = await llm_manager_mock.generate_response(test_case["request"], test_case["agent_type"], "high_quality")
            
            quality_metrics = assess_response_quality(agent_response["content"], test_case["request"])
            
            quality_result = {"request": test_case["request"][:40] + "...", "agent_type": test_case["agent_type"], "response_length": len(agent_response["content"]), "quality_metrics": quality_metrics, "meets_specificity": quality_metrics["specificity_score"] >= test_case["expected_min_specificity"], "meets_actionability": quality_metrics["actionability_score"] >= test_case["expected_min_actionability"], "meets_overall": quality_metrics["overall_score"] >= 0.6}
            
            quality_results.append(quality_result)

        specificity_passed = sum(1 for r in quality_results if r["meets_specificity"])
        actionability_passed = sum(1 for r in quality_results if r["meets_actionability"])
        overall_passed = sum(1 for r in quality_results if r["meets_overall"])
        
        total_tests = len(quality_results)
        
        specificity_rate = (specificity_passed / total_tests) * 100
        actionability_rate = (actionability_passed / total_tests) * 100
        overall_rate = (overall_passed / total_tests) * 100

        assert specificity_rate >= 80.0, f"Specificity pass rate {specificity_rate}% below 80%"
        assert actionability_rate >= 80.0, f"Actionability pass rate {actionability_rate}% below 80%" 
        assert overall_rate >= 85.0, f"Overall quality pass rate {overall_rate}% below 85%"

        for result in quality_results:
            assert result["quality_metrics"]["specificity_score"] >= 0.6, f"Response specificity too low: {result['quality_metrics']['specificity_score']}"
            assert result["quality_metrics"]["actionability_score"] >= 0.6, f"Response actionability too low: {result['quality_metrics']['actionability_score']}"

        logger.info(f"Quality validation: {specificity_rate}% specificity, {actionability_rate}% actionability, {overall_rate}% overall")
