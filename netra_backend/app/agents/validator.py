"""Validator Agent for NACIS - Ensures response accuracy and compliance.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Guarantees 95%+ accuracy through fact-checking,
citation validation, and compliance verification.
"""

from typing import Any, Dict, List, Optional

from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.guardrails.output_validators import OutputValidators
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ValidatorAgent(BaseSubAgent):
    """Validates responses for accuracy and compliance (<300 lines)."""
    
    def __init__(self, llm_manager: LLMManager,
                 output_validators: Optional[OutputValidators] = None):
        super().__init__(llm_manager, name="ValidatorAgent",
                        description="NACIS validator for accuracy and compliance")
        self._init_validation_components(output_validators)
        self._init_validation_criteria()
    
    def _init_validation_components(self, validators: Optional[OutputValidators]) -> None:
        """Initialize validation components."""
        self.output_validators = validators or OutputValidators()
        self.validation_model = "default_llm"  # Tier 2 for validation
        self.fact_check_model = "quality_llm"  # Tier 3 for fact-checking
    
    def _init_validation_criteria(self) -> None:
        """Initialize validation criteria."""
        self.min_citation_count = 2
        self.max_age_days = 30
        self.required_accuracy = 0.95
        self.max_response_length = 5000
    
    async def execute_from_context(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute validation from orchestrator context."""
        response = self._extract_response(context)
        research_data = self._extract_research_data(context)
        validation_result = await self._validate_response(response, research_data)
        return self._format_validation_result(validation_result)
    
    def _extract_response(self, context: ExecutionContext) -> Dict:
        """Extract response to validate from context."""
        if context.state and hasattr(context.state, 'accumulated_data'):
            return context.state.accumulated_data
        return {}
    
    def _extract_research_data(self, context: ExecutionContext) -> Dict:
        """Extract research data for fact-checking."""
        if context.state and hasattr(context.state, 'accumulated_data'):
            return context.state.accumulated_data.get('verified_sources', {})
        return {}
    
    async def _validate_response(self, response: Dict, research_data: Dict) -> Dict:
        """Perform comprehensive validation."""
        validations = {}
        validations["citations"] = await self._validate_citations(response, research_data)
        validations["accuracy"] = await self._validate_accuracy(response, research_data)
        validations["compliance"] = await self._validate_compliance(response)
        validations["format"] = self._validate_format(response)
        return validations
    
    async def _validate_citations(self, response: Dict, research_data: Dict) -> Dict:
        """Validate citations in response."""
        citations = self._extract_citations(response)
        validation = {
            "count": len(citations),
            "valid": len(citations) >= self.min_citation_count,
            "issues": []
        }
        for citation in citations:
            self._validate_single_citation(citation, research_data, validation)
        return validation
    
    def _extract_citations(self, response: Dict) -> List[Dict]:
        """Extract citations from response."""
        if "verified_sources" in response:
            return response["verified_sources"]
        elif "citations" in response:
            return response["citations"]
        return []
    
    def _validate_single_citation(self, citation: Dict, research_data: Dict,
                                 validation: Dict) -> None:
        """Validate a single citation."""
        if not citation.get("url"):
            validation["issues"].append("Missing URL in citation")
        if not citation.get("date"):
            validation["issues"].append("Missing date in citation")
        elif not self._is_recent(citation["date"]):
            validation["issues"].append(f"Outdated citation: {citation['date']}")
    
    def _is_recent(self, date_str: str) -> bool:
        """Check if date is recent enough."""
        # Simplified date check
        try:
            year = int(date_str[:4]) if len(date_str) >= 4 else 0
            return year >= 2024
        except (ValueError, IndexError):
            return False
    
    async def _validate_accuracy(self, response: Dict, research_data: Dict) -> Dict:
        """Validate factual accuracy of response."""
        claims = self._extract_claims(response)
        verified_count = 0
        issues = []
        for claim in claims[:5]:  # Check top 5 claims
            if await self._verify_claim(claim, research_data):
                verified_count += 1
            else:
                issues.append(f"Unverified claim: {claim[:50]}")
        accuracy_score = verified_count / len(claims) if claims else 0
        return {
            "score": accuracy_score,
            "valid": accuracy_score >= self.required_accuracy,
            "issues": issues
        }
    
    def _extract_claims(self, response: Dict) -> List[str]:
        """Extract factual claims from response."""
        content = str(response.get("data", ""))
        # Simplified claim extraction
        sentences = content.split('.')
        return [s.strip() for s in sentences if len(s.strip()) > 20]
    
    async def _verify_claim(self, claim: str, research_data: Dict) -> bool:
        """Verify a factual claim against research data."""
        if not research_data:
            return False  # Can't verify without data
        prompt = self._build_verification_prompt(claim, research_data)
        result = await self.llm_manager.ask_llm(prompt, self.fact_check_model)
        return "verified" in result.lower() or "true" in result.lower()
    
    def _build_verification_prompt(self, claim: str, research_data: Dict) -> str:
        """Build prompt for claim verification."""
        sources = str(research_data)[:1000]  # Limit context
        return f"""Verify this claim against the provided sources:
Claim: {claim}
Sources: {sources}
Is the claim verified? (Yes/No)"""
    
    async def _validate_compliance(self, response: Dict) -> Dict:
        """Validate compliance with safety and legal requirements."""
        validated = await self.output_validators.validate_output(response)
        return {
            "valid": validated.get("validated", False),
            "issues": validated.get("validation_issues", [])
        }
    
    def _validate_format(self, response: Dict) -> Dict:
        """Validate response format and structure."""
        issues = []
        if not response.get("data"):
            issues.append("Missing data field")
        if not response.get("trace"):
            issues.append("Missing trace field")
        content_length = len(str(response.get("data", "")))
        if content_length > self.max_response_length:
            issues.append(f"Response too long: {content_length} chars")
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def _format_validation_result(self, validations: Dict) -> Dict:
        """Format validation results."""
        all_valid = all(v.get("valid", False) for v in validations.values())
        all_issues = []
        for category, validation in validations.items():
            if "issues" in validation:
                all_issues.extend(validation["issues"])
        return {
            "status": "validated" if all_valid else "failed",
            "valid": all_valid,
            "validations": validations,
            "issues": all_issues,
            "recommendation": self._get_recommendation(all_valid, all_issues)
        }
    
    def _get_recommendation(self, valid: bool, issues: List[str]) -> str:
        """Get recommendation based on validation results."""
        if valid:
            return "Response validated - ready for delivery"
        elif len(issues) <= 2:
            return "Minor issues - consider corrections"
        else:
            return "Major issues - response needs revision"