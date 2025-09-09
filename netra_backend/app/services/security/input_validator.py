"""
Input Validator - SSOT Import Alias for Existing Implementation

This module provides SSOT import compatibility by aliasing the existing
InputValidator implementation from the middleware security module.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Prevent injection attacks and malicious input processing
- Value Impact: Protects user data and system integrity from security threats
- Strategic Impact: Critical for maintaining trust and regulatory compliance
"""

# SSOT Import: Use existing InputValidator from security middleware
from netra_backend.app.middleware.security_middleware import InputValidator

# Export for test compatibility
__all__ = ['InputValidator']