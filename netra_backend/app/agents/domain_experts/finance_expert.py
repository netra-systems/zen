"""Finance Domain Expert Agent for NACIS.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Provides financial expertise for TCO analysis and ROI calculations.
"""

from netra_backend.app.agents.domain_experts.base_expert import BaseDomainExpert
from netra_backend.app.llm.llm_manager import LLMManager


class FinanceExpert(BaseDomainExpert):
    """Finance domain expert for TCO and financial analysis."""
    
    def __init__(self, llm_manager: LLMManager):
        super().__init__(llm_manager, "finance")
        self._init_finance_expertise()
    
    def _init_finance_expertise(self) -> None:
        """Initialize finance-specific expertise."""
        self.expertise_areas = [
            "Total Cost of Ownership (TCO)",
            "Return on Investment (ROI)",
            "Cost-Benefit Analysis",
            "Budget Planning",
            "Financial Risk Assessment"
        ]
        self.compliance_requirements = [
            "cost breakdown",
            "roi calculation",
            "payback period"
        ]
        self.best_practices = [
            "Include all direct and indirect costs",
            "Consider time value of money",
            "Account for risk factors",
            "Validate assumptions with benchmarks",
            "Provide sensitivity analysis"
        ]
    
    def _meets_requirement(self, request: dict, requirement: str) -> bool:
        """Check finance-specific requirements."""
        if requirement == "cost breakdown":
            return self._has_cost_breakdown(request)
        elif requirement == "roi calculation":
            return self._has_roi_calculation(request)
        elif requirement == "payback period":
            return self._has_payback_period(request)
        return super()._meets_requirement(request, requirement)
    
    def _has_cost_breakdown(self, request: dict) -> bool:
        """Check if request has cost breakdown."""
        data = request.get('data', {})
        return 'costs' in data or 'cost_breakdown' in data or 'monthly_cost' in data
    
    def _has_roi_calculation(self, request: dict) -> bool:
        """Check if request has ROI calculation."""
        data = request.get('data', {})
        return 'roi' in data or 'return' in data or 'investment' in data
    
    def _has_payback_period(self, request: dict) -> bool:
        """Check if request has payback period."""
        data = request.get('data', {})
        return 'payback' in data or 'break_even' in data