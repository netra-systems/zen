"""Analytics and trend analysis for quality monitoring"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from collections import defaultdict
from dataclasses import asdict
import statistics

from app.logging_config import central_logger
from .models import QualityTrend, MetricType, AgentQualityProfile

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
        confidence = self._calculate_confidence(len(recent))
        
        return QualityTrend(
            metric_type=MetricType.QUALITY_SCORE,
            period="hour",
            trend_direction=direction,
            change_percentage=change_pct,
            current_average=recent_avg,
            previous_average=older_avg,
            forecast_next_period=forecast,
            confidence=confidence
        )
    
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
        
        return AgentQualityProfile(
            agent_name=agent,
            total_requests=len(events),
            average_quality_score=statistics.mean(scores),
            quality_distribution=distribution,
            slop_detection_count=self._count_slop(events),
            retry_count=0,
            fallback_count=0,
            average_response_time=0,
            last_updated=datetime.now(UTC),
            issues=issues,
            recommendations=recommendations
        )
    
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
        if statistics.mean(scores) < 0.5:
            issues.append("Low average quality score")
        generic_avg = statistics.mean([e.get('generic_phrases', 0) for e in events])
        if generic_avg > 2:
            issues.append("High frequency of generic phrases")
        circular = sum(1 for e in events if e.get('circular_reasoning', False))
        if circular > 5:
            issues.append("Frequent circular reasoning")
        return issues
    
    def _generate_recommendations(self, events: List, scores: List[float]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        if statistics.mean(scores) < 0.5:
            recommendations.append("Review and enhance agent prompts for specificity")
        if any(e.get('hallucination_risk', 0) > 0.5 for e in events):
            recommendations.append("Implement fact-checking mechanisms")
        actionability = statistics.mean([e.get('actionability', 0) for e in events])
        if actionability < 0.5:
            recommendations.append("Add concrete action steps to outputs")
        return recommendations
    
    def get_dashboard_data(self, metrics_buffer: Dict, active_alerts: Dict) -> Dict:
        """Get comprehensive dashboard data"""
        all_scores = []
        for events in metrics_buffer.values():
            all_scores.extend([e['quality_score'] for e in events])
        
        overall_stats = self._calculate_overall_stats(all_scores, active_alerts)
        agent_rankings = self._rank_agents()
        distribution = self._calculate_overall_distribution(metrics_buffer)
        
        return {
            'overall_stats': overall_stats,
            'agent_profiles': {n: asdict(p) for n, p in agent_rankings[:10]},
            'quality_distribution': dict(distribution),
            'timestamp': datetime.now(UTC).isoformat()
        }
    
    def _calculate_overall_stats(self, scores: List, alerts: Dict) -> Dict:
        """Calculate overall statistics"""
        return {
            'average_quality': statistics.mean(scores) if scores else 0,
            'total_events': len(scores),
            'active_alerts': len([a for a in alerts.values() if not a.resolved]),
            'critical_alerts': len([
                a for a in alerts.values()
                if a.severity.value == 'critical' and not a.resolved
            ])
        }
    
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
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        recent = [e for e in events if datetime.fromisoformat(e['timestamp']) > cutoff]
        
        if not recent:
            return {'error': f'No recent data for agent {agent}'}
        
        scores = [e['quality_score'] for e in recent]
        hourly_stats = self._calculate_hourly_stats(recent)
        
        return {
            'agent_name': agent,
            'period_hours': hours,
            'profile': asdict(profile),
            'statistics': self._calculate_statistics(scores),
            'hourly_stats': hourly_stats,
            'recent_issues': profile.issues,
            'recommendations': profile.recommendations,
            'timestamp': datetime.now(UTC).isoformat()
        }
    
    def _calculate_statistics(self, scores: List[float]) -> Dict:
        """Calculate detailed statistics"""
        return {
            'total_events': len(scores),
            'average_quality': statistics.mean(scores),
            'median_quality': statistics.median(scores),
            'std_dev': statistics.stdev(scores) if len(scores) > 1 else 0,
            'min_quality': min(scores),
            'max_quality': max(scores)
        }
    
    def _calculate_hourly_stats(self, events: List) -> Dict:
        """Calculate hourly statistics"""
        hourly = defaultdict(list)
        for e in events:
            hour = datetime.fromisoformat(e['timestamp']).replace(
                minute=0, second=0, microsecond=0
            )
            hourly[hour].append(e['quality_score'])
        
        return {
            hour.isoformat(): {
                'average': statistics.mean(scores),
                'min': min(scores),
                'max': max(scores),
                'count': len(scores)
            }
            for hour, scores in hourly.items()
        }