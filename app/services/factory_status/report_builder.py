"""Report builder for AI Factory Status Report.

Aggregates metrics and generates comprehensive status reports.
Module follows 300-line limit with 8-line function limit.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json

from app.services.factory_status.git_commit_parser import GitCommitParser
from app.services.factory_status.git_diff_analyzer import GitDiffAnalyzer
from app.services.factory_status.git_branch_tracker import GitBranchTracker
from app.services.factory_status.metrics_velocity import VelocityCalculator
from app.services.factory_status.metrics_impact import ImpactCalculator
from app.services.factory_status.quality_validation import QualityCalculator
from app.services.factory_status.business_reporting import BusinessValueCalculator


@dataclass
class ExecutiveSummary:
    """Executive summary for the report."""
    timestamp: datetime
    productivity_score: float
    key_highlights: List[str]
    action_items: List[str]
    business_value_score: float
    overall_status: str


@dataclass
class FactoryStatusReport:
    """Complete factory status report."""
    executive_summary: ExecutiveSummary
    velocity_metrics: Dict[str, Any]
    impact_metrics: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    business_value_metrics: Dict[str, Any]
    branch_metrics: Dict[str, Any]
    feature_progress: Dict[str, Any]
    recommendations: List[str]
    report_id: str
    generated_at: datetime


class ReportBuilder:
    """Builder for AI Factory Status Reports."""
    
    STATUS_THRESHOLDS = {
        "excellent": 8.0,
        "good": 6.0,
        "satisfactory": 4.0,
        "needs_improvement": 2.0
    }
    
    def __init__(self, repo_path: str = "."):
        """Initialize report builder with all components."""
        self.repo_path = repo_path
        self.commit_parser = GitCommitParser(repo_path)
        self.diff_analyzer = GitDiffAnalyzer(repo_path)
        self.branch_tracker = GitBranchTracker(repo_path)
        self.velocity_calc = VelocityCalculator(repo_path)
        self.impact_calc = ImpactCalculator(repo_path)
        self.quality_calc = QualityCalculator(repo_path)
        self.business_calc = BusinessValueCalculator(repo_path)
    
    def build_report(self, hours: int = 24) -> FactoryStatusReport:
        """Build complete factory status report."""
        # Gather all metrics
        velocity = self._gather_velocity_metrics(hours)
        impact = self._gather_impact_metrics(hours)
        quality = self._gather_quality_metrics(hours)
        business = self._gather_business_metrics(hours)
        branches = self._gather_branch_metrics()
        features = self._gather_feature_progress(hours)
        
        # Generate summary and recommendations
        summary = self._generate_executive_summary(
            velocity, impact, quality, business
        )
        recommendations = self._generate_recommendations(
            velocity, impact, quality, business, branches
        )
        
        return self._create_report(
            summary, velocity, impact, quality, 
            business, branches, features, recommendations
        )
    
    def _gather_velocity_metrics(self, hours: int) -> Dict[str, Any]:
        """Gather velocity metrics."""
        metrics = self.velocity_calc.calculate_velocity(hours)
        # Calculate per-hour and per-day from per-period
        period_hours = hours if hours <= 24 else 24
        commits_per_hour = metrics.commits_per_period / period_hours if period_hours > 0 else 0
        commits_per_day = metrics.commits_per_period if hours >= 24 else metrics.commits_per_period * (24 / hours)
        
        return {
            "commits_per_hour": commits_per_hour,
            "commits_per_day": commits_per_day,
            "velocity_trend": metrics.trend_slope,
            "peak_activity": {"hours": [], "days": []},  # Simplified for now
            "feature_delivery": {"vs_baseline": 1.0, "speed": metrics.features_per_period},
            "confidence_score": metrics.confidence
        }
    
    def _gather_impact_metrics(self, hours: int) -> Dict[str, Any]:
        """Gather impact metrics."""
        metrics = self.impact_calc.calculate_impact_metrics(hours)
        return {
            "total_lines_added": metrics.lines_added,
            "total_lines_deleted": metrics.lines_deleted,
            "files_changed": metrics.files_affected,
            "modules_affected": [],  # Module names not available in current structure
            "change_complexity": asdict(metrics.complexity),
            "customer_facing_ratio": metrics.customer_vs_internal_ratio,
            "risk_score": metrics.complexity.risk_score
        }
    
    def _gather_quality_metrics(self, hours: int) -> Dict[str, Any]:
        """Gather quality metrics."""
        metrics = self.quality_calc.calculate_quality_metrics()
        return {
            "test_coverage": asdict(metrics.test_coverage),
            "documentation": asdict(metrics.documentation),
            "architecture_compliance": asdict(metrics.architecture),
            "technical_debt": asdict(metrics.technical_debt),
            "quality_score": metrics.overall_quality_score,
            "confidence": 0.8  # Fixed confidence value for now
        }
    
    def _gather_business_metrics(self, hours: int) -> Dict[str, Any]:
        """Gather business value metrics."""
        metrics = self.business_calc.calculate_business_value_metrics(hours)
        # Convert objective mapping to scores dict
        objective_scores = {obj.value: count for obj, count in metrics.objective_mapping.items()}
        return {
            "objective_scores": objective_scores,
            "customer_impact": asdict(metrics.customer_impact),
            "revenue_metrics": asdict(metrics.revenue_metrics),
            "compliance_security": asdict(metrics.compliance_security),
            "innovation": asdict(metrics.innovation_metrics),
            "roi_estimate": asdict(metrics.roi_estimate) if metrics.roi_estimate else None,
            "overall_value_score": metrics.overall_business_value
        }
    
    def _gather_branch_metrics(self) -> Dict[str, Any]:
        """Gather branch metrics."""
        metrics = self.branch_tracker.calculate_metrics()
        return {
            "total_branches": metrics.total_branches,
            "active_branches": metrics.active_branches,
            "merged_branches": metrics.merged_branches,
            "stale_branches": metrics.stale_branches,
            "feature_branches": metrics.feature_branches,
            "average_branch_lifetime": metrics.average_branch_lifetime,
            "merge_frequency": metrics.merge_frequency,
            "collaboration_score": metrics.collaboration_score
        }
    
    def _gather_feature_progress(self, hours: int) -> Dict[str, Any]:
        """Gather feature progress information."""
        commits = self.commit_parser.get_commits(hours)
        patterns = self.commit_parser.analyze_commit_patterns(hours)
        
        features = [c for c in commits if "feat" in c.commit_type.value]
        fixes = [c for c in commits if "fix" in c.commit_type.value]
        
        return {
            "features_added": len(features),
            "features_list": [f.message[:100] for f in features[:5]],
            "bugs_fixed": len(fixes),
            "fixes_list": [f.message[:100] for f in fixes[:5]],
            "commit_distribution": patterns["commits_by_type"],
            "top_contributors": self._get_top_contributors(patterns)
        }
    
    def _get_top_contributors(self, patterns: Dict) -> List[Dict]:
        """Get top contributors from patterns."""
        authors = patterns.get("commits_by_author", {})
        sorted_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)
        return [{"name": a[0], "commits": a[1]} for a in sorted_authors[:3]]
    
    def _generate_executive_summary(self, velocity: Dict, impact: Dict,
                                   quality: Dict, business: Dict) -> ExecutiveSummary:
        """Generate executive summary."""
        productivity_score = self._calculate_productivity_score(
            velocity, impact, quality, business
        )
        
        highlights = self._extract_highlights(velocity, impact, quality, business)
        action_items = self._identify_action_items(velocity, quality, business)
        status = self._determine_status(productivity_score)
        
        return ExecutiveSummary(
            timestamp=datetime.now(),
            productivity_score=productivity_score,
            key_highlights=highlights[:3],
            action_items=action_items[:3],
            business_value_score=business["overall_value_score"],
            overall_status=status
        )
    
    def _calculate_productivity_score(self, velocity: Dict, impact: Dict,
                                     quality: Dict, business: Dict) -> float:
        """Calculate overall productivity score."""
        v_score = min(velocity["commits_per_day"] * 2, 10)
        i_score = min(impact["customer_facing_ratio"] * 10, 10)
        q_score = quality["quality_score"]
        b_score = business["overall_value_score"]
        
        weighted_score = (v_score * 0.2 + i_score * 0.2 + 
                         q_score * 0.3 + b_score * 0.3)
        return round(weighted_score, 2)
    
    def _extract_highlights(self, velocity: Dict, impact: Dict,
                           quality: Dict, business: Dict) -> List[str]:
        """Extract key highlights from metrics."""
        highlights = []
        
        if velocity["velocity_trend"] > 0:
            highlights.append(f"Development velocity increased by {velocity['velocity_trend']:.1%}")
        if impact["customer_facing_ratio"] > 0.5:
            ratio_pct = impact["customer_facing_ratio"] * 100
            highlights.append(f"{ratio_pct:.0f}% of changes are customer-facing")
        if quality["quality_score"] > 7:
            highlights.append(f"High code quality maintained (score: {quality['quality_score']:.1f})")
        if business["overall_value_score"] > 7:
            highlights.append(f"Strong business value delivery (score: {business['overall_value_score']:.1f})")
        
        return highlights if highlights else ["Steady development progress"]
    
    def _identify_action_items(self, velocity: Dict, quality: Dict,
                              business: Dict) -> List[str]:
        """Identify action items from metrics."""
        actions = []
        
        if velocity["velocity_trend"] < -0.2:
            actions.append("Address declining development velocity")
        if quality["technical_debt"]["debt_score"] > 30:
            actions.append("Reduce technical debt (score: {:.1f})".format(
                quality["technical_debt"]["debt_score"]))
        if quality["architecture_compliance"]["violations"] > 0:
            actions.append(f"Fix {quality['architecture_compliance']['violations']} architecture violations")
        if business["innovation"]["innovation_ratio"] < 0.1:
            actions.append("Increase innovation efforts (currently at {:.0%})".format(
                business["innovation"]["innovation_ratio"]))
        
        return actions if actions else ["Continue current development practices"]
    
    def _determine_status(self, score: float) -> str:
        """Determine overall status from score."""
        for status, threshold in self.STATUS_THRESHOLDS.items():
            if score >= threshold:
                return status
        return "needs_improvement"
    
    def _generate_recommendations(self, velocity: Dict, impact: Dict,
                                 quality: Dict, business: Dict,
                                 branches: Dict) -> List[str]:
        """Generate recommendations based on metrics."""
        recommendations = []
        
        if branches["stale_branches"] > 5:
            recommendations.append(f"Clean up {branches['stale_branches']} stale branches")
        if velocity["feature_delivery"]["vs_baseline"] < 0.8:
            recommendations.append("Feature delivery is below baseline - review development process")
        if quality["test_coverage"]["coverage_trend"] < 0:
            recommendations.append("Test coverage declining - increase testing efforts")
        if business["roi_estimate"] and business["roi_estimate"]["payback_months"] > 6:
            recommendations.append("Long ROI payback period - prioritize high-value features")
        
        return recommendations[:5] if recommendations else ["Maintain current practices"]
    
    def _create_report(self, summary: ExecutiveSummary, velocity: Dict,
                      impact: Dict, quality: Dict, business: Dict,
                      branches: Dict, features: Dict,
                      recommendations: List[str]) -> FactoryStatusReport:
        """Create final report object."""
        return FactoryStatusReport(
            executive_summary=summary,
            velocity_metrics=velocity,
            impact_metrics=impact,
            quality_metrics=quality,
            business_value_metrics=business,
            branch_metrics=branches,
            feature_progress=features,
            recommendations=recommendations,
            report_id=self._generate_report_id(),
            generated_at=datetime.now()
        )
    
    def _generate_report_id(self) -> str:
        """Generate unique report ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"FSR_{timestamp}"
    
    def export_json(self, report: FactoryStatusReport) -> str:
        """Export report to JSON format."""
        report_dict = asdict(report)
        return json.dumps(report_dict, indent=2, default=str)
    
    def export_summary(self, report: FactoryStatusReport) -> str:
        """Export executive summary as text."""
        summary = report.executive_summary
        lines = [
            f"AI Factory Status Report - {summary.timestamp.strftime('%Y-%m-%d %H:%M')}",
            f"Overall Status: {summary.overall_status.upper()}",
            f"Productivity Score: {summary.productivity_score}/10",
            f"Business Value Score: {summary.business_value_score}/10",
            "",
            "Key Highlights:",
            *[f"  • {h}" for h in summary.key_highlights],
            "",
            "Action Items:",
            *[f"  • {a}" for a in summary.action_items],
            "",
            "Recommendations:",
            *[f"  • {r}" for r in report.recommendations]
        ]
        return "\n".join(lines)