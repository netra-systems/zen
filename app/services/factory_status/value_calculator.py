"""Value calculator for customer impact and revenue metrics.

Handles customer impact analysis and revenue metric calculations.
Module follows 300-line limit with 8-line function limit.
"""

from typing import Dict, List

from .git_commit_parser import GitCommitParser, CommitInfo, CommitType
from .business_core import (
    BusinessObjective, CustomerImpactMetrics, RevenueMetrics, 
    ComplianceSecurityMetrics, BusinessConstants
)


class ObjectiveMapper:
    """Maps commits to business objectives."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize objective mapper."""
        self.commit_parser = GitCommitParser(repo_path)
    
    def map_commits(self, hours: int = 168) -> Dict[BusinessObjective, int]:
        """Map commits to business objectives."""
        commits = self.commit_parser.get_commits(hours)
        mapping = {obj: 0 for obj in BusinessObjective}
        
        for commit in commits:
            objective = self._classify_commit_objective(commit)
            mapping[objective] += 1
        
        return mapping
    
    def _classify_commit_objective(self, commit: CommitInfo) -> BusinessObjective:
        """Classify commit to business objective."""
        message_lower = commit.message.lower()
        
        if self._matches_patterns(message_lower, BusinessConstants.SECURITY_PATTERNS):
            return BusinessObjective.COMPLIANCE_SECURITY
        if self._matches_patterns(message_lower, BusinessConstants.REVENUE_PATTERNS):
            return BusinessObjective.REVENUE_GROWTH
        if self._matches_patterns(message_lower, BusinessConstants.PERFORMANCE_PATTERNS):
            return BusinessObjective.OPERATIONAL_EXCELLENCE
        if commit.commit_type == CommitType.FEATURE:
            return BusinessObjective.CUSTOMER_SATISFACTION
        if commit.commit_type in [CommitType.REFACTOR, CommitType.CHORE]:
            return BusinessObjective.TEAM_PRODUCTIVITY
        
        return BusinessObjective.MARKET_COMPETITIVENESS
    
    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern."""
        return any(pattern in text for pattern in patterns)


class CustomerImpactCalculator:
    """Calculator for customer impact metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize customer impact calculator."""
        self.commit_parser = GitCommitParser(repo_path)
    
    def calculate(self, hours: int = 168) -> CustomerImpactMetrics:
        """Calculate customer impact metrics."""
        commits = self.commit_parser.get_commits(hours)
        impact_counts = self._count_all_customer_impacts(commits)
        return self._build_customer_impact_metrics(impact_counts)
    
    def _count_all_customer_impacts(self, commits: List[CommitInfo]) -> Dict[str, int]:
        """Count all types of customer impacts from commits."""
        counts = {'customer_facing': 0, 'ux_improvements': 0, 'performance': 0, 'bug_fixes': 0, 'new_features': 0}
        for commit in commits:
            self._update_customer_impact_counts(counts, commit)
        return counts
    
    def _update_customer_impact_counts(self, counts: Dict[str, int], commit: CommitInfo) -> None:
        """Update customer impact counts for a single commit."""
        if self._is_customer_facing_commit(commit):
            counts['customer_facing'] += 1
        if self._is_ux_improvement(commit):
            counts['ux_improvements'] += 1
        if self._is_performance_enhancement(commit):
            counts['performance'] += 1
        if commit.commit_type == CommitType.FIX:
            counts['bug_fixes'] += 1
        if commit.commit_type == CommitType.FEATURE:
            counts['new_features'] += 1
    
    def _build_customer_impact_metrics(self, counts: Dict[str, int]) -> CustomerImpactMetrics:
        """Build CustomerImpactMetrics from counts."""
        satisfaction_score = self._calculate_satisfaction_score(
            counts['customer_facing'], counts['ux_improvements'], counts['bug_fixes'], counts['new_features']
        )
        return CustomerImpactMetrics(
            customer_facing_changes=counts['customer_facing'],
            user_experience_improvements=counts['ux_improvements'],
            performance_enhancements=counts['performance'],
            bug_fixes_affecting_users=counts['bug_fixes'],
            new_features_delivered=counts['new_features'],
            customer_satisfaction_score=satisfaction_score
        )
    
    def _is_customer_facing_commit(self, commit: CommitInfo) -> bool:
        """Check if commit affects customer-facing components."""
        return self._matches_patterns(commit.message.lower(), BusinessConstants.CUSTOMER_FACING_PATTERNS)
    
    def _is_ux_improvement(self, commit: CommitInfo) -> bool:
        """Check if commit improves user experience."""
        ux_keywords = ["ui", "ux", "interface", "user", "experience", "usability"]
        return self._matches_patterns(commit.message.lower(), ux_keywords)
    
    def _is_performance_enhancement(self, commit: CommitInfo) -> bool:
        """Check if commit enhances performance."""
        return self._matches_patterns(commit.message.lower(), BusinessConstants.PERFORMANCE_PATTERNS)
    
    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern."""
        return any(pattern in text for pattern in patterns)
    
    def _calculate_satisfaction_score(self, customer_facing: int, ux: int,
                                    fixes: int, features: int) -> float:
        """Calculate customer satisfaction score."""
        positive_impact = customer_facing * 2 + ux * 3 + features * 2
        stability_impact = fixes * 1.5
        
        total_score = positive_impact + stability_impact
        return min(total_score / 10, 10.0)


