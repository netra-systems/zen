"""
Real LLM provider tests with actual API calls.
All functions ≤8 lines per requirements.
"""

import os
import json
import pytest
from app.llm.llm_manager import LLMManager
from .real_services_test_fixtures import skip_if_no_real_services


class TestRealLLMProviders:
    """Test suite for different LLM providers with real API calls"""
    
    @skip_if_no_real_services
    @pytest.mark.parametrize("provider,model", [
        ("openai", "gpt-3.5-turbo"),
        ("anthropic", "claude-3-sonnet"),
        ("google", "gemini-1.5-flash"),
    ])
    async def test_llm_provider_real(self, provider: str, model: str):
        """Test each LLM provider with real API calls"""
        llm = LLMManager()
        
        # Skip if API key not available
        _skip_if_no_api_key(provider)
        
        # Test simple generation
        await _test_simple_generation(llm, model)
        
        # Test structured generation
        await _test_structured_generation(llm, model)
    
    @skip_if_no_real_services
    async def test_openai_specific_features(self):
        """Test OpenAI-specific features"""
        if not os.environ.get("OPENAI_API_KEY"):
            pytest.skip("No OpenAI API key")
        
        llm = LLMManager()
        await _test_openai_features(llm)
    
    @skip_if_no_real_services
    async def test_anthropic_specific_features(self):
        """Test Anthropic-specific features"""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("No Anthropic API key")
        
        llm = LLMManager()
        await _test_anthropic_features(llm)
    
    @skip_if_no_real_services
    async def test_google_specific_features(self):
        """Test Google-specific features"""
        if not os.environ.get("GEMINI_API_KEY"):
            pytest.skip("No Google API key")
        
        llm = LLMManager()
        await _test_google_features(llm)
    
    @skip_if_no_real_services
    async def test_provider_fallback_mechanisms(self):
        """Test fallback between providers"""
        llm = LLMManager()
        
        # Test with primary provider down (simulated)
        response = await llm.generate_with_fallback(
            "Test fallback message",
            primary_model="invalid_model",
            fallback_model="gpt-3.5-turbo"
        )
        
        assert response is not None
    
    @skip_if_no_real_services
    async def test_streaming_responses(self):
        """Test streaming responses from providers"""
        llm = LLMManager()
        
        if not os.environ.get("OPENAI_API_KEY"):
            pytest.skip("No OpenAI API key")
        
        chunks = []
        async for chunk in llm.generate_stream("Count from 1 to 5", model="gpt-3.5-turbo"):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert any("1" in str(chunk) for chunk in chunks)


def _skip_if_no_api_key(provider: str) -> None:
    """Skip test if API key not available"""
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY", 
        "google": "GEMINI_API_KEY"
    }
    
    if not os.environ.get(key_map[provider]):
        pytest.skip(f"No API key for {provider}")


async def _test_simple_generation(llm: LLMManager, model: str) -> None:
    """Test simple text generation"""
    prompt = "What is 2+2? Answer with just the number."
    response = await llm.generate(prompt, model=model)
    
    assert response is not None
    assert "4" in response


async def _test_structured_generation(llm: LLMManager, model: str) -> None:
    """Test structured JSON generation"""
    structured_prompt = "Generate a JSON object with fields: name (string), age (number), active (boolean)"
    structured_response = await llm.generate_structured(
        structured_prompt,
        model=model,
        response_format={"type": "json"}
    )
    
    _verify_structured_response(structured_response)


def _verify_structured_response(structured_response: str) -> None:
    """Verify structured response format"""
    assert structured_response is not None
    parsed = json.loads(structured_response)
    assert "name" in parsed
    assert "age" in parsed
    assert "active" in parsed


async def _test_openai_features(llm: LLMManager) -> None:
    """Test OpenAI-specific features"""
    # Test function calling
    response = await llm.generate_with_functions(
        "What's the weather like?",
        model="gpt-3.5-turbo",
        functions=[_get_weather_function_schema()]
    )
    
    assert response is not None


async def _test_anthropic_features(llm: LLMManager) -> None:
    """Test Anthropic-specific features"""
    # Test with system prompt
    response = await llm.generate(
        "Hello",
        model="claude-3-sonnet",
        system_prompt="You are a helpful assistant."
    )
    
    assert response is not None


async def _test_google_features(llm: LLMManager) -> None:
    """Test Google-specific features"""
    # Test multimodal capabilities (text only for now)
    response = await llm.generate(
        "Describe the concept of machine learning",
        model="gemini-1.5-flash"
    )
    
    assert response is not None
    assert len(response) > 50  # Should be descriptive


def _get_weather_function_schema() -> dict:
    """Get weather function schema for testing"""
    return {
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            }
        }
    }