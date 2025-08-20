"""Revenue metrics calculator.

Calculates revenue-related business metrics.
Follows 450-line limit with 25-line function limit.
"""

from typing import List
from .git_commit_parser import GitCommitParser, CommitInfo
from .metrics_business_value_types import RevenueMetrics
from .metrics_pattern_utils import BusinessValuePatternMatcher


class RevenueCalculator:
    """Calculator for revenue metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize revenue calculator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.pattern_matcher = BusinessValuePatternMatcher()
        self.repo_path = repo_path
    
    def calculate_revenue_metrics(self, hours: int = 168) -> RevenueMetrics:
        """Calculate revenue-related metrics."""
        commits = self.commit_parser.get_commits(hours)
        
        metrics = self._init_revenue_metrics()
        self._process_commits_for_revenue(commits, metrics)
        
        subscription_score = self._calc_subscription_impact(commits)
        revenue_impact = self._estimate_revenue_impact(metrics)
        
        return RevenueMetrics(
            revenue_generating_features=metrics['revenue_features'],
            monetization_improvements=metrics['monetization'],
            market_expansion_features=metrics['market_expansion'],
            subscription_impact_score=subscription_score,
            estimated_revenue_impact=revenue_impact,
            conversion_improvements=metrics['conversion']
        )
    
    def _init_revenue_metrics(self) -> dict:
        """Initialize revenue metrics dictionary."""
        return {
            'revenue_features': 0,
            'monetization': 0,
            'market_expansion': 0,
            'conversion': 0
        }
    
    def _process_commits_for_revenue(self, commits: List[CommitInfo], metrics: dict) -> None:
        """Process commits for revenue metrics."""
        for commit in commits:
            self._update_revenue_metrics(commit, metrics)
    
    def _update_revenue_metrics(self, commit: CommitInfo, metrics: dict) -> None:
        """Update revenue metrics for a commit."""
        if self.pattern_matcher.is_revenue_generating(commit):
            metrics['revenue_features'] += 1
        if self.pattern_matcher.is_monetization_improvement(commit):
            metrics['monetization'] += 1
        if self.pattern_matcher.is_market_expansion(commit):
            metrics['market_expansion'] += 1
        if self.pattern_matcher.is_conversion_improvement(commit):
            metrics['conversion'] += 1
    
    def _calc_subscription_impact(self, commits: List[CommitInfo]) -> float:
        """Calculate subscription impact score."""
        subscription_commits = self._filter_subscription_commits(commits)
        
        if not subscription_commits:
            return 0.0
        
        return min(len(subscription_commits) * 2.5, 10.0)
    
    def _filter_subscription_commits(self, commits: List[CommitInfo]) -> List[CommitInfo]:
        """Filter commits related to subscriptions."""
        return [c for c in commits 
                if "subscription" in c.message.lower()]
    
    def _estimate_revenue_impact(self, metrics: dict) -> float:
        """Estimate revenue impact in dollars."""
        base_feature_value = 10000  # $10k per revenue feature
        monetization_value = 25000  # $25k per monetization improvement
        
        revenue_features = metrics['revenue_features']
        monetization = metrics['monetization']
        
        return (revenue_features * base_feature_value + 
                monetization * monetization_value)