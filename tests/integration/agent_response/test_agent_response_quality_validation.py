"""Integration Tests for Agent Response Quality Validation

Tests comprehensive quality validation of agent responses including
content quality, relevance, actionability, and business value delivery.

Business Value Justification (BVJ):
- Segment: All segments - Quality/Brand/Retention
- Business Goal: Ensure high-quality AI responses that justify pricing
- Value Impact: Maintains platform reputation and user satisfaction
- Strategic Impact: Differentiates platform with superior AI quality
"""

import asyncio
import pytest
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from unittest.mock import patch

from test_framework.ssot.base_test_case import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    create_isolated_execution_context
)
from netra_backend.app.schemas.agent_result_types import TypedAgentResult
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class QualityDimension(Enum):
    """Quality dimensions for response evaluation."""
    RELEVANCE = "relevance"
    ACTIONABILITY = "actionability"
    CLARITY = "clarity"
    COMPLETENESS = "completeness"
    TECHNICAL_ACCURACY = "technical_accuracy"
    BUSINESS_VALUE = "business_value"


@dataclass
class QualityScore:
    """Quality score for a specific dimension."""
    dimension: QualityDimension
    score: float  # 0.0 to 1.0
    evidence: List[str]
    improvement_suggestions: List[str]


@dataclass
class ResponseQualityAssessment:
    """Comprehensive quality assessment of a response."""
    overall_score: float
    dimension_scores: Dict[QualityDimension, QualityScore]
    meets_business_standards: bool
    user_segment_appropriateness: str
    quality_tier: str  # "Poor", "Acceptable", "Good", "Excellent"


