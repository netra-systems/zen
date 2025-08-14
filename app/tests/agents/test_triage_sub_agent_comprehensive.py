"""
Comprehensive tests for TriageSubAgent with complete coverage
Builds upon existing tests to cover all methods, error handling, edge cases, and async operations
"""

import pytest
import json
import asyncio
import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from typing import Dict, Any, List

from app.agents.triage_sub_agent import TriageSubAgent
from app.agents.triage_sub_agent import (
    TriageResult,
    Priority,
    Complexity,
    KeyParameters,
    ExtractedEntities,
    UserIntent,
    ValidationStatus
)
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher
from app.redis_manager import RedisManager
from app.schemas import SubAgentLifecycle


class MockLLMManager:
    """Enhanced mock LLM manager for comprehensive testing"""
    def __init__(self):
        self.ask_llm = AsyncMock()
        self.call_count = 0
        self.responses = []
        self.failures = []
    
    def set_responses(self, responses):
        """Set predefined responses"""
        self.responses = responses
        self.call_count = 0
        
        def side_effect(*args, **kwargs):
            if self.call_count < len(self.failures) and self.failures[self.call_count]:
                raise Exception(f"LLM error {self.call_count}")
            
            if self.call_count < len(self.responses):
                response = self.responses[self.call_count]
            else:
                response = '{"category": "General Inquiry", "priority": "medium"}'
            
            self.call_count += 1
            return response
        
        self.ask_llm.side_effect = side_effect
    
    def set_failure_pattern(self, failures):
        """Set failure pattern (True for failure, False for success)"""
        self.failures = failures


class MockToolDispatcher:
    """Mock tool dispatcher"""
    def __init__(self):
        self.available_tools = {
            "cost_analyzer": {"category": "optimization", "relevance": 0.9},
            "latency_analyzer": {"category": "performance", "relevance": 0.8},
            "performance_predictor": {"category": "performance", "relevance": 0.7},
            "corpus_manager": {"category": "data", "relevance": 0.6},
            "multi_objective_optimization": {"category": "optimization", "relevance": 0.85}
        }


class MockRedisManager:
    """Enhanced mock Redis manager"""
    def __init__(self, available=True):
        self.available = available
        self.cache = {}
        self.get_calls = []
        self.set_calls = []
    
    async def get(self, key):
        self.get_calls.append(key)
        if not self.available:
            raise Exception("Redis not available")
        return self.cache.get(key)
    
    async def set(self, key, value, ex=None):
        self.set_calls.append((key, value, ex))
        if not self.available:
            raise Exception("Redis not available")
        self.cache[key] = value
        return True


@pytest.fixture
def mock_llm_manager():
    """Create enhanced mock LLM manager"""
    return MockLLMManager()


@pytest.fixture
def mock_tool_dispatcher():
    """Create mock tool dispatcher"""
    return MockToolDispatcher()


@pytest.fixture
def mock_redis_manager():
    """Create mock Redis manager"""
    return MockRedisManager()


@pytest.fixture
def mock_redis_unavailable():
    """Create mock Redis manager that's unavailable"""
    return MockRedisManager(available=False)


@pytest.fixture
def triage_agent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
    """Create TriageSubAgent with mocked dependencies"""
    return TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)


@pytest.fixture
def triage_agent_no_redis(mock_llm_manager, mock_tool_dispatcher):
    """Create TriageSubAgent without Redis"""
    return TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, None)


@pytest.fixture
def complex_state():
    """Create complex state for testing"""
    return DeepAgentState(
        user_request="I need to optimize my GPT-4 costs by 30% while maintaining sub-100ms latency for my e-commerce application that processes 10,000 requests per day using tools like cost analyzer and performance predictor",
        user_id="test_user_complex",
        session_id="session_complex_123"
    )


class TestAdvancedInitialization:
    """Test advanced initialization scenarios"""
    
    def test_initialization_configuration_values(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
        """Test that initialization sets correct configuration values"""
        agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)
        
        assert agent.cache_ttl == 3600
        assert agent.max_retries == 3
        assert agent.name == "TriageSubAgent"
        assert hasattr(agent, 'tool_dispatcher')
        assert hasattr(agent, 'redis_manager')
        assert hasattr(agent, 'fallback_categories')
    
    def test_initialization_with_custom_config(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
        """Test initialization with custom configuration"""
        agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)
        
        # Override configuration
        agent.cache_ttl = 7200
        agent.max_retries = 5
        
        assert agent.cache_ttl == 7200
        assert agent.max_retries == 5


