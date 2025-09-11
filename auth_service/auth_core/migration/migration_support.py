"""
Migration Support Features - Phase 1 JWT SSOT Remediation
Feature flags and dual-mode operation for safe JWT SSOT migration
Enables gradual rollout from backend JWT logic to auth service SSOT
"""
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field

from shared.isolated_environment import get_env
from auth_service.auth_core.config import AuthConfig

logger = logging.getLogger(__name__)

class MigrationPhase(Enum):
    """Migration phases for JWT SSOT transition"""
    PHASE_0_BASELINE = "phase_0_baseline"  # Current state - backend has JWT logic
    PHASE_1_AUTH_ENHANCED = "phase_1_auth_enhanced"  # Auth service enhanced with new APIs
    PHASE_2_BACKEND_INTEGRATION = "phase_2_backend_integration"  # Backend starts using auth APIs
    PHASE_3_VALIDATION_DUAL = "phase_3_validation_dual"  # Both systems validate (safety)
    PHASE_4_AUTH_ONLY = "phase_4_auth_only"  # Only auth service validates JWT
    PHASE_5_CLEANUP = "phase_5_cleanup"  # Remove backend JWT logic

class MigrationFlag(Enum):
    """Feature flags for migration control"""
    ENABLE_JWT_VALIDATION_API = "enable_jwt_validation_api"
    ENABLE_WEBSOCKET_AUTH_API = "enable_websocket_auth_api"
    ENABLE_SERVICE_AUTH_API = "enable_service_auth_api"
    ENABLE_PERFORMANCE_OPTIMIZATION = "enable_performance_optimization"
    ENABLE_DUAL_MODE_VALIDATION = "enable_dual_mode_validation"
    ENABLE_MIGRATION_LOGGING = "enable_migration_logging"
    ENABLE_BACKWARD_COMPATIBILITY = "enable_backward_compatibility"
    ENABLE_CIRCUIT_BREAKER = "enable_circuit_breaker"

@dataclass
class MigrationStatus:
    """Migration status tracking"""
    current_phase: MigrationPhase
    enabled_flags: List[MigrationFlag] = field(default_factory=list)
    migration_start_time: Optional[datetime] = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    migration_metrics: Dict[str, Any] = field(default_factory=dict)
    rollback_available: bool = True
    
