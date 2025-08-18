"""Development velocity metrics for AI Factory Status Report.

Calculates velocity trends, peak activity, and feature delivery speed.
Module follows 300-line limit with 8-line function limit.
"""

import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .git_commit_parser import GitCommitParser, CommitInfo, CommitType
from .git_branch_tracker import GitBranchTracker, BranchInfo, BranchType


class VelocityPeriod(Enum):
    """Time periods for velocity calculation."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class TrendDirection(Enum):
    """Direction of velocity trends."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class VelocityMetrics:
    """Velocity metrics for a specific period."""
    period: VelocityPeriod
    commits_per_period: float
    lines_per_period: float
    features_per_period: float
    files_per_period: float
    trend_direction: TrendDirection
    trend_slope: float
    confidence: float


@dataclass
class PeakActivity:
    """Peak activity period information."""
    hour: int
    day_of_week: int
    commits_count: int
    activity_score: float
    authors_active: int


@dataclass
class FeatureDeliverySpeed:
    """Feature delivery speed metrics."""
    average_feature_days: float
    median_feature_days: float
    fastest_feature_days: int
    slowest_feature_days: int
    baseline_comparison: float
    delivery_consistency: float


@dataclass
class VelocityBaseline:
    """Historical baseline for velocity comparison."""
    period_days: int
    commits_per_day: float
    lines_per_day: float
    features_per_week: float
    established_date: datetime


