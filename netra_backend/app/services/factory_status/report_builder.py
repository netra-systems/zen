"""Report builder for AI Factory Status Report.

Aggregates metrics and generates comprehensive status reports.
Module follows 450-line limit with 25-line function limit.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from netra_backend.app.services.factory_status.business_reporting import (
    BusinessValueCalculator,
)
from netra_backend.app.services.factory_status.git_branch_tracker import (
    GitBranchTracker,
)
from netra_backend.app.services.factory_status.git_commit_parser import GitCommitParser
from netra_backend.app.services.factory_status.git_diff_analyzer import GitDiffAnalyzer
from netra_backend.app.services.factory_status.metrics_impact import ImpactCalculator
from netra_backend.app.services.factory_status.metrics_velocity import (
    VelocityCalculator,
)
from netra_backend.app.services.factory_status.quality_validation import (
    QualityCalculator,
)


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
        self._init_parsers(repo_path)
        self._init_calculators(repo_path)
    
    def _init_parsers(self, repo_path: str) -> None:
        """Initialize parsing components."""
        self.commit_parser = GitCommitParser(repo_path)
        self.diff_analyzer = GitDiffAnalyzer(repo_path)
        self.branch_tracker = GitBranchTracker(repo_path)
    
    def _init_calculators(self, repo_path: str) -> None:
        """Initialize calculator components."""
        self.velocity_calc = VelocityCalculator(repo_path)
        self.impact_calc = ImpactCalculator(repo_path)
        self.quality_calc = QualityCalculator(repo_path)
        self.business_calc = BusinessValueCalculator(repo_path)
    
    def build_report(self, hours: int = 24) -> FactoryStatusReport:
        """Build complete factory status report."""
        metrics = self._gather_all_metrics(hours)
        summary_data = self._generate_summary_and_recommendations(metrics)
        return self._create_report_from_data(metrics, summary_data)

    def _gather_all_metrics(self, hours: int) -> Dict[str, Any]:
        """Gather all metrics for report"""
        time_metrics = self._gather_time_based_metrics(hours)
        static_metrics = self._gather_static_metrics(hours)
        return {**time_metrics, **static_metrics}
    
    def _gather_time_based_metrics(self, hours: int) -> Dict[str, Any]:
        """Gather time-based metrics."""
        return {
            "velocity": self._gather_velocity_metrics(hours),
            "impact": self._gather_impact_metrics(hours),
            "quality": self._gather_quality_metrics(hours),
            "business": self._gather_business_metrics(hours)
        }
    
    def _gather_static_metrics(self, hours: int) -> Dict[str, Any]:
        """Gather static metrics."""
        return {
            "branches": self._gather_branch_metrics(),
            "features": self._gather_feature_progress(hours)
        }

    def _generate_summary_and_recommendations(self, metrics: Dict) -> Dict[str, Any]:
        """Generate summary and recommendations"""
        summary = self._create_executive_summary(metrics)
        recommendations = self._create_recommendations(metrics)
        return {"summary": summary, "recommendations": recommendations}
    
    def _create_executive_summary(self, metrics: Dict) -> ExecutiveSummary:
        """Create executive summary from metrics."""
        return self._generate_executive_summary(
            metrics["velocity"], metrics["impact"], 
            metrics["quality"], metrics["business"]
        )
    
    def _create_recommendations(self, metrics: Dict) -> List[str]:
        """Create recommendations from metrics."""
        return self._generate_recommendations(
            metrics["velocity"], metrics["impact"], metrics["quality"], 
            metrics["business"], metrics["branches"]
        )

    def _create_report_from_data(self, metrics: Dict, summary_data: Dict) -> FactoryStatusReport:
        """Create report from gathered data"""
        return self._create_report(
            summary_data["summary"], metrics["velocity"], metrics["impact"], 
            metrics["quality"], metrics["business"], metrics["branches"], 
            metrics["features"], summary_data["recommendations"]
        )
    
    def _gather_velocity_metrics(self, hours: int) -> Dict[str, Any]:
        """Gather velocity metrics."""
        metrics = self.velocity_calc.calculate_velocity(hours)
        period_hours = hours if hours <= 24 else 24
        commit_rates = self._calculate_commit_rates(metrics, period_hours, hours)
        return self._build_velocity_metrics(metrics, commit_rates)

    def _calculate_commit_rates(self, metrics, period_hours: int, hours: int) -> Dict[str, float]:
        """Calculate commit rates per hour and day"""
        commits_per_hour = metrics.commits_per_period / period_hours if period_hours > 0 else 0
        commits_per_day = metrics.commits_per_period if hours >= 24 else metrics.commits_per_period * (24 / hours)
        return {"per_hour": commits_per_hour, "per_day": commits_per_day}

    def _build_velocity_metrics(self, metrics, commit_rates: Dict) -> Dict[str, Any]:
        """Build velocity metrics dictionary"""
        base_metrics = self._get_base_velocity_metrics(commit_rates, metrics)
        activity_metrics = self._get_activity_metrics(metrics)
        return {**base_metrics, **activity_metrics}
    
    def _get_base_velocity_metrics(self, commit_rates: Dict, metrics) -> Dict[str, Any]:
        """Get base velocity metrics."""
        return {
            "commits_per_hour": commit_rates["per_hour"],
            "commits_per_day": commit_rates["per_day"],
            "velocity_trend": metrics.trend_slope,
            "confidence_score": metrics.confidence
        }
    
    def _get_activity_metrics(self, metrics) -> Dict[str, Any]:
        """Get activity-related metrics."""
        return {
            "peak_activity": {"hours": [], "days": []},
            "feature_delivery": {"vs_baseline": 1.0, "speed": metrics.features_per_period}
        }
    
    def _gather_impact_metrics(self, hours: int) -> Dict[str, Any]:
        """Gather impact metrics."""
        metrics = self.impact_calc.calculate_impact_metrics(hours)
        return self._build_impact_metrics(metrics)

    def _build_impact_metrics(self, metrics) -> Dict[str, Any]:
        """Build impact metrics dictionary"""
        change_metrics = self._get_change_metrics(metrics)
        risk_metrics = self._get_risk_metrics(metrics)
        return {**change_metrics, **risk_metrics}
    
    def _get_change_metrics(self, metrics) -> Dict[str, Any]:
        """Get change-related metrics."""
        return {
            "total_lines_added": metrics.lines_added,
            "total_lines_deleted": metrics.lines_deleted,
            "files_changed": metrics.files_affected,
            "modules_affected": []
        }
    
    def _get_risk_metrics(self, metrics) -> Dict[str, Any]:
        """Get risk-related metrics."""
        return {
            "change_complexity": asdict(metrics.complexity),
            "customer_facing_ratio": metrics.customer_vs_internal_ratio,
            "risk_score": metrics.complexity.risk_score
        }
    
    def _gather_quality_metrics(self, hours: int) -> Dict[str, Any]:
        """Gather quality metrics."""
        metrics = self.quality_calc.calculate_quality_metrics()
        return self._build_quality_metrics(metrics)

    def _build_quality_metrics(self, metrics) -> Dict[str, Any]:
        """Build quality metrics dictionary"""
        quality_components = self._get_quality_components(metrics)
        quality_scores = self._get_quality_scores(metrics)
        return {**quality_components, **quality_scores}
    
    def _get_quality_components(self, metrics) -> Dict[str, Any]:
        """Get quality component metrics."""
        return {
            "test_coverage": asdict(metrics.test_coverage),
            "documentation": asdict(metrics.documentation),
            "architecture_compliance": asdict(metrics.architecture),
            "technical_debt": asdict(metrics.technical_debt)
        }
    
    def _get_quality_scores(self, metrics) -> Dict[str, Any]:
        """Get quality score metrics."""
        return {
            "quality_score": metrics.overall_quality_score,
            "confidence": 0.8
        }
    
    def _gather_business_metrics(self, hours: int) -> Dict[str, Any]:
        """Gather business value metrics."""
        metrics = self.business_calc.calculate_business_value_metrics(hours)
        objective_scores = self._convert_objective_mapping(metrics)
        return self._build_business_metrics(metrics, objective_scores)

    def _convert_objective_mapping(self, metrics) -> Dict[str, int]:
        """Convert objective mapping to scores dict"""
        return {obj.value: count for obj, count in metrics.objective_mapping.items()}

    def _build_business_metrics(self, metrics, objective_scores: Dict) -> Dict[str, Any]:
        """Build business metrics dictionary"""
        core_business = self._get_core_business_metrics(metrics, objective_scores)
        extended_business = self._get_extended_business_metrics(metrics)
        return {**core_business, **extended_business}
    
    def _get_core_business_metrics(self, metrics, objective_scores: Dict) -> Dict[str, Any]:
        """Get core business metrics."""
        return {
            "objective_scores": objective_scores,
            "customer_impact": asdict(metrics.customer_impact),
            "revenue_metrics": asdict(metrics.revenue_metrics),
            "compliance_security": asdict(metrics.compliance_security)
        }
    
    def _get_extended_business_metrics(self, metrics) -> Dict[str, Any]:
        """Get extended business metrics."""
        return {
            "innovation": asdict(metrics.innovation_metrics),
            "roi_estimate": asdict(metrics.roi_estimate) if metrics.roi_estimate else None,
            "overall_value_score": metrics.overall_business_value
        }
    
    def _gather_branch_metrics(self) -> Dict[str, Any]:
        """Gather branch metrics."""
        metrics = self.branch_tracker.calculate_metrics()
        return self._build_branch_metrics(metrics)

    def _build_branch_metrics(self, metrics) -> Dict[str, Any]:
        """Build branch metrics dictionary"""
        branch_counts = self._get_branch_counts(metrics)
        branch_stats = self._get_branch_statistics(metrics)
        return {**branch_counts, **branch_stats}
    
    def _get_branch_counts(self, metrics) -> Dict[str, Any]:
        """Get branch count metrics."""
        return {
            "total_branches": metrics.total_branches,
            "active_branches": metrics.active_branches,
            "merged_branches": metrics.merged_branches,
            "stale_branches": metrics.stale_branches,
            "feature_branches": metrics.feature_branches
        }
    
    def _get_branch_statistics(self, metrics) -> Dict[str, Any]:
        """Get branch statistical metrics."""
        return {
            "average_branch_lifetime": metrics.average_branch_lifetime,
            "merge_frequency": metrics.merge_frequency,
            "collaboration_score": metrics.collaboration_score
        }
    
    def _gather_feature_progress(self, hours: int) -> Dict[str, Any]:
        """Gather feature progress information."""
        # Get both raw commits and sessions for comprehensive reporting
        commits = self.commit_parser.get_commits(hours)
        sessions = self.commit_parser.get_commit_sessions(hours)
        patterns = self.commit_parser.analyze_commit_patterns(hours)
        
        # Analyze both individual commits and sessions
        feature_data = self._analyze_feature_commits(commits)
        session_data = self._analyze_commit_sessions(sessions)
        
        return self._build_feature_progress(feature_data, patterns, session_data)

    def _analyze_feature_commits(self, commits) -> Dict[str, Any]:
        """Analyze commits for features and fixes"""
        features = self._filter_feature_commits(commits)
        fixes = self._filter_fix_commits(commits)
        return self._build_commit_analysis(features, fixes)
    
    def _filter_feature_commits(self, commits) -> List:
        """Filter commits for features."""
        return [c for c in commits if "feat" in c.commit_type.value]
    
    def _filter_fix_commits(self, commits) -> List:
        """Filter commits for fixes."""
        return [c for c in commits if "fix" in c.commit_type.value]
    
    def _build_commit_analysis(self, features: List, fixes: List) -> Dict[str, Any]:
        """Build commit analysis dictionary."""
        return {
            "features": features,
            "fixes": fixes,
            "features_count": len(features),
            "fixes_count": len(fixes)
        }

    def _analyze_commit_sessions(self, sessions) -> Dict[str, Any]:
        """Analyze commit sessions for better noise reduction."""
        if not sessions:
            return {"sessions": [], "session_count": 0}
        
        # Sort sessions by most recent first
        sorted_sessions = sorted(sessions, key=lambda s: s.end_time, reverse=True)
        
        # Get summary for top sessions
        session_summaries = []
        for session in sorted_sessions[:10]:  # Show top 10 sessions
            session_summaries.append({
                "author": session.author,
                "summary": session.summary,
                "commits": len(session.commits),
                "duration_mins": int((session.end_time - session.start_time).total_seconds() / 60),
                "files_changed": session.total_files,
                "type": session.primary_type.value
            })
        
        return {
            "sessions": session_summaries,
            "session_count": len(sessions),
            "total_commits_in_sessions": sum(len(s.commits) for s in sessions)
        }
    
    def _build_feature_progress(self, feature_data: Dict, patterns: Dict, session_data: Dict) -> Dict[str, Any]:
        """Build feature progress dictionary with session grouping."""
        feature_summary = self._get_feature_summary(feature_data)
        commit_summary = self._get_commit_summary(patterns)
        
        # Add session-based summary for noise reduction
        session_summary = {
            "work_sessions": session_data.get("session_count", 0),
            "session_details": session_data.get("sessions", [])[:5],  # Show top 5 sessions
            "grouped_commits": session_data.get("total_commits_in_sessions", 0)
        }
        
        return {**feature_summary, **commit_summary, **session_summary}
    
    def _get_feature_summary(self, feature_data: Dict) -> Dict[str, Any]:
        """Get feature summary data."""
        return {
            "features_added": feature_data["features_count"],
            "features_list": [f.message[:100] for f in feature_data["features"][:5]],
            "bugs_fixed": feature_data["fixes_count"],
            "fixes_list": [f.message[:100] for f in feature_data["fixes"][:5]]
        }
    
    def _get_commit_summary(self, patterns: Dict) -> Dict[str, Any]:
        """Get commit summary data."""
        return {
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
        summary_data = self._gather_summary_components(velocity, impact, quality, business, productivity_score)
        return self._build_executive_summary(summary_data, business)

    def _gather_summary_components(self, velocity: Dict, impact: Dict, quality: Dict, 
                                 business: Dict, productivity_score: float) -> Dict:
        """Gather components for executive summary"""
        summary_data = self._extract_summary_insights(velocity, impact, quality, business)
        return self._build_summary_components_dict(summary_data, productivity_score)
    
    def _extract_summary_insights(self, velocity: Dict, impact: Dict, quality: Dict, business: Dict) -> Dict:
        """Extract insights from all metrics."""
        return {
            "highlights": self._extract_highlights(velocity, impact, quality, business),
            "action_items": self._identify_action_items(velocity, quality, business)
        }
    
    def _build_summary_components_dict(self, summary_data: Dict, productivity_score: float) -> Dict:
        """Build summary components dictionary."""
        return {
            "productivity_score": productivity_score,
            "highlights": summary_data["highlights"],
            "action_items": summary_data["action_items"],
            "status": self._determine_status(productivity_score)
        }

    def _build_executive_summary(self, summary_data: Dict, business: Dict) -> ExecutiveSummary:
        """Build executive summary object"""
        summary_params = self._prepare_executive_summary_params(summary_data, business)
        return ExecutiveSummary(**summary_params)
    
    def _prepare_executive_summary_params(self, summary_data: Dict, business: Dict) -> Dict:
        """Prepare parameters for ExecutiveSummary construction."""
        return {
            "timestamp": datetime.now(),
            "productivity_score": summary_data["productivity_score"],
            "key_highlights": summary_data["highlights"][:3],
            "action_items": summary_data["action_items"][:3],
            "business_value_score": business["overall_value_score"],
            "overall_status": summary_data["status"]
        }
    
    def _calculate_productivity_score(self, velocity: Dict, impact: Dict,
                                     quality: Dict, business: Dict) -> float:
        """Calculate overall productivity score."""
        component_scores = self._calculate_component_scores(velocity, impact, quality, business)
        weighted_score = self._apply_score_weights(component_scores)
        return round(weighted_score, 2)

    def _calculate_component_scores(self, velocity: Dict, impact: Dict, quality: Dict, business: Dict) -> Dict:
        """Calculate individual component scores"""
        return {
            "velocity": min(velocity["commits_per_day"] * 2, 10),
            "impact": min(impact["customer_facing_ratio"] * 10, 10),
            "quality": quality["quality_score"],
            "business": business["overall_value_score"]
        }

    def _apply_score_weights(self, component_scores: Dict) -> float:
        """Apply weights to component scores"""
        return (component_scores["velocity"] * 0.2 + component_scores["impact"] * 0.2 + 
                component_scores["quality"] * 0.3 + component_scores["business"] * 0.3)
    
    def _extract_highlights(self, velocity: Dict, impact: Dict,
                           quality: Dict, business: Dict) -> List[str]:
        """Extract key highlights from metrics."""
        highlights = self._collect_all_highlights(velocity, impact, quality, business)
        return highlights if highlights else ["Steady development progress"]
    
    def _collect_all_highlights(self, velocity: Dict, impact: Dict, quality: Dict, business: Dict) -> List[str]:
        """Collect highlights from all metric categories."""
        highlights = []
        self._check_velocity_highlights(highlights, velocity)
        self._check_impact_highlights(highlights, impact)
        self._check_quality_highlights(highlights, quality)
        self._check_business_highlights(highlights, business)
        return highlights

    def _check_velocity_highlights(self, highlights: List, velocity: Dict):
        """Check velocity for highlights"""
        if velocity["velocity_trend"] > 0:
            highlights.append(f"Development velocity increased by {velocity['velocity_trend']:.1%}")

    def _check_impact_highlights(self, highlights: List, impact: Dict):
        """Check impact metrics for highlights"""
        if impact["customer_facing_ratio"] > 0.5:
            ratio_pct = impact["customer_facing_ratio"] * 100
            highlights.append(f"{ratio_pct:.0f}% of changes are customer-facing")

    def _check_quality_highlights(self, highlights: List, quality: Dict):
        """Check quality metrics for highlights"""
        if quality["quality_score"] > 7:
            highlights.append(f"High code quality maintained (score: {quality['quality_score']:.1f})")

    def _check_business_highlights(self, highlights: List, business: Dict):
        """Check business metrics for highlights"""
        if business["overall_value_score"] > 7:
            highlights.append(f"Strong business value delivery (score: {business['overall_value_score']:.1f})")
    
    def _identify_action_items(self, velocity: Dict, quality: Dict,
                              business: Dict) -> List[str]:
        """Identify action items from metrics."""
        actions = []
        self._check_velocity_actions(actions, velocity)
        self._check_quality_actions(actions, quality)
        self._check_business_actions(actions, business)
        return actions if actions else ["Continue current development practices"]

    def _check_velocity_actions(self, actions: List, velocity: Dict):
        """Check velocity for action items"""
        if velocity["velocity_trend"] < -0.2:
            actions.append("Address declining development velocity")

    def _check_quality_actions(self, actions: List, quality: Dict):
        """Check quality metrics for action items"""
        if quality["technical_debt"]["debt_score"] > 30:
            actions.append("Reduce technical debt (score: {:.1f})".format(
                quality["technical_debt"]["debt_score"]))
        
        total_violations = self._calculate_architecture_violations(quality)
        if total_violations > 0:
            actions.append(f"Fix {total_violations} architecture violations")

    def _check_business_actions(self, actions: List, business: Dict):
        """Check business metrics for action items"""
        if business["innovation"]["innovation_ratio"] < 0.1:
            actions.append("Increase innovation efforts (currently at {:.0%})".format(
                business["innovation"]["innovation_ratio"]))

    def _calculate_architecture_violations(self, quality: Dict) -> int:
        """Calculate total architecture violations"""
        arch_compliance = quality["architecture_compliance"]
        return (
            arch_compliance.get("line_limit_violations", 0) +
            arch_compliance.get("function_limit_violations", 0) +
            len(arch_compliance.get("module_violations", []))
        )
    
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
        recommendations = self._collect_all_recommendations(velocity, quality, business, branches)
        return recommendations[:5] if recommendations else ["Maintain current practices"]
    
    def _collect_all_recommendations(self, velocity: Dict, quality: Dict, business: Dict, branches: Dict) -> List[str]:
        """Collect recommendations from all metric categories."""
        recommendations = []
        self._check_branch_recommendations(recommendations, branches)
        self._check_velocity_recommendations(recommendations, velocity)
        self._check_quality_recommendations(recommendations, quality)
        self._check_business_recommendations(recommendations, business)
        return recommendations

    def _check_branch_recommendations(self, recommendations: List, branches: Dict):
        """Check branch metrics for recommendations"""
        if branches["stale_branches"] > 5:
            recommendations.append(f"Clean up {branches['stale_branches']} stale branches")

    def _check_velocity_recommendations(self, recommendations: List, velocity: Dict):
        """Check velocity metrics for recommendations"""
        if velocity["feature_delivery"]["vs_baseline"] < 0.8:
            recommendations.append("Feature delivery is below baseline - review development process")

    def _check_quality_recommendations(self, recommendations: List, quality: Dict):
        """Check quality metrics for recommendations"""
        if quality["test_coverage"]["coverage_trend"] < 0:
            recommendations.append("Test coverage declining - increase testing efforts")

    def _check_business_recommendations(self, recommendations: List, business: Dict):
        """Check business metrics for recommendations"""
        if business["roi_estimate"] and business["roi_estimate"]["payback_months"] > 6:
            recommendations.append("Long ROI payback period - prioritize high-value features")
    
    def _create_report(self, summary: ExecutiveSummary, velocity: Dict,
                      impact: Dict, quality: Dict, business: Dict,
                      branches: Dict, features: Dict,
                      recommendations: List[str]) -> FactoryStatusReport:
        """Create final report object."""
        core_data = self._get_core_report_data(summary, velocity, impact, quality)
        extended_data = self._get_extended_report_data(business, branches, features, recommendations)
        return FactoryStatusReport(**core_data, **extended_data)
    
    def _get_core_report_data(self, summary: ExecutiveSummary, velocity: Dict,
                             impact: Dict, quality: Dict) -> Dict[str, Any]:
        """Get core report data."""
        return {
            "executive_summary": summary,
            "velocity_metrics": velocity,
            "impact_metrics": impact,
            "quality_metrics": quality
        }
    
    def _get_extended_report_data(self, business: Dict, branches: Dict,
                                 features: Dict, recommendations: List[str]) -> Dict[str, Any]:
        """Get extended report data."""
        report_metadata = self._generate_report_metadata()
        extended_data = self._build_extended_metrics_data(business, branches, features, recommendations)
        return {**extended_data, **report_metadata}
    
    def _generate_report_metadata(self) -> Dict[str, Any]:
        """Generate report metadata."""
        return {
            "report_id": self._generate_report_id(),
            "generated_at": datetime.now()
        }
    
    def _build_extended_metrics_data(self, business: Dict, branches: Dict, 
                                   features: Dict, recommendations: List[str]) -> Dict[str, Any]:
        """Build extended metrics data dictionary."""
        return {
            "business_value_metrics": business,
            "branch_metrics": branches,
            "feature_progress": features,
            "recommendations": recommendations
        }
    
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
        header_lines = self._build_summary_header(summary)
        content_lines = self._build_summary_content(summary, report)
        return "\n".join(header_lines + content_lines)

    def _build_summary_header(self, summary: ExecutiveSummary) -> List[str]:
        """Build summary header lines"""
        header_components = self._format_header_components(summary)
        return [*header_components, ""]
    
    def _format_header_components(self, summary: ExecutiveSummary) -> List[str]:
        """Format individual header components."""
        return [
            f"AI Factory Status Report - {summary.timestamp.strftime('%Y-%m-%d %H:%M')}",
            f"Overall Status: {summary.overall_status.upper()}",
            f"Productivity Score: {summary.productivity_score}/10",
            f"Business Value Score: {summary.business_value_score}/10"
        ]

    def _build_summary_content(self, summary: ExecutiveSummary, report: FactoryStatusReport) -> List[str]:
        """Build summary content lines"""
        content_sections = self._format_all_content_sections(summary, report)
        return self._flatten_content_sections(content_sections)
    
    def _format_all_content_sections(self, summary: ExecutiveSummary, report: FactoryStatusReport) -> Dict[str, List[str]]:
        """Format all content sections."""
        return {
            'highlights': ["Key Highlights:", *[f"  [U+2022] {h}" for h in summary.key_highlights]],
            'actions': ["Action Items:", *[f"  [U+2022] {a}" for a in summary.action_items]],
            'recommendations': ["Recommendations:", *[f"  [U+2022] {r}" for r in report.recommendations]]
        }
    
    def _flatten_content_sections(self, sections: Dict[str, List[str]]) -> List[str]:
        """Flatten content sections into single list."""
        return sections['highlights'] + [""] + sections['actions'] + [""] + sections['recommendations']