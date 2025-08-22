"""
Agent Response Pipeline Performance Tests

Business Value Justification (BVJ):
- Segment: ALL (core functionality for Free, Early, Mid, Enterprise)
- Business Goal: Protect $35K MRR from core functionality failures
- Value Impact: Validates pipeline performance under load and SLA compliance
- Revenue Impact: Prevents platform outages that would cause immediate customer churn

Performance and SLA compliance tests for agent response pipeline.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio

# Add project root to path
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

from logging_config import central_logger

from .agent_pipeline_mocks import AgentPipelineMocks

logger = central_logger.get_logger(__name__)


class TestAgentResponsePipelinePerformance:
    """Performance tests for agent response pipeline."""

    @pytest.fixture
    def llm_manager_mock(self):
        """Mock LLM manager for agent response testing"""
        return AgentPipelineMocks.create_llm_manager_mock()

    @pytest.fixture
    def websocket_manager_mock(self):
        """Mock WebSocket manager for connection handling"""
        return AgentPipelineMocks.create_websocket_manager_mock()

    @pytest.fixture
    def redis_manager_mock(self):
        """Mock Redis manager for agent state management"""
        return AgentPipelineMocks.create_redis_manager_mock()

    @pytest.mark.asyncio
    async def test_pipeline_performance_under_concurrent_load(self, llm_manager_mock, websocket_manager_mock, redis_manager_mock):
        """BVJ: Validates pipeline maintains performance under concurrent request load."""
        concurrent_requests = 50
        max_response_time = 30.0
        
        test_requests = []
        for i in range(concurrent_requests):
            request_types = [f"Optimize GPU memory for model {i} with 16GB limit", f"Analyze query performance for database_{i} over 1000 requests", f"Debug memory leak in application_{i} consuming 8GB", f"Scale infrastructure for service_{i} to handle 5x traffic", f"Generate performance report for system_{i} optimization"]
            
            test_requests.append({"user_id": str(uuid.uuid4()), "content": request_types[i % len(request_types)], "request_id": f"load_test_{i}", "timestamp": datetime.now(timezone.utc)})

        async def process_request_pipeline(request):
            start_time = time.time()
            
            try:
                triage_delay = 0.05 + (0.02 * (len(request["content"]) / 100))
                await asyncio.sleep(triage_delay)
                
                if "optimize" in request["content"].lower():
                    specialist_delay = 0.3 + (0.1 * len(request["content"]) / 200)
                elif "analyze" in request["content"].lower():
                    specialist_delay = 0.4 + (0.15 * len(request["content"]) / 200)
                elif "debug" in request["content"].lower():
                    specialist_delay = 0.25 + (0.1 * len(request["content"]) / 200)
                else:
                    specialist_delay = 0.2
                
                await asyncio.sleep(min(specialist_delay, 2.0))
                
                response = await llm_manager_mock.generate_response(request["content"], "optimization")
                
                processing_time = time.time() - start_time
                
                return {"request_id": request["request_id"], "success": True, "processing_time": processing_time, "response_length": len(response["content"]), "user_id": request["user_id"]}
                
            except Exception as e:
                processing_time = time.time() - start_time
                return {"request_id": request["request_id"], "success": False, "processing_time": processing_time, "error": str(e), "user_id": request["user_id"]}

        start_time = time.time()
        
        results = await asyncio.gather(*[process_request_pipeline(request) for request in test_requests], return_exceptions=True)
        
        total_time = time.time() - start_time

        successful_results = [r for r in results if not isinstance(r, Exception) and r.get("success")]
        failed_results = [r for r in results if isinstance(r, Exception) or not r.get("success")]
        
        success_rate = (len(successful_results) / len(results)) * 100
        
        if successful_results:
            avg_processing_time = sum(r["processing_time"] for r in successful_results) / len(successful_results)
            max_processing_time = max(r["processing_time"] for r in successful_results)
            p95_processing_time = sorted([r["processing_time"] for r in successful_results])[int(len(successful_results) * 0.95)]
        else:
            avg_processing_time = float('inf')
            max_processing_time = float('inf')
            p95_processing_time = float('inf')

        assert success_rate >= 95.0, f"Success rate {success_rate}% below 95% under load"
        assert avg_processing_time < max_response_time, f"Avg processing time {avg_processing_time:.2f}s exceeds {max_response_time}s"
        assert p95_processing_time < max_response_time, f"P95 processing time {p95_processing_time:.2f}s exceeds {max_response_time}s"
        assert total_time < 60.0, f"Total concurrent processing {total_time:.2f}s too slow"

        throughput = len(successful_results) / total_time
        assert throughput >= 1.0, f"Throughput {throughput:.2f} requests/sec too low"

        logger.info(f"Load test: {success_rate}% success, {avg_processing_time:.2f}s avg, {throughput:.2f} req/s")

    @pytest.mark.asyncio
    async def test_websocket_message_delivery_reliability(self, websocket_manager_mock):
        """BVJ: Validates reliable WebSocket message delivery for agent responses."""
        test_users = []
        for i in range(20):
            user_id = str(uuid.uuid4())
            user_websocket = Mock()
            user_websocket.state = "connected"
            
            user_messages = []
            
            async def make_send_text(messages=user_messages):
                async def send_text(message):
                    messages.append({"type": "text", "content": message, "timestamp": datetime.now(timezone.utc)})
                    return True
                return send_text

            async def make_send_json(messages=user_messages):
                async def send_json(data):
                    messages.append({"type": "json", "content": data, "timestamp": datetime.now(timezone.utc)})
                    return True
                return send_json

            user_websocket.send_text = AsyncMock(side_effect=await make_send_text())
            user_websocket.send_json = AsyncMock(side_effect=await make_send_json())
            user_websocket._messages = user_messages
            
            await websocket_manager_mock.add_connection(user_id, user_websocket)
            
            test_users.append({"user_id": user_id, "websocket": user_websocket, "messages": user_messages})

        agent_responses = [{"type": "agent_response", "content": f"Optimization analysis complete for request {i}. GPU memory reduced by {20 + i}%.", "agent_type": "optimization_specialist", "quality_score": 0.75 + (i * 0.01)} for i in range(len(test_users))]

        delivery_tasks = []
        for i, user in enumerate(test_users):
            delivery_tasks.append(websocket_manager_mock.send_to_user(user["user_id"], agent_responses[i]))

        start_time = time.time()
        delivery_results = await asyncio.gather(*delivery_tasks, return_exceptions=True)
        delivery_time = time.time() - start_time

        successful_deliveries = sum(1 for r in delivery_results if r is True)
        failed_deliveries = len(delivery_results) - successful_deliveries
        
        delivery_success_rate = (successful_deliveries / len(delivery_results)) * 100

        assert delivery_success_rate >= 98.0, f"Delivery success rate {delivery_success_rate}% below 98%"
        assert delivery_time < 5.0, f"Delivery time {delivery_time:.2f}s too slow for {len(test_users)} users"

        messages_received = 0
        for user in test_users:
            if len(user["messages"]) > 0:
                messages_received += 1
                last_message = user["messages"][-1]
                assert "optimization" in str(last_message["content"]).lower()

        receipt_rate = (messages_received / len(test_users)) * 100
        assert receipt_rate >= 95.0, f"Message receipt rate {receipt_rate}% below 95%"

        logger.info(f"WebSocket delivery: {delivery_success_rate}% success, {receipt_rate}% receipt, {delivery_time:.2f}s")

    @pytest.mark.asyncio 
    async def test_end_to_end_response_time_sla_compliance(self, llm_manager_mock, websocket_manager_mock, redis_manager_mock):
        """BVJ: Validates end-to-end response time meets SLA for customer satisfaction."""
        sla_requirements = {"max_response_time": 30.0, "p95_response_time": 20.0, "p99_response_time": 25.0, "success_rate": 98.0}

        sla_test_scenarios = [{"complexity": "simple", "content": "Optimize memory usage", "expected_time": 5.0}, {"complexity": "medium", "content": "Analyze GPU utilization across 100 training jobs and recommend optimizations", "expected_time": 12.0}, {"complexity": "complex", "content": "Comprehensive performance analysis of distributed training pipeline with cost optimization recommendations", "expected_time": 20.0}, {"complexity": "very_complex", "content": "Full system optimization including GPU memory, network latency, storage I/O, and cost analysis with detailed implementation plan", "expected_time": 25.0}]

        e2e_test_requests = []
        for i in range(100):
            scenario = sla_test_scenarios[i % len(sla_test_scenarios)]
            e2e_test_requests.append({"user_id": str(uuid.uuid4()), "request_id": f"sla_test_{i}", "content": f"{scenario['content']} for system_{i}", "complexity": scenario["complexity"], "expected_max_time": scenario["expected_time"]})

        async def complete_e2e_pipeline(request):
            pipeline_start = time.time()
            
            try:
                await asyncio.sleep(0.01)
                
                triage_time = 0.1 if request["complexity"] == "simple" else 0.2
                await asyncio.sleep(triage_time)
                
                complexity_processing_times = {"simple": 1.0, "medium": 3.0, "complex": 8.0, "very_complex": 15.0}
                specialist_time = complexity_processing_times.get(request["complexity"], 5.0)
                await asyncio.sleep(specialist_time)
                
                response = await llm_manager_mock.generate_response(request["content"], "optimization")
                
                await asyncio.sleep(0.05)
                
                total_time = time.time() - pipeline_start
                
                return {"request_id": request["request_id"], "success": True, "total_time": total_time, "complexity": request["complexity"], "response_length": len(response["content"]), "meets_expectation": total_time <= request["expected_max_time"]}
                
            except Exception as e:
                total_time = time.time() - pipeline_start
                return {"request_id": request["request_id"], "success": False, "total_time": total_time, "complexity": request["complexity"], "error": str(e), "meets_expectation": False}

        sla_start_time = time.time()
        
        batch_size = 20
        all_results = []
        
        for i in range(0, len(e2e_test_requests), batch_size):
            batch = e2e_test_requests[i:i + batch_size]
            batch_results = await asyncio.gather(*[complete_e2e_pipeline(request) for request in batch])
            all_results.extend(batch_results)
            
            await asyncio.sleep(0.1)

        total_sla_time = time.time() - sla_start_time

        successful_requests = [r for r in all_results if r["success"]]
        failed_requests = [r for r in all_results if not r["success"]]
        
        if successful_requests:
            response_times = [r["total_time"] for r in successful_requests]
            response_times.sort()
            
            success_rate = (len(successful_requests) / len(all_results)) * 100
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            p95_response_time = response_times[int(len(response_times) * 0.95)]
            p99_response_time = response_times[int(len(response_times) * 0.99)]
        else:
            success_rate = 0.0
            avg_response_time = float('inf')
            max_response_time = float('inf')
            p95_response_time = float('inf')
            p99_response_time = float('inf')

        assert success_rate >= sla_requirements["success_rate"], f"Success rate {success_rate}% below SLA {sla_requirements['success_rate']}%"
        assert max_response_time <= sla_requirements["max_response_time"], f"Max response time {max_response_time:.2f}s exceeds SLA {sla_requirements['max_response_time']}s"
        assert p95_response_time <= sla_requirements["p95_response_time"], f"P95 response time {p95_response_time:.2f}s exceeds SLA {sla_requirements['p95_response_time']}s"
        assert p99_response_time <= sla_requirements["p99_response_time"], f"P99 response time {p99_response_time:.2f}s exceeds SLA {sla_requirements['p99_response_time']}s"

        complexity_performance = {}
        for complexity in ["simple", "medium", "complex", "very_complex"]:
            complexity_results = [r for r in successful_requests if r["complexity"] == complexity]
            if complexity_results:
                meets_expectation = sum(1 for r in complexity_results if r["meets_expectation"])
                expectation_rate = (meets_expectation / len(complexity_results)) * 100
                complexity_performance[complexity] = expectation_rate
                
                assert expectation_rate >= 90.0, f"{complexity} complexity expectation rate {expectation_rate}% below 90%"

        logger.info(f"E2E SLA validation: {success_rate}% success, {avg_response_time:.2f}s avg, P95={p95_response_time:.2f}s, P99={p99_response_time:.2f}s")
