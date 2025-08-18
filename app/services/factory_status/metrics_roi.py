"""ROI metrics calculator.

Calculates return on investment estimates.
Follows 300-line limit with 8-line function limit.
"""

from typing import List
from .git_commit_parser import GitCommitParser, CommitInfo, CommitType
from .metrics_business_value_types import ROIEstimate
from .metrics_pattern_utils import BusinessValuePatternMatcher


class ROICalculator:
    """Calculator for ROI estimates."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize ROI calculator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.pattern_matcher = BusinessValuePatternMatcher()
        self.repo_path = repo_path
    
    def estimate_roi(self, hours: int = 168) -> ROIEstimate:
        """Estimate return on investment."""
        commits = self.commit_parser.get_commits(hours)
        
        investment_hours = self._calc_investment_hours(commits)
        benefit_value = self._estimate_benefit_value(commits)
        
        roi_percentage = self._calc_roi_percentage(investment_hours, benefit_value)
        payback_days = self._calc_payback_period(investment_hours, benefit_value)
        confidence = self._calc_confidence_level(commits)
        timeline = self._estimate_value_timeline(commits)
        
        return ROIEstimate(
            investment_hours=investment_hours,
            estimated_benefit_value=benefit_value,
            roi_percentage=roi_percentage,
            payback_period_days=payback_days,
            confidence_level=confidence,
            value_realization_timeline=timeline
        )
    
    def _calc_investment_hours(self, commits: List[CommitInfo]) -> float:
        """Calculate total investment hours."""
        total_changes = self._sum_code_changes(commits)
        estimated_hours = total_changes * 0.1  # 1 hour per 10 lines changed
        
        minimum_hours = len(commits) * 0.5  # Minimum 30 min per commit
        return max(estimated_hours, minimum_hours)
    
    def _sum_code_changes(self, commits: List[CommitInfo]) -> int:
        """Sum total code changes across commits."""
        return sum(c.insertions + c.deletions for c in commits)
    
    def _estimate_benefit_value(self, commits: List[CommitInfo]) -> float:
        """Estimate total benefit value."""
        benefit = 0.0
        
        for commit in commits:
            benefit += self._calc_commit_value(commit)
        
        return benefit
    
    def _calc_commit_value(self, commit: CommitInfo) -> float:
        """Calculate value for a single commit."""
        if commit.commit_type == CommitType.FEATURE:
            return 5000  # $5k per feature
        elif commit.commit_type == CommitType.FIX:
            return 2000  # $2k per fix
        elif commit.commit_type == CommitType.PERF:
            return 3000  # $3k per performance improvement
        return 0.0
    
    def _calc_roi_percentage(self, hours: float, benefit: float) -> float:
        """Calculate ROI percentage."""
        if hours == 0:
            return 0.0
        
        cost = hours * 100  # $100 per hour developer cost
        return ((benefit - cost) / cost) * 100 if cost > 0 else 0.0
    
    def _calc_payback_period(self, hours: float, benefit: float) -> int:
        """Calculate payback period in days."""
        if benefit == 0:
            return 999  # No payback
        
        cost = hours * 100
        daily_benefit = benefit / 30  # Spread over 30 days
        
        return int(cost / daily_benefit) if daily_benefit > 0 else 999
    
    def _calc_confidence_level(self, commits: List[CommitInfo]) -> float:
        """Calculate confidence level in estimates."""
        commit_count = len(commits)
        
        if commit_count < 5:
            return 0.3  # Low confidence
        elif commit_count < 20:
            return 0.7  # Medium confidence
        return 0.9  # High confidence
    
    def _estimate_value_timeline(self, commits: List[CommitInfo]) -> str:
        """Estimate value realization timeline."""
        customer_facing = self._count_customer_facing(commits)
        total_commits = len(commits)
        
        customer_ratio = customer_facing / max(total_commits, 1)
        
        if customer_ratio > 0.5:
            return "Immediate (1-2 weeks)"
        elif customer_facing > 0:
            return "Short-term (1-2 months)"
        return "Long-term (3-6 months)"
    
    def _count_customer_facing(self, commits: List[CommitInfo]) -> int:
        """Count customer-facing commits."""
        return sum(1 for c in commits 
                  if self.pattern_matcher.is_customer_facing_commit(c))