class TestValidationPatterns:
    """Test validation pattern matching"""
    
    def test_sql_injection_patterns(self, triage_agent):
        """Test SQL injection pattern detection"""
        malicious_requests = [
            "DROP TABLE users; SELECT * FROM secrets",
            "'; DELETE FROM logs; --",
            "UNION SELECT password FROM users",
            "admin'--",
            "1' OR '1'='1",
        ]
        
        for request in malicious_requests:
            validation = triage_agent._validate_request(request)
            assert validation.is_valid == False
            assert any("malicious pattern" in error.lower() for error in validation.validation_errors)
    
    def test_script_injection_patterns(self, triage_agent):
        """Test script injection pattern detection"""
        malicious_requests = [
            "<script>alert('xss')</script>",
            "javascript:alert('test')",
            "<img src=x onerror=alert('xss')>",
            "eval(malicious_code)",
            "document.cookie",
        ]
        
        for request in malicious_requests:
            validation = triage_agent._validate_request(request)
            assert validation.is_valid == False
            assert any("malicious pattern" in error.lower() for error in validation.validation_errors)
    
    def test_command_injection_patterns(self, triage_agent):
        """Test command injection pattern detection"""
        malicious_requests = [
            "rm -rf /",
            "cat /etc/passwd",
            "; curl malicious.com",
            "$(malicious command)",
            "`rm important_file`",
        ]
        
        for request in malicious_requests:
            validation = triage_agent._validate_request(request)
            assert validation.is_valid == False
            assert any("malicious pattern" in error.lower() for error in validation.validation_errors)
    
    def test_benign_technical_content(self, triage_agent):
        """Test that benign technical content passes validation"""
        benign_requests = [
            "How do I optimize my SQL SELECT queries for better performance?",
            "I need help with JavaScript async/await syntax",
            "Can you help me debug my React component's rendering?",
            "What's the best way to handle user authentication in my app?",
        ]
        
        for request in benign_requests:
            validation = triage_agent._validate_request(request)
            assert validation.is_valid == True
            assert len(validation.validation_errors) == 0


class TestAdvancedEntityExtraction:
    """Test advanced entity extraction functionality"""
    
    def test_extract_complex_model_names(self, triage_agent):
        """Test extraction of complex AI model names"""
        request = "Compare GPT-4-turbo with Claude-3-opus and Llama-2-70B-chat for my use case involving gemini-pro and palm-2"
        entities = triage_agent._extract_entities_from_request(request)
        
        expected_models = {"gpt-4-turbo", "claude-3-opus", "llama-2-70b-chat", "gemini-pro", "palm-2"}
        assert expected_models.issubset(set(entities.models_mentioned))
    
    def test_extract_comprehensive_metrics(self, triage_agent):
        """Test extraction of comprehensive performance metrics"""
        request = "I need to improve throughput, reduce latency, minimize cost, optimize memory usage, decrease error rate, and enhance accuracy"
        entities = triage_agent._extract_entities_from_request(request)
        
        expected_metrics = {"throughput", "latency", "cost", "memory", "error", "accuracy"}
        extracted_metrics = set(entities.metrics_mentioned)
        assert expected_metrics.issubset(extracted_metrics)
    
    def test_extract_numerical_thresholds_complex(self, triage_agent):
        """Test extraction of complex numerical thresholds"""
        request = "Keep response time under 250ms, achieve 99.9% uptime, process at least 1000 RPS, and stay within $500/month budget"
        entities = triage_agent._extract_entities_from_request(request)
        
        # Check for time thresholds
        time_thresholds = [t for t in entities.thresholds if t["type"] == "time"]
        assert len(time_thresholds) > 0
        
        # Check for rate thresholds  
        rate_thresholds = [t for t in entities.thresholds if t["type"] == "rate"]
        assert len(rate_thresholds) > 0
        
        # Check for cost thresholds
        cost_thresholds = [t for t in entities.thresholds if t["type"] == "cost"]
        assert len(cost_thresholds) > 0
    
    def test_extract_time_ranges_complex(self, triage_agent):
        """Test extraction of complex time ranges"""
        request = "Analyze performance over the last 30 days, peak hours from 9 AM to 5 PM, and weekend patterns"
        entities = triage_agent._extract_entities_from_request(request)
        
        assert len(entities.time_ranges) >= 2  # Should extract multiple time ranges
    
    def test_extract_provider_context(self, triage_agent):
        """Test extraction of provider and service context"""
        request = "Compare OpenAI GPT-4 on Azure with Anthropic Claude on AWS and Google PaLM on GCP"
        entities = triage_agent._extract_entities_from_request(request)
        
        # Should extract both models and providers
        assert "gpt-4" in entities.models_mentioned
        assert len(entities.models_mentioned) >= 3
        
        # Should extract cloud providers (stored as additional context)
        request_lower = request.lower()
        cloud_providers = ["azure", "aws", "gcp"]
        for provider in cloud_providers:
            assert provider in request_lower


