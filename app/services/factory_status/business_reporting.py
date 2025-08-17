"""Business reporting for ROI estimation and overall business metrics.

Handles ROI calculations, innovation metrics, and overall business value.
Module follows 300-line limit with 8-line function limit.
"""

from typing import List

from .git_commit_parser import GitCommitParser, CommitInfo, CommitType
from .business_core import (
    BusinessObjective, ROIEstimate, InnovationMetrics, BusinessValueMetrics,
    CustomerImpactMetrics, RevenueMetrics, ComplianceSecurityMetrics
)


class InnovationCalculator:
    """Calculator for innovation vs maintenance metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize innovation calculator."""
        self.commit_parser = GitCommitParser(repo_path)
    
    def calculate(self, hours: int = 168) -> InnovationMetrics:
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
    
    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern."""
        return any(pattern in text for pattern in patterns)
    
    def _calculate_advancement_score(self, innovation: int, new_tech: int,
                                   experimental: int) -> float:
        """Calculate technical advancement score."""
        advancement_points = innovation * 2 + new_tech * 3 + experimental * 1.5
        return min(advancement_points / 5, 10.0)


class ROICalculator:
    """Calculator for return on investment estimates."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize ROI calculator."""
        self.commit_parser = GitCommitParser(repo_path)
    
    def estimate(self, hours: int = 168) -> ROIEstimate:
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
        total_changes = sum(c.insertions + c.deletions for c in commits)
        estimated_hours = total_changes * 0.1
        
        return max(estimated_hours, len(commits) * 0.5)
    
    def _estimate_benefit_value(self, commits: List[CommitInfo]) -> float:
        """Estimate total benefit value."""
        benefit = 0.0
        
        for commit in commits:
            if commit.commit_type == CommitType.FEATURE:
                benefit += 5000
            elif commit.commit_type == CommitType.FIX:
                benefit += 2000
            elif commit.commit_type == CommitType.PERF:
                benefit += 3000
        
        return benefit
    
    def _calculate_roi_percentage(self, hours: float, benefit: float) -> float:
        """Calculate ROI percentage."""
        if hours == 0:
            return 0.0
        
        cost = hours * 100
        return ((benefit - cost) / cost) * 100 if cost > 0 else 0.0
    
    def _calculate_payback_period(self, hours: float, benefit: float) -> int:
        """Calculate payback period in days."""
        if benefit == 0:
            return 999
        
        cost = hours * 100
        daily_benefit = benefit / 30
        
        return int(cost / daily_benefit) if daily_benefit > 0 else 999
    
    def _calculate_confidence_level(self, commits: List[CommitInfo]) -> float:
        """Calculate confidence level in estimates."""
        if len(commits) < 5:
            return 0.3
        elif len(commits) < 20:
            return 0.7
        return 0.9
    
    def _estimate_value_timeline(self, commits: List[CommitInfo]) -> str:
        """Estimate value realization timeline."""
        from .business_core import BusinessConstants
        
        customer_facing = sum(1 for c in commits if self._is_customer_facing_commit(c))
        total_commits = len(commits)
        
        if customer_facing / max(total_commits, 1) > 0.5:
            return "Immediate (1-2 weeks)"
        elif customer_facing > 0:
            return "Short-term (1-2 months)"
        return "Long-term (3-6 months)"
    
    def _is_customer_facing_commit(self, commit: CommitInfo) -> bool:
        """Check if commit affects customer-facing components."""
        from .business_core import BusinessConstants
        return any(pattern in commit.message.lower() for pattern in BusinessConstants.CUSTOMER_FACING_PATTERNS)


class BusinessValueCalculator:
    """Main calculator orchestrating all business value metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize business value calculator."""
        self.repo_path = repo_path
    
    def calculate_business_value_metrics(self, hours: int = 168) -> BusinessValueMetrics:
        """Calculate comprehensive business value metrics."""
        from .value_calculator import (
            ObjectiveMapper, CustomerImpactCalculator, 
            RevenueCalculator, ComplianceSecurityCalculator
        )
        
        objective_mapper = ObjectiveMapper(self.repo_path)
        customer_calc = CustomerImpactCalculator(self.repo_path)
        revenue_calc = RevenueCalculator(self.repo_path)
        compliance_calc = ComplianceSecurityCalculator(self.repo_path)
        innovation_calc = InnovationCalculator(self.repo_path)
        roi_calc = ROICalculator(self.repo_path)
        
        objective_mapping = objective_mapper.map_commits(hours)
        customer_impact = customer_calc.calculate(hours)
        revenue_metrics = revenue_calc.calculate(hours)
        compliance_security = compliance_calc.calculate(hours)
        innovation_metrics = innovation_calc.calculate(hours)
        roi_estimate = roi_calc.estimate(hours)
        
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
        revenue_score = min(revenue.estimated_revenue_impact / 10000, 10)
        security_score = security.regulatory_compliance_score
        innovation_score = innovation.technical_advancement_score
        
        weights = [0.3, 0.25, 0.25, 0.2]
        scores = [customer_score, revenue_score, security_score, innovation_score]
        
        return sum(w * s for w, s in zip(weights, scores))