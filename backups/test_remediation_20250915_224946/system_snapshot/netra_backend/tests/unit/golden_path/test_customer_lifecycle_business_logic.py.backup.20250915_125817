"""
Test Customer Lifecycle Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Customer journey optimization
- Business Goal: Maximize customer lifetime value and prevent churn
- Value Impact: Customer lifecycle management directly impacts $500K+ ARR growth
- Strategic Impact: Customer retention is 5x more cost-effective than acquisition

This test validates core customer lifecycle algorithms that power:
1. Onboarding flow optimization and conversion funnels
2. Churn prediction and prevention algorithms
3. Upsell trigger detection and timing optimization
4. Customer health scoring and intervention points
5. Retention campaign effectiveness measurement

CRITICAL BUSINESS RULES:
- Free tier: Convert within 14 days or 50% churn probability
- Early tier: Upsell evaluation at 3 months, 80% usage threshold
- Mid tier: Enterprise evaluation at 6 months, 85% usage threshold
- Enterprise tier: Expansion opportunities at 12 months
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

from shared.types.core_types import UserID
from shared.isolated_environment import get_env

# Business Logic Classes (SSOT for customer lifecycle)

class SubscriptionTier(Enum):
    FREE = "free"
    EARLY = "early"
    MID = "mid" 
    ENTERPRISE = "enterprise"

class CustomerStatus(Enum):
    ACTIVE = "active"
    AT_RISK = "at_risk"
    CHURNED = "churned"
    ONBOARDING = "onboarding"
    CONVERTED = "converted"

class InterventionType(Enum):
    ONBOARDING_EMAIL = "onboarding_email"
    USAGE_TUTORIAL = "usage_tutorial"
    UPGRADE_OFFER = "upgrade_offer"
    RETENTION_DISCOUNT = "retention_discount"
    SUCCESS_MANAGER_OUTREACH = "success_manager_outreach"

@dataclass
class CustomerProfile:
    """Complete customer profile for lifecycle analysis."""
    user_id: str
    email: str
    signup_date: datetime
    current_tier: SubscriptionTier
    last_login: Optional[datetime]
    total_executions: int
    successful_executions: int
    monthly_usage_trend: List[int]  # Last 6 months
    support_tickets: int
    nps_score: Optional[int]  # Net Promoter Score 0-10
    
@dataclass
class UsagePattern:
    """Usage pattern analysis for lifecycle decisions."""
    daily_active_days: int
    peak_usage_hour: int
    preferred_agent_types: List[str]
    session_duration_avg: float
    feature_adoption_score: float  # 0.0 to 1.0

@dataclass  
class ChurnPrediction:
    """Churn prediction analysis result."""
    churn_probability: float  # 0.0 to 1.0
    risk_factors: List[str]
    days_to_predicted_churn: Optional[int]
    confidence_score: float
    recommended_interventions: List[InterventionType]

@dataclass
class UpsellOpportunity:
    """Upsell opportunity analysis."""
    recommended_tier: SubscriptionTier
    confidence_score: float
    monthly_savings_potential: Decimal
    usage_based_justification: str
    optimal_outreach_timing: datetime

class CustomerLifecycleManager:
    """
    SSOT Customer Lifecycle Management Business Logic
    
    This class implements customer journey optimization that directly
    impacts revenue growth and retention.
    """
    
    # CRITICAL BUSINESS RULES
    FREE_TIER_CONVERSION_WINDOW_DAYS = 14
    EARLY_TIER_UPSELL_EVALUATION_MONTHS = 3
    MID_TIER_ENTERPRISE_EVALUATION_MONTHS = 6
    ENTERPRISE_EXPANSION_EVALUATION_MONTHS = 12
    
    CHURN_RISK_THRESHOLDS = {
        'no_login_days': 7,
        'low_usage_threshold': 0.2,  # 20% of tier limit
        'support_ticket_threshold': 5,
        'low_nps_threshold': 6
    }
    
    TIER_USAGE_THRESHOLDS = {
        SubscriptionTier.FREE: {'capacity_threshold': 0.8, 'included_executions': 10},
        SubscriptionTier.EARLY: {'capacity_threshold': 0.8, 'included_executions': 200},
        SubscriptionTier.MID: {'capacity_threshold': 0.85, 'included_executions': 1000},
        SubscriptionTier.ENTERPRISE: {'capacity_threshold': 0.85, 'included_executions': 10000}
    }

    def analyze_customer_health(self, profile: CustomerProfile, usage_pattern: UsagePattern) -> Dict[str, any]:
        """
        Comprehensive customer health analysis.
        
        Returns health score and actionable insights for customer success.
        """
        health_factors = {
            'login_recency': self._score_login_recency(profile.last_login),
            'usage_consistency': self._score_usage_consistency(profile.monthly_usage_trend),
            'success_rate': self._score_execution_success(profile.total_executions, profile.successful_executions),
            'engagement_depth': self._score_engagement_depth(usage_pattern),
            'satisfaction': self._score_satisfaction(profile.nps_score, profile.support_tickets)
        }
        
        # Weighted health score calculation (0.0 to 1.0)
        weights = {'login_recency': 0.25, 'usage_consistency': 0.3, 'success_rate': 0.2, 
                  'engagement_depth': 0.15, 'satisfaction': 0.1}
        
        overall_health_score = sum(health_factors[factor] * weights[factor] for factor in health_factors)
        
        # Determine customer status
        if overall_health_score >= 0.8:
            status = CustomerStatus.ACTIVE
        elif overall_health_score >= 0.6:
            status = CustomerStatus.AT_RISK
        else:
            status = CustomerStatus.CHURNED
            
        return {
            'health_score': overall_health_score,
            'status': status,
            'factor_scores': health_factors,
            'primary_risk_factors': [factor for factor, score in health_factors.items() if score < 0.5]
        }

    def predict_churn_risk(self, profile: CustomerProfile, usage_pattern: UsagePattern) -> ChurnPrediction:
        """
        Advanced churn prediction algorithm.
        
        Critical for proactive customer retention.
        """
        risk_factors = []
        risk_score = 0.0
        
        # Login recency risk
        if profile.last_login is None or (datetime.now(timezone.utc) - profile.last_login).days > self.CHURN_RISK_THRESHOLDS['no_login_days']:
            risk_factors.append('inactive_login_pattern')
            risk_score += 0.3
            
        # Usage decline risk
        if len(profile.monthly_usage_trend) >= 2:
            recent_usage = sum(profile.monthly_usage_trend[-2:]) / 2
            tier_threshold = self.TIER_USAGE_THRESHOLDS[profile.current_tier]['included_executions']
            if recent_usage < (tier_threshold * self.CHURN_RISK_THRESHOLDS['low_usage_threshold']):
                risk_factors.append('declining_usage_pattern')
                risk_score += 0.25
                
        # Support issues risk
        if profile.support_tickets > self.CHURN_RISK_THRESHOLDS['support_ticket_threshold']:
            risk_factors.append('high_support_burden')
            risk_score += 0.2
            
        # Satisfaction risk
        if profile.nps_score is not None and profile.nps_score <= self.CHURN_RISK_THRESHOLDS['low_nps_threshold']:
            risk_factors.append('low_satisfaction_score')
            risk_score += 0.15
            
        # Feature adoption risk
        if usage_pattern.feature_adoption_score < 0.3:
            risk_factors.append('poor_feature_adoption')
            risk_score += 0.1
            
        # Calculate days to predicted churn
        days_to_churn = None
        if risk_score > 0.5:
            # Higher risk = faster predicted churn
            days_to_churn = max(7, int(60 * (1 - risk_score)))
            
        # Recommend interventions based on risk factors
        interventions = self._recommend_interventions(risk_factors, profile.current_tier)
        
        return ChurnPrediction(
            churn_probability=min(1.0, risk_score),
            risk_factors=risk_factors,
            days_to_predicted_churn=days_to_churn,
            confidence_score=min(1.0, len(risk_factors) * 0.2),
            recommended_interventions=interventions
        )

    def identify_upsell_opportunities(self, profile: CustomerProfile, usage_pattern: UsagePattern) -> Optional[UpsellOpportunity]:
        """
        Identify optimal upsell opportunities with timing.
        
        Critical for revenue expansion.
        """
        current_tier = profile.current_tier
        
        # Don't upsell Enterprise (highest tier)
        if current_tier == SubscriptionTier.ENTERPRISE:
            return None
            
        tier_config = self.TIER_USAGE_THRESHOLDS[current_tier]
        usage_ratio = profile.total_executions / max(1, tier_config['included_executions'])
        
        # Check if customer is hitting capacity limits
        if usage_ratio < tier_config['capacity_threshold']:
            return None
            
        # Check timing constraints
        account_age_months = (datetime.now(timezone.utc) - profile.signup_date).days / 30
        
        timing_requirements = {
            SubscriptionTier.FREE: 0.5,  # 2 weeks
            SubscriptionTier.EARLY: self.EARLY_TIER_UPSELL_EVALUATION_MONTHS,
            SubscriptionTier.MID: self.MID_TIER_ENTERPRISE_EVALUATION_MONTHS
        }
        
        if account_age_months < timing_requirements.get(current_tier, 0):
            return None
            
        # Determine recommended tier
        if current_tier == SubscriptionTier.FREE:
            recommended_tier = SubscriptionTier.EARLY
        elif current_tier == SubscriptionTier.EARLY:
            recommended_tier = SubscriptionTier.MID
        elif current_tier == SubscriptionTier.MID:
            recommended_tier = SubscriptionTier.ENTERPRISE
        else:
            return None
            
        # Calculate potential savings (simplified)
        monthly_savings = self._calculate_tier_upgrade_savings(profile, recommended_tier)
        
        # Build justification
        justification = f"Usage at {usage_ratio:.0%} of {current_tier.value} tier capacity"
        if monthly_savings > 0:
            justification += f", potential monthly savings: ${monthly_savings}"
            
        # Optimal timing (prefer beginning of month for cleaner billing)
        next_month = datetime.now(timezone.utc).replace(day=1) + timedelta(days=32)
        optimal_timing = next_month.replace(day=1)
        
        return UpsellOpportunity(
            recommended_tier=recommended_tier,
            confidence_score=min(1.0, usage_ratio),
            monthly_savings_potential=monthly_savings,
            usage_based_justification=justification,
            optimal_outreach_timing=optimal_timing
        )

    def calculate_customer_lifetime_value(self, profile: CustomerProfile) -> Dict[str, Decimal]:
        """
        Calculate customer lifetime value for business planning.
        
        Critical for marketing spend optimization.
        """
        # Base monthly revenue by tier
        tier_monthly_revenue = {
            SubscriptionTier.FREE: Decimal('0.00'),
            SubscriptionTier.EARLY: Decimal('49.00'),
            SubscriptionTier.MID: Decimal('199.00'),
            SubscriptionTier.ENTERPRISE: Decimal('999.00')
        }
        
        current_monthly_revenue = tier_monthly_revenue[profile.current_tier]
        
        # Calculate historical overage revenue (simplified)
        avg_monthly_usage = sum(profile.monthly_usage_trend) / max(1, len(profile.monthly_usage_trend))
        tier_included = self.TIER_USAGE_THRESHOLDS[profile.current_tier]['included_executions']
        
        overage_rates = {
            SubscriptionTier.FREE: Decimal('0.00'),
            SubscriptionTier.EARLY: Decimal('0.10'),
            SubscriptionTier.MID: Decimal('0.05'),
            SubscriptionTier.ENTERPRISE: Decimal('0.02')
        }
        
        monthly_overage = max(0, avg_monthly_usage - tier_included) * overage_rates[profile.current_tier]
        total_monthly_revenue = current_monthly_revenue + monthly_overage
        
        # Predict customer lifespan based on health and tier
        health_analysis = self.analyze_customer_health(profile, UsagePattern(
            daily_active_days=20,
            peak_usage_hour=14,
            preferred_agent_types=['cost_optimizer'],
            session_duration_avg=30.0,
            feature_adoption_score=0.7
        ))
        
        # Tier-based lifespan assumptions (in months)
        base_lifespan = {
            SubscriptionTier.FREE: 2,
            SubscriptionTier.EARLY: 12,
            SubscriptionTier.MID: 24,
            SubscriptionTier.ENTERPRISE: 36
        }
        
        health_multiplier = 0.5 + (health_analysis['health_score'] * 1.5)
        predicted_lifespan_months = base_lifespan[profile.current_tier] * health_multiplier
        
        ltv = total_monthly_revenue * Decimal(str(predicted_lifespan_months))
        
        return {
            'monthly_revenue': total_monthly_revenue,
            'predicted_lifespan_months': Decimal(str(predicted_lifespan_months)),
            'lifetime_value': ltv,
            'health_multiplier': Decimal(str(health_multiplier))
        }

    # PRIVATE HELPER METHODS

    def _score_login_recency(self, last_login: Optional[datetime]) -> float:
        """Score login recency (0.0 to 1.0)."""
        if last_login is None:
            return 0.0
            
        days_since_login = (datetime.now(timezone.utc) - last_login).days
        
        if days_since_login == 0:
            return 1.0
        elif days_since_login <= 3:
            return 0.8
        elif days_since_login <= 7:
            return 0.6
        elif days_since_login <= 14:
            return 0.4
        elif days_since_login <= 30:
            return 0.2
        else:
            return 0.0

    def _score_usage_consistency(self, monthly_trend: List[int]) -> float:
        """Score usage consistency over time (0.0 to 1.0)."""
        if len(monthly_trend) < 2:
            return 0.5  # Neutral score for insufficient data
            
        # Calculate coefficient of variation (lower = more consistent)
        avg_usage = sum(monthly_trend) / len(monthly_trend)
        if avg_usage == 0:
            return 0.0
            
        variance = sum((x - avg_usage) ** 2 for x in monthly_trend) / len(monthly_trend)
        std_dev = variance ** 0.5
        coefficient_of_variation = std_dev / avg_usage
        
        # Convert to 0-1 score (lower CV = higher score)
        consistency_score = max(0.0, 1.0 - coefficient_of_variation)
        return min(1.0, consistency_score)

    def _score_execution_success(self, total: int, successful: int) -> float:
        """Score execution success rate (0.0 to 1.0)."""
        if total == 0:
            return 0.5  # Neutral for no usage
            
        success_rate = successful / total
        return success_rate

    def _score_engagement_depth(self, usage_pattern: UsagePattern) -> float:
        """Score engagement depth based on usage patterns (0.0 to 1.0)."""
        factors = [
            min(1.0, usage_pattern.daily_active_days / 20),  # Up to 20 days/month is excellent
            usage_pattern.feature_adoption_score,
            min(1.0, usage_pattern.session_duration_avg / 60),  # Up to 60 min sessions
            min(1.0, len(usage_pattern.preferred_agent_types) / 3)  # Using multiple agent types
        ]
        
        return sum(factors) / len(factors)

    def _score_satisfaction(self, nps_score: Optional[int], support_tickets: int) -> float:
        """Score customer satisfaction (0.0 to 1.0)."""
        if nps_score is None:
            nps_component = 0.5  # Neutral for missing data
        else:
            nps_component = nps_score / 10  # Convert 0-10 to 0-1
            
        # Penalize high support ticket volume
        support_penalty = min(0.5, support_tickets * 0.05)  # Up to 50% penalty
        support_component = max(0.0, 1.0 - support_penalty)
        
        return (nps_component + support_component) / 2

    def _recommend_interventions(self, risk_factors: List[str], tier: SubscriptionTier) -> List[InterventionType]:
        """Recommend interventions based on risk factors."""
        interventions = []
        
        if 'inactive_login_pattern' in risk_factors:
            interventions.append(InterventionType.ONBOARDING_EMAIL)
            
        if 'declining_usage_pattern' in risk_factors:
            interventions.append(InterventionType.USAGE_TUTORIAL)
            
        if 'poor_feature_adoption' in risk_factors:
            interventions.append(InterventionType.USAGE_TUTORIAL)
            
        if 'high_support_burden' in risk_factors or 'low_satisfaction_score' in risk_factors:
            if tier in [SubscriptionTier.MID, SubscriptionTier.ENTERPRISE]:
                interventions.append(InterventionType.SUCCESS_MANAGER_OUTREACH)
            else:
                interventions.append(InterventionType.RETENTION_DISCOUNT)
                
        return interventions

    def _calculate_tier_upgrade_savings(self, profile: CustomerProfile, target_tier: SubscriptionTier) -> Decimal:
        """Calculate potential monthly savings from tier upgrade."""
        # Simplified calculation - would be more complex in real implementation
        current_usage = sum(profile.monthly_usage_trend) / max(1, len(profile.monthly_usage_trend))
        
        # Current tier costs (base + overage)
        current_tier_config = self.TIER_USAGE_THRESHOLDS[profile.current_tier]
        target_tier_config = self.TIER_USAGE_THRESHOLDS[target_tier]
        
        # Simple savings calculation based on overage reduction
        if current_usage > current_tier_config['included_executions']:
            potential_overage_reduction = min(
                current_usage - current_tier_config['included_executions'],
                target_tier_config['included_executions'] - current_tier_config['included_executions']
            )
            
            overage_rates = {
                SubscriptionTier.FREE: Decimal('0.00'),
                SubscriptionTier.EARLY: Decimal('0.10'),
                SubscriptionTier.MID: Decimal('0.05'),
                SubscriptionTier.ENTERPRISE: Decimal('0.02')
            }
            
            current_overage_rate = overage_rates[profile.current_tier]
            target_overage_rate = overage_rates[target_tier]
            
            return potential_overage_reduction * (current_overage_rate - target_overage_rate)
            
        return Decimal('0.00')


@pytest.mark.golden_path
@pytest.mark.unit
class TestCustomerLifecycleBusinessLogic:
    """Test customer lifecycle business logic that drives revenue growth."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.manager = CustomerLifecycleManager()
        self.base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        
    def _create_test_profile(self, tier: SubscriptionTier = SubscriptionTier.EARLY, 
                           days_since_signup: int = 30, 
                           monthly_usage: List[int] = None) -> CustomerProfile:
        """Helper to create test customer profiles."""
        if monthly_usage is None:
            monthly_usage = [50, 75, 100, 120, 90, 80]
            
        return CustomerProfile(
            user_id=str(uuid.uuid4()),
            email="test@example.com",
            signup_date=self.base_date - timedelta(days=days_since_signup),
            current_tier=tier,
            last_login=self.base_date - timedelta(days=2),
            total_executions=sum(monthly_usage),
            successful_executions=int(sum(monthly_usage) * 0.9),  # 90% success rate
            monthly_usage_trend=monthly_usage,
            support_tickets=1,
            nps_score=8
        )
        
    def _create_test_usage_pattern(self) -> UsagePattern:
        """Helper to create test usage patterns."""
        return UsagePattern(
            daily_active_days=15,
            peak_usage_hour=14,
            preferred_agent_types=['cost_optimizer', 'data_helper'],
            session_duration_avg=30.0,
            feature_adoption_score=0.7
        )

    # CUSTOMER HEALTH ANALYSIS TESTS

    def test_healthy_customer_analysis(self):
        """Test customer health analysis for healthy customer."""
        profile = self._create_test_profile(
            tier=SubscriptionTier.EARLY,
            monthly_usage=[40, 45, 50, 55, 60, 65]  # Growing usage
        )
        profile.last_login = self.base_date - timedelta(days=1)  # Recent login
        profile.nps_score = 9  # High satisfaction
        
        usage_pattern = self._create_test_usage_pattern()
        usage_pattern.feature_adoption_score = 0.85  # High adoption
        
        result = self.manager.analyze_customer_health(profile, usage_pattern)
        
        assert result['health_score'] >= 0.8
        assert result['status'] == CustomerStatus.ACTIVE
        assert len(result['primary_risk_factors']) == 0

    def test_at_risk_customer_analysis(self):
        """Test customer health analysis for at-risk customer."""
        profile = self._create_test_profile(
            tier=SubscriptionTier.EARLY,
            monthly_usage=[100, 80, 60, 40, 20, 10]  # Declining usage
        )
        profile.last_login = self.base_date - timedelta(days=5)  # Less recent login
        profile.support_tickets = 3
        profile.nps_score = 6
        
        usage_pattern = self._create_test_usage_pattern()
        usage_pattern.feature_adoption_score = 0.4  # Lower adoption
        
        result = self.manager.analyze_customer_health(profile, usage_pattern)
        
        assert 0.4 <= result['health_score'] <= 0.8
        assert result['status'] == CustomerStatus.AT_RISK
        assert len(result['primary_risk_factors']) > 0

    def test_churned_customer_analysis(self):
        """Test customer health analysis for churned customer."""
        profile = self._create_test_profile(
            tier=SubscriptionTier.FREE,
            monthly_usage=[5, 3, 1, 0, 0, 0]  # No recent usage
        )
        profile.last_login = self.base_date - timedelta(days=15)  # Very old login
        profile.support_tickets = 8
        profile.nps_score = 3
        
        usage_pattern = self._create_test_usage_pattern()
        usage_pattern.feature_adoption_score = 0.1  # Very low adoption
        usage_pattern.daily_active_days = 2
        
        result = self.manager.analyze_customer_health(profile, usage_pattern)
        
        assert result['health_score'] < 0.6
        assert result['status'] == CustomerStatus.CHURNED
        assert len(result['primary_risk_factors']) >= 3

    # CHURN PREDICTION TESTS

    def test_low_churn_risk_prediction(self):
        """Test churn prediction for low-risk customer."""
        profile = self._create_test_profile(
            tier=SubscriptionTier.MID,
            monthly_usage=[800, 850, 900, 950, 1000, 1100]  # Growing usage
        )
        profile.last_login = self.base_date - timedelta(hours=12)
        profile.support_tickets = 0
        profile.nps_score = 9
        
        usage_pattern = self._create_test_usage_pattern()
        usage_pattern.feature_adoption_score = 0.9
        
        result = self.manager.predict_churn_risk(profile, usage_pattern)
        
        assert result.churn_probability < 0.3
        assert len(result.risk_factors) <= 1
        assert result.days_to_predicted_churn is None
        assert len(result.recommended_interventions) <= 1

    def test_high_churn_risk_prediction(self):
        """Test churn prediction for high-risk customer."""
        profile = self._create_test_profile(
            tier=SubscriptionTier.EARLY,
            monthly_usage=[150, 100, 50, 20, 5, 0]  # Declining usage
        )
        profile.last_login = self.base_date - timedelta(days=10)  # Inactive
        profile.support_tickets = 6
        profile.nps_score = 4
        
        usage_pattern = self._create_test_usage_pattern()
        usage_pattern.feature_adoption_score = 0.2
        usage_pattern.daily_active_days = 3
        
        result = self.manager.predict_churn_risk(profile, usage_pattern)
        
        assert result.churn_probability > 0.7
        assert len(result.risk_factors) >= 3
        assert result.days_to_predicted_churn is not None
        assert result.days_to_predicted_churn <= 30
        assert len(result.recommended_interventions) >= 2

    def test_churn_risk_intervention_recommendations(self):
        """Test that churn risk analysis recommends appropriate interventions."""
        profile = self._create_test_profile(tier=SubscriptionTier.ENTERPRISE)
        profile.last_login = self.base_date - timedelta(days=8)  # Trigger inactive risk
        profile.support_tickets = 7  # Trigger high support risk
        profile.nps_score = 5  # Trigger low satisfaction risk
        
        usage_pattern = self._create_test_usage_pattern()
        usage_pattern.feature_adoption_score = 0.25  # Trigger poor adoption risk
        
        result = self.manager.predict_churn_risk(profile, usage_pattern)
        
        # Enterprise customers should get success manager outreach
        assert InterventionType.SUCCESS_MANAGER_OUTREACH in result.recommended_interventions
        assert InterventionType.ONBOARDING_EMAIL in result.recommended_interventions
        assert InterventionType.USAGE_TUTORIAL in result.recommended_interventions

    # UPSELL OPPORTUNITY TESTS

    def test_free_tier_upsell_opportunity(self):
        """Test upsell opportunity identification for Free tier heavy users."""
        profile = self._create_test_profile(
            tier=SubscriptionTier.FREE,
            days_since_signup=20,  # Past conversion window
            monthly_usage=[8, 9, 10, 12, 15, 18]  # Growing, hitting limits
        )
        
        usage_pattern = self._create_test_usage_pattern()
        
        result = self.manager.identify_upsell_opportunities(profile, usage_pattern)
        
        assert result is not None
        assert result.recommended_tier == SubscriptionTier.EARLY
        assert result.confidence_score > 0.8  # High usage ratio
        assert "Usage at" in result.usage_based_justification

    def test_early_tier_upsell_opportunity(self):
        """Test upsell opportunity for Early tier approaching limits."""
        profile = self._create_test_profile(
            tier=SubscriptionTier.EARLY,
            days_since_signup=100,  # Past 3 month evaluation period
            monthly_usage=[160, 170, 180, 190, 200, 220]  # Approaching/exceeding limits
        )
        
        usage_pattern = self._create_test_usage_pattern()
        
        result = self.manager.identify_upsell_opportunities(profile, usage_pattern)
        
        assert result is not None
        assert result.recommended_tier == SubscriptionTier.MID
        assert result.confidence_score > 0.8

    def test_no_upsell_for_enterprise(self):
        """Test that Enterprise customers don't get upsell recommendations."""
        profile = self._create_test_profile(
            tier=SubscriptionTier.ENTERPRISE,
            monthly_usage=[8000, 8500, 9000, 9500, 10000, 12000]  # High usage
        )
        
        usage_pattern = self._create_test_usage_pattern()
        
        result = self.manager.identify_upsell_opportunities(profile, usage_pattern)
        
        assert result is None

    def test_no_premature_upsell(self):
        """Test that customers aren't upsold before timing requirements."""
        profile = self._create_test_profile(
            tier=SubscriptionTier.EARLY,
            days_since_signup=30,  # Less than 3 months
            monthly_usage=[180, 190, 200, 210, 220, 240]  # High usage but too early
        )
        
        usage_pattern = self._create_test_usage_pattern()
        
        result = self.manager.identify_upsell_opportunities(profile, usage_pattern)
        
        assert result is None

    # CUSTOMER LIFETIME VALUE TESTS

    def test_free_tier_lifetime_value_calculation(self):
        """Test LTV calculation for Free tier customers."""
        profile = self._create_test_profile(
            tier=SubscriptionTier.FREE,
            monthly_usage=[5, 6, 7, 8, 8, 7]  # Modest usage
        )
        profile.nps_score = 8  # Good satisfaction
        
        result = self.manager.calculate_customer_lifetime_value(profile)
        
        assert result['monthly_revenue'] == Decimal('0.00')  # Free tier
        assert result['predicted_lifespan_months'] > 0
        assert result['lifetime_value'] == Decimal('0.00')  # No revenue from free
        assert result['health_multiplier'] > 1.0  # Good health extends lifespan

    def test_early_tier_lifetime_value_calculation(self):
        """Test LTV calculation for Early tier customers."""
        profile = self._create_test_profile(
            tier=SubscriptionTier.EARLY,
            monthly_usage=[180, 190, 200, 210, 220, 230]  # Some overage
        )
        profile.nps_score = 8
        
        result = self.manager.calculate_customer_lifetime_value(profile)
        
        assert result['monthly_revenue'] > Decimal('49.00')  # Base + overage
        assert result['predicted_lifespan_months'] > 12  # Healthy customer extends base
        assert result['lifetime_value'] > Decimal('500.00')  # Meaningful LTV

    def test_enterprise_tier_lifetime_value_calculation(self):
        """Test LTV calculation for Enterprise tier customers."""
        profile = self._create_test_profile(
            tier=SubscriptionTier.ENTERPRISE,
            monthly_usage=[9000, 9500, 10000, 10500, 11000, 11500]  # Some overage
        )
        profile.nps_score = 9
        
        result = self.manager.calculate_customer_lifetime_value(profile)
        
        assert result['monthly_revenue'] > Decimal('999.00')  # Base + overage
        assert result['predicted_lifespan_months'] > 36  # Long enterprise relationships
        assert result['lifetime_value'] > Decimal('30000.00')  # High enterprise LTV

    def test_unhealthy_customer_reduced_ltv(self):
        """Test that unhealthy customers have reduced LTV predictions."""
        healthy_profile = self._create_test_profile(tier=SubscriptionTier.MID)
        healthy_profile.nps_score = 9
        healthy_profile.support_tickets = 0
        
        unhealthy_profile = self._create_test_profile(
            tier=SubscriptionTier.MID,
            monthly_usage=[800, 600, 400, 200, 100, 50]  # Declining
        )
        unhealthy_profile.nps_score = 4
        unhealthy_profile.support_tickets = 8
        unhealthy_profile.last_login = self.base_date - timedelta(days=10)
        
        healthy_ltv = self.manager.calculate_customer_lifetime_value(healthy_profile)
        unhealthy_ltv = self.manager.calculate_customer_lifetime_value(unhealthy_profile)
        
        assert unhealthy_ltv['lifetime_value'] < healthy_ltv['lifetime_value']
        assert unhealthy_ltv['health_multiplier'] < healthy_ltv['health_multiplier']

    # EDGE CASE AND VALIDATION TESTS

    def test_customer_with_no_usage_history(self):
        """Test handling of customers with no usage history."""
        profile = self._create_test_profile(monthly_usage=[])
        profile.total_executions = 0
        profile.successful_executions = 0
        
        usage_pattern = self._create_test_usage_pattern()
        
        health_result = self.manager.analyze_customer_health(profile, usage_pattern)
        churn_result = self.manager.predict_churn_risk(profile, usage_pattern)
        upsell_result = self.manager.identify_upsell_opportunities(profile, usage_pattern)
        ltv_result = self.manager.calculate_customer_lifetime_value(profile)
        
        # Should handle gracefully without crashing
        assert 'health_score' in health_result
        assert 'churn_probability' in churn_result.__dict__
        assert upsell_result is None  # No usage = no upsell
        assert 'lifetime_value' in ltv_result

    def test_customer_lifecycle_business_constants(self):
        """Test that business constants are properly defined."""
        assert self.manager.FREE_TIER_CONVERSION_WINDOW_DAYS == 14
        assert self.manager.EARLY_TIER_UPSELL_EVALUATION_MONTHS == 3
        assert self.manager.MID_TIER_ENTERPRISE_EVALUATION_MONTHS == 6
        assert self.manager.ENTERPRISE_EXPANSION_EVALUATION_MONTHS == 12
        
        # Verify tier thresholds exist for all tiers
        for tier in SubscriptionTier:
            assert tier in self.manager.TIER_USAGE_THRESHOLDS
            assert 'capacity_threshold' in self.manager.TIER_USAGE_THRESHOLDS[tier]
            assert 'included_executions' in self.manager.TIER_USAGE_THRESHOLDS[tier]