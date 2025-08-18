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

from .base import UnifiedConfigManager
from .validator import ConfigurationValidator
from .secrets import SecretManager
from .database import DatabaseConfigManager
from .services import ServiceConfigManager

__all__ = [
    "UnifiedConfigManager",
    "ConfigurationValidator", 
    "SecretManager",
    "DatabaseConfigManager",
    "ServiceConfigManager"
]