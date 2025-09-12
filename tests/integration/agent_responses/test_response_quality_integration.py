"""
Integration Tests for Agent Response Quality and Business Value Delivery

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: User Experience & Platform Value - Ensure agents deliver high-quality, actionable responses
- Value Impact: Validates agents provide substantive business solutions (90% of platform value)
- Strategic Impact: $500K+ ARR protection - Response quality directly impacts user satisfaction and retention

This module tests agent response quality with emphasis on:
1. Response content quality and actionability
2. Business problem-solving capability
3. Response formatting and structure
4. Context awareness and personalization
5. Multi-agent coordination for complex responses

CRITICAL REQUIREMENTS per CLAUDE.md:
- NO MOCKS - use real agent systems and LLM responses
- Focus on business value and actionable insights
- Test response quality across different agent types
- Validate response structure and formatting
- Ensure responses solve real business problems
- Test context retention and personalization
"""

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import pytest

# SSOT imports following established patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Agent response infrastructure - REAL SERVICES ONLY
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher
from netra_backend.app.agents.base_agent import BaseAgent


@dataclass
class ResponseQualityMetrics:
    """Metrics for evaluating agent response quality."""
    
    # Content quality metrics
    response_length: int = 0
    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    
    # Business value metrics
    actionable_items_count: int = 0
    recommendations_count: int = 0
    insights_count: int = 0
    data_points_count: int = 0
    
    # Structure quality metrics
    has_introduction: bool = False
    has_summary: bool = False
    has_structured_format: bool = False
    has_clear_sections: bool = False
    
    # Context quality metrics
    addresses_user_question: bool = False
    uses_domain_context: bool = False
    personalizes_response: bool = False
    maintains_conversation_context: bool = False
    
    # Technical quality metrics
    response_time: float = 0.0
    tool_usage_count: int = 0
    error_indicators_count: int = 0
    
    def calculate_quality_score(self) -> float:
        """Calculate overall quality score (0-100)."""
        score = 0
        
        # Content quality (25 points)
        if self.word_count >= 50:
            score += min(25, self.word_count / 20)
        
        # Business value (30 points)
        business_value = (
            self.actionable_items_count * 3 +
            self.recommendations_count * 3 +
            self.insights_count * 2 +
            self.data_points_count * 1
        )
        score += min(30, business_value)
        
        # Structure quality (20 points)
        structure_score = 0
        if self.has_structured_format:
            structure_score += 5
        if self.has_clear_sections:
            structure_score += 5
        if self.has_introduction:
            structure_score += 5
        if self.has_summary:
            structure_score += 5
        score += structure_score
        
        # Context quality (15 points)
        context_score = 0
        if self.addresses_user_question:
            context_score += 5
        if self.uses_domain_context:
            context_score += 4
        if self.personalizes_response:
            context_score += 3
        if self.maintains_conversation_context:
            context_score += 3
        score += context_score
        
        # Technical quality (10 points)
        technical_score = 10
        if self.response_time > 30:
            technical_score -= 5
        if self.error_indicators_count > 0:
            technical_score -= self.error_indicators_count * 2
        score += max(0, technical_score)
        
        return min(100, max(0, score))


