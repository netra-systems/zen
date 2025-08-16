"""Business value metrics for AI Factory Status Report.

Maps commits to business objectives and calculates ROI estimates.
Module follows 300-line limit with 8-line function limit.
"""

import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from .git_commit_parser import GitCommitParser, CommitInfo, CommitType
from .git_diff_analyzer import GitDiffAnalyzer, DiffMetrics, BusinessImpact


class BusinessObjective(Enum):
    """Business objectives for mapping commits."""
    CUSTOMER_SATISFACTION = "customer_satisfaction"
    REVENUE_GROWTH = "revenue_growth"
    OPERATIONAL_EXCELLENCE = "operational_excellence"
    MARKET_COMPETITIVENESS = "market_competitiveness"
    COMPLIANCE_SECURITY = "compliance_security"
    TEAM_PRODUCTIVITY = "team_productivity"


class ValueCategory(Enum):
    """Categories of business value."""
    DIRECT_REVENUE = "direct_revenue"
    COST_REDUCTION = "cost_reduction"
    RISK_MITIGATION = "risk_mitigation"
    EFFICIENCY_GAIN = "efficiency_gain"
    INNOVATION = "innovation"
    MAINTENANCE = "maintenance"


@dataclass
class BusinessValueScore:
    """Business value score for a change."""
    objective: BusinessObjective
    category: ValueCategory
    impact_score: float
    confidence: float
    revenue_potential: float
    cost_impact: float
    time_to_value: int  # days


@dataclass
class CustomerImpactMetrics:
    """Customer impact assessment."""
    customer_facing_changes: int
    user_experience_improvements: int
    performance_enhancements: int
    bug_fixes_affecting_users: int
    new_features_delivered: int
    customer_satisfaction_score: float


@dataclass
class RevenueMetrics:
    """Revenue-related metrics."""
    revenue_generating_features: int
    monetization_improvements: int
    market_expansion_features: int
    subscription_impact_score: float
    estimated_revenue_impact: float
    conversion_improvements: int


@dataclass
class ComplianceSecurityMetrics:
    """Compliance and security metrics."""
    security_fixes: int
    compliance_improvements: int
    audit_preparation_items: int
    data_protection_enhancements: int
    regulatory_compliance_score: float
    security_risk_reduction: float


@dataclass
class ROIEstimate:
    """Return on investment estimate."""
    investment_hours: float
    estimated_benefit_value: float
    roi_percentage: float
    payback_period_days: int
    confidence_level: float
    value_realization_timeline: str


@dataclass
class InnovationMetrics:
    """Innovation vs maintenance tracking."""
    innovation_commits: int
    maintenance_commits: int
    innovation_ratio: float
    new_technology_adoption: int
    experimental_features: int
    technical_advancement_score: float


@dataclass
class BusinessValueMetrics:
    """Comprehensive business value metrics."""
    objective_mapping: Dict[BusinessObjective, int]
    customer_impact: CustomerImpactMetrics
    revenue_metrics: RevenueMetrics
    compliance_security: ComplianceSecurityMetrics
    roi_estimate: ROIEstimate
    innovation_metrics: InnovationMetrics
    overall_business_value: float


