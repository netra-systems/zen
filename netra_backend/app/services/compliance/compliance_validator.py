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

# SSOT Import: Use existing ComplianceValidator from security module
from netra_backend.app.security.compliance_validators import ComplianceValidator

# Export for test compatibility
__all__ = ['ComplianceValidator']