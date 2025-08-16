"""Development velocity metrics for AI Factory Status Report.

Calculates velocity trends, peak activity, and feature delivery speed.
Module follows 300-line limit with 8-line function limit.
"""

import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
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
        hourly_data = self._group_by_hour(commits)
        daily_data = self._group_by_day(commits)
        
        period = self._determine_period(hours)
        trend = self._calculate_trend(daily_data)
        
        return self._build_velocity_metrics(
            commits, period, trend, hours
        )
    
    def _group_by_hour(self, commits: List[CommitInfo]) -> Dict[int, List[CommitInfo]]:
        """Group commits by hour of day."""
        hourly = {}
        for commit in commits:
            hour = commit.timestamp.hour
            if hour not in hourly:
                hourly[hour] = []
            hourly[hour].append(commit)
        return hourly
    
    def _group_by_day(self, commits: List[CommitInfo]) -> Dict[str, List[CommitInfo]]:
        """Group commits by day."""
        daily = {}
        for commit in commits:
            day = commit.timestamp.strftime("%Y-%m-%d")
            if day not in daily:
                daily[day] = []
            daily[day].append(commit)
        return daily
    
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
        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x_squared = sum(x * x for x in x_vals)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x * sum_x)
        return slope
    
    def _classify_trend(self, slope: float, values: List[int]) -> Tuple[TrendDirection, float]:
        """Classify trend direction from slope."""
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        volatility = std_dev / statistics.mean(values) if values else 0
        
        if volatility > 0.5:
            return TrendDirection.VOLATILE, slope
        elif slope > 0.1:
            return TrendDirection.INCREASING, slope
        elif slope < -0.1:
            return TrendDirection.DECREASING, slope
        return TrendDirection.STABLE, slope
    
    def _build_velocity_metrics(self, commits: List[CommitInfo], 
                               period: VelocityPeriod, 
                               trend: Tuple[TrendDirection, float],
                               hours: int) -> VelocityMetrics:
        """Build velocity metrics object."""
        period_count = self._get_period_count(period, hours)
        feature_commits = [c for c in commits if c.commit_type == CommitType.FEATURE]
        
        return VelocityMetrics(
            period=period,
            commits_per_period=len(commits) / period_count,
            lines_per_period=sum(c.insertions + c.deletions for c in commits) / period_count,
            features_per_period=len(feature_commits) / period_count,
            files_per_period=sum(c.files_changed for c in commits) / period_count,
            trend_direction=trend[0],
            trend_slope=trend[1],
            confidence=self._calculate_confidence(commits)
        )
    
    def _get_period_count(self, period: VelocityPeriod, hours: int) -> float:
        """Get number of periods in timeframe."""
        if period == VelocityPeriod.HOUR:
            return max(hours, 1)
        elif period == VelocityPeriod.DAY:
            return max(hours / 24, 1)
        elif period == VelocityPeriod.WEEK:
            return max(hours / 168, 1)
        return max(hours / 744, 1)
    
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
        
        peak_hour = max(hourly_data.keys(), key=lambda h: len(hourly_data[h]))
        peak_commits = hourly_data[peak_hour]
        
        return PeakActivity(
            hour=peak_hour,
            day_of_week=self._find_peak_day(commits),
            commits_count=len(peak_commits),
            activity_score=self._calculate_activity_score(peak_commits),
            authors_active=len(set(c.author for c in peak_commits))
        )
    
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
        
        total_changes = sum(c.insertions + c.deletions for c in commits)
        unique_authors = len(set(c.author for c in commits))
        
        score = (len(commits) * 10 + total_changes * 0.1 + unique_authors * 20)
        return min(score / 100, 10.0)
    
    def calculate_feature_delivery_speed(self, days: int = 90) -> FeatureDeliverySpeed:
        """Calculate feature delivery speed metrics."""
        branches = self.branch_tracker.get_all_branches()
        feature_branches = [b for b in branches if b.branch_type == BranchType.FEATURE]
        
        delivery_times = self._calculate_delivery_times(feature_branches)
        baseline = self._get_baseline_delivery_speed()
        
        return self._build_delivery_speed_metrics(delivery_times, baseline)
    
    def _calculate_delivery_times(self, branches: List[BranchInfo]) -> List[int]:
        """Calculate delivery times for feature branches."""
        times = []
        for branch in branches:
            if branch.status.value == "merged":
                # Simplified calculation - would need creation date for accuracy
                delivery_days = max(branch.commit_count // 2, 1)
                times.append(delivery_days)
        return times
    
    def _get_baseline_delivery_speed(self) -> float:
        """Get baseline delivery speed."""
        # Simplified baseline - could be from historical data
        return 14.0  # 14 days average baseline
    
    def _build_delivery_speed_metrics(self, times: List[int], 
                                     baseline: float) -> FeatureDeliverySpeed:
        """Build feature delivery speed metrics."""
        if not times:
            return FeatureDeliverySpeed(0, 0, 0, 0, 0, 0)
        
        avg_days = statistics.mean(times)
        median_days = statistics.median(times)
        
        return FeatureDeliverySpeed(
            average_feature_days=avg_days,
            median_feature_days=median_days,
            fastest_feature_days=min(times),
            slowest_feature_days=max(times),
            baseline_comparison=(baseline - avg_days) / baseline * 100,
            delivery_consistency=self._calculate_consistency(times)
        )
    
    def _calculate_consistency(self, times: List[int]) -> float:
        """Calculate delivery consistency score."""
        if len(times) < 2:
            return 1.0
        
        std_dev = statistics.stdev(times)
        mean_time = statistics.mean(times)
        coefficient_of_variation = std_dev / mean_time
        
        consistency = max(0, 1 - coefficient_of_variation)
        return min(consistency, 1.0)
    
    def establish_baseline(self, historical_days: int = 90) -> VelocityBaseline:
        """Establish velocity baseline from historical data."""
        commits = self.commit_parser.get_commits(historical_days * 24)
        feature_commits = [c for c in commits if c.commit_type == CommitType.FEATURE]
        
        return VelocityBaseline(
            period_days=historical_days,
            commits_per_day=len(commits) / historical_days,
            lines_per_day=sum(c.insertions + c.deletions for c in commits) / historical_days,
            features_per_week=len(feature_commits) / (historical_days / 7),
            established_date=datetime.now()
        )
    
    def compare_to_baseline(self, current: VelocityMetrics, 
                           baseline: VelocityBaseline) -> Dict[str, float]:
        """Compare current velocity to baseline."""
        return {
            "commits_vs_baseline": self._calculate_percentage_change(
                current.commits_per_period, baseline.commits_per_day
            ),
            "lines_vs_baseline": self._calculate_percentage_change(
                current.lines_per_period, baseline.lines_per_day
            ),
            "features_vs_baseline": self._calculate_percentage_change(
                current.features_per_period, baseline.features_per_week / 7
            )
        }
    
    def _calculate_percentage_change(self, current: float, baseline: float) -> float:
        """Calculate percentage change from baseline."""
        if baseline == 0:
            return 0.0
        return ((current - baseline) / baseline) * 100