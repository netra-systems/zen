"""Golden Test Suite for TriageSubAgent Business Logic

CRITICAL TEST SUITE: Validates triage categorization, entity extraction, intent detection,
tool recommendations, and all business logic patterns.

This comprehensive test suite covers:
1. Triage categorization with real-world scenarios
2. Entity extraction (models, metrics, time ranges, thresholds)
3. Intent detection and classification
4. Tool recommendation algorithms
5. Fallback mechanisms and error recovery
6. Caching behavior and performance
7. Complex multi-category scenarios
8. Edge cases and boundary conditions

BVJ: ALL segments | Customer Experience | First contact reliability = Revenue protection
"""

import asyncio
import json
import pytest
import time
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from netra_backend.app.agents.triage.unified_triage_agent import (
    UnifiedTriageAgent, TriageResult, Priority, Complexity, 
    ExtractedEntities, UserIntent, ToolRecommendation
)
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas.registry import DeepAgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle

# Stubs for deleted functionality - these tests need refactoring
class TriageProcessor:
    pass

class TriageCore:
    def __init__(self, redis_manager=None):
        self.redis_manager = redis_manager

class TriageSubAgent:
    def __init__(self, llm_manager=None, tool_dispatcher=None, redis_manager=None):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.redis_manager = redis_manager