class ResponseQualityValidator:
    """Validator for comprehensive response quality assessment."""
    
    def __init__(self):
        self.quality_thresholds = {
            "Poor": 0.0,
            "Acceptable": 0.6,
            "Good": 0.75,
            "Excellent": 0.9
        }
        
    def validate_response_quality(self, response: Any, query: str, 
                                user_segment: str = "General") -> ResponseQualityAssessment:
        """Validate comprehensive response quality."""
        dimension_scores = {}
        
        # Evaluate each quality dimension
        dimension_scores[QualityDimension.RELEVANCE] = self._evaluate_relevance(response, query)
        dimension_scores[QualityDimension.ACTIONABILITY] = self._evaluate_actionability(response)
        dimension_scores[QualityDimension.CLARITY] = self._evaluate_clarity(response)
        dimension_scores[QualityDimension.COMPLETENESS] = self._evaluate_completeness(response, query)
        dimension_scores[QualityDimension.TECHNICAL_ACCURACY] = self._evaluate_technical_accuracy(response)
        dimension_scores[QualityDimension.BUSINESS_VALUE] = self._evaluate_business_value(response, user_segment)
        
        # Calculate overall score
        overall_score = sum(score.score for score in dimension_scores.values()) / len(dimension_scores)
        
        # Determine quality tier
        quality_tier = "Poor"
        for tier, threshold in sorted(self.quality_thresholds.items(), key=lambda x: x[1], reverse=True):
            if overall_score >= threshold:
                quality_tier = tier
                break
                
        # Determine if meets business standards
        meets_business_standards = overall_score >= 0.7  # 70% threshold for business acceptability
        
        return ResponseQualityAssessment(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            meets_business_standards=meets_business_standards,
            user_segment_appropriateness=self._assess_segment_appropriateness(response, user_segment),
            quality_tier=quality_tier
        )
        
    def _evaluate_relevance(self, response: Any, query: str) -> QualityScore:
        """Evaluate response relevance to the query."""
        score = 0.5  # Base score
        evidence = []
        suggestions = []
        
        response_text = str(response).lower() if response else ""
        query_text = query.lower()
        
        # Extract key terms from query
        query_terms = [term for term in re.findall(r'\b\w+\b', query_text) 
                      if len(term) > 3 and term not in ['what', 'how', 'when', 'where', 'why']]
        
        if query_terms:
            # Check how many query terms appear in response
            relevant_terms = [term for term in query_terms if term in response_text]
            relevance_ratio = len(relevant_terms) / len(query_terms)
            score = min(1.0, 0.4 + relevance_ratio * 0.6)
            
            if relevance_ratio > 0.7:
                evidence.append(f"Response addresses {len(relevant_terms)}/{len(query_terms)} key query terms")
            else:
                suggestions.append("Response should address more key terms from the query")
                
        if not response_text:
            score = 0.0
            suggestions.append("Response should not be empty")
            
        return QualityScore(QualityDimension.RELEVANCE, score, evidence, suggestions)
        
    def _evaluate_actionability(self, response: Any) -> QualityScore:
        """Evaluate if response provides actionable insights."""
        score = 0.5  # Base score
        evidence = []
        suggestions = []
        
        response_text = str(response).lower() if response else ""
        
        # Look for actionable language
        action_indicators = [
            'recommend', 'suggest', 'should', 'could', 'implement', 'consider',
            'optimize', 'improve', 'increase', 'reduce', 'configure', 'set up',
            'deploy', 'monitor', 'track', 'measure', 'analyze', 'review'
        ]
        
        action_count = sum(1 for indicator in action_indicators if indicator in response_text)
        
        if action_count >= 3:
            score = 0.9
            evidence.append(f"Response contains {action_count} actionable recommendations")
        elif action_count >= 1:
            score = 0.7
            evidence.append("Response provides some actionable guidance")
        else:
            score = 0.3
            suggestions.append("Response should include specific actionable recommendations")
            
        # Check for concrete examples or steps
        if any(phrase in response_text for phrase in ['for example', 'step 1', 'first', 'next']):
            score += 0.1
            evidence.append("Response includes concrete examples or steps")
            
        return QualityScore(QualityDimension.ACTIONABILITY, min(1.0, score), evidence, suggestions)
        
    def _evaluate_clarity(self, response: Any) -> QualityScore:
        """Evaluate response clarity and readability."""
        score = 0.5  # Base score
        evidence = []
        suggestions = []
        
        response_text = str(response) if response else ""
        
        if not response_text:
            return QualityScore(QualityDimension.CLARITY, 0.0, [], ["Response should not be empty"])
            
        # Basic readability checks
        sentence_count = len([s for s in response_text.split('.') if s.strip()])
        word_count = len(response_text.split())
        
        if word_count > 0:
            avg_words_per_sentence = word_count / max(1, sentence_count)
            
            # Optimal sentence length: 15-20 words
            if 10 <= avg_words_per_sentence <= 25:
                score += 0.2
                evidence.append("Response has good sentence length balance")
            elif avg_words_per_sentence > 30:
                suggestions.append("Consider shorter sentences for better readability")
                
        # Check for structure indicators
        if any(indicator in response_text for indicator in [':', '-', '1.', '[U+2022]', '\n']):
            score += 0.1
            evidence.append("Response uses structure to improve clarity")
            
        # Check for technical jargon balance
        if len(response_text) > 50:  # Only for substantial responses
            score += 0.2  # Assume reasonable jargon balance unless extremely technical
            
        return QualityScore(QualityDimension.CLARITY, min(1.0, score), evidence, suggestions)
        
    def _evaluate_completeness(self, response: Any, query: str) -> QualityScore:
        """Evaluate response completeness relative to query scope."""
        score = 0.5  # Base score
        evidence = []
        suggestions = []
        
        response_text = str(response) if response else ""
        
        if not response_text:
            return QualityScore(QualityDimension.COMPLETENESS, 0.0, [], ["Response should not be empty"])
            
        # Assess response length relative to query complexity
        query_complexity = len(query.split()) + query.count('?') * 2
        response_length = len(response_text.split())
        
        if query_complexity > 10:  # Complex query
            if response_length > 50:
                score = 0.8
                evidence.append("Response provides substantial content for complex query")
            elif response_length > 20:
                score = 0.6
                evidence.append("Response provides adequate content for complex query")
            else:
                suggestions.append("Complex query may require more detailed response")
                
        else:  # Simple query
            if response_length > 10:
                score = 0.8
                evidence.append("Response provides appropriate detail for query")
                
        return QualityScore(QualityDimension.COMPLETENESS, score, evidence, suggestions)
        
    def _evaluate_technical_accuracy(self, response: Any) -> QualityScore:
        """Evaluate technical accuracy (basic validation)."""
        score = 0.7  # Assume generally accurate unless obvious issues
        evidence = []
        suggestions = []
        
        response_text = str(response).lower() if response else ""
        
        # Check for obviously incorrect statements (basic)
        incorrect_patterns = [
            'always 100%', 'never fails', 'impossible to', 'completely secure',
            'zero latency', 'infinite storage', 'no cost'
        ]
        
        incorrect_count = sum(1 for pattern in incorrect_patterns if pattern in response_text)
        
        if incorrect_count > 0:
            score -= 0.3 * incorrect_count
            suggestions.append("Avoid absolute statements that may be technically inaccurate")
        else:
            evidence.append("No obvious technical inaccuracies detected")
            
        # Check for appropriate technical disclaimers
        if any(phrase in response_text for phrase in ['may vary', 'depending on', 'typically', 'generally']):
            score += 0.1
            evidence.append("Response includes appropriate technical qualifications")
            
        return QualityScore(QualityDimension.TECHNICAL_ACCURACY, max(0.0, min(1.0, score)), evidence, suggestions)
        
    def _evaluate_business_value(self, response: Any, user_segment: str) -> QualityScore:
        """Evaluate business value delivery."""
        score = 0.5  # Base score
        evidence = []
        suggestions = []
        
        response_text = str(response).lower() if response else ""
        
        # Business value indicators
        value_indicators = [
            'roi', 'return on investment', 'cost savings', 'efficiency', 'revenue',
            'productivity', 'competitive advantage', 'scalability', 'growth',
            'performance improvement', 'time savings', 'resource optimization'
        ]
        
        value_count = sum(1 for indicator in value_indicators if indicator in response_text)
        
        if value_count >= 2:
            score = 0.8
            evidence.append(f"Response emphasizes business value with {value_count} value indicators")
        elif value_count >= 1:
            score = 0.6
            evidence.append("Response includes some business value considerations")
        else:
            suggestions.append("Response should emphasize business value and ROI")
            
        # Segment-specific adjustments
        if user_segment == "Enterprise":
            enterprise_indicators = ['compliance', 'security', 'governance', 'audit', 'scale']
            if any(indicator in response_text for indicator in enterprise_indicators):
                score += 0.1
                evidence.append("Response addresses Enterprise-specific concerns")
        elif user_segment == "Free":
            if 'cost-effective' in response_text or 'free' in response_text:
                score += 0.1
                evidence.append("Response addresses cost concerns for Free tier users")
                
        return QualityScore(QualityDimension.BUSINESS_VALUE, min(1.0, score), evidence, suggestions)
        
    def _assess_segment_appropriateness(self, response: Any, user_segment: str) -> str:
        """Assess if response is appropriate for user segment."""
        response_text = str(response).lower() if response else ""
        
        if user_segment == "Enterprise":
            if any(term in response_text for term in ['enterprise', 'compliance', 'governance', 'security']):
                return "Highly appropriate for Enterprise segment"
            elif any(term in response_text for term in ['scale', 'infrastructure', 'performance']):
                return "Moderately appropriate for Enterprise segment"
            else:
                return "Could be more tailored to Enterprise needs"
                
        elif user_segment == "Free":
            if any(term in response_text for term in ['cost-effective', 'free', 'budget']):
                return "Well-tailored for Free tier users"
            elif len(response_text) < 200:  # Concise for free users
                return "Appropriate length for Free tier"
            else:
                return "Could be more concise for Free tier users"
                
        return "Generally appropriate for user segment"


