"""
Quality report generation for corpus operations
Handles comprehensive report creation and recommendations
"""

from datetime import datetime, UTC
from typing import Dict, List, Any


class QualityReportGenerator:
    """Generates comprehensive quality reports"""
    
    async def generate_quality_report(
        self,
        corpus_id: str,
        score_dist: Dict[str, float],
        validation_summary: Dict[str, Any],
        issue_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        report_components = await self._gather_report_components(
            score_dist, validation_summary, issue_analysis
        )
        return self._build_quality_report(corpus_id, report_components)
    
    async def _gather_report_components(
        self,
        score_dist: Dict[str, float],
        validation_summary: Dict[str, Any],
        issue_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gather all components for quality report."""
        recommendations = await self._generate_recommendations(issue_analysis)
        
        return {
            "score_dist": score_dist,
            "validation_summary": validation_summary,
            "issue_analysis": issue_analysis,
            "recommendations": recommendations
        }
    
    def _build_quality_report(self, corpus_id: str, components: Dict[str, Any]) -> Dict[str, Any]:
        """Build quality report from gathered components."""
        return {
            "corpus_id": corpus_id,
            "report_timestamp": datetime.now(UTC).isoformat(),
            "quality_distribution": components["score_dist"],
            "validation_summary": components["validation_summary"],
            "issue_analysis": components["issue_analysis"],
            "recommendations": components["recommendations"],
            "overall_health": self._assess_overall_health(components["score_dist"], components["issue_analysis"])
        }
    
    async def _generate_recommendations(self, issue_analysis: Dict) -> List[str]:
        """Generate quality improvement recommendations"""
        if issue_analysis["total_issues"] == 0:
            return ["Quality metrics look good - maintain current practices"]
        
        recommendations = []
        categories = issue_analysis.get("issue_categories", {})
        self._add_category_recommendations(recommendations, categories)
        self._add_priority_recommendation(recommendations, issue_analysis.get("top_issues", []))
        
        return recommendations
    
    def _add_category_recommendations(self, recommendations: List[str], categories: Dict[str, int]) -> None:
        """Add recommendations based on issue categories."""
        if categories.get("completeness", 0) > 0:
            recommendations.append("Address data completeness issues - review missing fields")
        
        if categories.get("validation", 0) > 0:
            recommendations.append("Strengthen validation rules - check data formats and schemas")
        
        if categories.get("consistency", 0) > 0:
            recommendations.append("Improve data consistency - resolve duplicates and conflicts")
    
    def _add_priority_recommendation(self, recommendations: List[str], top_issues: List) -> None:
        """Add priority recommendation based on most common issue."""
        if len(top_issues) > 0:
            most_common_issue = top_issues[0][0]
            recommendations.append(f"Priority: Address '{most_common_issue}' issue type")
    
    def _assess_overall_health(
        self,
        score_dist: Dict[str, float],
        issue_analysis: Dict
    ) -> str:
        """Assess overall corpus health"""
        avg_score = score_dist.get("mean", 0.0)
        total_issues = issue_analysis.get("total_issues", 0)
        
        return self._determine_health_level(avg_score, total_issues)
    
    def _determine_health_level(self, avg_score: float, total_issues: int) -> str:
        """Determine health level from score and issue count."""
        if avg_score >= 0.8 and total_issues < 5:
            return "excellent"
        elif avg_score >= 0.6 and total_issues < 15:
            return "good"
        elif avg_score >= 0.4 and total_issues < 30:
            return "fair"
        else:
            return "poor"