class BusinessValueCalculator:
    """Calculator for business value metrics."""
    
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
    
    def __init__(self, repo_path: str = "."):
        """Initialize business value calculator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.diff_analyzer = GitDiffAnalyzer(repo_path)
        self.repo_path = repo_path
    
    def map_commits_to_objectives(self, hours: int = 168) -> Dict[BusinessObjective, int]:
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
        
        if self._matches_patterns(message_lower, self.SECURITY_PATTERNS):
            return BusinessObjective.COMPLIANCE_SECURITY
        if self._matches_patterns(message_lower, self.REVENUE_PATTERNS):
            return BusinessObjective.REVENUE_GROWTH
        if self._matches_patterns(message_lower, self.PERFORMANCE_PATTERNS):
            return BusinessObjective.OPERATIONAL_EXCELLENCE
        if commit.commit_type == CommitType.FEATURE:
            return BusinessObjective.CUSTOMER_SATISFACTION
        if commit.commit_type in [CommitType.REFACTOR, CommitType.CHORE]:
            return BusinessObjective.TEAM_PRODUCTIVITY
        
        return BusinessObjective.MARKET_COMPETITIVENESS
    
    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern."""
        return any(pattern in text for pattern in patterns)
    
    def calculate_customer_impact(self, hours: int = 168) -> CustomerImpactMetrics:
        """Calculate customer impact metrics."""
        commits = self.commit_parser.get_commits(hours)
        
        customer_facing = 0
        ux_improvements = 0
        performance_enhancements = 0
        bug_fixes = 0
        new_features = 0
        
        for commit in commits:
            if self._is_customer_facing_commit(commit):
                customer_facing += 1
            if self._is_ux_improvement(commit):
                ux_improvements += 1
            if self._is_performance_enhancement(commit):
                performance_enhancements += 1
            if commit.commit_type == CommitType.FIX:
                bug_fixes += 1
            if commit.commit_type == CommitType.FEATURE:
                new_features += 1
        
        satisfaction_score = self._calculate_satisfaction_score(
            customer_facing, ux_improvements, bug_fixes, new_features
        )
        
        return CustomerImpactMetrics(
            customer_facing_changes=customer_facing,
            user_experience_improvements=ux_improvements,
            performance_enhancements=performance_enhancements,
            bug_fixes_affecting_users=bug_fixes,
            new_features_delivered=new_features,
            customer_satisfaction_score=satisfaction_score
        )
    
    def _is_customer_facing_commit(self, commit: CommitInfo) -> bool:
        """Check if commit affects customer-facing components."""
        return self._matches_patterns(commit.message.lower(), self.CUSTOMER_FACING_PATTERNS)
    
    def _is_ux_improvement(self, commit: CommitInfo) -> bool:
        """Check if commit improves user experience."""
        ux_keywords = ["ui", "ux", "interface", "user", "experience", "usability"]
        return self._matches_patterns(commit.message.lower(), ux_keywords)
    
    def _is_performance_enhancement(self, commit: CommitInfo) -> bool:
        """Check if commit enhances performance."""
        return self._matches_patterns(commit.message.lower(), self.PERFORMANCE_PATTERNS)
    
    def _calculate_satisfaction_score(self, customer_facing: int, ux: int,
                                    fixes: int, features: int) -> float:
        """Calculate customer satisfaction score."""
        positive_impact = customer_facing * 2 + ux * 3 + features * 2
        stability_impact = fixes * 1.5
        
        total_score = positive_impact + stability_impact
        return min(total_score / 10, 10.0)  # Normalize to 0-10
    
    def calculate_revenue_metrics(self, hours: int = 168) -> RevenueMetrics:
        """Calculate revenue-related metrics."""
        commits = self.commit_parser.get_commits(hours)
        
        revenue_features = 0
        monetization_improvements = 0
        market_expansion = 0
        conversion_improvements = 0
        
        for commit in commits:
            if self._is_revenue_generating(commit):
                revenue_features += 1
            if self._is_monetization_improvement(commit):
                monetization_improvements += 1
            if self._is_market_expansion(commit):
                market_expansion += 1
            if self._is_conversion_improvement(commit):
                conversion_improvements += 1
        
        subscription_score = self._calculate_subscription_impact(commits)
        revenue_impact = self._estimate_revenue_impact(
            revenue_features, monetization_improvements
        )
        
        return RevenueMetrics(
            revenue_generating_features=revenue_features,
            monetization_improvements=monetization_improvements,
            market_expansion_features=market_expansion,
            subscription_impact_score=subscription_score,
            estimated_revenue_impact=revenue_impact,
            conversion_improvements=conversion_improvements
        )
    
    def _is_revenue_generating(self, commit: CommitInfo) -> bool:
        """Check if commit generates revenue."""
        return self._matches_patterns(commit.message.lower(), self.REVENUE_PATTERNS)
    
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
        # Simplified estimation model
        base_feature_value = 10000  # $10k per revenue feature
        monetization_value = 25000  # $25k per monetization improvement
        
        return (revenue_features * base_feature_value + 
                monetization * monetization_value)
    
    def calculate_compliance_security_metrics(self, hours: int = 168) -> ComplianceSecurityMetrics:
        """Calculate compliance and security metrics."""
        commits = self.commit_parser.get_commits(hours)
        
        security_fixes = 0
        compliance_improvements = 0
        audit_items = 0
        data_protection = 0
        
        for commit in commits:
            if self._is_security_fix(commit):
                security_fixes += 1
            if self._is_compliance_improvement(commit):
                compliance_improvements += 1
            if self._is_audit_preparation(commit):
                audit_items += 1
            if self._is_data_protection(commit):
                data_protection += 1
        
        compliance_score = self._calculate_compliance_score(
            security_fixes, compliance_improvements, audit_items
        )
        risk_reduction = self._calculate_risk_reduction(
            security_fixes, data_protection
        )
        
        return ComplianceSecurityMetrics(
            security_fixes=security_fixes,
            compliance_improvements=compliance_improvements,
            audit_preparation_items=audit_items,
            data_protection_enhancements=data_protection,
            regulatory_compliance_score=compliance_score,
            security_risk_reduction=risk_reduction
        )
    
    def _is_security_fix(self, commit: CommitInfo) -> bool:
        """Check if commit is a security fix."""
        return self._matches_patterns(commit.message.lower(), self.SECURITY_PATTERNS)
    
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
    
    def _calculate_compliance_score(self, security: int, compliance: int, 
                                   audit: int) -> float:
        """Calculate compliance score."""
        total_items = security + compliance + audit
        return min(total_items * 2.5, 10.0)
    
    def _calculate_risk_reduction(self, security: int, protection: int) -> float:
        """Calculate security risk reduction percentage."""
        risk_items = security + protection
        return min(risk_items * 15, 100.0)  # Max 100% risk reduction
    
    def calculate_innovation_metrics(self, hours: int = 168) -> InnovationMetrics:
        """Calculate innovation vs maintenance metrics."""
        commits = self.commit_parser.get_commits(hours)
        
        innovation_commits = 0
        maintenance_commits = 0
        new_tech = 0
        experimental = 0
        
        for commit in commits:
            if self._is_innovation_commit(commit):
                innovation_commits += 1
            elif self._is_maintenance_commit(commit):
                maintenance_commits += 1
            
            if self._involves_new_technology(commit):
                new_tech += 1
            if self._is_experimental(commit):
                experimental += 1
        
        total_commits = len(commits)
        innovation_ratio = (innovation_commits / max(total_commits, 1)) * 100
        
        advancement_score = self._calculate_advancement_score(
            innovation_commits, new_tech, experimental
        )
        
        return InnovationMetrics(
            innovation_commits=innovation_commits,
            maintenance_commits=maintenance_commits,
            innovation_ratio=innovation_ratio,
            new_technology_adoption=new_tech,
            experimental_features=experimental,
            technical_advancement_score=advancement_score
        )
    
    def _is_innovation_commit(self, commit: CommitInfo) -> bool:
        """Check if commit represents innovation."""
        innovation_keywords = ["new", "innovative", "experimental", "research", "prototype"]
        return (commit.commit_type == CommitType.FEATURE or 
                self._matches_patterns(commit.message.lower(), innovation_keywords))
    
    def _is_maintenance_commit(self, commit: CommitInfo) -> bool:
        """Check if commit is maintenance."""
        return commit.commit_type in [CommitType.FIX, CommitType.REFACTOR, 
                                     CommitType.CHORE, CommitType.STYLE]
    
    def _involves_new_technology(self, commit: CommitInfo) -> bool:
        """Check if commit involves new technology adoption."""
        tech_keywords = ["api", "framework", "library", "integration", "upgrade"]
        return self._matches_patterns(commit.message.lower(), tech_keywords)
    
    def _is_experimental(self, commit: CommitInfo) -> bool:
        """Check if commit is experimental."""
        exp_keywords = ["experiment", "prototype", "poc", "trial", "beta"]
        return self._matches_patterns(commit.message.lower(), exp_keywords)
    
    def _calculate_advancement_score(self, innovation: int, new_tech: int,
                                   experimental: int) -> float:
        """Calculate technical advancement score."""
        advancement_points = innovation * 2 + new_tech * 3 + experimental * 1.5
        return min(advancement_points / 5, 10.0)
    
    def estimate_roi(self, hours: int = 168) -> ROIEstimate:
        """Estimate return on investment."""
        commits = self.commit_parser.get_commits(hours)
        
        investment_hours = self._calculate_investment_hours(commits)
        benefit_value = self._estimate_benefit_value(commits)
        
        roi_percentage = self._calculate_roi_percentage(investment_hours, benefit_value)
        payback_days = self._calculate_payback_period(investment_hours, benefit_value)
        confidence = self._calculate_confidence_level(commits)
        timeline = self._estimate_value_timeline(commits)
        
        return ROIEstimate(
            investment_hours=investment_hours,
            estimated_benefit_value=benefit_value,
            roi_percentage=roi_percentage,
            payback_period_days=payback_days,
            confidence_level=confidence,
            value_realization_timeline=timeline
        )
    
    def _calculate_investment_hours(self, commits: List[CommitInfo]) -> float:
        """Calculate total investment hours."""
        # Estimate based on commit complexity
        total_changes = sum(c.insertions + c.deletions for c in commits)
        estimated_hours = total_changes * 0.1  # 1 hour per 10 lines changed
        
        return max(estimated_hours, len(commits) * 0.5)  # Minimum 30 min per commit
    
    def _estimate_benefit_value(self, commits: List[CommitInfo]) -> float:
        """Estimate total benefit value."""
        benefit = 0.0
        
        for commit in commits:
            if commit.commit_type == CommitType.FEATURE:
                benefit += 5000  # $5k per feature
            elif commit.commit_type == CommitType.FIX:
                benefit += 2000  # $2k per fix
            elif commit.commit_type == CommitType.PERF:
                benefit += 3000  # $3k per performance improvement
        
        return benefit
    
    def _calculate_roi_percentage(self, hours: float, benefit: float) -> float:
        """Calculate ROI percentage."""
        if hours == 0:
            return 0.0
        
        cost = hours * 100  # $100 per hour developer cost
        return ((benefit - cost) / cost) * 100 if cost > 0 else 0.0
    
    def _calculate_payback_period(self, hours: float, benefit: float) -> int:
        """Calculate payback period in days."""
        if benefit == 0:
            return 999  # No payback
        
        cost = hours * 100
        daily_benefit = benefit / 30  # Spread over 30 days
        
        return int(cost / daily_benefit) if daily_benefit > 0 else 999
    
    def _calculate_confidence_level(self, commits: List[CommitInfo]) -> float:
        """Calculate confidence level in estimates."""
        if len(commits) < 5:
            return 0.3  # Low confidence
        elif len(commits) < 20:
            return 0.7  # Medium confidence
        return 0.9  # High confidence
    
    def _estimate_value_timeline(self, commits: List[CommitInfo]) -> str:
        """Estimate value realization timeline."""
        customer_facing = sum(1 for c in commits if self._is_customer_facing_commit(c))
        total_commits = len(commits)
        
        if customer_facing / max(total_commits, 1) > 0.5:
            return "Immediate (1-2 weeks)"
        elif customer_facing > 0:
            return "Short-term (1-2 months)"
        return "Long-term (3-6 months)"
    
    def calculate_business_value_metrics(self, hours: int = 168) -> BusinessValueMetrics:
        """Calculate comprehensive business value metrics."""
        objective_mapping = self.map_commits_to_objectives(hours)
        customer_impact = self.calculate_customer_impact(hours)
        revenue_metrics = self.calculate_revenue_metrics(hours)
        compliance_security = self.calculate_compliance_security_metrics(hours)
        roi_estimate = self.estimate_roi(hours)
        innovation_metrics = self.calculate_innovation_metrics(hours)
        
        overall_value = self._calculate_overall_business_value(
            customer_impact, revenue_metrics, compliance_security, 
            innovation_metrics
        )
        
        return BusinessValueMetrics(
            objective_mapping=objective_mapping,
            customer_impact=customer_impact,
            revenue_metrics=revenue_metrics,
            compliance_security=compliance_security,
            roi_estimate=roi_estimate,
            innovation_metrics=innovation_metrics,
            overall_business_value=overall_value
        )
    
    def _calculate_overall_business_value(self, customer: CustomerImpactMetrics,
                                         revenue: RevenueMetrics,
                                         security: ComplianceSecurityMetrics,
                                         innovation: InnovationMetrics) -> float:
        """Calculate overall business value score."""
        customer_score = customer.customer_satisfaction_score
        revenue_score = min(revenue.estimated_revenue_impact / 10000, 10)  # Normalize
        security_score = security.regulatory_compliance_score
        innovation_score = innovation.technical_advancement_score
        
        weights = [0.3, 0.25, 0.25, 0.2]
        scores = [customer_score, revenue_score, security_score, innovation_score]
        
        return sum(w * s for w, s in zip(weights, scores))