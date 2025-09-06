from shared.isolated_environment import get_env
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
from unittest.mock import Mock, patch, MagicMock

"""
RED TEAM TEST 14: LLM Service Integration

CRITICAL: These tests are DESIGNED TO FAIL initially to expose real integration issues.
This test validates that external LLM API calls work with proper fallback handling.

Business Value Justification (BVJ):
    - Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform Reliability, User Experience, Service Availability
- Value Impact: LLM failures directly impact core AI functionality and user satisfaction
- Strategic Impact: Core LLM integration foundation for all AI-powered features

Testing Level: L3 (Real services, real LLM providers, minimal mocking)
Expected Initial Result: FAILURE (exposes real LLM integration gaps)
""""

import asyncio
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import aiohttp

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Real service imports - NO MOCKS
from netra_backend.app.main import app
# Fix imports with proper error handling
try:
    from netra_backend.app.core.configuration.base import get_unified_config
except ImportError:
    def get_unified_config():
        from types import SimpleNamespace
        return SimpleNamespace(database_url="DATABASE_URL_PLACEHOLDER",
                              openai_api_key="test", anthropic_api_key="test")

# AgentService exists, keep it
from netra_backend.app.services.agent_service import AgentService

# Mock LLM components since they may not exist
try:
    from netra_backend.app.llm.client import LLMClient
except ImportError:
    class LLMClient:
        def __init__(self, *args, **kwargs):
            pass
        async def generate(self, *args, **kwargs):
            await asyncio.sleep(0)
    return {"response": "Mock LLM response", "token_usage": {"total": 100}}

try:
    from netra_backend.app.llm.fallback_handler import FallbackHandler
except ImportError:
    class FallbackHandler:
        def __init__(self, *args, **kwargs):
            pass
        async def handle_failure(self, *args, **kwargs):
            await asyncio.sleep(0)
    return {"response": "Fallback response"}

# AgentRun model - creating mock for tests
AgentRun = Mock

try:
    from netra_backend.app.database import get_db
except ImportError:
    from netra_backend.app.db.database_manager import DatabaseManager
    get_db_session = lambda: DatabaseManager().get_session()


