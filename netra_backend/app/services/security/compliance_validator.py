"""
Compliance Validator - SSOT Import Compatibility Module

This module provides SSOT import compatibility by re-exporting the ComplianceValidator
from its actual location in the services.compliance module.

Business Value Justification (BVJ):
- Segment: Enterprise ($500K+ ARR) customers requiring compliance
- Business Goal: Ensure regulatory compliance for security standards  
- Value Impact: Enables enterprise contracts and prevents regulatory issues
- Strategic Impact: Critical for enterprise customer acquisition and retention
"""

# SSOT Import: Re-export ComplianceValidator from its actual location
from netra_backend.app.services.compliance.compliance_validator import (
    ComplianceValidator,
    ComplianceFramework,
    ComplianceResult,
    ComplianceScore,
    ComplianceViolation
)

# Export for import compatibility
__all__ = [
    'ComplianceValidator',
    'ComplianceFramework', 
    'ComplianceResult',
    'ComplianceScore',
    'ComplianceViolation'
]