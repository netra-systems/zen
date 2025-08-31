"""
LLM Manager Test Helpers - Reusable functions for LLM testing
Extracted from test_llm_manager_provider_switching.py for 25-line function compliance
"""

import asyncio
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type
from unittest.mock import AsyncMock, MagicMock
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


import pytest
from pydantic import BaseModel

from shared.isolated_environment import get_env
from netra_backend.app.schemas.config import AppConfig, LLMConfig

class LLMProvider(Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    MOCK = "mock"

class MockLLMResponse:
    """Mock LLM response for testing"""
    
    def __init__(self, content: str, provider: str = "mock"):
        self.content = content
        self.provider = provider
        self.timestamp = datetime.now(UTC)

def create_mock_app_config() -> AppConfig:
    """Create mock app configuration with environment detection"""
    config = AppConfig()
    config.environment = "testing"
    config.llm_configs = _create_llm_configs()
    
    # Set LLM enabled flag based on environment
    config.dev_mode_llm_enabled = _should_enable_llm()
    
    return config

def _should_enable_llm() -> bool:
    """Determine if LLM should be enabled based on environment"""
    # Check for real LLM markers or API keys
    if _has_real_llm_marker() or _has_api_keys():
        return True
    return False  # Default to mock for faster tests

def _has_real_llm_marker() -> bool:
    """Check if real LLM is explicitly requested"""
    # Check pytest markers or environment flags
    return get_env().get("USE_REAL_LLM", "false").lower() == "true"

def _has_api_keys() -> bool:
    """Check if any LLM API keys are available"""
    api_keys = ["GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    return any(get_env().get(key) for key in api_keys)

def _create_llm_configs() -> Dict[str, LLMConfig]:
    """Create LLM configurations with real or test keys"""
    configs = {}
    
    # OpenAI configuration
    openai_key = get_env().get('GOOGLE_API_KEY', 'test_openai_key')
    configs['openai_gpt4'] = LLMConfig(
        provider='openai', model_name=LLMModel.GEMINI_2_5_FLASH.value, api_key=openai_key
    )
    
    # Google configuration
    google_key = get_env().get('GOOGLE_API_KEY', 'test_google_key')
    configs['google_gemini'] = LLMConfig(
        provider='google', model_name='gemini-pro', api_key=google_key
    )
    
    # Anthropic configuration
    anthropic_key = get_env().get('ANTHROPIC_API_KEY', 'test_anthropic_key')
    configs['anthropic_claude'] = LLMConfig(
        provider='anthropic', model_name=LLMModel.GEMINI_2_5_FLASH.value, api_key=anthropic_key
    )
    
    return configs

def create_mock_providers() -> Dict[str, Any]:
    """Create mock provider clients"""
    from netra_backend.tests.helpers.llm_mock_clients import MockLLMClient
    return {
        'openai_gpt4': MockLLMClient(LLMProvider.OPENAI, LLMModel.GEMINI_2_5_FLASH.value),
        'google_gemini': MockLLMClient(LLMProvider.GOOGLE, 'gemini-pro'),
        'anthropic_claude': MockLLMClient(LLMProvider.ANTHROPIC, LLMModel.GEMINI_2_5_FLASH.value)
    }

def register_providers_with_manager(manager, providers: Dict[str, Any]):
    """Register all providers with manager"""
    for key, client in providers.items():
        provider = LLMProvider(key.split('_')[0])
        manager.register_provider_client(provider, client.model_name, client)

def setup_weighted_load_balancing(manager, weights: Dict[str, float]):
    """Setup weighted load balancing strategy"""
    manager.load_balancing['strategy'] = 'weighted'
    manager.load_balancing['provider_weights'] = weights

def setup_round_robin_load_balancing(manager):
    """Setup round-robin load balancing strategy"""
    manager.load_balancing['strategy'] = 'round_robin'

async def execute_concurrent_requests(manager, count: int, prompt_prefix: str) -> List[Any]:
    """Execute multiple concurrent requests"""
    tasks = [manager.invoke_with_failover(f"{prompt_prefix} {i}") for i in range(count)]
    return await asyncio.gather(*tasks, return_exceptions=True)

def make_providers_fail(providers: Dict[str, Any], provider_keys: List[str]):
    """Make specified providers fail"""
    for key in provider_keys:
        if key in providers:
            providers[key].should_fail = True

def extract_provider_from_response(result) -> Optional[str]:
    """Extract provider name from response content"""
    content = result.content.lower()
    if '[openai]' in content:
        return 'openai'
    elif '[google]' in content:
        return 'google'
    elif '[anthropic]' in content:
        return 'anthropic'
    return None

def count_provider_usage(results: List[Any]) -> Dict[str, int]:
    """Count usage per provider from results"""
    usage = {}
    for result in results:
        if hasattr(result, 'content'):
            provider = extract_provider_from_response(result)
            if provider:
                usage[provider] = usage.get(provider, 0) + 1
    return usage

def assert_health_status(manager, provider_key: str, expected_healthy: bool):
    """Assert provider health status"""
    health_info = manager.provider_health[provider_key]
    assert health_info['healthy'] == expected_healthy

def assert_failure_count(manager, provider_key: str, expected_count: int):
    """Assert provider failure count"""
    health_info = manager.provider_health[provider_key]
    assert health_info['failure_count'] == expected_count

def assert_provider_statistics_format(stats: Dict[str, Any]):
    """Assert provider statistics have correct format"""
    for provider_key, stat in stats.items():
        required_keys = [
            'provider', 'model_name', 'request_count', 
            'successful_requests', 'failed_requests', 
            'success_rate', 'health_status'
        ]
        for key in required_keys:
            assert key in stat

async def simulate_provider_usage_pattern(manager, providers: Dict[str, Any]):
    """Simulate typical provider usage for testing"""
    await _simulate_successful_requests(manager, 5)
    await _simulate_failure_requests(manager, providers, 2)

async def _simulate_successful_requests(manager, count: int):
    """Simulate successful requests"""
    for _ in range(count):
        try:
            await manager.invoke_with_failover("test prompt")
        except:
            pass

async def _simulate_failure_requests(manager, providers: Dict[str, Any], count: int):
    """Simulate failure requests"""
    providers['openai_gpt4'].should_fail = True
    for _ in range(count):
        try:
            await manager.invoke_with_failover("test prompt", 'openai_gpt-4')
        except:
            pass
    providers['openai_gpt4'].should_fail = False