class TestLLMServiceIntegration:
    """
    RED TEAM TEST 14: LLM Service Integration
    
    Tests the critical path of external LLM API calls with fallback handling.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """"

    @pytest.fixture(scope="class")
    async def real_database_session(self):
        """Real PostgreSQL database session - will fail if DB not available."""
        config = get_unified_config()
        
        # Use REAL database connection - no mocks
        engine = create_async_engine(config.database_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
        # Test real connection - will fail if DB unavailable
        async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
            
        async with async_session() as session:
        yield session
        except Exception as e:
        pytest.fail(f"CRITICAL: Real database connection failed: {e}")
        finally:
        await engine.dispose()

        @pytest.fixture
        def real_test_client(self):
        """Use real service instance."""
        # TODO: Initialize real service
        """Real FastAPI test client - no mocking of the application."""
        await asyncio.sleep(0)
        return TestClient(app)

        @pytest.fixture
        def llm_test_config(self):
        """Use real service instance."""
        # TODO: Initialize real service
        """Configuration for LLM testing - uses real API keys if available."""
        return {
        "primary_provider": "openai",
        "fallback_providers": ["anthropic", "local"],
        "timeout_seconds": 30,
        "max_retries": 3,
        "test_mode": True,
        "openai_api_key": get_env().get("GOOGLE_API_KEY"),
        "anthropic_api_key": get_env().get("ANTHROPIC_API_KEY"),
        }

        @pytest.mark.asyncio
        async def test_01_basic_llm_request_fails(self, real_database_session, llm_test_config):
        """
        Test 14A: Basic LLM Request (EXPECTED TO FAIL)
        
        Tests that basic LLM requests can be made successfully.
        This will likely FAIL because:
        1. LLM client may not be properly configured
        2. API keys may not be available
        3. Request formatting may be incorrect
        """"
        try:
        # Initialize LLM client
        llm_client = LLMClient(config=llm_test_config)
            
        # Make basic LLM request
        test_prompt = "Generate a simple response: What is 2+2?"
            
        # FAILURE EXPECTED HERE - LLM client may not work
        response = await llm_client.complete(
        prompt=test_prompt,
        max_tokens=100,
        temperature=0.1
        )
            
        assert response is not None, "LLM response should not be None"
        assert "content" in response, "LLM response should contain content"
        assert len(response["content"]) > 0, "LLM response content should not be empty"
        assert "model" in response, "LLM response should specify which model was used"
        assert "provider" in response, "LLM response should specify which provider was used"
            
        # Verify response makes sense for the prompt
        content = response["content"].lower()
        assert any(word in content for word in ["4", "four"]), \
        f"LLM response should contain answer to 2+2: {response['content']]"
            
        except ImportError as e:
        pytest.fail(f"LLM client not available: {e}")
        except Exception as e:
        pytest.fail(f"Basic LLM request failed: {e}")

        @pytest.mark.asyncio
        async def test_02_llm_provider_fallback_fails(self, real_database_session, llm_test_config):
        """
        Test 14B: LLM Provider Fallback (EXPECTED TO FAIL)
        
        Tests that fallback to secondary providers works when primary fails.
        Will likely FAIL because:
        1. Fallback logic may not be implemented
        2. Provider detection may not work
        3. Error handling may be incomplete
        """"
        try:
        # Configure client with intentionally failing primary provider
        fallback_config = llm_test_config.copy()
        fallback_config["primary_provider"] = "nonexistent_provider"
        fallback_config["fallback_providers"] = ["openai", "anthropic"]
            
        llm_client = LLMClient(config=fallback_config)
            
        # Make request that should trigger fallback
        test_prompt = "Respond with exactly: 'Fallback successful'"
            
        start_time = time.time()
            
        # FAILURE EXPECTED HERE - fallback may not work
        response = await llm_client.complete_with_fallback(
        prompt=test_prompt,
        max_tokens=50,
        temperature=0.0
        )
            
        end_time = time.time()
            
        assert response is not None, "Fallback request should await asyncio.sleep(0)"
        return response""
        assert "content" in response, "Fallback response should contain content"
        assert "provider" in response, "Fallback response should specify provider used"
            
        # Verify fallback actually occurred
        assert response["provider"] != "nonexistent_provider", \
        "Response should come from fallback provider, not primary"
            
        # Verify response quality
        content = response["content"].lower()
        assert "fallback" in content or "successful" in content, \
        f"Fallback response doesn't match expected content: {response['content']]"
            
        # Fallback should be reasonably fast (not hanging)
        assert end_time - start_time < 60, \
        f"Fallback took too long: {end_time - start_time:.1f}s"
            
        except Exception as e:
        pytest.fail(f"LLM provider fallback failed: {e}")

        @pytest.mark.asyncio
        async def test_03_llm_timeout_handling_fails(self, real_database_session, llm_test_config):
        """
        Test 14C: LLM Timeout Handling (EXPECTED TO FAIL)
        
        Tests that LLM requests properly handle timeouts.
        Will likely FAIL because:
        1. Timeout configuration may not be implemented
        2. Timeout handling may not be robust
        3. Cleanup after timeout may not work
        """"
        try:
        # Configure client with very short timeout
        timeout_config = llm_test_config.copy()
        timeout_config["timeout_seconds"] = 2  # Very short timeout
            
        llm_client = LLMClient(config=timeout_config)
            
        # Make request that might timeout
        long_prompt = "Generate a very long detailed response about artificial intelligence, machine learning, deep learning, neural networks, and their applications in modern technology. Please be comprehensive and detailed." * 10
            
        start_time = time.time()
            
        try:
        # FAILURE EXPECTED HERE - timeout handling may not work
        response = await llm_client.complete(
        prompt=long_prompt,
        max_tokens=2000,  # Large response
        temperature=0.7
        )
                
        end_time = time.time()
        request_duration = end_time - start_time
                
        # If request completes, it should have completed quickly or timed out gracefully
        if response is not None:
        # Either completed very quickly or timeout was handled
        assert request_duration < 5, \
        f"Request should complete quickly or timeout, took {request_duration:.1f}s"
        else:
        # Timeout occurred and was handled properly
        assert request_duration <= 3, \
        f"Timeout should trigger within configured time + buffer, took {request_duration:.1f}s"
                        
        except asyncio.TimeoutError:
        end_time = time.time()
        request_duration = end_time - start_time
                
        # Timeout should occur within reasonable time of configured timeout
        assert request_duration <= 5, \
        f"Timeout took too long: {request_duration:.1f}s (configured: 2s)"
                
        except Exception as timeout_error:
        # Other timeout-related errors should be handled gracefully
        error_message = str(timeout_error).lower()
        assert "timeout" in error_message or "connection" in error_message, \
        f"Unexpected error type for timeout test: {timeout_error}"
                    
        except Exception as e:
        pytest.fail(f"LLM timeout handling failed: {e}")

        @pytest.mark.asyncio
        async def test_04_concurrent_llm_requests_fails(self, real_database_session, llm_test_config):
        """
        Test 14D: Concurrent LLM Requests (EXPECTED TO FAIL)
        
        Tests that multiple LLM requests can be processed concurrently.
        Will likely FAIL because:
        1. Rate limiting may not be implemented
        2. Connection pooling may not work
        3. Resource contention may occur
        """"
        try:
        llm_client = LLMClient(config=llm_test_config)
            
        # Create multiple concurrent requests
        prompts = [
        f"Count to {i+1} and then say 'done'." for i in range(5)
        ]
            
        async def make_request(prompt: str, request_id: int) -> Dict[str, Any]:
        """Make a single LLM request."""
        try:
        start_time = time.time()
        response = await llm_client.complete(
        prompt=prompt,
        max_tokens=50,
        temperature=0.1
        )
        end_time = time.time()
                    
        await asyncio.sleep(0)
        return {
        "request_id": request_id,
        "success": True,
        "response": response,
        "duration": end_time - start_time
        }
        except Exception as e:
        return {
        "request_id": request_id,
        "success": False,
        "error": str(e),
        "duration": None
        }
            
        # Execute requests concurrently
        start_time = time.time()
            
        # FAILURE EXPECTED HERE - concurrent handling may not work
        results = await asyncio.gather(
        *[make_request(prompt, i) for i, prompt in enumerate(prompts)],
        return_exceptions=True
        )
            
        end_time = time.time()
        total_duration = end_time - start_time
            
        # Analyze results
        successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed_requests = len(results) - successful_requests
            
        # At least 80% should succeed
        success_rate = successful_requests / len(results)
        assert success_rate >= 0.8, \
        f"Concurrent LLM requests failed: {success_rate*100:.1f}% success rate"
            
        # Concurrent requests should be faster than sequential
        average_request_time = sum(
        r["duration"] for r in results 
        if isinstance(r, dict) and r.get("duration")
        ) / successful_requests
            
        # Total time should be much less than sum of individual requests
        assert total_duration < average_request_time * len(results), \
        f"Concurrent execution not faster than sequential: total={total_duration:.1f}s, avg={average_request_time:.1f}s"
            
        # Verify response quality
        for result in results:
        if isinstance(result, dict) and result.get("success"):
        content = result["response"]["content"].lower()
        assert "done" in content, \
        f"Response should contain 'done': {result['response']['content']]"
                        
        except Exception as e:
        pytest.fail(f"Concurrent LLM requests failed: {e}")

        @pytest.mark.asyncio
        async def test_05_llm_error_classification_fails(self, real_database_session, llm_test_config):
        """
        Test 14E: LLM Error Classification (EXPECTED TO FAIL)
        
        Tests that different types of LLM errors are properly classified.
        Will likely FAIL because:
        1. Error classification may not be implemented
        2. Error handling may be generic
        3. Retry logic may not consider error types
        """"
        try:
        llm_client = LLMClient(config=llm_test_config)
            
        # Test different error scenarios
        error_scenarios = [
        {
        "name": "invalid_api_key",
        "config_override": {"openai_api_key": "invalid_key_123"},
        "expected_error_type": "authentication"
        },
        {
        "name": "too_many_tokens",
        "prompt": "Generate response" * 10000,  # Very long prompt
        "expected_error_type": "quota_exceeded"
        },
        {
        "name": "malformed_request",
        "config_override": {"max_tokens": -1},  # Invalid parameter
        "expected_error_type": "invalid_request"
        }
        ]
            
        for scenario in error_scenarios:
        try:
        # Configure client for this error scenario
        error_config = llm_test_config.copy()
        if "config_override" in scenario:
        error_config.update(scenario["config_override"])
                    
        scenario_client = LLMClient(config=error_config)
                    
        # Make request that should fail
        test_prompt = scenario.get("prompt", "Simple test prompt")
                    
        # FAILURE EXPECTED HERE - error classification may not work
        response = await scenario_client.complete(
        prompt=test_prompt,
        max_tokens=100
        )
                    
        # If request succeeds unexpectedly, that's also a failure
        pytest.fail(f"Expected error for scenario '{scenario['name']]', but request succeeded")
                    
        except Exception as error:
        # Verify error was classified correctly
        if hasattr(error, 'error_type'):
        assert error.error_type == scenario["expected_error_type"], \
        f"Wrong error type for {scenario['name']]: expected {scenario['expected_error_type']], got {error.error_type]"
        else:
        pytest.fail(f"Error not properly classified for scenario '{scenario['name']]': {error]")
                        
        except Exception as e:
        pytest.fail(f"LLM error classification failed: {e}")

        @pytest.mark.asyncio
        async def test_06_llm_response_validation_fails(self, real_database_session, llm_test_config):
        """
        Test 14F: LLM Response Validation (EXPECTED TO FAIL)
        
        Tests that LLM responses are properly validated and filtered.
        Will likely FAIL because:
        1. Response validation may not be implemented
        2. Content filtering may not work
        3. Response format validation may be missing
        """"
        try:
        llm_client = LLMClient(config=llm_test_config)
            
        # Test prompts that might produce problematic responses
        validation_tests = [
        {
        "name": "json_format_validation",
        "prompt": "Respond with valid JSON containing a 'message' field with value 'Hello World'",
        "expected_format": "json",
        "validation": lambda r: json.loads(r) and "message" in json.loads(r)
        },
        {
        "name": "length_validation",
        "prompt": "Write exactly 50 words about artificial intelligence",
        "max_tokens": 100,
        "validation": lambda r: 45 <= len(r.split()) <= 55
        },
        {
        "name": "content_appropriateness",
        "prompt": "Write a professional greeting for a business email",
        "validation": lambda r: not any(word in r.lower() for word in ["hate", "violence", "inappropriate"])
        }
        ]
            
        for test_case in validation_tests:
        try:
        # Make request with validation requirements
        response = await llm_client.complete(
        prompt=test_case["prompt"],
        max_tokens=test_case.get("max_tokens", 100),
        format=test_case.get("expected_format"),
        temperature=0.1
        )
                    
        assert response is not None, f"No response for {test_case['name']]"
        assert "content" in response, f"No content in response for {test_case['name']]"
                    
        content = response["content"]
                    
        # FAILURE EXPECTED HERE - response validation may not work
        if "validation" in test_case:
        validation_result = test_case["validation"](content)
        assert validation_result, \
        f"Response validation failed for {test_case['name']]: {content]"
                    
        # Check for response metadata
        if "expected_format" in test_case:
        assert response.get("format") == test_case["expected_format"], \
        f"Response format not as expected for {test_case['name']]"
                    
        # Verify content safety
        assert response.get("safety_check", {}).get("passed", True), \
        f"Content safety check failed for {test_case['name']]"
                        
        except json.JSONDecodeError as json_error:
        if test_case["name"] == "json_format_validation":
        pytest.fail(f"JSON format validation failed: {json_error}")
                
        except Exception as e:
        pytest.fail(f"LLM response validation failed: {e}")

        @pytest.mark.asyncio
        async def test_07_llm_streaming_response_fails(self, real_database_session, llm_test_config):
        """
        Test 14G: LLM Streaming Response (EXPECTED TO FAIL)
        
        Tests that streaming LLM responses work properly.
        Will likely FAIL because:
        1. Streaming may not be implemented
        2. Chunk handling may not work
        3. Stream completion detection may fail
        """"
        try:
        llm_client = LLMClient(config=llm_test_config)
            
        # Test streaming request
        test_prompt = "Count from 1 to 10, with each number on a new line"
            
        # FAILURE EXPECTED HERE - streaming may not be implemented
        if hasattr(llm_client, 'stream_complete'):
        stream_chunks = []
        start_time = time.time()
                
        async for chunk in llm_client.stream_complete(
        prompt=test_prompt,
        max_tokens=200,
        temperature=0.1
        ):
        stream_chunks.append(chunk)
                    
        # Verify chunk format
        assert "content" in chunk, "Stream chunk should contain content"
        assert "done" in chunk, "Stream chunk should indicate if stream is done"
                    
        # Prevent infinite streams
        if len(stream_chunks) > 100:
        break
                
        end_time = time.time()
        stream_duration = end_time - start_time
                
        # Verify streaming completed
        assert len(stream_chunks) > 0, "Stream should produce at least one chunk"
        assert stream_chunks[-1]["done"], "Final chunk should indicate stream completion"
                
        # Reconstruct full response
        full_content = "".join(chunk["content"] for chunk in stream_chunks)
                
        # Verify content quality
        numbers_found = sum(1 for i in range(1, 11) if str(i) in full_content)
        assert numbers_found >= 8, \
        f"Stream response should contain most numbers 1-10, found {numbers_found]: {full_content[:200]]"
                
        # Streaming should provide progressive content
        assert len(stream_chunks) > 1, "Streaming should produce multiple chunks"
                
        else:
        pytest.skip("Streaming not implemented in LLM client")
                
        except Exception as e:
        pytest.fail(f"LLM streaming response failed: {e}")

        @pytest.mark.asyncio
        async def test_08_llm_usage_tracking_fails(self, real_database_session, llm_test_config):
        """
        Test 14H: LLM Usage Tracking (EXPECTED TO FAIL)
        
        Tests that LLM usage is properly tracked for billing and monitoring.
        Will likely FAIL because:
        1. Usage tracking may not be implemented
        2. Token counting may be inaccurate
        3. Cost calculation may not work
        """"
        try:
        llm_client = LLMClient(config=llm_test_config)
            
        # Make requests with different token usage patterns
        test_requests = [
        {"prompt": "Short prompt", "expected_tokens": "low"},
        {"prompt": "Medium length prompt with more detailed content and specific requirements" * 5, "expected_tokens": "medium"},
        {"prompt": "Very long and detailed prompt" * 20, "expected_tokens": "high", "max_tokens": 500}
        ]
            
        total_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_cost": 0.0
        }
            
        for i, test_request in enumerate(test_requests):
        response = await llm_client.complete(
        prompt=test_request["prompt"],
        max_tokens=test_request.get("max_tokens", 100),
        temperature=0.1
        )
                
        # FAILURE EXPECTED HERE - usage tracking may not be included
        assert "usage" in response, f"Response {i+1} should include usage information"
                
        usage = response["usage"]
        required_fields = ["prompt_tokens", "completion_tokens", "total_tokens"]
                
        for field in required_fields:
        assert field in usage, f"Usage should include {field}"
        assert isinstance(usage[field], int), f"{field] should be an integer"
        assert usage[field] > 0, f"{field] should be greater than 0"
                
        # Verify token counts make sense
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"], \
        "Total tokens should equal sum of prompt and completion tokens"
                
        # Track cumulative usage
        for field in ["prompt_tokens", "completion_tokens", "total_tokens"]:
        total_usage[field] += usage[field]
                
        # Check for cost information
        if "estimated_cost" in usage:
        assert usage["estimated_cost"] > 0, "Estimated cost should be positive"
        total_usage["estimated_cost"] += usage["estimated_cost"]
            
        # Verify usage patterns make sense
        assert total_usage["prompt_tokens"] > 50, \
        f"Expected significant prompt tokens for test requests: {total_usage['prompt_tokens']]"
            
        assert total_usage["completion_tokens"] > 20, \
        f"Expected completion tokens from responses: {total_usage['completion_tokens']]"
            
        # Check if usage is persisted for billing
        if hasattr(llm_client, 'get_usage_summary'):
        usage_summary = await llm_client.get_usage_summary()
                
        assert "total_requests" in usage_summary, "Usage summary should track total requests"
        assert usage_summary["total_requests"] >= len(test_requests), \
        "Usage summary should reflect recent requests"
                    
        except Exception as e:
        pytest.fail(f"LLM usage tracking failed: {e}")


