"""
Auth Service Validation Package

Provides comprehensive validation utilities for auth service deployment readiness,
configuration validation, and staging environment preparation.

This package addresses critical deployment issues identified in staging failures:
- Database connectivity and credential validation
- JWT secret consistency between services
- OAuth configuration and environment alignment
- SSL parameter compatibility for different connection types
- Container lifecycle management preparedness

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent deployment failures and reduce service downtime
- Value Impact: Eliminates configuration-related deployment issues
- Strategic Impact: Ensures reliable auth service availability across all environments
"""

from auth_service.auth_core.validation.pre_deployment_validator import (
    PreDeploymentValidator,
    main as run_validation
)

__all__ = [
    "PreDeploymentValidator",
    "run_validation"
]

__version__ = "1.0.0"