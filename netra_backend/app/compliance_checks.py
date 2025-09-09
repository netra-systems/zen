"""
Compliance Checks Module - SSOT for Compliance Check Types and Management

This module provides the missing compliance check classes that are imported
by the existing ComplianceValidator implementation.

Business Value Justification (BVJ):
- Segment: Enterprise ($500K+ ARR) customers requiring compliance
- Business Goal: Ensure regulatory compliance for security standards  
- Value Impact: Enables enterprise contracts and prevents regulatory issues
- Strategic Impact: Critical for enterprise customer acquisition and retention
"""

from typing import Dict
from netra_backend.app.security.compliance_types import (
    ComplianceCheck,
    ComplianceStatus
)

class ComplianceCheckManager:
    """Manager for compliance checks."""
    
    def __init__(self):
        """Initialize compliance check manager."""
        self.checks: Dict[str, ComplianceCheck] = {}
    
    def add_check(self, check: ComplianceCheck) -> None:
        """Add a compliance check."""
        self.checks[check.id] = check
    
    def get_check(self, check_id: str) -> ComplianceCheck:
        """Get a compliance check by ID."""
        return self.checks.get(check_id)
    
    def list_checks(self) -> Dict[str, ComplianceCheck]:
        """List all compliance checks."""
        return self.checks.copy()

# Re-export for compatibility
__all__ = [
    'ComplianceCheck',
    'ComplianceCheckManager', 
    'ComplianceStatus'
]