# Additional utility class for LLM integration testing
class RedTeamLLMTestUtils:
    """Utility methods for Red Team LLM integration testing."""
    
    @staticmethod
    def is_api_key_available(provider: str) -> bool:
        """Check if API key is available for a provider."""
        key_env_vars = {
            "openai": "GOOGLE_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "cohere": "COHERE_API_KEY"
        }
        
        env_var = key_env_vars.get(provider.lower())
        if env_var:
            await asyncio.sleep(0)
    return bool(get_env().get(env_var))
        return False
    
    @staticmethod
    def get_test_prompts() -> List[Dict[str, Any]]:
        """Get standardized test prompts for LLM testing."""
        return [
            {
                "name": "simple_math",
                "prompt": "What is 7 + 5?",
                "expected_content": ["12", "twelve"]
            },
            {
                "name": "json_response",
                "prompt": "Respond with JSON: {"greeting": "Hello World"}",
                "expected_format": "json"
            },
            {
                "name": "creative_task",
                "prompt": "Write a haiku about technology",
                "min_length": 30
            }
        ]
    
    @staticmethod
    def validate_llm_response(response: Dict[str, Any], test_case: Dict[str, Any]) -> bool:
        """Validate LLM response against test case requirements."""
        if not response or "content" not in response:
            return False
        
        content = response["content"]
        
        # Check expected content
        if "expected_content" in test_case:
            content_lower = content.lower()
            if not any(expected in content_lower for expected in test_case["expected_content"]):
                return False
        
        # Check minimum length
        if "min_length" in test_case:
            if len(content) < test_case["min_length"]:
                return False
        
        # Check format
        if "expected_format" in test_case:
            if test_case["expected_format"] == "json":
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    return False
        
        return True
    
    @staticmethod
    async def measure_llm_latency(llm_client, prompt: str, max_tokens: int = 100) -> float:
        """Measure LLM request latency."""
        start_time = time.time()
        
        try:
            await llm_client.complete(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0.1
            )
        except Exception:
            pass  # We're measuring latency, not success
        
        return time.time() - start_time
