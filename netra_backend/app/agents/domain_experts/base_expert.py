"""Base Domain Expert Agent for NACIS.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Foundation for specialized domain expertise in AI consultation.
"""

from typing import Any, Dict, List

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class BaseDomainExpert(BaseAgent):
    """Base class for domain expert agents (<300 lines)."""
    
    def __init__(self, llm_manager: LLMManager, domain: str):
        super().__init__(llm_manager, name=f"{domain}Expert",
                        description=f"Domain expert for {domain}")
        self._init_domain_config(domain)
        self._init_expertise_areas()
    
    def _init_domain_config(self, domain: str) -> None:
        """Initialize domain configuration."""
        self.domain = domain
        self.expert_model = "quality_llm"  # Tier 3 for expertise
        self.confidence_threshold = 0.8
    
    def _init_expertise_areas(self) -> None:
        """Initialize expertise areas (override in subclasses)."""
        self.expertise_areas = []
        self.compliance_requirements = []
        self.best_practices = []
    
    async def execute_from_context(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute domain validation from context."""
        request = self._extract_request(context)
        requirements = await self._validate_requirements(request)
        recommendations = await self._generate_recommendations(request)
        compliance = self._check_compliance(request)
        return self._format_expert_response(requirements, recommendations, compliance)
    
    def _extract_request(self, context: ExecutionContext) -> Dict:
        """Extract request from context."""
        if context.state:
            return {
                "query": context.state.user_request or "",
                "data": getattr(context.state, 'accumulated_data', {})
            }
        return {}
    
    async def _validate_requirements(self, request: Dict) -> Dict:
        """Validate domain-specific requirements."""
        prompt = self._build_validation_prompt(request)
        response = await self.llm_manager.ask_llm(prompt, self.expert_model)
        return self._parse_validation_response(response)
    
    def _build_validation_prompt(self, request: Dict) -> str:
        """Build validation prompt for domain expertise."""
        return f"""As a {self.domain} expert, validate these requirements:
Query: {request.get('query', '')}
Context: {str(request.get('data', {}))[:500]}

Check for completeness, accuracy, and {self.domain}-specific considerations."""
    
    def _parse_validation_response(self, response: str) -> Dict:
        """Parse validation response."""
        return {
            "valid": "valid" in response.lower() or "correct" in response.lower(),
            "details": response[:500]
        }
    
    async def _generate_recommendations(self, request: Dict) -> List[str]:
        """Generate domain-specific recommendations."""
        prompt = self._build_recommendation_prompt(request)
        response = await self.llm_manager.ask_llm(prompt, self.expert_model)
        return self._extract_recommendations(response)
    
    def _build_recommendation_prompt(self, request: Dict) -> str:
        """Build recommendation prompt."""
        return f"""As a {self.domain} expert, provide recommendations for:
{request.get('query', '')}

Focus on {self.domain}-specific best practices and industry standards."""
    
    def _extract_recommendations(self, response: str) -> List[str]:
        """Extract recommendations from response."""
        lines = response.split('\n')
        recommendations = []
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                recommendations.append(line)
        return recommendations[:5]  # Top 5 recommendations
    
    def _check_compliance(self, request: Dict) -> Dict:
        """Check domain-specific compliance."""
        issues = []
        for requirement in self.compliance_requirements:
            if not self._meets_requirement(request, requirement):
                issues.append(f"Missing: {requirement}")
        return {
            "compliant": len(issues) == 0,
            "issues": issues
        }
    
    def _meets_requirement(self, request: Dict, requirement: str) -> bool:
        """Check if request meets specific requirement."""
        query_lower = request.get('query', '').lower()
        return requirement.lower() in query_lower or self._check_data_requirement(request, requirement)
    
    def _check_data_requirement(self, request: Dict, requirement: str) -> bool:
        """Check requirement in data."""
        data_str = str(request.get('data', {})).lower()
        return requirement.lower() in data_str
    
    def _format_expert_response(self, requirements: Dict, 
                              recommendations: List[str], compliance: Dict) -> Dict:
        """Format expert response."""
        return {
            "domain": self.domain,
            "status": "validated" if requirements["valid"] and compliance["compliant"] else "issues_found",
            "requirements": requirements,
            "recommendations": recommendations,
            "compliance": compliance,
            "expertise_applied": self.expertise_areas
        }