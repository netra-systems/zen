"""
Quality Issue Detection and Improvement Suggestions
Contains functions for detecting quality issues and suggesting improvements - delegates to core implementation
"""

from typing import Dict, List
from netra_backend.app.core.interfaces_quality import QualityValidator as CoreQualityValidator
from netra_backend.app.core.quality_types import ContentType, QualityLevel, QualityMetrics


class QualityValidators:
    """Collection of validation and improvement suggestion methods - delegates to core implementation"""
    
    def __init__(self):
        """Initialize with core quality validator."""
        self._core_validator = CoreQualityValidator()
    
    def determine_validity(self, metrics: QualityMetrics, content_type: ContentType, strict_mode: bool = False) -> bool:
        """Determine if output meets quality thresholds"""
        return self._core_validator.check_thresholds(metrics, content_type, strict_mode)
    
    def detect_issues(self, output: str, content_type: ContentType) -> List[str]:
        """Detect specific quality issues using core analyzer"""
        # Use core analyzer to get metrics, then extract issues
        metrics = self._analyze_with_core(output, content_type)
        return metrics.issues
    
    def suggest_improvements(self, output: str, content_type: ContentType) -> List[str]:
        """Suggest improvements based on core analysis"""
        metrics = self._analyze_with_core(output, content_type)
        return self._core_validator.generate_suggestions(metrics, content_type)
    
    def determine_quality_level(self, overall_score: float) -> QualityLevel:
        """Determine quality level based on overall score"""
        if overall_score >= 0.9:
            return QualityLevel.EXCELLENT
        elif overall_score >= 0.75:
            return QualityLevel.GOOD
        elif overall_score >= 0.6:
            return QualityLevel.ACCEPTABLE
        elif overall_score >= 0.4:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE
    
    async def _analyze_with_core(self, content: str, content_type: ContentType) -> QualityMetrics:
        """Analyze content using core validator and return metrics"""
        result = await self._core_validator.validate_content(content, content_type, {})
        return result.metrics