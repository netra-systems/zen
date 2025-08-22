"""Engineering Domain Expert Agent for NACIS.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Provides technical expertise for optimization and performance analysis.
"""

from netra_backend.app.agents.domain_experts.base_expert import BaseDomainExpert
from netra_backend.app.llm.llm_manager import LLMManager


class EngineeringExpert(BaseDomainExpert):
    """Engineering domain expert for technical optimization."""
    
    def __init__(self, llm_manager: LLMManager):
        super().__init__(llm_manager, "engineering")
        self._init_engineering_expertise()
    
    def _init_engineering_expertise(self) -> None:
        """Initialize engineering-specific expertise."""
        self.expertise_areas = [
            "Performance Optimization",
            "System Architecture",
            "Scalability Analysis",
            "Technical Debt Assessment",
            "Infrastructure Design"
        ]
        self.compliance_requirements = [
            "performance metrics",
            "scalability plan",
            "technical specifications"
        ]
        self.best_practices = [
            "Measure baseline performance",
            "Define clear SLAs/SLOs",
            "Consider horizontal scaling",
            "Implement monitoring and observability",
            "Plan for failure scenarios"
        ]
    
    def _meets_requirement(self, request: dict, requirement: str) -> bool:
        """Check engineering-specific requirements."""
        if requirement == "performance metrics":
            return self._has_performance_metrics(request)
        elif requirement == "scalability plan":
            return self._has_scalability_plan(request)
        elif requirement == "technical specifications":
            return self._has_technical_specs(request)
        return super()._meets_requirement(request, requirement)
    
    def _has_performance_metrics(self, request: dict) -> bool:
        """Check if request has performance metrics."""
        data = request.get('data', {})
        metrics = ['latency', 'throughput', 'response_time', 'qps']
        return any(m in str(data).lower() for m in metrics)
    
    def _has_scalability_plan(self, request: dict) -> bool:
        """Check if request has scalability considerations."""
        data = request.get('data', {})
        scalability = ['scale', 'growth', 'capacity', 'load']
        return any(s in str(data).lower() for s in scalability)
    
    def _has_technical_specs(self, request: dict) -> bool:
        """Check if request has technical specifications."""
        data = request.get('data', {})
        specs = ['cpu', 'memory', 'storage', 'bandwidth', 'architecture']
        return any(s in str(data).lower() for s in specs)