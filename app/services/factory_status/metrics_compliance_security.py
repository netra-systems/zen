"""Compliance and security metrics calculator.

Calculates security fixes and compliance metrics.
Follows 450-line limit with 25-line function limit.
"""

from typing import List
from .git_commit_parser import GitCommitParser, CommitInfo
from .metrics_business_value_types import ComplianceSecurityMetrics
from .metrics_pattern_utils import BusinessValuePatternMatcher


class ComplianceSecurityCalculator:
    """Calculator for compliance and security metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize compliance security calculator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.pattern_matcher = BusinessValuePatternMatcher()
        self.repo_path = repo_path
    
    def calculate_compliance_security_metrics(self, hours: int = 168) -> ComplianceSecurityMetrics:
        """Calculate compliance and security metrics."""
        commits = self.commit_parser.get_commits(hours)
        
        metrics = self._init_security_metrics()
        self._process_commits_for_security(commits, metrics)
        
        compliance_score = self._calc_compliance_score(metrics)
        risk_reduction = self._calc_risk_reduction(metrics)
        
        return ComplianceSecurityMetrics(
            security_fixes=metrics['security_fixes'],
            compliance_improvements=metrics['compliance'],
            audit_preparation_items=metrics['audit_items'],
            data_protection_enhancements=metrics['data_protection'],
            regulatory_compliance_score=compliance_score,
            security_risk_reduction=risk_reduction
        )
    
    def _init_security_metrics(self) -> dict:
        """Initialize security metrics dictionary."""
        return {
            'security_fixes': 0,
            'compliance': 0,
            'audit_items': 0,
            'data_protection': 0
        }
    
    def _process_commits_for_security(self, commits: List[CommitInfo], metrics: dict) -> None:
        """Process commits for security metrics."""
        for commit in commits:
            self._update_security_metrics(commit, metrics)
    
    def _update_security_metrics(self, commit: CommitInfo, metrics: dict) -> None:
        """Update security metrics for a commit."""
        if self.pattern_matcher.is_security_fix(commit):
            metrics['security_fixes'] += 1
        if self.pattern_matcher.is_compliance_improvement(commit):
            metrics['compliance'] += 1
        if self.pattern_matcher.is_audit_preparation(commit):
            metrics['audit_items'] += 1
        if self.pattern_matcher.is_data_protection(commit):
            metrics['data_protection'] += 1
    
    def _calc_compliance_score(self, metrics: dict) -> float:
        """Calculate compliance score."""
        security = metrics['security_fixes']
        compliance = metrics['compliance']
        audit = metrics['audit_items']
        
        total_items = security + compliance + audit
        return min(total_items * 2.5, 10.0)
    
    def _calc_risk_reduction(self, metrics: dict) -> float:
        """Calculate security risk reduction percentage."""
        security = metrics['security_fixes']
        protection = metrics['data_protection']
        
        risk_items = security + protection
        return min(risk_items * 15, 100.0)  # Max 100% risk reduction