"""
Business Value Validation Helpers for E2E Agent Golden Path Tests

This module provides utilities to validate that agent responses deliver substantive
business value rather than just technical success. These validators ensure agents
provide actionable insights and cost optimization recommendations.

Business Justification:
- Protects $500K+ ARR by ensuring agent responses have substance
- Validates core value proposition of AI-powered cost optimization
- Prevents technical success from masking business value failures
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ResponseQualityLevel(Enum):
    """Classification levels for agent response quality"""
    EXCELLENT = "excellent"      # Exceeds expectations with detailed insights
    GOOD = "good"               # Meets expectations with actionable content
    ACCEPTABLE = "acceptable"   # Basic requirements met
    POOR = "poor"              # Lacks substance or actionability
    INADEQUATE = "inadequate"   # Technical success but no business value


@dataclass
class BusinessValueMetrics:
    """Metrics for evaluating business value delivery in agent responses"""

    # Response Content Analysis
    word_count: int = 0
    sentence_count: int = 0
    technical_depth_score: float = 0.0

    # Business Value Indicators
    cost_savings_mentioned: bool = False
    quantified_recommendations: int = 0
    actionable_steps_count: int = 0
    specific_technologies_mentioned: int = 0

    # Quality Scores (0.0 to 1.0)
    relevance_score: float = 0.0
    completeness_score: float = 0.0
    actionability_score: float = 0.0
    business_impact_score: float = 0.0

    # Overall Assessment
    quality_level: ResponseQualityLevel = ResponseQualityLevel.INADEQUATE
    overall_score: float = 0.0
    passes_business_threshold: bool = False


class AgentResponseQualityValidator:
    """Validates agent response quality and business value delivery"""

    # Business value keywords that indicate substantive responses
    COST_OPTIMIZATION_KEYWORDS = [
        'cost', 'savings', 'optimize', 'reduce', 'efficiency', 'budget',
        'spend', 'pricing', 'billing', 'allocation', 'resource management'
    ]

    ACTIONABLE_KEYWORDS = [
        'recommend', 'suggest', 'implement', 'configure', 'setup',
        'deploy', 'migration', 'strategy', 'plan', 'approach'
    ]

    TECHNICAL_DEPTH_KEYWORDS = [
        'api', 'infrastructure', 'architecture', 'performance', 'monitoring',
        'scaling', 'configuration', 'integration', 'deployment', 'security'
    ]

    def __init__(self, business_threshold: float = 0.6):
        """
        Initialize validator with configurable business value threshold.

        Args:
            business_threshold: Minimum overall score required for business value (0.0-1.0)
        """
        self.business_threshold = business_threshold

    def validate_response_quality(self, response_content: str,
                                query_context: Optional[str] = None) -> BusinessValueMetrics:
        """
        Comprehensive validation of agent response quality and business value.

        Args:
            response_content: The agent's response text
            query_context: Original user query for relevance assessment

        Returns:
            BusinessValueMetrics with complete assessment
        """
        metrics = BusinessValueMetrics()

        if not response_content or not response_content.strip():
            return metrics  # Returns inadequate quality by default

        # Basic content analysis
        metrics.word_count = len(response_content.split())
        metrics.sentence_count = len([s for s in response_content.split('.') if s.strip()])

        # Business value indicator analysis
        metrics = self._analyze_business_value_indicators(response_content, metrics)

        # Quality scoring
        metrics = self._calculate_quality_scores(response_content, query_context, metrics)

        # Overall assessment
        metrics = self._determine_overall_quality(metrics)

        return metrics

    def _analyze_business_value_indicators(self, content: str,
                                         metrics: BusinessValueMetrics) -> BusinessValueMetrics:
        """Analyze content for business value indicators"""
        content_lower = content.lower()

        # Check for cost optimization mentions
        metrics.cost_savings_mentioned = any(
            keyword in content_lower for keyword in self.COST_OPTIMIZATION_KEYWORDS
        )

        # Count quantified recommendations (numbers with units/percentages)
        number_patterns = [
            r'\d+%',  # Percentages
            r'\$\d+',  # Dollar amounts
            r'\d+\s*(seconds?|minutes?|hours?|days?|months?)',  # Time units
            r'\d+\s*(GB|MB|TB|instances?|servers?|requests?)',  # Technical units
        ]

        for pattern in number_patterns:
            metrics.quantified_recommendations += len(re.findall(pattern, content, re.IGNORECASE))

        # Count actionable steps (imperative language)
        actionable_patterns = [
            r'(you should|i recommend|consider|implement|configure|setup|deploy)',
            r'(step \d+|first|next|then|finally)',
            r'(upgrade|migrate|switch|enable|disable|optimize)'
        ]

        for pattern in actionable_patterns:
            metrics.actionable_steps_count += len(re.findall(pattern, content, re.IGNORECASE))

        # Count specific technologies mentioned
        metrics.specific_technologies_mentioned = len([
            keyword for keyword in self.TECHNICAL_DEPTH_KEYWORDS
            if keyword in content_lower
        ])

        return metrics

    def _calculate_quality_scores(self, content: str, query_context: Optional[str],
                                metrics: BusinessValueMetrics) -> BusinessValueMetrics:
        """Calculate individual quality dimension scores"""

        # Relevance score (0.0 - 1.0)
        if query_context:
            # Simple relevance check based on keyword overlap
            query_words = set(query_context.lower().split())
            content_words = set(content.lower().split())
            if query_words:
                overlap = len(query_words.intersection(content_words))
                metrics.relevance_score = min(overlap / len(query_words), 1.0)
        else:
            # Default relevance if no query context
            metrics.relevance_score = 0.8 if metrics.word_count > 50 else 0.4

        # Completeness score based on content depth
        if metrics.word_count >= 200 and metrics.sentence_count >= 5:
            metrics.completeness_score = 1.0
        elif metrics.word_count >= 100 and metrics.sentence_count >= 3:
            metrics.completeness_score = 0.7
        elif metrics.word_count >= 50:
            metrics.completeness_score = 0.5
        else:
            metrics.completeness_score = 0.2

        # Actionability score based on actionable content
        actionable_score = min(metrics.actionable_steps_count * 0.2, 1.0)
        quantified_score = min(metrics.quantified_recommendations * 0.3, 1.0)
        metrics.actionability_score = (actionable_score + quantified_score) / 2

        # Business impact score
        cost_score = 0.5 if metrics.cost_savings_mentioned else 0.0
        tech_score = min(metrics.specific_technologies_mentioned * 0.1, 0.5)
        metrics.business_impact_score = cost_score + tech_score

        return metrics

    def _determine_overall_quality(self, metrics: BusinessValueMetrics) -> BusinessValueMetrics:
        """Determine overall quality level and pass/fail status"""

        # Calculate weighted overall score
        weights = {
            'relevance': 0.25,
            'completeness': 0.25,
            'actionability': 0.3,
            'business_impact': 0.2
        }

        metrics.overall_score = (
            weights['relevance'] * metrics.relevance_score +
            weights['completeness'] * metrics.completeness_score +
            weights['actionability'] * metrics.actionability_score +
            weights['business_impact'] * metrics.business_impact_score
        )

        # Determine quality level
        if metrics.overall_score >= 0.9:
            metrics.quality_level = ResponseQualityLevel.EXCELLENT
        elif metrics.overall_score >= 0.75:
            metrics.quality_level = ResponseQualityLevel.GOOD
        elif metrics.overall_score >= 0.6:
            metrics.quality_level = ResponseQualityLevel.ACCEPTABLE
        elif metrics.overall_score >= 0.4:
            metrics.quality_level = ResponseQualityLevel.POOR
        else:
            metrics.quality_level = ResponseQualityLevel.INADEQUATE

        # Business threshold check
        metrics.passes_business_threshold = metrics.overall_score >= self.business_threshold

        return metrics


class CostOptimizationValidator:
    """Specialized validator for AI cost optimization responses"""

    COST_OPTIMIZATION_REQUIREMENTS = [
        'specific_savings_amount',      # Must mention dollar amounts or percentages
        'actionable_recommendations',   # Must provide implementable steps
        'technology_specificity',       # Must reference specific AI/cloud technologies
        'timeframe_estimates',          # Should mention implementation timeframes
        'measurement_metrics'           # Should explain how to measure success
    ]

    def validate_cost_optimization_response(self, response_content: str) -> Dict[str, Any]:
        """
        Validate response specifically for AI cost optimization business value.

        Returns:
            Dict with validation results for each requirement
        """
        validation_results = {
            'requirements_met': {},
            'overall_score': 0.0,
            'passes_cost_optimization_test': False,
            'business_value_summary': ''
        }

        content_lower = response_content.lower()

        # Check each requirement
        requirements_scores = {}

        # Specific savings amount
        has_savings = bool(re.search(r'(\$\d+|\d+%|\d+\s*percent)', response_content, re.IGNORECASE))
        requirements_scores['specific_savings_amount'] = 1.0 if has_savings else 0.0

        # Actionable recommendations
        action_patterns = r'(implement|configure|switch to|upgrade|migrate|optimize|reduce|eliminate)'
        action_count = len(re.findall(action_patterns, content_lower))
        requirements_scores['actionable_recommendations'] = min(action_count * 0.25, 1.0)

        # Technology specificity
        tech_patterns = r'(aws|azure|gcp|openai|anthropic|gpu|cpu|api|kubernetes|docker)'
        tech_count = len(re.findall(tech_patterns, content_lower))
        requirements_scores['technology_specificity'] = min(tech_count * 0.2, 1.0)

        # Timeframe estimates
        time_patterns = r'(\d+\s*(day|week|month|hour)|immediately|short.?term|long.?term)'
        has_timeframe = bool(re.search(time_patterns, content_lower))
        requirements_scores['timeframe_estimates'] = 0.8 if has_timeframe else 0.0

        # Measurement metrics
        metric_patterns = r'(monitor|measure|track|metrics|kpi|benchmark|baseline)'
        has_metrics = bool(re.search(metric_patterns, content_lower))
        requirements_scores['measurement_metrics'] = 0.7 if has_metrics else 0.0

        # Calculate overall score
        validation_results['requirements_met'] = requirements_scores
        validation_results['overall_score'] = sum(requirements_scores.values()) / len(requirements_scores)

        # Pass/fail determination (need at least 60% score with savings mentioned)
        validation_results['passes_cost_optimization_test'] = (
            validation_results['overall_score'] >= 0.6 and
            requirements_scores['specific_savings_amount'] > 0
        )

        # Generate business value summary
        validation_results['business_value_summary'] = self._generate_business_value_summary(
            requirements_scores, validation_results['overall_score']
        )

        return validation_results

    def _generate_business_value_summary(self, scores: Dict[str, float],
                                       overall_score: float) -> str:
        """Generate human-readable summary of business value assessment"""

        strong_areas = [req for req, score in scores.items() if score >= 0.8]
        weak_areas = [req for req, score in scores.items() if score < 0.4]

        summary_parts = []

        if overall_score >= 0.8:
            summary_parts.append("EXCELLENT business value delivery")
        elif overall_score >= 0.6:
            summary_parts.append("GOOD business value delivery")
        elif overall_score >= 0.4:
            summary_parts.append("ACCEPTABLE business value delivery")
        else:
            summary_parts.append("INADEQUATE business value delivery")

        if strong_areas:
            summary_parts.append(f"Strong in: {', '.join(strong_areas)}")

        if weak_areas:
            summary_parts.append(f"Needs improvement: {', '.join(weak_areas)}")

        return ". ".join(summary_parts)


def validate_agent_business_value(response_content: str,
                                query_context: Optional[str] = None,
                                specialized_validation: str = None) -> Dict[str, Any]:
    """
    Comprehensive business value validation for agent responses.

    Args:
        response_content: Agent response text
        query_context: Original user query
        specialized_validation: Type of specialized validation ('cost_optimization', etc.)

    Returns:
        Complete validation results with business value assessment
    """
    # General quality validation
    quality_validator = AgentResponseQualityValidator()
    quality_metrics = quality_validator.validate_response_quality(
        response_content, query_context
    )

    validation_results = {
        'general_quality': quality_metrics,
        'passes_business_threshold': quality_metrics.passes_business_threshold,
        'overall_assessment': quality_metrics.quality_level.value,
        'specialized_validation': None
    }

    # Specialized validation if requested
    if specialized_validation == 'cost_optimization':
        cost_validator = CostOptimizationValidator()
        cost_results = cost_validator.validate_cost_optimization_response(response_content)
        validation_results['specialized_validation'] = cost_results

        # Override pass/fail based on specialized validation
        validation_results['passes_business_threshold'] = (
            quality_metrics.passes_business_threshold and
            cost_results['passes_cost_optimization_test']
        )

    return validation_results


# Convenience functions for test usage
def assert_response_has_business_value(response_content: str,
                                     query_context: Optional[str] = None,
                                     min_score: float = 0.6):
    """
    Assert that agent response delivers sufficient business value.
    Raises AssertionError with detailed message if business value is insufficient.
    """
    results = validate_agent_business_value(response_content, query_context)

    if not results['passes_business_threshold']:
        quality = results['general_quality']
        error_msg = (
            f"Agent response failed business value validation. "
            f"Score: {quality.overall_score:.2f} (required: {min_score:.2f}). "
            f"Quality: {quality.quality_level.value}. "
            f"Issues: Word count: {quality.word_count}, "
            f"Actionable steps: {quality.actionable_steps_count}, "
            f"Cost savings mentioned: {quality.cost_savings_mentioned}. "
            f"Response preview: {response_content[:200]}..."
        )
        raise AssertionError(error_msg)


def assert_cost_optimization_value(response_content: str):
    """
    Assert that response provides specific cost optimization business value.
    """
    results = validate_agent_business_value(
        response_content,
        specialized_validation='cost_optimization'
    )

    if not results['passes_business_threshold']:
        cost_results = results['specialized_validation']
        error_msg = (
            f"Response failed cost optimization validation. "
            f"Score: {cost_results['overall_score']:.2f}. "
            f"Summary: {cost_results['business_value_summary']}. "
            f"Requirements met: {cost_results['requirements_met']}"
        )
        raise AssertionError(error_msg)