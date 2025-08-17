"""Pattern matching utilities for business value metrics.

Provides reusable pattern matching functions.
Follows 300-line limit with 8-line function limit.
"""

from typing import List
from .git_commit_parser import CommitInfo, CommitType
from .metrics_business_value_types import BusinessObjective


class PatternMatcher:
    """Utility class for pattern matching in commits."""
    
    CUSTOMER_FACING_PATTERNS = [
        r"frontend/", r"app/routes/", r"app/websocket/",
        r"public/", r"app/schemas/", r"components/chat/"
    ]
    
    REVENUE_PATTERNS = [
        r"payment", r"billing", r"subscription", r"pricing",
        r"monetization", r"revenue", r"purchase", r"sales"
    ]
    
    SECURITY_PATTERNS = [
        r"auth", r"security", r"crypto", r"password",
        r"token", r"permission", r"access", r"vulnerability"
    ]
    
    PERFORMANCE_PATTERNS = [
        r"cache", r"optimize", r"performance", r"speed",
        r"latency", r"throughput", r"efficiency"
    ]

    @staticmethod
    def matches_patterns(text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern."""
        return any(pattern in text for pattern in patterns)

    @staticmethod
    def classify_commit_objective(commit: CommitInfo) -> BusinessObjective:
        """Classify commit to business objective."""
        message_lower = commit.message.lower()
        
        if PatternMatcher._matches_security(message_lower):
            return BusinessObjective.COMPLIANCE_SECURITY
        if PatternMatcher._matches_revenue(message_lower):
            return BusinessObjective.REVENUE_GROWTH
        if PatternMatcher._matches_performance(message_lower):
            return BusinessObjective.OPERATIONAL_EXCELLENCE
        return PatternMatcher._classify_by_type(commit.commit_type)

    @staticmethod
    def _matches_security(message: str) -> bool:
        """Check if message matches security patterns."""
        return PatternMatcher.matches_patterns(
            message, PatternMatcher.SECURITY_PATTERNS
        )

    @staticmethod
    def _matches_revenue(message: str) -> bool:
        """Check if message matches revenue patterns."""
        return PatternMatcher.matches_patterns(
            message, PatternMatcher.REVENUE_PATTERNS
        )

    @staticmethod
    def _matches_performance(message: str) -> bool:
        """Check if message matches performance patterns."""
        return PatternMatcher.matches_patterns(
            message, PatternMatcher.PERFORMANCE_PATTERNS
        )

    @staticmethod
    def _classify_by_type(commit_type: CommitType) -> BusinessObjective:
        """Classify objective by commit type."""
        if commit_type == CommitType.FEATURE:
            return BusinessObjective.CUSTOMER_SATISFACTION
        if commit_type in [CommitType.REFACTOR, CommitType.CHORE]:
            return BusinessObjective.TEAM_PRODUCTIVITY
        return BusinessObjective.MARKET_COMPETITIVENESS

    @staticmethod
    def is_customer_facing_commit(commit: CommitInfo) -> bool:
        """Check if commit affects customer-facing components."""
        return PatternMatcher.matches_patterns(
            commit.message.lower(), 
            PatternMatcher.CUSTOMER_FACING_PATTERNS
        )

    @staticmethod
    def is_ux_improvement(commit: CommitInfo) -> bool:
        """Check if commit improves user experience."""
        ux_keywords = ["ui", "ux", "interface", "user", "experience", "usability"]
        return PatternMatcher.matches_patterns(commit.message.lower(), ux_keywords)

    @staticmethod
    def is_performance_enhancement(commit: CommitInfo) -> bool:
        """Check if commit enhances performance."""
        return PatternMatcher.matches_patterns(
            commit.message.lower(), 
            PatternMatcher.PERFORMANCE_PATTERNS
        )

    @staticmethod
    def is_revenue_generating(commit: CommitInfo) -> bool:
        """Check if commit generates revenue."""
        return PatternMatcher.matches_patterns(
            commit.message.lower(), 
            PatternMatcher.REVENUE_PATTERNS
        )

    @staticmethod
    def is_monetization_improvement(commit: CommitInfo) -> bool:
        """Check if commit improves monetization."""
        monetization_keywords = ["pricing", "payment", "billing", "subscription"]
        return PatternMatcher.matches_patterns(
            commit.message.lower(), 
            monetization_keywords
        )

    @staticmethod
    def is_market_expansion(commit: CommitInfo) -> bool:
        """Check if commit enables market expansion."""
        expansion_keywords = ["localization", "i18n", "region", "market", "global"]
        return PatternMatcher.matches_patterns(
            commit.message.lower(), 
            expansion_keywords
        )

    @staticmethod
    def is_conversion_improvement(commit: CommitInfo) -> bool:
        """Check if commit improves conversion."""
        conversion_keywords = ["onboarding", "signup", "registration", "conversion"]
        return PatternMatcher.matches_patterns(
            commit.message.lower(), 
            conversion_keywords
        )

    @staticmethod
    def is_security_fix(commit: CommitInfo) -> bool:
        """Check if commit is a security fix."""
        return PatternMatcher.matches_patterns(
            commit.message.lower(), 
            PatternMatcher.SECURITY_PATTERNS
        )

    @staticmethod
    def is_compliance_improvement(commit: CommitInfo) -> bool:
        """Check if commit improves compliance."""
        compliance_keywords = ["compliance", "regulation", "gdpr", "hipaa", "audit"]
        return PatternMatcher.matches_patterns(
            commit.message.lower(), 
            compliance_keywords
        )

    @staticmethod
    def is_audit_preparation(commit: CommitInfo) -> bool:
        """Check if commit prepares for audit."""
        audit_keywords = ["audit", "logging", "monitoring", "documentation"]
        return PatternMatcher.matches_patterns(
            commit.message.lower(), 
            audit_keywords
        )

    @staticmethod
    def is_data_protection(commit: CommitInfo) -> bool:
        """Check if commit enhances data protection."""
        protection_keywords = ["encryption", "privacy", "data protection", "anonymization"]
        return PatternMatcher.matches_patterns(
            commit.message.lower(), 
            protection_keywords
        )

    @staticmethod
    def is_innovation_commit(commit: CommitInfo) -> bool:
        """Check if commit represents innovation."""
        innovation_keywords = ["new", "innovative", "experimental", "research", "prototype"]
        return (commit.commit_type == CommitType.FEATURE or 
                PatternMatcher.matches_patterns(commit.message.lower(), innovation_keywords))

    @staticmethod
    def is_maintenance_commit(commit: CommitInfo) -> bool:
        """Check if commit is maintenance."""
        return commit.commit_type in [CommitType.FIX, CommitType.REFACTOR, 
                                     CommitType.CHORE, CommitType.STYLE]

    @staticmethod
    def involves_new_technology(commit: CommitInfo) -> bool:
        """Check if commit involves new technology adoption."""
        tech_keywords = ["api", "framework", "library", "integration", "upgrade"]
        return PatternMatcher.matches_patterns(
            commit.message.lower(), 
            tech_keywords
        )

    @staticmethod
    def is_experimental(commit: CommitInfo) -> bool:
        """Check if commit is experimental."""
        exp_keywords = ["experiment", "prototype", "poc", "trial", "beta"]
        return PatternMatcher.matches_patterns(
            commit.message.lower(), 
            exp_keywords
        )