class ResponseQualityAnalyzer:
    """Analyzes agent response quality using various metrics."""
    
    def __init__(self):
        # Keywords for identifying business value elements
        self.actionable_keywords = [
            'recommend', 'suggest', 'should', 'could', 'implement', 'optimize',
            'improve', 'reduce', 'increase', 'deploy', 'configure', 'action'
        ]
        
        self.insight_keywords = [
            'analysis', 'finding', 'insight', 'trend', 'pattern', 'correlation',
            'impact', 'conclusion', 'observation', 'discovery'
        ]
        
        self.recommendation_keywords = [
            'recommendation', 'advice', 'guidance', 'best practice', 'solution',
            'approach', 'strategy', 'plan', 'proposal'
        ]
        
        self.error_keywords = [
            'error', 'failed', 'unable', 'cannot', 'issue', 'problem',
            'exception', 'timeout', 'unavailable'
        ]
    
    def analyze_response(self, response: str, user_message: str, response_time: float, tools_used: List[str] = None) -> ResponseQualityMetrics:
        """Analyze response quality and return metrics."""
        if not response:
            return ResponseQualityMetrics()
        
        metrics = ResponseQualityMetrics()
        response_lower = response.lower()
        
        # Basic content metrics
        metrics.response_length = len(response)
        metrics.word_count = len(response.split())
        metrics.sentence_count = len([s for s in response.split('.') if s.strip()])
        metrics.paragraph_count = len([p for p in response.split('\n\n') if p.strip()])
        metrics.response_time = response_time
        metrics.tool_usage_count = len(tools_used or [])
        
        # Business value analysis
        metrics.actionable_items_count = self._count_keywords(response_lower, self.actionable_keywords)
        metrics.recommendations_count = self._count_keywords(response_lower, self.recommendation_keywords)
        metrics.insights_count = self._count_keywords(response_lower, self.insight_keywords)
        metrics.error_indicators_count = self._count_keywords(response_lower, self.error_keywords)
        
        # Data points (numbers, percentages, metrics)
        metrics.data_points_count = len(re.findall(r'\d+(?:\.\d+)?%?|\$\d+(?:,\d{3})*(?:\.\d{2})?', response))
        
        # Structure analysis
        metrics.has_introduction = self._has_introduction(response)
        metrics.has_summary = self._has_summary(response)
        metrics.has_structured_format = self._has_structured_format(response)
        metrics.has_clear_sections = self._has_clear_sections(response)
        
        # Context analysis
        metrics.addresses_user_question = self._addresses_user_question(response, user_message)
        metrics.uses_domain_context = self._uses_domain_context(response)
        metrics.personalizes_response = self._personalizes_response(response)
        
        return metrics
    
    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        """Count occurrences of keywords in text."""
        count = 0
        for keyword in keywords:
            count += text.count(keyword)
        return count
    
    def _has_introduction(self, response: str) -> bool:
        """Check if response has an introduction."""
        intro_indicators = ['based on', 'analysis shows', 'here is', 'let me', 'i\'ll help']
        first_sentence = response.lower().split('.')[0] if '.' in response else response.lower()
        return any(indicator in first_sentence for indicator in intro_indicators)
    
    def _has_summary(self, response: str) -> bool:
        """Check if response has a summary or conclusion."""
        summary_indicators = ['in summary', 'to summarize', 'in conclusion', 'overall', 'key takeaway']
        return any(indicator in response.lower() for indicator in summary_indicators)
    
    def _has_structured_format(self, response: str) -> bool:
        """Check if response has structured formatting."""
        # Look for lists, bullets, numbering
        structure_indicators = ['\n-', '\n•', '\n*', '1.', '2.', '3.', '\n##', '\n###']
        return any(indicator in response for indicator in structure_indicators)
    
    def _has_clear_sections(self, response: str) -> bool:
        """Check if response has clear sections."""
        # Look for section headers or clear topic transitions
        return '\n\n' in response and len(response.split('\n\n')) >= 2
    
    def _addresses_user_question(self, response: str, user_message: str) -> bool:
        """Check if response addresses the user's question."""
        if not user_message:
            return False
        
        # Extract key terms from user message
        user_keywords = set(word.lower() for word in re.findall(r'\w+', user_message) if len(word) > 3)
        response_keywords = set(word.lower() for word in re.findall(r'\w+', response) if len(word) > 3)
        
        # Check overlap
        overlap = len(user_keywords & response_keywords)
        return overlap >= min(3, len(user_keywords) // 2)
    
    def _uses_domain_context(self, response: str) -> bool:
        """Check if response uses domain-specific context."""
        domain_indicators = [
            'system', 'performance', 'optimization', 'cost', 'efficiency',
            'infrastructure', 'analysis', 'metrics', 'data', 'report'
        ]
        return sum(1 for indicator in domain_indicators if indicator in response.lower()) >= 2
    
    def _personalizes_response(self, response: str) -> bool:
        """Check if response is personalized."""
        personal_indicators = ['your', 'you', 'specific', 'custom', 'based on your']
        return any(indicator in response.lower() for indicator in personal_indicators)


class TestResponseQualityIntegration(SSotAsyncTestCase):
    """Integration tests for agent response quality and business value delivery."""
    
    async def async_setup_method(self, method=None):
        """Set up test environment with real agent response infrastructure."""
        await super().async_setup_method(method)
        
        # Initialize environment
        self.env = get_env()
        self.set_env_var("TESTING", "true")
        self.set_env_var("TEST_MODE", "response_quality")
        
        # Initialize response quality analyzer
        self.quality_analyzer = ResponseQualityAnalyzer()
        
        # Initialize agent infrastructure
        self.agent_factory = None
        self.execution_engine = None
        self.tool_dispatcher = None
        
        # Quality metrics tracking
        self.quality_metrics = {
            'responses_analyzed': 0,
            'average_quality_score': 0.0,
            'high_quality_responses': 0,
            'business_value_responses': 0,
            'response_times': []
        }
        
        await self._initialize_response_infrastructure()
    
    async def _initialize_response_infrastructure(self):
        """Initialize real agent infrastructure for response testing."""
        try:
            # Initialize agent factory
            self.agent_factory = get_agent_instance_factory()
            
            # Initialize tool dispatcher
            self.tool_dispatcher = EnhancedToolDispatcher()
            
            # Initialize execution engine
            self.execution_engine = UserExecutionEngine(
                tool_dispatcher=self.tool_dispatcher
            )
            
            self.record_metric("response_infrastructure_init_success", True)
            
        except Exception as e:
            self.record_metric("response_infrastructure_init_error", str(e))
            raise
    
    async def _execute_and_analyze_response(
        self,
        agent_name: str,
        user_message: str,
        user_context: UserExecutionContext,
        tools_available: List[str] = None
    ) -> Tuple[AgentExecutionResult, ResponseQualityMetrics]:
        """Execute agent and analyze response quality."""
        # Create execution context
        execution_context = AgentExecutionContext(
            agent_name=agent_name,
            user_message=user_message,
            user_context=user_context,
            tools_available=tools_available or [],
            execution_id=f"quality_exec_{uuid.uuid4().hex[:8]}"
        )
        
        # Execute agent
        start_time = time.time()
        result = await self.execution_engine.execute_agent(execution_context)
        execution_time = time.time() - start_time
        
        # Analyze response quality
        response_content = result.agent_response if result else ""
        tools_used = result.tools_used if result else []
        
        quality_metrics = self.quality_analyzer.analyze_response(
            response_content,
            user_message,
            execution_time,
            tools_used
        )
        
        return result, quality_metrics
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_triage_agent_response_quality(self):
        """
        Test triage agent response quality for system analysis queries.
        
        Business Value: Validates triage agent provides high-quality initial
        analysis and routing decisions for user queries.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id=f"triage_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"triage_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"triage_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "triage_quality"}
        )
        
        # Test various triage scenarios
        test_scenarios = [
            {
                "message": "Our application is running slowly and users are complaining about response times",
                "expected_elements": ["performance", "analysis", "recommendations"],
                "min_quality_score": 70
            },
            {
                "message": "I need to optimize our cloud costs - they've increased 50% this month",
                "expected_elements": ["cost", "optimization", "analysis"],
                "min_quality_score": 70
            },
            {
                "message": "Help me understand why our database queries are taking so long",
                "expected_elements": ["database", "queries", "performance"],
                "min_quality_score": 65
            }
        ]
        
        quality_scores = []
        response_analysis = []
        
        for scenario in test_scenarios:
            # Execute triage agent
            result, quality_metrics = await self._execute_and_analyze_response(
                agent_name="triage_agent",
                user_message=scenario["message"],
                user_context=user_context,
                tools_available=["system_analyzer", "performance_monitor"]
            )
            
            # Validate execution succeeded
            self.assertIsNotNone(result, f"Triage agent should execute successfully for: {scenario['message'][:50]}...")
            self.assertTrue(result.success or result.partial_success, "Triage execution should succeed")
            
            # Validate response content
            self.assertIsNotNone(result.agent_response, "Triage agent should provide response")
            self.assertGreater(len(result.agent_response), 50, "Response should be substantial")
            
            # Calculate quality score
            quality_score = quality_metrics.calculate_quality_score()
            quality_scores.append(quality_score)
            
            # Validate quality score
            self.assertGreater(
                quality_score, 
                scenario["min_quality_score"], 
                f"Quality score {quality_score} should exceed {scenario['min_quality_score']} for: {scenario['message'][:50]}..."
            )
            
            # Validate expected elements are present
            response_lower = result.agent_response.lower()
            for element in scenario["expected_elements"]:
                self.assertIn(element, response_lower, 
                            f"Response should contain '{element}' for query about {element}")
            
            # Business value validation
            self.assertGreater(quality_metrics.actionable_items_count, 0, 
                             "Triage response should contain actionable items")
            
            response_analysis.append({
                "scenario": scenario["message"][:30] + "...",
                "quality_score": quality_score,
                "word_count": quality_metrics.word_count,
                "actionable_items": quality_metrics.actionable_items_count,
                "response_time": quality_metrics.response_time
            })
        
        # Overall quality validation
        avg_quality_score = sum(quality_scores) / len(quality_scores)
        self.assertGreater(avg_quality_score, 65, "Average triage quality should exceed 65")
        
        # Performance validation
        avg_response_time = sum(m.response_time for _, m in [
            await self._execute_and_analyze_response("triage_agent", s["message"], user_context)
            for s in test_scenarios[:1]  # Test one for timing
        ]) / 1
        
        self.record_metric("triage_avg_quality_score", avg_quality_score)
        self.record_metric("triage_scenarios_tested", len(test_scenarios))
        self.record_metric("triage_response_analysis", response_analysis)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_optimization_agent_business_value_delivery(self):
        """
        Test optimization agent delivers high business value in responses.
        
        Business Value: Validates optimization agent provides actionable
        cost savings and performance improvements with measurable impact.
        """
        # Create user context for optimization testing
        user_context = UserExecutionContext(
            user_id=f"opt_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"opt_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"opt_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "optimization_business_value"}
        )
        
        # Test optimization scenarios with expected business value
        optimization_scenarios = [
            {
                "message": "Optimize our AWS infrastructure - we're spending $10,000/month",
                "expected_business_value": {
                    "cost_savings": True,
                    "specific_recommendations": True,
                    "quantified_impact": True
                },
                "required_elements": ["cost", "savings", "AWS", "recommendations"],
                "min_quality_score": 75
            },
            {
                "message": "Our API response times are 2-3 seconds, need to improve performance",
                "expected_business_value": {
                    "performance_improvements": True,
                    "actionable_steps": True,
                    "measurable_outcomes": True
                },
                "required_elements": ["performance", "response time", "optimization", "improvement"],
                "min_quality_score": 70
            }
        ]
        
        business_value_scores = []
        optimization_results = []
        
        for scenario in optimization_scenarios:
            # Execute optimization agent
            result, quality_metrics = await self._execute_and_analyze_response(
                agent_name="apex_optimizer_agent",
                user_message=scenario["message"],
                user_context=user_context,
                tools_available=["cost_analyzer", "performance_optimizer", "system_analyzer"]
            )
            
            # Validate execution
            self.assertIsNotNone(result)
            self.assertTrue(result.success or result.partial_success)
            
            # Validate business value elements
            response_content = result.agent_response
            self.assertIsNotNone(response_content)
            
            # Check for required elements
            response_lower = response_content.lower()
            for element in scenario["required_elements"]:
                self.assertIn(element, response_lower, 
                            f"Optimization response should mention '{element}'")
            
            # Business value analysis
            business_value_score = 0
            
            # Check for cost savings indicators
            if scenario["expected_business_value"]["cost_savings"]:
                cost_indicators = ["save", "reduce cost", "optimize spending", "cost reduction"]
                if any(indicator in response_lower for indicator in cost_indicators):
                    business_value_score += 25
            
            # Check for specific recommendations
            if scenario["expected_business_value"]["specific_recommendations"]:
                if quality_metrics.recommendations_count >= 2:
                    business_value_score += 25
            
            # Check for quantified impact
            if scenario["expected_business_value"]["quantified_impact"]:
                if quality_metrics.data_points_count >= 1:
                    business_value_score += 25
            
            # Check for actionable steps
            if scenario["expected_business_value"].get("actionable_steps"):
                if quality_metrics.actionable_items_count >= 3:
                    business_value_score += 25
            
            business_value_scores.append(business_value_score)
            
            # Quality score validation
            quality_score = quality_metrics.calculate_quality_score()
            self.assertGreater(quality_score, scenario["min_quality_score"], 
                             f"Optimization quality score should exceed {scenario['min_quality_score']}")
            
            # Validate substantial content
            self.assertGreater(quality_metrics.word_count, 100, 
                             "Optimization response should be comprehensive")
            
            optimization_results.append({
                "scenario": scenario["message"][:40] + "...",
                "business_value_score": business_value_score,
                "quality_score": quality_score,
                "recommendations": quality_metrics.recommendations_count,
                "actionable_items": quality_metrics.actionable_items_count,
                "data_points": quality_metrics.data_points_count
            })
        
        # Overall business value validation
        avg_business_value = sum(business_value_scores) / len(business_value_scores)
        self.assertGreater(avg_business_value, 60, 
                         "Average business value score should exceed 60")
        
        self.record_metric("optimization_avg_business_value", avg_business_value)
        self.record_metric("optimization_results", optimization_results)
        self.record_metric("optimization_business_value_validated", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_agent_response_coordination(self):
        """
        Test response quality in multi-agent coordination scenarios.
        
        Business Value: Validates complex problems requiring multiple agents
        produce coordinated, high-quality responses.
        """
        # Create user context for multi-agent testing
        user_context = UserExecutionContext(
            user_id=f"multi_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"multi_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"multi_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "multi_agent_coordination"}
        )
        
        # Complex scenario requiring multiple agent types
        complex_query = (
            "We need a comprehensive analysis of our system: "
            "performance issues are causing customer complaints, "
            "costs are rising, and we need actionable recommendations "
            "with a detailed implementation plan."
        )
        
        # Execute multiple agents in sequence to simulate coordination
        agent_sequence = [
            {
                "agent": "triage_agent",
                "focus": "Initial analysis and problem identification",
                "tools": ["system_analyzer"]
            },
            {
                "agent": "data_helper_agent", 
                "focus": "Data gathering and performance analysis",
                "tools": ["performance_monitor", "data_processor"]
            },
            {
                "agent": "apex_optimizer_agent",
                "focus": "Optimization recommendations and implementation plan",
                "tools": ["cost_analyzer", "performance_optimizer"]
            }
        ]
        
        agent_responses = []
        cumulative_context = complex_query
        
        for step in agent_sequence:
            # Execute agent with cumulative context
            result, quality_metrics = await self._execute_and_analyze_response(
                agent_name=step["agent"],
                user_message=cumulative_context,
                user_context=user_context,
                tools_available=step["tools"]
            )
            
            # Validate execution
            self.assertIsNotNone(result, f"{step['agent']} should execute successfully")
            self.assertTrue(result.success or result.partial_success)
            
            # Quality validation
            quality_score = quality_metrics.calculate_quality_score()
            self.assertGreater(quality_score, 60, 
                             f"{step['agent']} quality score should exceed 60")
            
            # Content validation
            response_content = result.agent_response
            self.assertIsNotNone(response_content)
            self.assertGreater(len(response_content), 75, 
                             f"{step['agent']} should provide substantial response")
            
            # Context continuity validation
            self.assertTrue(quality_metrics.addresses_user_question,
                          f"{step['agent']} should address the user question")
            
            agent_responses.append({
                "agent": step["agent"],
                "quality_score": quality_score,
                "word_count": quality_metrics.word_count,
                "actionable_items": quality_metrics.actionable_items_count,
                "recommendations": quality_metrics.recommendations_count,
                "response_preview": response_content[:100] + "..."
            })
            
            # Add this agent's response to cumulative context for next agent
            cumulative_context += f"\n\nPrevious analysis from {step['agent']}: {response_content[:200]}..."
        
        # Validate coordination effectiveness
        total_actionable_items = sum(r["actionable_items"] for r in agent_responses)
        total_recommendations = sum(r["recommendations"] for r in agent_responses)
        avg_quality = sum(r["quality_score"] for r in agent_responses) / len(agent_responses)
        
        # Multi-agent coordination should produce substantial results
        self.assertGreater(total_actionable_items, 5, 
                         "Multi-agent coordination should produce multiple actionable items")
        self.assertGreater(total_recommendations, 3, 
                         "Multi-agent coordination should produce multiple recommendations")
        self.assertGreater(avg_quality, 65, 
                         "Average quality across agents should exceed 65")
        
        # Validate complementary responses (each agent should add value)
        for i, response in enumerate(agent_responses):
            self.assertGreater(response["quality_score"], 55, 
                             f"Agent {response['agent']} should meet minimum quality threshold")
            
            # Each agent should contribute meaningfully
            self.assertTrue(
                response["actionable_items"] > 0 or response["recommendations"] > 0,
                f"Agent {response['agent']} should contribute actionable value"
            )
        
        self.record_metric("multi_agent_avg_quality", avg_quality)
        self.record_metric("multi_agent_total_actionable_items", total_actionable_items)
        self.record_metric("multi_agent_total_recommendations", total_recommendations)
        self.record_metric("multi_agent_responses", agent_responses)
        self.record_metric("multi_agent_coordination_success", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_response_personalization_and_context_awareness(self):
        """
        Test agent response personalization and context awareness.
        
        Business Value: Validates agents provide personalized, context-aware
        responses that enhance user experience and engagement.
        """
        # Create user contexts with different profiles
        user_profiles = [
            {
                "user_id": f"tech_user_{uuid.uuid4().hex[:8]}",
                "profile": "technical_lead",
                "metadata": {
                    "role": "Technical Lead",
                    "experience": "Senior",
                    "preferences": "detailed_technical_analysis",
                    "context": "enterprise_infrastructure"
                },
                "query": "Optimize our microservices architecture for better performance"
            },
            {
                "user_id": f"biz_user_{uuid.uuid4().hex[:8]}",
                "profile": "business_manager", 
                "metadata": {
                    "role": "Business Manager",
                    "experience": "Business",
                    "preferences": "high_level_summary_with_roi",
                    "context": "cost_optimization"
                },
                "query": "Reduce our cloud spending while maintaining service quality"
            }
        ]
        
        personalization_results = []
        
        for profile in user_profiles:
            # Create personalized user context
            user_context = UserExecutionContext(
                user_id=profile["user_id"],
                thread_id=f"personal_thread_{uuid.uuid4().hex[:8]}",
                run_id=f"personal_run_{uuid.uuid4().hex[:8]}",
                session_metadata={
                    "test_type": "personalization",
                    **profile["metadata"]
                }
            )
            
            # Execute agent with personalized context
            result, quality_metrics = await self._execute_and_analyze_response(
                agent_name="apex_optimizer_agent",
                user_message=profile["query"],
                user_context=user_context,
                tools_available=["system_analyzer", "cost_analyzer", "performance_optimizer"]
            )
            
            # Validate execution
            self.assertIsNotNone(result)
            self.assertTrue(result.success or result.partial_success)
            
            # Analyze response for personalization
            response_content = result.agent_response
            self.assertIsNotNone(response_content)
            
            # Validate context awareness
            self.assertTrue(quality_metrics.addresses_user_question,
                          "Response should address user's specific question")
            
            # Profile-specific validation
            response_lower = response_content.lower()
            
            if profile["profile"] == "technical_lead":
                # Technical responses should be detailed and technical
                technical_terms = ["architecture", "performance", "optimization", "system", "technical"]
                technical_matches = sum(1 for term in technical_terms if term in response_lower)
                self.assertGreater(technical_matches, 2, 
                                 "Technical user should receive technical response")
                
                # Should have detailed recommendations
                self.assertGreater(quality_metrics.recommendations_count, 2,
                                 "Technical user should receive detailed recommendations")
                
            elif profile["profile"] == "business_manager":
                # Business responses should focus on ROI and high-level benefits
                business_terms = ["cost", "savings", "roi", "business", "value", "benefit"]
                business_matches = sum(1 for term in business_terms if term in response_lower)
                self.assertGreater(business_matches, 2,
                                 "Business user should receive business-focused response")
                
                # Should have cost/benefit analysis
                self.assertGreater(quality_metrics.data_points_count, 0,
                                 "Business user should receive quantified information")
            
            # Quality validation
            quality_score = quality_metrics.calculate_quality_score()
            self.assertGreater(quality_score, 65, 
                             f"Personalized response quality should exceed 65 for {profile['profile']}")
            
            # Personalization validation
            self.assertTrue(quality_metrics.personalizes_response,
                          "Response should show personalization elements")
            
            personalization_results.append({
                "profile": profile["profile"],
                "quality_score": quality_score,
                "personalizes_response": quality_metrics.personalizes_response,
                "addresses_question": quality_metrics.addresses_user_question,
                "uses_domain_context": quality_metrics.uses_domain_context,
                "word_count": quality_metrics.word_count,
                "actionable_items": quality_metrics.actionable_items_count
            })
        
        # Validate differentiation between profiles
        tech_result = personalization_results[0]
        biz_result = personalization_results[1]
        
        # Responses should be personalized differently
        self.assertNotEqual(tech_result["word_count"], biz_result["word_count"],
                          "Technical and business responses should differ in length")
        
        # Both should be high quality but potentially different styles
        for result in personalization_results:
            self.assertTrue(result["personalizes_response"],
                          f"{result['profile']} should receive personalized response")
            self.assertTrue(result["addresses_question"],
                          f"{result['profile']} response should address their question")
            self.assertGreater(result["quality_score"], 60,
                             f"{result['profile']} should receive quality response")
        
        self.record_metric("personalization_results", personalization_results)
        self.record_metric("personalization_validated", True)
        avg_personalization_quality = sum(r["quality_score"] for r in personalization_results) / len(personalization_results)
        self.record_metric("avg_personalization_quality", avg_personalization_quality)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_response_formatting_and_structure_quality(self):
        """
        Test response formatting and structure quality across different scenarios.
        
        Business Value: Ensures responses are well-structured and readable,
        improving user comprehension and action-ability.
        """
        # Create user context for formatting tests
        user_context = UserExecutionContext(
            user_id=f"format_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"format_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"format_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "formatting_quality"}
        )
        
        # Test scenarios that should produce well-structured responses
        formatting_scenarios = [
            {
                "agent": "data_helper_agent",
                "query": "Generate a comprehensive report on system performance with key metrics and recommendations",
                "expected_structure": {
                    "has_sections": True,
                    "has_lists": True,
                    "has_summary": True,
                    "min_paragraphs": 3
                }
            },
            {
                "agent": "apex_optimizer_agent", 
                "query": "Create an optimization plan for reducing costs with step-by-step implementation",
                "expected_structure": {
                    "has_numbered_steps": True,
                    "has_recommendations": True,
                    "has_introduction": True,
                    "min_word_count": 150
                }
            }
        ]
        
        formatting_results = []
        
        for scenario in formatting_scenarios:
            # Execute agent
            result, quality_metrics = await self._execute_and_analyze_response(
                agent_name=scenario["agent"],
                user_message=scenario["query"],
                user_context=user_context,
                tools_available=["system_analyzer", "performance_monitor", "report_generator"]
            )
            
            # Validate execution
            self.assertIsNotNone(result)
            self.assertTrue(result.success or result.partial_success)
            
            response_content = result.agent_response
            self.assertIsNotNone(response_content)
            
            # Structure validation
            expected = scenario["expected_structure"]
            
            if expected.get("has_sections"):
                self.assertTrue(quality_metrics.has_clear_sections,
                              f"{scenario['agent']} should provide clear sections")
            
            if expected.get("has_lists"):
                self.assertTrue(quality_metrics.has_structured_format,
                              f"{scenario['agent']} should use structured formatting")
            
            if expected.get("has_summary"):
                self.assertTrue(quality_metrics.has_summary,
                              f"{scenario['agent']} should provide summary")
            
            if expected.get("has_introduction"):
                self.assertTrue(quality_metrics.has_introduction,
                              f"{scenario['agent']} should provide introduction")
            
            if expected.get("min_paragraphs"):
                self.assertGreaterEqual(quality_metrics.paragraph_count, expected["min_paragraphs"],
                                      f"{scenario['agent']} should have at least {expected['min_paragraphs']} paragraphs")
            
            if expected.get("min_word_count"):
                self.assertGreaterEqual(quality_metrics.word_count, expected["min_word_count"],
                                      f"{scenario['agent']} should have at least {expected['min_word_count']} words")
            
            # General formatting quality
            quality_score = quality_metrics.calculate_quality_score()
            self.assertGreater(quality_score, 65,
                             f"{scenario['agent']} formatting quality should exceed 65")
            
            # Readability checks
            avg_sentence_length = quality_metrics.word_count / max(quality_metrics.sentence_count, 1)
            self.assertLess(avg_sentence_length, 30,
                          f"{scenario['agent']} should maintain readable sentence length")
            
            formatting_results.append({
                "agent": scenario["agent"],
                "quality_score": quality_score,
                "has_structured_format": quality_metrics.has_structured_format,
                "has_clear_sections": quality_metrics.has_clear_sections,
                "has_introduction": quality_metrics.has_introduction,
                "has_summary": quality_metrics.has_summary,
                "paragraph_count": quality_metrics.paragraph_count,
                "avg_sentence_length": avg_sentence_length
            })
        
        # Overall formatting quality validation
        avg_formatting_quality = sum(r["quality_score"] for r in formatting_results) / len(formatting_results)
        self.assertGreater(avg_formatting_quality, 65,
                         "Average formatting quality should exceed 65")
        
        # Structure consistency validation
        structured_responses = sum(1 for r in formatting_results if r["has_structured_format"])
        self.assertGreater(structured_responses, 0,
                         "At least one response should have structured formatting")
        
        self.record_metric("formatting_results", formatting_results)
        self.record_metric("avg_formatting_quality", avg_formatting_quality)
        self.record_metric("structured_responses_count", structured_responses)
        self.record_metric("formatting_quality_validated", True)
    
    async def async_teardown_method(self, method=None):
        """Clean up response quality infrastructure and log comprehensive metrics."""
        try:
            # Calculate final quality metrics
            all_metrics = self.get_all_metrics()
            
            # Clean up infrastructure
            if self.execution_engine:
                await self.execution_engine.cleanup()
            
            # Log comprehensive response quality analysis
            if all_metrics:
                print(f"\nResponse Quality Integration Test Results:")
                print(f"=" * 60)
                
                # Quality scores
                quality_keys = [k for k in all_metrics.keys() if 'quality' in k and 'score' in k]
                if quality_keys:
                    print(f"Quality Scores:")
                    for key in quality_keys:
                        print(f"  {key}: {all_metrics[key]:.2f}")
                
                # Business value metrics  
                business_keys = [k for k in all_metrics.keys() if 'business' in k or 'actionable' in k]
                if business_keys:
                    print(f"\nBusiness Value Metrics:")
                    for key in business_keys:
                        print(f"  {key}: {all_metrics[key]}")
                
                # Performance metrics
                perf_keys = [k for k in all_metrics.keys() if 'time' in k or 'count' in k]
                if perf_keys:
                    print(f"\nPerformance Metrics:")
                    for key in perf_keys:
                        value = all_metrics[key]
                        if isinstance(value, float):
                            print(f"  {key}: {value:.3f}")
                        else:
                            print(f"  {key}: {value}")
                
                print(f"=" * 60)
            
            self.record_metric("response_quality_test_completed", True)
            
        except Exception as e:
            self.record_metric("test_cleanup_error", str(e))
        
        await super().async_teardown_method(method)