class RevenueCalculator:
    """Calculator for revenue-related metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize revenue calculator."""
        self.commit_parser = GitCommitParser(repo_path)
    
    def calculate(self, hours: int = 168) -> RevenueMetrics:
        """Calculate revenue-related metrics."""
        commits = self.commit_parser.get_commits(hours)
        counts = self._count_revenue_features(commits)
        scores = self._calculate_revenue_scores(commits, counts)
        return self._build_revenue_metrics(counts, scores)
    
    def _count_revenue_features(self, commits: List[CommitInfo]) -> Dict[str, int]:
        """Count all revenue-related features from commits."""
        counts = {'revenue': 0, 'monetization': 0, 'market': 0, 'conversion': 0}
        for commit in commits:
            self._update_revenue_counts(counts, commit)
        return counts
    
    def _update_revenue_counts(self, counts: Dict[str, int], commit: CommitInfo) -> None:
        """Update revenue counts for a single commit."""
        if self._is_revenue_generating(commit):
            counts['revenue'] += 1
        if self._is_monetization_improvement(commit):
            counts['monetization'] += 1
        if self._is_market_expansion(commit):
            counts['market'] += 1
        if self._is_conversion_improvement(commit):
            counts['conversion'] += 1
    
    def _calculate_revenue_scores(self, commits: List[CommitInfo], counts: Dict[str, int]) -> Dict[str, float]:
        """Calculate subscription score and revenue impact."""
        return {
            'subscription': self._calculate_subscription_impact(commits),
            'impact': self._estimate_revenue_impact(counts['revenue'], counts['monetization'])
        }
    
    def _build_revenue_metrics(self, counts: Dict[str, int], scores: Dict[str, float]) -> RevenueMetrics:
        """Build RevenueMetrics from counts and scores."""
        return RevenueMetrics(
            revenue_generating_features=counts['revenue'],
            monetization_improvements=counts['monetization'],
            market_expansion_features=counts['market'],
            subscription_impact_score=scores['subscription'],
            estimated_revenue_impact=scores['impact'],
            conversion_improvements=counts['conversion']
        )
    
    def _is_revenue_generating(self, commit: CommitInfo) -> bool:
        """Check if commit generates revenue."""
        return self._matches_patterns(commit.message.lower(), BusinessConstants.REVENUE_PATTERNS)
    
    def _is_monetization_improvement(self, commit: CommitInfo) -> bool:
        """Check if commit improves monetization."""
        monetization_keywords = ["pricing", "payment", "billing", "subscription"]
        return self._matches_patterns(commit.message.lower(), monetization_keywords)
    
    def _is_market_expansion(self, commit: CommitInfo) -> bool:
        """Check if commit enables market expansion."""
        expansion_keywords = ["localization", "i18n", "region", "market", "global"]
        return self._matches_patterns(commit.message.lower(), expansion_keywords)
    
    def _is_conversion_improvement(self, commit: CommitInfo) -> bool:
        """Check if commit improves conversion."""
        conversion_keywords = ["onboarding", "signup", "registration", "conversion"]
        return self._matches_patterns(commit.message.lower(), conversion_keywords)
    
    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern."""
        return any(pattern in text for pattern in patterns)
    
    def _calculate_subscription_impact(self, commits: List[CommitInfo]) -> float:
        """Calculate subscription impact score."""
        subscription_commits = [c for c in commits 
                              if "subscription" in c.message.lower()]
        if not subscription_commits:
            return 0.0
        return min(len(subscription_commits) * 2.5, 10.0)
    
    def _estimate_revenue_impact(self, revenue_features: int, 
                                monetization: int) -> float:
        """Estimate revenue impact in dollars."""
        base_feature_value = 10000
        monetization_value = 25000
        return (revenue_features * base_feature_value + monetization * monetization_value)


class ComplianceSecurityCalculator:
    """Calculator for compliance and security metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize compliance security calculator."""
        self.commit_parser = GitCommitParser(repo_path)
    
    def calculate(self, hours: int = 168) -> ComplianceSecurityMetrics:
        """Calculate compliance and security metrics."""
        commits = self.commit_parser.get_commits(hours)
        counts = self._count_security_features(commits)
        scores = self._calculate_security_scores(counts)
        return self._build_security_metrics(counts, scores)
    
    def _count_security_features(self, commits: List[CommitInfo]) -> Dict[str, int]:
        """Count all security-related features from commits."""
        counts = {'security': 0, 'compliance': 0, 'audit': 0, 'protection': 0}
        for commit in commits:
            self._update_security_counts(counts, commit)
        return counts
    
    def _update_security_counts(self, counts: Dict[str, int], commit: CommitInfo) -> None:
        """Update security counts for a single commit."""
        if self._is_security_fix(commit):
            counts['security'] += 1
        if self._is_compliance_improvement(commit):
            counts['compliance'] += 1
        if self._is_audit_preparation(commit):
            counts['audit'] += 1
        if self._is_data_protection(commit):
            counts['protection'] += 1
    
    def _calculate_security_scores(self, counts: Dict[str, int]) -> Dict[str, float]:
        """Calculate compliance score and risk reduction."""
        return {
            'compliance': self._calculate_compliance_score(counts['security'], counts['compliance'], counts['audit']),
            'risk': self._calculate_risk_reduction(counts['security'], counts['protection'])
        }
    
    def _build_security_metrics(self, counts: Dict[str, int], scores: Dict[str, float]) -> ComplianceSecurityMetrics:
        """Build ComplianceSecurityMetrics from counts and scores."""
        return ComplianceSecurityMetrics(
            security_fixes=counts['security'],
            compliance_improvements=counts['compliance'],
            audit_preparation_items=counts['audit'],
            data_protection_enhancements=counts['protection'],
            regulatory_compliance_score=scores['compliance'],
            security_risk_reduction=scores['risk']
        )
    
    def _is_security_fix(self, commit: CommitInfo) -> bool:
        """Check if commit is a security fix."""
        return self._matches_patterns(commit.message.lower(), BusinessConstants.SECURITY_PATTERNS)
    
    def _is_compliance_improvement(self, commit: CommitInfo) -> bool:
        """Check if commit improves compliance."""
        compliance_keywords = ["compliance", "regulation", "gdpr", "hipaa", "audit"]
        return self._matches_patterns(commit.message.lower(), compliance_keywords)
    
    def _is_audit_preparation(self, commit: CommitInfo) -> bool:
        """Check if commit prepares for audit."""
        audit_keywords = ["audit", "logging", "monitoring", "documentation"]
        return self._matches_patterns(commit.message.lower(), audit_keywords)
    
    def _is_data_protection(self, commit: CommitInfo) -> bool:
        """Check if commit enhances data protection."""
        protection_keywords = ["encryption", "privacy", "data protection", "anonymization"]
        return self._matches_patterns(commit.message.lower(), protection_keywords)
    
    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern."""
        return any(pattern in text for pattern in patterns)
    
    def _calculate_compliance_score(self, security: int, compliance: int, 
                                   audit: int) -> float:
        """Calculate compliance score."""
        return min((security + compliance + audit) * 2.5, 10.0)
    
    def _calculate_risk_reduction(self, security: int, protection: int) -> float:
        """Calculate security risk reduction percentage."""
        return min((security + protection) * 15, 100.0)