class MigrationManager:
    """
    Manages JWT SSOT migration phases and feature flags
    
    Provides safe, gradual migration from backend JWT logic to auth service SSOT.
    """
    
    def __init__(self):
        self.status = self._load_migration_status()
        self.feature_flags = self._load_feature_flags()
        self.migration_callbacks = {}
        self.rollback_handlers = {}
        
        logger.info(f"Migration Manager initialized - Phase: {self.status.current_phase.value}")
    
    def is_flag_enabled(self, flag: MigrationFlag) -> bool:
        """
        Check if a migration feature flag is enabled
        """
        try:
            # Check environment variable override
            env_key = f"MIGRATION_{flag.value.upper()}"
            env_value = get_env().get(env_key)
            
            if env_value is not None:
                return env_value.lower() in ['true', '1', 'yes', 'on']
            
            # Check internal flag status
            return flag in self.feature_flags.get('enabled', [])
            
        except Exception as e:
            logger.error(f"Error checking feature flag {flag.value}: {e}")
            return False
    
    def enable_flag(self, flag: MigrationFlag, persist: bool = True) -> bool:
        """
        Enable a migration feature flag
        """
        try:
            if 'enabled' not in self.feature_flags:
                self.feature_flags['enabled'] = []
            
            if flag not in self.feature_flags['enabled']:
                self.feature_flags['enabled'].append(flag)
                
                if persist:
                    self._save_feature_flags()
                
                logger.info(f"Migration flag enabled: {flag.value}")
                
                # Execute flag enable callback if registered
                if flag in self.migration_callbacks:
                    self.migration_callbacks[flag]('enabled')
                
                return True
            
            return True  # Already enabled
            
        except Exception as e:
            logger.error(f"Error enabling feature flag {flag.value}: {e}")
            return False
    
    def disable_flag(self, flag: MigrationFlag, persist: bool = True) -> bool:
        """
        Disable a migration feature flag
        """
        try:
            if 'enabled' in self.feature_flags and flag in self.feature_flags['enabled']:
                self.feature_flags['enabled'].remove(flag)
                
                if persist:
                    self._save_feature_flags()
                
                logger.info(f"Migration flag disabled: {flag.value}")
                
                # Execute flag disable callback if registered
                if flag in self.migration_callbacks:
                    self.migration_callbacks[flag]('disabled')
                
                return True
            
            return True  # Already disabled
            
        except Exception as e:
            logger.error(f"Error disabling feature flag {flag.value}: {e}")
            return False
    
    def set_migration_phase(self, phase: MigrationPhase) -> bool:
        """
        Set current migration phase
        """
        try:
            old_phase = self.status.current_phase
            self.status.current_phase = phase
            self.status.last_updated = datetime.now(timezone.utc)
            
            # Auto-enable flags for phase
            self._enable_flags_for_phase(phase)
            
            # Persist status
            self._save_migration_status()
            
            logger.info(f"Migration phase changed: {old_phase.value} → {phase.value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting migration phase {phase.value}: {e}")
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get comprehensive migration status
        """
        try:
            enabled_flags = [flag.value for flag in self.feature_flags.get('enabled', [])]
            
            return {
                "current_phase": self.status.current_phase.value,
                "enabled_flags": enabled_flags,
                "migration_start_time": self.status.migration_start_time.isoformat() if self.status.migration_start_time else None,
                "last_updated": self.status.last_updated.isoformat(),
                "rollback_available": self.status.rollback_available,
                "migration_metrics": self.status.migration_metrics,
                "environment": AuthConfig.get_environment(),
                "api_status": self._get_api_status()
            }
            
        except Exception as e:
            logger.error(f"Error getting migration status: {e}")
            return {"error": "status_unavailable"}
    
    def start_migration(self) -> bool:
        """
        Start migration process
        """
        try:
            if self.status.migration_start_time is None:
                self.status.migration_start_time = datetime.now(timezone.utc)
                self.status.current_phase = MigrationPhase.PHASE_1_AUTH_ENHANCED
                
                # Enable initial flags
                initial_flags = [
                    MigrationFlag.ENABLE_JWT_VALIDATION_API,
                    MigrationFlag.ENABLE_WEBSOCKET_AUTH_API,
                    MigrationFlag.ENABLE_MIGRATION_LOGGING,
                    MigrationFlag.ENABLE_BACKWARD_COMPATIBILITY
                ]
                
                for flag in initial_flags:
                    self.enable_flag(flag, persist=False)
                
                self._save_migration_status()
                
                logger.info("JWT SSOT migration started - Phase 1")
                return True
            else:
                logger.warning("Migration already started")
                return False
                
        except Exception as e:
            logger.error(f"Error starting migration: {e}")
            return False
    
    def rollback_migration(self, reason: str = "manual_rollback") -> bool:
        """
        Rollback migration to previous phase
        """
        try:
            if not self.status.rollback_available:
                logger.error("Rollback not available for current migration state")
                return False
            
            current_phase = self.status.current_phase
            rollback_phase = self._get_rollback_phase(current_phase)
            
            if rollback_phase:
                logger.warning(f"Rolling back migration: {current_phase.value} → {rollback_phase.value}, reason: {reason}")
                
                # Execute rollback handlers
                if current_phase in self.rollback_handlers:
                    self.rollback_handlers[current_phase](reason)
                
                # Set rollback phase
                self.status.current_phase = rollback_phase
                self.status.last_updated = datetime.now(timezone.utc)
                
                # Record rollback in metrics
                if 'rollbacks' not in self.status.migration_metrics:
                    self.status.migration_metrics['rollbacks'] = []
                
                self.status.migration_metrics['rollbacks'].append({
                    "from_phase": current_phase.value,
                    "to_phase": rollback_phase.value,
                    "reason": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                self._save_migration_status()
                return True
            else:
                logger.error(f"No rollback phase defined for {current_phase.value}")
                return False
                
        except Exception as e:
            logger.error(f"Error during migration rollback: {e}")
            return False
    
    def register_callback(self, flag: MigrationFlag, callback: Callable) -> None:
        """
        Register callback for flag state changes
        """
        self.migration_callbacks[flag] = callback
        logger.debug(f"Registered callback for flag: {flag.value}")
    
    def register_rollback_handler(self, phase: MigrationPhase, handler: Callable) -> None:
        """
        Register rollback handler for migration phase
        """
        self.rollback_handlers[phase] = handler
        logger.debug(f"Registered rollback handler for phase: {phase.value}")
    
    def update_metrics(self, metric_name: str, value: Any) -> None:
        """
        Update migration metrics
        """
        try:
            self.status.migration_metrics[metric_name] = value
            self.status.migration_metrics['last_metric_update'] = datetime.now(timezone.utc).isoformat()
            
            # Persist metrics periodically
            if len(self.status.migration_metrics) % 10 == 0:
                self._save_migration_status()
                
        except Exception as e:
            logger.error(f"Error updating migration metric {metric_name}: {e}")
    
    def _load_migration_status(self) -> MigrationStatus:
        """
        Load migration status from persistent storage
        """
        try:
            # In production, this would load from database/Redis
            # For now, use environment variable or default
            phase_env = get_env().get("MIGRATION_PHASE", "phase_0_baseline")
            
            try:
                current_phase = MigrationPhase(phase_env)
            except ValueError:
                logger.warning(f"Invalid migration phase in environment: {phase_env}")
                current_phase = MigrationPhase.PHASE_0_BASELINE
            
            return MigrationStatus(
                current_phase=current_phase,
                last_updated=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error loading migration status: {e}")
            return MigrationStatus(current_phase=MigrationPhase.PHASE_0_BASELINE)
    
    def _save_migration_status(self) -> bool:
        """
        Save migration status to persistent storage
        """
        try:
            # In production, this would save to database/Redis
            # For now, just log the status
            logger.info(f"Migration status updated: {self.status.current_phase.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving migration status: {e}")
            return False
    
    def _load_feature_flags(self) -> Dict[str, List[MigrationFlag]]:
        """
        Load feature flags from persistent storage
        """
        try:
            # Default enabled flags based on environment
            environment = AuthConfig.get_environment()
            
            if environment in ["development", "test"]:
                # Enable all flags in development
                default_enabled = list(MigrationFlag)
            else:
                # Conservative defaults for production
                default_enabled = [
                    MigrationFlag.ENABLE_MIGRATION_LOGGING,
                    MigrationFlag.ENABLE_BACKWARD_COMPATIBILITY
                ]
            
            return {"enabled": default_enabled}
            
        except Exception as e:
            logger.error(f"Error loading feature flags: {e}")
            return {"enabled": []}
    
    def _save_feature_flags(self) -> bool:
        """
        Save feature flags to persistent storage
        """
        try:
            # In production, this would save to database/Redis
            enabled_flags = [flag.value for flag in self.feature_flags.get('enabled', [])]
            logger.debug(f"Feature flags updated: {enabled_flags}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving feature flags: {e}")
            return False
    
    def _enable_flags_for_phase(self, phase: MigrationPhase) -> None:
        """
        Auto-enable flags appropriate for migration phase
        """
        phase_flags = {
            MigrationPhase.PHASE_0_BASELINE: [
                MigrationFlag.ENABLE_MIGRATION_LOGGING
            ],
            MigrationPhase.PHASE_1_AUTH_ENHANCED: [
                MigrationFlag.ENABLE_JWT_VALIDATION_API,
                MigrationFlag.ENABLE_WEBSOCKET_AUTH_API,
                MigrationFlag.ENABLE_SERVICE_AUTH_API,
                MigrationFlag.ENABLE_PERFORMANCE_OPTIMIZATION,
                MigrationFlag.ENABLE_MIGRATION_LOGGING,
                MigrationFlag.ENABLE_BACKWARD_COMPATIBILITY
            ],
            MigrationPhase.PHASE_2_BACKEND_INTEGRATION: [
                MigrationFlag.ENABLE_JWT_VALIDATION_API,
                MigrationFlag.ENABLE_WEBSOCKET_AUTH_API,
                MigrationFlag.ENABLE_SERVICE_AUTH_API,
                MigrationFlag.ENABLE_PERFORMANCE_OPTIMIZATION,
                MigrationFlag.ENABLE_DUAL_MODE_VALIDATION,
                MigrationFlag.ENABLE_MIGRATION_LOGGING,
                MigrationFlag.ENABLE_CIRCUIT_BREAKER
            ]
        }
        
        if phase in phase_flags:
            for flag in phase_flags[phase]:
                self.enable_flag(flag, persist=False)
    
    def _get_rollback_phase(self, current_phase: MigrationPhase) -> Optional[MigrationPhase]:
        """
        Get appropriate rollback phase for current phase
        """
        rollback_map = {
            MigrationPhase.PHASE_1_AUTH_ENHANCED: MigrationPhase.PHASE_0_BASELINE,
            MigrationPhase.PHASE_2_BACKEND_INTEGRATION: MigrationPhase.PHASE_1_AUTH_ENHANCED,
            MigrationPhase.PHASE_3_VALIDATION_DUAL: MigrationPhase.PHASE_2_BACKEND_INTEGRATION,
            MigrationPhase.PHASE_4_AUTH_ONLY: MigrationPhase.PHASE_3_VALIDATION_DUAL,
            MigrationPhase.PHASE_5_CLEANUP: MigrationPhase.PHASE_4_AUTH_ONLY
        }
        
        return rollback_map.get(current_phase)
    
    def _get_api_status(self) -> Dict[str, bool]:
        """
        Get status of migration APIs
        """
        return {
            "jwt_validation_api": self.is_flag_enabled(MigrationFlag.ENABLE_JWT_VALIDATION_API),
            "websocket_auth_api": self.is_flag_enabled(MigrationFlag.ENABLE_WEBSOCKET_AUTH_API),
            "service_auth_api": self.is_flag_enabled(MigrationFlag.ENABLE_SERVICE_AUTH_API),
            "performance_optimization": self.is_flag_enabled(MigrationFlag.ENABLE_PERFORMANCE_OPTIMIZATION),
            "dual_mode_validation": self.is_flag_enabled(MigrationFlag.ENABLE_DUAL_MODE_VALIDATION)
        }

# Global migration manager instance
migration_manager = MigrationManager()

# Convenience functions for flag checking
def is_jwt_validation_enabled() -> bool:
    """Check if JWT validation API is enabled"""
    return migration_manager.is_flag_enabled(MigrationFlag.ENABLE_JWT_VALIDATION_API)

def is_websocket_auth_enabled() -> bool:
    """Check if WebSocket auth API is enabled"""
    return migration_manager.is_flag_enabled(MigrationFlag.ENABLE_WEBSOCKET_AUTH_API)

def is_service_auth_enabled() -> bool:
    """Check if service auth API is enabled"""
    return migration_manager.is_flag_enabled(MigrationFlag.ENABLE_SERVICE_AUTH_API)

def is_dual_mode_enabled() -> bool:
    """Check if dual mode validation is enabled"""
    return migration_manager.is_flag_enabled(MigrationFlag.ENABLE_DUAL_MODE_VALIDATION)

def is_performance_optimization_enabled() -> bool:
    """Check if performance optimization is enabled"""
    return migration_manager.is_flag_enabled(MigrationFlag.ENABLE_PERFORMANCE_OPTIMIZATION)

# Migration API wrapper for backward compatibility
def with_migration_support(api_function: Callable):
    """
    Decorator to add migration support to API functions
    """
    def wrapper(*args, **kwargs):
        # Check if API is enabled
        function_name = api_function.__name__
        
        if 'jwt_validation' in function_name and not is_jwt_validation_enabled():
            return {"error": "jwt_validation_api_disabled", "migration_phase": migration_manager.status.current_phase.value}
        
        if 'websocket' in function_name and not is_websocket_auth_enabled():
            return {"error": "websocket_auth_api_disabled", "migration_phase": migration_manager.status.current_phase.value}
        
        if 'service' in function_name and not is_service_auth_enabled():
            return {"error": "service_auth_api_disabled", "migration_phase": migration_manager.status.current_phase.value}
        
        # Log migration API usage
        if migration_manager.is_flag_enabled(MigrationFlag.ENABLE_MIGRATION_LOGGING):
            logger.debug(f"Migration API called: {function_name}")
            migration_manager.update_metrics(f"{function_name}_calls", 
                migration_manager.status.migration_metrics.get(f"{function_name}_calls", 0) + 1)
        
        # Execute the function
        return api_function(*args, **kwargs)
    
    return wrapper