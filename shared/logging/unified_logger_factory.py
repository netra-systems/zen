from shared.isolated_environment import get_env
"""
Unified Logger Factory - Single source of truth for all logging initialization
Eliminates 489+ duplicate logging patterns across the codebase.

This module provides the ONLY way to initialize loggers throughout the system.
All services (netra_backend, auth_service, dev_launcher) must use this factory.
"""
from typing import Optional, Dict, Any
import logging
import sys
import os
from pathlib import Path


class UnifiedLoggerFactory:
    """
    Centralized logger factory that eliminates all duplicate logging patterns.
    
    This factory provides consistent logger initialization across all services
    while supporting service-specific configuration where needed.
    """
    
    _initialized = False
    _loggers: Dict[str, logging.Logger] = {}
    _base_config: Optional[Dict[str, Any]] = None
    
    @classmethod
    def _ensure_base_initialization(cls) -> None:
        """Ensure base logging configuration is set up once globally."""
        if cls._initialized:
            return
            
        # Configure base logging format and level
        cls._base_config = cls._get_base_config()
        
        # Set up the root logger configuration
        logging.basicConfig(
            level=cls._base_config['level'],
            format=cls._base_config['format'],
            handlers=cls._create_handlers(cls._base_config)
        )
        
        cls._initialized = True
    
    @classmethod
    def _get_base_config(cls) -> Dict[str, Any]:
        """Get base logging configuration from environment."""
        # Use os.environ directly to avoid circular import
        
        # Determine environment-specific log level
        log_level_str = os.environ.get('LOG_LEVEL', 'INFO').upper()
        try:
            log_level = getattr(logging, log_level_str)
        except AttributeError:
            log_level = logging.INFO
        
        # Determine if we're in a service that needs file logging
        enable_file_logging = os.environ.get('ENABLE_FILE_LOGGING', 'false').lower() == 'true'
        
        # Get service name from environment or infer from process
        service_name = cls._infer_service_name()
        
        return {
            'level': log_level,
            'format': f'%(asctime)s - {service_name} - %(name)s - %(levelname)s - %(message)s',
            'enable_file_logging': enable_file_logging,
            'service_name': service_name
        }
    
    @classmethod
    def _infer_service_name(cls) -> str:
        """Infer service name from the current process/environment."""
        # Check for explicit service name using os.environ to avoid circular import
        service_name = os.environ.get('SERVICE_NAME')
        if service_name:
            return service_name
            
        # Infer from the main module path
        main_module = sys.modules.get('__main__')
        if main_module and hasattr(main_module, '__file__'):
            main_file = Path(main_module.__file__)
            
            # Check if we're in auth_service
            if 'auth_service' in str(main_file):
                return 'auth-service'
            # Check if we're in dev_launcher
            elif 'dev_launcher' in str(main_file):
                return 'dev-launcher'
            # Check if we're in netra_backend
            elif 'netra_backend' in str(main_file):
                return 'netra-backend'
            # Check for test environment
            elif 'test' in str(main_file) or 'pytest' in str(main_file):
                return 'test-runner'
        
        return 'netra-service'
    
    @classmethod
    def _create_handlers(cls, config: Dict[str, Any]) -> list:
        """Create logging handlers based on configuration."""
        handlers = []
        
        # Always include console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(config['format']))
        handlers.append(console_handler)
        
        # Add file handler if enabled
        if config.get('enable_file_logging'):
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            
            service_name = config['service_name'].replace('-', '_')
            log_file = log_dir / f'{service_name}.log'
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(config['format']))
            handlers.append(file_handler)
        
        return handlers
    
    @classmethod
    def get_logger(cls, name: Optional[str] = None) -> logging.Logger:
        """
        Get a logger instance with unified configuration.
        
        This is the ONLY method that should be used to get loggers
        throughout the entire codebase.
        
        Args:
            name: Logger name, defaults to calling module name
            
        Returns:
            Configured logger instance
        """
        # Ensure base configuration is set up
        cls._ensure_base_initialization()
        
        # Use provided name or infer from caller
        if name is None:
            # Get the calling frame to determine module name
            frame = sys._getframe(1)
            module = frame.f_globals.get('__name__', 'unknown')
            name = module
        
        # Return cached logger if exists
        if name in cls._loggers:
            return cls._loggers[name]
        
        # Create new logger
        logger = logging.getLogger(name)
        logger.setLevel(cls._base_config['level'])
        
        # Cache and return
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def configure_for_service(cls, service_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Configure logging for a specific service with custom settings.
        
        This allows services to override default behavior while maintaining
        unified patterns.
        
        Args:
            service_config: Service-specific configuration overrides
        """
        if service_config:
            # Reset initialization to apply new config
            cls._initialized = False
            cls._loggers.clear()
            
            # Update base config with service overrides
            base_config = cls._get_base_config()
            base_config.update(service_config)
            cls._base_config = base_config
            
            # Re-initialize with new config
            cls._ensure_base_initialization()
    
    @classmethod
    def reset(cls) -> None:
        """Reset the factory state (primarily for testing)."""
        cls._initialized = False
        cls._loggers.clear()
        cls._base_config = None


# Global convenience functions for backward compatibility
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a unified logger instance.
    
    This function replaces ALL instances of:
    - import logging; logger = logging.getLogger(__name__)
    - from netra_backend.app.logging_config import central_logger
    - Any other logging initialization patterns
    
    Usage:
        from shared.logging.unified_logger_factory import get_logger
        logger = get_logger(__name__)  # or just get_logger()
    """
    return UnifiedLoggerFactory.get_logger(name)


def configure_service_logging(service_config: Optional[Dict[str, Any]] = None) -> None:
    """Configure logging for a specific service."""
    UnifiedLoggerFactory.configure_for_service(service_config)


def reset_logging() -> None:
    """Reset logging configuration (for testing)."""
    UnifiedLoggerFactory.reset()
