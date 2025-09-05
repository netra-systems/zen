"""Token Optimization Package

This package provides production-ready token optimization functionality for the Netra platform,
with complete SSOT compliance, user isolation, and frozen dataclass respect.

Key Components:
- TokenOptimizationIntegrationService: Main interface for all token optimization
- TokenOptimizationContextManager: Immutable context management
- TokenOptimizationSessionFactory: User-isolated session management
- TokenOptimizationConfigManager: Configuration-driven settings

All components respect architectural constraints and deliver business value through
cost optimization and real-time token usage analytics.
"""

from netra_backend.app.services.token_optimization.integration_service import TokenOptimizationIntegrationService
from netra_backend.app.services.token_optimization.context_manager import TokenOptimizationContextManager
from netra_backend.app.services.token_optimization.session_factory import TokenOptimizationSessionFactory
from netra_backend.app.services.token_optimization.config_manager import TokenOptimizationConfigManager

__all__ = [
    "TokenOptimizationIntegrationService",
    "TokenOptimizationContextManager", 
    "TokenOptimizationSessionFactory",
    "TokenOptimizationConfigManager"
]

__version__ = "1.0.0"
__author__ = "Netra Platform Team"