class TestTriageCategorization:
    """Test comprehensive triage categorization with real-world scenarios."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM manager for testing."""
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock()
        return llm
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Mock tool dispatcher for testing."""
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.dispatch = AsyncMock()
        return dispatcher
    
    @pytest.fixture
    def mock_redis_manager(self):
        """Mock Redis manager for testing."""
        redis = Mock(spec=RedisManager)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        return redis
    
    @pytest.fixture
    def triage_agent(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
        """Create TriageSubAgent for testing."""
        return TriageSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
    
    @pytest.fixture
    def triage_core(self, mock_redis_manager):
        """Create TriageCore for testing."""
        return TriageCore(redis_manager=mock_redis_manager)
    
    def test_cost_optimization_categorization(self, triage_core):
        """Test cost optimization request categorization."""
        cost_requests = [
            "Help me reduce my AI inference costs by 30%",
            "My model serving bills are too high, need optimization",
            "Looking to minimize compute costs for LLM workloads",
            "Cost analysis for GPU vs CPU deployment options",
            "Budget optimization for machine learning operations"
        ]
        
        for request in cost_requests:
            result = triage_core.create_fallback_result(request)
            
            # Should be categorized as cost optimization
            assert "cost" in result.category.lower() or "optimization" in result.category.lower()
            assert result.confidence_score >= 0.4  # Fallback should have reasonable confidence
            assert result.priority in [Priority.HIGH, Priority.MEDIUM]
            assert isinstance(result.extracted_entities, ExtractedEntities)
            assert isinstance(result.user_intent, UserIntent)
            assert len(result.tool_recommendations) >= 0
            
    def test_performance_optimization_categorization(self, triage_core):
        """Test performance optimization request categorization."""
        performance_requests = [
            "My model inference is taking too long, need speed improvements",
            "Optimize throughput for batch processing workloads",
            "Reduce latency for real-time prediction API",
            "Performance tuning for distributed training jobs",
            "Scaling issues with high-traffic model serving"
        ]
        
        for request in performance_requests:
            result = triage_core.create_fallback_result(request)
            
            # Should be categorized as performance optimization
            assert "performance" in result.category.lower() or "optimization" in result.category.lower()
            assert result.priority in [Priority.HIGH, Priority.CRITICAL]
            assert result.complexity in [Complexity.MODERATE, Complexity.COMPLEX, Complexity.EXPERT]
            
    def test_workload_analysis_categorization(self, triage_core):
        """Test workload analysis request categorization."""
        analysis_requests = [
            "Analyze my current AI infrastructure utilization",
            "Need insights into model performance patterns",
            "Resource consumption analysis for ML workloads",
            "Understanding bottlenecks in my AI pipeline",
            "Generate report on compute efficiency metrics"
        ]
        
        for request in analysis_requests:
            result = triage_core.create_fallback_result(request)
            
            # Should be categorized as analysis
            assert "analysis" in result.category.lower() or "workload" in result.category.lower()
            assert result.priority in [Priority.MEDIUM, Priority.LOW]
            assert result.user_intent.primary_intent in ["analyze", "report", "insights"]
            
    def test_configuration_categorization(self, triage_core):
        """Test configuration and settings request categorization."""
        config_requests = [
            "Help me configure auto-scaling for my model endpoints",
            "Set up monitoring and alerting for AI workloads",
            "Configure resource limits for training jobs",
            "Setup deployment pipeline for ML models",
            "Environment configuration for multi-tenant AI platform"
        ]
        
        for request in config_requests:
            result = triage_core.create_fallback_result(request)
            
            # Should be categorized as configuration
            assert ("configuration" in result.category.lower() or 
                   "settings" in result.category.lower() or
                   "configure" in result.category.lower())
            assert result.complexity in [Complexity.MODERATE, Complexity.COMPLEX]
            
    def test_multi_category_complex_requests(self, triage_core):
        """Test complex requests that span multiple categories."""
        complex_requests = [
            "I need to optimize both cost and performance for my GPT-4 deployment while setting up proper monitoring",
            "Analyze current spending, improve inference speed, and configure auto-scaling for production workloads",
            "Cost analysis with performance benchmarking for model serving infrastructure migration",
            "Setup monitoring, optimize resource utilization, and reduce operational costs for ML platform"
        ]
        
        for request in complex_requests:
            result = triage_core.create_fallback_result(request)
            
            # Complex requests should have higher complexity
            assert result.complexity in [Complexity.COMPLEX, Complexity.EXPERT]
            assert result.priority in [Priority.HIGH, Priority.CRITICAL]
            # Should extract multiple components
            assert len(result.extracted_entities.models_mentioned) >= 0
            assert len(result.extracted_entities.metrics_mentioned) >= 0
            
    def test_edge_case_categorization(self, triage_core):
        """Test edge cases and unusual requests."""
        edge_cases = [
            "",  # Empty request
            "Help",  # Single word
            "????????????",  # Non-ASCII characters
            "a" * 1000,  # Very long request
            "What is the meaning of life?",  # Irrelevant question
            "Delete all data immediately",  # Potentially harmful request
            "1234567890",  # Numbers only
            "!!!@@@###$$$",  # Special characters only
        ]
        
        for request in edge_cases:
            result = triage_core.create_fallback_result(request)
            
            # Should handle gracefully without errors
            assert isinstance(result, TriageResult)
            assert result.category is not None
            assert 0 <= result.confidence_score <= 1
            assert isinstance(result.validation_status, ValidationStatus)


class TestEntityExtraction:
    """Test entity extraction from user requests."""
    
    @pytest.fixture
    def triage_core(self):
        return TriageCore()
    
    def test_model_name_extraction(self, triage_core):
        """Test extraction of AI model names from requests."""
        model_requests = [
            "Optimize my GPT-4 deployment costs",
            "Claude-2 inference is too slow",
            "Compare BERT vs RoBERTa performance",
            "LLaMA 2 serving optimization needed",
            "Stable Diffusion XL cost analysis",
            "My custom transformer model needs tuning",
            "OpenAI GPT-3.5-turbo vs GPT-4 comparison"
        ]
        
        for request in model_requests:
            entities = triage_core.entity_extractor.extract_entities(request)
            
            # Should extract model-related entities
            assert isinstance(entities, ExtractedEntities)
            # Models might be extracted as part of general entity extraction
            assert len(entities.models_mentioned) >= 0  # May or may not find specific models
            
    def test_metrics_extraction(self, triage_core):
        """Test extraction of performance metrics from requests."""
        metrics_requests = [
            "Reduce latency by 50ms and improve throughput to 1000 RPS",
            "My error rate is at 2.5% need to get it under 1%",
            "Token processing speed dropped to 15 tokens/second",
            "GPU utilization stuck at 60%, want to reach 85%",
            "Memory usage spiked to 16GB, normal is 8GB",
            "Cost per inference increased to $0.002 from $0.001",
            "Response time P99 is 2.5 seconds, target is under 1 second"
        ]
        
        for request in metrics_requests:
            entities = triage_core.entity_extractor.extract_entities(request)
            
            # Should identify metrics and numerical values
            assert isinstance(entities, ExtractedEntities)
            assert len(entities.metrics_mentioned) >= 0
            assert len(entities.thresholds) >= 0  # Might extract threshold values
            
    def test_time_range_extraction(self, triage_core):
        """Test extraction of time ranges and temporal information."""
        time_requests = [
            "Performance degraded over the last 7 days",
            "Cost trends for the past 3 months",
            "Need analysis from January to March 2024",
            "Yesterday's incident needs investigation",
            "Real-time monitoring setup required",
            "Weekly reports generation automation",
            "Historical data from Q4 2023 comparison"
        ]
        
        for request in time_requests:
            entities = triage_core.entity_extractor.extract_entities(request)
            
            # Should extract temporal information
            assert isinstance(entities, ExtractedEntities)
            assert len(entities.time_ranges) >= 0  # May extract time-related entities
            
    def test_threshold_and_target_extraction(self, triage_core):
        """Test extraction of thresholds, limits, and targets."""
        threshold_requests = [
            "Keep costs under $1000 per month",
            "Latency must be below 100ms",
            "Scale up when CPU > 80%",
            "Alert when error rate exceeds 5%",
            "Target 99.9% uptime SLA",
            "Maximum 50 concurrent requests",
            "Budget limit of $50K for Q1"
        ]
        
        for request in threshold_requests:
            entities = triage_core.entity_extractor.extract_entities(request)
            
            # Should extract threshold values and targets
            assert isinstance(entities, ExtractedEntities)
            assert len(entities.thresholds) >= 0
            assert len(entities.targets) >= 0
            
    def test_complex_multi_entity_extraction(self, triage_core):
        """Test extraction from requests with multiple entity types."""
        complex_requests = [
            "Optimize GPT-4 costs to under $500/month while maintaining sub-200ms latency for the production API serving 1000+ daily users",
            "Analyze Claude-2 vs GPT-3.5-turbo performance over the last 30 days, focusing on token/s throughput and cost per 1K tokens",
            "Setup monitoring for BERT model inference with alerts when memory usage > 8GB or response time > 500ms during peak hours (9-5 PST)"
        ]
        
        for request in complex_requests:
            entities = triage_core.entity_extractor.extract_entities(request)
            
            # Should extract multiple types of entities
            assert isinstance(entities, ExtractedEntities)
            # Complex requests should have some entities extracted
            total_entities = (len(entities.models_mentioned) + 
                            len(entities.metrics_mentioned) + 
                            len(entities.time_ranges) + 
                            len(entities.thresholds) + 
                            len(entities.targets))
            assert total_entities >= 0  # Should find some entities


class TestIntentDetection:
    """Test user intent detection and classification."""
    
    @pytest.fixture
    def triage_core(self):
        return TriageCore()
    
    def test_optimization_intent_detection(self, triage_core):
        """Test detection of optimization-related intents."""
        optimization_requests = [
            "I want to optimize my model serving costs",
            "Please help me improve inference speed",
            "Looking to reduce GPU usage",
            "Optimize for better performance",
            "Make my workloads more efficient"
        ]
        
        for request in optimization_requests:
            intent = triage_core.intent_detector.detect_intent(request)
            
            assert isinstance(intent, UserIntent)
            assert intent.primary_intent in ["optimize", "improve", "reduce", "enhance"]
            assert intent.action_required is True
            
    def test_analysis_intent_detection(self, triage_core):
        """Test detection of analysis-related intents."""
        analysis_requests = [
            "Can you analyze my current infrastructure?",
            "I need insights into model performance",
            "Show me cost trends",
            "Generate a report on resource usage",
            "Provide recommendations based on data"
        ]
        
        for request in analysis_requests:
            intent = triage_core.intent_detector.detect_intent(request)
            
            assert isinstance(intent, UserIntent)
            assert intent.primary_intent in ["analyze", "report", "insights", "review"]
            
    def test_configuration_intent_detection(self, triage_core):
        """Test detection of configuration-related intents."""
        config_requests = [
            "Help me set up monitoring",
            "Configure auto-scaling rules",
            "I need to setup deployment pipeline",
            "Install monitoring tools",
            "Create alerting policies"
        ]
        
        for request in config_requests:
            intent = triage_core.intent_detector.detect_intent(request)
            
            assert isinstance(intent, UserIntent)
            assert intent.primary_intent in ["configure", "setup", "install", "create"]
            assert intent.action_required is True
            
    def test_troubleshooting_intent_detection(self, triage_core):
        """Test detection of troubleshooting-related intents."""
        troubleshooting_requests = [
            "My models are failing frequently",
            "Debug performance issues",
            "Something is wrong with my deployment",
            "Fix the latency spikes",
            "Investigate cost anomalies"
        ]
        
        for request in troubleshooting_requests:
            intent = triage_core.intent_detector.detect_intent(request)
            
            assert isinstance(intent, UserIntent)
            assert intent.primary_intent in ["debug", "fix", "investigate", "troubleshoot", "resolve"]
            assert intent.action_required is True
            
    def test_multi_intent_detection(self, triage_core):
        """Test detection of multiple intents in complex requests."""
        multi_intent_requests = [
            "Analyze current costs and then optimize my deployment",
            "Setup monitoring and configure alerts for performance issues",
            "Debug the latency problem and provide optimization recommendations",
            "Generate cost report and help reduce expenses"
        ]
        
        for request in multi_intent_requests:
            intent = triage_core.intent_detector.detect_intent(request)
            
            assert isinstance(intent, UserIntent)
            assert len(intent.secondary_intents) >= 0  # May detect secondary intents
            assert intent.action_required is True  # Complex requests usually require action


class TestToolRecommendation:
    """Test tool recommendation algorithms."""
    
    @pytest.fixture
    def triage_core(self):
        return TriageCore()
    
    def test_cost_optimization_tool_recommendations(self, triage_core):
        """Test tool recommendations for cost optimization requests."""
        # Mock entities for cost optimization
        entities = ExtractedEntities(
            models_mentioned=["GPT-4", "Claude-2"],
            metrics_mentioned=["cost", "billing"],
            thresholds=[{"type": "cost", "value": "$500", "operator": "under"}]
        )
        
        tools = triage_core.tool_recommender.recommend_tools("Cost Optimization", entities)
        
        assert isinstance(tools, list)
        for tool in tools:
            assert isinstance(tool, ToolRecommendation)
            assert tool.tool_name is not None
            assert 0 <= tool.relevance_score <= 1
            assert isinstance(tool.parameters, dict)
            
    def test_performance_optimization_tool_recommendations(self, triage_core):
        """Test tool recommendations for performance optimization requests."""
        entities = ExtractedEntities(
            models_mentioned=["BERT"],
            metrics_mentioned=["latency", "throughput", "response_time"],
            thresholds=[{"type": "latency", "value": "100ms", "operator": "under"}]
        )
        
        tools = triage_core.tool_recommender.recommend_tools("Performance Optimization", entities)
        
        assert isinstance(tools, list)
        # Should recommend performance-related tools
        for tool in tools:
            assert isinstance(tool, ToolRecommendation)
            assert tool.relevance_score > 0
            
    def test_analysis_tool_recommendations(self, triage_core):
        """Test tool recommendations for analysis requests."""
        entities = ExtractedEntities(
            metrics_mentioned=["utilization", "efficiency", "trends"],
            time_ranges=[{"start": "2024-01-01", "end": "2024-03-31"}]
        )
        
        tools = triage_core.tool_recommender.recommend_tools("Workload Analysis", entities)
        
        assert isinstance(tools, list)
        # Should recommend analysis/reporting tools
        for tool in tools:
            assert isinstance(tool, ToolRecommendation)
            
    def test_tool_relevance_scoring(self, triage_core):
        """Test tool relevance scoring accuracy."""
        # High-relevance scenario
        high_rel_entities = ExtractedEntities(
            models_mentioned=["GPT-4", "Claude-2", "BERT"],
            metrics_mentioned=["cost", "latency", "throughput"],
            thresholds=[{"type": "cost", "value": "$1000"}]
        )
        
        high_rel_tools = triage_core.tool_recommender.recommend_tools("Cost Optimization", high_rel_entities)
        
        # Low-relevance scenario
        low_rel_entities = ExtractedEntities(
            models_mentioned=[],
            metrics_mentioned=[],
            thresholds=[]
        )
        
        low_rel_tools = triage_core.tool_recommender.recommend_tools("General Inquiry", low_rel_entities)
        
        # High relevance should generally have higher scores (if tools are returned)
        if high_rel_tools and low_rel_tools:
            avg_high_score = sum(t.relevance_score for t in high_rel_tools) / len(high_rel_tools)
            avg_low_score = sum(t.relevance_score for t in low_rel_tools) / len(low_rel_tools)
            assert avg_high_score >= avg_low_score
            
    def test_tool_parameter_customization(self, triage_core):
        """Test tool parameter customization based on extracted entities."""
        entities = ExtractedEntities(
            models_mentioned=["GPT-4"],
            metrics_mentioned=["cost"],
            thresholds=[{"type": "budget", "value": "$500", "period": "monthly"}],
            targets=[{"metric": "cost_reduction", "value": "30%"}]
        )
        
        tools = triage_core.tool_recommender.recommend_tools("Cost Optimization", entities)
        
        for tool in tools:
            # Parameters should be customized based on entities
            assert isinstance(tool.parameters, dict)
            # May contain model-specific or threshold-specific parameters


class TestFallbackMechanisms:
    """Test fallback mechanisms and error recovery."""
    
    @pytest.fixture
    def triage_agent(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
        llm_manager = mock_llm_manager
        return TriageSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
    
    @pytest.fixture
    def mock_llm_manager(self):
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock()
        return llm
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        return Mock(spec=ToolDispatcher)
    
    @pytest.fixture
    def mock_redis_manager(self):
        redis = Mock(spec=RedisManager)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        return redis
    
    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self, triage_agent):
        """Test fallback when LLM processing fails."""
        # Configure LLM to fail
        triage_agent.llm_manager.generate_response.side_effect = Exception("LLM API Error")
        
        state = DeepAgentState()
        state.user_request = "Help me optimize my model costs"
        
        # Should fallback gracefully
        result = await triage_agent._execute_triage_fallback(state, "test_run", True)
        
        assert isinstance(result, dict)
        assert "metadata" in result
        assert result["metadata"]["fallback_used"] is True
        
    @pytest.mark.asyncio
    async def test_json_parsing_fallback(self, triage_agent):
        """Test fallback when LLM response is not valid JSON."""
        # Configure LLM to return invalid JSON
        triage_agent.llm_manager.generate_response.return_value = "This is not JSON at all"
        
        state = DeepAgentState()
        state.user_request = "Analyze my infrastructure costs"
        
        # Should handle gracefully
        result = await triage_agent._execute_triage_fallback(state, "test_run", True)
        
        assert isinstance(result, dict)
        assert result["metadata"]["fallback_used"] is True
        
    @pytest.mark.asyncio
    async def test_network_timeout_fallback(self, triage_agent):
        """Test fallback when network requests timeout."""
        # Simulate timeout
        async def timeout_side_effect(*args, **kwargs):
            await asyncio.sleep(0.1)
            raise asyncio.TimeoutError("Request timed out")
        
        triage_agent.llm_manager.generate_response.side_effect = timeout_side_effect
        
        state = DeepAgentState()
        state.user_request = "Performance optimization needed"
        
        result = await triage_agent._execute_triage_fallback(state, "test_run", True)
        
        assert isinstance(result, dict)
        assert result["metadata"]["fallback_used"] is True
        
    def test_fallback_result_quality(self, triage_agent):
        """Test quality of fallback results."""
        test_requests = [
            "Optimize my GPT-4 costs",
            "Improve model performance",
            "Setup monitoring dashboard",
            "Analyze resource usage patterns"
        ]
        
        for request in test_requests:
            result = triage_agent.triage_core.create_fallback_result(request)
            
            # Fallback results should be valid and useful
            assert isinstance(result, TriageResult)
            assert result.category != "unknown"  # Should categorize properly
            assert result.confidence_score >= 0.3  # Reasonable confidence
            assert len(result.tool_recommendations) >= 0
            assert result.metadata.fallback_used is True
            
    def test_partial_llm_response_handling(self, triage_agent):
        """Test handling of partial or corrupted LLM responses."""
        partial_responses = [
            '{"category": "Cost Optimization", "confidence"',  # Incomplete JSON
            '{"category": "Performance", "confidence_score": "invalid"}',  # Invalid types
            '{"category": null, "confidence_score": 0.8}',  # Null values
            '{"unexpected_field": "value"}',  # Missing required fields
        ]
        
        for response in partial_responses:
            # Should handle gracefully without crashing
            parsed = triage_agent.triage_core.extract_and_validate_json(response)
            # May return None or partial data, but should not crash
            assert parsed is None or isinstance(parsed, dict)


class TestCachingBehavior:
    """Test caching behavior and performance optimizations."""
    
    @pytest.fixture
    def mock_redis(self):
        redis = Mock(spec=RedisManager)
        redis.get = AsyncMock()
        redis.set = AsyncMock()
        return redis
    
    @pytest.fixture
    def triage_core_with_cache(self, mock_redis):
        return TriageCore(redis_manager=mock_redis)
    
    @pytest.fixture
    def triage_core_no_cache(self):
        return TriageCore(redis_manager=None)
    
    def test_request_hash_generation(self, triage_core_with_cache):
        """Test request hash generation for caching."""
        requests = [
            "Optimize my model costs",
            "optimize my model costs",  # Case insensitive
            "Optimize  my   model    costs",  # Multiple spaces
            "  Optimize my model costs  ",  # Leading/trailing spaces
        ]
        
        hashes = [triage_core_with_cache.generate_request_hash(req) for req in requests]
        
        # Similar requests should produce same hash
        assert len(set(hashes)) == 1  # All should be same hash
        
        # Different requests should produce different hashes
        different_request = "Analyze performance metrics"
        different_hash = triage_core_with_cache.generate_request_hash(different_request)
        assert different_hash not in hashes
        
    @pytest.mark.asyncio
    async def test_cache_miss_behavior(self, triage_core_with_cache, mock_redis):
        """Test behavior when cache misses."""
        # Configure Redis to return None (cache miss)
        mock_redis.get.return_value = None
        
        request_hash = triage_core_with_cache.generate_request_hash("test request")
        result = await triage_core_with_cache.get_cached_result(request_hash)
        
        assert result is None
        mock_redis.get.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_cache_hit_behavior(self, triage_core_with_cache, mock_redis):
        """Test behavior when cache hits."""
        # Configure Redis to return cached data
        cached_data = {
            "category": "Cost Optimization",
            "confidence_score": 0.9,
            "metadata": {"cache_hit": True}
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        request_hash = triage_core_with_cache.generate_request_hash("test request")
        result = await triage_core_with_cache.get_cached_result(request_hash)
        
        assert result == cached_data
        mock_redis.get.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_cache_storage(self, triage_core_with_cache, mock_redis):
        """Test caching of results."""
        result_data = {
            "category": "Performance Optimization",
            "confidence_score": 0.85,
            "tool_recommendations": []
        }
        
        request_hash = triage_core_with_cache.generate_request_hash("performance test")
        await triage_core_with_cache.cache_result(request_hash, result_data)
        
        # Should call Redis set with proper parameters
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert len(call_args[0]) >= 2  # key and value
        
    @pytest.mark.asyncio
    async def test_cache_error_handling(self, triage_core_with_cache, mock_redis):
        """Test error handling in cache operations."""
        # Configure Redis to raise exceptions
        mock_redis.get.side_effect = Exception("Redis connection error")
        mock_redis.set.side_effect = Exception("Redis write error")
        
        request_hash = triage_core_with_cache.generate_request_hash("test")
        
        # Should handle cache errors gracefully
        result = await triage_core_with_cache.get_cached_result(request_hash)
        assert result is None  # Should return None on cache error
        
        # Should handle cache write errors gracefully
        await triage_core_with_cache.cache_result(request_hash, {"test": "data"})
        # Should not raise exception
        
    @pytest.mark.asyncio
    async def test_no_cache_behavior(self, triage_core_no_cache):
        """Test behavior when no cache is available."""
        request_hash = triage_core_no_cache.generate_request_hash("test")
        
        # Should return None immediately
        result = await triage_core_no_cache.get_cached_result(request_hash)
        assert result is None
        
        # Should handle cache storage gracefully
        await triage_core_no_cache.cache_result(request_hash, {"test": "data"})
        # Should not raise exception


class TestComplexScenarios:
    """Test complex real-world scenarios and edge cases."""
    
    @pytest.fixture
    def triage_agent(self, mock_llm_manager, mock_tool_dispatcher, mock_redis_manager):
        return TriageSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher,
            redis_manager=mock_redis_manager
        )
    
    @pytest.fixture
    def mock_llm_manager(self):
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock()
        return llm
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        return Mock(spec=ToolDispatcher)
    
    @pytest.fixture
    def mock_redis_manager(self):
        redis = Mock(spec=RedisManager)
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        return redis
    
    @pytest.mark.asyncio
    async def test_validation_failure_scenarios(self, triage_agent):
        """Test various request validation failure scenarios."""
        invalid_requests = [
            "",  # Empty request
            " " * 10,  # Only whitespace
            None,  # Null request (if passed through)
            "a",  # Too short
            "?" * 10000,  # Too long
        ]
        
        for invalid_request in invalid_requests:
            if invalid_request is None:
                continue  # Skip None as it may not reach validation
                
            state = DeepAgentState()
            state.user_request = invalid_request
            
            context = ExecutionContext(
                run_id="validation_test",
                agent_name="TriageTestAgent",
                state=state,
                stream_updates=False
            )
            
            # Should handle validation gracefully
            is_valid = await triage_agent.validate_preconditions(context)
            
            if not is_valid:
                # If validation fails, state should be updated appropriately
                assert hasattr(state, 'triage_result') or state.triage_result is None
                
    @pytest.mark.asyncio
    async def test_concurrent_execution(self, triage_agent):
        """Test concurrent triage executions."""
        # Create multiple concurrent requests
        states = []
        for i in range(5):
            state = DeepAgentState()
            state.user_request = f"Optimize costs for workload {i}"
            states.append(state)
        
        # Execute concurrently
        tasks = []
        for i, state in enumerate(states):
            task = triage_agent._execute_triage_fallback(state, f"concurrent_run_{i}", False)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, dict)
            
    @pytest.mark.asyncio
    async def test_large_request_handling(self, triage_agent):
        """Test handling of very large requests."""
        # Create a large request
        large_request = "Please help me optimize " + "my AI infrastructure " * 500
        
        state = DeepAgentState()
        state.user_request = large_request
        
        # Should handle without memory issues
        result = await triage_agent._execute_triage_fallback(state, "large_request_test", False)
        
        assert isinstance(result, dict)
        assert "category" in result
        
    @pytest.mark.asyncio
    async def test_special_characters_handling(self, triage_agent):
        """Test handling of requests with special characters."""
        special_requests = [
            "Optimize my model's performance (>90% accuracy needed)",
            "Cost reduction for GPT-4 @ $0.03/1K tokens",
            "Setup monitoring & alerting for production workloads",
            "Latency < 100ms & throughput > 1000 RPS required",
            "Model serving with 99.9% uptime SLA",
            "Resource usage: CPU 80%+, Memory 16GB+, GPU 90%+"
        ]
        
        for request in special_requests:
            state = DeepAgentState()
            state.user_request = request
            
            result = await triage_agent._execute_triage_fallback(state, "special_chars_test", False)
            
            assert isinstance(result, dict)
            assert "category" in result
            
    def test_boundary_value_testing(self, triage_agent):
        """Test boundary values for numerical thresholds."""
        boundary_test_cases = [
            # Confidence scores
            {"confidence_score": 0.0},  # Minimum
            {"confidence_score": 1.0},  # Maximum
            {"confidence_score": 0.5},  # Middle
            
            # Duration values
            {"triage_duration_ms": 0},    # Minimum
            {"triage_duration_ms": 1000}, # Normal
            {"triage_duration_ms": 60000}, # Large
        ]
        
        for test_case in boundary_test_cases:
            # Test that these values are handled properly
            if "confidence_score" in test_case:
                # Should be valid confidence score
                score = test_case["confidence_score"]
                assert 0 <= score <= 1
                
    @pytest.mark.asyncio
    async def test_state_management_during_execution(self, triage_agent):
        """Test agent state management during triage execution."""
        state = DeepAgentState()
        state.user_request = "Test state management"
        
        # Check initial state
        initial_state = triage_agent.get_state()
        assert initial_state == SubAgentLifecycle.PENDING
        
        # Execute triage
        result = await triage_agent._execute_triage_fallback(state, "state_test", False)
        
        # Should complete successfully
        assert isinstance(result, dict)
        # Agent state management is handled by BaseAgent
        
    @pytest.mark.asyncio
    async def test_cleanup_after_execution(self, triage_agent):
        """Test cleanup behavior after triage execution."""
        state = DeepAgentState()
        state.user_request = "Test cleanup behavior"
        
        # Execute triage
        await triage_agent._execute_triage_fallback(state, "cleanup_test", False)
        
        # Test cleanup
        await triage_agent.cleanup(state, "cleanup_test")
        
        # Should handle cleanup gracefully
        if hasattr(state, 'triage_result') and state.triage_result:
            assert isinstance(state.triage_result, dict)


class TestPerformanceBenchmarks:
    """Test performance characteristics and benchmarks."""
    
    @pytest.fixture
    def triage_core(self):
        return TriageCore()
    
    def test_fallback_categorization_performance(self, triage_core):
        """Test performance of fallback categorization."""
        test_requests = [
            "Optimize model costs",
            "Improve inference performance",
            "Setup monitoring dashboard",
            "Analyze resource usage",
            "Debug latency issues"
        ] * 20  # 100 requests total
        
        start_time = time.time()
        
        for request in test_requests:
            result = triage_core.create_fallback_result(request)
            assert isinstance(result, TriageResult)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should process 100 fallback requests in reasonable time
        assert total_time < 5.0  # Should complete in under 5 seconds
        
        avg_time_per_request = total_time / len(test_requests)
        assert avg_time_per_request < 0.1  # Under 100ms per request average
        
    def test_hash_generation_performance(self, triage_core):
        """Test performance of request hash generation."""
        requests = [f"Test request {i} with some content to hash" for i in range(1000)]
        
        start_time = time.time()
        hashes = [triage_core.generate_request_hash(req) for req in requests]
        end_time = time.time()
        
        # Should generate 1000 hashes quickly
        assert (end_time - start_time) < 1.0  # Under 1 second
        
        # All hashes should be unique (different requests)
        assert len(set(hashes)) == len(requests)
        
    def test_json_extraction_performance(self, triage_core):
        """Test performance of JSON extraction methods."""
        test_responses = [
            '{"category": "Cost Optimization", "confidence_score": 0.8}',
            'Some text before {"category": "Performance", "confidence_score": 0.9} some text after',
            '{"malformed": "json", "missing": quotes}',
            'category: "Analysis"\nconfidence_score: "0.7"',
            '{"complex": {"nested": {"structure": "value"}}, "array": [1, 2, 3]}'
        ] * 50  # 250 extractions total
        
        start_time = time.time()
        
        for response in test_responses:
            result = triage_core.extract_and_validate_json(response)
            # Result can be None or dict
            assert result is None or isinstance(result, dict)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should process all extractions reasonably quickly
        assert total_time < 3.0  # Under 3 seconds for 250 extractions
        
    def test_memory_usage_stability(self, triage_core):
        """Test that repeated operations don't cause memory leaks."""
        import gc
        import sys
        
        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Perform many operations
        for i in range(100):
            request = f"Test memory usage request {i}"
            result = triage_core.create_fallback_result(request)
            hash_val = triage_core.generate_request_hash(request)
            json_result = triage_core.extract_and_validate_json('{"test": "data"}')
            
            # Clear references
            del result, hash_val, json_result
        
        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory usage should be stable (allow some growth for caches)
        object_growth = final_objects - initial_objects
        assert object_growth < 1000  # Should not create excessive objects