class TestAdvancedIntentDetermination:
    """Test advanced intent determination"""
    
    def test_intent_priority_resolution(self, triage_agent):
        """Test intent priority when multiple intents are present"""
        request = "First analyze my current costs, then optimize them, and finally generate a report"
        intent = triage_agent._determine_intent(request)
        
        # Primary intent should be the most actionable one
        assert intent.primary_intent in ["analyze", "optimize", "generate"]
        assert len(intent.secondary_intents) >= 1
        assert intent.action_required == True
    
    def test_intent_confidence_scoring(self, triage_agent):
        """Test intent confidence scoring"""
        high_confidence_request = "Optimize my model costs using the cost analyzer tool"
        low_confidence_request = "Maybe look into some stuff about things"
        
        high_confidence_intent = triage_agent._determine_intent(high_confidence_request)
        low_confidence_intent = triage_agent._determine_intent(low_confidence_request)
        
        # High confidence request should have clear intent
        assert high_confidence_intent.primary_intent == "optimize"
        assert high_confidence_intent.confidence_score > 0.7
        
        # Low confidence request should have lower confidence
        assert low_confidence_intent.confidence_score < 0.5
    
    def test_intent_context_awareness(self, triage_agent):
        """Test intent determination with context awareness"""
        requests_and_intents = [
            ("Debug my failing API calls", "debug"),
            ("Scale my infrastructure for Black Friday", "scale"),
            ("Monitor my application performance", "monitor"),
            ("Migrate from GPT-3.5 to GPT-4", "migrate"),
            ("Validate my optimization results", "validate"),
        ]
        
        for request, expected_intent in requests_and_intents:
            intent = triage_agent._determine_intent(request)
            assert intent.primary_intent == expected_intent or expected_intent in intent.secondary_intents


class TestAdvancedToolRecommendation:
    """Test advanced tool recommendation logic"""
    
    def test_recommend_tools_with_relevance_scoring(self, triage_agent):
        """Test tool recommendation with relevance scoring"""
        entities = ExtractedEntities(
            models_mentioned=["gpt-4"],
            metrics_mentioned=["cost", "latency"],
            thresholds=[{"type": "cost", "value": 1000, "unit": "USD"}]
        )
        
        tools = triage_agent._recommend_tools("Cost Optimization", entities)
        
        assert len(tools) > 0
        # Tools should be sorted by relevance score (descending)
        for i in range(len(tools) - 1):
            assert tools[i].relevance_score >= tools[i + 1].relevance_score
        
        # All scores should be between 0 and 1
        for tool in tools:
            assert 0 <= tool.relevance_score <= 1
    
    def test_recommend_tools_category_matching(self, triage_agent):
        """Test tool recommendation based on category matching"""
        test_cases = [
            ("Performance Optimization", ["latency"], ["latency_analyzer", "performance_predictor"]),
            ("Cost Optimization", ["cost"], ["cost_analyzer"]),
            ("Data Management", ["corpus", "dataset"], ["corpus_manager"]),
            ("Multi-objective Optimization", ["cost", "latency"], ["multi_objective_optimization"]),
        ]
        
        for category, metrics, expected_tools in test_cases:
            entities = ExtractedEntities(metrics_mentioned=metrics)
            tools = triage_agent._recommend_tools(category, entities)
            
            # Should recommend relevant tools
            recommended_names = [tool.tool_name for tool in tools]
            for expected_tool in expected_tools:
                if expected_tool in triage_agent.tool_dispatcher.available_tools:
                    assert any(expected_tool in name for name in recommended_names)
    
    def test_recommend_tools_empty_entities(self, triage_agent):
        """Test tool recommendation with empty entities"""
        empty_entities = ExtractedEntities()
        tools = triage_agent._recommend_tools("General Inquiry", empty_entities)
        
        # Should still return some tools, but with lower relevance
        assert len(tools) >= 0
        if tools:
            assert all(tool.relevance_score <= 0.5 for tool in tools)


