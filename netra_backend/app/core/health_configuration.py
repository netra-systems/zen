from netra_backend.app.core.isolated_environment import get_env

"""
Central health check configuration.
Provides unified configuration for all health checks across the platform.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import os


@dataclass
class HealthConfiguration:
    """Central health check configuration."""
    
    # Timeout settings
    default_timeout_seconds: float = 10.0
    liveness_timeout_seconds: float = 5.0
    readiness_timeout_seconds: float = 15.0
    
    # Cache settings
    result_cache_ttl_seconds: int = 30
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # Environment-specific settings
    development_mode_overrides: Dict[str, Any] = field(default_factory=dict)
    staging_mode_overrides: Dict[str, Any] = field(default_factory=dict)
    production_mode_overrides: Dict[str, Any] = field(default_factory=dict)
    
    # Component priorities (1=critical, 2=important, 3=optional)
    component_priorities: Dict[str, int] = field(default_factory=dict)
    
    # Component-specific timeout overrides
    component_timeouts: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default configurations based on environment."""
        environment = get_env().get('ENVIRONMENT', 'development')
        
        # Default development overrides
        if not self.development_mode_overrides:
            self.development_mode_overrides = {
                "clickhouse": {"enabled": False, "status": "disabled"},
                "default_timeout_seconds": 5.0,
                "result_cache_ttl_seconds": 10
            }
        
        # Default staging overrides
        if not self.staging_mode_overrides:
            self.staging_mode_overrides = {
                "default_timeout_seconds": 8.0,
                "result_cache_ttl_seconds": 20
            }
        
        # Default production overrides
        if not self.production_mode_overrides:
            self.production_mode_overrides = {
                "default_timeout_seconds": 10.0,
                "result_cache_ttl_seconds": 30,
                "max_retries": 5
            }
        
        # Default component priorities
        if not self.component_priorities:
            self.component_priorities = {
                # Critical services (priority 1)
                "postgres": 1,
                "jwt_configuration": 1,
                
                # Important services (priority 2)
                "redis": 2,
                "websocket": 2,
                "system_resources": 2,
                "auth_service": 2,
                "circuit_breakers": 2,
                "oauth_providers": 2,
                
                # Optional services (priority 3)
                "clickhouse": 3,
                "discovery": 3,
                "database_monitoring": 3
            }
        
        # Default component-specific timeouts
        if not self.component_timeouts:
            self.component_timeouts = {
                "postgres": 10.0,
                "redis": 5.0,
                "clickhouse": 10.0,
                "websocket": 5.0,
                "system_resources": 5.0,
                "auth_service": 8.0,
                "oauth_providers": 5.0,
                "circuit_breakers": 5.0,
                "discovery": 3.0,
                "database_monitoring": 8.0,
                "jwt_configuration": 2.0
            }
        
        # Apply environment-specific overrides
        self._apply_environment_overrides(environment)
    
    def _apply_environment_overrides(self, environment: str) -> None:
        """Apply environment-specific configuration overrides."""
        overrides = None
        
        if environment == 'development':
            overrides = self.development_mode_overrides
        elif environment == 'staging':
            overrides = self.staging_mode_overrides
        elif environment == 'production':
            overrides = self.production_mode_overrides
        
        if overrides:
            # Apply timeout overrides
            if 'default_timeout_seconds' in overrides:
                self.default_timeout_seconds = overrides['default_timeout_seconds']
            if 'result_cache_ttl_seconds' in overrides:
                self.result_cache_ttl_seconds = overrides['result_cache_ttl_seconds']
            if 'max_retries' in overrides:
                self.max_retries = overrides['max_retries']
    
    def get_component_timeout(self, component_name: str) -> float:
        """Get timeout for a specific component."""
        return self.component_timeouts.get(component_name, self.default_timeout_seconds)
    
    def get_component_priority(self, component_name: str) -> int:
        """Get priority for a specific component."""
        return self.component_priorities.get(component_name, 2)  # Default to important
    
    def is_component_enabled(self, component_name: str, environment: Optional[str] = None) -> bool:
        """Check if a component is enabled in the current environment."""
        if not environment:
            environment = get_env().get('ENVIRONMENT', 'development')
        
        # Check environment-specific overrides
        overrides = None
        if environment == 'development':
            overrides = self.development_mode_overrides
        elif environment == 'staging':
            overrides = self.staging_mode_overrides
        elif environment == 'production':
            overrides = self.production_mode_overrides
        
        if overrides and component_name in overrides:
            component_config = overrides[component_name]
            if isinstance(component_config, dict):
                return component_config.get('enabled', True)
        
        # Default to enabled
        return True


# Global health configuration instance
health_config = HealthConfiguration()