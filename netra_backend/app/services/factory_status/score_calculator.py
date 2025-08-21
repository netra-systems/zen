"""Score calculator for compliance metrics."""

from datetime import datetime
from typing import Dict, Any

from netra_backend.app.services.factory_status.spec_analyzer_core import ComplianceScore


class ScoreCalculator:
    """Calculates compliance scores."""
    
    def calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted overall score."""
        weights = self._get_score_weights()
        total = self._calculate_weighted_sum(scores, weights)
        return min(100, max(0, total))
    
    def _get_score_weights(self) -> Dict[str, float]:
        """Get scoring weights for different categories."""
        return {
            "architecture": 0.3, "type_safety": 0.25,
            "spec_alignment": 0.2, "test_coverage": 0.15,
            "documentation": 0.1
        }
    
    def _calculate_weighted_sum(self, scores: Dict[str, float], weights: Dict[str, float]) -> float:
        """Calculate weighted sum of scores."""
        return sum(scores.get(k, 0) * v for k, v in weights.items())
    
    def calculate_module_score(self, module_metrics: Dict[str, Any]) -> ComplianceScore:
        """Calculate score for a single module."""
        scores = module_metrics["scores"]
        base_data = self._build_compliance_base_data(module_metrics, scores)
        individual_scores = self._extract_individual_scores(scores)
        return ComplianceScore(**base_data, **individual_scores)
    
    def _build_compliance_base_data(self, module_metrics: Dict[str, Any], scores: Dict[str, float]) -> Dict[str, Any]:
        """Build base compliance score data."""
        return {
            "module_name": module_metrics["name"],
            "overall_score": self.calculate_overall_score(scores),
            "violations": module_metrics.get("violations", []),
            "timestamp": datetime.utcnow()
        }
    
    def _extract_individual_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Extract individual score components."""
        return {
            "architecture_score": scores.get("architecture", 0),
            "type_safety_score": scores.get("type_safety", 0),
            "spec_alignment_score": scores.get("spec_alignment", 0),
            "test_coverage_score": scores.get("test_coverage", 0),
            "documentation_score": scores.get("documentation", 0)
        }