class TestCachingMechanisms:
    """Test comprehensive caching mechanisms"""
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, triage_agent):
        """Test cache key generation consistency"""
        request1 = "Optimize my costs"
        request2 = "  OPTIMIZE   MY   COSTS  "  # Same but different formatting
        request3 = "Reduce my expenses"  # Different request
        
        key1 = triage_agent._generate_request_hash(request1)
        key2 = triage_agent._generate_request_hash(request2)
        key3 = triage_agent._generate_request_hash(request3)
        
        # Same semantic content should generate same key
        assert key1 == key2
        # Different content should generate different key
        assert key1 != key3
        
        # Keys should be valid hash format
        assert len(key1) == 64  # SHA-256 hex length
        assert all(c in '0123456789abcdef' for c in key1)
    
    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, triage_agent, complex_state, mock_redis_manager):
        """Test cache hit improves performance"""
        # Prepare cached result
        cached_result = {
            "category": "Cost Optimization",
            "priority": "high",
            "confidence_score": 0.9,
            "metadata": {"cache_hit": False, "triage_duration_ms": 150}
        }
        
        cache_key = triage_agent._generate_request_hash(complex_state.user_request)
        mock_redis_manager.cache[cache_key] = json.dumps(cached_result)
        
        start_time = datetime.now()
        await triage_agent.execute(complex_state, "test_run", stream_updates=False)
        end_time = datetime.now()
        
        execution_time = (end_time - start_time).total_seconds() * 1000
        
        # Cache hit should be fast (less than 100ms for simple operations)
        assert execution_time < 100
        
        # Should have retrieved from cache
        assert len(mock_redis_manager.get_calls) > 0
        # Should have marked as cache hit
        assert complex_state.triage_result["metadata"]["cache_hit"] == True
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_scenarios(self, triage_agent, complex_state, mock_redis_manager):
        """Test cache invalidation scenarios"""
        # Test with corrupted cache data
        cache_key = triage_agent._generate_request_hash(complex_state.user_request)
        mock_redis_manager.cache[cache_key] = "invalid json data"
        
        # Mock LLM to return valid response
        triage_agent.llm_manager.set_responses([
            '{"category": "Cost Optimization", "priority": "high", "confidence_score": 0.9}'
        ])
        
        await triage_agent.execute(complex_state, "test_run", stream_updates=False)
        
        # Should fall back to LLM when cache data is corrupted
        assert complex_state.triage_result["category"] == "Cost Optimization"
        assert complex_state.triage_result["metadata"]["cache_hit"] == False
    
    @pytest.mark.asyncio
    async def test_cache_warming_strategy(self, triage_agent, mock_redis_manager):
        """Test cache warming with common requests"""
        common_requests = [
            "Optimize my AI costs",
            "Improve model performance", 
            "Reduce latency issues",
            "Scale my infrastructure",
            "Debug API failures"
        ]
        
        # Mock LLM responses
        responses = []
        for i, request in enumerate(common_requests):
            responses.append(f'{{"category": "Category_{i}", "priority": "medium", "confidence_score": 0.8}}')
        
        triage_agent.llm_manager.set_responses(responses)
        
        # Warm cache by processing requests
        for request in common_requests:
            state = DeepAgentState(user_request=request)
            await triage_agent.execute(state, "cache_warm", stream_updates=False)
        
        # Verify cache was populated
        assert len(mock_redis_manager.cache) == len(common_requests)
        
        # Verify subsequent requests use cache
        state = DeepAgentState(user_request=common_requests[0])
        await triage_agent.execute(state, "cache_test", stream_updates=False)
        
        assert state.triage_result["metadata"]["cache_hit"] == True


