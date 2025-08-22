"""Core types and interfaces for business value metrics.

Defines enums, dataclasses and interfaces for business value assessment.
Module follows 450-line limit with 25-line function limit.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


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


class BusinessConstants:
    """Constants for business value calculations."""
    
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