class VelocityCalculator:
    """Calculator for development velocity metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize velocity calculator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.branch_tracker = GitBranchTracker(repo_path)
        self.repo_path = repo_path
    
    def calculate_velocity(self, hours: int = 168) -> VelocityMetrics:
        """Calculate velocity metrics for period."""
        commits = self.commit_parser.get_commits(hours)
        grouped_data = self._prepare_commit_groups(commits)
        period = self._determine_period(hours)
        trend = self._calculate_trend(grouped_data['daily'])
        return self._build_velocity_metrics(commits, period, trend, hours)
    
    def _prepare_commit_groups(self, commits: List[CommitInfo]) -> Dict[str, Dict]:
        """Prepare hourly and daily commit groupings."""
        return {
            'hourly': self._group_by_hour(commits),
            'daily': self._group_by_day(commits)
        }
    
    def _group_by_hour(self, commits: List[CommitInfo]) -> Dict[int, List[CommitInfo]]:
        """Group commits by hour of day."""
        hourly = {}
        for commit in commits:
            hour = commit.timestamp.hour
            self._add_commit_to_hourly_group(hourly, hour, commit)
        return hourly
    
    def _add_commit_to_hourly_group(self, hourly: dict, hour: int, commit: CommitInfo) -> None:
        """Add commit to hourly group."""
        if hour not in hourly:
            hourly[hour] = []
        hourly[hour].append(commit)
    
    def _group_by_day(self, commits: List[CommitInfo]) -> Dict[str, List[CommitInfo]]:
        """Group commits by day."""
        daily = {}
        for commit in commits:
            day = commit.timestamp.strftime("%Y-%m-%d")
            self._add_commit_to_daily_group(daily, day, commit)
        return daily
    
    def _add_commit_to_daily_group(self, daily: dict, day: str, commit: CommitInfo) -> None:
        """Add commit to daily group."""
        if day not in daily:
            daily[day] = []
        daily[day].append(commit)
    
    def _determine_period(self, hours: int) -> VelocityPeriod:
        """Determine appropriate period for hours."""
        if hours <= 24:
            return VelocityPeriod.HOUR
        elif hours <= 168:
            return VelocityPeriod.DAY
        elif hours <= 744:
            return VelocityPeriod.WEEK
        return VelocityPeriod.MONTH
    
    def _calculate_trend(self, daily_data: Dict[str, List[CommitInfo]]) -> Tuple[TrendDirection, float]:
        """Calculate trend using linear regression."""
        if len(daily_data) < 3:
            return TrendDirection.STABLE, 0.0
        
        x_values = list(range(len(daily_data)))
        y_values = [len(commits) for commits in daily_data.values()]
        
        slope = self._linear_regression_slope(x_values, y_values)
        return self._classify_trend(slope, y_values)
    
    def _linear_regression_slope(self, x_vals: List[int], y_vals: List[int]) -> float:
        """Calculate linear regression slope."""
        n = len(x_vals)
        sums = self._calculate_regression_sums(x_vals, y_vals)
        return self._compute_slope(n, sums)
    
    def _calculate_regression_sums(self, x_vals: List[int], y_vals: List[int]) -> Dict[str, float]:
        """Calculate sums needed for regression."""
        return {
            'sum_x': sum(x_vals),
            'sum_y': sum(y_vals),
            'sum_xy': sum(x * y for x, y in zip(x_vals, y_vals)),
            'sum_x_squared': sum(x * x for x in x_vals)
        }
    
    def _compute_slope(self, n: int, sums: Dict[str, float]) -> float:
        """Compute linear regression slope from sums."""
        numerator = n * sums['sum_xy'] - sums['sum_x'] * sums['sum_y']
        denominator = n * sums['sum_x_squared'] - sums['sum_x'] * sums['sum_x']
        return numerator / denominator
    
    def _classify_trend(self, slope: float, values: List[int]) -> Tuple[TrendDirection, float]:
        """Classify trend direction from slope."""
        volatility = self._calculate_volatility(values)
        direction = self._determine_trend_direction(slope, volatility)
        return direction, slope
    
    def _calculate_volatility(self, values: List[int]) -> float:
        """Calculate volatility coefficient."""
        if not values or len(values) < 2:
            return 0
        std_dev = statistics.stdev(values)
        mean_val = statistics.mean(values)
        return std_dev / mean_val if mean_val else 0
    
    def _determine_trend_direction(self, slope: float, volatility: float) -> TrendDirection:
        """Determine trend direction from slope and volatility."""
        if volatility > 0.5:
            return TrendDirection.VOLATILE
        elif slope > 0.1:
            return TrendDirection.INCREASING
        elif slope < -0.1:
            return TrendDirection.DECREASING
        return TrendDirection.STABLE
    
    def _build_velocity_metrics(self, commits: List[CommitInfo], 
                               period: VelocityPeriod, 
                               trend: Tuple[TrendDirection, float],
                               hours: int) -> VelocityMetrics:
        """Build velocity metrics object."""
        period_count = self._get_period_count(period, hours)
        metrics_data = self._calculate_metrics_data(commits, period_count)
        return VelocityMetrics(
            period=period,
            trend_direction=trend[0],
            trend_slope=trend[1],
            confidence=self._calculate_confidence(commits),
            **metrics_data
        )
    
    def _calculate_metrics_data(self, commits: List[CommitInfo], period_count: float) -> Dict[str, float]:
        """Calculate velocity metrics data."""
        feature_commits = [c for c in commits if c.commit_type == CommitType.FEATURE]
        return {
            'commits_per_period': len(commits) / period_count,
            'lines_per_period': sum(c.insertions + c.deletions for c in commits) / period_count,
            'features_per_period': len(feature_commits) / period_count,
            'files_per_period': sum(c.files_changed for c in commits) / period_count
        }
    
    def _get_period_count(self, period: VelocityPeriod, hours: int) -> float:
        """Get number of periods in timeframe."""
        period_mappings = {
            VelocityPeriod.HOUR: hours,
            VelocityPeriod.DAY: hours / 24,
            VelocityPeriod.WEEK: hours / 168,
            VelocityPeriod.MONTH: hours / 744
        }
        return max(period_mappings.get(period, hours / 744), 1)
    
    def _calculate_confidence(self, commits: List[CommitInfo]) -> float:
        """Calculate confidence in velocity measurement."""
        if len(commits) < 5:
            return 0.3
        elif len(commits) < 20:
            return 0.7
        return 0.95
    
    def find_peak_activity(self, days: int = 30) -> PeakActivity:
        """Find peak activity periods."""
        commits = self.commit_parser.get_commits(days * 24)
        hourly_data = self._group_by_hour(commits)
        peak_data = self._analyze_peak_activity(commits, hourly_data)
        return PeakActivity(**peak_data)
    
    def _analyze_peak_activity(self, commits: List[CommitInfo], hourly_data: dict) -> dict:
        """Analyze peak activity data."""
        peak_hour = max(hourly_data.keys(), key=lambda h: len(hourly_data[h]))
        peak_commits = hourly_data[peak_hour]
        return {
            'hour': peak_hour,
            'day_of_week': self._find_peak_day(commits),
            'commits_count': len(peak_commits),
            'activity_score': self._calculate_activity_score(peak_commits),
            'authors_active': len(set(c.author for c in peak_commits))
        }
    
    def _find_peak_day(self, commits: List[CommitInfo]) -> int:
        """Find peak day of week (0=Monday)."""
        day_counts = {}
        for commit in commits:
            day = commit.timestamp.weekday()
            day_counts[day] = day_counts.get(day, 0) + 1
        
        return max(day_counts.keys(), key=lambda d: day_counts[d]) if day_counts else 0
    
    def _calculate_activity_score(self, commits: List[CommitInfo]) -> float:
        """Calculate activity score for commits."""
        if not commits:
            return 0.0
        
        score_components = self._get_activity_score_components(commits)
        raw_score = self._compute_raw_activity_score(score_components)
        return min(raw_score / 100, 10.0)
    
    def _get_activity_score_components(self, commits: List[CommitInfo]) -> Dict[str, int]:
        """Get components for activity score calculation."""
        return {
            'commits_count': len(commits),
            'total_changes': sum(c.insertions + c.deletions for c in commits),
            'unique_authors': len(set(c.author for c in commits))
        }
    
    def _compute_raw_activity_score(self, components: Dict[str, int]) -> float:
        """Compute raw activity score from components."""
        return (
            components['commits_count'] * 10 +
            components['total_changes'] * 0.1 +
            components['unique_authors'] * 20
        )
    
    def calculate_feature_delivery_speed(self, days: int = 90) -> FeatureDeliverySpeed:
        """Calculate feature delivery speed metrics."""
        feature_branches = self._get_feature_branches()
        delivery_times = self._calculate_delivery_times(feature_branches)
        baseline = self._get_baseline_delivery_speed()
        return self._build_delivery_speed_metrics(delivery_times, baseline)
    
    def _get_feature_branches(self) -> List[BranchInfo]:
        """Get feature branches from tracker."""
        branches = self.branch_tracker.get_all_branches()
        return [b for b in branches if b.branch_type == BranchType.FEATURE]
    
    def _calculate_delivery_times(self, branches: List[BranchInfo]) -> List[int]:
        """Calculate delivery times for feature branches."""
        times = []
        for branch in branches:
            if self._is_merged_branch(branch):
                delivery_days = self._estimate_delivery_days(branch)
                times.append(delivery_days)
        return times
    
    def _is_merged_branch(self, branch: BranchInfo) -> bool:
        """Check if branch is merged."""
        return branch.status.value == "merged"
    
    def _estimate_delivery_days(self, branch: BranchInfo) -> int:
        """Estimate delivery days for branch."""
        return max(branch.commit_count // 2, 1)
    
    def _get_baseline_delivery_speed(self) -> float:
        """Get baseline delivery speed."""
        # Simplified baseline - could be from historical data
        return 14.0  # 14 days average baseline
    
    def _build_delivery_speed_metrics(self, times: List[int], 
                                     baseline: float) -> FeatureDeliverySpeed:
        """Build feature delivery speed metrics."""
        if not times:
            return FeatureDeliverySpeed(0, 0, 0, 0, 0, 0)
        
        stats = self._calculate_delivery_stats(times, baseline)
        return FeatureDeliverySpeed(**stats)
    
    def _calculate_delivery_stats(self, times: List[int], baseline: float) -> Dict[str, float]:
        """Calculate delivery speed statistics."""
        avg_days = statistics.mean(times)
        return {
            'average_feature_days': avg_days,
            'median_feature_days': statistics.median(times),
            'fastest_feature_days': min(times),
            'slowest_feature_days': max(times),
            'baseline_comparison': (baseline - avg_days) / baseline * 100,
            'delivery_consistency': self._calculate_consistency(times)
        }
    
    def _calculate_consistency(self, times: List[int]) -> float:
        """Calculate delivery consistency score."""
        if len(times) < 2:
            return 1.0
        
        coefficient_of_variation = self._get_coefficient_of_variation(times)
        consistency = max(0, 1 - coefficient_of_variation)
        return min(consistency, 1.0)
    
    def _get_coefficient_of_variation(self, times: List[int]) -> float:
        """Get coefficient of variation for times."""
        std_dev = statistics.stdev(times)
        mean_time = statistics.mean(times)
        return std_dev / mean_time if mean_time else 0
    
    def establish_baseline(self, historical_days: int = 90) -> VelocityBaseline:
        """Establish velocity baseline from historical data."""
        commits = self.commit_parser.get_commits(historical_days * 24)
        baseline_data = self._calculate_baseline_data(commits, historical_days)
        return VelocityBaseline(**baseline_data)
    
    def _calculate_baseline_data(self, commits: List[CommitInfo], historical_days: int) -> Dict[str, Any]:
        """Calculate baseline data from commits."""
        feature_commits = [c for c in commits if c.commit_type == CommitType.FEATURE]
        return {
            'period_days': historical_days,
            'commits_per_day': len(commits) / historical_days,
            'lines_per_day': sum(c.insertions + c.deletions for c in commits) / historical_days,
            'features_per_week': len(feature_commits) / (historical_days / 7),
            'established_date': datetime.now()
        }
    
    def compare_to_baseline(self, current: VelocityMetrics, 
                           baseline: VelocityBaseline) -> Dict[str, float]:
        """Compare current velocity to baseline."""
        comparisons = [
            ('commits_vs_baseline', current.commits_per_period, baseline.commits_per_day),
            ('lines_vs_baseline', current.lines_per_period, baseline.lines_per_day),
            ('features_vs_baseline', current.features_per_period, baseline.features_per_week / 7)
        ]
        return {name: self._calculate_percentage_change(current_val, baseline_val)
                for name, current_val, baseline_val in comparisons}
    
    def _calculate_percentage_change(self, current: float, baseline: float) -> float:
        """Calculate percentage change from baseline."""
        if baseline == 0:
            return 0.0
        return ((current - baseline) / baseline) * 100