"""
DEPRECATED - Backward Compatibility Wrapper for SSOT Logging Factory
SSOT_COMPATIBILITY_WRAPPER = True

This module is DEPRECATED and maintained only for backward compatibility.
NEW CODE SHOULD IMPORT FROM: shared.logging.unified_logging_ssot

SSOT REMEDIATION: This wrapper routes all factory calls to the unified SSOT logging system,
eliminating 489+ duplicate logging patterns while maintaining compatibility.

Business Value: Prevents $500K+ ARR Golden Path debugging failures during SSOT migration.
"""

import warnings
from shared.isolated_environment import get_env
from typing import Optional, Dict, Any
import logging
import sys
import os
from pathlib import Path

# Import SSOT logging
from shared.logging.unified_logging_ssot import get_ssot_logger, get_logger as ssot_get_logger

# Issue deprecation warning
warnings.warn(
    "shared.logging.unified_logger_factory is deprecated. "
    "Use 'from shared.logging.unified_logging_ssot import get_logger' instead.",
    DeprecationWarning,
    stacklevel=2
)


class UnifiedLoggerFactory:
    """
    DEPRECATED - Backward compatibility wrapper for SSOT logging.
    
    All methods now delegate to shared.logging.unified_logging_ssot.
    This maintains compatibility while eliminating duplicate logging patterns.
    """
    
    _initialized = False
    _loggers: Dict[str, logging.Logger] = {}
    _base_config: Optional[Dict[str, Any]] = None
    
    @classmethod
    def _ensure_base_initialization(cls) -> None:
        """DEPRECATED: SSOT handles initialization automatically."""
        pass  # SSOT handles initialization
    
    @classmethod
    def get_logger(cls, name: Optional[str] = None) -> logging.Logger:
        """
        DEPRECATED: Delegate to SSOT logging system.
        
        Use 'from shared.logging.unified_logging_ssot import get_logger' instead.
        """
        # Delegate to SSOT
        ssot_logger = ssot_get_logger(name)
        
        # Return a stdlib-compatible wrapper for backward compatibility
        class StdlibLoggerWrapper:
            def __init__(self, ssot_logger):
                self._ssot = ssot_logger
                
            def debug(self, msg, *args, **kwargs):
                self._ssot.debug(str(msg))
            
            def info(self, msg, *args, **kwargs):
                self._ssot.info(str(msg))
                
            def warning(self, msg, *args, **kwargs):
                self._ssot.warning(str(msg))
                
            def error(self, msg, *args, **kwargs):
                self._ssot.error(str(msg))
                
            def critical(self, msg, *args, **kwargs):
                self._ssot.critical(str(msg))
                
            def setLevel(self, level):
                pass  # SSOT handles level configuration
                
        # Cache wrapper for consistency
        if name not in cls._loggers:
            cls._loggers[name] = StdlibLoggerWrapper(ssot_logger)
            
        return cls._loggers[name]
    
    @classmethod
    def configure_for_service(cls, service_config: Optional[Dict[str, Any]] = None) -> None:
        """DEPRECATED: SSOT handles service configuration automatically."""
        pass  # SSOT handles configuration
    
    @classmethod
    def reset(cls) -> None:
        """DEPRECATED: Use shared.logging.unified_logging_ssot.reset_logging instead."""
        from shared.logging.unified_logging_ssot import reset_logging
        reset_logging()
        cls._initialized = False
        cls._loggers.clear()
        cls._base_config = None


# Global convenience functions for backward compatibility
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    DEPRECATED: Get a unified logger instance via SSOT delegation.
    
    NEW CODE SHOULD USE: from shared.logging.unified_logging_ssot import get_logger
    
    This function maintains backward compatibility by delegating to SSOT.
    """
    return UnifiedLoggerFactory.get_logger(name)


def configure_service_logging(service_config: Optional[Dict[str, Any]] = None) -> None:
    """DEPRECATED: SSOT handles service configuration automatically."""
    # SSOT handles configuration automatically
    pass


def reset_logging() -> None:
    """DEPRECATED: Reset logging configuration via SSOT."""
    from shared.logging.unified_logging_ssot import reset_logging as ssot_reset
    ssot_reset()
    UnifiedLoggerFactory.reset()
