"""
Tests for LLM Test Manager - Real LLM testing framework validation

Tests the core functionality of the LLM testing framework including
model support, caching, and intelligent fallback mechanisms.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import os
from unittest.mock import AsyncMock, patch

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.tests.e2e.infrastructure import (

# Add project root to path
    LLMTestManager,
    LLMTestModel,
    LLMTestConfig,
    LLMTestRequest,
    LLMTestResponse
)


@pytest.fixture
def test_config():
    """Create test configuration."""
    return LLMTestConfig(
        enabled=False,  # Use mocks for tests
        models=[LLMTestModel.GPT_4, LLMTestModel.CLAUDE_3_OPUS],
        cache_enabled=True,
        timeout_seconds=10
    )


@pytest.fixture
def llm_manager(test_config):
    """Create LLM test manager with test configuration."""
    return LLMTestManager(test_config)


@pytest.fixture
def sample_request():
    """Create sample LLM test request."""
    return LLMTestRequest(
        prompt="What is the capital of France?",
        model=LLMTestModel.GPT_4,
        temperature=0.7,
        use_cache=True
    )


class TestLLMTestManager:
    """Test suite for LLM Test Manager."""
    
    def test_initialization_with_config(self, test_config):
        """Test manager initialization with configuration."""
        manager = LLMTestManager(test_config)
        assert manager.config == test_config
        assert not manager.is_real_testing_enabled()
        
    def test_environment_config_loading(self):
        """Test loading configuration from environment."""
        with patch.dict(os.environ, {
            "ENABLE_REAL_LLM_TESTING": "true",
            "LLM_TEST_MODELS": "gpt-4,claude-3-opus"
        }):
            manager = LLMTestManager()
            assert manager.config.enabled
            assert LLMTestModel.GPT_4 in manager.config.models
            
    async def test_mock_response_generation(self, llm_manager, sample_request):
        """Test mock response generation when real LLMs disabled."""
        response = await llm_manager.generate_response(sample_request)
        assert isinstance(response, LLMTestResponse)
        assert response.success
        assert response.model_used == sample_request.model
        assert len(response.content) > 0
        
    def test_cache_key_generation(self, llm_manager, sample_request):
        """Test cache key generation consistency."""
        key1 = llm_manager._generate_cache_key(sample_request)
        key2 = llm_manager._generate_cache_key(sample_request)
        assert key1 == key2
        assert len(key1) == 32  # MD5 hash length
        
    def test_available_models(self, llm_manager):
        """Test getting available models."""
        models = llm_manager.get_available_models()
        assert isinstance(models, list)
        assert all(isinstance(model, LLMTestModel) for model in models)
        
    def test_statistics_collection(self, llm_manager):
        """Test statistics collection."""
        stats = llm_manager.get_statistics()
        assert isinstance(stats, dict)
        assert "enabled" in stats
        assert "available_models" in stats
        assert "cache_enabled" in stats
        
    async def test_fallback_behavior(self, llm_manager):
        """Test fallback to mock when real clients unavailable."""
        request = LLMTestRequest(
            prompt="Test fallback",
            model=LLMTestModel.GPT_4,
            use_cache=False
        )
        response = await llm_manager.generate_response(request)
        assert response.success
        assert response.content
        
    def test_real_client_initialization_without_keys(self):
        """Test real client initialization fails without API keys."""
        config = LLMTestConfig(enabled=True, models=[LLMTestModel.GPT_4])
        manager = LLMTestManager(config)
        # Should fallback to mocks when no real API keys
        assert len(manager._clients) > 0  # Mock clients created
        
    async def test_response_time_tracking(self, llm_manager, sample_request):
        """Test response time tracking in responses."""
        response = await llm_manager.generate_response(sample_request)
        assert response.response_time_ms > 0
        assert isinstance(response.response_time_ms, int)


class TestLLMTestRequest:
    """Test suite for LLM Test Request model."""
    
    def test_request_validation(self):
        """Test request model validation."""
        request = LLMTestRequest(
            prompt="Test prompt",
            model=LLMTestModel.GPT_4
        )
        assert request.prompt == "Test prompt"
        assert request.model == LLMTestModel.GPT_4
        assert request.temperature == 0.7  # Default value
        
    def test_invalid_model_rejection(self):
        """Test rejection of invalid model values."""
        with pytest.raises(ValueError):
            LLMTestRequest(
                prompt="Test",
                model="invalid-model"
            )


class TestLLMTestResponse:
    """Test suite for LLM Test Response model."""
    
    def test_response_creation(self):
        """Test response model creation."""
        response = LLMTestResponse(
            content="Test response",
            model_used=LLMTestModel.GPT_4,
            response_time_ms=150
        )
        assert response.content == "Test response"
        assert response.model_used == LLMTestModel.GPT_4
        assert response.response_time_ms == 150
        assert response.success  # Default value
        
    def test_cache_hit_flag(self):
        """Test cache hit flag functionality."""
        response = LLMTestResponse(
            content="Cached response",
            model_used=LLMTestModel.GPT_4,
            response_time_ms=50,
            cache_hit=True
        )
        assert response.cache_hit