@pytest.mark.integration
@pytest.mark.real_services
class TestAgentResponseQualityValidation(BaseIntegrationTest):
    """Test agent response quality validation scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.env = self.get_env()  # Use SSOT environment from base class
        self.quality_validator = ResponseQualityValidator()
        self.test_user_id = "test_user_quality"
        self.test_thread_id = "thread_quality_001"
        
    async def test_data_helper_agent_response_quality_meets_business_standards(self):
        """
        Test DataHelperAgent response quality meets business standards.
        
        BVJ: All segments - Quality/Brand
        Validates that data analysis responses consistently meet quality
        standards across all business dimensions.
        """
        # GIVEN: A user execution context and quality assessment framework
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            business_query = "Analyze customer acquisition costs and recommend optimization strategies for our SaaS platform"
            
            # WHEN: Agent generates response for quality assessment
            result = await agent.run(context, query=business_query)
            
            # THEN: Response quality meets business standards
            assert result is not None, "DataHelper must generate response for quality assessment"
            
            if isinstance(result, TypedAgentResult) and result.success:
                # Assess response quality
                quality_assessment = self.quality_validator.validate_response_quality(
                    response=result.result,
                    query=business_query,
                    user_segment="Mid"
                )
                
                # Validate overall quality
                assert quality_assessment.overall_score >= 0.7, \
                    f"Response quality {quality_assessment.overall_score:.2f} below business standard (0.7)"
                
                assert quality_assessment.meets_business_standards, \
                    "Response must meet business standards for customer delivery"
                
                assert quality_assessment.quality_tier in ["Good", "Excellent"], \
                    f"Response quality tier '{quality_assessment.quality_tier}' below acceptable standards"
                
                # Validate key quality dimensions
                critical_dimensions = [QualityDimension.RELEVANCE, QualityDimension.BUSINESS_VALUE, QualityDimension.ACTIONABILITY]
                for dimension in critical_dimensions:
                    dimension_score = quality_assessment.dimension_scores[dimension].score
                    assert dimension_score >= 0.6, \
                        f"{dimension.value} score {dimension_score:.2f} below critical threshold (0.6)"
                
                logger.info(f" PASS:  DataHelper response quality validated: "
                           f"overall={quality_assessment.overall_score:.2f}, "
                           f"tier={quality_assessment.quality_tier}, "
                           f"business_standards={quality_assessment.meets_business_standards}")
                           
    async def test_optimization_agent_technical_response_quality_for_enterprise(self):
        """
        Test OptimizationsCoreSubAgent technical response quality for Enterprise users.
        
        BVJ: Enterprise - Technical Excellence/Premium Value
        Validates that optimization responses meet higher quality standards
        expected by Enterprise customers paying premium prices.
        """
        # GIVEN: An Enterprise user context and technical optimization query
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            # Set Enterprise context
            context.add_context("user_segment", "Enterprise")
            context.add_context("subscription_tier", "Premium")
            
            agent = OptimizationsCoreSubAgent()
            technical_query = "Provide infrastructure optimization recommendations for scaling our AI/ML workloads to handle 10x traffic growth while maintaining sub-100ms latency"
            
            # WHEN: Agent generates technical response for Enterprise user
            result = await agent.run(context, query=technical_query)
            
            # THEN: Response quality meets Enterprise standards
            assert result is not None, "OptimizationsCore must generate response for Enterprise assessment"
            
            if isinstance(result, TypedAgentResult) and result.success:
                # Assess response quality with Enterprise standards
                quality_assessment = self.quality_validator.validate_response_quality(
                    response=result.result,
                    query=technical_query,
                    user_segment="Enterprise"
                )
                
                # Enterprise quality requirements (higher thresholds)
                ENTERPRISE_QUALITY_THRESHOLD = 0.8
                assert quality_assessment.overall_score >= ENTERPRISE_QUALITY_THRESHOLD, \
                    f"Enterprise response quality {quality_assessment.overall_score:.2f} below threshold ({ENTERPRISE_QUALITY_THRESHOLD})"
                
                assert quality_assessment.quality_tier in ["Good", "Excellent"], \
                    f"Enterprise response quality tier '{quality_assessment.quality_tier}' insufficient"
                
                # Validate Enterprise-specific quality dimensions
                enterprise_dimensions = [
                    QualityDimension.TECHNICAL_ACCURACY,
                    QualityDimension.COMPLETENESS,
                    QualityDimension.ACTIONABILITY
                ]
                
                for dimension in enterprise_dimensions:
                    dimension_score = quality_assessment.dimension_scores[dimension].score
                    assert dimension_score >= 0.75, \
                        f"Enterprise {dimension.value} score {dimension_score:.2f} below threshold (0.75)"
                
                # Validate Enterprise segment appropriateness
                assert "highly appropriate" in quality_assessment.user_segment_appropriateness.lower() or \
                       "moderately appropriate" in quality_assessment.user_segment_appropriateness.lower(), \
                    f"Response not appropriate for Enterprise: {quality_assessment.user_segment_appropriateness}"
                
                logger.info(f" PASS:  Enterprise optimization response quality validated: "
                           f"overall={quality_assessment.overall_score:.2f}, "
                           f"tier={quality_assessment.quality_tier}, "
                           f"appropriateness='{quality_assessment.user_segment_appropriateness}'")
                           
    async def test_response_quality_consistency_across_query_types(self):
        """
        Test response quality consistency across different query types.
        
        BVJ: All segments - Brand/Reliability
        Validates that agents maintain consistent quality across various
        query types and complexity levels.
        """
        # GIVEN: Multiple query types with different complexity levels
        query_scenarios = [
            {"query": "What is AI optimization?", "complexity": "Simple", "expected_tier": "Acceptable"},
            {"query": "How can I optimize my database performance for better AI model training?", "complexity": "Medium", "expected_tier": "Good"},
            {"query": "Design a comprehensive infrastructure optimization strategy for a multi-cloud AI platform handling real-time analytics with sub-10ms latency requirements", "complexity": "Complex", "expected_tier": "Good"}
        ]
        
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            quality_assessments = []
            
            # WHEN: Agent handles queries of varying complexity
            for scenario in query_scenarios:
                result = await agent.run(context, query=scenario["query"])
                
                if isinstance(result, TypedAgentResult) and result.success:
                    assessment = self.quality_validator.validate_response_quality(
                        response=result.result,
                        query=scenario["query"],
                        user_segment="General"
                    )
                    assessment.query_complexity = scenario["complexity"]
                    assessment.expected_tier = scenario["expected_tier"]
                    quality_assessments.append(assessment)
            
            # THEN: Quality is consistent across query types
            assert len(quality_assessments) >= 2, "Multiple quality assessments needed for consistency test"
            
            overall_scores = [assessment.overall_score for assessment in quality_assessments]
            avg_quality = sum(overall_scores) / len(overall_scores)
            quality_variance = sum((score - avg_quality) ** 2 for score in overall_scores) / len(overall_scores)
            
            # Quality consistency requirements
            assert avg_quality >= 0.6, f"Average quality {avg_quality:.2f} below consistency threshold"
            assert quality_variance < 0.05, f"Quality variance {quality_variance:.3f} too high (inconsistent quality)"
            
            # Validate each assessment meets minimum standards
            for assessment in quality_assessments:
                assert assessment.meets_business_standards, \
                    f"Query '{assessment.query_complexity}' complexity response doesn't meet business standards"
                
                # Validate tier meets expectations
                tier_hierarchy = {"Poor": 0, "Acceptable": 1, "Good": 2, "Excellent": 3}
                actual_tier_value = tier_hierarchy.get(assessment.quality_tier, 0)
                expected_tier_value = tier_hierarchy.get(assessment.expected_tier, 1)
                
                assert actual_tier_value >= expected_tier_value, \
                    f"{assessment.query_complexity} query: quality tier '{assessment.quality_tier}' below expected '{assessment.expected_tier}'"
            
            logger.info(f" PASS:  Quality consistency validated across query types: "
                       f"avg_quality={avg_quality:.2f}, variance={quality_variance:.3f}, "
                       f"assessments={len(quality_assessments)}")
                       
    async def test_response_quality_improvement_feedback_loop(self):
        """
        Test response quality improvement through feedback loop.
        
        BVJ: Platform/Internal - Continuous Improvement
        Validates that quality assessments provide actionable feedback
        for improving response quality over time.
        """
        # GIVEN: A user execution context and quality improvement scenario
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            improvement_query = "Help me reduce infrastructure costs"
            
            # WHEN: Response is generated and assessed for improvement opportunities
            result = await agent.run(context, query=improvement_query)
            
            if isinstance(result, TypedAgentResult) and result.success:
                initial_assessment = self.quality_validator.validate_response_quality(
                    response=result.result,
                    query=improvement_query,
                    user_segment="General"
                )
                
                # THEN: Quality assessment provides actionable improvement feedback
                improvement_suggestions = []
                for dimension, score_info in initial_assessment.dimension_scores.items():
                    improvement_suggestions.extend(score_info.improvement_suggestions)
                
                # Validate feedback is actionable
                assert len(improvement_suggestions) <= 10, "Feedback should be focused and actionable, not overwhelming"
                
                # Categorize improvement areas
                improvement_areas = {
                    "content": [],
                    "structure": [],
                    "business_value": [],
                    "technical": []
                }
                
                for suggestion in improvement_suggestions:
                    suggestion_lower = suggestion.lower()
                    if any(term in suggestion_lower for term in ['actionable', 'recommend', 'specific']):
                        improvement_areas["content"].append(suggestion)
                    elif any(term in suggestion_lower for term in ['structure', 'format', 'clarity']):
                        improvement_areas["structure"].append(suggestion)
                    elif any(term in suggestion_lower for term in ['business', 'value', 'roi']):
                        improvement_areas["business_value"].append(suggestion)
                    elif any(term in suggestion_lower for term in ['technical', 'accuracy']):
                        improvement_areas["technical"].append(suggestion)
                
                # Validate improvement opportunities are identified
                if initial_assessment.overall_score < 0.9:  # Room for improvement
                    total_suggestions = sum(len(suggestions) for suggestions in improvement_areas.values())
                    assert total_suggestions > 0, "Quality assessment should identify improvement opportunities"
                
                # Validate dimension-specific feedback
                for dimension, score_info in initial_assessment.dimension_scores.items():
                    if score_info.score < 0.8:  # Below excellence
                        assert len(score_info.improvement_suggestions) > 0, \
                            f"{dimension.value} score {score_info.score:.2f} should have improvement suggestions"
                
                logger.info(f" PASS:  Quality improvement feedback validated: "
                           f"overall_score={initial_assessment.overall_score:.2f}, "
                           f"total_suggestions={len(improvement_suggestions)}, "
                           f"improvement_areas={[(area, len(suggestions)) for area, suggestions in improvement_areas.items() if suggestions]}")
                           
    def teardown_method(self):
        """Clean up test resources."""
        super().teardown_method()