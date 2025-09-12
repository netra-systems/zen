"""
Business Scenario Factory

Factory class to create high-value business scenarios for testing mock response
elimination. Focuses on scenarios where receiving inauthentic AI responses would
have severe business consequences for enterprise customers.

Business Value: Validates that $500K+ ARR scenarios never receive mock responses
that could cause customer churn or reputation damage.
"""

import random
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class BusinessImpactLevel(Enum):
    """Business impact levels for different scenarios."""
    CRITICAL = "critical"      # $1M+ ARR, board decisions, public disclosure
    HIGH = "high"              # $500K+ ARR, executive decisions, contract renewals
    MEDIUM = "medium"          # $100K+ ARR, department decisions, budget planning
    LOW = "low"                # <$100K ARR, individual decisions, routine queries


class BusinessRole(Enum):
    """Business roles with different requirements."""
    CEO = "ceo"
    CFO = "cfo"
    CTO = "cto"
    VP_PROCUREMENT = "vp_procurement"
    DATA_ANALYST = "data_analyst"
    BUSINESS_STRATEGIST = "business_strategist"
    BOARD_MEMBER = "board_member"
    INVESTOR_RELATIONS = "investor_relations"


@dataclass
class BusinessScenario:
    """Represents a business scenario for testing."""
    title: str
    description: str
    user_role: BusinessRole
    arr_value: int
    subscription_tier: str
    business_context: Dict[str, Any]
    query_message: str
    impact_level: BusinessImpactLevel
    failure_consequences: List[str]
    success_criteria: List[str]
    mock_response_tolerance: float = 0.0  # 0.0 = no tolerance for enterprise


