"""
Response Quality Evaluator - Compatibility Module for Integration Tests

This module provides a compatibility layer for integration tests that expect
a ResponseQualityEvaluator class. This wraps the existing business value
validation functionality in a compatible interface.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for integration tests
- Uses existing business value validators from test_framework
- DO NOT use in production - this is test infrastructure only

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Stability  
- Value Impact: Enables integration test collection and execution
- Strategic Impact: Maintains test coverage during system evolution
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

# Import existing business value validation functionality
from test_framework.business_value_validators import (
    AgentResponseQualityValidator,
    ResponseQualityLevel,
    BusinessValueMetrics
)

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ResponseQualityEvaluator:
    """
    Compatibility wrapper for AgentResponseQualityValidator.
    
    This class provides a clean interface for response quality evaluation
    while leveraging existing business value validation infrastructure.
    """
    
    def __init__(self):
        """Initialize the response quality evaluator."""
        self._validator = AgentResponseQualityValidator()
        logger.info("ResponseQualityEvaluator initialized (compatibility layer)")
    
    def evaluate_response_quality(
        self,
        response: str,
        context: Optional[Dict[str, Any]] = None,
        user_request: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate the quality of an agent response.
        
        Args:
            response: The agent response text to evaluate
            context: Optional context information for evaluation
            user_request: Optional original user request for relevance scoring
            
        Returns:
            Dictionary containing quality metrics and scores
        """
        try:
            # Use existing business value validator
            metrics = self._validator.evaluate_response_quality(response)
            
            # Convert to expected format for compatibility
            return {
                'overall_quality': self._get_overall_quality_level(metrics),
                'business_value_score': metrics.business_value_score,
                'technical_quality_score': metrics.technical_depth_score,
                'completeness_score': metrics.completeness_score,
                'relevance_score': metrics.relevance_score,
                'metrics': {
                    'word_count': metrics.word_count,
                    'sentence_count': metrics.sentence_count,
                    'actionable_steps_count': metrics.actionable_steps_count,
                    'cost_savings_mentioned': metrics.cost_savings_mentioned,
                    'quantified_recommendations': metrics.quantified_recommendations,
                    'specific_technologies_mentioned': metrics.specific_technologies_mentioned
                },
                'quality_level': metrics.quality_level.value if hasattr(metrics, 'quality_level') else 'good',
                'validation_passed': metrics.business_value_score >= 0.6
            }
            
        except Exception as e:
            logger.error(f"Error evaluating response quality: {e}")
            # Return minimal valid response on error
            return {
                'overall_quality': 'acceptable',
                'business_value_score': 0.5,
                'technical_quality_score': 0.5,
                'completeness_score': 0.5,
                'relevance_score': 0.5,
                'metrics': {
                    'word_count': len(response.split()) if response else 0,
                    'sentence_count': response.count('.') if response else 0,
                    'actionable_steps_count': 0,
                    'cost_savings_mentioned': False,
                    'quantified_recommendations': 0,
                    'specific_technologies_mentioned': 0
                },
                'quality_level': 'acceptable',
                'validation_passed': False,
                'error': str(e)
            }
    
    def _get_overall_quality_level(self, metrics: BusinessValueMetrics) -> str:
        """Determine overall quality level from metrics."""
        # Simple scoring logic based on business value score
        if metrics.business_value_score >= 0.8:
            return 'excellent'
        elif metrics.business_value_score >= 0.7:
            return 'good'
        elif metrics.business_value_score >= 0.6:
            return 'acceptable'
        elif metrics.business_value_score >= 0.4:
            return 'poor'
        else:
            return 'inadequate'
    
    def validate_minimum_quality(
        self,
        response: str,
        minimum_score: float = 0.6
    ) -> bool:
        """
        Validate that response meets minimum quality standards.
        
        Args:
            response: The response to validate
            minimum_score: Minimum acceptable business value score
            
        Returns:
            True if response meets minimum quality standards
        """
        try:
            evaluation = self.evaluate_response_quality(response)
            return evaluation['business_value_score'] >= minimum_score
        except Exception as e:
            logger.error(f"Error validating minimum quality: {e}")
            return False


# Export the main class for compatibility
__all__ = ['ResponseQualityEvaluator', 'ResponseQualityLevel', 'BusinessValueMetrics']