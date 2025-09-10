"""
Cross-Service Configuration Validator

This module provides validation across all services to ensure configuration
consistency and prevent breaking changes that affect multiple services.

Works in conjunction with:
- shared.configuration.central_config_validator (environment-based validation)
- netra_backend.app.core.config_dependencies (backend-specific dependencies)
"""

import os
import importlib
import logging
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfigCheck:
    """Result of checking a configuration in a specific service."""
    service_name: str
    config_key: str
    is_required: bool
    can_delete: bool
    impact_description: str
    affected_components: List[str]
    migration_required: bool
    migration_guide: Optional[str] = None


class CrossServiceConfigValidator:
    """
    Validates configuration changes across all Netra services.
    
    This validator checks how configuration changes will impact:
    - netra_backend
    - auth_service
    - frontend (if applicable)
    - shared components
    """
    
    # Map of services and their configuration dependency sources
    SERVICE_CONFIG_SOURCES = {
        "netra_backend": {
            "module": "netra_backend.app.core.config_dependencies",
            "class": "ConfigDependencyMap",
            "methods": {
                "check_deletion": "can_delete_config",
                "get_impact": "get_impact_analysis",
                "get_alternatives": "get_alternatives"
            }
        },
        "auth_service": {
            "module": "auth_service.auth_core.auth_environment",
            "class": "AuthEnvironment",
            "methods": {
                # Auth service uses different pattern
                "check_required": "is_config_required"
            }
        },
        "shared": {
            "module": "shared.configuration.central_config_validator",
            "class": "CentralConfigurationValidator",
            "methods": {
                "check_deletion": "check_config_before_deletion"
            }
        }
    }
    
    # Critical cross-service configurations
    CROSS_SERVICE_CONFIGS = {
        "JWT_SECRET_KEY": ["netra_backend", "auth_service"],
        "SECRET_KEY": ["netra_backend", "auth_service"],
        "DATABASE_URL": ["netra_backend", "auth_service"],
        "POSTGRES_HOST": ["netra_backend", "auth_service"],
        "POSTGRES_PORT": ["netra_backend", "auth_service"],
        "POSTGRES_DB": ["netra_backend", "auth_service"],
        "POSTGRES_USER": ["netra_backend", "auth_service"],
        "POSTGRES_PASSWORD": ["netra_backend", "auth_service"],
        "REDIS_URL": ["netra_backend", "auth_service"],
        "REDIS_HOST": ["netra_backend", "auth_service"],
        "REDIS_PORT": ["netra_backend", "auth_service"],
        "FRONTEND_URL": ["netra_backend", "auth_service", "frontend"],
        "BACKEND_URL": ["netra_backend", "auth_service", "frontend"],
        "AUTH_SERVICE_URL": ["netra_backend", "auth_service"],
        "AUTH_REDIRECT_URI": ["netra_backend", "auth_service"],
        "AUTH_CALLBACK_URL": ["netra_backend", "auth_service"],
        # OAuth configs are critical across services
        "GOOGLE_OAUTH_CLIENT_ID": ["auth_service"],
        "GOOGLE_OAUTH_CLIENT_SECRET": ["auth_service"],
        "GOOGLE_OAUTH_CLIENT_ID_TEST": ["auth_service"],
        "GOOGLE_OAUTH_CLIENT_SECRET_TEST": ["auth_service"],
        "GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT": ["auth_service"],
        "GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT": ["auth_service"],
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": ["auth_service"],
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": ["auth_service"],
        "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION": ["auth_service"],
        "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION": ["auth_service"],
    }
    
    def __init__(self):
        """Initialize the cross-service validator."""
        self.service_validators = {}
        self._load_service_validators()
    
    def _load_service_validators(self):
        """Dynamically load configuration validators from each service."""
        for service_name, config in self.SERVICE_CONFIG_SOURCES.items():
            try:
                module = importlib.import_module(config["module"])
                validator_class = getattr(module, config["class"])
                self.service_validators[service_name] = {
                    "class": validator_class,
                    "methods": config["methods"]
                }
                logger.debug(f"Loaded validator for {service_name}")
            except (ImportError, AttributeError) as e:
                logger.warning(f"Could not load validator for {service_name}: {e}")
                self.service_validators[service_name] = None
    
    def validate_config_deletion(self, config_key: str) -> List[ServiceConfigCheck]:
        """
        Check if a configuration can be safely deleted across all services.
        
        Args:
            config_key: The configuration key to check
            
        Returns:
            List of ServiceConfigCheck results for each affected service
        """
        results = []
        
        # Check each service that might use this config
        affected_services = self.CROSS_SERVICE_CONFIGS.get(config_key, ["netra_backend", "auth_service"])
        
        for service_name in affected_services:
            check_result = self._check_service_config(service_name, config_key)
            if check_result:
                results.append(check_result)
        
        # Also check with central validator
        try:
            from shared.configuration.central_config_validator import check_config_before_deletion
            result = check_config_before_deletion(config_key)
            can_delete = result["safe_to_delete"]
            reason = result["reason"]
            affected = result["affected_services"]
            
            results.append(ServiceConfigCheck(
                service_name="central_validator",
                config_key=config_key,
                is_required=not can_delete,
                can_delete=can_delete,
                impact_description=reason,
                affected_components=affected,
                migration_required="migration required" in reason.lower()
            ))
        except ImportError:
            logger.warning("Central validator not available")
        
        return results
    
    def _check_service_config(self, service_name: str, config_key: str) -> Optional[ServiceConfigCheck]:
        """Check configuration requirements for a specific service."""
        if service_name not in self.service_validators:
            return None
        
        validator_info = self.service_validators.get(service_name)
        if not validator_info:
            return None
        
        try:
            if service_name == "netra_backend":
                # Use backend's ConfigDependencyMap
                can_delete, reason = validator_info["class"].can_delete_config(config_key)
                impact_analysis = validator_info["class"].get_impact_analysis(config_key)
                
                return ServiceConfigCheck(
                    service_name=service_name,
                    config_key=config_key,
                    is_required=not can_delete,
                    can_delete=can_delete,
                    impact_description=reason,
                    affected_components=impact_analysis.get("affected_services", []),
                    migration_required=impact_analysis.get("deletion_requires", False),
                    migration_guide=impact_analysis.get("migration_guide")
                )
            
            elif service_name == "auth_service":
                # Auth service might have different pattern
                # For now, assume it's required if in CROSS_SERVICE_CONFIGS
                is_required = config_key in self.CROSS_SERVICE_CONFIGS
                
                return ServiceConfigCheck(
                    service_name=service_name,
                    config_key=config_key,
                    is_required=is_required,
                    can_delete=not is_required,
                    impact_description=f"Configuration used by {service_name}",
                    affected_components=["oauth", "authentication", "session_management"],
                    migration_required=False
                )
            
        except Exception as e:
            logger.error(f"Error checking {service_name} for {config_key}: {e}")
        
        return None
    
    def get_cross_service_impact_report(self, config_key: str) -> str:
        """
        Generate a comprehensive impact report for a configuration change.
        
        Args:
            config_key: The configuration key to analyze
            
        Returns:
            Formatted report string
        """
        checks = self.validate_config_deletion(config_key)
        
        report_lines = [
            "=" * 80,
            f"CROSS-SERVICE IMPACT ANALYSIS: {config_key}",
            "=" * 80,
            ""
        ]
        
        # Summary
        total_services = len(checks)
        blocking_services = sum(1 for c in checks if not c.can_delete)
        
        if blocking_services > 0:
            report_lines.append(f"⛔ DELETION BLOCKED by {blocking_services}/{total_services} services")
        else:
            report_lines.append(f"✅ Can be deleted - no critical dependencies found")
        
        report_lines.extend(["", "-" * 40, ""])
        
        # Detailed results
        for check in checks:
            status = "❌ REQUIRED" if check.is_required else "✅ Optional"
            
            report_lines.extend([
                f"Service: {check.service_name}",
                f"Status: {status}",
                f"Impact: {check.impact_description}",
            ])
            
            if check.affected_components:
                report_lines.append(f"Affected Components: {', '.join(check.affected_components)}")
            
            if check.migration_required and check.migration_guide:
                report_lines.extend([
                    "Migration Required: YES",
                    f"Migration Guide: {check.migration_guide}"
                ])
            
            report_lines.extend(["", "-" * 40, ""])
        
        # Check for legacy status
        try:
            from shared.configuration.central_config_validator import LegacyConfigMarker
            legacy_info = LegacyConfigMarker.get_legacy_info(config_key)
            
            if legacy_info:
                report_lines.extend([
                    "LEGACY STATUS:",
                    f"Deprecation Date: {legacy_info.get('deprecation_date', 'N/A')}",
                    f"Removal Version: {legacy_info.get('removal_version', 'N/A')}",
                    f"Replacement: {legacy_info.get('replacement', 'N/A')}",
                    f"Migration Guide: {legacy_info.get('migration_guide', 'N/A')}",
                ])
                
                if legacy_info.get("critical_security"):
                    report_lines.append("⚠️ SECURITY CRITICAL: This is a security-sensitive configuration!")
                
                report_lines.extend(["", "-" * 40, ""])
        except ImportError:
            pass
        
        return "\n".join(report_lines)
    
    def validate_environment_configs(self, environment: str, configs: Dict[str, Any]) -> List[str]:
        """
        Validate a set of configurations for a specific environment.
        
        Args:
            environment: The target environment (development, test, staging, production)
            configs: Dictionary of configuration key-value pairs
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        # Check for missing cross-service configs
        for config_key, required_services in self.CROSS_SERVICE_CONFIGS.items():
            if config_key not in configs or not configs[config_key]:
                # Check if it's environment-specific
                env_specific_key = f"{config_key}_{environment.upper()}"
                if env_specific_key not in configs or not configs[env_specific_key]:
                    issues.append(
                        f"Missing cross-service config: {config_key} " 
                        f"(required by: {', '.join(required_services)})"
                    )
        
        # Check for legacy configs
        try:
            from shared.configuration.central_config_validator import LegacyConfigMarker
            legacy_warnings = LegacyConfigMarker.check_legacy_usage(configs)
            issues.extend(legacy_warnings)
        except ImportError:
            pass
        
        # Check with backend validator
        try:
            from netra_backend.app.core.config_dependencies import ConfigDependencyMap
            consistency_issues = ConfigDependencyMap.check_config_consistency(configs)
            issues.extend(consistency_issues)
            
            legacy_issues = ConfigDependencyMap.check_legacy_configs(configs)
            issues.extend(legacy_issues)
        except ImportError:
            pass
        
        return issues
    
    def get_required_configs_for_service(self, service_name: str) -> Set[str]:
        """
        Get all required configuration keys for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Set of required configuration keys
        """
        required_configs = set()
        
        # Add configs from CROSS_SERVICE_CONFIGS
        for config_key, services in self.CROSS_SERVICE_CONFIGS.items():
            if service_name in services:
                required_configs.add(config_key)
        
        # Try to get service-specific requirements
        if service_name == "netra_backend":
            try:
                from netra_backend.app.core.config_dependencies import ConfigDependencyMap
                service_configs = ConfigDependencyMap.get_required_configs(service_name)
                required_configs.update(service_configs.keys())
            except ImportError:
                pass
        
        return required_configs
    
    def generate_service_config_report(self, service_name: str) -> str:
        """
        Generate a configuration requirements report for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Formatted report string
        """
        configs = self.get_required_configs_for_service(service_name)
        
        report_lines = [
            "=" * 80,
            f"CONFIGURATION REQUIREMENTS: {service_name}",
            "=" * 80,
            "",
            f"Total Required Configs: {len(configs)}",
            "",
            "Required Configuration Keys:",
            "-" * 40
        ]
        
        for config in sorted(configs):
            report_lines.append(f"  - {config}")
        
        return "\n".join(report_lines)
    
    @staticmethod
    def validate_oauth_configs(environment: str) -> Dict[str, Any]:
        """
        DEPRECATED: Validate OAuth configuration for a specific environment.
        
        This method now delegates to SSOT OAuth validation.
        Use shared.configuration.central_config_validator.validate_oauth_configs_for_environment() instead.
        
        Args:
            environment: The environment to validate (development, test, staging, production)
            
        Returns:
            Dict with 'valid' (bool) and 'errors' (list) keys
        """
        try:
            # SSOT OAuth validation - this replaces duplicate implementation
            from shared.configuration.central_config_validator import validate_oauth_configs_for_environment
            
            # Use SSOT OAuth validation
            return validate_oauth_configs_for_environment(environment)
            
        except ImportError:
            # Fallback if SSOT not available
            from shared.isolated_environment import get_env
            
            env = get_env()
            errors = ["SSOT OAuth validation not available - using deprecated fallback"]
            
            try:
                # Check for environment-specific OAuth credentials
                client_id_key = f"GOOGLE_OAUTH_CLIENT_ID_{environment.upper()}"
                client_secret_key = f"GOOGLE_OAUTH_CLIENT_SECRET_{environment.upper()}"
                
                client_id = env.get(client_id_key)
                client_secret = env.get(client_secret_key)
                
                # Validate client ID
                if not client_id:
                    errors.append(f"Missing {client_id_key} for {environment} environment")
                elif client_id in ["", "your-client-id", "REPLACE_WITH"]:
                    errors.append(f"Invalid {client_id_key} - contains placeholder value")
                
                # Validate client secret
                if not client_secret:
                    errors.append(f"Missing {client_secret_key} for {environment} environment")
                elif client_secret in ["", "your-client-secret", "REPLACE_WITH"]:
                    errors.append(f"Invalid {client_secret_key} - contains placeholder value")
                elif len(client_secret) < 10:
                    errors.append(f"Invalid {client_secret_key} - too short (minimum 10 characters)")
                
                # Additional validation for production/staging
                if environment.lower() in ['staging', 'production']:
                    # Check that we're not using development credentials in production
                    dev_client_id = env.get("GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT")
                    if client_id == dev_client_id and dev_client_id:
                        errors.append(f"Security issue: {environment} environment is using development OAuth credentials")
                
            except Exception as e:
                errors.append(f"OAuth validation error for {environment}: {str(e)}")
            
            return {
                "valid": len(errors) == 1,  # Only the deprecation warning
                "errors": errors
            }


# Convenience functions for direct usage
def validate_config_deletion_cross_service(config_key: str) -> Dict[str, Any]:
    """
    Check if a configuration can be deleted across all services.
    
    Args:
        config_key: Configuration key to check
        
    Returns:
        Dict with 'safe' (bool) and 'affected_services' (list) keys
    """
    validator = CrossServiceConfigValidator()
    checks = validator.validate_config_deletion(config_key)
    
    can_delete = all(c.can_delete for c in checks)
    affected_services = []
    for check in checks:
        affected_services.extend(check.affected_components)
        if check.service_name not in affected_services:
            affected_services.append(check.service_name)
    
    return {
        "safe": can_delete,
        "affected_services": list(set(affected_services))  # Remove duplicates
    }


def get_cross_service_config_report() -> str:
    """
    Generate a full cross-service configuration report.
    
    Returns:
        Formatted report of all cross-service configuration requirements
    """
    validator = CrossServiceConfigValidator()
    
    report_lines = [
        "=" * 80,
        "CROSS-SERVICE CONFIGURATION MAPPING",
        "=" * 80,
        ""
    ]
    
    for config_key, services in sorted(validator.CROSS_SERVICE_CONFIGS.items()):
        report_lines.append(f"{config_key}:")
        for service in services:
            report_lines.append(f"  - {service}")
        report_lines.append("")
    
    return "\n".join(report_lines)