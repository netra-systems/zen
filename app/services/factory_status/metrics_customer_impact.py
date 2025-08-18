"""Customer impact metrics calculator.

Calculates customer-facing changes and satisfaction metrics.
Follows 300-line limit with 8-line function limit.
"""

from typing import List
from .git_commit_parser import GitCommitParser, CommitInfo, CommitType
from .metrics_business_value_types import CustomerImpactMetrics
from .metrics_pattern_utils import BusinessValuePatternMatcher


class CustomerImpactCalculator:
    """Calculator for customer impact metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize customer impact calculator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.pattern_matcher = BusinessValuePatternMatcher()
        self.repo_path = repo_path
    
    def calculate_customer_impact(self, hours: int = 168) -> CustomerImpactMetrics:
        """Calculate customer impact metrics."""
        commits = self.commit_parser.get_commits(hours)
        
        metrics = self._init_metrics()
        self._process_commits(commits, metrics)
        
        satisfaction_score = self._calculate_satisfaction_score(metrics)
        
        return CustomerImpactMetrics(
            customer_facing_changes=metrics['customer_facing'],
            user_experience_improvements=metrics['ux_improvements'],
            performance_enhancements=metrics['performance'],
            bug_fixes_affecting_users=metrics['bug_fixes'],
            new_features_delivered=metrics['new_features'],
            customer_satisfaction_score=satisfaction_score
        )
    
    def _init_metrics(self) -> dict:
        """Initialize metrics dictionary."""
        return {
            'customer_facing': 0,
            'ux_improvements': 0,
            'performance': 0,
            'bug_fixes': 0,
            'new_features': 0
        }
    
    def _process_commits(self, commits: List[CommitInfo], metrics: dict) -> None:
        """Process commits to extract metrics."""
        for commit in commits:
            self._update_metrics_for_commit(commit, metrics)
    
    def _update_metrics_for_commit(self, commit: CommitInfo, metrics: dict) -> None:
        """Update metrics for a single commit."""
        if self.pattern_matcher.is_customer_facing_commit(commit):
            metrics['customer_facing'] += 1
        if self.pattern_matcher.is_ux_improvement(commit):
            metrics['ux_improvements'] += 1
        if self.pattern_matcher.is_performance_enhancement(commit):
            metrics['performance'] += 1
        self._update_commit_type_metrics(commit, metrics)
    
    def _update_commit_type_metrics(self, commit: CommitInfo, metrics: dict) -> None:
        """Update metrics based on commit type."""
        if commit.commit_type == CommitType.FIX:
            metrics['bug_fixes'] += 1
        if commit.commit_type == CommitType.FEATURE:
            metrics['new_features'] += 1
    
    def _calculate_satisfaction_score(self, metrics: dict) -> float:
        """Calculate customer satisfaction score."""
        positive_impact = self._calc_positive_impact(metrics)
        stability_impact = self._calc_stability_impact(metrics)
        
        total_score = positive_impact + stability_impact
        return min(total_score / 10, 10.0)  # Normalize to 0-10
    
    def _calc_positive_impact(self, metrics: dict) -> float:
        """Calculate positive impact score."""
        customer_facing = metrics['customer_facing']
        ux = metrics['ux_improvements']
        features = metrics['new_features']
        
        return customer_facing * 2 + ux * 3 + features * 2
    
    def _calc_stability_impact(self, metrics: dict) -> float:
        """Calculate stability impact score."""
        fixes = metrics['bug_fixes']
        return fixes * 1.5