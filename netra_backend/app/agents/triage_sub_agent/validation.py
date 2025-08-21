# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-13T00:00:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Refactored from triage_sub_agent_legacy.py - Validation (25-line function limit)
# Git: v6 | dirty
# Change: Refactor | Scope: Component | Risk: Low
# Session: compliance-fix | Seq: 4
# Review: Pending | Score: 95
# ================================
"""Triage validation utilities - compliant with 25-line limit."""

import re
from typing import List
from app.agents.triage_sub_agent.models import ValidationStatus


def check_request_length(request: str, validation: ValidationStatus) -> None:
    """Check if request length is valid."""
    if len(request) > 10000:
        validation.validation_errors.append("Request exceeds maximum length of 10000 characters")
        validation.is_valid = False
    elif len(request) < 3:
        validation.validation_errors.append("Request is too short to process")
        validation.is_valid = False


def get_injection_patterns() -> List[str]:
    """Get patterns for detecting injection attempts."""
    return [
        r'<script', r'javascript:', r'DROP\s+TABLE', r'DELETE\s+FROM',
        r'INSERT\s+INTO', r'UNION\s+SELECT', r"'\s*OR\s*'", r";\s*DELETE",
        r"--\s*$", r"admin'\s*--", r"eval\s*\(", r"document\.cookie",
        r"<img.*onerror", r"SELECT.*FROM.*users", r"SELECT.*FROM.*secrets",
        r"rm\s+-rf\s+/", r"cat\s+/etc/passwd", r";\s*curl\s+", r"\$\(",
        r"`.*`", r"/etc/passwd", r"&&\s*rm", r"\|\s*rm"
    ]


def check_injection_patterns(request: str, validation: ValidationStatus) -> None:
    """Check for potential injection patterns."""
    for pattern in get_injection_patterns():
        if re.search(pattern, request, re.IGNORECASE):
            validation.validation_errors.append("Potentially malicious pattern detected")
            validation.is_valid = False
            break


def add_validation_warnings(request: str, validation: ValidationStatus) -> None:
    """Add warnings for edge cases."""
    if len(request) > 5000:
        validation.warnings.append("Request is very long, processing may take longer")
    if not re.search(r'[a-zA-Z]', request):
        validation.warnings.append("Request contains no alphabetic characters")


def validate_request(request: str) -> ValidationStatus:
    """Validate and sanitize the user request."""
    validation = ValidationStatus()
    check_request_length(request, validation)
    if validation.is_valid:
        check_injection_patterns(request, validation)
    add_validation_warnings(request, validation)
    return validation