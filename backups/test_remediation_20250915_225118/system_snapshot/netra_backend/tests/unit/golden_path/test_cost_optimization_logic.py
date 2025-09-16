"""
Test Cost Optimization Business Value Logic

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise (core revenue generating tiers)
- Business Goal: Validate cost analysis calculations that drive $500K+ ARR
- Value Impact: Ensures accuracy of cost savings recommendations that justify platform value
- Strategic Impact: Core algorithm validation for AI-driven cost optimization - our primary value proposition

CRITICAL: This test validates the business logic calculations that determine cost optimization 
recommendations. These calculations directly impact customer ROI and platform justification.

This test focuses on BUSINESS LOGIC validation, not system integration.
Tests the algorithms and calculations that deliver quantifiable business value to customers.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from decimal import Decimal
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.core_types import UserID

class CostCategory(Enum):
    """Cost categories for optimization analysis."""
    COMPUTE = 'compute'
    STORAGE = 'storage'
    NETWORK = 'network'
    DATABASE = 'database'
    MONITORING = 'monitoring'
    SECURITY = 'security'

class OptimizationStrategy(Enum):
    """Types of cost optimization strategies."""
    RIGHTSIZING = 'rightsizing'
    RESERVED_INSTANCES = 'reserved_instances'
    SPOT_INSTANCES = 'spot_instances'
    STORAGE_OPTIMIZATION = 'storage_optimization'
    AUTOMATION = 'automation'
    CONSOLIDATION = 'consolidation'

class ConfidenceLevel(Enum):
    """Confidence levels for cost optimization recommendations."""
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'

@dataclass
class CostData:
    """Cost data structure for optimization analysis."""
    category: CostCategory
    current_monthly_cost: Decimal
    resource_count: int
    utilization_percentage: float
    region: str
    service_name: str
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class OptimizationRecommendation:
    """Cost optimization recommendation with business value metrics."""
    strategy: OptimizationStrategy
    category: CostCategory
    current_cost: Decimal
    optimized_cost: Decimal
    monthly_savings: Decimal
    annual_savings: Decimal
    confidence_level: ConfidenceLevel
    implementation_effort: str
    business_justification: str
    roi_timeframe_months: int
    risk_assessment: str

class MockCostOptimizationAnalyzer:
    """Mock cost optimization analyzer for business logic testing."""

    def __init__(self):
        self.optimization_thresholds = {CostCategory.COMPUTE: {'underutilization_threshold': 0.3, 'overutilization_threshold': 0.8, 'minimum_monthly_cost': Decimal('100')}, CostCategory.STORAGE: {'underutilization_threshold': 0.5, 'overutilization_threshold': 0.9, 'minimum_monthly_cost': Decimal('50')}, CostCategory.DATABASE: {'underutilization_threshold': 0.4, 'overutilization_threshold': 0.85, 'minimum_monthly_cost': Decimal('200')}}
        self.savings_multipliers = {OptimizationStrategy.RIGHTSIZING: 0.25, OptimizationStrategy.RESERVED_INSTANCES: 0.35, OptimizationStrategy.SPOT_INSTANCES: 0.6, OptimizationStrategy.STORAGE_OPTIMIZATION: 0.3, OptimizationStrategy.AUTOMATION: 0.15, OptimizationStrategy.CONSOLIDATION: 0.4}
        self.business_value_thresholds = {'minimum_monthly_savings': Decimal('500'), 'high_value_monthly_savings': Decimal('5000'), 'enterprise_monthly_savings': Decimal('20000')}

    def analyze_cost_optimization_opportunities(self, cost_data_list: List[CostData]) -> Dict[str, Any]:
        """Business logic: Analyze cost data and identify optimization opportunities."""
        total_current_cost = sum((data.current_monthly_cost for data in cost_data_list))
        recommendations = []
        total_potential_savings = Decimal('0')
        for cost_data in cost_data_list:
            category_recommendations = self._analyze_category_optimization(cost_data)
            recommendations.extend(category_recommendations)
            for rec in category_recommendations:
                total_potential_savings += rec.monthly_savings
        annual_savings_potential = total_potential_savings * 12
        roi_percentage = annual_savings_potential / total_current_cost * 12 * 100 if total_current_cost > 0 else 0
        business_impact_tier = self._calculate_business_impact_tier(total_potential_savings)
        return {'total_current_monthly_cost': total_current_cost, 'total_potential_monthly_savings': total_potential_savings, 'total_potential_annual_savings': annual_savings_potential, 'roi_percentage': roi_percentage, 'recommendations': recommendations, 'business_impact_tier': business_impact_tier, 'recommendation_count': len(recommendations), 'high_confidence_recommendations': len([r for r in recommendations if r.confidence_level == ConfidenceLevel.HIGH]), 'justifies_platform_cost': total_potential_savings >= self.business_value_thresholds['minimum_monthly_savings']}

    def _analyze_category_optimization(self, cost_data: CostData) -> List[OptimizationRecommendation]:
        """Analyze optimization opportunities for a specific cost category."""
        recommendations = []
        if cost_data.category not in self.optimization_thresholds:
            return recommendations
        thresholds = self.optimization_thresholds[cost_data.category]
        if cost_data.current_monthly_cost < thresholds['minimum_monthly_cost']:
            return recommendations
        if cost_data.utilization_percentage < thresholds['underutilization_threshold']:
            rightsizing_rec = self._generate_rightsizing_recommendation(cost_data)
            if rightsizing_rec:
                recommendations.append(rightsizing_rec)
        if cost_data.category in [CostCategory.COMPUTE, CostCategory.DATABASE]:
            if cost_data.current_monthly_cost >= Decimal('1000'):
                reserved_rec = self._generate_reserved_instances_recommendation(cost_data)
                if reserved_rec:
                    recommendations.append(reserved_rec)
        if cost_data.category == CostCategory.STORAGE:
            storage_rec = self._generate_storage_optimization_recommendation(cost_data)
            if storage_rec:
                recommendations.append(storage_rec)
        if cost_data.resource_count > 5:
            consolidation_rec = self._generate_consolidation_recommendation(cost_data)
            if consolidation_rec:
                recommendations.append(consolidation_rec)
        return recommendations

    def _generate_rightsizing_recommendation(self, cost_data: CostData) -> Optional[OptimizationRecommendation]:
        """Generate rightsizing recommendation based on utilization."""
        utilization = cost_data.utilization_percentage
        if utilization < 0.1:
            savings_multiplier = 0.6
            confidence = ConfidenceLevel.HIGH
            effort = 'Low - automated'
        elif utilization < 0.2:
            savings_multiplier = 0.4
            confidence = ConfidenceLevel.HIGH
            effort = 'Low - automated'
        elif utilization < 0.3:
            savings_multiplier = 0.25
            confidence = ConfidenceLevel.MEDIUM
            effort = 'Low - review required'
        else:
            return None
        monthly_savings = cost_data.current_monthly_cost * Decimal(str(savings_multiplier))
        optimized_cost = cost_data.current_monthly_cost - monthly_savings
        return OptimizationRecommendation(strategy=OptimizationStrategy.RIGHTSIZING, category=cost_data.category, current_cost=cost_data.current_monthly_cost, optimized_cost=optimized_cost, monthly_savings=monthly_savings, annual_savings=monthly_savings * 12, confidence_level=confidence, implementation_effort=effort, business_justification=f'Resource utilization at {utilization:.0%} indicates significant overprovisioning', roi_timeframe_months=1, risk_assessment='Low risk - can be reversed easily')

    def _generate_reserved_instances_recommendation(self, cost_data: CostData) -> Optional[OptimizationRecommendation]:
        """Generate reserved instances recommendation for predictable workloads."""
        savings_multiplier = 0.35
        monthly_savings = cost_data.current_monthly_cost * Decimal(str(savings_multiplier))
        optimized_cost = cost_data.current_monthly_cost - monthly_savings
        return OptimizationRecommendation(strategy=OptimizationStrategy.RESERVED_INSTANCES, category=cost_data.category, current_cost=cost_data.current_monthly_cost, optimized_cost=optimized_cost, monthly_savings=monthly_savings, annual_savings=monthly_savings * 12, confidence_level=ConfidenceLevel.HIGH, implementation_effort='Medium - requires planning', business_justification='Predictable workload pattern suitable for reserved capacity', roi_timeframe_months=12, risk_assessment='Medium risk - requires capacity commitment')

    def _generate_storage_optimization_recommendation(self, cost_data: CostData) -> Optional[OptimizationRecommendation]:
        """Generate storage optimization recommendation."""
        savings_multiplier = 0.3
        monthly_savings = cost_data.current_monthly_cost * Decimal(str(savings_multiplier))
        optimized_cost = cost_data.current_monthly_cost - monthly_savings
        return OptimizationRecommendation(strategy=OptimizationStrategy.STORAGE_OPTIMIZATION, category=cost_data.category, current_cost=cost_data.current_monthly_cost, optimized_cost=optimized_cost, monthly_savings=monthly_savings, annual_savings=monthly_savings * 12, confidence_level=ConfidenceLevel.MEDIUM, implementation_effort='Medium - data migration required', business_justification='Storage usage patterns indicate opportunity for intelligent tiering', roi_timeframe_months=3, risk_assessment='Low risk - data integrity maintained')

    def _generate_consolidation_recommendation(self, cost_data: CostData) -> Optional[OptimizationRecommendation]:
        """Generate consolidation recommendation for multiple resources."""
        if cost_data.resource_count < 3:
            return None
        consolidation_factor = min(cost_data.resource_count / 2, 5)
        savings_multiplier = 0.2 + consolidation_factor * 0.05
        savings_multiplier = min(savings_multiplier, 0.5)
        monthly_savings = cost_data.current_monthly_cost * Decimal(str(savings_multiplier))
        optimized_cost = cost_data.current_monthly_cost - monthly_savings
        return OptimizationRecommendation(strategy=OptimizationStrategy.CONSOLIDATION, category=cost_data.category, current_cost=cost_data.current_monthly_cost, optimized_cost=optimized_cost, monthly_savings=monthly_savings, annual_savings=monthly_savings * 12, confidence_level=ConfidenceLevel.MEDIUM, implementation_effort='High - requires architecture changes', business_justification=f'Consolidating {cost_data.resource_count} resources can improve efficiency', roi_timeframe_months=6, risk_assessment='Medium risk - requires careful planning')

    def _calculate_business_impact_tier(self, monthly_savings: Decimal) -> str:
        """Calculate business impact tier based on savings potential."""
        if monthly_savings >= self.business_value_thresholds['enterprise_monthly_savings']:
            return 'Enterprise Impact ($20K+/month)'
        elif monthly_savings >= self.business_value_thresholds['high_value_monthly_savings']:
            return 'High Impact ($5K-$20K/month)'
        elif monthly_savings >= self.business_value_thresholds['minimum_monthly_savings']:
            return 'Medium Impact ($500-$5K/month)'
        else:
            return 'Low Impact (<$500/month)'

    def calculate_platform_roi(self, monthly_savings: Decimal, platform_cost: Decimal) -> Dict[str, Any]:
        """Calculate ROI of the platform based on cost savings delivered."""
        if platform_cost <= 0:
            return {'roi_multiple': 0, 'payback_months': float('inf'), 'justification': 'Invalid platform cost'}
        annual_savings = monthly_savings * 12
        annual_platform_cost = platform_cost * 12
        roi_multiple = annual_savings / annual_platform_cost if annual_platform_cost > 0 else 0
        payback_months = platform_cost / monthly_savings if monthly_savings > 0 else float('inf')
        if roi_multiple >= 10:
            justification = 'Exceptional ROI - platform pays for itself many times over'
        elif roi_multiple >= 5:
            justification = 'Excellent ROI - strong business case for platform'
        elif roi_multiple >= 2:
            justification = 'Good ROI - platform provides solid value'
        elif roi_multiple >= 1:
            justification = 'Break-even ROI - platform cost justified by savings'
        else:
            justification = 'Negative ROI - savings do not justify platform cost'
        return {'roi_multiple': float(roi_multiple), 'payback_months': float(payback_months) if payback_months != float('inf') else None, 'annual_savings': annual_savings, 'annual_platform_cost': annual_platform_cost, 'justification': justification, 'business_case_strength': 'strong' if roi_multiple >= 3 else 'weak' if roi_multiple < 1 else 'moderate'}

    def prioritize_recommendations_by_business_value(self, recommendations: List[OptimizationRecommendation]) -> List[OptimizationRecommendation]:
        """Prioritize recommendations based on business value and implementation ease."""

        def business_value_score(rec: OptimizationRecommendation) -> float:
            savings_score = float(rec.monthly_savings) / 1000
            confidence_multiplier = {ConfidenceLevel.HIGH: 1.0, ConfidenceLevel.MEDIUM: 0.7, ConfidenceLevel.LOW: 0.4}[rec.confidence_level]
            effort_multiplier = {'Low - automated': 1.0, 'Low - review required': 0.9, 'Medium - requires planning': 0.7, 'Medium - data migration required': 0.6, 'High - requires architecture changes': 0.4}.get(rec.implementation_effort, 0.5)
            timeframe_multiplier = max(0.1, 1.0 - (rec.roi_timeframe_months - 1) * 0.1)
            return savings_score * confidence_multiplier * effort_multiplier * timeframe_multiplier
        return sorted(recommendations, key=business_value_score, reverse=True)

    def generate_executive_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary for business stakeholders."""
        recommendations = analysis_result['recommendations']
        immediate_opportunities = [r for r in recommendations if r.roi_timeframe_months <= 3 and r.confidence_level == ConfidenceLevel.HIGH]
        immediate_savings = sum((r.monthly_savings for r in immediate_opportunities))
        quick_wins = [r for r in recommendations if r.implementation_effort.startswith('Low') and r.monthly_savings >= Decimal('1000')]
        high_impact_opportunities = [r for r in recommendations if r.monthly_savings >= Decimal('5000')]
        return {'total_annual_savings_potential': analysis_result['total_potential_annual_savings'], 'roi_percentage': analysis_result['roi_percentage'], 'business_impact_tier': analysis_result['business_impact_tier'], 'immediate_opportunities': {'count': len(immediate_opportunities), 'monthly_savings': immediate_savings, 'annual_savings': immediate_savings * 12}, 'quick_wins': {'count': len(quick_wins), 'description': 'Low-effort optimizations with significant savings'}, 'high_impact_opportunities': {'count': len(high_impact_opportunities), 'description': 'Major cost reduction opportunities requiring strategic attention'}, 'recommendation_categories': {strategy.value: len([r for r in recommendations if r.strategy == strategy]) for strategy in OptimizationStrategy}, 'confidence_distribution': {level.value: len([r for r in recommendations if r.confidence_level == level]) for level in ConfidenceLevel}, 'platform_justification': analysis_result['justifies_platform_cost']}

