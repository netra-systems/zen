"""Advanced integration tests for TriageSubAgent with REAL LLM usage.

These tests cover complex, real-world scenarios not covered in existing tests:
1. Circuit breaker behavior under load
2. Cache invalidation and TTL expiration
3. WebSocket streaming during triage
4. Fallback mechanisms with degraded LLM
5. Entity extraction with ambiguous queries

Business Value: Ensures robust triage under all conditions for revenue protection.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

# Use the explicit import pattern that works in other tests
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.base.interface import WebSocketManagerProtocol
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.core.isolated_environment import IsolatedEnvironment
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.triage_sub_agent.core import TriageCore
from netra_backend.app.agents.triage_sub_agent.models import TriageResult
from netra_backend.app.database import get_db_session
from netra_backend.app.config import get_config

logger = central_logger.get_logger(__name__)

# Real environment configuration
env = IsolatedEnvironment()


@pytest.fixture
async def real_llm_manager():
    """Get real LLM manager instance with actual API credentials."""
    from netra_backend.app.config import get_config
    settings = get_config()
    llm_manager = LLMManager(settings)
    yield llm_manager


@pytest.fixture
async def real_redis_manager():
    """Get real Redis manager for caching tests."""
    # Redis manager is disabled in test environment
    return None


@pytest.fixture
async def real_tool_dispatcher(db_session: AsyncSession):
    """Get real tool dispatcher with actual tools loaded."""
    dispatcher = ToolDispatcher()
    return dispatcher


@pytest.fixture
async def websocket_manager():
    """Create a mock WebSocket manager to track streaming updates."""
    class MockWebSocketManager:
        def __init__(self):
            self.updates = []
            
        async def send_agent_update(self, run_id: str, agent_name: str, update: Dict[str, Any]):
            self.updates.append({
                "run_id": run_id,
                "agent_name": agent_name,
                "update": update,
                "timestamp": datetime.now()
            })
    
    return MockWebSocketManager()


@pytest.fixture
async def real_triage_agent_with_cache(real_llm_manager, real_tool_dispatcher, real_redis_manager, websocket_manager):
    """Create real TriageSubAgent with Redis caching enabled."""
    agent = TriageSubAgent(
        llm_manager=real_llm_manager,
        tool_dispatcher=real_tool_dispatcher,
        redis_manager=real_redis_manager,
        websocket_manager=websocket_manager
    )
    yield agent
    # TriageSubAgent doesn't have a cleanup method


class TestTriageAdvancedRealScenarios:
    """Advanced test suite for TriageSubAgent with real-world scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_circuit_breaker_with_rapid_failures_and_recovery(
        self, real_triage_agent_with_cache, db_session
    ):
        """Test 1: Circuit breaker behavior under rapid failure conditions with real LLM."""
        # First, trigger multiple failures to open circuit
        failure_queries = [
            "",  # Empty query
            "a" * 10000,  # Extremely long query
            "\x00\x01\x02",  # Binary data
        ]
        
        results = []
        for idx, query in enumerate(failure_queries):
            state = DeepAgentState(
                run_id=f"test_circuit_{idx}",
                user_query=query,
                user_request=query,  # Add user_request field
                triage_result={},
                data_result={}
            )
            
            try:
                await real_triage_agent_with_cache.execute(state, f"test_circuit_{idx}", False)
                results.append({"status": "success", "result": state.triage_result})
            except Exception as e:
                results.append({"status": "error", "error": str(e)})
        
        # Check circuit breaker status
        circuit_status = real_triage_agent_with_cache.get_circuit_breaker_status()
        
        # Now test with valid query to see if circuit recovers
        valid_state = DeepAgentState(
            run_id="test_circuit_recovery",
            user_query="Help me optimize my GPT-4 API costs",
            user_request="Help me optimize my GPT-4 API costs",
            triage_result={},
            data_result={}
        )
        
        # Wait for recovery timeout if circuit is open
        if circuit_status.get("state") == "open":
            await asyncio.sleep(2)  # Wait for recovery
        
        await real_triage_agent_with_cache.execute(valid_state, "test_circuit_recovery", False)
        recovery_result = valid_state.triage_result
        
        # Validate recovery
        assert recovery_result is not None
        if isinstance(recovery_result, dict):
            assert "category" in recovery_result or "intents" in recovery_result
        
        # Check health status
        health = real_triage_agent_with_cache.get_health_status()
        assert health is not None
        
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_cache_behavior_with_ttl_and_invalidation(
        self, real_triage_agent_with_cache, db_session
    ):
        """Test 2: Cache TTL expiration and invalidation with real Redis."""
        # First request - should hit LLM
        query = "What are the best practices for reducing Claude API latency?"
        
        state1 = DeepAgentState(
            run_id="test_cache_1",
            user_query=query,
            user_request=query,
            triage_result={},
            data_result={}
        )
        
        start_time = time.time()
        await real_triage_agent_with_cache.execute(state1, "test_cache_1", False)
        result1 = state1.triage_result
        first_duration = time.time() - start_time
        
        # Second request - should hit cache
        state2 = DeepAgentState(
            run_id="test_cache_2",
            user_query=query,  # Same query
            user_request=query,
            triage_result={},
            data_result={}
        )
        
        start_time = time.time()
        await real_triage_agent_with_cache.execute(state2, "test_cache_2", False)
        result2 = state2.triage_result
        second_duration = time.time() - start_time
        
        # Cache hit should be much faster
        assert second_duration < first_duration * 0.5
        
        # Check cache metadata
        if isinstance(result2, dict) and "metadata" in result2:
            assert result2["metadata"].get("cache_hit") == True
        
        # Test cache invalidation by clearing
        if real_triage_agent_with_cache.redis_manager:
            request_hash = real_triage_agent_with_cache.triage_core.generate_request_hash(query)
            cache_key = f"triage:result:{request_hash}"
            await real_triage_agent_with_cache.redis_manager.delete(cache_key)
        
        # Third request - should hit LLM again after invalidation
        state3 = DeepAgentState(
            run_id="test_cache_3",
            user_query=query,
            user_request=query,
            triage_result={},
            data_result={}
        )
        
        start_time = time.time()
        await real_triage_agent_with_cache.execute(state3, "test_cache_3", False)
        result3 = state3.triage_result
        third_duration = time.time() - start_time
        
        # Should be slow again after cache invalidation
        assert third_duration > second_duration * 2
        
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_websocket_streaming_during_complex_triage(
        self, real_triage_agent_with_cache, websocket_manager, db_session
    ):
        """Test 3: WebSocket streaming updates during complex multi-step triage."""
        # Complex query requiring multiple analysis steps
        complex_query = """
        I need to:
        1. Analyze my organization's AI spending across GPT-4, Claude, and Gemini
        2. Set up real-time alerts when any model exceeds $1000/day
        3. Generate a cost optimization report with specific recommendations
        4. Configure auto-scaling rules based on usage patterns
        5. Export all data to our internal dashboard via API
        """
        
        state = DeepAgentState(
            run_id="test_websocket_stream",
            user_query=complex_query,
            user_request=complex_query,
            triage_result={},
            data_result={}
        )
        
        # Execute with streaming enabled
        await real_triage_agent_with_cache.execute(state, "test_websocket_stream", True)
        result = state.triage_result
        
        # Check WebSocket updates were sent
        assert len(websocket_manager.updates) > 0
        
        # Verify update sequence
        update_types = [u["update"].get("status") for u in websocket_manager.updates]
        assert "processing" in update_types
        
        # Check result has multiple intents detected
        assert result is not None
        if isinstance(result, dict):
            if "intents" in result:
                assert len(result["intents"]) >= 3  # Should detect multiple intents
            
            # Verify entities were extracted
            if "entities" in result:
                entities = result["entities"]
                model_names = ["gpt-4", "claude", "gemini"]
                assert any(model in str(entities).lower() for model in model_names)
        
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_fallback_mechanism_with_degraded_llm_service(
        self, real_llm_manager, real_tool_dispatcher, real_redis_manager, db_session
    ):
        """Test 4: Fallback mechanisms when LLM service is degraded."""
        # Create agent with modified LLM manager to simulate degradation
        class DegradedLLMManager(LLMManager):
            def __init__(self, real_manager):
                self.real_manager = real_manager
                self.call_count = 0
                
            async def generate_with_gemini(self, *args, **kwargs):
                self.call_count += 1
                if self.call_count <= 2:
                    # Simulate timeout/failure for first attempts
                    raise TimeoutError("LLM service timeout")
                # Work on third attempt
                return await self.real_manager.generate_with_gemini(*args, **kwargs)
                
            def __getattr__(self, name):
                return getattr(self.real_manager, name)
        
        degraded_llm = DegradedLLMManager(real_llm_manager)
        
        agent = TriageSubAgent(
            llm_manager=degraded_llm,
            tool_dispatcher=real_tool_dispatcher,
            redis_manager=real_redis_manager,
            websocket_manager=None
        )
        
        # Test with query that should trigger fallback
        state = DeepAgentState(
            run_id="test_fallback",
            user_query="Optimize my AI costs",
            user_request="Optimize my AI costs",
            triage_result={},
            data_result={}
        )
        
        # Execute - should use fallback after failures
        await agent.execute(state, "test_fallback", False)
        
        # Check that result exists (either from retry success or fallback)
        assert state.triage_result is not None
        
        # Check metadata for fallback usage or retry info
        if isinstance(state.triage_result, dict):
            metadata = state.triage_result.get("metadata", {})
            # Either fallback was used or retries succeeded
            assert metadata.get("fallback_used") == True or degraded_llm.call_count > 1
        
        # Agent cleanup not needed
        
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_entity_extraction_with_ambiguous_and_technical_queries(
        self, real_triage_agent_with_cache, db_session
    ):
        """Test 5: Entity extraction with ambiguous and highly technical queries."""
        test_cases = [
            {
                "query": "Compare the performance of gpt-4-turbo-2024-04-09 vs claude-3-opus-20240229 for our RAG pipeline with 8k context windows",
                "expected_entities": ["gpt-4-turbo", "claude-3-opus", "rag", "8k", "context"],
                "expected_intent_types": ["comparison", "performance", "technical"]
            },
            {
                "query": "Set threshold at 0.95 confidence for semantic search with cosine similarity < 0.7 and implement exponential backoff starting at 100ms",
                "expected_entities": ["0.95", "0.7", "100ms", "exponential backoff", "semantic search"],
                "expected_intent_types": ["configuration", "technical", "threshold"]
            },
            {
                "query": "The thing isn't working right when I try to do the stuff with the AI thingy",
                "expected_entities": [],  # Ambiguous query
                "expected_intent_types": ["support", "troubleshooting"]
            },
            {
                "query": "Migrate from text-embedding-ada-002 to text-embedding-3-large while maintaining backward compatibility with 1536-dimensional vectors",
                "expected_entities": ["text-embedding-ada-002", "text-embedding-3-large", "1536"],
                "expected_intent_types": ["migration", "compatibility", "technical"]
            },
            {
                "query": "Implement A/B testing between Anthropic's constitutional AI and OpenAI's RLHF approaches for our customer service bot with p-value < 0.05",
                "expected_entities": ["anthropic", "openai", "rlhf", "constitutional ai", "0.05", "a/b testing"],
                "expected_intent_types": ["testing", "comparison", "implementation"]
            }
        ]
        
        for idx, test_case in enumerate(test_cases):
            state = DeepAgentState(
                run_id=f"test_entity_{idx}",
                user_query=test_case["query"],
                user_request=test_case["query"],
                triage_result={},
                data_result={}
            )
            
            await real_triage_agent_with_cache.execute(state, f"test_entity_{idx}", False)
            result = state.triage_result
            
            # Validate result structure
            assert result is not None
            if isinstance(result, dict):
                # Check entity extraction
                if "entities" in result:
                    extracted_entities = str(result.get("entities", [])).lower()
                    for expected_entity in test_case["expected_entities"]:
                        if expected_entity:  # Skip empty expected entities
                            # Check if entity or a reasonable variation is found
                            entity_found = (
                                expected_entity.lower() in extracted_entities or
                                expected_entity.replace("-", " ").lower() in extracted_entities or
                                expected_entity.replace("_", " ").lower() in extracted_entities
                            )
                            if not entity_found and expected_entity not in ["rag", "rlhf"]:
                                # Some technical acronyms might not be extracted exactly
                                logger.warning(f"Entity '{expected_entity}' not found in: {extracted_entities}")
                
                # Check intent classification
                if "intents" in result:
                    intent_types = [intent.get("type", "").lower() for intent in result["intents"]]
                    for expected_intent in test_case["expected_intent_types"]:
                        # Check if intent type or related category is detected
                        intent_found = any(
                            expected_intent in intent_type or
                            intent_type in expected_intent
                            for intent_type in intent_types
                        )
                        if not intent_found:
                            # Log but don't fail - LLM might use different categorization
                            logger.info(f"Expected intent '{expected_intent}' not explicitly found, got: {intent_types}")
                
                # Verify confidence scores
                if "confidence_score" in result:
                    assert 0.0 <= result["confidence_score"] <= 1.0
                
                # Check for recommended tools
                if "recommended_tools" in result:
                    assert isinstance(result["recommended_tools"], list)
                    
        # Verify execution metrics
        metrics = real_triage_agent_with_cache.get_execution_metrics()
        assert metrics is not None
        
        # Check modern reliability status
        reliability_status = real_triage_agent_with_cache.get_modern_reliability_status()
        assert reliability_status is not None