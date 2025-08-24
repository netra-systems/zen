from dev_launcher.isolated_environment import get_env
"""Startup configuration for robust initialization system.

This module defines configuration settings for the startup manager
to ensure reliable cold start and graceful degradation.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability
- Value Impact: Prevents cold start failures that block development
- Strategic Impact: Enables reliable deployments and faster time-to-market
"""

import os
from typing import Dict, Any


class StartupConfig:
    """Configuration settings for the startup manager."""
    
    # Circuit breaker settings
    MAX_FAILURES: int = 3
    RECOVERY_TIMEOUT_SECONDS: int = 300  # 5 minutes
    
    # Retry settings
    MAX_RETRIES: int = 3
    INITIAL_RETRY_DELAY: float = 1.0
    MAX_RETRY_DELAY: float = 30.0
    BACKOFF_MULTIPLIER: float = 2.0
    
    # Component priorities
    COMPONENT_PRIORITIES = {
        # CRITICAL components must start successfully
        "database": "CRITICAL",
        "configuration": "CRITICAL", 
        "secrets": "CRITICAL",
        
        # HIGH priority components should start but can degrade
        "redis": "HIGH",
        "auth_service": "HIGH",
        "websocket": "HIGH",
        
        # MEDIUM priority components are important but optional
        "clickhouse": "MEDIUM",
        "monitoring": "MEDIUM",
        "background_tasks": "MEDIUM",
        
        # LOW priority components are nice-to-have
        "metrics": "LOW",
        "tracing": "LOW",
        "analytics": "LOW"
    }
    
    # Database initialization settings
    DATABASE_INIT_TIMEOUT: int = 60  # seconds
    DATABASE_POOL_MIN: int = 5
    DATABASE_POOL_MAX: int = 20
    DATABASE_ACQUIRE_TIMEOUT: int = 10  # seconds
    
    # Service health check settings
    HEALTH_CHECK_INTERVAL: int = 30  # seconds
    HEALTH_CHECK_TIMEOUT: int = 5  # seconds
    
    # Graceful degradation settings
    ALLOW_DEGRADED_MODE: bool = get_env().get("ALLOW_DEGRADED_MODE", "true").lower() == "true"
    USE_ROBUST_STARTUP: bool = get_env().get("USE_ROBUST_STARTUP", "true").lower() == "true"
    GRACEFUL_STARTUP_MODE: bool = get_env().get("GRACEFUL_STARTUP_MODE", "true").lower() == "true"
    
    @classmethod
    def get_component_priority(cls, component_name: str) -> str:
        """Get priority level for a component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Priority level (CRITICAL, HIGH, MEDIUM, LOW)
        """
        return cls.COMPONENT_PRIORITIES.get(component_name, "LOW")
    
    @classmethod
    def is_critical_component(cls, component_name: str) -> bool:
        """Check if a component is critical for startup.
        
        Args:
            component_name: Name of the component
            
        Returns:
            True if component is critical
        """
        return cls.get_component_priority(component_name) == "CRITICAL"
    
    @classmethod
    def get_retry_delay(cls, attempt: int) -> float:
        """Calculate retry delay with exponential backoff.
        
        Args:
            attempt: Current retry attempt number (0-based)
            
        Returns:
            Delay in seconds before next retry
        """
        delay = cls.INITIAL_RETRY_DELAY * (cls.BACKOFF_MULTIPLIER ** attempt)
        return min(delay, cls.MAX_RETRY_DELAY)
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration as dictionary
        """
        return {
            "max_failures": cls.MAX_FAILURES,
            "recovery_timeout": cls.RECOVERY_TIMEOUT_SECONDS,
            "max_retries": cls.MAX_RETRIES,
            "allow_degraded_mode": cls.ALLOW_DEGRADED_MODE,
            "use_robust_startup": cls.USE_ROBUST_STARTUP,
            "graceful_startup_mode": cls.GRACEFUL_STARTUP_MODE,
            "component_priorities": cls.COMPONENT_PRIORITIES
        }