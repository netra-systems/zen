"""Business Domain Expert Agent for NACIS.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Provides business strategy expertise for market analysis and growth.
"""

from netra_backend.app.agents.domain_experts.base_expert import BaseDomainExpert
from netra_backend.app.llm.llm_manager import LLMManager


class BusinessExpert(BaseDomainExpert):
    """Business domain expert for strategy and market analysis."""
    
    def __init__(self, llm_manager: LLMManager):
        super().__init__(llm_manager, "business")
        self._init_business_expertise()
    
    def _init_business_expertise(self) -> None:
        """Initialize business-specific expertise."""
        self.expertise_areas = [
            "Market Analysis",
            "Competitive Intelligence",
            "Business Model Validation",
            "Growth Strategy",
            "Risk Management"
        ]
        self.compliance_requirements = [
            "market analysis",
            "competitive landscape",
            "business case"
        ]
        self.best_practices = [
            "Validate market demand",
            "Analyze competitive positioning",
            "Define clear value proposition",
            "Identify target segments",
            "Assess market risks"
        ]
    
    def _meets_requirement(self, request: dict, requirement: str) -> bool:
        """Check business-specific requirements."""
        if requirement == "market analysis":
            return self._has_market_analysis(request)
        elif requirement == "competitive landscape":
            return self._has_competitive_analysis(request)
        elif requirement == "business case":
            return self._has_business_case(request)
        return super()._meets_requirement(request, requirement)
    
    def _has_market_analysis(self, request: dict) -> bool:
        """Check if request has market analysis."""
        data = request.get('data', {})
        market_terms = ['market', 'demand', 'customers', 'segments']
        return any(t in str(data).lower() for t in market_terms)
    
    def _has_competitive_analysis(self, request: dict) -> bool:
        """Check if request has competitive analysis."""
        data = request.get('data', {})
        competitive_terms = ['competitor', 'competition', 'alternative', 'benchmark']
        return any(t in str(data).lower() for t in competitive_terms)
    
    def _has_business_case(self, request: dict) -> bool:
        """Check if request has business case."""
        data = request.get('data', {})
        business_terms = ['revenue', 'profit', 'growth', 'strategy']
        return any(t in str(data).lower() for t in business_terms)