"""Business value metrics aggregator.

Orchestrates all business value calculators and provides comprehensive metrics.
Follows 450-line limit with 25-line function limit.
"""

from typing import Dict

from netra_backend.app.services.factory_status.git_commit_parser import GitCommitParser
from netra_backend.app.services.factory_status.metrics_business_value_types import (
    BusinessObjective,
    BusinessValueMetrics,
    ComplianceSecurityMetrics,
    CustomerImpactMetrics,
    InnovationMetrics,
    RevenueMetrics,
)
from netra_backend.app.services.factory_status.metrics_compliance_security import (
    ComplianceSecurityCalculator,
)
from netra_backend.app.services.factory_status.metrics_customer_impact import (
    CustomerImpactCalculator,
)
from netra_backend.app.services.factory_status.metrics_innovation import (
    InnovationCalculator,
)
from netra_backend.app.services.factory_status.metrics_pattern_utils import (
    BusinessValuePatternMatcher,
)
from netra_backend.app.services.factory_status.metrics_revenue import RevenueCalculator
from netra_backend.app.services.factory_status.metrics_roi import ROICalculator


class BusinessValueAggregator:
    """Aggregates all business value metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize business value aggregator."""
        self.commit_parser = GitCommitParser(repo_path)
        self.pattern_matcher = BusinessValuePatternMatcher()
        self.customer_calc = CustomerImpactCalculator(repo_path)
        self.revenue_calc = RevenueCalculator(repo_path)
        self.security_calc = ComplianceSecurityCalculator(repo_path)
        self.innovation_calc = InnovationCalculator(repo_path)
        self.roi_calc = ROICalculator(repo_path)
        self.repo_path = repo_path
    
    def calculate_business_value_metrics(self, hours: int = 168) -> BusinessValueMetrics:
        """Calculate comprehensive business value metrics."""
        objective_mapping = self._map_commits_to_objectives(hours)
        customer_impact = self.customer_calc.calculate_customer_impact(hours)
        revenue_metrics = self.revenue_calc.calculate_revenue_metrics(hours)
        compliance_security = self.security_calc.calculate_compliance_security_metrics(hours)
        roi_estimate = self.roi_calc.estimate_roi(hours)
        innovation_metrics = self.innovation_calc.calculate_innovation_metrics(hours)
        
        overall_value = self._calc_overall_business_value(
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
    
    def _map_commits_to_objectives(self, hours: int = 168) -> Dict[BusinessObjective, int]:
        """Map commits to business objectives."""
        commits = self.commit_parser.get_commits(hours)
        mapping = {obj: 0 for obj in BusinessObjective}
        
        for commit in commits:
            objective = self.pattern_matcher.classify_commit_objective(commit)
            mapping[objective] += 1
        
        return mapping
    
    def _calc_overall_business_value(self, customer: CustomerImpactMetrics,
                                   revenue: RevenueMetrics,
                                   security: ComplianceSecurityMetrics,
                                   innovation: InnovationMetrics) -> float:
        """Calculate overall business value score."""
        scores = self._extract_scores(customer, revenue, security, innovation)
        weights = [0.3, 0.25, 0.25, 0.2]
        
        return sum(w * s for w, s in zip(weights, scores))
    
    def _extract_scores(self, customer: CustomerImpactMetrics,
                       revenue: RevenueMetrics,
                       security: ComplianceSecurityMetrics,
                       innovation: InnovationMetrics) -> list:
        """Extract normalized scores from metrics."""
        customer_score = customer.customer_satisfaction_score
        revenue_score = min(revenue.estimated_revenue_impact / 10000, 10)  # Normalize
        security_score = security.regulatory_compliance_score
        innovation_score = innovation.technical_advancement_score
        
        return [customer_score, revenue_score, security_score, innovation_score]