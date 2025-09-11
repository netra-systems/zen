"""
Environment Context - System-wide environment detection and injection.

This package provides comprehensive environment detection and dependency injection
to eliminate environment defaults that cause Golden Path failures.

ROOT CAUSE RESOLUTION: Addresses the core architectural issue where services
default to EnvironmentType.DEVELOPMENT, causing staging services to connect
to localhost instead of proper staging endpoints.

Key Components:
- CloudEnvironmentDetector: Robust Cloud Run environment detection
- EnvironmentContextService: Dependency injection for environment-aware services  
- Integration patterns for eliminating defaults throughout the system

Business Impact: Prevents $500K+ ARR Golden Path failures by ensuring all
services receive proper environment context instead of localhost defaults.
"""

from .cloud_environment_detector import (
    CloudEnvironmentDetector,
    EnvironmentContext,
    EnvironmentType,
    CloudPlatform,
    get_cloud_environment_detector,
    detect_current_environment
)

from .environment_context_service import (
    EnvironmentContextService,
    EnvironmentAware,
    ServiceConfiguration,
    get_environment_context_service,
    initialize_environment_context,
    get_current_environment,
    get_service_url_for_current_environment
)

__all__ = [
    # Cloud Environment Detection
    "CloudEnvironmentDetector",
    "EnvironmentContext", 
    "EnvironmentType",
    "CloudPlatform",
    "get_cloud_environment_detector",
    "detect_current_environment",
    
    # Environment Context Service
    "EnvironmentContextService",
    "EnvironmentAware",
    "ServiceConfiguration", 
    "get_environment_context_service",
    "initialize_environment_context",
    "get_current_environment",
    "get_service_url_for_current_environment",
]