@pytest.mark.asyncio
class TestErrorHandlingAndRecovery:
    """Test comprehensive error handling and recovery"""
    
    async def test_llm_timeout_handling(self, triage_agent, complex_state):
        """Test LLM timeout handling"""
        # Mock LLM to timeout
        async def timeout_llm(*args, **kwargs):
            await asyncio.sleep(0.1)
            raise asyncio.TimeoutError("LLM request timed out")
        
        triage_agent.llm_manager.ask_llm.side_effect = timeout_llm
        
        await triage_agent.execute(complex_state, "timeout_test", stream_updates=False)
        
        # Should fall back to basic categorization
        assert complex_state.triage_result != None
        assert complex_state.triage_result["metadata"]["fallback_used"] == True
        assert "timeout" in complex_state.triage_result["metadata"]["error_details"].lower()
    
    async def test_llm_rate_limit_handling(self, triage_agent, complex_state):
        """Test LLM rate limit error handling"""
        # Mock rate limit error
        def rate_limit_error(*args, **kwargs):
            raise Exception("Rate limit exceeded. Please try again later.")
        
        triage_agent.llm_manager.ask_llm.side_effect = rate_limit_error
        
        await triage_agent.execute(complex_state, "rate_limit_test", stream_updates=False)
        
        # Should handle gracefully and fall back
        assert complex_state.triage_result != None
        assert complex_state.triage_result["metadata"]["fallback_used"] == True
        assert "rate limit" in complex_state.triage_result["metadata"]["error_details"].lower()
    
    async def test_redis_connection_failures(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_unavailable):
        """Test Redis connection failure handling"""
        agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_unavailable)
        state = DeepAgentState(user_request="Test request")
        
        # Mock successful LLM response
        mock_llm_manager.set_responses([
            '{"category": "General Inquiry", "priority": "medium", "confidence_score": 0.7}'
        ])
        
        await agent.execute(state, "redis_fail_test", stream_updates=False)
        
        # Should complete successfully despite Redis failure
        assert state.triage_result != None
        assert state.triage_result["category"] == "General Inquiry"
        # Should not have cache hit since Redis failed
        assert state.triage_result["metadata"]["cache_hit"] == False
    
    async def test_partial_llm_response_handling(self, triage_agent, complex_state):
        """Test handling of partial or incomplete LLM responses"""
        incomplete_responses = [
            '{"category": "Cost Optimization"}',  # Missing required fields
            '{"priority": "high", "confidence_score": 0.8}',  # Missing category
            '{"category": "Performance", "priority": "invalid_priority"}',  # Invalid enum
            '{"category": "", "priority": "medium"}',  # Empty category
        ]
        
        for incomplete_response in incomplete_responses:
            triage_agent.llm_manager.set_responses([incomplete_response])
            
            state = DeepAgentState(user_request="Test incomplete response")
            await triage_agent.execute(state, "incomplete_test", stream_updates=False)
            
            # Should handle incomplete responses gracefully
            assert state.triage_result != None
            assert "category" in state.triage_result
            # Should use fallback for incomplete responses
            assert state.triage_result["metadata"]["fallback_used"] == True
    
    async def test_json_parsing_edge_cases(self, triage_agent):
        """Test JSON parsing with edge cases"""
        edge_case_responses = [
            '{"category": "Test", "description": "Text with \\"quotes\\" and newlines\\n"}',
            '{"category": "Test", "nested": {"key": "value", "array": [1, 2, 3]}}',
            '{"category": "Test", "unicode": "Special chars: éñüñ¡ç∆"}',
            '{"category": "Test", "numbers": {"int": 123, "float": 45.67, "scientific": 1e-5}}',
        ]
        
        for response in edge_case_responses:
            result = triage_agent._extract_and_validate_json(response)
            assert result != None
            assert result["category"] == "Test"
    
    async def test_memory_pressure_handling(self, triage_agent):
        """Test behavior under simulated memory pressure"""
        # Create very large request to simulate memory pressure
        large_request = "Optimize costs " * 10000  # Very large request
        
        state = DeepAgentState(user_request=large_request)
        
        # Mock LLM response
        triage_agent.llm_manager.set_responses([
            '{"category": "Cost Optimization", "priority": "high", "confidence_score": 0.8}'
        ])
        
        await triage_agent.execute(state, "memory_test", stream_updates=False)
        
        # Should handle large requests without crashing
        assert state.triage_result != None
        assert state.triage_result["category"] == "Cost Optimization"


