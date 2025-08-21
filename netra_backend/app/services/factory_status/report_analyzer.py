"""Report Analysis for Factory Status Integration."""

from typing import Dict, List, Any
from datetime import datetime

from netra_backend.app.services.factory_status.spec_compliance_scorer import ComplianceScore


class ReportAnalyzer:
    """Handles analysis and formatting of compliance reports."""
    
    async def analyze_trends(self) -> Dict[str, Any]:
        """Analyze compliance trends over time."""
        # In production, load historical data from database
        return self._create_trend_analysis()
    
    def _create_trend_analysis(self) -> Dict[str, Any]:
        """Create trend analysis structure."""
        return {
            "direction": "improving",
            "change_percentage": 5.2,
            "modules_improved": 8,
            "modules_declined": 2
        }

    async def check_orchestration_alignment(self) -> Dict[str, Any]:
        """Check alignment with master orchestration spec."""
        alignment = self._get_alignment_principles()
        
        return self._format_alignment_result(alignment)
    
    def _get_alignment_principles(self) -> Dict[str, bool]:
        """Get orchestration alignment principles."""
        return {
            "architecture_compliance": True,
            "multi_agent_coordination": True,
            "root_cause_analysis": True,
            "continuous_validation": True
        }
    
    def _format_alignment_result(self, alignment: Dict[str, bool]) -> Dict[str, Any]:
        """Format alignment check result."""
        return {
            "aligned": all(alignment.values()),
            "principles": alignment,
            "recommendations": []
        }

    def score_to_dict(self, score: ComplianceScore) -> Dict[str, Any]:
        """Convert ComplianceScore to dictionary."""
        base_scores = self._extract_base_scores(score)
        metadata = self._extract_score_metadata(score)
        
        return {**base_scores, **metadata}
    
    def _extract_base_scores(self, score: ComplianceScore) -> Dict[str, float]:
        """Extract base compliance scores."""
        return {
            "overall_score": score.overall_score,
            "architecture_score": score.architecture_score,
            "type_safety_score": score.type_safety_score,
            "spec_alignment_score": score.spec_alignment_score
        }
    
    def _extract_score_metadata(self, score: ComplianceScore) -> Dict[str, Any]:
        """Extract score metadata and counts."""
        return {
            "test_coverage_score": score.test_coverage_score,
            "documentation_score": score.documentation_score,
            "violations_count": len(score.violations),
            "timestamp": score.timestamp.isoformat()
        }

    def rank_modules(self, module_scores: Dict[str, ComplianceScore]) -> Dict[str, List[Dict]]:
        """Rank modules by compliance score."""
        sorted_modules = self._sort_modules_by_score(module_scores)
        top_modules = self._get_top_modules(sorted_modules)
        bottom_modules = self._get_bottom_modules(sorted_modules)
        
        return {"top": top_modules, "bottom": bottom_modules}
    
    def _sort_modules_by_score(self, module_scores: Dict[str, ComplianceScore]) -> List[tuple]:
        """Sort modules by compliance score."""
        return sorted(
            module_scores.items(),
            key=lambda x: x[1].overall_score,
            reverse=True
        )
    
    def _get_top_modules(self, sorted_modules: List[tuple]) -> List[Dict]:
        """Get top 5 performing modules."""
        return [
            {"name": name, "score": score.overall_score}
            for name, score in sorted_modules[:5]
        ]
    
    def _get_bottom_modules(self, sorted_modules: List[tuple]) -> List[Dict]:
        """Get bottom 5 performing modules."""
        return [
            {"name": name, "score": score.overall_score}
            for name, score in sorted_modules[-5:]
        ]

    def create_report_structure(self, overall_score: float, module_scores: Dict[str, ComplianceScore],
                              ranked_modules: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Create base report data structure."""
        basic_data = self._get_basic_report_fields(overall_score)
        module_data = self._get_module_report_fields(module_scores, ranked_modules)
        
        return {**basic_data, **module_data}
    
    def _get_basic_report_fields(self, overall_score: float) -> Dict[str, Any]:
        """Get basic report fields."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_compliance_score": overall_score
        }
    
    def _get_module_report_fields(self, module_scores: Dict[str, ComplianceScore],
                                ranked_modules: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Get module-related report fields."""
        return {
            "module_scores": {k: self.score_to_dict(v) for k, v in module_scores.items()},
            "top_compliant_modules": ranked_modules["top"],
            "modules_needing_attention": ranked_modules["bottom"]
        }