"""
Single Source of Truth (SSOT) Orchestration Configuration Module

This module provides the unified OrchestrationConfig that manages all orchestration
availability checks across the entire test suite. It eliminates SSOT violations
and orchestration availability duplication.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
Ensures consistent orchestration availability determination, proper feature flagging, and reliable module loading.

CRITICAL: This is the ONLY source for orchestration availability checks in the system.
ALL orchestration modules must use OrchestrationConfig for availability determination.

Key Features:
- Centralized availability checking for all orchestration components
- Lazy loading pattern with proper error handling
- Thread-safe availability caching
- Graceful degradation when imports fail
- Environment-based configuration override
- Comprehensive availability reporting

Availability Properties:
- orchestrator_available: TestOrchestratorAgent imports
- master_orchestration_available: MasterOrchestrationController imports
- background_e2e_available: BackgroundE2EAgent imports
- all_orchestration_available: All orchestration features available
"""

import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple, Union, List
from functools import lru_cache

# Import SSOT environment management
from shared.isolated_environment import get_env

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


class OrchestrationConfig:
    """
    Single Source of Truth (SSOT) configuration for orchestration availability.
    
    This class manages all orchestration availability checks using a lazy loading
    pattern with proper caching and thread safety. It provides a centralized
    location for determining which orchestration features are available.
    
    Features:
    - Lazy loading with import error handling
    - Thread-safe availability caching
    - Environment-based override capability
    - Comprehensive availability reporting
    - Graceful degradation on import failures
    - Singleton pattern for consistent state
    
    Usage:
        config = OrchestrationConfig()
        
        if config.orchestrator_available:
            # Use TestOrchestratorAgent features
            
        if config.all_orchestration_available:
            # All orchestration features available
            
        # Get comprehensive status
        status = config.get_availability_status()
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        """Singleton pattern implementation with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(OrchestrationConfig, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize orchestration configuration with lazy loading."""
        if getattr(self, '_initialized', False):
            return
            
        with self._lock:
            if self._initialized:
                return
                
            # Environment manager
            self.env = get_env()
            
            # Availability cache - None means not yet checked
            self._availability_cache: Dict[str, Optional[bool]] = {
                'orchestrator': None,
                'master_orchestration': None,
                'background_e2e': None,
                'docker': None
            }
            
            # Import cache for loaded modules
            self._import_cache: Dict[str, Any] = {}
            
            # Error tracking
            self._import_errors: Dict[str, str] = {}
            self._last_check_time: Optional[float] = None
            
            # Configuration
            self._force_refresh = False
            self._debug_mode = self.env.get("ORCHESTRATION_DEBUG", "false").lower() == "true"
            self._no_services_mode = self.env.get("TEST_NO_SERVICES", "false").lower() == "true"
            
            self._initialized = True
            
            if self._debug_mode:
                logger.debug(f"OrchestrationConfig initialized [singleton instance]")
    
    def _get_env_override(self, feature_name: str) -> Optional[bool]:
        """
        Check for environment variable override for availability.
        
        Args:
            feature_name: Name of orchestration feature
            
        Returns:
            Environment override value or None if not set
        """
        env_var = f"ORCHESTRATION_{feature_name.upper()}_AVAILABLE"
        env_value = self.env.get(env_var)
        
        if env_value is not None:
            return env_value.lower() in ("true", "1", "yes", "on")
        
        return None
    
    def _check_orchestrator_availability(self) -> Tuple[bool, Optional[str]]:
        """
        Check TestOrchestratorAgent availability with detailed error reporting.
        
        Returns:
            Tuple of (availability, error_message)
        """
        try:
            # Try importing TestOrchestratorAgent and related components
            from test_framework.orchestration.test_orchestrator_agent import (
                TestOrchestratorAgent, 
                OrchestrationConfig as TestOrchestrationConfig, 
                ExecutionMode,
                add_orchestrator_arguments, 
                execute_with_orchestrator
            )
            
            # Cache imports for potential reuse
            self._import_cache.update({
                'TestOrchestratorAgent': TestOrchestratorAgent,
                'TestOrchestrationConfig': TestOrchestrationConfig,
                'ExecutionMode': ExecutionMode,
                'add_orchestrator_arguments': add_orchestrator_arguments,
                'execute_with_orchestrator': execute_with_orchestrator
            })
            
            if self._debug_mode:
                logger.debug("TestOrchestratorAgent imports successful")
            
            return True, None
            
        except ImportError as e:
            error_msg = f"TestOrchestratorAgent unavailable: {str(e)}"
            if self._debug_mode:
                logger.debug(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"TestOrchestratorAgent check failed: {str(e)}"
            logger.warning(error_msg)
            return False, error_msg
    
    def _check_master_orchestration_availability(self) -> Tuple[bool, Optional[str]]:
        """
        Check MasterOrchestrationController availability with detailed error reporting.
        
        Returns:
            Tuple of (availability, error_message)
        """
        try:
            # Try importing MasterOrchestrationController and related components
            from test_framework.orchestration.master_orchestration_controller import (
                MasterOrchestrationController,
                OrchestrationMode,
                create_background_only_controller,
                create_hybrid_controller,
                create_legacy_controller
            )
            from test_framework.orchestration.progress_streaming_agent import ProgressOutputMode
            
            # Cache imports for potential reuse
            self._import_cache.update({
                'MasterOrchestrationController': MasterOrchestrationController,
                'OrchestrationMode': OrchestrationMode,
                'ProgressOutputMode': ProgressOutputMode,
                'create_background_only_controller': create_background_only_controller,
                'create_hybrid_controller': create_hybrid_controller,
                'create_legacy_controller': create_legacy_controller
            })
            
            if self._debug_mode:
                logger.debug("MasterOrchestrationController imports successful")
            
            return True, None
            
        except ImportError as e:
            error_msg = f"MasterOrchestrationController unavailable: {str(e)}"
            if self._debug_mode:
                logger.debug(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"MasterOrchestrationController check failed: {str(e)}"
            logger.warning(error_msg)
            return False, error_msg
    
    def _check_background_e2e_availability(self) -> Tuple[bool, Optional[str]]:
        """
        Check BackgroundE2EAgent availability with detailed error reporting.
        
        Returns:
            Tuple of (availability, error_message)
        """
        try:
            # Try importing BackgroundE2EAgent and related components
            from test_framework.orchestration.background_e2e_agent import (
                BackgroundE2EAgent,
                E2ETestCategory,
                BackgroundTaskConfig,
                add_background_e2e_arguments,
                handle_background_e2e_commands
            )
            
            # Cache imports for potential reuse
            self._import_cache.update({
                'BackgroundE2EAgent': BackgroundE2EAgent,
                'E2ETestCategory': E2ETestCategory,
                'BackgroundTaskConfig': BackgroundTaskConfig,
                'add_background_e2e_arguments': add_background_e2e_arguments,
                'handle_background_e2e_commands': handle_background_e2e_commands
            })
            
            if self._debug_mode:
                logger.debug("BackgroundE2EAgent imports successful")
            
            return True, None
            
        except ImportError as e:
            error_msg = f"BackgroundE2EAgent unavailable: {str(e)}"
            if self._debug_mode:
                logger.debug(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"BackgroundE2EAgent check failed: {str(e)}"
            logger.warning(error_msg)
            return False, error_msg

    def _check_docker_availability(self) -> Tuple[bool, Optional[str]]:
        """
        Check Docker availability with detailed error reporting.

        Returns:
            Tuple of (availability, error_message)
        """
        try:
            import docker
            client = docker.from_env()
            client.ping()

            if self._debug_mode:
                logger.debug("Docker service available and responding")

            return True, None

        except ImportError as e:
            error_msg = f"Docker library unavailable: {str(e)}"
            if self._debug_mode:
                logger.debug(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Docker service unavailable: {str(e)}"
            if self._debug_mode:
                logger.debug(error_msg)
            return False, error_msg

    def _check_service_availability(self, service_name: str, host: str = "localhost", port: int = None, timeout: float = 2.0) -> Tuple[bool, Optional[str]]:
        """
        Check if a specific service is available and responding.
        
        Args:
            service_name: Name of the service (for logging)
            host: Service host (default: localhost)
            port: Service port
            timeout: Connection timeout in seconds
            
        Returns:
            Tuple of (availability, error_message)
        """
        if port is None:
            return False, f"No port specified for {service_name}"
            
        try:
            import socket
            with socket.create_connection((host, port), timeout=timeout):
                if self._debug_mode:
                    logger.debug(f"Service {service_name} available at {host}:{port}")
                return True, None
                
        except (socket.timeout, socket.error, ConnectionRefusedError, OSError) as e:
            error_msg = f"Service {service_name} unavailable at {host}:{port}: {str(e)}"
            if self._debug_mode:
                logger.debug(error_msg)
            return False, error_msg

    def _check_availability(self, feature_name: str) -> bool:
        """
        Internal method to check and cache availability for a specific feature.
        
        Args:
            feature_name: Name of orchestration feature to check
            
        Returns:
            True if feature is available
        """
        # Check environment override first
        env_override = self._get_env_override(feature_name)
        if env_override is not None:
            self._availability_cache[feature_name] = env_override
            if self._debug_mode:
                logger.debug(f"Using environment override for {feature_name}: {env_override}")
            return env_override
        
        # Check if already cached and not forced refresh
        if not self._force_refresh and self._availability_cache[feature_name] is not None:
            return self._availability_cache[feature_name]
        
        # Perform actual availability check
        with self._lock:
            # Double-check pattern
            if not self._force_refresh and self._availability_cache[feature_name] is not None:
                return self._availability_cache[feature_name]
            
            try:
                if feature_name == 'orchestrator':
                    available, error = self._check_orchestrator_availability()
                elif feature_name == 'master_orchestration':
                    available, error = self._check_master_orchestration_availability()
                elif feature_name == 'background_e2e':
                    available, error = self._check_background_e2e_availability()
                elif feature_name == 'docker':
                    available, error = self._check_docker_availability()
                else:
                    available, error = False, f"Unknown feature: {feature_name}"
                
                # Cache result
                self._availability_cache[feature_name] = available
                
                # Store error if any
                if error:
                    self._import_errors[feature_name] = error
                elif feature_name in self._import_errors:
                    # Clear previous error if now available
                    del self._import_errors[feature_name]
                
                return available
                
            except Exception as e:
                logger.error(f"Unexpected error checking {feature_name} availability: {e}")
                self._availability_cache[feature_name] = False
                self._import_errors[feature_name] = str(e)
                return False
    
    @property
    def orchestrator_available(self) -> bool:
        """
        Check if TestOrchestratorAgent is available.
        
        This property tests for the availability of:
        - TestOrchestratorAgent class
        - OrchestrationConfig class
        - ExecutionMode enum
        - add_orchestrator_arguments function
        - execute_with_orchestrator function
        
        Returns:
            True if all TestOrchestratorAgent components are importable
        """
        return self._check_availability('orchestrator')
    
    @property
    def master_orchestration_available(self) -> bool:
        """
        Check if MasterOrchestrationController is available.
        
        This property tests for the availability of:
        - MasterOrchestrationController class
        - OrchestrationMode enum  
        - ProgressOutputMode enum
        - Controller factory functions
        
        Returns:
            True if all MasterOrchestrationController components are importable
        """
        return self._check_availability('master_orchestration')
    
    @property
    def background_e2e_available(self) -> bool:
        """
        Check if BackgroundE2EAgent is available.
        
        This property tests for the availability of:
        - BackgroundE2EAgent class
        - E2ETestCategory enum
        - BackgroundTaskConfig class
        - Background E2E argument and command functions
        
        Returns:
            True if all BackgroundE2EAgent components are importable
        """
        return self._check_availability('background_e2e')

    @property
    def docker_available(self) -> bool:
        """
        Check if Docker is available for testing.

        This property tests for the availability of:
        - Docker service running and responding
        - Docker Python library available

        Returns:
            True if Docker is available for test orchestration
        """
        if self._no_services_mode:
            return False  # In no-services mode, Docker is always unavailable
        return self._check_availability('docker')

    @property
    def no_services_mode(self) -> bool:
        """
        Check if running in no-services mode.
        
        In no-services mode, tests run without external service dependencies.
        This is useful for lightweight test execution in environments where
        services like Docker, databases, or other infrastructure aren't available.
        
        Returns:
            True if TEST_NO_SERVICES environment variable is set to true
        """
        return self._no_services_mode

    @property
    def all_orchestration_available(self) -> bool:
        """
        Check if ALL orchestration features are available.
        
        This is a convenience property that returns True only if:
        - TestOrchestratorAgent is available
        - MasterOrchestrationController is available  
        - BackgroundE2EAgent is available
        
        Returns:
            True if all orchestration components are available
        """
        return (
            self.orchestrator_available and 
            self.master_orchestration_available and 
            self.background_e2e_available
        )
    
    @property
    def any_orchestration_available(self) -> bool:
        """
        Check if ANY orchestration features are available.
        
        Returns:
            True if at least one orchestration component is available
        """
        return (
            self.orchestrator_available or 
            self.master_orchestration_available or 
            self.background_e2e_available
        )
    
    def get_available_features(self) -> Set[str]:
        """
        Get set of available orchestration features.
        
        Returns:
            Set of feature names that are currently available
        """
        available = set()
        
        if self.orchestrator_available:
            available.add('orchestrator')
        if self.master_orchestration_available:
            available.add('master_orchestration')
        if self.background_e2e_available:
            available.add('background_e2e')
        
        return available
    
    def get_unavailable_features(self) -> Set[str]:
        """
        Get set of unavailable orchestration features.
        
        Returns:
            Set of feature names that are currently unavailable
        """
        unavailable = set()
        
        if not self.orchestrator_available:
            unavailable.add('orchestrator')
        if not self.master_orchestration_available:
            unavailable.add('master_orchestration')
        if not self.background_e2e_available:
            unavailable.add('background_e2e')
        
        return unavailable
    
    def get_import_errors(self) -> Dict[str, str]:
        """
        Get dictionary of import errors for unavailable features.
        
        Returns:
            Dictionary mapping feature names to error messages
        """
        return self._import_errors.copy()
    
    def get_cached_import(self, import_name: str) -> Optional[Any]:
        """
        Get a cached import if available.
        
        Args:
            import_name: Name of cached import to retrieve
            
        Returns:
            Cached import object or None if not cached
        """
        return self._import_cache.get(import_name)
    
    def refresh_availability(self, force: bool = False):
        """
        Refresh availability checks, optionally forcing re-check.
        
        Args:
            force: If True, ignore cache and re-check all availability
        """
        if force:
            with self._lock:
                self._force_refresh = True
                self._availability_cache = {k: None for k in self._availability_cache}
                self._import_errors.clear()
                self._import_cache.clear()
                
                # Trigger re-check of all features
                _ = self.orchestrator_available
                _ = self.master_orchestration_available
                _ = self.background_e2e_available
                
                self._force_refresh = False
                
                if self._debug_mode:
                    logger.debug("Orchestration availability refreshed (forced)")
    
    def get_availability_status(self) -> Dict[str, Any]:
        """
        Get comprehensive availability status report.
        
        Returns:
            Dictionary with detailed availability information
        """
        return {
            "orchestrator_available": self.orchestrator_available,
            "master_orchestration_available": self.master_orchestration_available,
            "background_e2e_available": self.background_e2e_available,
            "all_orchestration_available": self.all_orchestration_available,
            "any_orchestration_available": self.any_orchestration_available,
            "available_features": list(self.get_available_features()),
            "unavailable_features": list(self.get_unavailable_features()),
            "import_errors": self.get_import_errors(),
            "cached_imports": list(self._import_cache.keys()),
            "environment_overrides": {
                f"ORCHESTRATION_{name.upper()}_AVAILABLE": self._get_env_override(name)
                for name in ['orchestrator', 'master_orchestration', 'background_e2e']
                if self._get_env_override(name) is not None
            },
            "debug_mode": self._debug_mode
        }
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """
        Get service-specific configuration for orchestration components.

        This method provides configuration settings specific to individual services
        within the orchestration system. It follows SSOT patterns by providing
        a centralized location for service configuration management.

        Args:
            service_name: Name of service to get configuration for
                         (e.g., 'orchestrator', 'master_orchestration', 'background_e2e')

        Returns:
            Dictionary containing service-specific configuration

        Raises:
            ValueError: If service_name is not recognized
        """
        # Define known service configurations
        service_configs = {
            'orchestrator': {
                'availability_key': 'orchestrator',
                'import_modules': [
                    'test_framework.orchestration.test_orchestrator_agent',
                ],
                'required_classes': [
                    'TestOrchestratorAgent',
                    'OrchestrationConfig',
                    'ExecutionMode'
                ],
                'timeout_seconds': 30,
                'retry_attempts': 3,
                'environment_vars': [
                    'ORCHESTRATION_ORCHESTRATOR_AVAILABLE'
                ]
            },
            'master_orchestration': {
                'availability_key': 'master_orchestration',
                'import_modules': [
                    'test_framework.orchestration.master_orchestration_controller',
                    'test_framework.orchestration.progress_streaming_agent'
                ],
                'required_classes': [
                    'MasterOrchestrationController',
                    'OrchestrationMode',
                    'ProgressOutputMode'
                ],
                'timeout_seconds': 60,
                'retry_attempts': 2,
                'environment_vars': [
                    'ORCHESTRATION_MASTER_ORCHESTRATION_AVAILABLE'
                ]
            },
            'background_e2e': {
                'availability_key': 'background_e2e',
                'import_modules': [
                    'test_framework.orchestration.background_e2e_agent'
                ],
                'required_classes': [
                    'BackgroundE2EAgent',
                    'E2ETestCategory',
                    'BackgroundTaskConfig'
                ],
                'timeout_seconds': 90,
                'retry_attempts': 1,
                'environment_vars': [
                    'ORCHESTRATION_BACKGROUND_E2E_AVAILABLE'
                ]
            }
        }

        # Validate service name
        if service_name not in service_configs:
            available_services = list(service_configs.keys())
            raise ValueError(
                f"Unknown service '{service_name}'. "
                f"Available services: {available_services}"
            )

        # Get base configuration
        base_config = service_configs[service_name].copy()

        # Add dynamic configuration from environment and availability status
        base_config.update({
            'available': self._check_availability(service_name),
            'cached_imports': {
                name: obj for name, obj in self._import_cache.items()
                if any(cls in name for cls in base_config['required_classes'])
            },
            'last_error': self._import_errors.get(service_name),
            'environment_override': self._get_env_override(service_name),
            'debug_mode': self._debug_mode
        })

        # Add environment-specific settings
        if service_name in ['background_e2e']:
            # Background E2E needs longer timeouts and specific resource limits
            base_config.update({
                'resource_limits': {
                    'memory_gb': 4,
                    'cpu_percent': 80,
                    'disk_gb': 10
                },
                'background_eligible': True
            })
        elif service_name in ['orchestrator']:
            # Orchestrator needs rapid response times
            base_config.update({
                'resource_limits': {
                    'memory_gb': 1,
                    'cpu_percent': 40,
                    'disk_gb': 2
                },
                'background_eligible': False
            })

        if self._debug_mode:
            logger.debug(f"Generated service config for {service_name}: {len(base_config)} keys")

        return base_config

    def validate_configuration(self) -> List[str]:
        """
        Validate orchestration configuration and return any issues found.

        Returns:
            List of configuration issues (empty list if all valid)
        """
        issues = []

        # Check for basic availability
        if not self.any_orchestration_available:
            issues.append("No orchestration features are available - all imports failed")

        # Check for partial availability that might indicate issues
        available_count = len(self.get_available_features())
        if 0 < available_count < 3:
            issues.append(f"Only {available_count}/3 orchestration features available - may indicate import issues")

        # Check for import errors
        errors = self.get_import_errors()
        if errors:
            for feature, error in errors.items():
                issues.append(f"Import error for {feature}: {error}")

        # Check environment consistency
        env_overrides = {}
        for name in ['orchestrator', 'master_orchestration', 'background_e2e']:
            override = self._get_env_override(name)
            if override is not None:
                env_overrides[name] = override

        if env_overrides:
            issues.append(f"Environment overrides active: {env_overrides}")

        return issues
    
    def __repr__(self) -> str:
        """String representation of orchestration config."""
        available = self.get_available_features()
        return f"OrchestrationConfig(available={available})"


# ========== Global Orchestration Configuration Management ==========

# Global singleton instance
_global_orchestration_config: Optional[OrchestrationConfig] = None
_global_config_lock = threading.RLock()


def get_orchestration_config() -> OrchestrationConfig:
    """
    Get global orchestration configuration instance (singleton).
    
    This function provides access to the singleton OrchestrationConfig instance
    that maintains consistent availability state across the entire application.
    
    Returns:
        OrchestrationConfig singleton instance
    """
    global _global_orchestration_config
    
    if _global_orchestration_config is None:
        with _global_config_lock:
            if _global_orchestration_config is None:
                _global_orchestration_config = OrchestrationConfig()
    
    return _global_orchestration_config


def refresh_global_orchestration_config(force: bool = False):
    """
    Refresh the global orchestration configuration.
    
    Args:
        force: If True, force re-check of all availability
    """
    config = get_orchestration_config()
    config.refresh_availability(force=force)


def validate_global_orchestration_config() -> List[str]:
    """
    Validate the global orchestration configuration.
    
    Returns:
        List of configuration issues found
    """
    config = get_orchestration_config()
    return config.validate_configuration()


# ========== Convenience Functions ==========

def is_orchestrator_available() -> bool:
    """Convenience function to check orchestrator availability."""
    return get_orchestration_config().orchestrator_available


def is_master_orchestration_available() -> bool:
    """Convenience function to check master orchestration availability."""
    return get_orchestration_config().master_orchestration_available


def is_background_e2e_available() -> bool:
    """Convenience function to check background E2E availability."""
    return get_orchestration_config().background_e2e_available


def is_docker_available() -> bool:
    """Convenience function to check Docker availability."""
    return get_orchestration_config().docker_available


def is_all_orchestration_available() -> bool:
    """Convenience function to check if all orchestration is available."""
    return get_orchestration_config().all_orchestration_available


def get_orchestration_status() -> Dict[str, Any]:
    """Convenience function to get orchestration status."""
    return get_orchestration_config().get_availability_status()


def is_no_services_mode() -> bool:
    """Convenience function to check if running in no-services mode."""
    return get_orchestration_config().no_services_mode


def check_service_available(service_name: str, host: str = "localhost", port: int = None, timeout: float = 2.0) -> bool:
    """
    Convenience function to check if a specific service is available.
    
    Args:
        service_name: Name of the service (for logging)
        host: Service host (default: localhost)
        port: Service port
        timeout: Connection timeout in seconds
        
    Returns:
        True if service is available and responding
    """
    config = get_orchestration_config()
    available, _ = config._check_service_availability(service_name, host, port, timeout)
    return available


# Create global singleton instance for easy importing
orchestration_config = get_orchestration_config()


# Export SSOT orchestration configuration
__all__ = [
    'OrchestrationConfig',
    'orchestration_config',
    'get_orchestration_config',
    'refresh_global_orchestration_config',
    'validate_global_orchestration_config',
    'is_orchestrator_available',
    'is_master_orchestration_available',
    'is_background_e2e_available',
    'is_docker_available',
    'is_all_orchestration_available',
    'get_orchestration_status',
    'is_no_services_mode',
    'check_service_available'
]