"""
Shared fixtures and utilities for LLM manager integration tests.

BVJ:
- Segment: ALL (Free, Early, Mid, Enterprise) - Core AI functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from LLM integration failures
- Value Impact: Ensures agent request → LLM call → response handling → error recovery
- Revenue Impact: Prevents customer AI requests from failing due to broken LLM integration
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Set testing environment
import os
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MockLLMProvider:
    """Mock LLM provider for testing LLM manager integration."""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.request_count = 0
        self.total_tokens_used = 0
        self.response_times = []
        self.error_rate = 0.0
        self.failure_modes = {}
        self.rate_limit_count = 0
        
    async def generate_response(self, prompt: str, model: str = "gpt-4", **kwargs) -> Dict[str, Any]:
        """Generate LLM response with realistic behavior."""
        self.request_count += 1
        start_time = time.time()
        
        processing_time = 0.1 + (len(prompt) / 1000)
        await asyncio.sleep(min(processing_time, 3.0))
        
        response_time = time.time() - start_time
        self.response_times.append(response_time)
        
        if self.error_rate > 0 and (self.request_count % int(1/self.error_rate)) == 0:
            if "rate_limit" in self.failure_modes:
                self.rate_limit_count += 1
                raise Exception("Rate limit exceeded")
            elif "timeout" in self.failure_modes:
                raise Exception("Request timeout")
            else:
                raise Exception("LLM provider error")
        
        response_content = self._generate_contextual_response(prompt)
        prompt_tokens = len(prompt.split())
        completion_tokens = len(response_content.split())
        total_tokens = prompt_tokens + completion_tokens
        
        self.total_tokens_used += total_tokens
        
        return {
            "content": response_content,
            "model": model,
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total_tokens},
            "finish_reason": "stop",
            "response_time": response_time,
            "provider": self.provider_name
        }
    
    def _generate_contextual_response(self, prompt: str) -> str:
        """Generate contextual response based on prompt content."""
        prompt_lower = prompt.lower()
        
        if "triage" in prompt_lower or "route" in prompt_lower:
            return "Based on your request, I'll route this to the optimization specialist."
        elif "optimization" in prompt_lower or "performance" in prompt_lower:
            return "GPU optimization analysis: Current usage shows 24GB peak allocation. Recommended strategies: gradient checkpointing, mixed precision training."
        elif "data" in prompt_lower or "analysis" in prompt_lower:
            return "Data analysis results: Query latency improved from 450ms to 180ms (60% improvement)."
        else:
            return "I understand your request and I'm here to help with AI workload optimization."


class MockLLMManagerWithIntegration(LLMManager):
    """Mock LLM manager with provider integration and fallback handling."""
    
    def __init__(self):
        self.providers = {
            "openai": MockLLMProvider("openai"),
            "anthropic": MockLLMProvider("anthropic"),
            "azure": MockLLMProvider("azure")
        }
        self.primary_provider = "openai"
        self.fallback_providers = ["anthropic", "azure"]
        self.request_metrics = {
            "total_requests": 0, "successful_requests": 0, "failed_requests": 0,
            "fallback_usage": 0, "avg_response_time": 0, "total_tokens_used": 0
        }
        self.circuit_breaker_state = {}
    
    async def generate_response(self, prompt: str, agent_type: str = "general", **kwargs) -> Dict[str, Any]:
        """Generate response with provider fallback and error handling."""
        self.request_metrics["total_requests"] += 1
        
        for provider_name in [self.primary_provider] + self.fallback_providers:
            try:
                provider = self.providers[provider_name]
                response = await provider.generate_response(prompt, **kwargs)
                
                if provider_name != self.primary_provider:
                    self.request_metrics["fallback_usage"] += 1
                
                self.request_metrics["successful_requests"] += 1
                self.request_metrics["total_tokens_used"] += response["usage"]["total_tokens"]
                
                return response
                
            except Exception as e:
                continue
        
        self.request_metrics["failed_requests"] += 1
        raise Exception("All LLM providers failed")


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider."""
    return MockLLMProvider("test_provider")


@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager with integration."""
    return MockLLMManagerWithIntegration()


@pytest.fixture
def llm_test_agent(mock_llm_manager):
    """Create test agent with LLM manager."""
    class TestAgent(BaseSubAgent):
        def __init__(self, llm_manager):
            super().__init__(llm_manager, name="test_agent")
    
    return TestAgent(mock_llm_manager)