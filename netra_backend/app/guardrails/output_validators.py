"""Output validation for NACIS responses.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Ensures safe, compliant, and accurate responses
before delivery to users.
"""

import re
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class OutputValidators:
    """Validates output for safety and compliance (<300 lines)."""
    
    def __init__(self):
        self._init_content_filters()
        self._init_compliance_rules()
        self._init_format_requirements()
    
    def _init_content_filters(self) -> None:
        """Initialize content filtering rules."""
        self.prohibited_content = [
            "medical advice", "legal advice", "financial advice",
            "harm", "violence", "illegal"
        ]
        self.sensitive_topics = [
            "health", "finance", "legal", "personal"
        ]
    
    def _init_compliance_rules(self) -> None:
        """Initialize compliance validation rules."""
        self.required_disclaimers = {
            "financial": "This is not financial advice.",
            "medical": "Consult a healthcare professional.",
            "legal": "Consult a legal professional."
        }
    
    def _init_format_requirements(self) -> None:
        """Initialize format requirements."""
        self.max_response_length = 5000
        self.min_response_length = 10
        self.required_elements = ["data", "trace"]
    
    async def validate_output(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean output response."""
        validated = response.copy()
        issues = []
        self._check_content_safety(validated, issues)
        self._check_compliance(validated, issues)
        self._check_format(validated, issues)
        return self._finalize_response(validated, issues)
    
    def _check_content_safety(self, response: Dict, issues: List[str]) -> None:
        """Check content for safety violations."""
        content = self._extract_content(response)
        for prohibited in self.prohibited_content:
            if prohibited in content.lower():
                issues.append(f"Prohibited content: {prohibited}")
    
    def _extract_content(self, response: Dict) -> str:
        """Extract text content from response."""
        data = response.get("data", {})
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            return str(data.get("analysis", ""))
        return ""
    
    def _check_compliance(self, response: Dict, issues: List[str]) -> None:
        """Check compliance requirements."""
        content = self._extract_content(response)
        disclaimers_needed = self._identify_needed_disclaimers(content)
        if disclaimers_needed:
            self._add_disclaimers(response, disclaimers_needed)
    
    def _identify_needed_disclaimers(self, content: str) -> List[str]:
        """Identify which disclaimers are needed."""
        needed = []
        content_lower = content.lower()
        # Check for financial content specifically
        if any(word in content_lower for word in ["financial", "roi", "investment", "profit"]):
            needed.append("financial")
        # Check other sensitive topics
        for topic in self.sensitive_topics:
            if topic in content_lower and topic not in needed:
                needed.append(topic)
        return needed
    
    def _add_disclaimers(self, response: Dict, topics: List[str]) -> None:
        """Add required disclaimers to response."""
        disclaimers = []
        for topic in topics:
            if topic in self.required_disclaimers:
                disclaimers.append(self.required_disclaimers[topic])
        if disclaimers:
            response["disclaimers"] = disclaimers
    
    def _check_format(self, response: Dict, issues: List[str]) -> None:
        """Check response format requirements."""
        for element in self.required_elements:
            if element not in response:
                issues.append(f"Missing required element: {element}")
        self._check_response_length(response, issues)
    
    def _check_response_length(self, response: Dict, issues: List[str]) -> None:
        """Check response length constraints."""
        content = self._extract_content(response)
        if len(content) > self.max_response_length:
            issues.append("Response exceeds maximum length")
        elif len(content) < self.min_response_length:
            issues.append("Response too short")
    
    def _finalize_response(self, response: Dict, issues: List[str]) -> Dict:
        """Finalize response with validation results."""
        if issues:
            response["validation_issues"] = issues
            logger.warning(f"Output validation issues: {issues}")
        response["validated"] = len(issues) == 0
        return response
    
    def redact_sensitive_data(self, text: str) -> str:
        """Redact sensitive data from output."""
        patterns = {
            r'\b\d{3}-\d{2}-\d{4}\b': '[SSN_REDACTED]',
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b': '[CC_REDACTED]',
            r'\b[A-Za-z0-9]{32,}\b': '[KEY_REDACTED]'
        }
        for pattern, replacement in patterns.items():
            text = re.sub(pattern, replacement, text)
        return text
    
    def format_for_display(self, response: Dict) -> Dict:
        """Format response for user display."""
        formatted = response.copy()
        if "data" in formatted:
            formatted["data"] = self._clean_data_for_display(formatted["data"])
        if "trace" in formatted:
            formatted["trace"] = self._format_trace(formatted["trace"])
        return formatted
    
    def _clean_data_for_display(self, data: Any) -> Any:
        """Clean data for display."""
        if isinstance(data, str):
            return self.redact_sensitive_data(data)
        elif isinstance(data, dict):
            return {k: self._clean_data_for_display(v) for k, v in data.items()}
        return data
    
    def _format_trace(self, trace: List[str]) -> List[str]:
        """Format trace for display."""
        return [line[:100] for line in trace[:5]]  # Limit trace display