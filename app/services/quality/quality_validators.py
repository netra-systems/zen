"""
Quality Issue Detection and Improvement Suggestions
Contains functions for detecting quality issues and suggesting improvements
"""

from typing import Dict, List
from .quality_models import ValidationConfig, QualityLevel, QualityMetrics
from .quality_score_calculators import QualityScoreCalculators


class QualityValidators:
    """Collection of validation and improvement suggestion methods"""
    
    @staticmethod
    def determine_validity(metrics: QualityMetrics, config: ValidationConfig) -> bool:
        """Determine if output meets quality thresholds"""
        return (
            metrics.overall_score >= config.min_quality_score and
            metrics.specificity_score >= config.min_specificity and
            metrics.actionability_score >= config.min_actionability and
            metrics.quality_level not in [QualityLevel.POOR, QualityLevel.UNACCEPTABLE]
        )
    
    @staticmethod
    def detect_issues(output: str, scores: Dict[str, float], config: ValidationConfig) -> List[str]:
        """Detect specific quality issues"""
        issues = []
        
        if len(output) < config.min_length:
            issues.append(f"Output too short ({len(output)} chars, minimum {config.min_length})")
        
        if scores['specificity'] < 0.5:
            issues.append("High presence of generic language and vague statements")
        
        if scores['actionability'] < 0.3:
            issues.append("Lacks actionable recommendations or concrete steps")
        
        if scores['quantification'] < 0.2:
            issues.append("Missing quantifiable metrics and measurements")
        
        # Check for specific slop patterns
        if any(phrase in output.lower() for phrase in QualityScoreCalculators.GENERIC_PHRASES[:5]):
            issues.append("Contains generic AI phrases")
        
        return issues
    
    @staticmethod
    def suggest_improvements(scores: Dict[str, float]) -> List[str]:
        """Suggest improvements based on scores"""
        improvements = []
        
        if scores['specificity'] < 0.7:
            improvements.append("Add specific technical details and avoid generic language")
        
        if scores['actionability'] < 0.6:
            improvements.append("Include concrete implementation steps with parameters")
        
        if scores['quantification'] < 0.5:
            improvements.append("Add measurable metrics (percentages, times, sizes)")
        
        return improvements
    
    @staticmethod
    def determine_quality_level(overall_score: float) -> QualityLevel:
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