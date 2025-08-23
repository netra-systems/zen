"""Business reporting for ROI estimation and overall business metrics.

Handles ROI calculations, innovation metrics, and overall business value.
Module follows 450-line limit with 25-line function limit.
"""

from typing import List

from netra_backend.app.services.factory_status.business_core import (
    BusinessObjective,
    BusinessValueMetrics,
    ComplianceSecurityMetrics,
    CustomerImpactMetrics,
    InnovationMetrics,
    RevenueMetrics,
    ROIEstimate,
)
from netra_backend.app.services.factory_status.git_commit_parser import (
    CommitInfo,
    CommitType,
    GitCommitParser,
)


class InnovationCalculator:
    """Calculator for innovation vs maintenance metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize innovation calculator."""
        self.commit_parser = GitCommitParser(repo_path)
    
    def calculate(self, hours: int = 168) -> InnovationMetrics:
        """Calculate innovation vs maintenance metrics."""
        commits = self.commit_parser.get_commits(hours)
        commit_counters = self._analyze_commits_for_innovation(commits)
        return self._build_innovation_metrics(commit_counters, len(commits))
    
    def _analyze_commits_for_innovation(self, commits: List[CommitInfo]) -> dict:
        """Analyze commits and count innovation indicators."""
        counters = {'innovation': 0, 'maintenance': 0, 'new_tech': 0, 'experimental': 0}
        for commit in commits:
            self._update_commit_counters(counters, commit)
        return counters
    
    def _update_commit_counters(self, counters: dict, commit: CommitInfo) -> None:
        """Update commit counters based on commit type."""
        if self._is_innovation_commit(commit):
            counters['innovation'] += 1
        elif self._is_maintenance_commit(commit):
            counters['maintenance'] += 1
        
        if self._involves_new_technology(commit):
            counters['new_tech'] += 1
        if self._is_experimental(commit):
            counters['experimental'] += 1
    
    def _build_innovation_metrics(self, counters: dict, total_commits: int) -> InnovationMetrics:
        """Build innovation metrics from counters."""
        innovation_ratio = (counters['innovation'] / max(total_commits, 1)) * 100
        advancement_score = self._calculate_advancement_score(
            counters['innovation'], counters['new_tech'], counters['experimental']
        )
        return InnovationMetrics(
            innovation_commits=counters['innovation'],
            maintenance_commits=counters['maintenance'],
            innovation_ratio=innovation_ratio,
            new_technology_adoption=counters['new_tech'],
            experimental_features=counters['experimental'],
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
        roi_data = self._calculate_roi_data(commits)
        return self._build_roi_estimate(roi_data)
    
    def _calculate_roi_data(self, commits: List[CommitInfo]) -> dict:
        """Calculate ROI calculation data."""
        investment_hours = self._calculate_investment_hours(commits)
        benefit_value = self._estimate_benefit_value(commits)
        return {
            'investment_hours': investment_hours,
            'benefit_value': benefit_value,
            'roi_percentage': self._calculate_roi_percentage(investment_hours, benefit_value),
            'payback_days': self._calculate_payback_period(investment_hours, benefit_value),
            'confidence': self._calculate_confidence_level(commits),
            'timeline': self._estimate_value_timeline(commits)
        }
    
    def _build_roi_estimate(self, roi_data: dict) -> ROIEstimate:
        """Build ROI estimate from data."""
        return ROIEstimate(
            investment_hours=roi_data['investment_hours'],
            estimated_benefit_value=roi_data['benefit_value'],
            roi_percentage=roi_data['roi_percentage'],
            payback_period_days=roi_data['payback_days'],
            confidence_level=roi_data['confidence'],
            value_realization_timeline=roi_data['timeline']
        )
    
    def _calculate_investment_hours(self, commits: List[CommitInfo]) -> float:
        """Calculate total investment hours."""
        total_changes = sum(c.insertions + c.deletions for c in commits)
        estimated_hours = total_changes * 0.1
        
        return max(estimated_hours, len(commits) * 0.5)
    
    def _estimate_benefit_value(self, commits: List[CommitInfo]) -> float:
        """Estimate total benefit value."""
        benefit_values = self._get_benefit_type_values()
        return sum(self._calculate_commit_benefit(commit, benefit_values) for commit in commits)
    
    def _get_benefit_type_values(self) -> dict:
        """Get benefit values for different commit types."""
        return {
            CommitType.FEATURE: 5000,
            CommitType.FIX: 2000,
            CommitType.PERF: 3000
        }
    
    def _calculate_commit_benefit(self, commit: CommitInfo, benefit_values: dict) -> float:
        """Calculate benefit value for a single commit."""
        return benefit_values.get(commit.commit_type, 0.0)
    
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
        from netra_backend.app.services.factory_status.business_core import BusinessConstants
        
        customer_facing = sum(1 for c in commits if self._is_customer_facing_commit(c))
        total_commits = len(commits)
        
        if customer_facing / max(total_commits, 1) > 0.5:
            return "Immediate (1-2 weeks)"
        elif customer_facing > 0:
            return "Short-term (1-2 months)"
        return "Long-term (3-6 months)"
    
    def _is_customer_facing_commit(self, commit: CommitInfo) -> bool:
        """Check if commit affects customer-facing components."""
        from netra_backend.app.services.factory_status.business_core import BusinessConstants
        return any(pattern in commit.message.lower() for pattern in BusinessConstants.CUSTOMER_FACING_PATTERNS)


class BusinessValueCalculator:
    """Main calculator orchestrating all business value metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize business value calculator."""
        self.repo_path = repo_path
    
    def calculate_business_value_metrics(self, hours: int = 168) -> BusinessValueMetrics:
        """Calculate comprehensive business value metrics."""
        calculators = self._initialize_value_calculators()
        metrics_data = self._calculate_all_metrics(calculators, hours)
        return self._build_business_value_metrics(metrics_data)
    
    def _initialize_value_calculators(self) -> dict:
        """Initialize all value calculation components."""
        from .value_calculator import (
            ComplianceSecurityCalculator,
            CustomerImpactCalculator,
            ObjectiveMapper,
            RevenueCalculator,
        )
        return {
            'objective_mapper': ObjectiveMapper(self.repo_path),
            'customer_calc': CustomerImpactCalculator(self.repo_path),
            'revenue_calc': RevenueCalculator(self.repo_path),
            'compliance_calc': ComplianceSecurityCalculator(self.repo_path),
            'innovation_calc': InnovationCalculator(self.repo_path),
            'roi_calc': ROICalculator(self.repo_path)
        }
    
    def _calculate_all_metrics(self, calculators: dict, hours: int) -> dict:
        """Calculate all business metrics using calculators."""
        return {
            'objective_mapping': calculators['objective_mapper'].map_commits(hours),
            'customer_impact': calculators['customer_calc'].calculate(hours),
            'revenue_metrics': calculators['revenue_calc'].calculate(hours),
            'compliance_security': calculators['compliance_calc'].calculate(hours),
            'innovation_metrics': calculators['innovation_calc'].calculate(hours),
            'roi_estimate': calculators['roi_calc'].estimate(hours)
        }
    
    def _build_business_value_metrics(self, metrics_data: dict) -> BusinessValueMetrics:
        """Build final BusinessValueMetrics object."""
        overall_value = self._calculate_overall_business_value(
            metrics_data['customer_impact'], metrics_data['revenue_metrics'], 
            metrics_data['compliance_security'], metrics_data['innovation_metrics']
        )
        return BusinessValueMetrics(
            objective_mapping=metrics_data['objective_mapping'],
            customer_impact=metrics_data['customer_impact'],
            revenue_metrics=metrics_data['revenue_metrics'],
            compliance_security=metrics_data['compliance_security'],
            roi_estimate=metrics_data['roi_estimate'],
            innovation_metrics=metrics_data['innovation_metrics'],
            overall_business_value=overall_value
        )
    
    def _calculate_overall_business_value(self, customer: CustomerImpactMetrics,
                                         revenue: RevenueMetrics,
                                         security: ComplianceSecurityMetrics,
                                         innovation: InnovationMetrics) -> float:
        """Calculate overall business value score."""
        component_scores = self._extract_component_scores(customer, revenue, security, innovation)
        return self._apply_business_value_weights(component_scores)
    
    def _extract_component_scores(self, customer: CustomerImpactMetrics, revenue: RevenueMetrics,
                                 security: ComplianceSecurityMetrics, innovation: InnovationMetrics) -> list:
        """Extract component scores for business value calculation."""
        return [
            customer.customer_satisfaction_score,
            min(revenue.estimated_revenue_impact / 10000, 10),
            security.regulatory_compliance_score,
            innovation.technical_advancement_score
        ]
    
    def _apply_business_value_weights(self, scores: list) -> float:
        """Apply weights to business value component scores."""
        weights = [0.3, 0.25, 0.25, 0.2]
        return sum(w * s for w, s in zip(weights, scores))