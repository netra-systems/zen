"""Response Quality Evaluator Service

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core AI response quality assessment
- Business Goal: Product Excellence & User Experience - Premium AI quality validation
- Value Impact: Evaluates agent response quality to ensure customer satisfaction
- Strategic Impact: Critical for product differentiation and enterprise adoption

This service provides comprehensive response quality evaluation for agent responses,
including metrics for relevance, completeness, accuracy, clarity, and business value.

ARCHITECTURE ALIGNMENT:
- SSOT service for response quality evaluation
- Integrates with agent execution pipeline for quality assessment
- Uses structured quality metrics for consistent evaluation
- Supports business scenario validation and user satisfaction prediction
"""

import asyncio
import json
import re
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum
from dataclasses import dataclass

# Type imports for response evaluation
from shared.types.core_types import UserID, ThreadID, RunID

logger = logging.getLogger(__name__)


class ResponseQualityLevel(Enum):
    """Response quality levels for evaluation."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"


@dataclass
class ResponseQualityMetrics:
    """Comprehensive response quality metrics."""
    relevance_score: float = 0.0
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    clarity_score: float = 0.0
    usefulness_score: float = 0.0
    timeliness_score: float = 0.0
    overall_quality_score: float = 0.0
    quality_level: ResponseQualityLevel = ResponseQualityLevel.UNACCEPTABLE
    business_value_delivered: bool = False
    user_satisfaction_predicted: float = 0.0


class ResponseQualityEvaluator:
    """
    Service for evaluating agent response quality across multiple dimensions.

    Provides comprehensive quality assessment including business value validation,
    user satisfaction prediction, and structured quality metrics.
    """

    def __init__(self):
        """Initialize the response quality evaluator."""
        self.quality_thresholds = {
            ResponseQualityLevel.EXCELLENT: 0.9,
            ResponseQualityLevel.GOOD: 0.75,
            ResponseQualityLevel.ACCEPTABLE: 0.6,
            ResponseQualityLevel.POOR: 0.4,
            ResponseQualityLevel.UNACCEPTABLE: 0.0
        }

        self.business_value_keywords = [
            "recommend", "strategy", "improve", "increase", "optimize",
            "implement", "plan", "analyze", "solution", "benefit",
            "roi", "impact", "growth", "efficiency", "cost",
            "revenue", "market", "competitive", "advantage", "value"
        ]

        self.quality_indicators = {
            "actionable": ["step", "action", "implement", "execute", "deploy"],
            "specific": ["percent", "%", "number", "metric", "target", "goal"],
            "structured": ["first", "second", "third", "1.", "2.", "3.", "•", "-"],
            "comprehensive": ["analyze", "comprehensive", "detailed", "thorough", "complete"]
        }

    async def evaluate_response_quality(self, response: Any, scenario: Any) -> ResponseQualityMetrics:
        """
        Evaluate response quality across multiple dimensions.

        Args:
            response: Agent response to evaluate
            scenario: Business scenario context for evaluation

        Returns:
            ResponseQualityMetrics with comprehensive quality assessment
        """
        try:
            # Convert response to string for analysis
            response_text = self._extract_response_text(response)

            if not response_text or len(response_text.strip()) < 10:
                return ResponseQualityMetrics(
                    quality_level=ResponseQualityLevel.UNACCEPTABLE,
                    overall_quality_score=0.0
                )

            # Calculate individual quality metrics
            relevance_score = await self._evaluate_relevance(response_text, scenario)
            completeness_score = await self._evaluate_completeness(response_text, scenario)
            accuracy_score = await self._evaluate_accuracy(response_text)
            clarity_score = await self._evaluate_clarity(response_text)
            usefulness_score = await self._evaluate_usefulness(response_text, scenario)
            timeliness_score = 1.0  # Assume good timeliness for now

            # Calculate overall quality score (weighted average)
            overall_quality_score = (
                relevance_score * 0.25 +
                completeness_score * 0.25 +
                accuracy_score * 0.15 +
                clarity_score * 0.15 +
                usefulness_score * 0.20
            )

            # Determine quality level
            quality_level = self._determine_quality_level(overall_quality_score)

            # Assess business value delivery
            business_value_delivered = await self._evaluate_business_value(response_text, scenario)

            # Predict user satisfaction
            user_satisfaction_predicted = min(overall_quality_score * 1.1, 1.0)

            metrics = ResponseQualityMetrics(
                relevance_score=relevance_score,
                completeness_score=completeness_score,
                accuracy_score=accuracy_score,
                clarity_score=clarity_score,
                usefulness_score=usefulness_score,
                timeliness_score=timeliness_score,
                overall_quality_score=overall_quality_score,
                quality_level=quality_level,
                business_value_delivered=business_value_delivered,
                user_satisfaction_predicted=user_satisfaction_predicted
            )

            logger.info(f"Response quality evaluation completed: {quality_level.value} (score: {overall_quality_score:.2f})")
            return metrics

        except Exception as e:
            logger.error(f"Error evaluating response quality: {e}", exc_info=True)
            return ResponseQualityMetrics(
                quality_level=ResponseQualityLevel.UNACCEPTABLE,
                overall_quality_score=0.0
            )

    def _extract_response_text(self, response: Any) -> str:
        """Extract text from response object."""
        if isinstance(response, str):
            return response
        elif hasattr(response, 'content'):
            return str(response.content)
        elif hasattr(response, 'text'):
            return str(response.text)
        elif hasattr(response, 'message'):
            return str(response.message)
        elif isinstance(response, dict):
            # Try common keys for response content
            for key in ['content', 'text', 'message', 'response', 'output']:
                if key in response:
                    return str(response[key])
            return str(response)
        else:
            return str(response)

    async def _evaluate_relevance(self, response_text: str, scenario: Any) -> float:
        """Evaluate how relevant the response is to the scenario."""
        if not scenario:
            return 0.5  # Neutral if no scenario context

        scenario_text = ""
        if hasattr(scenario, 'request_content'):
            scenario_text = scenario.request_content.lower()
        elif hasattr(scenario, 'request'):
            scenario_text = scenario.request.lower()
        elif isinstance(scenario, dict):
            scenario_text = str(scenario.get('request', scenario.get('request_content', ''))).lower()

        if not scenario_text:
            return 0.5

        response_lower = response_text.lower()

        # Extract key terms from scenario
        scenario_words = set(word.strip('.,!?') for word in scenario_text.split() if len(word) > 3)
        response_words = set(word.strip('.,!?') for word in response_lower.split() if len(word) > 3)

        if not scenario_words:
            return 0.5

        # Calculate word overlap
        common_words = scenario_words.intersection(response_words)
        relevance_score = len(common_words) / len(scenario_words)

        return min(relevance_score * 1.5, 1.0)  # Boost for good relevance

    async def _evaluate_completeness(self, response_text: str, scenario: Any) -> float:
        """Evaluate how complete the response is."""
        # Base completeness on response length and structure
        word_count = len(response_text.split())

        # Basic completeness based on length
        if word_count < 20:
            length_score = 0.2
        elif word_count < 50:
            length_score = 0.4
        elif word_count < 100:
            length_score = 0.6
        elif word_count < 200:
            length_score = 0.8
        else:
            length_score = 1.0

        # Check for structured content
        structure_score = 0.0
        if any(indicator in response_text.lower() for indicators in self.quality_indicators.values() for indicator in indicators):
            structure_score = 0.3

        # Check for expected deliverables if scenario provides them
        deliverable_score = 0.0
        if scenario and hasattr(scenario, 'expected_deliverables'):
            expected_count = len(scenario.expected_deliverables)
            if expected_count > 0:
                # Simple heuristic: check for keyword mentions
                mentions = sum(1 for deliverable in scenario.expected_deliverables
                              if any(word in response_text.lower() for word in deliverable.lower().split('_')))
                deliverable_score = mentions / expected_count

        return (length_score * 0.5 + structure_score + deliverable_score * 0.5)

    async def _evaluate_accuracy(self, response_text: str) -> float:
        """Evaluate accuracy of the response (basic heuristic)."""
        # Since we can't verify factual accuracy without external sources,
        # use confidence indicators and consistency

        confidence_indicators = [
            "according to", "research shows", "studies indicate",
            "data suggests", "analysis reveals", "evidence shows"
        ]

        uncertainty_indicators = [
            "might", "could", "possibly", "maybe", "perhaps",
            "unclear", "uncertain", "unknown"
        ]

        response_lower = response_text.lower()

        confidence_count = sum(1 for indicator in confidence_indicators if indicator in response_lower)
        uncertainty_count = sum(1 for indicator in uncertainty_indicators if indicator in response_lower)

        # Favor responses with confidence indicators, penalize excessive uncertainty
        accuracy_score = 0.7  # Base score
        accuracy_score += confidence_count * 0.1
        accuracy_score -= uncertainty_count * 0.05

        return max(0.0, min(accuracy_score, 1.0))

    async def _evaluate_clarity(self, response_text: str) -> float:
        """Evaluate clarity and readability of the response."""
        # Simple readability metrics
        sentences = response_text.split('.')
        if not sentences:
            return 0.0

        # Average sentence length
        total_words = len(response_text.split())
        avg_sentence_length = total_words / len(sentences) if sentences else 0

        # Clarity score based on sentence length (prefer moderate length)
        if 10 <= avg_sentence_length <= 25:
            length_clarity = 1.0
        elif 5 <= avg_sentence_length < 10 or 25 < avg_sentence_length <= 40:
            length_clarity = 0.7
        else:
            length_clarity = 0.4

        # Check for clear structure indicators
        structure_clarity = 0.0
        if any(indicator in response_text for indicators in self.quality_indicators["structured"] for indicator in indicators):
            structure_clarity = 0.3

        return length_clarity * 0.7 + structure_clarity

    async def _evaluate_usefulness(self, response_text: str, scenario: Any) -> float:
        """Evaluate practical usefulness of the response."""
        response_lower = response_text.lower()

        # Check for actionable content
        actionable_score = 0.0
        for indicator in self.quality_indicators["actionable"]:
            if indicator in response_lower:
                actionable_score += 0.2

        # Check for specific, measurable content
        specific_score = 0.0
        for indicator in self.quality_indicators["specific"]:
            if indicator in response_lower:
                specific_score += 0.2

        # Check for business value keywords
        business_score = 0.0
        business_mentions = sum(1 for keyword in self.business_value_keywords if keyword in response_lower)
        business_score = min(business_mentions * 0.1, 0.4)

        usefulness = min(actionable_score + specific_score + business_score, 1.0)
        return usefulness

    async def _evaluate_business_value(self, response_text: str, scenario: Any) -> bool:
        """Determine if response delivers business value."""
        response_lower = response_text.lower()

        # Check for business value indicators
        business_indicators = 0

        # Actionable recommendations
        if any(word in response_lower for word in ["recommend", "suggest", "propose", "advise"]):
            business_indicators += 1

        # Quantified impact
        if any(word in response_lower for word in ["%", "percent", "increase", "decrease", "improve"]):
            business_indicators += 1

        # Strategic content
        if any(word in response_lower for word in ["strategy", "plan", "roadmap", "approach"]):
            business_indicators += 1

        # Implementation guidance
        if any(word in response_lower for word in ["implement", "execute", "deploy", "steps"]):
            business_indicators += 1

        # Business value delivered if multiple indicators present
        return business_indicators >= 2

    def _determine_quality_level(self, overall_score: float) -> ResponseQualityLevel:
        """Determine quality level based on overall score."""
        if overall_score >= self.quality_thresholds[ResponseQualityLevel.EXCELLENT]:
            return ResponseQualityLevel.EXCELLENT
        elif overall_score >= self.quality_thresholds[ResponseQualityLevel.GOOD]:
            return ResponseQualityLevel.GOOD
        elif overall_score >= self.quality_thresholds[ResponseQualityLevel.ACCEPTABLE]:
            return ResponseQualityLevel.ACCEPTABLE
        elif overall_score >= self.quality_thresholds[ResponseQualityLevel.POOR]:
            return ResponseQualityLevel.POOR
        else:
            return ResponseQualityLevel.UNACCEPTABLE


# Create default instance for easy importing
response_quality_evaluator = ResponseQualityEvaluator()

__all__ = [
    'ResponseQualityEvaluator',
    'ResponseQualityMetrics',
    'ResponseQualityLevel',
    'response_quality_evaluator'
]