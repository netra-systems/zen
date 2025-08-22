"""
Core compliance check data structures and types.
Defines the foundational components for security compliance tracking.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List


class ComplianceStandard(str, Enum):
    """Security compliance standards."""
    OWASP_TOP_10 = "owasp_top_10_2021"
    NIST_CSF = "nist_cybersecurity_framework"
    ISO_27001 = "iso_27001"
    SOC2_TYPE2 = "soc2_type2"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"


class ComplianceStatus(str, Enum):
    """Compliance status types."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_APPLICABLE = "not_applicable"
    NEEDS_REVIEW = "needs_review"


@dataclass
class ComplianceCheck:
    """Individual compliance check."""
    id: str
    title: str
    description: str
    standard: ComplianceStandard
    requirement: str
    status: ComplianceStatus
    evidence: List[str]
    remediation_steps: List[str]
    priority: str  # high, medium, low
    last_checked: datetime
    next_check_date: datetime


class ComplianceCheckManager:
    """Manages compliance check collections."""
    
    def __init__(self):
        self.checks: Dict[str, ComplianceCheck] = {}
    
    def add_check(self, check: ComplianceCheck) -> None:
        """Add compliance check to collection."""
        self.checks[check.id] = check
    
    def get_check(self, check_id: str) -> ComplianceCheck:
        """Retrieve specific compliance check."""
        return self.checks.get(check_id)
    
    def get_all_checks(self) -> List[ComplianceCheck]:
        """Get all compliance checks."""
        return list(self.checks.values())
    
    def get_checks_by_standard(self, standard: ComplianceStandard) -> List[ComplianceCheck]:
        """Get all checks for specific standard."""
        return [check for check in self.checks.values() if check.standard == standard]
    
    def get_checks_by_status(self, status: ComplianceStatus) -> List[ComplianceCheck]:
        """Get all checks with specific status."""
        return [check for check in self.checks.values() if check.status == status]