@pytest.mark.golden_path
@pytest.mark.unit
class CostOptimizationLogicTests(SSotBaseTestCase):
    """Test cost optimization business logic validation."""

    def setup_method(self, method=None):
        """Setup test environment."""
        super().setup_method(method)
        self.analyzer = MockCostOptimizationAnalyzer()
        self.test_user_id = UserID('enterprise_customer_123')

    @pytest.mark.unit
    def test_cost_analysis_thresholds_business_logic(self):
        """Test cost analysis thresholds for different categories."""
        compute_thresholds = self.analyzer.optimization_thresholds[CostCategory.COMPUTE]
        assert compute_thresholds['underutilization_threshold'] == 0.3
        assert compute_thresholds['minimum_monthly_cost'] == Decimal('100')
        storage_thresholds = self.analyzer.optimization_thresholds[CostCategory.STORAGE]
        assert storage_thresholds['underutilization_threshold'] == 0.5
        assert storage_thresholds['minimum_monthly_cost'] == Decimal('50')
        database_thresholds = self.analyzer.optimization_thresholds[CostCategory.DATABASE]
        assert database_thresholds['minimum_monthly_cost'] == Decimal('200')
        self.record_metric('cost_threshold_logic_validated', True)

    @pytest.mark.unit
    def test_rightsizing_recommendation_calculation_logic(self):
        """Test rightsizing recommendation calculation business logic."""
        underutilized_cost_data = CostData(category=CostCategory.COMPUTE, current_monthly_cost=Decimal('5000'), resource_count=10, utilization_percentage=0.1, region='us-east-1', service_name='EC2')
        recommendations = self.analyzer._analyze_category_optimization(underutilized_cost_data)
        rightsizing_recs = [r for r in recommendations if r.strategy == OptimizationStrategy.RIGHTSIZING]
        assert len(rightsizing_recs) == 1
        rec = rightsizing_recs[0]
        assert rec.confidence_level == ConfidenceLevel.HIGH
        assert rec.monthly_savings >= Decimal('2500')
        assert rec.roi_timeframe_months == 1
        assert 'overprovisioning' in rec.business_justification.lower()
        marginal_cost_data = CostData(category=CostCategory.COMPUTE, current_monthly_cost=Decimal('2000'), resource_count=5, utilization_percentage=0.25, region='us-east-1', service_name='EC2')
        marginal_recommendations = self.analyzer._analyze_category_optimization(marginal_cost_data)
        marginal_rightsizing = [r for r in marginal_recommendations if r.strategy == OptimizationStrategy.RIGHTSIZING]
        assert len(marginal_rightsizing) == 1
        marginal_rec = marginal_rightsizing[0]
        assert marginal_rec.confidence_level == ConfidenceLevel.MEDIUM
        assert marginal_rec.monthly_savings < rec.monthly_savings
        self.record_metric('rightsizing_calculation_accuracy', True)
        self.record_metric('high_underutilization_savings', float(rec.monthly_savings))
        self.record_metric('marginal_underutilization_savings', float(marginal_rec.monthly_savings))

    @pytest.mark.unit
    def test_reserved_instances_recommendation_logic(self):
        """Test reserved instances recommendation business logic."""
        high_cost_compute = CostData(category=CostCategory.COMPUTE, current_monthly_cost=Decimal('10000'), resource_count=20, utilization_percentage=0.7, region='us-east-1', service_name='EC2')
        recommendations = self.analyzer._analyze_category_optimization(high_cost_compute)
        ri_recs = [r for r in recommendations if r.strategy == OptimizationStrategy.RESERVED_INSTANCES]
        assert len(ri_recs) == 1
        ri_rec = ri_recs[0]
        assert ri_rec.confidence_level == ConfidenceLevel.HIGH
        assert ri_rec.monthly_savings >= Decimal('3000')
        assert ri_rec.roi_timeframe_months == 12
        assert 'predictable workload' in ri_rec.business_justification.lower()
        assert ri_rec.risk_assessment == 'Medium risk - requires capacity commitment'
        low_cost_compute = CostData(category=CostCategory.COMPUTE, current_monthly_cost=Decimal('500'), resource_count=2, utilization_percentage=0.8, region='us-east-1', service_name='EC2')
        low_cost_recommendations = self.analyzer._analyze_category_optimization(low_cost_compute)
        low_cost_ri_recs = [r for r in low_cost_recommendations if r.strategy == OptimizationStrategy.RESERVED_INSTANCES]
        assert len(low_cost_ri_recs) == 0
        self.record_metric('reserved_instances_logic_accuracy', True)
        self.record_metric('ri_monthly_savings', float(ri_rec.monthly_savings))

    @pytest.mark.unit
    def test_comprehensive_cost_analysis_business_value(self):
        """Test comprehensive cost analysis for enterprise customer."""
        enterprise_cost_data = [CostData(category=CostCategory.COMPUTE, current_monthly_cost=Decimal('25000'), resource_count=100, utilization_percentage=0.2, region='us-east-1', service_name='EC2'), CostData(category=CostCategory.DATABASE, current_monthly_cost=Decimal('15000'), resource_count=10, utilization_percentage=0.6, region='us-east-1', service_name='RDS'), CostData(category=CostCategory.STORAGE, current_monthly_cost=Decimal('8000'), resource_count=50, utilization_percentage=0.4, region='us-east-1', service_name='S3')]
        analysis_result = self.analyzer.analyze_cost_optimization_opportunities(enterprise_cost_data)
        assert analysis_result['total_current_monthly_cost'] == Decimal('48000')
        assert analysis_result['total_potential_monthly_savings'] >= Decimal('10000')
        assert analysis_result['roi_percentage'] >= 20
        assert analysis_result['justifies_platform_cost'] is True
        assert analysis_result['recommendation_count'] >= 3
        assert analysis_result['high_confidence_recommendations'] >= 2
        assert 'Enterprise Impact' in analysis_result['business_impact_tier']
        annual_savings = analysis_result['total_potential_annual_savings']
        assert annual_savings >= Decimal('120000')
        recommendations = analysis_result['recommendations']
        compute_recommendations = [r for r in recommendations if r.category == CostCategory.COMPUTE]
        assert len(compute_recommendations) >= 2
        database_recommendations = [r for r in recommendations if r.category == CostCategory.DATABASE]
        assert len(database_recommendations) >= 1
        self.record_metric('enterprise_monthly_savings', float(analysis_result['total_potential_monthly_savings']))
        self.record_metric('enterprise_annual_savings', float(annual_savings))
        self.record_metric('enterprise_roi_percentage', analysis_result['roi_percentage'])
        self.record_metric('enterprise_recommendation_count', analysis_result['recommendation_count'])

    @pytest.mark.unit
    def test_platform_roi_calculation_logic(self):
        """Test platform ROI calculation business logic."""
        monthly_savings = Decimal('20000')
        platform_cost = Decimal('2000')
        roi_result = self.analyzer.calculate_platform_roi(monthly_savings, platform_cost)
        assert roi_result['roi_multiple'] == 10.0
        assert roi_result['payback_months'] == 0.1
        assert roi_result['annual_savings'] == Decimal('240000')
        assert roi_result['annual_platform_cost'] == Decimal('24000')
        assert 'exceptional roi' in roi_result['justification'].lower()
        assert roi_result['business_case_strength'] == 'strong'
        marginal_savings = Decimal('1500')
        marginal_platform_cost = Decimal('1000')
        marginal_roi = self.analyzer.calculate_platform_roi(marginal_savings, marginal_platform_cost)
        assert marginal_roi['roi_multiple'] == 1.5
        assert marginal_roi['business_case_strength'] == 'moderate'
        assert 'good roi' in marginal_roi['justification'].lower()
        low_savings = Decimal('500')
        high_platform_cost = Decimal('1000')
        negative_roi = self.analyzer.calculate_platform_roi(low_savings, high_platform_cost)
        assert negative_roi['roi_multiple'] == 0.5
        assert negative_roi['business_case_strength'] == 'weak'
        assert 'negative roi' in negative_roi['justification'].lower()
        self.record_metric('excellent_roi_multiple', roi_result['roi_multiple'])
        self.record_metric('marginal_roi_multiple', marginal_roi['roi_multiple'])
        self.record_metric('roi_calculation_accuracy', True)

    @pytest.mark.unit
    def test_recommendation_prioritization_business_logic(self):
        """Test recommendation prioritization based on business value."""
        recommendations = [OptimizationRecommendation(strategy=OptimizationStrategy.RIGHTSIZING, category=CostCategory.COMPUTE, current_cost=Decimal('10000'), optimized_cost=Decimal('6000'), monthly_savings=Decimal('4000'), annual_savings=Decimal('48000'), confidence_level=ConfidenceLevel.HIGH, implementation_effort='Low - automated', business_justification='High underutilization', roi_timeframe_months=1, risk_assessment='Low risk'), OptimizationRecommendation(strategy=OptimizationStrategy.CONSOLIDATION, category=CostCategory.DATABASE, current_cost=Decimal('8000'), optimized_cost=Decimal('4800'), monthly_savings=Decimal('3200'), annual_savings=Decimal('38400'), confidence_level=ConfidenceLevel.MEDIUM, implementation_effort='High - requires architecture changes', business_justification='Multiple DB instances', roi_timeframe_months=6, risk_assessment='Medium risk'), OptimizationRecommendation(strategy=OptimizationStrategy.STORAGE_OPTIMIZATION, category=CostCategory.STORAGE, current_cost=Decimal('2000'), optimized_cost=Decimal('1400'), monthly_savings=Decimal('600'), annual_savings=Decimal('7200'), confidence_level=ConfidenceLevel.LOW, implementation_effort='Medium - data migration required', business_justification='Storage tiering opportunity', roi_timeframe_months=3, risk_assessment='Low risk')]
        prioritized = self.analyzer.prioritize_recommendations_by_business_value(recommendations)
        assert prioritized[0].strategy == OptimizationStrategy.RIGHTSIZING
        assert prioritized[0].monthly_savings == Decimal('4000')
        assert prioritized[0].implementation_effort == 'Low - automated'
        assert prioritized[-1].monthly_savings == Decimal('600')
        first_priority_savings = prioritized[0].monthly_savings
        last_priority_savings = prioritized[-1].monthly_savings
        assert first_priority_savings > last_priority_savings
        self.record_metric('prioritization_logic_accuracy', True)
        self.record_metric('top_priority_savings', float(first_priority_savings))

    @pytest.mark.unit
    def test_executive_summary_generation_logic(self):
        """Test executive summary generation for business stakeholders."""
        analysis_result = {'total_current_monthly_cost': Decimal('50000'), 'total_potential_monthly_savings': Decimal('18000'), 'total_potential_annual_savings': Decimal('216000'), 'roi_percentage': 43.2, 'business_impact_tier': 'Enterprise Impact ($20K+/month)', 'recommendation_count': 8, 'high_confidence_recommendations': 5, 'justifies_platform_cost': True, 'recommendations': [OptimizationRecommendation(strategy=OptimizationStrategy.RIGHTSIZING, category=CostCategory.COMPUTE, current_cost=Decimal('15000'), optimized_cost=Decimal('9000'), monthly_savings=Decimal('6000'), annual_savings=Decimal('72000'), confidence_level=ConfidenceLevel.HIGH, implementation_effort='Low - automated', business_justification='High underutilization', roi_timeframe_months=1, risk_assessment='Low risk'), OptimizationRecommendation(strategy=OptimizationStrategy.RESERVED_INSTANCES, category=CostCategory.DATABASE, current_cost=Decimal('12000'), optimized_cost=Decimal('7800'), monthly_savings=Decimal('4200'), annual_savings=Decimal('50400'), confidence_level=ConfidenceLevel.HIGH, implementation_effort='Medium - requires planning', business_justification='Predictable workload', roi_timeframe_months=2, risk_assessment='Medium risk')]}
        executive_summary = self.analyzer.generate_executive_summary(analysis_result)
        assert executive_summary['total_annual_savings_potential'] == Decimal('216000')
        assert executive_summary['roi_percentage'] == 43.2
        assert executive_summary['business_impact_tier'] == 'Enterprise Impact ($20K+/month)'
        assert executive_summary['platform_justification'] is True
        immediate_ops = executive_summary['immediate_opportunities']
        assert immediate_ops['count'] == 1
        assert immediate_ops['monthly_savings'] == Decimal('6000')
        assert immediate_ops['annual_savings'] == Decimal('72000')
        quick_wins = executive_summary['quick_wins']
        assert quick_wins['count'] == 1
        assert 'low-effort' in quick_wins['description'].lower()
        high_impact = executive_summary['high_impact_opportunities']
        assert high_impact['count'] == 2
        strategy_distribution = executive_summary['recommendation_categories']
        assert OptimizationStrategy.RIGHTSIZING.value in strategy_distribution
        assert OptimizationStrategy.RESERVED_INSTANCES.value in strategy_distribution
        self.record_metric('executive_summary_completeness', True)
        self.record_metric('immediate_opportunities_identified', immediate_ops['count'])
        self.record_metric('high_impact_opportunities_identified', high_impact['count'])

    @pytest.mark.unit
    def test_business_impact_tier_calculation_logic(self):
        """Test business impact tier calculation for different savings levels."""
        test_scenarios = [(Decimal('25000'), 'Enterprise Impact ($20K+/month)'), (Decimal('12000'), 'High Impact ($5K-$20K/month)'), (Decimal('2500'), 'Medium Impact ($500-$5K/month)'), (Decimal('300'), 'Low Impact (<$500/month)')]
        for monthly_savings, expected_tier in test_scenarios:
            calculated_tier = self.analyzer._calculate_business_impact_tier(monthly_savings)
            assert calculated_tier == expected_tier, f"Savings ${monthly_savings}/month should be '{expected_tier}', got '{calculated_tier}'"
        self.record_metric('business_impact_tier_accuracy', True)

    @pytest.mark.unit
    def test_minimum_cost_threshold_business_logic(self):
        """Test minimum cost thresholds prevent optimization of small costs."""
        small_cost_data = CostData(category=CostCategory.COMPUTE, current_monthly_cost=Decimal('50'), resource_count=1, utilization_percentage=0.1, region='us-east-1', service_name='EC2')
        recommendations = self.analyzer._analyze_category_optimization(small_cost_data)
        assert len(recommendations) == 0, 'Small costs should not generate optimization recommendations'
        sufficient_cost_data = CostData(category=CostCategory.COMPUTE, current_monthly_cost=Decimal('500'), resource_count=2, utilization_percentage=0.1, region='us-east-1', service_name='EC2')
        sufficient_recommendations = self.analyzer._analyze_category_optimization(sufficient_cost_data)
        assert len(sufficient_recommendations) > 0, 'Sufficient costs should generate recommendations'
        self.record_metric('minimum_cost_threshold_logic', True)

    @pytest.mark.unit
    def test_cost_optimization_accuracy_for_customer_segments(self):
        """Test cost optimization accuracy across different customer segments."""
        small_business_data = [CostData(category=CostCategory.COMPUTE, current_monthly_cost=Decimal('1500'), resource_count=5, utilization_percentage=0.3, region='us-east-1', service_name='EC2')]
        small_business_result = self.analyzer.analyze_cost_optimization_opportunities(small_business_data)
        mid_market_data = [CostData(category=CostCategory.COMPUTE, current_monthly_cost=Decimal('15000'), resource_count=30, utilization_percentage=0.25, region='us-east-1', service_name='EC2'), CostData(category=CostCategory.DATABASE, current_monthly_cost=Decimal('5000'), resource_count=5, utilization_percentage=0.6, region='us-east-1', service_name='RDS')]
        mid_market_result = self.analyzer.analyze_cost_optimization_opportunities(mid_market_data)
        assert mid_market_result['total_potential_monthly_savings'] > small_business_result['total_potential_monthly_savings']
        small_business_monthly_savings = small_business_result['total_potential_monthly_savings']
        mid_market_monthly_savings = mid_market_result['total_potential_monthly_savings']
        assert small_business_monthly_savings >= Decimal('300')
        assert mid_market_monthly_savings >= Decimal('4000')
        assert small_business_result['roi_percentage'] >= 15
        assert mid_market_result['roi_percentage'] >= 20
        self.record_metric('small_business_monthly_savings', float(small_business_monthly_savings))
        self.record_metric('mid_market_monthly_savings', float(mid_market_monthly_savings))
        self.record_metric('customer_segment_accuracy', True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')