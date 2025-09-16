"""Emergency Configuration Module - P0 VPC Connector Capacity Remediation

This module provides emergency configuration settings to reduce VPC connector load
during capacity exhaustion emergencies.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure (ALL users impacted during emergency)
- Business Goal: System Stability during infrastructure emergencies
- Value Impact: Prevents complete service outage during VPC capacity emergencies
- Strategic Impact: Protects $500K+ ARR by maintaining Golden Path functionality

P0 EMERGENCY CONTEXT:
- VPC connector capacity exhaustion in staging environment
- Database connection pool exhaustion causing cascading failures
- WebSocket connection overload contributing to VPC stress
- Need immediate load reduction without service restart

REMEDIATION APPROACH:
1. Reduce database connection pool sizes to minimum viable
2. Implement WebSocket connection throttling
3. Add circuit breaker patterns for overload protection
4. Enable emergency mode feature flags
5. Configure graceful degradation for non-critical features
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class EmergencyLevel(Enum):
    """Emergency levels for progressive load reduction."""
    NORMAL = "normal"          # Normal operation
    ELEVATED = "elevated"      # Proactive load reduction
    HIGH = "high"             # Significant load reduction
    CRITICAL = "critical"     # Maximum load reduction


@dataclass
class EmergencyDatabaseConfig:
    """Emergency database configuration for VPC load reduction."""
    # Normal operation values (current)
    normal_pool_size: int = 25
    normal_max_overflow: int = 50
    normal_pool_timeout: int = 30
    normal_pool_recycle: int = 1800

    # Emergency reduction values
    elevated_pool_size: int = 15
    elevated_max_overflow: int = 25
    elevated_pool_timeout: int = 20
    elevated_pool_recycle: int = 900

    high_pool_size: int = 8
    high_max_overflow: int = 12
    high_pool_timeout: int = 15
    high_pool_recycle: int = 600

    critical_pool_size: int = 5
    critical_max_overflow: int = 5
    critical_pool_timeout: int = 10
    critical_pool_recycle: int = 300

    def get_settings_for_level(self, level: EmergencyLevel) -> Dict[str, int]:
        """Get database settings for the specified emergency level."""
        if level == EmergencyLevel.NORMAL:
            return {
                'pool_size': self.normal_pool_size,
                'max_overflow': self.normal_max_overflow,
                'pool_timeout': self.normal_pool_timeout,
                'pool_recycle': self.normal_pool_recycle
            }
        elif level == EmergencyLevel.ELEVATED:
            return {
                'pool_size': self.elevated_pool_size,
                'max_overflow': self.elevated_max_overflow,
                'pool_timeout': self.elevated_pool_timeout,
                'pool_recycle': self.elevated_pool_recycle
            }
        elif level == EmergencyLevel.HIGH:
            return {
                'pool_size': self.high_pool_size,
                'max_overflow': self.high_max_overflow,
                'pool_timeout': self.high_pool_timeout,
                'pool_recycle': self.high_pool_recycle
            }
        elif level == EmergencyLevel.CRITICAL:
            return {
                'pool_size': self.critical_pool_size,
                'max_overflow': self.critical_max_overflow,
                'pool_timeout': self.critical_pool_timeout,
                'pool_recycle': self.critical_pool_recycle
            }
        else:
            raise ValueError(f"Unknown emergency level: {level}")


@dataclass
class EmergencyWebSocketConfig:
    """Emergency WebSocket configuration for connection throttling."""
    # Normal operation values
    normal_max_connections_per_user: int = 10
    normal_max_total_connections: int = 1000
    normal_heartbeat_interval: int = 30
    normal_connection_timeout: int = 60

    # Emergency reduction values
    elevated_max_connections_per_user: int = 5
    elevated_max_total_connections: int = 500
    elevated_heartbeat_interval: int = 60
    elevated_connection_timeout: int = 45

    high_max_connections_per_user: int = 3
    high_max_total_connections: int = 250
    high_heartbeat_interval: int = 90
    high_connection_timeout: int = 30

    critical_max_connections_per_user: int = 1
    critical_max_total_connections: int = 100
    critical_heartbeat_interval: int = 120
    critical_connection_timeout: int = 15

    def get_settings_for_level(self, level: EmergencyLevel) -> Dict[str, int]:
        """Get WebSocket settings for the specified emergency level."""
        if level == EmergencyLevel.NORMAL:
            return {
                'max_connections_per_user': self.normal_max_connections_per_user,
                'max_total_connections': self.normal_max_total_connections,
                'heartbeat_interval': self.normal_heartbeat_interval,
                'connection_timeout': self.normal_connection_timeout
            }
        elif level == EmergencyLevel.ELEVATED:
            return {
                'max_connections_per_user': self.elevated_max_connections_per_user,
                'max_total_connections': self.elevated_max_total_connections,
                'heartbeat_interval': self.elevated_heartbeat_interval,
                'connection_timeout': self.elevated_connection_timeout
            }
        elif level == EmergencyLevel.HIGH:
            return {
                'max_connections_per_user': self.high_max_connections_per_user,
                'max_total_connections': self.high_max_total_connections,
                'heartbeat_interval': self.high_heartbeat_interval,
                'connection_timeout': self.high_connection_timeout
            }
        elif level == EmergencyLevel.CRITICAL:
            return {
                'max_connections_per_user': self.critical_max_connections_per_user,
                'max_total_connections': self.critical_max_total_connections,
                'heartbeat_interval': self.critical_heartbeat_interval,
                'connection_timeout': self.critical_connection_timeout
            }
        else:
            raise ValueError(f"Unknown emergency level: {level}")


@dataclass
class EmergencyFeatureFlags:
    """Emergency feature flags for graceful degradation."""
    # Features that can be disabled during emergency
    disable_non_critical_logging: bool = False
    disable_analytics_collection: bool = False
    disable_performance_monitoring: bool = False
    disable_debug_endpoints: bool = False
    disable_background_tasks: bool = False
    enable_circuit_breaker: bool = False
    enable_connection_throttling: bool = False
    enable_aggressive_cleanup: bool = False

    def get_flags_for_level(self, level: EmergencyLevel) -> Dict[str, bool]:
        """Get feature flags for the specified emergency level."""
        if level == EmergencyLevel.NORMAL:
            return {
                'disable_non_critical_logging': False,
                'disable_analytics_collection': False,
                'disable_performance_monitoring': False,
                'disable_debug_endpoints': False,
                'disable_background_tasks': False,
                'enable_circuit_breaker': False,
                'enable_connection_throttling': False,
                'enable_aggressive_cleanup': False
            }
        elif level == EmergencyLevel.ELEVATED:
            return {
                'disable_non_critical_logging': True,
                'disable_analytics_collection': False,
                'disable_performance_monitoring': False,
                'disable_debug_endpoints': False,
                'disable_background_tasks': False,
                'enable_circuit_breaker': True,
                'enable_connection_throttling': True,
                'enable_aggressive_cleanup': False
            }
        elif level == EmergencyLevel.HIGH:
            return {
                'disable_non_critical_logging': True,
                'disable_analytics_collection': True,
                'disable_performance_monitoring': True,
                'disable_debug_endpoints': False,
                'disable_background_tasks': True,
                'enable_circuit_breaker': True,
                'enable_connection_throttling': True,
                'enable_aggressive_cleanup': True
            }
        elif level == EmergencyLevel.CRITICAL:
            return {
                'disable_non_critical_logging': True,
                'disable_analytics_collection': True,
                'disable_performance_monitoring': True,
                'disable_debug_endpoints': True,
                'disable_background_tasks': True,
                'enable_circuit_breaker': True,
                'enable_connection_throttling': True,
                'enable_aggressive_cleanup': True
            }
        else:
            raise ValueError(f"Unknown emergency level: {level}")


class EmergencyConfigurationManager:
    """Manager for emergency configuration during VPC capacity emergencies."""

    def __init__(self):
        """Initialize emergency configuration manager."""
        self._database_config = EmergencyDatabaseConfig()
        self._websocket_config = EmergencyWebSocketConfig()
        self._feature_flags = EmergencyFeatureFlags()
        self._current_level = self._detect_emergency_level()

        if self._current_level != EmergencyLevel.NORMAL:
            logger.warning(f"🚨 EMERGENCY MODE ACTIVE: {self._current_level.value.upper()} - VPC connector load reduction enabled")
        else:
            logger.info("Emergency configuration manager initialized - normal operation mode")

    def _detect_emergency_level(self) -> EmergencyLevel:
        """Detect current emergency level from environment variables."""
        env = get_env()

        # Check for explicit emergency level setting
        emergency_level = env.get('EMERGENCY_LEVEL', 'normal').lower()

        # Validate emergency level
        try:
            return EmergencyLevel(emergency_level)
        except ValueError:
            logger.warning(f"Invalid emergency level '{emergency_level}', defaulting to NORMAL")
            return EmergencyLevel.NORMAL

    def get_current_level(self) -> EmergencyLevel:
        """Get the current emergency level."""
        return self._current_level

    def set_emergency_level(self, level: EmergencyLevel) -> None:
        """Set the emergency level and log the change."""
        if level != self._current_level:
            old_level = self._current_level
            self._current_level = level

            if level == EmergencyLevel.NORMAL:
                logger.info(f"✅ Emergency mode DEACTIVATED: {old_level.value} → {level.value}")
            else:
                logger.critical(f"🚨 Emergency mode ACTIVATED: {old_level.value} → {level.value} - Load reduction in effect")

    def get_database_config(self) -> Dict[str, int]:
        """Get database configuration for current emergency level."""
        config = self._database_config.get_settings_for_level(self._current_level)

        if self._current_level != EmergencyLevel.NORMAL:
            logger.info(f"📊 Emergency database config active ({self._current_level.value}): "
                       f"pool_size={config['pool_size']}, max_overflow={config['max_overflow']}, "
                       f"timeout={config['pool_timeout']}s")

        return config

    def get_websocket_config(self) -> Dict[str, int]:
        """Get WebSocket configuration for current emergency level."""
        config = self._websocket_config.get_settings_for_level(self._current_level)

        if self._current_level != EmergencyLevel.NORMAL:
            logger.info(f"🔌 Emergency WebSocket config active ({self._current_level.value}): "
                       f"max_connections_per_user={config['max_connections_per_user']}, "
                       f"max_total={config['max_total_connections']}")

        return config

    def get_feature_flags(self) -> Dict[str, bool]:
        """Get feature flags for current emergency level."""
        flags = self._feature_flags.get_flags_for_level(self._current_level)

        if self._current_level != EmergencyLevel.NORMAL:
            enabled_features = [key for key, value in flags.items() if value]
            logger.info(f"🎛️ Emergency feature flags active ({self._current_level.value}): {enabled_features}")

        return flags

    def is_emergency_mode(self) -> bool:
        """Check if any emergency mode is active."""
        return self._current_level != EmergencyLevel.NORMAL

    def should_throttle_connections(self) -> bool:
        """Check if connection throttling should be enabled."""
        flags = self.get_feature_flags()
        return flags.get('enable_connection_throttling', False)

    def should_enable_circuit_breaker(self) -> bool:
        """Check if circuit breaker should be enabled."""
        flags = self.get_feature_flags()
        return flags.get('enable_circuit_breaker', False)

    def get_vpc_load_reduction_summary(self) -> Dict[str, Any]:
        """Get summary of VPC load reduction measures in effect."""
        if not self.is_emergency_mode():
            return {"emergency_mode": False, "vpc_load_reduction": "none"}

        db_config = self.get_database_config()
        ws_config = self.get_websocket_config()
        flags = self.get_feature_flags()

        # Calculate load reduction percentages
        normal_db = self._database_config.get_settings_for_level(EmergencyLevel.NORMAL)
        normal_ws = self._websocket_config.get_settings_for_level(EmergencyLevel.NORMAL)

        db_pool_reduction = round((1 - (db_config['pool_size'] / normal_db['pool_size'])) * 100, 1)
        ws_connection_reduction = round((1 - (ws_config['max_total_connections'] / normal_ws['max_total_connections'])) * 100, 1)

        return {
            "emergency_mode": True,
            "emergency_level": self._current_level.value,
            "vpc_load_reduction": {
                "database_pool_reduction_percent": db_pool_reduction,
                "websocket_connection_reduction_percent": ws_connection_reduction,
                "circuit_breaker_enabled": flags.get('enable_circuit_breaker', False),
                "connection_throttling_enabled": flags.get('enable_connection_throttling', False),
                "background_tasks_disabled": flags.get('disable_background_tasks', False)
            },
            "current_limits": {
                "database_pool_size": db_config['pool_size'],
                "database_max_overflow": db_config['max_overflow'],
                "websocket_max_total_connections": ws_config['max_total_connections'],
                "websocket_max_per_user": ws_config['max_connections_per_user']
            }
        }


# Global emergency configuration manager instance
_emergency_manager: Optional[EmergencyConfigurationManager] = None


def get_emergency_config() -> EmergencyConfigurationManager:
    """Get the global emergency configuration manager instance."""
    global _emergency_manager
    if _emergency_manager is None:
        _emergency_manager = EmergencyConfigurationManager()
    return _emergency_manager


def is_emergency_mode() -> bool:
    """Quick check if emergency mode is active."""
    return get_emergency_config().is_emergency_mode()


def get_emergency_database_config() -> Dict[str, int]:
    """Get emergency database configuration."""
    return get_emergency_config().get_database_config()


def get_emergency_websocket_config() -> Dict[str, int]:
    """Get emergency WebSocket configuration."""
    return get_emergency_config().get_websocket_config()


def get_emergency_feature_flags() -> Dict[str, bool]:
    """Get emergency feature flags."""
    return get_emergency_config().get_feature_flags()


# Export public interface
__all__ = [
    'EmergencyLevel',
    'EmergencyConfigurationManager',
    'get_emergency_config',
    'is_emergency_mode',
    'get_emergency_database_config',
    'get_emergency_websocket_config',
    'get_emergency_feature_flags'
]