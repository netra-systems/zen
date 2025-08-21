"""Unified Configuration Management System

Enterprise-grade configuration management for Netra Apex.
Eliminates $12K MRR loss from configuration inconsistencies.

**CRITICAL: Single Source of Truth for All Configuration**

Business Value Justification (BVJ):
- Segment: Enterprise 
- Business Goal: Zero configuration-related incidents
- Value Impact: +$12K MRR from improved reliability
- Revenue Impact: Prevents data inconsistency losses

Architecture:
- base.py: Core configuration loading orchestration
- database.py: Database URL and connection management
- services.py: LLM, Redis, and external service configuration
- secrets.py: Secure secret management and rotation
- validator.py: Comprehensive configuration validation

All files ≤300 lines, all functions ≤8 lines.
"""

from netra_backend.app.base import UnifiedConfigManager
from netra_backend.app.validator import ConfigurationValidator
from netra_backend.app.secrets import SecretManager
from netra_backend.app.database import DatabaseConfigManager
from netra_backend.app.services import ServiceConfigManager
from netra_backend.app.loader import ConfigurationLoader, get_configuration, reload_configuration
from netra_backend.app.environment import EnvironmentDetector, get_environment, is_production, is_development
from netra_backend.app.unified_secrets import UnifiedSecretManager, load_secrets, get_secret

__all__ = [
    "UnifiedConfigManager",
    "ConfigurationValidator", 
    "SecretManager",
    "DatabaseConfigManager",
    "ServiceConfigManager",
    "ConfigurationLoader",
    "EnvironmentDetector",
    "UnifiedSecretManager",
    "get_configuration",
    "reload_configuration",
    "get_environment",
    "is_production",
    "is_development",
    "load_secrets",
    "get_secret"
]