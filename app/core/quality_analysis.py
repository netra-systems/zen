"""Quality content analysis methods - Single source of truth.

Contains analysis helper methods extracted from interfaces_quality.py to maintain
the 300-line limit per CLAUDE.md requirements.
"""

import re
from typing import Dict

from app.logging_config import central_logger
from .quality_types import ContentType, QualityMetrics

logger = central_logger.get_logger(__name__)


class QualityAnalyzer:
    """Handles content quality analysis methods."""
    
    def analyze_specificity(self, content: str) -> float:
        """Analyze content specificity."""
        specific_indicators = ['parameter', 'config', 'value', 'setting', '%', 'seconds', 'bytes']
        return min(1.0, sum(1 for indicator in specific_indicators if indicator in content.lower()) / 5)
    
    def analyze_actionability(self, content: str) -> float:
        """Analyze content actionability."""
        action_words = ['run', 'execute', 'configure', 'set', 'enable', 'disable', 'install']
        return min(1.0, sum(1 for word in action_words if word in content.lower()) / 4)
    
    def analyze_quantification(self, content: str) -> float:
        """Analyze content quantification."""
        numbers = re.findall(r'\d+(?:\.\d+)?', content)
        return min(1.0, len(numbers) / 3)
    
    def analyze_relevance(self, content: str, content_type: ContentType) -> float:
        """Analyze content relevance to type."""
        # Simplified relevance scoring
        return 0.8  # Default implementation
    
    def analyze_completeness(self, content: str, content_type: ContentType) -> float:
        """Analyze content completeness."""
        return min(1.0, len(content.split()) / 50)
    
    def analyze_clarity(self, content: str) -> float:
        """Analyze content clarity."""
        avg_sentence_length = len(content.split()) / max(1, content.count('.'))
        return max(0.0, 1.0 - (avg_sentence_length - 15) / 20)
    
    def analyze_novelty(self, content: str) -> float:
        """Analyze content novelty."""
        # Simplified novelty scoring
        return 0.7  # Default implementation


class QualityIssueDetector:
    """Handles quality issue detection methods."""
    
    def count_generic_phrases(self, content: str) -> int:
        """Count generic phrases in content."""
        generic_phrases = ['in general', 'basically', 'obviously', 'clearly', 'simply']
        return sum(1 for phrase in generic_phrases if phrase in content.lower())
    
    def detect_circular_reasoning(self, content: str) -> bool:
        """Detect circular reasoning patterns."""
        return 'because it is' in content.lower() or 'it works because' in content.lower()
    
    def assess_hallucination_risk(self, content: str) -> float:
        """Assess hallucination risk."""
        # Simplified risk assessment
        return 0.1  # Default low risk
    
    def calculate_redundancy_ratio(self, content: str) -> float:
        """Calculate content redundancy ratio."""
        words = content.lower().split()
        unique_words = set(words)
        return 1.0 - (len(unique_words) / max(1, len(words)))