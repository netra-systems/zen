"""Unit Tests for Triage Golden Path - Core Logic Validation

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All (Free/Early/Mid/Enterprise/Platform) - System Foundation
- Business Goal: Ensure triage agent correctly routes requests to deliver AI value
- Value Impact: Triage is the entry point that determines how $500K+ ARR user requests are handled
- Strategic Impact: Critical infrastructure that enables all downstream AI optimization value delivery
- Revenue Protection: Without proper triage, users get wrong agents  ->  poor experiences  ->  churn

PURPOSE: This test suite validates the core triage logic that determines agent execution
workflow for user requests. Triage is the critical first step that must run successfully
for any user to get AI value from the platform.

KEY COVERAGE:
1. Core triage logic without complex dependencies
2. Data sufficiency determination (sufficient/partial/insufficient)
3. Intent detection and category classification
4. Agent routing decisions based on request analysis
5. Fallback mechanisms when LLM processing fails
6. Performance requirements for fast response times

GOLDEN PATH PROTECTION:
Tests ensure triage correctly identifies what users need and routes them to appropriate
agents. This is the foundation that enables the entire $500K+ ARR golden path user flow.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from test_framework.ssot.base_test_case import SSotBaseTestCase

from netra_backend.app.agents.triage.unified_triage_agent import (
    UnifiedTriageAgent,
    UnifiedTriageAgentFactory, 
    TriageConfig
)
from netra_backend.app.agents.triage.models import (
    Priority,
    Complexity,
    ExtractedEntities,
    UserIntent,
    ToolRecommendation,
    TriageResult,
    TriageMetadata
)


@dataclass
class MockUserExecutionContext:
    """Mock user context for unit testing - isolated per test"""
    user_id: str
    request_id: str
    thread_id: str
    run_id: str
    session_id: str
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if not hasattr(self, 'metadata'):
            self.metadata = {}


@dataclass 
class MockState:
    """Mock state object for execute() calls"""
    original_request: str
    request: Optional[str] = None
    user_request: Optional[str] = None
    
    def __post_init__(self):
        # Provide fallback aliases only when fields are None
        if self.request is None:
            self.request = self.original_request
        if self.user_request is None:
            self.user_request = self.original_request


class TestTriageGoldenPath(SSotBaseTestCase):
    """Unit tests for triage golden path core logic
    
    This test class validates the critical triage functionality that determines
    how user requests are routed through the agent system. These tests focus on
    core business logic without requiring complex infrastructure dependencies.
    
    Tests MUST ensure triage correctly:
    1. Classifies user requests into appropriate categories
    2. Determines data sufficiency for downstream agents  
    3. Routes users to correct agents based on intent
    4. Provides fallback mechanisms for edge cases
    """
    
    def setup_method(self, method=None):
        """Setup for each test with proper isolation"""
        super().setup_method(method)
        
        # Create mock dependencies with minimal behavior
        self.mock_llm_manager = Mock()
        self.mock_tool_dispatcher = Mock()
        
        # Create isolated user context for this test
        self.user_context = MockUserExecutionContext(
            user_id=f"test_user_{self.get_test_context().test_id}",
            request_id=f"test_req_{self.get_test_context().test_id}",
            thread_id=f"test_thread_{self.get_test_context().test_id}",
            run_id=f"test_run_{self.get_test_context().test_id}",
            session_id=f"test_session_{self.get_test_context().test_id}",
            metadata={}
        )
        
        # Create triage agent instance
        self.triage_agent = UnifiedTriageAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher,
            context=self.user_context,
            execution_priority=0
        )
        
        # Mock WebSocket methods to avoid errors
        self.triage_agent.emit_agent_started = AsyncMock()
        self.triage_agent.emit_thinking = AsyncMock()
        self.triage_agent.emit_agent_completed = AsyncMock()
        self.triage_agent.emit_error = AsyncMock()
        self.triage_agent.store_metadata_result = Mock()
    
    # ========================================================================
    # CORE TRIAGE LOGIC TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_triage_execution_priority_is_zero(self):
        """Test that triage agent has execution priority 0 (MUST RUN FIRST)
        
        Business Impact: Ensures triage runs first in agent pipeline.
        This is critical because all other agents depend on triage results.
        """
        assert self.triage_agent.execution_priority == 0
        assert self.triage_agent.EXECUTION_ORDER == 0
        
        # Verify factory creates agent with correct priority
        factory_agent = UnifiedTriageAgentFactory.create_for_context(
            context=self.user_context,
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
        assert factory_agent.execution_priority == 0
    
    @pytest.mark.unit
    async def test_request_extraction_from_various_state_formats(self):
        """Test request extraction from different state object formats
        
        Business Impact: Ensures triage works with various upstream state formats.
        Critical for compatibility across different entry points to the system.
        """
        # Test with original_request
        state1 = MockState(original_request="Optimize my costs")
        request1 = self.triage_agent._extract_request(state1)
        assert request1 == "Optimize my costs"
        
        # Test with request field
        state2 = MockState(original_request="", request="Analyze performance")
        request2 = self.triage_agent._extract_request(state2)
        assert request2 == "Analyze performance"
        
        # Test with dict state
        state3 = {"user_request": "Compare models"}
        request3 = self.triage_agent._extract_request(state3)
        assert request3 == "Compare models"
        
        # Test with missing request
        state4 = MockState(original_request="")
        state4.original_request = None
        state4.request = None
        state4.user_request = None
        request4 = self.triage_agent._extract_request(state4)
        assert request4 is None
    
    @pytest.mark.unit
    def test_request_validation_security_and_format(self):
        """Test request validation for security and format compliance
        
        Business Impact: Protects against malicious input and ensures
        requests meet minimum quality standards for processing.
        """
        # Valid request
        valid_result = self.triage_agent._validate_request("Optimize my AWS costs for production workloads")
        assert valid_result["valid"] is True
        assert valid_result["reason"] is None
        
        # Too short
        short_result = self.triage_agent._validate_request("hi")
        assert short_result["valid"] is False
        assert "too short" in short_result["reason"].lower()
        
        # Too long 
        long_request = "x" * 10001
        long_result = self.triage_agent._validate_request(long_request)
        assert long_result["valid"] is False
        assert "too long" in long_result["reason"].lower()
        
        # Malicious content
        malicious_request = "DROP TABLE users; SELECT * FROM users"
        malicious_result = self.triage_agent._validate_request(malicious_request)
        assert malicious_result["valid"] is False
        assert "malicious" in malicious_result["reason"].lower()
        
        # JavaScript injection
        js_request = "<script>alert('xss')</script>help me"
        js_result = self.triage_agent._validate_request(js_request)
        assert js_result["valid"] is False
        
        self.record_metric("validation_tests_passed", 5)
    
    # ========================================================================
    # ENTITY EXTRACTION TESTS
    # ========================================================================
    
    @pytest.mark.unit
    def test_entity_extraction_models(self):
        """Test extraction of AI model names from user requests
        
        Business Impact: Accurate model extraction enables better tool selection
        and cost analysis for specific models mentioned by users.
        """
        # Test various model patterns
        request = "Compare gpt-4 vs claude-3 vs llama-70b performance"
        entities = self.triage_agent._extract_entities(request)
        
        # Should extract model names
        assert len(entities.models) >= 2  # At least some models detected
        
        # Test specific patterns
        model_patterns = [
            ("Using gpt-4-turbo for analysis", ["gpt-4-turbo"]),
            ("Claude-3 vs GPT-4", ["claude-3"]),  # Case insensitive
            ("Need help with gemini-pro", ["gemini-pro"]),
        ]
        
        for request_text, expected_models in model_patterns:
            entities = self.triage_agent._extract_entities(request_text)
            for model in expected_models:
                # Check if any extracted model contains the expected pattern
                found = any(model.lower() in extracted.lower() for extracted in entities.models)
                assert found, f"Model {model} not found in {entities.models}"
    
    @pytest.mark.unit
    def test_entity_extraction_metrics_and_time_ranges(self):
        """Test extraction of metrics and time periods from requests
        
        Business Impact: Enables targeted analysis tools based on specific
        metrics and time periods mentioned by users.
        """
        request = "Analyze latency and throughput for last 7 days, cost over 2024-01-01"
        entities = self.triage_agent._extract_entities(request)
        
        # Should extract metrics
        expected_metrics = ["latency", "throughput", "cost"]
        for metric in expected_metrics:
            assert metric in entities.metrics, f"Metric {metric} not found in {entities.metrics}"
        
        # Should extract time ranges
        assert len(entities.time_ranges) > 0
        
        # Test specific time patterns
        time_requests = [
            "last 30 days",
            "this month", 
            "2024-01-15",
            "yesterday"
        ]
        
        for time_text in time_requests:
            test_request = f"Show me costs for {time_text}"
            entities = self.triage_agent._extract_entities(test_request)
            assert len(entities.time_ranges) > 0, f"No time range found for: {time_text}"
    
    @pytest.mark.unit
    def test_entity_extraction_numerical_values(self):
        """Test extraction and classification of numerical values
        
        Business Impact: Proper classification of thresholds vs targets enables
        more accurate optimization recommendations.
        """
        # Test threshold detection
        threshold_request = "Alert when cost exceeds $1000 maximum threshold"
        entities = self.triage_agent._extract_entities(threshold_request)
        assert len(entities.thresholds) > 0
        
        # Test target detection
        target_request = "Achieve 95% accuracy target with latency goal of 100ms"
        entities = self.triage_agent._extract_entities(target_request)
        assert len(entities.targets) > 0
        
        # Test provider detection
        provider_request = "Compare AWS vs Azure vs GCP costs with OpenAI API"
        entities = self.triage_agent._extract_entities(provider_request)
        
        expected_providers = ["aws", "azure", "gcp", "openai"]
        found_providers = [p.lower() for p in entities.providers]
        for provider in expected_providers:
            assert provider in found_providers, f"Provider {provider} not found"
    
    # ========================================================================
    # INTENT DETECTION TESTS  
    # ========================================================================
    
    @pytest.mark.unit
    def test_intent_detection_primary_intents(self):
        """Test detection of primary user intents from requests
        
        Business Impact: Accurate intent detection drives correct agent routing,
        ensuring users get the right type of assistance.
        """
        # Test optimization intent
        optimize_request = "Help me optimize and reduce my AI costs"
        intent = self.triage_agent._detect_intent(optimize_request)
        assert intent.primary_intent == "optimize"
        assert intent.confidence > 0.5
        assert intent.action_required is True
        
        # Test analysis intent
        analyze_request = "I need to analyze my usage patterns and examine trends"
        intent = self.triage_agent._detect_intent(analyze_request)
        assert intent.primary_intent == "analyze"
        assert intent.confidence > 0.5
        
        # Test configuration intent
        config_request = "Please help configure and set up my API settings"
        intent = self.triage_agent._detect_intent(config_request)
        assert intent.primary_intent == "configure"
        assert intent.action_required is True
        
        # Test troubleshooting intent
        trouble_request = "Having issues with API, need to debug and fix problems"
        intent = self.triage_agent._detect_intent(trouble_request)
        assert intent.primary_intent == "troubleshoot"
    
    @pytest.mark.unit
    def test_intent_secondary_intents_detection(self):
        """Test detection of secondary intents in complex requests
        
        Business Impact: Multi-intent requests require more sophisticated
        handling with multiple agents or complex workflows.
        """
        complex_request = "Analyze my costs, then optimize performance and configure alerts"
        intent = self.triage_agent._detect_intent(complex_request)
        
        # Should detect primary intent
        assert intent.primary_intent in ["analyze", "optimize", "configure"]
        
        # Should detect secondary intents
        assert len(intent.secondary_intents) > 0
        
        # Should recognize action is required
        assert intent.action_required is True
        
        # Confidence should be reasonable
        assert 0.3 <= intent.confidence <= 1.0
    
    @pytest.mark.unit
    def test_intent_action_required_detection(self):
        """Test detection of whether user requests require action
        
        Business Impact: Determines urgency and agent priority for handling requests.
        """
        # Action required cases
        action_requests = [
            "Please help me optimize costs",
            "I need to fix this issue", 
            "Must resolve performance problems",
            "How do I configure this setting?"
        ]
        
        for request in action_requests:
            intent = self.triage_agent._detect_intent(request)
            assert intent.action_required is True, f"Action not detected for: {request}"
        
        # No action required cases
        info_requests = [
            "What is the current status?",
            "Explain how this works",
            "Show me the documentation"
        ]
        
        for request in info_requests:
            intent = self.triage_agent._detect_intent(request)
            # These might or might not require action depending on keywords
            # but should at least parse without errors
            assert isinstance(intent.action_required, bool)
    
    # ========================================================================
    # TOOL RECOMMENDATION TESTS
    # ========================================================================
    
    @pytest.mark.unit
    def test_tool_recommendation_by_category(self):
        """Test tool recommendations based on request category
        
        Business Impact: Correct tool selection improves response quality
        and reduces execution time for user requests.
        """
        # Test cost optimization tools
        entities = ExtractedEntities(models=["gpt-4"], metrics=["cost"])
        tools = self.triage_agent._recommend_tools("Cost Optimization", entities)
        
        assert len(tools.primary_tools) > 0
        assert len(tools.tool_scores) > 0
        
        # Primary tools should have higher scores than secondary
        primary_scores = [tools.tool_scores.get(tool, 0) for tool in tools.primary_tools]
        secondary_scores = [tools.tool_scores.get(tool, 0) for tool in tools.secondary_tools]
        
        if primary_scores and secondary_scores:
            assert max(primary_scores) >= max(secondary_scores)
        
        # Test performance optimization tools
        perf_entities = ExtractedEntities(metrics=["latency", "throughput"])
        perf_tools = self.triage_agent._recommend_tools("Performance Optimization", perf_entities)
        
        assert len(perf_tools.primary_tools) > 0
        
        # Test workload analysis tools
        analysis_entities = ExtractedEntities(models=["claude-3"], time_ranges=["last 30 days"])
        analysis_tools = self.triage_agent._recommend_tools("Workload Analysis", analysis_entities)
        
        assert len(analysis_tools.primary_tools) > 0
    
    @pytest.mark.unit
    def test_tool_scoring_with_entity_bonuses(self):
        """Test tool scoring system with entity-based bonuses
        
        Business Impact: Better tool scoring leads to more relevant
        tool selection and higher user satisfaction.
        """
        # Create entities with models and metrics
        entities = ExtractedEntities(
            models=["gpt-4", "claude-3"],
            metrics=["latency", "cost"]
        )
        
        tools = self.triage_agent._recommend_tools("Cost Optimization", entities)
        
        # All primary tools should have scores
        for tool in tools.primary_tools:
            assert tool in tools.tool_scores
            assert tools.tool_scores[tool] > 0
        
        # Scores should be reasonable (between 0 and 1)
        for score in tools.tool_scores.values():
            assert 0 <= score <= 1.0
        
        self.record_metric("tool_recommendation_tests_passed", 3)
    
    # ========================================================================
    # AGENT ROUTING TESTS (CRITICAL FOR GOLDEN PATH)
    # ========================================================================
    
    @pytest.mark.unit
    def test_next_agents_determination_insufficient_data(self):
        """Test agent routing when data is insufficient
        
        Business Impact: Ensures users get help gathering data before
        attempting analysis that would fail due to missing information.
        """
        # Create triage result with insufficient data
        triage_result = TriageResult(
            category="Cost Optimization",
            data_sufficiency="insufficient",
            user_intent=UserIntent(primary_intent="optimize", action_required=True)
        )
        
        next_agents = self.triage_agent._determine_next_agents(triage_result)
        
        # Should route to data helper only
        assert "data_helper" in next_agents
        assert len(next_agents) == 1  # Only data helper for insufficient data
    
    @pytest.mark.unit
    def test_next_agents_determination_partial_data(self):
        """Test agent routing when data is partially available
        
        Business Impact: Optimizes workflow by combining data gathering
        with selective analysis based on available information.
        """
        # Create triage result with partial data and optimization intent
        triage_result = TriageResult(
            category="Cost Optimization", 
            data_sufficiency="partial",
            user_intent=UserIntent(primary_intent="optimize", action_required=True)
        )
        
        next_agents = self.triage_agent._determine_next_agents(triage_result)
        
        # Should start with data helper
        assert "data_helper" in next_agents
        assert next_agents[0] == "data_helper"  # Should be first
        
        # Should include optimization for optimization intent
        assert "optimization" in next_agents
        
        # Should include actions for action_required
        assert "actions" in next_agents
    
    @pytest.mark.unit
    def test_next_agents_determination_sufficient_data(self):
        """Test agent routing when sufficient data is available
        
        Business Impact: Enables direct execution of analysis and optimization
        without unnecessary data gathering delays.
        """
        # Test analysis intent with sufficient data
        analysis_result = TriageResult(
            category="Workload Analysis",
            data_sufficiency="sufficient",
            user_intent=UserIntent(primary_intent="analyze", action_required=False)
        )
        
        next_agents = self.triage_agent._determine_next_agents(analysis_result)
        
        # Should include data agent for analysis
        assert "data" in next_agents
        
        # Test optimization intent with sufficient data
        optimization_result = TriageResult(
            category="Cost Optimization",
            data_sufficiency="sufficient", 
            user_intent=UserIntent(primary_intent="optimize", action_required=True)
        )
        
        next_agents = self.triage_agent._determine_next_agents(optimization_result)
        
        # Should include both data and optimization
        assert "data" in next_agents
        assert "optimization" in next_agents
        assert "actions" in next_agents  # action_required=True
        
        # Data should come before optimization
        data_index = next_agents.index("data")
        opt_index = next_agents.index("optimization")
        assert data_index < opt_index
    
    @pytest.mark.unit
    def test_next_agents_fallback_to_data_helper(self):
        """Test fallback to data helper when no specific agents match
        
        Business Impact: Ensures all users get assistance even when
        requests don't match standard patterns.
        """
        # Create triage result with no clear intent match
        unclear_result = TriageResult(
            category="General Request",
            data_sufficiency="unknown",
            user_intent=UserIntent(primary_intent="unknown", action_required=False)
        )
        
        next_agents = self.triage_agent._determine_next_agents(unclear_result)
        
        # Should fallback to data helper
        assert "data_helper" in next_agents
        assert len(next_agents) >= 1
    
    # ========================================================================
    # INTENT ANALYSIS HELPER TESTS
    # ========================================================================
    
    @pytest.mark.unit
    def test_intent_analysis_keywords(self):
        """Test intent analysis helper methods
        
        Business Impact: Accurate intent classification improves agent routing.
        """
        # Test analysis intent detection
        assert self.triage_agent._intent_needs_analysis("analyze costs")
        assert self.triage_agent._intent_needs_analysis("review performance")
        assert self.triage_agent._intent_needs_analysis("investigate trends")
        assert not self.triage_agent._intent_needs_analysis("simple request")
        
        # Test optimization intent detection  
        assert self.triage_agent._intent_needs_optimization("optimize performance")
        assert self.triage_agent._intent_needs_optimization("reduce costs")
        assert self.triage_agent._intent_needs_optimization("improve efficiency")
        assert not self.triage_agent._intent_needs_optimization("show status")
        
        # Test action intent detection
        assert self.triage_agent._intent_needs_actions("implement solution")
        assert self.triage_agent._intent_needs_actions("deploy changes") 
        assert self.triage_agent._intent_needs_actions("setup configuration")
        assert not self.triage_agent._intent_needs_actions("understand concept")
    
    # ========================================================================
    # FALLBACK MECHANISM TESTS
    # ========================================================================
    
    @pytest.mark.unit
    def test_fallback_category_classification(self):
        """Test fallback classification when LLM is unavailable
        
        Business Impact: Ensures system continues to function even when
        LLM services are down, maintaining basic user assistance.
        """
        # Test cost optimization fallback
        cost_request = "Help reduce my expensive AI bills and save money"
        result = self.triage_agent._create_fallback_result(cost_request)
        
        assert result.category == "Cost Optimization"
        assert result.confidence_score == 0.3  # Lower confidence for fallback
        assert result.metadata["fallback"] is True
        
        # Test performance optimization fallback
        perf_request = "Fix slow response times and improve performance bottlenecks"
        result = self.triage_agent._create_fallback_result(perf_request)
        
        assert result.category == "Performance Optimization"
        assert result.confidence_score == 0.3
        
        # Test workload analysis fallback
        analysis_request = "Analyze my usage patterns and examine trends"
        result = self.triage_agent._create_fallback_result(analysis_request)
        
        assert result.category == "Workload Analysis"
        
        # Test general request fallback
        unclear_request = "Hello, can you help me?"
        result = self.triage_agent._create_fallback_result(unclear_request)
        
        assert result.category == "General Request"
    
    @pytest.mark.unit 
    def test_fallback_keyword_scoring_with_priorities(self):
        """Test fallback keyword scoring with category priorities
        
        Business Impact: Ensures most relevant category is selected
        when multiple keywords match.
        """
        # Request with multiple category keywords
        multi_request = "Analyze costs and optimize performance with configuration"
        result = self.triage_agent._create_fallback_result(multi_request)
        
        # Should pick highest priority category (Cost Optimization = priority 10)
        assert result.category in ["Cost Optimization", "Performance Optimization", "Workload Analysis"]
        
        # Test priority ordering
        request_priorities = [
            ("reduce costs optimize", "Cost Optimization"),  # Highest priority
            ("improve performance speed", "Performance Optimization"),  # Second highest
            ("analyze usage patterns", "Workload Analysis"),  # Third highest
        ]
        
        for request_text, expected_category in request_priorities:
            result = self.triage_agent._create_fallback_result(request_text)
            assert result.category == expected_category
    
    @pytest.mark.unit
    def test_fallback_priority_determination(self):
        """Test priority determination in fallback scenarios
        
        Business Impact: Ensures urgent requests get appropriate priority
        even when LLM processing fails.
        """
        # High priority keywords
        urgent_request = "URGENT: Critical issue needs immediate fix ASAP"
        result = self.triage_agent._create_fallback_result(urgent_request)
        assert result.priority == Priority.HIGH
        
        # Low priority keywords
        casual_request = "When you can, low priority question eventually"
        result = self.triage_agent._create_fallback_result(casual_request)
        assert result.priority == Priority.LOW
        
        # Default medium priority
        normal_request = "Standard optimization request"
        result = self.triage_agent._create_fallback_result(normal_request)
        assert result.priority == Priority.MEDIUM
    
    @pytest.mark.unit
    def test_fallback_result_completeness(self):
        """Test that fallback results include all required fields
        
        Business Impact: Ensures downstream agents receive complete
        information even in fallback scenarios.
        """
        request = "Help optimize my costs"
        result = self.triage_agent._create_fallback_result(request)
        
        # Verify all required fields are present
        assert isinstance(result.category, str)
        assert isinstance(result.priority, Priority)
        assert isinstance(result.complexity, Complexity)
        assert isinstance(result.confidence_score, float)
        assert isinstance(result.data_sufficiency, str)
        assert isinstance(result.extracted_entities, ExtractedEntities)
        assert isinstance(result.user_intent, UserIntent)
        assert isinstance(result.tool_recommendation, ToolRecommendation)
        assert isinstance(result.next_steps, list)
        assert isinstance(result.metadata, dict)
        assert isinstance(result.reasoning, str)
        
        # Verify fallback metadata
        assert result.metadata["fallback"] is True
        assert "fallback_reason" in result.metadata
        assert "processing_time" in result.metadata
    
    # ========================================================================
    # PERFORMANCE AND TIMING TESTS
    # ========================================================================
    
    @pytest.mark.unit
    def test_triage_performance_requirements(self):
        """Test triage performance meets business requirements
        
        Business Impact: Fast triage response times improve user experience
        and perceived system responsiveness.
        """
        start_time = time.time()
        
        # Test fallback processing speed (no LLM calls)
        request = "Optimize my costs quickly"
        result = self.triage_agent._create_fallback_result(request)
        
        processing_time = time.time() - start_time
        
        # Fallback should be very fast (< 100ms for unit test)
        assert processing_time < 0.1, f"Fallback took {processing_time:.3f}s, should be < 0.1s"
        
        # Record performance metrics
        self.record_metric("fallback_processing_time_ms", processing_time * 1000)
        self.record_metric("performance_requirement_met", processing_time < 0.1)
    
    @pytest.mark.unit
    def test_request_hash_generation_consistency(self):
        """Test request hash generation for caching consistency
        
        Business Impact: Consistent hashing enables effective caching
        of triage results for improved performance.
        """
        request1 = "Optimize my AWS costs"
        request2 = "optimize my aws costs"  # Different case
        request3 = " Optimize my AWS costs "  # Extra whitespace
        
        # Generate hashes
        hash1 = self.triage_agent._generate_request_hash(request1, self.user_context)
        hash2 = self.triage_agent._generate_request_hash(request2, self.user_context)
        hash3 = self.triage_agent._generate_request_hash(request3, self.user_context)
        
        # Should normalize to same hash (case insensitive, trimmed)
        assert hash1 == hash2 == hash3
        
        # Different user should produce different hash
        other_context = MockUserExecutionContext(
            user_id="other_user",
            request_id="other_req", 
            thread_id="other_thread",
            run_id="other_run",
            session_id="other_session",
            metadata={}
        )
        
        hash_other = self.triage_agent._generate_request_hash(request1, other_context)
        assert hash1 != hash_other
    
    # ========================================================================
    # ERROR HANDLING TESTS
    # ========================================================================
    
    @pytest.mark.unit
    def test_error_result_creation(self):
        """Test error result creation for exception scenarios
        
        Business Impact: Graceful error handling prevents system crashes
        and provides meaningful feedback to users.
        """
        error_message = "LLM service unavailable"
        error_result = self.triage_agent._create_error_result(error_message)
        
        # Verify error result structure
        assert error_result["success"] is False
        assert error_result["error"] == error_message
        assert error_result["category"] == "Error"
        assert error_result["priority"] == "high"
        assert error_result["data_sufficiency"] == "insufficient"
        assert error_result["next_agents"] == []
        assert "error_time" in error_result["metadata"]
        assert error_result["metadata"]["error_type"] == "triage_failure"
    
    @pytest.mark.unit
    async def test_execute_with_missing_context(self):
        """Test execute method behavior when context is missing
        
        Business Impact: Robust error handling prevents crashes when
        system state is inconsistent.
        """
        # Create agent without context
        agent_no_context = UnifiedTriageAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher,
            context=None
        )
        
        # Mock WebSocket methods 
        agent_no_context.emit_agent_started = AsyncMock()
        agent_no_context.emit_error = AsyncMock()
        
        # Execute should handle missing context gracefully
        state = MockState(original_request="Test request")
        result = await agent_no_context.execute(state)
        
        # Should return error result
        assert result["success"] is False
        assert "context" in result["error"].lower()
    
    @pytest.mark.unit
    async def test_execute_with_invalid_request(self):
        """Test execute method with invalid request data
        
        Business Impact: Input validation prevents processing of
        malicious or malformed requests.
        """
        # Test with empty request
        empty_state = MockState(original_request="")
        result = await self.triage_agent.execute(empty_state)
        
        # Should return error or fallback result
        assert isinstance(result, dict)
        if not result.get("success", True):
            assert "error" in result
        else:
            # If fallback was used, should have low confidence
            assert result.get("confidence_score", 1.0) <= 0.5
        
        # Test with malicious request
        malicious_state = MockState(original_request="<script>alert('xss')</script>")
        result = await self.triage_agent.execute(malicious_state)
        
        # Should either reject or handle safely
        assert isinstance(result, dict)
    
    # ========================================================================
    # FACTORY PATTERN TESTS
    # ========================================================================
    
    @pytest.mark.unit
    def test_factory_creates_isolated_instances(self):
        """Test that factory creates properly isolated agent instances
        
        Business Impact: User isolation is critical for multi-tenant system.
        Ensures users cannot see each other's data or interfere with execution.
        """
        # Create two contexts for different users
        context1 = MockUserExecutionContext(
            user_id="user1",
            request_id="req1",
            thread_id="thread1", 
            run_id="run1",
            session_id="session1",
            metadata={}
        )
        
        context2 = MockUserExecutionContext(
            user_id="user2", 
            request_id="req2",
            thread_id="thread2",
            run_id="run2", 
            session_id="session2",
            metadata={}
        )
        
        # Create agents using factory
        agent1 = UnifiedTriageAgentFactory.create_for_context(
            context=context1,
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
        
        agent2 = UnifiedTriageAgentFactory.create_for_context(
            context=context2,
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
        
        # Verify isolation
        assert agent1 is not agent2
        assert agent1.context is not agent2.context
        assert agent1.context.user_id != agent2.context.user_id
        assert agent1.context.request_id != agent2.context.request_id
        
        # Verify proper initialization
        assert agent1.execution_priority == 0
        assert agent2.execution_priority == 0
        assert agent1.context.user_id == "user1"
        assert agent2.context.user_id == "user2"
    
    @pytest.mark.unit
    def test_factory_with_websocket_bridge(self):
        """Test factory integration with WebSocket bridge
        
        Business Impact: WebSocket integration enables real-time user feedback
        during triage processing.
        """
        mock_websocket_bridge = Mock()
        
        agent = UnifiedTriageAgentFactory.create_for_context(
            context=self.user_context,
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher,
            websocket_bridge=mock_websocket_bridge
        )
        
        # Verify WebSocket bridge was set (would need actual implementation to verify)
        assert agent is not None
        assert agent.execution_priority == 0
    
    # ========================================================================
    # COMPREHENSIVE INTEGRATION TEST
    # ========================================================================
    
    @pytest.mark.unit
    async def test_complete_triage_flow_with_fallback(self):
        """Test complete triage flow using fallback mechanisms
        
        Business Impact: End-to-end validation ensures triage provides
        complete results that enable downstream agent execution.
        """
        # Setup: Mock LLM failure to force fallback
        self.mock_llm_manager.generate_structured_response = AsyncMock(side_effect=Exception("LLM unavailable"))
        self.mock_llm_manager.generate_response = AsyncMock(side_effect=Exception("LLM unavailable"))
        
        # Execute complete triage flow
        state = MockState(original_request="Help me optimize my AWS costs to reduce spending")
        
        start_time = time.time()
        result = await self.triage_agent.execute(state, self.user_context)
        execution_time = time.time() - start_time
        
        # Verify successful completion with fallback
        assert result["success"] is True
        assert result["category"] == "Cost Optimization"  # Should classify correctly
        assert result["priority"] in ["critical", "high", "medium", "low"]
        assert result["complexity"] in ["high", "medium", "low"]
        assert result["data_sufficiency"] in ["sufficient", "partial", "insufficient"]
        assert isinstance(result["next_agents"], list)
        assert len(result["next_agents"]) > 0
        
        # Verify confidence is appropriately low for fallback
        assert result["confidence_score"] <= 0.5
        
        # Verify entities were extracted
        assert "entities" in result
        assert "intent" in result
        assert "tools" in result
        
        # Verify metadata includes fallback information
        metadata = result["metadata"] 
        assert metadata.get("fallback") is True
        
        # Verify performance
        assert execution_time < 1.0, f"Triage took {execution_time:.3f}s, should be < 1.0s"
        
        # Record comprehensive metrics
        self.record_metric("complete_triage_execution_time", execution_time)
        self.record_metric("triage_category_accuracy", result["category"] == "Cost Optimization")
        self.record_metric("next_agents_provided", len(result["next_agents"]))
        self.record_metric("fallback_execution_success", True)
        
        # Verify WebSocket events were called
        self.triage_agent.emit_agent_started.assert_called_once()
        self.triage_agent.emit_thinking.assert_called_once()
        self.triage_agent.emit_agent_completed.assert_called_once()
        
        # Verify metadata storage calls
        assert self.triage_agent.store_metadata_result.call_count >= 4  # Multiple metadata calls
    
    def teardown_method(self, method=None):
        """Cleanup after each test"""
        # Record final test metrics
        metrics = self.get_all_metrics()
        total_tests = sum(1 for key in metrics.keys() if key.endswith("_tests_passed"))
        
        self.record_metric("total_unit_tests_executed", total_tests)
        self.record_metric("triage_logic_validation_complete", True)
        
        # Call parent teardown
        super().teardown_method(method)