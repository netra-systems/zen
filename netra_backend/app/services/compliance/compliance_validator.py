"""
Compliance Validator - SSOT Import Alias for Existing Implementation

This module provides SSOT import compatibility by aliasing the existing
ComplianceValidator implementation from the security module.

Business Value Justification (BVJ):
- Segment: Enterprise ($500K+ ARR) customers requiring compliance
- Business Goal: Ensure regulatory compliance for security standards
- Value Impact: Enables enterprise contracts and prevents regulatory issues
- Strategic Impact: Critical for enterprise customer acquisition and retention
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from datetime import datetime

# SSOT Import: Use existing ComplianceValidator from security module
from netra_backend.app.security.compliance_validators import ComplianceValidator

# Additional types required by tests
class ComplianceFramework(Enum):
    """Supported compliance frameworks."""
    GDPR = "gdpr"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    ISO27001 = "iso27001"
    PCI_DSS = "pci_dss"
    CCPA = "ccpa"
    NIST = "nist"


@dataclass
class ComplianceScore:
    """Compliance score result."""
    framework: ComplianceFramework
    score: float  # 0.0 to 1.0
    max_score: float
    percentage: float
    category_scores: Dict[str, float]


@dataclass
class ComplianceViolation:
    """Compliance violation details."""
    framework: ComplianceFramework
    rule_id: str
    severity: str  # critical, high, medium, low
    description: str
    remediation_steps: List[str]
    affected_systems: List[str]


@dataclass
class ComplianceResult:
    """Comprehensive compliance validation result."""
    framework: ComplianceFramework
    overall_score: ComplianceScore
    violations: List[ComplianceViolation]
    passed_checks: int
    total_checks: int
    compliance_percentage: float
    status: str  # compliant, non_compliant, partially_compliant
    validation_timestamp: datetime
    recommendations: List[str]


# Export for test compatibility
__all__ = [
    'ComplianceValidator',
    'ComplianceFramework',
    'ComplianceResult', 
    'ComplianceScore',
    'ComplianceViolation'
]