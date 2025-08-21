"""Analytics and trend analysis for quality monitoring"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from collections import defaultdict
from dataclasses import asdict
import statistics

from netra_backend.app.logging_config import central_logger
from netra_backend.app.models import QualityTrend, MetricType, AgentQualityProfile

logger = central_logger.get_logger(__name__)


class TrendAnalyzer:
    """Analyzes trends and generates insights"""
    
    def __init__(self):
        self.agent_profiles: Dict[str, AgentQualityProfile] = {}
    
    async def analyze_trends(self, metrics_buffer: Dict) -> List[QualityTrend]:
        """Analyze trends in quality metrics"""
        trends = []
        for agent_name, events in metrics_buffer.items():
            if len(events) < 10:
                continue
            trend = self._analyze_agent_trend(agent_name, list(events))
            if trend:
                trends.append(trend)
        return trends
    
    def _analyze_agent_trend(self, agent: str, events: List) -> Optional[QualityTrend]:
        """Analyze trend for single agent"""
        recent = [e['quality_score'] for e in events[-50:]]
        older = [e['quality_score'] for e in events[-100:-50]]
        if not recent or not older:
            return None
        return self._calculate_trend(recent, older)
    
    def _calculate_trend(self, recent: List[float], older: List[float]) -> QualityTrend:
        """Calculate trend metrics"""
        recent_avg = statistics.mean(recent)
        older_avg = statistics.mean(older)
        change_pct = self._calculate_change_percentage(recent_avg, older_avg)
        direction = self._determine_direction(change_pct)
        forecast = self._forecast_next_period(recent_avg, older_avg)
        return self._build_quality_trend(recent_avg, older_avg, change_pct, direction, forecast, len(recent))
    
    def _build_quality_trend(self, recent_avg: float, older_avg: float, change_pct: float, 
                           direction: str, forecast: float, sample_size: int) -> QualityTrend:
        """Build QualityTrend object"""
        confidence = self._calculate_confidence(sample_size)
        return self._create_quality_trend_object(recent_avg, older_avg, change_pct, direction, forecast, confidence)
    
    def _create_quality_trend_object(self, recent_avg: float, older_avg: float, change_pct: float,
                                   direction: str, forecast: float, confidence: float) -> QualityTrend:
        """Create QualityTrend object with parameters"""
        basic_params = self._get_trend_basic_params(recent_avg, older_avg, change_pct)
        extended_params = self._get_trend_extended_params(direction, forecast, confidence)
        return QualityTrend(**{**basic_params, **extended_params})
    
    def _get_trend_basic_params(self, recent_avg: float, older_avg: float, change_pct: float) -> Dict:
        """Get basic trend parameters"""
        type_params = {'metric_type': MetricType.QUALITY_SCORE, 'period': 'hour'}
        avg_params = {'current_average': recent_avg, 'previous_average': older_avg}
        return {**type_params, **avg_params, 'change_percentage': change_pct}
    
    def _get_trend_extended_params(self, direction: str, forecast: float, confidence: float) -> Dict:
        """Get extended trend parameters"""
        return {
            'trend_direction': direction,
            'forecast_next_period': forecast,
            'confidence': confidence
        }
    
    def _calculate_change_percentage(self, current: float, previous: float) -> float:
        """Calculate percentage change"""
        if previous == 0:
            return 0
        return ((current - previous) / previous) * 100
    
    def _determine_direction(self, change_pct: float) -> str:
        """Determine trend direction"""
        if change_pct > 5:
            return "improving"
        elif change_pct < -5:
            return "degrading"
        return "stable"
    
    def _forecast_next_period(self, current: float, previous: float) -> float:
        """Simple linear forecast"""
        forecast = current + (current - previous) * 0.5
        return min(1.0, max(0.0, forecast))
    
    def _calculate_confidence(self, sample_size: int) -> float:
        """Calculate confidence based on sample size"""
        return 0.7 if sample_size > 20 else 0.5
    
    async def update_agent_profiles(self, metrics_buffer: Dict):
        """Update quality profiles for each agent"""
        for agent_name, events in metrics_buffer.items():
            if not events:
                continue
            profile = self._create_agent_profile(agent_name, list(events)[-100:])
            self.agent_profiles[agent_name] = profile
    
    def _create_agent_profile(self, agent: str, events: List) -> AgentQualityProfile:
        """Create agent quality profile"""
        scores = [e['quality_score'] for e in events]
        distribution = self._calculate_distribution(events)
        issues = self._identify_issues(events, scores)
        recommendations = self._generate_recommendations(events, scores)
        return self._build_agent_profile(agent, events, scores, distribution, issues, recommendations)
    
    def _build_agent_profile(self, agent: str, events: List, scores: List[float], 
                           distribution: Dict, issues: List[str], recommendations: List[str]) -> AgentQualityProfile:
        """Build AgentQualityProfile object"""
        basic_metrics = self._get_basic_agent_metrics(events, scores)
        return self._create_agent_profile_object(agent, distribution, issues, recommendations, basic_metrics)
    
    def _get_basic_agent_metrics(self, events: List, scores: List[float]) -> Dict:
        """Get basic agent metrics"""
        return {
            'total_requests': len(events),
            'average_quality_score': statistics.mean(scores),
            'slop_detection_count': self._count_slop(events)
        }
    
    def _create_agent_profile_object(self, agent: str, distribution: Dict, issues: List[str],
                                   recommendations: List[str], basic_metrics: Dict) -> AgentQualityProfile:
        """Create AgentQualityProfile object"""
        profile_data = self._get_profile_data(agent, distribution, issues, recommendations, basic_metrics)
        return AgentQualityProfile(**profile_data)
    
    def _get_profile_data(self, agent: str, distribution: Dict, issues: List[str], 
                         recommendations: List[str], basic_metrics: Dict) -> Dict:
        """Get agent profile data dictionary"""
        base_data = self._get_profile_base_data(agent, basic_metrics)
        extended_data = self._get_profile_extended_data(distribution, issues, recommendations)
        return {**base_data, **extended_data}
    
    def _get_profile_base_data(self, agent: str, basic_metrics: Dict) -> Dict:
        """Get profile base data"""
        agent_data = self._get_agent_identity_data(agent)
        metric_data = self._get_metric_data(basic_metrics)
        default_data = self._get_default_profile_data()
        return {**agent_data, **metric_data, **default_data}
    
    def _get_agent_identity_data(self, agent: str) -> Dict:
        """Get agent identity data"""
        return {'agent_name': agent}
    
    def _get_metric_data(self, basic_metrics: Dict) -> Dict:
        """Get metrics data"""
        return {
            'total_requests': basic_metrics['total_requests'],
            'average_quality_score': basic_metrics['average_quality_score'],
            'slop_detection_count': basic_metrics['slop_detection_count']
        }
    
    def _get_default_profile_data(self) -> Dict:
        """Get default profile data"""
        return {
            'retry_count': 0,
            'fallback_count': 0,
            'average_response_time': 0,
            'last_updated': datetime.now(UTC)
        }
    
    def _get_profile_extended_data(self, distribution: Dict, issues: List[str], recommendations: List[str]) -> Dict:
        """Get profile extended data"""
        return {
            'quality_distribution': distribution,
            'issues': issues,
            'recommendations': recommendations
        }
    
    def _calculate_distribution(self, events: List) -> Dict[str, int]:
        """Calculate quality distribution"""
        distribution = defaultdict(int)
        for e in events:
            distribution[e['quality_level']] += 1
        return dict(distribution)
    
    def _count_slop(self, events: List) -> int:
        """Count slop detections"""
        return sum(1 for e in events if e['quality_level'] in ['poor', 'unacceptable'])
    
    def _identify_issues(self, events: List, scores: List[float]) -> List[str]:
        """Identify quality issues"""
        issues = []
        self._check_quality_score_issues(scores, issues)
        self._check_generic_phrase_issues(events, issues)
        self._check_circular_reasoning_issues(events, issues)
        return issues
    
    def _check_quality_score_issues(self, scores: List[float], issues: List[str]):
        """Check for low quality score issues"""
        if statistics.mean(scores) < 0.5:
            issues.append("Low average quality score")
    
    def _check_generic_phrase_issues(self, events: List, issues: List[str]):
        """Check for generic phrase issues"""
        generic_avg = statistics.mean([e.get('generic_phrases', 0) for e in events])
        if generic_avg > 2:
            issues.append("High frequency of generic phrases")
    
    def _check_circular_reasoning_issues(self, events: List, issues: List[str]):
        """Check for circular reasoning issues"""
        circular = sum(1 for e in events if e.get('circular_reasoning', False))
        if circular > 5:
            issues.append("Frequent circular reasoning")
    
    def _generate_recommendations(self, events: List, scores: List[float]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        self._add_quality_recommendations(scores, recommendations)
        self._add_hallucination_recommendations(events, recommendations)
        self._add_actionability_recommendations(events, recommendations)
        return recommendations
    
    def _add_quality_recommendations(self, scores: List[float], recommendations: List[str]):
        """Add quality-based recommendations"""
        if statistics.mean(scores) < 0.5:
            recommendations.append("Review and enhance agent prompts for specificity")
    
    def _add_hallucination_recommendations(self, events: List, recommendations: List[str]):
        """Add hallucination-related recommendations"""
        if any(e.get('hallucination_risk', 0) > 0.5 for e in events):
            recommendations.append("Implement fact-checking mechanisms")
    
    def _add_actionability_recommendations(self, events: List, recommendations: List[str]):
        """Add actionability recommendations"""
        actionability = statistics.mean([e.get('actionability', 0) for e in events])
        if actionability < 0.5:
            recommendations.append("Add concrete action steps to outputs")
    
    def get_dashboard_data(self, metrics_buffer: Dict, active_alerts: Dict) -> Dict:
        """Get comprehensive dashboard data"""
        all_scores = self._extract_all_scores(metrics_buffer)
        overall_stats = self._calculate_overall_stats(all_scores, active_alerts)
        agent_rankings = self._rank_agents()
        distribution = self._calculate_overall_distribution(metrics_buffer)
        return self._build_dashboard_response(overall_stats, agent_rankings, distribution)
    
    def _extract_all_scores(self, metrics_buffer: Dict) -> List[float]:
        """Extract all quality scores from metrics buffer"""
        all_scores = []
        for events in metrics_buffer.values():
            all_scores.extend([e['quality_score'] for e in events])
        return all_scores
    
    def _build_dashboard_response(self, overall_stats: Dict, agent_rankings: List, distribution: Dict) -> Dict:
        """Build dashboard response dictionary"""
        return {
            'overall_stats': overall_stats,
            'agent_profiles': {n: asdict(p) for n, p in agent_rankings[:10]},
            'quality_distribution': dict(distribution),
            'timestamp': datetime.now(UTC).isoformat()
        }
    
    def _calculate_overall_stats(self, scores: List, alerts: Dict) -> Dict:
        """Calculate overall statistics"""
        average_quality = statistics.mean(scores) if scores else 0
        active_alerts_count = self._count_active_alerts(alerts)
        critical_alerts_count = self._count_critical_alerts(alerts)
        return self._build_stats_dict(average_quality, len(scores), active_alerts_count, critical_alerts_count)
    
    def _build_stats_dict(self, average_quality: float, total_events: int, 
                         active_alerts: int, critical_alerts: int) -> Dict:
        """Build overall statistics dictionary"""
        quality_data = {'average_quality': average_quality, 'total_events': total_events}
        alert_data = {'active_alerts': active_alerts, 'critical_alerts': critical_alerts}
        return {**quality_data, **alert_data}
    
    def _count_active_alerts(self, alerts: Dict) -> int:
        """Count active alerts"""
        return len([a for a in alerts.values() if not a.resolved])
    
    def _count_critical_alerts(self, alerts: Dict) -> int:
        """Count critical alerts"""
        return len([
            a for a in alerts.values()
            if a.severity.value == 'critical' and not a.resolved
        ])
    
    def _rank_agents(self) -> List[tuple]:
        """Rank agents by quality score"""
        return sorted(
            self.agent_profiles.items(),
            key=lambda x: x[1].average_quality_score,
            reverse=True
        )
    
    def _calculate_overall_distribution(self, metrics_buffer: Dict) -> Dict:
        """Calculate overall quality distribution"""
        distribution = defaultdict(int)
        for events in metrics_buffer.values():
            for e in events:
                distribution[e['quality_level']] += 1
        return dict(distribution)
    
    def get_agent_report(self, agent: str, events: List, hours: int = 24) -> Dict:
        """Generate detailed agent report"""
        if agent not in self.agent_profiles:
            return {'error': f'No data for agent {agent}'}
        profile = self.agent_profiles[agent]
        recent = self._filter_recent_events(events, hours)
        return self._validate_and_build_report(agent, profile, recent, hours)
    
    def _validate_and_build_report(self, agent: str, profile: AgentQualityProfile, recent: List, hours: int) -> Dict:
        """Validate recent data and build report"""
        if not recent:
            return {'error': f'No recent data for agent {agent}'}
        return self._build_agent_report(agent, profile, recent, hours)
    
    def _filter_recent_events(self, events: List, hours: int) -> List:
        """Filter events for recent time period"""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        return [e for e in events if datetime.fromisoformat(e['timestamp']) > cutoff]
    
    def _build_agent_report(self, agent: str, profile: AgentQualityProfile, recent: List, hours: int) -> Dict:
        """Build detailed agent report"""
        scores = [e['quality_score'] for e in recent]
        hourly_stats = self._calculate_hourly_stats(recent)
        report_data = self._get_report_data(agent, hours, profile, scores, hourly_stats)
        return report_data
    
    def _get_report_data(self, agent: str, hours: int, profile: AgentQualityProfile, 
                        scores: List[float], hourly_stats: Dict) -> Dict:
        """Get complete report data dictionary"""
        basic_data = self._get_report_basic_data(agent, hours, profile)
        analysis_data = self._get_report_analysis_data(scores, hourly_stats, profile)
        return {**basic_data, **analysis_data}
    
    def _get_report_basic_data(self, agent: str, hours: int, profile: AgentQualityProfile) -> Dict:
        """Get basic report data"""
        return {
            'agent_name': agent,
            'period_hours': hours,
            'profile': asdict(profile),
            'timestamp': datetime.now(UTC).isoformat()
        }
    
    def _get_report_analysis_data(self, scores: List[float], hourly_stats: Dict, profile: AgentQualityProfile) -> Dict:
        """Get analysis data for report"""
        return {
            'statistics': self._calculate_statistics(scores),
            'hourly_stats': hourly_stats,
            'recent_issues': profile.issues,
            'recommendations': profile.recommendations
        }
    
    def _calculate_statistics(self, scores: List[float]) -> Dict:
        """Calculate detailed statistics"""
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0
        basic_stats = self._get_basic_statistics(scores)
        return self._build_statistics_dict(basic_stats, std_dev)
    
    def _get_basic_statistics(self, scores: List[float]) -> Dict:
        """Get basic statistical measurements"""
        central_stats = self._get_central_tendency_stats(scores)
        range_stats = self._get_range_stats(scores)
        return {**central_stats, **range_stats, 'total_events': len(scores)}
    
    def _get_central_tendency_stats(self, scores: List[float]) -> Dict:
        """Get central tendency statistics"""
        return {
            'average_quality': statistics.mean(scores),
            'median_quality': statistics.median(scores)
        }
    
    def _get_range_stats(self, scores: List[float]) -> Dict:
        """Get range statistics"""
        return {
            'min_quality': min(scores),
            'max_quality': max(scores)
        }
    
    def _build_statistics_dict(self, basic_stats: Dict, std_dev: float) -> Dict:
        """Build complete statistics dictionary"""
        return {
            **basic_stats,
            'std_dev': std_dev
        }
    
    def _calculate_hourly_stats(self, events: List) -> Dict:
        """Calculate hourly statistics"""
        hourly = self._group_events_by_hour(events)
        return self._build_hourly_stats_dict(hourly)
    
    def _group_events_by_hour(self, events: List) -> Dict:
        """Group events by hour"""
        hourly = defaultdict(list)
        for e in events:
            hour = self._normalize_to_hour(e['timestamp'])
            hourly[hour].append(e['quality_score'])
        return hourly
    
    def _normalize_to_hour(self, timestamp: str) -> datetime:
        """Normalize timestamp to hour boundary"""
        return datetime.fromisoformat(timestamp).replace(
            minute=0, second=0, microsecond=0
        )
    
    def _build_hourly_stats_dict(self, hourly: Dict) -> Dict:
        """Build hourly statistics dictionary"""
        return {
            hour.isoformat(): self._get_hour_stats(scores)
            for hour, scores in hourly.items()
        }
    
    def _get_hour_stats(self, scores: List[float]) -> Dict:
        """Get statistics for a single hour"""
        return {
            'average': statistics.mean(scores),
            'min': min(scores),
            'max': max(scores),
            'count': len(scores)
        }