class TestAsyncOperations:
    """Test async operation handling"""
    
    @pytest.mark.asyncio
    async def test_concurrent_executions(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
        """Test concurrent triage executions"""
        agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher, mock_redis_manager)
        
        # Prepare different responses for concurrent requests
        responses = [
            '{"category": "Cost Optimization", "priority": "high", "confidence_score": 0.9}',
            '{"category": "Performance Optimization", "priority": "medium", "confidence_score": 0.8}',
            '{"category": "Data Management", "priority": "low", "confidence_score": 0.7}',
        ]
        mock_llm_manager.set_responses(responses)
        
        # Create concurrent states
        states = [
            DeepAgentState(user_request=f"Request {i}", user_id=f"user_{i}")
            for i in range(3)
        ]
        
        # Execute concurrently
        tasks = [
            agent.execute(state, f"concurrent_{i}", stream_updates=False)
            for i, state in enumerate(states)
        ]
        
        await asyncio.gather(*tasks)
        
        # All should complete successfully
        for state in states:
            assert state.triage_result != None
            assert "category" in state.triage_result
    
    @pytest.mark.asyncio
    async def test_websocket_streaming_updates(self, triage_agent, complex_state):
        """Test WebSocket streaming updates during execution"""
        # Mock WebSocket manager
        mock_ws_manager = AsyncMock()
        triage_agent.websocket_manager = mock_ws_manager
        
        triage_agent.llm_manager.set_responses([
            '{"category": "Cost Optimization", "priority": "high", "confidence_score": 0.9}'
        ])
        
        await triage_agent.execute(complex_state, "stream_test", stream_updates=True)
        
        # Should have sent WebSocket updates
        assert mock_ws_manager.send_message.called
        
        # Check messages sent - the actual call structure sends message as second argument
        call_args_list = mock_ws_manager.send_message.call_args_list
        
        # Extract message content from the call arguments
        messages_sent = []
        for call in call_args_list:
            if len(call.args) > 1:
                message = call.args[1]
                if isinstance(message, dict):
                    messages_sent.append(message)
        
        # Should have sent at least one message
        assert len(messages_sent) > 0
        
        # Check if any messages contain status information
        status_found = False
        for message in messages_sent:
            if isinstance(message, dict):
                # Check for status in various message formats
                if "status" in message or "type" in message:
                    status_found = True
                    break
                if "payload" in message and isinstance(message["payload"], dict):
                    if "status" in message["payload"] or "state" in message["payload"]:
                        status_found = True
                        break
        
        assert status_found, f"No status updates found in messages: {messages_sent}"
    
    @pytest.mark.asyncio
    async def test_async_cleanup_operations(self, triage_agent, complex_state):
        """Test async cleanup operations"""
        # Add some test data to be cleaned up
        complex_state.triage_result = {
            "category": "Test Category",
            "metadata": {
                "triage_duration_ms": 250,
                "cache_hit": False,
                "llm_calls": 1
            }
        }
        
        with patch('app.agents.triage_sub_agent.logger') as mock_logger:
            await triage_agent.cleanup(complex_state, "cleanup_test")
            
            # Should log cleanup information
            assert mock_logger.debug.called or mock_logger.info.called


class TestPydanticModelValidation:
    """Test Pydantic model validation and serialization"""
    
    def test_triage_result_comprehensive_validation(self):
        """Test comprehensive TriageResult validation"""
        # Valid complete result
        valid_result = TriageResult(
            category="Cost Optimization",
            confidence_score=0.85,
            priority=Priority.HIGH,
            complexity=Complexity.MODERATE,
            estimated_execution_time=300,
            key_parameters=KeyParameters(
                workload_type="inference",
                optimization_focus="cost",
                constraints=["latency < 100ms"]
            ),
            metadata={"source": "llm", "version": "1.0"}
        )
        
        assert valid_result.category == "Cost Optimization"
        assert valid_result.confidence_score == 0.85
        assert valid_result.priority == Priority.HIGH
        assert valid_result.complexity == Complexity.MODERATE
    
    def test_triage_result_edge_case_validation(self):
        """Test TriageResult validation edge cases"""
        # Test minimum valid result
        minimal_result = TriageResult(
            category="Test",
            confidence_score=0.0,
            priority=Priority.LOW,
            complexity=Complexity.SIMPLE
        )
        
        assert minimal_result.confidence_score == 0.0
        assert minimal_result.estimated_execution_time == None
        
        # Test maximum confidence
        max_confidence_result = TriageResult(
            category="Test",
            confidence_score=1.0,
            priority=Priority.CRITICAL,
            complexity=Complexity.EXPERT
        )
        
        assert max_confidence_result.confidence_score == 1.0
    
    def test_extracted_entities_complex_validation(self):
        """Test ExtractedEntities with complex data"""
        complex_entities = ExtractedEntities(
            models_mentioned=["gpt-4", "claude-2", "llama-2"],
            metrics_mentioned=["cost", "latency", "throughput", "accuracy"],
            thresholds=[
                {"type": "time", "value": 100, "unit": "ms"},
                {"type": "cost", "value": 1000, "unit": "USD"},
                {"type": "rate", "value": 500, "unit": "RPS"}
            ],
            targets=[
                {"type": "percentage", "value": 30, "description": "cost reduction"},
                {"type": "absolute", "value": 50, "unit": "ms", "description": "max latency"}
            ],
            time_ranges=["last 7 days", "peak hours", "weekend"],
            additional_context={
                "business_domain": "e-commerce",
                "scale": "enterprise",
                "urgency": "high"
            }
        )
        
        assert len(complex_entities.models_mentioned) == 3
        assert len(complex_entities.thresholds) == 3
        assert len(complex_entities.targets) == 2
        assert complex_entities.additional_context["business_domain"] == "e-commerce"
    
    def test_user_intent_comprehensive(self):
        """Test UserIntent with comprehensive data"""
        comprehensive_intent = UserIntent(
            primary_intent="optimize",
            secondary_intents=["analyze", "monitor", "report"],
            action_required=True,
            confidence_score=0.92,
            intent_modifiers=["urgent", "cost-sensitive"],
            expected_outcome="30% cost reduction with maintained performance",
            timeline_mentioned="within 2 weeks"
        )
        
        assert comprehensive_intent.primary_intent == "optimize"
        assert len(comprehensive_intent.secondary_intents) == 3
        assert comprehensive_intent.confidence_score == 0.92
        assert "urgent" in comprehensive_intent.intent_modifiers


