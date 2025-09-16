"""
CORS Configuration Module - Compatibility Layer

This module provides backward compatibility for tests and code that imports
from shared.cors_config but the actual implementation is in cors_config_builder.

This is part of Issue #1197 foundational infrastructure fixes.
"""

# Import everything from the actual CORS config builder
from shared.cors_config_builder import *

# Maintain backward compatibility - re-export key classes and functions
from shared.cors_config_builder import (
    CORSEnvironment,
    CORSConfigurationBuilder,
)

# Check what else is available in the module
try:
    from shared.cors_config_builder import CORSSecurityLevel
except ImportError:
    CORSSecurityLevel = None

try:
    from shared.cors_config_builder import DynamicCORSConfig
except ImportError:
    DynamicCORSConfig = None

try:
    from shared.cors_config_builder import CORSOriginClassification
except ImportError:
    CORSOriginClassification = None

# For tests that might expect a simple config object
def get_cors_config(environment: str = "development"):
    """
    Simple function to get CORS configuration for the given environment.
    
    Args:
        environment: Environment name (development, staging, production)
        
    Returns:
        CORSConfigurationBuilder instance configured for the environment
    """
    from shared.isolated_environment import get_env
    
    env = get_env()
    builder = CORSConfigurationBuilder()
    
    # Check what methods are available on the builder
    if hasattr(builder, 'for_staging') and environment.lower() == "staging":
        return builder.for_staging()
    elif hasattr(builder, 'for_production') and environment.lower() == "production":
        return builder.for_production()
    elif hasattr(builder, 'for_development'):
        return builder.for_development()
    else:
        # Return basic builder if specific environment methods don't exist
        return builder

# Legacy aliases if needed
CORSConfigBuilder = CORSConfigurationBuilder  # Alias for the correct class name
CorsConfig = CORSConfigurationBuilder
CorsEnvironment = CORSEnvironment

# Legacy function alias for tests expecting get_config
get_config = get_cors_config