class BusinessScenarioFactory:
    """
    Factory to create business scenarios for mock response elimination testing.
    
    Creates realistic high-value business scenarios where receiving mock/fallback
    responses would cause immediate business damage.
    """
    
    def __init__(self):
        self._scenario_templates = self._initialize_scenario_templates()
    
    def _initialize_scenario_templates(self) -> Dict[str, Any]:
        """Initialize predefined scenario templates."""
        return {
            "board_presentation": {
                "base_title": "Board Presentation Analysis",
                "roles": [BusinessRole.CEO, BusinessRole.CFO],
                "arr_range": (1000000, 5000000),  # $1M-$5M
                "impact_level": BusinessImpactLevel.CRITICAL,
                "time_pressure": True,
                "public_visibility": True
            },
            "earnings_call": {
                "base_title": "Public Company Earnings Call",
                "roles": [BusinessRole.CFO, BusinessRole.INVESTOR_RELATIONS],
                "arr_range": (1200000, 10000000),  # $1.2M-$10M
                "impact_level": BusinessImpactLevel.CRITICAL,
                "sec_compliance": True,
                "investor_impact": True
            },
            "contract_renewal": {
                "base_title": "Enterprise Contract Renewal",
                "roles": [BusinessRole.VP_PROCUREMENT, BusinessRole.CTO],
                "arr_range": (500000, 2000000),  # $500K-$2M
                "impact_level": BusinessImpactLevel.HIGH,
                "competitive_evaluation": True,
                "renewal_at_risk": True
            },
            "budget_allocation": {
                "base_title": "Annual Budget Allocation",
                "roles": [BusinessRole.CFO, BusinessRole.CTO],
                "arr_range": (800000, 3000000),  # $800K-$3M
                "impact_level": BusinessImpactLevel.HIGH,
                "financial_planning": True,
                "audit_requirements": True
            },
            "platform_demo": {
                "base_title": "Enterprise Platform Demonstration",
                "roles": [BusinessRole.CTO, BusinessRole.VP_PROCUREMENT],
                "arr_range": (750000, 2500000),  # $750K-$2.5M
                "impact_level": BusinessImpactLevel.HIGH,
                "sales_critical": True,
                "competitive_comparison": True
            }
        }
    
    def create_board_presentation_scenario(
        self,
        custom_topic: Optional[str] = None,
        arr_value: Optional[int] = None
    ) -> BusinessScenario:
        """Create a board presentation scenario (critical impact)."""
        
        template = self._scenario_templates["board_presentation"]
        role = random.choice(template["roles"])
        arr = arr_value or random.randint(*template["arr_range"])
        
        topics = [
            "Q4 infrastructure cost optimization strategy",
            "cloud migration ROI analysis for board approval",
            "AI platform value demonstration for investment committee",
            "technology spend efficiency report for shareholders",
            "digital transformation cost-benefit analysis"
        ]
        
        topic = custom_topic or random.choice(topics)
        
        return BusinessScenario(
            title=f"Board Presentation: {topic}",
            description=f"{role.value.upper()} preparing critical board presentation on {topic}",
            user_role=role,
            arr_value=arr,
            subscription_tier="enterprise",
            business_context={
                "board_presentation": True,
                "time_critical": True,
                "high_visibility": True,
                "investor_impact": True,
                "strategic_decision": True,
                "financial_impact": arr * 0.1  # 10% of ARR at stake
            },
            query_message=(
                f"URGENT: Board meeting in 2 hours. Need comprehensive AI analysis "
                f"of {topic}. This will determine our strategic technology direction "
                f"and impact ${arr/1000:.0f}K annual budget allocation."
            ),
            impact_level=BusinessImpactLevel.CRITICAL,
            failure_consequences=[
                "Immediate loss of board confidence",
                "Strategic technology decision delay",
                f"${arr/1000:.0f}K budget reallocation risk",
                "CEO/CFO credibility damage",
                "Investor presentation failure"
            ],
            success_criteria=[
                "Comprehensive strategic analysis provided",
                "Clear financial implications outlined", 
                "Board-ready presentation data delivered",
                "Executive credibility maintained",
                "Strategic direction clarity achieved"
            ],
            mock_response_tolerance=0.0
        )
    
    def create_earnings_call_scenario(
        self,
        quarter: str = "Q3",
        arr_value: Optional[int] = None
    ) -> BusinessScenario:
        """Create an earnings call preparation scenario (critical impact)."""
        
        template = self._scenario_templates["earnings_call"]
        role = random.choice(template["roles"])
        arr = arr_value or random.randint(*template["arr_range"])
        
        return BusinessScenario(
            title=f"Public Company {quarter} Earnings Call Preparation",
            description=f"{role.value.upper()} preparing {quarter} earnings call with SEC compliance",
            user_role=role,
            arr_value=arr,
            subscription_tier="enterprise",
            business_context={
                "earnings_call": True,
                "sec_compliance": True,
                "public_disclosure": True,
                "investor_relations": True,
                "stock_impact": True,
                "quarter": quarter,
                "company_type": "public"
            },
            query_message=(
                f"EARNINGS CALL PREPARATION: Analyze {quarter} cloud infrastructure "
                f"efficiency and cost optimization achievements. Data will be referenced "
                f"in public earnings call and SEC filings. Need precise, auditable metrics."
            ),
            impact_level=BusinessImpactLevel.CRITICAL,
            failure_consequences=[
                "SEC compliance violation risk",
                "Investor confidence damage", 
                "Stock price negative impact",
                "Earnings call credibility loss",
                "Regulatory scrutiny increase"
            ],
            success_criteria=[
                "SEC-compliant data provided",
                "Auditable metrics delivered",
                "Investor-grade analysis quality",
                "Public disclosure readiness",
                "Regulatory compliance maintained"
            ],
            mock_response_tolerance=0.0
        )
    
    def create_contract_renewal_scenario(
        self,
        competitor_count: int = 3,
        arr_value: Optional[int] = None
    ) -> BusinessScenario:
        """Create a contract renewal evaluation scenario (high impact)."""
        
        template = self._scenario_templates["contract_renewal"]
        role = random.choice(template["roles"])
        arr = arr_value or random.randint(*template["arr_range"])
        
        return BusinessScenario(
            title=f"${arr/1000:.0f}K Enterprise Contract Renewal Evaluation",
            description=f"{role.value.upper()} evaluating platform against {competitor_count} competitors",
            user_role=role,
            arr_value=arr,
            subscription_tier="enterprise",
            business_context={
                "contract_renewal": True,
                "competitive_evaluation": True,
                "renewal_at_risk": True,
                "competitor_count": competitor_count,
                "evaluation_stage": "final",
                "decision_timeline": "30_days"
            },
            query_message=(
                f"Contract renewal evaluation: Demonstrate platform value with "
                f"comprehensive analysis of infrastructure optimization. "
                f"{role.value.replace('_', ' ').title()} evaluating against {competitor_count} competitors. "
                f"Show ROI justification for ${arr/1000:.0f}K annual investment."
            ),
            impact_level=BusinessImpactLevel.HIGH,
            failure_consequences=[
                f"${arr/1000:.0f}K annual revenue loss",
                "Customer churn to competitor",
                "Negative reference impact",
                "Competitive disadvantage exposure",
                "Renewal team credibility damage"
            ],
            success_criteria=[
                "Clear ROI demonstration",
                "Competitive advantage highlighted",
                "Value proposition strengthened",
                "Renewal probability increased",
                "Customer confidence maintained"
            ],
            mock_response_tolerance=0.0
        )
    
    def create_cfo_budget_scenario(
        self,
        budget_amount: int = 20000000,
        arr_value: Optional[int] = None
    ) -> BusinessScenario:
        """Create a CFO budget allocation scenario (high impact)."""
        
        arr = arr_value or random.randint(800000, 2500000)
        
        return BusinessScenario(
            title=f"CFO Budget Allocation: ${budget_amount/1000000:.0f}M Technology Budget",
            description=f"CFO analyzing ${budget_amount/1000000:.0f}M technology budget optimization",
            user_role=BusinessRole.CFO,
            arr_value=arr,
            subscription_tier="enterprise",
            business_context={
                "budget_allocation": True,
                "financial_planning": True,
                "audit_requirements": True,
                "sox_compliance": True,
                "budget_amount": budget_amount,
                "fiscal_planning": True
            },
            query_message=(
                f"CFO CRITICAL: Analyze Q4 infrastructure spend optimization for "
                f"annual budgeting. Need accurate cost savings projections for "
                f"${budget_amount/1000000:.0f}M budget allocation. Data will be audited and reported to board."
            ),
            impact_level=BusinessImpactLevel.HIGH,
            failure_consequences=[
                "Budget misallocation risk",
                "Audit compliance failure",
                "Board reporting inaccuracy",
                "CFO credibility damage",
                "Financial planning disruption"
            ],
            success_criteria=[
                "Accurate financial projections",
                "Audit-compliant data provided",
                "Board-ready financial analysis",
                "Budget optimization clarity",
                "Fiduciary responsibility met"
            ],
            mock_response_tolerance=0.0
        )
    
    def create_platform_demo_scenario(
        self,
        prospect_name: str = "MegaCorp",
        arr_value: Optional[int] = None
    ) -> BusinessScenario:
        """Create a platform demonstration scenario (high impact)."""
        
        template = self._scenario_templates["platform_demo"]
        role = random.choice(template["roles"])
        arr = arr_value or random.randint(*template["arr_range"])
        
        return BusinessScenario(
            title=f"Enterprise Demo: {prospect_name} - ${arr/1000:.0f}K Opportunity",
            description=f"{role.value.upper()} final platform demonstration for ${arr/1000:.0f}K prospect",
            user_role=role,
            arr_value=arr,
            subscription_tier="enterprise",
            business_context={
                "platform_demo": True,
                "sales_critical": True,
                "competitive_evaluation": True,
                "final_decision": True,
                "prospect_value": arr,
                "demo_stage": "final"
            },
            query_message=(
                f"Platform demonstration: Show comprehensive AI-powered cost "
                f"optimization analysis for enterprise infrastructure. {role.value.replace('_', ' ').title()} "
                f"at {prospect_name} evaluating against 3 competitors for ${arr/1000:.0f}K annual contract."
            ),
            impact_level=BusinessImpactLevel.HIGH,
            failure_consequences=[
                f"${arr/1000:.0f}K sales opportunity loss",
                "Competitive deal failure",
                "Demo team credibility damage",
                "Sales pipeline impact",
                "Revenue target miss"
            ],
            success_criteria=[
                "Impressive capability demonstration",
                "Competitive differentiation clear",
                "Prospect engagement high",
                "Technical credibility established",
                "Sales advancement achieved"
            ],
            mock_response_tolerance=0.0
        )
    
    def create_random_high_value_scenario(self) -> BusinessScenario:
        """Create a random high-value business scenario."""
        
        scenario_types = [
            "board_presentation",
            "earnings_call", 
            "contract_renewal",
            "budget_allocation",
            "platform_demo"
        ]
        
        scenario_type = random.choice(scenario_types)
        
        if scenario_type == "board_presentation":
            return self.create_board_presentation_scenario()
        elif scenario_type == "earnings_call":
            return self.create_earnings_call_scenario()
        elif scenario_type == "contract_renewal":
            return self.create_contract_renewal_scenario()
        elif scenario_type == "budget_allocation":
            return self.create_cfo_budget_scenario()
        elif scenario_type == "platform_demo":
            return self.create_platform_demo_scenario()
    
    def create_progressive_value_scenarios(self, count: int = 5) -> List[BusinessScenario]:
        """Create a progression of scenarios with increasing business value."""
        
        scenarios = []
        
        # Start with medium value, progress to critical
        arr_values = [300000, 600000, 1000000, 2000000, 5000000]
        scenario_types = [
            "contract_renewal",
            "budget_allocation", 
            "platform_demo",
            "board_presentation",
            "earnings_call"
        ]
        
        for i in range(min(count, len(arr_values))):
            arr_value = arr_values[i]
            scenario_type = scenario_types[i % len(scenario_types)]
            
            if scenario_type == "board_presentation":
                scenario = self.create_board_presentation_scenario(arr_value=arr_value)
            elif scenario_type == "earnings_call":
                scenario = self.create_earnings_call_scenario(arr_value=arr_value)
            elif scenario_type == "contract_renewal":
                scenario = self.create_contract_renewal_scenario(arr_value=arr_value)
            elif scenario_type == "budget_allocation":
                scenario = self.create_cfo_budget_scenario(arr_value=arr_value)
            elif scenario_type == "platform_demo":
                scenario = self.create_platform_demo_scenario(arr_value=arr_value)
            
            scenarios.append(scenario)
        
        return scenarios
    
    def create_mock_response_test_cases(self) -> List[Dict[str, Any]]:
        """Create test cases specifically designed to trigger mock responses."""
        
        scenarios = [
            self.create_board_presentation_scenario(),
            self.create_earnings_call_scenario(),
            self.create_contract_renewal_scenario(),
            self.create_cfo_budget_scenario(),
            self.create_platform_demo_scenario()
        ]
        
        test_cases = []
        
        for scenario in scenarios:
            # Create failure-inducing query
            failure_query = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": f" ALERT:  FORCE_FAILURE_SCENARIO  ALERT:  {scenario.query_message}",
                "context": {
                    "user_role": scenario.user_role.value,
                    "arr_value": scenario.arr_value,
                    "subscription": scenario.subscription_tier,
                    "business_critical": True,
                    "mock_tolerance": scenario.mock_response_tolerance,
                    **scenario.business_context
                },
                "request_id": f"mock_test_{scenario.title.lower().replace(' ', '_')}_{int(time.time())}"
            }
            
            test_case = {
                "scenario": scenario,
                "failure_query": failure_query,
                "expected_authentic_handling": True,
                "mock_response_forbidden": True,
                "business_impact_if_mock": scenario.failure_consequences,
                "success_criteria": scenario.success_criteria
            }
            
            test_cases.append(test_case)
        
        return test_cases


# Utility functions for common scenario creation
def create_fortune_500_ceo_scenario() -> BusinessScenario:
    """Create Fortune 500 CEO scenario (maximum business impact)."""
    factory = BusinessScenarioFactory()
    return factory.create_board_presentation_scenario(
        custom_topic="strategic technology investment for competitive advantage",
        arr_value=1500000
    )


def create_public_company_cfo_scenario() -> BusinessScenario:
    """Create public company CFO scenario (SEC compliance critical)."""
    factory = BusinessScenarioFactory()
    return factory.create_earnings_call_scenario(
        quarter="Q4",
        arr_value=1200000
    )


def create_enterprise_renewal_risk_scenario() -> BusinessScenario:
    """Create enterprise contract renewal at-risk scenario."""
    factory = BusinessScenarioFactory()
    return factory.create_contract_renewal_scenario(
        competitor_count=3,
        arr_value=800000
    )


def create_sales_demo_critical_scenario() -> BusinessScenario:
    """Create sales demo critical opportunity scenario."""
    factory = BusinessScenarioFactory()
    return factory.create_platform_demo_scenario(
        prospect_name="Global Enterprise Corp",
        arr_value=750000
    )