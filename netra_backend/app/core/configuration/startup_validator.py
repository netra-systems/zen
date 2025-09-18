"""
Configuration Startup Validation Integration

This module integrates ConfigDependencyMap with the application startup process
to ensure configuration integrity before allowing the application to start.
"""

import logging
from typing import List, Tuple, Optional
from enum import Enum

from netra_backend.app.core.config_dependencies import ConfigDependencyMap, ConfigImpactLevel
from netra_backend.app.config import get_config as get_unified_config
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger


class StartupValidationMode(Enum):
    """Startup validation modes"""
    STRICT = "strict"      # Fail on any critical config issues
    PERMISSIVE = "permissive"  # Warn but continue with non-critical issues
    EMERGENCY = "emergency"    # Allow startup with minimal checks only


class ConfigurationStartupValidator:
    """
    Validates configuration during application startup using ConfigDependencyMap.
    Provides protection against configuration deletions and ensures critical
    services can start properly.
    """
    
    def __init__(self, mode: StartupValidationMode = StartupValidationMode.STRICT):
        self.mode = mode
        self.logger = central_logger.get_logger(__name__)
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_startup_configuration(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate configuration for startup readiness.
        
        Returns:
            Tuple[bool, List[str], List[str]]: (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        try:
            self._validate_critical_dependencies()
            self._validate_config_values()
            self._check_service_readiness()
            
            is_valid = self._determine_validation_result()
            self._log_validation_results(is_valid)
            
            return is_valid, self.errors, self.warnings
            
        except Exception as e:
            error_msg = f"Startup validation failed with exception: {str(e)}"
            self.errors.append(error_msg)
            self.logger.error(error_msg)
            return False, self.errors, self.warnings
    
    def _validate_critical_dependencies(self) -> None:
        """Validate all critical configuration dependencies"""
        env = get_env()
        required_configs = ConfigDependencyMap.get_required_configs()
        
        for config_key, metadata in required_configs.items():
            value = env.get(config_key)
            
            if not value and not metadata.get("fallback_allowed", False):
                impact = metadata.get("deletion_impact", "Unknown impact")
                error_msg = f"CRITICAL CONFIG MISSING: {config_key} - {impact}"
                
                if metadata.get("impact_level") == ConfigImpactLevel.CRITICAL:
                    self.errors.append(error_msg)
                    self.logger.error(error_msg)
                else:
                    self.warnings.append(error_msg)
                    self.logger.warning(error_msg)
    
    def _validate_config_values(self) -> None:
        """Validate configuration values using ConfigDependencyMap rules"""
        env = get_env()
        all_configs = {
            **ConfigDependencyMap.CRITICAL_DEPENDENCIES,
            **ConfigDependencyMap.HIGH_PRIORITY_DEPENDENCIES,
            **ConfigDependencyMap.SERVICE_SPECIFIC_DEPENDENCIES
        }
        
        for config_key in all_configs:
            value = env.get(config_key)
            if value:
                is_valid, message = ConfigDependencyMap.validate_config_value(config_key, value)
                if not is_valid:
                    error_msg = f"INVALID CONFIG VALUE: {config_key} - {message}"
                    
                    # Determine severity based on impact level
                    config_info = all_configs[config_key]
                    if config_info.get("impact_level") == ConfigImpactLevel.CRITICAL:
                        self.errors.append(error_msg)
                        self.logger.error(error_msg)
                    else:
                        self.warnings.append(error_msg)
                        self.logger.warning(error_msg)
    
    def _check_service_readiness(self) -> None:
        """Check if critical services can be initialized with current config"""
        try:
            # Test configuration loading
            config = get_unified_config()
            
            # Check database connectivity prerequisites
            if not config.database_url:
                self.errors.append("DATABASE CONFIG: No database URL configured - database services will fail")
            
            # Check auth prerequisites
            if not config.jwt_secret_key:
                self.errors.append("AUTH CONFIG: No JWT secret key - authentication will fail")
            
            # Check configuration consistency
            issues = ConfigDependencyMap.check_config_consistency(config.__dict__)
            for issue in issues:
                if "CRITICAL" in issue:
                    self.errors.append(f"CONFIG CONSISTENCY: {issue}")
                elif "WARNING" in issue:
                    self.warnings.append(f"CONFIG CONSISTENCY: {issue}")
                else:
                    self.warnings.append(f"CONFIG INFO: {issue}")
                    
        except Exception as e:
            error_msg = f"Service readiness check failed: {str(e)}"
            self.errors.append(error_msg)
            self.logger.error(error_msg)
    
    def _determine_validation_result(self) -> bool:
        """Determine if validation passed based on mode and results"""
        if self.mode == StartupValidationMode.EMERGENCY:
            # In emergency mode, only fail if we can't load basic config
            return len([e for e in self.errors if "database_url" in e.lower()]) == 0
        
        elif self.mode == StartupValidationMode.PERMISSIVE:
            # In permissive mode, only fail on critical errors
            critical_errors = [e for e in self.errors if "CRITICAL" in e]
            return len(critical_errors) == 0
        
        else:  # STRICT mode
            # In strict mode, fail on any errors
            return len(self.errors) == 0
    
    def _log_validation_results(self, is_valid: bool) -> None:
        """Log validation results"""
        if is_valid:
            self.logger.info(f"Startup configuration validation PASSED ({self.mode.value} mode)")
            if self.warnings:
                self.logger.info(f"Warnings: {len(self.warnings)} issues detected but not blocking")
        else:
            self.logger.error(f"Startup configuration validation FAILED ({self.mode.value} mode)")
            self.logger.error(f"Errors: {len(self.errors)}, Warnings: {len(self.warnings)}")
    
    def get_validation_summary(self) -> dict:
        """Get validation summary for reporting"""
        return {
            "mode": self.mode.value,
            "passed": len(self.errors) == 0 if self.mode == StartupValidationMode.STRICT else self._determine_validation_result(),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings
        }


def validate_startup_config(mode: StartupValidationMode = StartupValidationMode.STRICT) -> bool:
    """
    Convenience function to validate startup configuration.
    
    Args:
        mode: Validation mode to use
        
    Returns:
        bool: True if validation passed
    """
    validator = ConfigurationStartupValidator(mode)
    is_valid, errors, warnings = validator.validate_startup_configuration()
    
    if not is_valid:
        logger = central_logger.get_logger(__name__)
        logger.error("STARTUP BLOCKED: Configuration validation failed")
        for error in errors:
            logger.error(f"  - {error}")
    
    return is_valid


def get_critical_config_status() -> dict:
    """
    Get status of critical configuration dependencies.
    
    Returns:
        dict: Status of all critical configurations
    """
    env = get_env()
    status = {}
    
    for config_key, metadata in ConfigDependencyMap.CRITICAL_DEPENDENCIES.items():
        value = env.get(config_key)
        is_present = bool(value)
        is_valid = True
        validation_message = "OK"
        
        if value:
            is_valid, validation_message = ConfigDependencyMap.validate_config_value(config_key, value)
        
        status[config_key] = {
            "present": is_present,
            "valid": is_valid,
            "required_by": metadata.get("required_by", []),
            "impact_level": metadata.get("impact_level", ConfigImpactLevel.MEDIUM).value,
            "fallback_allowed": metadata.get("fallback_allowed", False),
            "validation_message": validation_message,
            "deletion_impact": metadata.get("deletion_impact", "Unknown")
        }
    
    return status


# Integration hook for startup sequence
def integrate_with_startup(startup_orchestrator) -> bool:
    """
    Integration point for the startup sequence.
    This should be called during the startup process to validate configuration.
    
    Args:
        startup_orchestrator: The startup orchestrator instance
        
    Returns:
        bool: True if configuration is valid for startup
    """
    try:
        logger = central_logger.get_logger(__name__)
        logger.info("Running ConfigDependencyMap startup validation...")
        
        # Use permissive mode for startup to allow graceful degradation
        mode = StartupValidationMode.PERMISSIVE
        is_valid = validate_startup_config(mode)
        
        if is_valid:
            logger.info("Configuration dependency validation passed")
        else:
            logger.warning("Configuration dependency validation failed - continuing with degraded functionality")
        
        return is_valid
        
    except Exception as e:
        logger = central_logger.get_logger(__name__)
        logger.error(f"ConfigDependencyMap startup integration failed: {e}")
        # Don't block startup on integration errors
        return True