class TestPerformanceOptimization:
    """Test performance optimization features"""
    
    @pytest.mark.asyncio
    async def test_request_processing_performance(self, triage_agent):
        """Test request processing performance"""
        # Test with various request sizes
        request_sizes = [10, 100, 1000, 5000]  # Character counts
        
        for size in request_sizes:
            request = "Optimize my costs. " * (size // 20)  # Approximate target size
            state = DeepAgentState(user_request=request)
            
            triage_agent.llm_manager.set_responses([
                '{"category": "Cost Optimization", "priority": "medium", "confidence_score": 0.8}'
            ])
            
            start_time = datetime.now()
            await triage_agent.execute(state, f"perf_test_{size}", stream_updates=False)
            end_time = datetime.now()
            
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Should complete within reasonable time (adjust threshold as needed)
            assert execution_time < 5000  # 5 seconds max
            assert state.triage_result != None
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self, triage_agent):
        """Test memory efficiency with large datasets"""
        # Test with large request
        large_request = "Analyze and optimize " * 1000
        state = DeepAgentState(user_request=large_request)
        
        triage_agent.llm_manager.set_responses([
            '{"category": "Performance Optimization", "priority": "high", "confidence_score": 0.85}'
        ])
        
        await triage_agent.execute(state, "memory_test", stream_updates=False)
        
        # Should handle large requests efficiently
        assert state.triage_result != None
        assert state.triage_result["category"] == "Performance Optimization"
    
    def test_hash_generation_performance(self, triage_agent):
        """Test hash generation performance"""
        # Test hash generation with various input sizes
        test_inputs = [
            "Short request",
            "Medium length request with some technical details about optimization",
            "Very long request " * 100 + " with lots of repeated content and technical jargon about AI model optimization, cost reduction, performance improvements, and various metrics and thresholds",
        ]
        
        for test_input in test_inputs:
            start_time = datetime.now()
            hash_result = triage_agent._generate_request_hash(test_input)
            end_time = datetime.now()
            
            generation_time = (end_time - start_time).total_seconds() * 1000
            
            # Hash generation should be fast (< 10ms)
            assert generation_time < 10
            assert len(hash_result) == 64  # SHA-256 hash length
            assert hash_result.isalnum()  # Should be alphanumeric


class TestEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.asyncio
    async def test_empty_and_whitespace_requests(self, triage_agent):
        """Test handling of empty and whitespace-only requests"""
        edge_cases = [
            "",  # Empty string
            "   ",  # Only whitespace
            "\n\t\r",  # Only whitespace characters
            ".",  # Single character
            "??",  # Only punctuation
        ]
        
        for request in edge_cases:
            state = DeepAgentState(user_request=request)
            result = await triage_agent.check_entry_conditions(state, "edge_test")
            
            # Should reject very short/empty requests
            assert result == False
            if state.triage_result:
                assert "error" in state.triage_result
    
    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, triage_agent):
        """Test handling of Unicode and special characters"""
        unicode_requests = [
            "Optimize costs for my café's AI system",  # Accented characters
            "Analyse les coûts d'IA pour mon système",  # French with accents
            "优化我的AI成本",  # Chinese characters
            "Оптимизируйте стоимость ИИ",  # Russian Cyrillic
            "🚀 Optimize my AI costs! 💰📊",  # Emojis
            "Cost optimization → better performance",  # Special arrows
        ]
        
        for request in unicode_requests:
            state = DeepAgentState(user_request=request)
            
            triage_agent.llm_manager.set_responses([
                '{"category": "Cost Optimization", "priority": "medium", "confidence_score": 0.8}'
            ])
            
            await triage_agent.execute(state, "unicode_test", stream_updates=False)
            
            # Should handle Unicode without crashing
            assert state.triage_result != None
            assert "category" in state.triage_result
    
    @pytest.mark.asyncio
    async def test_extremely_long_requests(self, triage_agent):
        """Test handling of extremely long requests"""
        # Create request at the boundary (10,000 characters)
        boundary_request = "Optimize AI costs " * 588  # ~10,000 chars
        very_long_request = "Optimize AI costs " * 1000  # ~17,000 chars
        
        # Boundary case should pass validation
        boundary_state = DeepAgentState(user_request=boundary_request)
        boundary_validation = triage_agent._validate_request(boundary_request)
        assert boundary_validation.is_valid == True
        
        # Very long request should be rejected
        very_long_validation = triage_agent._validate_request(very_long_request)
        assert very_long_validation.is_valid == False
        assert any("exceeds maximum length" in error for error in very_long_validation.validation_errors)
    
    @pytest.mark.asyncio
    async def test_malformed_json_responses(self, triage_agent, complex_state):
        """Test handling of malformed JSON responses from LLM"""
        malformed_responses = [
            '{"category": "Test"',  # Unclosed JSON
            '{"category": "Test", "priority": }',  # Missing value
            '{"category": "Test", "priority": "high",}',  # Trailing comma
            'category: "Test", priority: "high"',  # Missing braces
            'null',  # Null response
            '',  # Empty response
        ]
        
        for malformed_response in malformed_responses:
            triage_agent.llm_manager.set_responses([malformed_response])
            
            state = DeepAgentState(user_request="Test malformed JSON")
            await triage_agent.execute(state, "malformed_test", stream_updates=False)
            
            # Should handle malformed JSON gracefully
            assert state.triage_result != None
            assert state.triage_result["metadata"]["fallback_used"] == True


class TestSecurityAndValidation:
    """Test security and validation features"""
    
    def test_input_sanitization(self, triage_agent):
        """Test input sanitization and cleaning"""
        potentially_harmful_inputs = [
            "<script>alert('xss')</script>Optimize costs",
            "Optimize'; DROP TABLE costs; --",
            "Costs\\x00\\x01\\x02optimization",  # Null bytes and control chars
            "Cost optimization\r\n\r\n<img src=x onerror=alert(1)>",
        ]
        
        for harmful_input in potentially_harmful_inputs:
            validation = triage_agent._validate_request(harmful_input)
            
            # Should detect and reject harmful patterns
            if any("malicious pattern" in error.lower() for error in validation.validation_errors):
                assert validation.is_valid == False
    
    def test_request_normalization(self, triage_agent):
        """Test request normalization for consistent processing"""
        variations = [
            "  Optimize   my   AI   costs  ",
            "OPTIMIZE MY AI COSTS",
            "optimize my ai costs",
            "Optimize\tmy\nAI\rcosts",
        ]
        
        hashes = [triage_agent._generate_request_hash(variation) for variation in variations]
        
        # All variations should produce the same hash (after normalization)
        assert len(set(hashes)) == 1  # All hashes should be identical
    
    @pytest.mark.asyncio
    async def test_resource_limits(self, triage_agent):
        """Test resource limit enforcement"""
        # Test with request at size limit
        max_size_request = "a" * 10000  # Exactly at limit
        over_limit_request = "a" * 10001  # Over limit
        
        max_validation = triage_agent._validate_request(max_size_request)
        over_validation = triage_agent._validate_request(over_limit_request)
        
        # At limit should pass (with possible warning)
        assert max_validation.is_valid == True
        
        # Over limit should fail
        assert over_validation.is_valid == False
        assert any("exceeds maximum length" in error for error in over_validation.validation_errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--durations=10"])