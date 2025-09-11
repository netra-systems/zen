"""
DEPRECATED - Backward Compatibility Wrapper for Cloud Run Logging
SSOT_COMPATIBILITY_WRAPPER = True

This module is DEPRECATED and maintained only for backward compatibility.
NEW CODE SHOULD IMPORT FROM: shared.logging.unified_logging_ssot

SSOT REMEDIATION: Cloud Run logging configuration is now integrated into 
the unified SSOT logging system, eliminating duplicate configuration.

Business Value: Prevents $500K+ ARR Golden Path failures caused by
Cloud Run logging configuration conflicts during SSOT migration.
"""

import sys
import logging
import warnings
from shared.isolated_environment import IsolatedEnvironment

# Import SSOT logging
from shared.logging.unified_logging_ssot import get_ssot_logger

# Issue deprecation warning
warnings.warn(
    "netra_backend.app.core.logging_config is deprecated. "
    "Cloud Run logging is now handled by shared.logging.unified_logging_ssot.",
    DeprecationWarning,
    stacklevel=2
)


def configure_cloud_run_logging():
    """
    DEPRECATED: Cloud Run configuration is now handled by SSOT logging system.
    
    This function maintains backward compatibility by triggering SSOT initialization
    which includes all Cloud Run optimizations automatically.
    """
    # Initialize SSOT logger which handles Cloud Run configuration
    ssot_logger = get_ssot_logger()
    
    # The SSOT logger automatically handles:
    # - Cloud Run environment detection
    # - ANSI escape code prevention
    # - JSON logging for GCP Cloud Logging
    # - Exception handler setup
    # - Environment variable configuration


def setup_exception_handler():
    """
    DEPRECATED: Exception handling is now part of SSOT logging system.
    
    This function maintains backward compatibility by triggering SSOT initialization.
    """
    # SSOT logger handles exception setup automatically
    ssot_logger = get_ssot_logger()


# DEPRECATED: Initialize SSOT logging system instead
# These functions were called on module import - now delegate to SSOT
ssot_logger = get_ssot_logger()  # This triggers all initialization including Cloud Run setup