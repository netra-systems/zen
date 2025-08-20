"""Innovation metrics calculator.

Calculates innovation vs maintenance metrics.
Follows 450-line limit with 25-line function limit.
"""

from typing import List
from .git_commit_parser import GitCommitParser, CommitInfo
from .metrics_business_value_types import InnovationMetrics
from .metrics_pattern_utils import BusinessValuePatternMatcher


class InnovationCalculator:
    """Calculator for innovation metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize innovation calculator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.pattern_matcher = BusinessValuePatternMatcher()
        self.repo_path = repo_path
    
    def calculate_innovation_metrics(self, hours: int = 168) -> InnovationMetrics:
        """Calculate innovation vs maintenance metrics."""
        commits = self.commit_parser.get_commits(hours)
        
        metrics = self._init_innovation_metrics()
        self._process_commits_for_innovation(commits, metrics)
        
        innovation_ratio = self._calc_innovation_ratio(commits, metrics)
        advancement_score = self._calc_advancement_score(metrics)
        
        return InnovationMetrics(
            innovation_commits=metrics['innovation'],
            maintenance_commits=metrics['maintenance'],
            innovation_ratio=innovation_ratio,
            new_technology_adoption=metrics['new_tech'],
            experimental_features=metrics['experimental'],
            technical_advancement_score=advancement_score
        )
    
    def _init_innovation_metrics(self) -> dict:
        """Initialize innovation metrics dictionary."""
        return {
            'innovation': 0,
            'maintenance': 0,
            'new_tech': 0,
            'experimental': 0
        }
    
    def _process_commits_for_innovation(self, commits: List[CommitInfo], metrics: dict) -> None:
        """Process commits for innovation metrics."""
        for commit in commits:
            self._update_innovation_metrics(commit, metrics)
    
    def _update_innovation_metrics(self, commit: CommitInfo, metrics: dict) -> None:
        """Update innovation metrics for a commit."""
        self._classify_commit_type(commit, metrics)
        self._check_technology_adoption(commit, metrics)
    
    def _classify_commit_type(self, commit: CommitInfo, metrics: dict) -> None:
        """Classify commit as innovation or maintenance."""
        if self.pattern_matcher.is_innovation_commit(commit):
            metrics['innovation'] += 1
        elif self.pattern_matcher.is_maintenance_commit(commit):
            metrics['maintenance'] += 1
    
    def _check_technology_adoption(self, commit: CommitInfo, metrics: dict) -> None:
        """Check for technology adoption indicators."""
        if self.pattern_matcher.involves_new_technology(commit):
            metrics['new_tech'] += 1
        if self.pattern_matcher.is_experimental(commit):
            metrics['experimental'] += 1
    
    def _calc_innovation_ratio(self, commits: List[CommitInfo], metrics: dict) -> float:
        """Calculate innovation ratio percentage."""
        total_commits = len(commits)
        innovation_commits = metrics['innovation']
        
        return (innovation_commits / max(total_commits, 1)) * 100
    
    def _calc_advancement_score(self, metrics: dict) -> float:
        """Calculate technical advancement score."""
        innovation = metrics['innovation']
        new_tech = metrics['new_tech']
        experimental = metrics['experimental']
        
        advancement_points = innovation * 2 + new_tech * 3 + experimental * 1.5
        return min(advancement_points / 5, 10.0)