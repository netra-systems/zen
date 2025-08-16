"""
Focused tests for Real Agent Services - LLM providers and agent orchestration
Tests real LLM integration, agent coordination, and end-to-end workflows
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

import os
import sys
import asyncio
import pytest
import time
from typing import Dict, List, Optional, Any, Callable, TypeVar
from pathlib import Path
import functools
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

T = TypeVar('T')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.agent_service import AgentService
from app.llm.llm_manager import LLMManager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Test markers for agent services
pytestmark = [
    pytest.mark.real_services,
    pytest.mark.real_llm,
    pytest.mark.e2e
]

# Skip tests if real services not enabled
skip_if_no_real_services = pytest.mark.skipif(
    os.environ.get("ENABLE_REAL_LLM_TESTING") != "true",
    reason="Real service tests disabled. Set ENABLE_REAL_LLM_TESTING=true to run"
)


class TestRealAgentServices:
    """Test real agent services integration"""
    
    # Timeout configurations for agent services
    LLM_TIMEOUT = 60  # seconds
    AGENT_TIMEOUT = 120  # seconds for full agent processing
    
    @staticmethod
    def with_retry_and_timeout(timeout: int = 30, max_attempts: int = 3):
        """Decorator to add retry logic and timeout to service calls"""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry=retry_if_exception_type((ConnectionError, TimeoutError, asyncio.TimeoutError))
            )
            @functools.wraps(func)
            async def wrapper(*wrapped_args, **wrapped_kwargs):
                return await asyncio.wait_for(func(*wrapped_args, **wrapped_kwargs), timeout=timeout)
            return wrapper
        return decorator
    
    @pytest.fixture(scope="class")
    async def test_user_data(self):
        """Create test user data for real service tests"""
        return {
            "user_id": f"test_user_{int(time.time())}",
            "email": f"test_{int(time.time())}@example.com",
            "name": "Test User Real Services"
        }
    
    @pytest.fixture(scope="class")
    async def agent_service(self):
        """Initialize real agent service for testing"""
        return AgentService()
    
    @pytest.fixture(scope="class")
    async def llm_manager(self):
        """Initialize real LLM manager for testing"""
        return LLMManager()

    def _create_test_message(self, test_user_data):
        """Create test message for agent testing"""
        return {
            "content": "Analyze supply chain optimization for automotive industry",
            "user_id": test_user_data["user_id"],
            "timestamp": time.time()
        }

    def _validate_agent_response(self, response):
        """Validate agent response structure and content"""
        assert response is not None
        assert "content" in response or "message" in response
        content = response.get("content") or response.get("message", "")
        assert len(content) > 50  # Meaningful response length
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=120)  # 2 minutes for full orchestration
    async def test_full_agent_orchestration_with_real_llm(self, agent_service, test_user_data):
        """Test complete agent orchestration with real LLM providers"""
        test_message = self._create_test_message(test_user_data)
        response = await agent_service.process_message(
            message=test_message["content"],
            user_id=test_message["user_id"]
        )
        self._validate_agent_response(response)
        logger.info(f"Agent orchestration completed successfully for user {test_user_data['user_id']}")

    def _create_coordination_scenario(self):
        """Create multi-agent coordination test scenario"""
        return {
            "primary_task": "Supply chain risk assessment",
            "secondary_tasks": ["Market analysis", "Cost optimization"],
            "coordination_type": "parallel_processing"
        }

    def _validate_coordination_results(self, results):
        """Validate multi-agent coordination results"""
        assert isinstance(results, (list, dict))
        if isinstance(results, list):
            assert len(results) > 0
        if isinstance(results, dict):
            assert len(results.keys()) > 0
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=180)  # 3 minutes for coordination
    async def test_multi_agent_coordination_real(self, agent_service):
        """Test real multi-agent coordination scenarios"""
        scenario = self._create_coordination_scenario()
        results = await agent_service.coordinate_agents(
            primary_task=scenario["primary_task"],
            secondary_tasks=scenario["secondary_tasks"]
        )
        self._validate_coordination_results(results)
        logger.info("Multi-agent coordination completed successfully")

    def _get_test_providers_and_models(self):
        """Get list of LLM providers and models to test"""
        return [
            ("openai", "gpt-4o-mini"),
            ("anthropic", "claude-3-haiku-20240307"),
            ("google", "gemini-1.5-flash")
        ]

    def _create_provider_test_prompt(self, provider, model):
        """Create test prompt for specific provider and model"""
        return f"Test prompt for {provider} {model}: Explain quantum computing in one sentence."

    def _validate_llm_response(self, response, provider, model):
        """Validate LLM provider response"""
        assert response is not None
        assert len(str(response)) > 20  # Non-trivial response
        logger.info(f"LLM test passed for {provider}/{model}")
        return True

    @skip_if_no_real_services
    @pytest.mark.parametrize("provider,model", [
        ("openai", "gpt-4o-mini"),
        ("anthropic", "claude-3-haiku-20240307"),
        ("google", "gemini-1.5-flash")
    ])
    @with_retry_and_timeout(timeout=60)
    async def test_llm_provider_real(self, llm_manager, provider: str, model: str):
        """Test real LLM provider integration"""
        prompt = self._create_provider_test_prompt(provider, model)
        response = await llm_manager.generate_response(
            prompt=prompt,
            provider=provider,
            model=model
        )
        self._validate_llm_response(response, provider, model)

    def _create_streaming_test_scenario(self):
        """Create streaming response test scenario"""
        return {
            "prompt": "Generate a detailed explanation of machine learning concepts",
            "stream": True,
            "max_tokens": 500
        }

    def _validate_streaming_response(self, stream_response):
        """Validate streaming response from LLM"""
        chunks_received = 0
        total_content = ""
        for chunk in stream_response:
            chunks_received += 1
            if hasattr(chunk, 'content'):
                total_content += chunk.content
        assert chunks_received > 0
        assert len(total_content) > 50
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=90)
    async def test_llm_streaming_responses(self, llm_manager):
        """Test LLM streaming response functionality"""
        scenario = self._create_streaming_test_scenario()
        stream_response = await llm_manager.generate_stream(
            prompt=scenario["prompt"],
            stream=scenario["stream"],
            max_tokens=scenario["max_tokens"]
        )
        self._validate_streaming_response(stream_response)
        logger.info("LLM streaming test completed successfully")

    def _create_agent_performance_scenario(self):
        """Create agent performance testing scenario"""
        return {
            "concurrent_requests": 3,
            "test_prompts": [
                "Analyze market trends",
                "Optimize supply chain",
                "Generate risk assessment"
            ]
        }

    def _validate_performance_results(self, results, expected_count):
        """Validate agent performance test results"""
        assert len(results) == expected_count
        for result in results:
            assert result is not None
            assert not isinstance(result, Exception)
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=200)  # Extended timeout for concurrent tests
    async def test_agent_performance_under_load(self, agent_service):
        """Test agent performance under concurrent load"""
        scenario = self._create_agent_performance_scenario()
        tasks = [
            agent_service.process_message(prompt, f"perf_user_{i}")
            for i, prompt in enumerate(scenario["test_prompts"])
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        self._validate_performance_results(results, scenario["concurrent_requests"])
        logger.info("Agent performance test completed successfully")

    def _create_error_recovery_scenario(self):
        """Create error recovery test scenario"""
        return {
            "invalid_prompt": "",  # Empty prompt to trigger error
            "recovery_prompt": "Valid recovery prompt for testing"
        }

    def _validate_error_recovery(self, error_result, recovery_result):
        """Validate error recovery behavior"""
        # Should handle error gracefully
        assert error_result is None or isinstance(error_result, Exception)
        # Recovery should succeed
        assert recovery_result is not None
        assert not isinstance(recovery_result, Exception)
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=60)
    async def test_agent_error_recovery(self, agent_service):
        """Test agent error recovery mechanisms"""
        scenario = self._create_error_recovery_scenario()
        
        # Test error handling
        error_result = await agent_service.process_message(
            scenario["invalid_prompt"], "error_test_user"
        )
        
        # Test recovery
        recovery_result = await agent_service.process_message(
            scenario["recovery_prompt"], "error_test_user"
        )
        
        self._validate_error_recovery(error_result, recovery_result)
        logger.info("Agent error recovery test completed successfully")