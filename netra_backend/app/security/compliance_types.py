"""Security compliance types and enums for Netra AI Platform."""

from typing import List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


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
