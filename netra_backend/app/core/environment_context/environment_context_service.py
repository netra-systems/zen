"""
EnvironmentContextService - Dependency injection system for environment-aware services.

This service eliminates environment defaults by providing definitive environment context
to all components that need environment-specific configuration.

ROOT CAUSE RESOLUTION:
- Eliminates EnvironmentType.DEVELOPMENT defaults throughout the system
- Provides dependency injection pattern for environment context
- Ensures all services receive proper environment configuration
- Implements fail-fast behavior when environment cannot be determined

Business Impact: Prevents $500K+ ARR Golden Path failures by ensuring staging services
connect to staging endpoints, not localhost defaults.
"""

import asyncio
from typing import Dict, Optional, Any, Protocol, runtime_checkable
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from netra_backend.app.logging_config import central_logger
from .cloud_environment_detector import (
    CloudEnvironmentDetector, 
    EnvironmentContext, 
    EnvironmentType,
    get_cloud_environment_detector
)


@runtime_checkable 
class EnvironmentAware(Protocol):
    """Protocol for services that require environment context."""
    
    def set_environment_context(self, context: EnvironmentContext) -> None:
        """Set environment context for the service."""
        ...


@dataclass
class ServiceConfiguration:
    """Environment-specific service configuration."""
    service_urls: Dict[str, str] = field(default_factory=dict)
    timeouts: Dict[str, float] = field(default_factory=dict)
    retry_settings: Dict[str, Any] = field(default_factory=dict)
    feature_flags: Dict[str, bool] = field(default_factory=dict)
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get URL for a specific service."""
        return self.service_urls.get(service_name)
    
    def get_timeout(self, operation: str, default: float = 10.0) -> float:
        """Get timeout for a specific operation."""
        return self.timeouts.get(operation, default)


class EnvironmentContextService:
    """
    Centralized service for environment context management and injection.
    
    CRITICAL FEATURES:
    - Eliminates all environment defaults throughout the system
    - Provides definitive environment context via dependency injection
    - Generates environment-specific configurations
    - Implements fail-fast when environment cannot be determined
    - Caches context and configurations for performance
    """
    
    def __init__(self, detector: Optional[CloudEnvironmentDetector] = None):
        self.logger = central_logger.get_logger(__name__)
        self.detector = detector or get_cloud_environment_detector()
        self._context: Optional[EnvironmentContext] = None
        self._service_configs: Dict[EnvironmentType, ServiceConfiguration] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize the service with environment detection.
        
        CRITICAL: This method MUST be called during application startup
        to ensure environment context is available for all services.
        
        Raises:
            RuntimeError: When environment cannot be determined
        """
        if self._initialized:
            self.logger.debug("EnvironmentContextService already initialized")
            return
        
        self.logger.info("Initializing EnvironmentContextService with environment detection")
        
        # Detect environment context (will raise RuntimeError if unable to determine)
        self._context = await self.detector.detect_environment_context()
        
        # Pre-generate service configurations for the detected environment
        self._generate_service_configurations()
        
        self._initialized = True
        
        self.logger.info(
            f"EnvironmentContextService initialized successfully. "
            f"Environment: {self._context.environment_type.value}, "
            f"Platform: {self._context.cloud_platform.value}"
        )
    
    def get_environment_context(self) -> EnvironmentContext:
        """
        Get current environment context.
        
        Returns:
            Current environment context
            
        Raises:
            RuntimeError: If service not initialized or environment unknown
        """
        if not self._initialized:
            raise RuntimeError(
                "EnvironmentContextService not initialized. Call initialize() during application startup."
            )
        
        if not self._context:
            raise RuntimeError(
                "Environment context not available. Environment detection may have failed."
            )
        
        return self._context
    
    def get_service_configuration(self, service_type: Optional[str] = None) -> ServiceConfiguration:
        """
        Get service configuration for current environment.
        
        Args:
            service_type: Optional specific service type for specialized config
            
        Returns:
            ServiceConfiguration for current environment
            
        Raises:
            RuntimeError: If service not initialized
        """
        context = self.get_environment_context()
        
        config = self._service_configs.get(context.environment_type)
        if not config:
            # Fallback: generate on demand
            config = self._create_service_configuration_for_environment(context.environment_type)
            self._service_configs[context.environment_type] = config
        
        return config
    
    def inject_environment_context(self, service: Any) -> Any:
        """
        Inject environment context into a service.
        
        Args:
            service: Service instance that implements EnvironmentAware protocol
            
        Returns:
            The service instance with environment context injected
            
        Raises:
            RuntimeError: If service not initialized
            ValueError: If service doesn't support environment injection
        """
        context = self.get_environment_context()
        
        if hasattr(service, 'set_environment_context'):
            service.set_environment_context(context)
            self.logger.debug(f"Injected environment context into {service.__class__.__name__}")
        elif isinstance(service, EnvironmentAware):
            service.set_environment_context(context)
            self.logger.debug(f"Injected environment context into {service.__class__.__name__}")
        else:
            raise ValueError(
                f"Service {service.__class__.__name__} does not implement environment context injection. "
                f"Add set_environment_context method or implement EnvironmentAware protocol."
            )
        
        return service
    
    @asynccontextmanager
    async def get_environment_aware_service(self, service_class, *args, **kwargs):
        """
        Context manager for creating environment-aware services.
        
        Args:
            service_class: Service class to instantiate
            *args, **kwargs: Arguments for service constructor
            
        Yields:
            Service instance with environment context injected
        """
        # Ensure we're initialized
        if not self._initialized:
            await self.initialize()
        
        # Create service instance
        service = service_class(*args, **kwargs)
        
        # Inject environment context
        try:
            self.inject_environment_context(service)
            yield service
        finally:
            # Cleanup if service has cleanup method
            if hasattr(service, 'cleanup'):
                try:
                    if asyncio.iscoroutinefunction(service.cleanup):
                        await service.cleanup()
                    else:
                        service.cleanup()
                except Exception as e:
                    self.logger.warning(f"Error during service cleanup: {e}")
    
    def create_environment_specific_instance(self, factory_func, *args, **kwargs):
        """
        Create an instance using environment-specific parameters.
        
        Args:
            factory_func: Factory function that accepts environment_type parameter
            *args, **kwargs: Additional arguments for factory function
            
        Returns:
            Instance created with correct environment type
            
        Raises:
            RuntimeError: If service not initialized
        """
        context = self.get_environment_context()
        
        # Convert our EnvironmentType to the expected format
        if hasattr(context.environment_type, 'value'):
            env_value = context.environment_type.value
        else:
            env_value = str(context.environment_type)
        
        # Call factory function with environment type
        return factory_func(*args, environment_type=env_value, **kwargs)
    
    def _generate_service_configurations(self) -> None:
        """Generate service configurations for all environments."""
        for env_type in EnvironmentType:
            if env_type != EnvironmentType.UNKNOWN:
                self._service_configs[env_type] = self._create_service_configuration_for_environment(env_type)
    
    def _create_service_configuration_for_environment(self, environment_type: EnvironmentType) -> ServiceConfiguration:
        """
        Create service configuration for specific environment.
        
        Args:
            environment_type: Target environment type
            
        Returns:
            ServiceConfiguration with environment-specific settings
        """
        if environment_type == EnvironmentType.TESTING:
            return ServiceConfiguration(
                service_urls={
                    "auth_service": "http://localhost:8081",
                    "backend_service": "http://localhost:8000"
                },
                timeouts={
                    "health_check": 2.0,
                    "api_call": 5.0,
                    "websocket_connect": 3.0
                },
                retry_settings={
                    "max_retries": 3,
                    "retry_delay": 0.5
                },
                feature_flags={
                    "enable_debug_logging": True,
                    "strict_validation": False
                }
            )
        
        elif environment_type == EnvironmentType.DEVELOPMENT:
            return ServiceConfiguration(
                service_urls={
                    "auth_service": "http://localhost:8081",
                    "backend_service": "http://localhost:8000"
                },
                timeouts={
                    "health_check": 5.0,
                    "api_call": 10.0,
                    "websocket_connect": 5.0
                },
                retry_settings={
                    "max_retries": 5,
                    "retry_delay": 1.0
                },
                feature_flags={
                    "enable_debug_logging": True,
                    "strict_validation": True
                }
            )
        
        elif environment_type == EnvironmentType.STAGING:
            return ServiceConfiguration(
                service_urls={
                    "auth_service": "https://auth.staging.netrasystems.ai",
                    "backend_service": "https://api.staging.netrasystems.ai"
                },
                timeouts={
                    "health_check": 15.0,
                    "api_call": 30.0,
                    "websocket_connect": 10.0
                },
                retry_settings={
                    "max_retries": 10,
                    "retry_delay": 2.0
                },
                feature_flags={
                    "enable_debug_logging": False,
                    "strict_validation": True
                }
            )
        
        elif environment_type == EnvironmentType.PRODUCTION:
            return ServiceConfiguration(
                service_urls={
                    "auth_service": "https://auth.netrasystems.ai",
                    "backend_service": "https://api.netrasystems.ai"
                },
                timeouts={
                    "health_check": 30.0,
                    "api_call": 45.0,
                    "websocket_connect": 15.0
                },
                retry_settings={
                    "max_retries": 15,
                    "retry_delay": 3.0
                },
                feature_flags={
                    "enable_debug_logging": False,
                    "strict_validation": True
                }
            )
        
        else:
            # Fallback for unknown environments
            self.logger.warning(f"Creating fallback configuration for unknown environment: {environment_type}")
            return ServiceConfiguration(
                service_urls={
                    "auth_service": "http://localhost:8081",
                    "backend_service": "http://localhost:8000"
                },
                timeouts={
                    "health_check": 10.0,
                    "api_call": 20.0,
                    "websocket_connect": 5.0
                },
                retry_settings={
                    "max_retries": 5,
                    "retry_delay": 1.0
                },
                feature_flags={
                    "enable_debug_logging": True,
                    "strict_validation": False
                }
            )
    
    def is_initialized(self) -> bool:
        """Check if the service has been initialized."""
        return self._initialized
    
    def get_environment_type(self) -> EnvironmentType:
        """Get the current environment type."""
        context = self.get_environment_context()
        return context.environment_type
    
    def get_service_url(self, service_name: str) -> str:
        """
        Get service URL for current environment.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service URL for current environment
            
        Raises:
            RuntimeError: If service not initialized
            ValueError: If service URL not configured
        """
        config = self.get_service_configuration()
        url = config.get_service_url(service_name)
        
        if not url:
            raise ValueError(
                f"Service URL not configured for '{service_name}' in environment "
                f"'{self.get_environment_type().value}'"
            )
        
        return url
    
    async def validate_environment_context(self) -> Dict[str, Any]:
        """
        Validate current environment context and configuration.
        
        Returns:
            Validation result with status and details
        """
        validation_result = {
            "valid": True,
            "environment_type": None,
            "cloud_platform": None,
            "issues": [],
            "warnings": []
        }
        
        try:
            # Check if initialized
            if not self._initialized:
                validation_result["valid"] = False
                validation_result["issues"].append("EnvironmentContextService not initialized")
                return validation_result
            
            # Get context
            context = self.get_environment_context()
            validation_result["environment_type"] = context.environment_type.value
            validation_result["cloud_platform"] = context.cloud_platform.value
            
            # Validate confidence score
            if context.confidence_score < 0.7:
                validation_result["valid"] = False
                validation_result["issues"].append(
                    f"Low confidence environment detection: {context.confidence_score:.2f}"
                )
            
            # Validate service configuration
            config = self.get_service_configuration()
            
            # Check if critical service URLs are configured
            critical_services = ["auth_service", "backend_service"]
            for service_name in critical_services:
                url = config.get_service_url(service_name)
                if not url:
                    validation_result["valid"] = False
                    validation_result["issues"].append(f"Missing URL for {service_name}")
                elif context.environment_type == EnvironmentType.STAGING and "localhost" in url:
                    validation_result["valid"] = False
                    validation_result["issues"].append(
                        f"{service_name} URL uses localhost in staging environment: {url}"
                    )
                elif context.environment_type == EnvironmentType.PRODUCTION and ("localhost" in url or "staging" in url):
                    validation_result["valid"] = False
                    validation_result["issues"].append(
                        f"{service_name} URL inappropriate for production: {url}"
                    )
            
            # Check environment consistency
            if context.environment_type == EnvironmentType.UNKNOWN:
                validation_result["valid"] = False
                validation_result["issues"].append("Environment type could not be determined")
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["issues"].append(f"Validation error: {str(e)}")
        
        return validation_result


# Singleton instance for global usage
_service_instance: Optional[EnvironmentContextService] = None


def get_environment_context_service() -> EnvironmentContextService:
    """Get singleton EnvironmentContextService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = EnvironmentContextService()
    return _service_instance


async def initialize_environment_context() -> EnvironmentContextService:
    """
    Initialize environment context service.
    
    This function should be called during application startup to ensure
    environment context is available for all services.
    
    Returns:
        Initialized EnvironmentContextService
        
    Raises:
        RuntimeError: When environment cannot be determined
    """
    service = get_environment_context_service()
    await service.initialize()
    return service


# Convenience functions for common operations
async def get_current_environment() -> EnvironmentType:
    """Get current environment type."""
    service = get_environment_context_service()
    if not service.is_initialized():
        await service.initialize()
    return service.get_environment_type()


async def get_service_url_for_current_environment(service_name: str) -> str:
    """Get service URL for current environment."""
    service = get_environment_context_service()
    if not service.is_initialized():
        await service.initialize()
    return service.get_service_url(service_name)