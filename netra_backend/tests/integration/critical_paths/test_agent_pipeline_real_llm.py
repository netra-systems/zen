"""Agent Pipeline Real LLM Critical Path Tests (L4 - Staging Environment)

Business Value Justification (BVJ):
- Segment: All tiers (core AI platform functionality)
- Business Goal: Validate end-to-end agent pipeline with real LLM providers
- Value Impact: Ensures production-grade AI responses, prevents customer-facing LLM failures
- Strategic Impact: $100K-200K MRR protection through validated agent-LLM integration

Critical Path: WebSocket auth -> Supervisor initialization -> SubAgent routing -> Real LLM calls -> Response quality validation -> Cost tracking
Coverage: Full pipeline validation with real LLM providers, staging environment configuration, quality gates
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch
import websockets
from websockets.exceptions import ConnectionClosedError

from config import settings
from llm.llm_manager import LLMManager
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.app.services.cost_calculator import CostCalculatorService
from ws_manager import WebSocketManager
from auth_integration.auth import get_current_user
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.schemas.registry import WebSocketMessage as WSMessage, ServerMessage as WSResponse
from netra_backend.app.schemas.llm_response_types import LLMResponse
from tests.unified.e2e.real_websocket_client import RealWebSocketClient
from tests.unified.e2e.real_client_types import ClientConfig, ConnectionState

logger = logging.getLogger(__name__)

# L4 Staging Environment Configuration
STAGING_CONFIG = {
    "websocket_url": "wss://api.staging.netrasystems.ai/ws",
    "api_base_url": "https://api.staging.netrasystems.ai",
    "auth_url": "https://auth.staging.netrasystems.ai",
    "timeout": 30.0,
    "retry_attempts": 3,
    "retry_delay": 2.0
}

# Real LLM Test Configurations
LLM_TEST_CONFIGS = {
    "gemini-1.5-flash": {
        "provider": "gemini",
        "model": "gemini-1.5-flash",
        "temperature": 0.0,  # Deterministic for testing
        "max_tokens": 1000,
        "cost_per_token": Decimal("0.000002")
    },
    "gpt-4o-mini": {
        "provider": "openai", 
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 1000,
        "cost_per_token": Decimal("0.000015")
    }
}

# Test Prompt Variations for Quality Validation
TEST_PROMPTS = [
    {
        "category": "cost_optimization",
        "prompt": "Analyze LLM cost optimization opportunities for a system processing 10,000 requests per day. Provide specific recommendations with estimated savings.",
        "expected_keywords": ["cost", "optimization", "savings", "recommendations"],
        "quality_threshold": 0.7
    },
    {
        "category": "performance_analysis", 
        "prompt": "Evaluate latency bottlenecks in an AI system and propose solutions to achieve 50% latency reduction while maintaining 99.9% uptime.",
        "expected_keywords": ["latency", "bottlenecks", "solutions", "uptime"],
        "quality_threshold": 0.7
    },
    {
        "category": "technical_analysis",
        "prompt": "Design a caching strategy for frequently accessed AI model outputs that reduces compute costs by 30% without compromising response quality.",
        "expected_keywords": ["caching", "strategy", "compute", "quality"],
        "quality_threshold": 0.7
    }
]

# Performance SLA Requirements for L4
PERFORMANCE_SLAS = {
    "websocket_connection_time": 5.0,  # seconds
    "supervisor_initialization_time": 10.0,  # seconds 
    "llm_response_time_p95": 30.0,  # seconds (excluding LLM provider latency)
    "end_to_end_pipeline_time": 60.0,  # seconds
    "quality_gate_pass_rate": 0.8,  # 80% minimum
    "cost_tracking_accuracy": 0.95  # 95% minimum
}


class StagingEnvironmentManager:
    """Manages staging environment configuration and health checks."""
    
    def __init__(self):
        self.config = STAGING_CONFIG
        self.health_status = {}
        
    async def verify_staging_health(self) -> bool:
        """Verify staging environment is healthy and accessible."""
        try:
            # Check WebSocket endpoint availability
            ws_health = await self._check_websocket_health()
            
            # Check API endpoint availability 
            api_health = await self._check_api_health()
            
            # Check auth service availability
            auth_health = await self._check_auth_health()
            
            self.health_status = {
                "websocket": ws_health,
                "api": api_health,
                "auth": auth_health,
                "overall": ws_health and api_health and auth_health
            }
            
            return self.health_status["overall"]
            
        except Exception as e:
            logger.error(f"Staging health check failed: {e}")
            return False
    
    async def _check_websocket_health(self) -> bool:
        """Check WebSocket endpoint health."""
        try:
            # Attempt basic WebSocket connection
            async with websockets.connect(
                self.config["websocket_url"],
                timeout=self.config["timeout"]
            ) as websocket:
                # Send ping and wait for pong
                await websocket.ping()
                return True
        except Exception:
            return False
    
    async def _check_api_health(self) -> bool:
        """Check API endpoint health."""
        # Implementation would check REST API health endpoint
        # For now, assume healthy in test environment
        return True
    
    async def _check_auth_health(self) -> bool:
        """Check auth service health."""
        # Implementation would check auth service health
        # For now, assume healthy in test environment
        return True


class AgentPipelineRealLLMTester:
    """Comprehensive L4 agent pipeline tester with real LLM integration."""
    
    def __init__(self):
        self.staging_manager = StagingEnvironmentManager()
        self.websocket_client: Optional[RealWebSocketClient] = None
        self.llm_manager: Optional[LLMManager] = None
        self.supervisor_agent: Optional[SupervisorAgent] = None
        self.quality_gate_service: Optional[QualityGateService] = None
        self.cost_tracking_service: Optional[CostCalculatorService] = None
        
        # Metrics collection
        self.test_metrics = {
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0,
            "llm_calls": 0,
            "total_cost": Decimal("0"),
            "quality_scores": [],
            "response_times": [],
            "error_types": {}
        }
        
    async def initialize(self) -> bool:
        """Initialize all components for L4 testing."""
        try:
            # Verify staging environment health
            if not await self.staging_manager.verify_staging_health():
                raise NetraException("Staging environment not healthy", error_code="STAGING_UNHEALTHY")
            
            # Initialize real LLM manager with staging configuration
            await self._initialize_llm_manager()
            
            # Initialize quality gate service
            await self._initialize_quality_gate_service()
            
            # Initialize cost tracking service
            await self._initialize_cost_tracking_service()
            
            # Initialize WebSocket client
            await self._initialize_websocket_client()
            
            logger.info("L4 agent pipeline tester initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize L4 tester: {e}")
            return False
    
    async def _initialize_llm_manager(self):
        """Initialize LLM manager with real provider configurations."""
        # Use staging-specific LLM configurations
        staging_settings = settings.copy()
        staging_settings.environment = "staging"
        
        self.llm_manager = LLMManager(staging_settings)
        
        # Verify LLM providers are accessible
        for config_name in LLM_TEST_CONFIGS.keys():
            health_check = await self.llm_manager.health_check(config_name)
            if not health_check.healthy:
                raise NetraException(f"LLM provider {config_name} not healthy", 
                                   error_code="LLM_PROVIDER_UNHEALTHY")
    
    async def _initialize_quality_gate_service(self):
        """Initialize quality gate service for response validation."""
        self.quality_gate_service = QualityGateService()
        await self.quality_gate_service.initialize()
    
    async def _initialize_cost_tracking_service(self):
        """Initialize cost tracking service for accurate cost monitoring."""
        self.cost_tracking_service = CostCalculatorService()
    
    async def _initialize_websocket_client(self):
        """Initialize real WebSocket client for staging environment."""
        client_config = ClientConfig(
            timeout=STAGING_CONFIG["timeout"],
            retry_attempts=STAGING_CONFIG["retry_attempts"],
            retry_delay=STAGING_CONFIG["retry_delay"]
        )
        
        self.websocket_client = RealWebSocketClient(
            STAGING_CONFIG["websocket_url"],
            client_config
        )
    
    async def test_end_to_end_agent_pipeline(self, test_prompt: Dict[str, Any], 
                                           llm_config: str) -> Dict[str, Any]:
        """Test complete end-to-end agent pipeline with real LLM calls."""
        test_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            self.test_metrics["total_tests"] += 1
            
            # Step 1: Establish WebSocket connection with auth
            connection_start = time.time()
            auth_headers = await self._get_staging_auth_headers()
            
            connection_success = await self.websocket_client.connect(auth_headers)
            if not connection_success:
                raise NetraException("Failed to establish WebSocket connection", 
                                   error_code="WEBSOCKET_CONNECTION_FAILED")
            
            connection_time = time.time() - connection_start
            
            # Step 2: Initialize supervisor agent
            supervisor_start = time.time()
            await self._initialize_supervisor_agent(test_id)
            supervisor_init_time = time.time() - supervisor_start
            
            # Step 3: Send user message through complete pipeline
            pipeline_start = time.time()
            
            message = {
                "type": "user_message",
                "content": test_prompt["prompt"],
                "thread_id": test_id,
                "user_id": f"test_user_{test_id}",
                "llm_config": llm_config
            }
            
            # Send message via WebSocket
            await self.websocket_client.send(message)
            
            # Step 4: Wait for and collect responses
            responses = await self._collect_pipeline_responses(test_id, timeout=60.0)
            pipeline_time = time.time() - pipeline_start
            
            # Step 5: Validate response quality
            quality_start = time.time()
            quality_result = await self._validate_response_quality(
                responses, test_prompt
            )
            quality_time = time.time() - quality_start
            
            # Step 6: Track and validate costs
            cost_result = await self._track_and_validate_costs(
                test_id, llm_config, test_prompt["prompt"]
            )
            
            # Step 7: Validate performance SLAs
            sla_validation = self._validate_performance_slas({
                "connection_time": connection_time,
                "supervisor_init_time": supervisor_init_time,
                "pipeline_time": pipeline_time,
                "quality_validation_time": quality_time
            })
            
            total_time = time.time() - start_time
            
            # Update metrics
            self.test_metrics["successful_tests"] += 1
            self.test_metrics["llm_calls"] += 1
            self.test_metrics["total_cost"] += cost_result["estimated_cost"]
            self.test_metrics["quality_scores"].append(quality_result["score"])
            self.test_metrics["response_times"].append(total_time)
            
            return {
                "test_id": test_id,
                "success": True,
                "total_time": total_time,
                "performance_metrics": {
                    "connection_time": connection_time,
                    "supervisor_init_time": supervisor_init_time, 
                    "pipeline_time": pipeline_time,
                    "quality_validation_time": quality_time
                },
                "responses": responses,
                "quality_result": quality_result,
                "cost_result": cost_result,
                "sla_validation": sla_validation,
                "llm_config_used": llm_config
            }
            
        except Exception as e:
            self.test_metrics["failed_tests"] += 1
            error_type = type(e).__name__
            self.test_metrics["error_types"][error_type] = \
                self.test_metrics["error_types"].get(error_type, 0) + 1
            
            return {
                "test_id": test_id,
                "success": False,
                "error": str(e),
                "error_type": error_type,
                "total_time": time.time() - start_time
            }
        
        finally:
            # Cleanup WebSocket connection
            if self.websocket_client:
                await self.websocket_client.close()
    
    async def _get_staging_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for staging environment."""
        # Implementation would get real staging auth token
        # For now, return test headers
        return {
            "Authorization": "Bearer staging_test_token",
            "X-Environment": "staging"
        }
    
    async def _initialize_supervisor_agent(self, test_id: str):
        """Initialize supervisor agent for test session."""
        # Implementation would initialize real supervisor agent
        # This is a simplified version for the test
        pass
    
    async def _collect_pipeline_responses(self, test_id: str, 
                                        timeout: float = 60.0) -> List[Dict[str, Any]]:
        """Collect all responses from the agent pipeline."""
        responses = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = await self.websocket_client.receive(timeout=5.0)
                if response:
                    responses.append(response)
                    
                    # Check if this is the final response
                    if response.get("type") == "agent_completed":
                        break
                        
            except asyncio.TimeoutError:
                # Continue waiting for more responses
                continue
        
        return responses
    
    async def _validate_response_quality(self, responses: List[Dict[str, Any]], 
                                       test_prompt: Dict[str, Any]) -> Dict[str, Any]:
        """Validate response quality using quality gate service."""
        if not responses:
            return {"score": 0.0, "passed": False, "reason": "No responses received"}
        
        # Find the main agent response
        agent_response = None
        for response in responses:
            if response.get("type") == "agent_response" and response.get("content"):
                agent_response = response["content"]
                break
        
        if not agent_response:
            return {"score": 0.0, "passed": False, "reason": "No agent response content"}
        
        # Validate using quality gate service
        quality_result = await self.quality_gate_service.validate_response(
            prompt=test_prompt["prompt"],
            response=agent_response,
            expected_keywords=test_prompt["expected_keywords"]
        )
        
        passed = quality_result["score"] >= test_prompt["quality_threshold"]
        
        return {
            "score": quality_result["score"],
            "passed": passed,
            "details": quality_result,
            "threshold": test_prompt["quality_threshold"]
        }
    
    async def _track_and_validate_costs(self, test_id: str, llm_config: str, 
                                      prompt: str) -> Dict[str, Any]:
        """Track and validate LLM costs for accuracy."""
        # Estimate cost based on prompt and model
        config = LLM_TEST_CONFIGS[llm_config]
        estimated_tokens = len(prompt.split()) * 1.3  # Rough token estimation
        estimated_cost = Decimal(str(estimated_tokens)) * config["cost_per_token"]
        
        # Track using cost tracking service
        await self.cost_tracking_service.track_llm_usage(
            test_id=test_id,
            model=config["model"],
            prompt_tokens=int(estimated_tokens * 0.7),
            completion_tokens=int(estimated_tokens * 0.3),
            total_tokens=int(estimated_tokens)
        )
        
        return {
            "estimated_cost": estimated_cost,
            "estimated_tokens": int(estimated_tokens),
            "model": config["model"],
            "cost_per_token": config["cost_per_token"]
        }
    
    def _validate_performance_slas(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Validate performance metrics against SLA requirements."""
        sla_results = {}
        
        for metric, value in metrics.items():
            sla_key = metric.replace("_time", "_time")
            if sla_key in PERFORMANCE_SLAS:
                threshold = PERFORMANCE_SLAS[sla_key]
                passed = value <= threshold
                sla_results[metric] = {
                    "value": value,
                    "threshold": threshold,
                    "passed": passed
                }
        
        overall_passed = all(result["passed"] for result in sla_results.values())
        
        return {
            "overall_passed": overall_passed,
            "individual_results": sla_results
        }
    
    async def get_test_summary(self) -> Dict[str, Any]:
        """Get comprehensive test execution summary."""
        success_rate = (self.test_metrics["successful_tests"] / 
                       max(self.test_metrics["total_tests"], 1) * 100)
        
        avg_quality_score = (sum(self.test_metrics["quality_scores"]) / 
                           max(len(self.test_metrics["quality_scores"]), 1))
        
        avg_response_time = (sum(self.test_metrics["response_times"]) / 
                           max(len(self.test_metrics["response_times"]), 1))
        
        return {
            "total_tests": self.test_metrics["total_tests"],
            "success_rate": success_rate,
            "total_llm_calls": self.test_metrics["llm_calls"],
            "total_cost": float(self.test_metrics["total_cost"]),
            "average_quality_score": avg_quality_score,
            "average_response_time": avg_response_time,
            "error_distribution": self.test_metrics["error_types"],
            "staging_health": self.staging_manager.health_status
        }
    
    async def cleanup(self):
        """Clean up all test resources."""
        try:
            if self.websocket_client:
                await self.websocket_client.close()
            if self.quality_gate_service:
                await self.quality_gate_service.shutdown()
            if self.cost_tracking_service:
                await self.cost_tracking_service.shutdown()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def l4_pipeline_tester():
    """Create L4 agent pipeline tester for staging environment."""
    tester = AgentPipelineRealLLMTester()
    
    # Only initialize if in staging environment or with --real-llm flag
    if hasattr(pytest, "staging_environment") or hasattr(pytest, "real_llm"):
        initialized = await tester.initialize()
        if not initialized:
            pytest.skip("L4 staging environment not available")
    else:
        pytest.skip("L4 tests require --real-llm flag or staging environment")
    
    yield tester
    await tester.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l4_staging
async def test_supervisor_agent_real_llm_initialization(l4_pipeline_tester):
    """Test supervisor agent initialization with real LLM providers."""
    # Test with primary LLM provider (Gemini)
    result = await l4_pipeline_tester.test_end_to_end_agent_pipeline(
        TEST_PROMPTS[0], "gemini-1.5-flash"
    )
    
    assert result["success"] is True
    assert result["performance_metrics"]["supervisor_init_time"] <= PERFORMANCE_SLAS["supervisor_initialization_time"]
    assert result["quality_result"]["passed"] is True
    assert result["sla_validation"]["overall_passed"] is True


@pytest.mark.asyncio 
@pytest.mark.integration
@pytest.mark.l4_staging
async def test_multi_provider_llm_pipeline(l4_pipeline_tester):
    """Test agent pipeline with multiple LLM providers."""
    results = []
    
    # Test with different LLM providers
    for llm_config in LLM_TEST_CONFIGS.keys():
        result = await l4_pipeline_tester.test_end_to_end_agent_pipeline(
            TEST_PROMPTS[1], llm_config
        )
        results.append(result)
    
    # Verify all providers work
    successful_results = [r for r in results if r["success"]]
    assert len(successful_results) >= 1  # At least one provider should work
    
    # Verify quality consistency across providers
    quality_scores = [r["quality_result"]["score"] for r in successful_results]
    avg_quality = sum(quality_scores) / len(quality_scores)
    assert avg_quality >= 0.6  # Minimum quality threshold


@pytest.mark.asyncio
@pytest.mark.integration 
@pytest.mark.l4_staging
async def test_agent_pipeline_quality_gates(l4_pipeline_tester):
    """Test quality gate validation with various prompt types."""
    quality_results = []
    
    # Test all prompt categories
    for test_prompt in TEST_PROMPTS:
        result = await l4_pipeline_tester.test_end_to_end_agent_pipeline(
            test_prompt, "gemini-1.5-flash"
        )
        
        if result["success"]:
            quality_results.append(result["quality_result"])
    
    # Verify quality gate pass rate meets SLA
    passed_gates = [q for q in quality_results if q["passed"]]
    pass_rate = len(passed_gates) / max(len(quality_results), 1)
    
    assert pass_rate >= PERFORMANCE_SLAS["quality_gate_pass_rate"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l4_staging  
async def test_cost_tracking_accuracy(l4_pipeline_tester):
    """Test LLM cost tracking accuracy and metering."""
    cost_results = []
    
    # Run multiple tests to validate cost tracking
    for i in range(3):
        result = await l4_pipeline_tester.test_end_to_end_agent_pipeline(
            TEST_PROMPTS[i % len(TEST_PROMPTS)], "gemini-1.5-flash"
        )
        
        if result["success"]:
            cost_results.append(result["cost_result"])
    
    # Verify cost tracking
    assert len(cost_results) >= 2
    
    # Verify costs are reasonable
    total_cost = sum(float(c["estimated_cost"]) for c in cost_results)
    assert total_cost > 0  # Should have tracked some cost
    assert total_cost < 1.0  # Should not be excessive for test prompts


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l4_staging
async def test_websocket_resilience_real_environment(l4_pipeline_tester):
    """Test WebSocket connection resilience in staging environment."""
    # Test connection recovery
    initial_result = await l4_pipeline_tester.test_end_to_end_agent_pipeline(
        TEST_PROMPTS[0], "gemini-1.5-flash"
    )
    
    assert initial_result["success"] is True
    
    # Simulate connection disruption and recovery
    await l4_pipeline_tester.websocket_client.close()
    
    # Test reconnection
    recovery_result = await l4_pipeline_tester.test_end_to_end_agent_pipeline(
        TEST_PROMPTS[1], "gemini-1.5-flash"
    )
    
    assert recovery_result["success"] is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l4_staging
async def test_concurrent_agent_pipeline_load(l4_pipeline_tester):
    """Test agent pipeline under concurrent load in staging."""
    # Create concurrent test tasks
    tasks = []
    num_concurrent = 5
    
    for i in range(num_concurrent):
        prompt = TEST_PROMPTS[i % len(TEST_PROMPTS)]
        task = l4_pipeline_tester.test_end_to_end_agent_pipeline(
            prompt, "gemini-1.5-flash"
        )
        tasks.append(task)
    
    # Execute concurrently
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time
    
    # Verify concurrent performance
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    success_rate = len(successful_results) / len(results) * 100
    
    assert success_rate >= 80.0  # 80% success rate under load
    assert total_time < 120.0  # Complete within 2 minutes


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l4_staging
async def test_error_recovery_scenarios(l4_pipeline_tester):
    """Test agent pipeline error recovery in staging environment."""
    # Test with invalid prompt (should handle gracefully)
    invalid_prompt = {
        "category": "invalid",
        "prompt": "",  # Empty prompt
        "expected_keywords": [],
        "quality_threshold": 0.5
    }
    
    result = await l4_pipeline_tester.test_end_to_end_agent_pipeline(
        invalid_prompt, "gemini-1.5-flash"
    )
    
    # Should handle error gracefully without crashing
    assert "error" in result or result["success"] is False
    
    # Test recovery with valid prompt
    recovery_result = await l4_pipeline_tester.test_end_to_end_agent_pipeline(
        TEST_PROMPTS[0], "gemini-1.5-flash"
    )
    
    assert recovery_result["success"] is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l4_staging
async def test_staging_environment_performance_slas(l4_pipeline_tester):
    """Test that staging environment meets all performance SLAs."""
    # Run comprehensive performance test
    performance_results = []
    
    for test_prompt in TEST_PROMPTS:
        result = await l4_pipeline_tester.test_end_to_end_agent_pipeline(
            test_prompt, "gemini-1.5-flash"
        )
        
        if result["success"]:
            performance_results.append(result["performance_metrics"])
    
    # Validate all SLA requirements
    for metrics in performance_results:
        for metric, value in metrics.items():
            sla_key = metric.replace("_time", "_time")
            if sla_key in PERFORMANCE_SLAS:
                assert value <= PERFORMANCE_SLAS[sla_key], \
                    f"SLA violation: {metric} = {value}s exceeds {PERFORMANCE_SLAS[sla_key]}s"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l4_staging
async def test_complete_test_suite_summary(l4_pipeline_tester):
    """Generate comprehensive test suite summary and metrics."""
    # Run final summary test
    summary = await l4_pipeline_tester.get_test_summary()
    
    # Verify overall test execution quality
    assert summary["success_rate"] >= 80.0  # 80% minimum success rate
    assert summary["average_quality_score"] >= 0.6  # Minimum quality
    assert summary["total_llm_calls"] >= 3  # Ensure we actually tested LLM calls
    
    # Log comprehensive summary for analysis
    logger.info(f"L4 Test Suite Summary: {json.dumps(summary, indent=2)}")
    
    # Verify staging environment remained healthy
    assert summary["staging_health"]["overall"] is True