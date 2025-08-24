from dev_launcher.isolated_environment import get_env
"""Input filtering and validation for NACIS security.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Prevents jailbreaking, PII exposure, and malicious inputs
to ensure safe AI consultation.
"""

import os
import re
from typing import Dict, List, Optional, Tuple

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class InputFilters:
    """Filters and validates input for security (<300 lines)."""
    
    def __init__(self):
        self.enabled = get_env().get("GUARDRAILS_ENABLED", "true").lower() == "true"
        self._init_pii_patterns()
        self._init_jailbreak_patterns()
        self._init_spam_indicators()
    
    def _init_pii_patterns(self) -> None:
        """Initialize PII detection patterns."""
        self.pii_patterns = {
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "api_key": r'\b[A-Za-z0-9]{32,}\b'
        }
    
    def _init_jailbreak_patterns(self) -> None:
        """Initialize jailbreak detection patterns."""
        self.jailbreak_keywords = [
            "ignore previous", "disregard instructions",
            "bypass", "override", "system prompt",
            "reveal prompt", "show instructions"
        ]
        self.role_play_patterns = [
            "you are now", "act as", "pretend to be",
            "roleplay", "simulate being"
        ]
    
    def _init_spam_indicators(self) -> None:
        """Initialize spam detection indicators."""
        self.spam_patterns = {
            "excessive_caps": r'[A-Z]{10,}',
            "repeated_chars": r'(.)\1{9,}',
            "excessive_punctuation": r'[!?]{5,}'
        }
        self.max_length = 10000  # Maximum input length
    
    async def filter_input(self, text: str) -> Tuple[str, List[str]]:
        """Filter input and return cleaned text with warnings."""
        warnings = []
        cleaned = self._check_length(text, warnings)
        cleaned = self._redact_pii(cleaned, warnings)
        self._check_jailbreak(cleaned, warnings)
        self._check_spam(cleaned, warnings)
        return cleaned, warnings
    
    def _check_length(self, text: str, warnings: List[str]) -> str:
        """Check and limit input length."""
        if len(text) > self.max_length:
            warnings.append("Input truncated to maximum length")
            return text[:self.max_length]
        return text
    
    def _redact_pii(self, text: str, warnings: List[str]) -> str:
        """Redact PII from input."""
        redacted = text
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, redacted)
            if matches:
                warnings.append(f"PII detected and redacted: {pii_type}")
                redacted = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", redacted)
        return redacted
    
    def _check_jailbreak(self, text: str, warnings: List[str]) -> None:
        """Check for jailbreak attempts."""
        text_lower = text.lower()
        for keyword in self.jailbreak_keywords:
            if keyword in text_lower:
                warnings.append(f"Potential jailbreak attempt: {keyword}")
        for pattern in self.role_play_patterns:
            if pattern in text_lower:
                warnings.append(f"Role-play attempt detected: {pattern}")
    
    def _check_spam(self, text: str, warnings: List[str]) -> None:
        """Check for spam indicators."""
        for spam_type, pattern in self.spam_patterns.items():
            if re.search(pattern, text):
                warnings.append(f"Spam indicator: {spam_type}")
    
    def is_safe(self, warnings: List[str]) -> bool:
        """Determine if input is safe based on warnings."""
        critical_warnings = self._get_critical_warnings(warnings)
        return len(critical_warnings) == 0
    
    def _get_critical_warnings(self, warnings: List[str]) -> List[str]:
        """Get critical warnings that should block processing."""
        critical = []
        for warning in warnings:
            if self._is_critical_warning(warning):
                critical.append(warning)
        return critical
    
    def _is_critical_warning(self, warning: str) -> bool:
        """Check if warning is critical."""
        critical_terms = ["jailbreak", "role-play", "api_key"]
        return any(term in warning.lower() for term in critical_terms)
    
    def sanitize_for_llm(self, text: str) -> str:
        """Sanitize text for LLM processing."""
        sanitized = self._remove_control_chars(text)
        sanitized = self._normalize_whitespace(sanitized)
        return sanitized.strip()
    
    def _remove_control_chars(self, text: str) -> str:
        """Remove control characters."""
        return ''.join(char for char in text if ord(char) >= 32 or char == '\n')
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace."""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text