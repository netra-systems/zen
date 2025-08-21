"""Configurable resilience policies for unified resilience framework.

This module provides enterprise-grade policy management with:
- Service-specific resilience configurations
- Environment-aware policy selection
- Dynamic policy updates and validation
- Integration with all resilience components

All functions are <=8 lines per MANDATORY requirements.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
import json

from app.logging_config import central_logger
from netra_backend.app.circuit_breaker import CircuitConfig
from netra_backend.app.retry_manager import RetryConfig, RetryPresets
from netra_backend.app.fallback import FallbackConfig, FallbackPresets
from netra_backend.app.monitor import AlertThreshold, AlertSeverity

logger = central_logger.get_logger(__name__)


class ServiceTier(Enum):
    """Service tier levels for policy assignment."""
    CRITICAL = "critical"
    ESSENTIAL = "essential"
    STANDARD = "standard"
    EXPERIMENTAL = "experimental"


class EnvironmentType(Enum):
    """Environment types for policy selection."""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TESTING = "testing"


@dataclass
class ResiliencePolicy:
    """Complete resilience policy for a service."""
    name: str
    service_tier: ServiceTier
    environment: EnvironmentType
    circuit_config: CircuitConfig
    retry_config: RetryConfig
    fallback_configs: List[FallbackConfig] = field(default_factory=list)
    alert_thresholds: List[AlertThreshold] = field(default_factory=list)
    enabled: bool = True
    
    def __post_init__(self) -> None:
        """Validate policy configuration."""
        self._validate_configs()
        self._validate_name()
    
    def _validate_configs(self) -> None:
        """Validate all configuration objects."""
        if not isinstance(self.circuit_config, CircuitConfig):
            raise ValueError("circuit_config must be CircuitConfig instance")
        if not isinstance(self.retry_config, RetryConfig):
            raise ValueError("retry_config must be RetryConfig instance")
    
    def _validate_name(self) -> None:
        """Validate policy name."""
        if not self.name or not self.name.strip():
            raise ValueError("Policy name cannot be empty")


@dataclass
class PolicyTemplate:
    """Template for creating resilience policies."""
    name: str
    description: str
    service_tier: ServiceTier
    circuit_defaults: Dict[str, Any] = field(default_factory=dict)
    retry_defaults: Dict[str, Any] = field(default_factory=dict)
    fallback_defaults: List[Dict[str, Any]] = field(default_factory=list)
    alert_defaults: List[Dict[str, Any]] = field(default_factory=list)


class UnifiedPolicyManager:
    """Enterprise resilience policy manager."""
    
    def __init__(self) -> None:
        self.policies: Dict[str, ResiliencePolicy] = {}
        self.templates: Dict[str, PolicyTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self) -> None:
        """Load default policy templates."""
        self._create_critical_template()
        self._create_essential_template()
        self._create_standard_template()
        self._create_experimental_template()
    
    def _get_critical_circuit_defaults(self) -> Dict[str, Any]:
        """Get circuit defaults for critical services."""
        return {
            "failure_threshold": 3,
            "recovery_timeout": 15.0,
            "timeout_seconds": 5.0,
            "adaptive_threshold": True
        }
    
    def _get_critical_retry_defaults(self) -> Dict[str, Any]:
        """Get retry defaults for critical services."""
        return {
            "max_attempts": 5,
            "base_delay": 0.5,
            "max_delay": 30.0
        }
    
    def _create_critical_template(self) -> None:
        """Create template for critical services."""
        template = PolicyTemplate(
            name="critical_service",
            description="High availability policy for critical services",
            service_tier=ServiceTier.CRITICAL,
            circuit_defaults=self._get_critical_circuit_defaults(),
            retry_defaults=self._get_critical_retry_defaults()
        )
        self.templates["critical_service"] = template
    
    def _get_essential_circuit_defaults(self) -> Dict[str, Any]:
        """Get circuit defaults for essential services."""
        return {
            "failure_threshold": 5,
            "recovery_timeout": 30.0,
            "timeout_seconds": 10.0,
            "adaptive_threshold": True
        }
    
    def _get_essential_retry_defaults(self) -> Dict[str, Any]:
        """Get retry defaults for essential services."""
        return {
            "max_attempts": 3,
            "base_delay": 1.0,
            "max_delay": 60.0
        }
    
    def _create_essential_template(self) -> None:
        """Create template for essential services."""
        template = PolicyTemplate(
            name="essential_service",
            description="Balanced policy for essential services",
            service_tier=ServiceTier.ESSENTIAL,
            circuit_defaults=self._get_essential_circuit_defaults(),
            retry_defaults=self._get_essential_retry_defaults()
        )
        self.templates["essential_service"] = template
    
    def _get_standard_circuit_defaults(self) -> Dict[str, Any]:
        """Get circuit defaults for standard services."""
        return {
            "failure_threshold": 10,
            "recovery_timeout": 60.0,
            "timeout_seconds": 15.0,
            "adaptive_threshold": False
        }
    
    def _get_standard_retry_defaults(self) -> Dict[str, Any]:
        """Get retry defaults for standard services."""
        return {
            "max_attempts": 2,
            "base_delay": 2.0,
            "max_delay": 120.0
        }
    
    def _create_standard_template(self) -> None:
        """Create template for standard services."""
        template = PolicyTemplate(
            name="standard_service",
            description="Standard policy for regular services",
            service_tier=ServiceTier.STANDARD,
            circuit_defaults=self._get_standard_circuit_defaults(),
            retry_defaults=self._get_standard_retry_defaults()
        )
        self.templates["standard_service"] = template
    
    def _get_experimental_circuit_defaults(self) -> Dict[str, Any]:
        """Get experimental circuit defaults."""
        return {
            "failure_threshold": 20,
            "recovery_timeout": 120.0,
            "timeout_seconds": 30.0,
            "adaptive_threshold": False
        }
    
    def _get_experimental_retry_defaults(self) -> Dict[str, Any]:
        """Get experimental retry defaults."""
        return {
            "max_attempts": 1,
            "base_delay": 5.0,
            "max_delay": 300.0
        }
    
    def _create_experimental_template(self) -> None:
        """Create template for experimental services."""
        template = PolicyTemplate(
            name="experimental_service",
            description="Lenient policy for experimental services",
            service_tier=ServiceTier.EXPERIMENTAL,
            circuit_defaults=self._get_experimental_circuit_defaults(),
            retry_defaults=self._get_experimental_retry_defaults()
        )
        self.templates["experimental_service"] = template
    
    def _validate_template_exists(self, template_name: str) -> PolicyTemplate:
        """Validate template exists and return it."""
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        return template
    
    def _build_policy_from_configs(
        self,
        service_name: str,
        template: PolicyTemplate,
        environment: EnvironmentType,
        circuit_config: CircuitConfig,
        retry_config: RetryConfig
    ) -> ResiliencePolicy:
        """Build policy from configurations."""
        return ResiliencePolicy(
            name=service_name,
            service_tier=template.service_tier,
            environment=environment,
            circuit_config=circuit_config,
            retry_config=retry_config
        )
    
    def create_policy_from_template(
        self, 
        service_name: str, 
        template_name: str, 
        environment: EnvironmentType,
        overrides: Optional[Dict[str, Any]] = None
    ) -> ResiliencePolicy:
        """Create policy from template with optional overrides."""
        template = self._validate_template_exists(template_name)
        circuit_config = self._create_circuit_config(service_name, template, overrides)
        retry_config = self._create_retry_config(template, overrides)
        policy = self._build_policy_from_configs(
            service_name, template, environment, circuit_config, retry_config
        )
        self.policies[service_name] = policy
        return policy
    
    def _apply_circuit_overrides(
        self, 
        config_dict: Dict[str, Any], 
        overrides: Optional[Dict[str, Any]]
    ) -> None:
        """Apply circuit configuration overrides."""
        if overrides and "circuit" in overrides:
            config_dict.update(overrides["circuit"])
    
    def _create_circuit_config(
        self, 
        service_name: str, 
        template: PolicyTemplate, 
        overrides: Optional[Dict[str, Any]]
    ) -> CircuitConfig:
        """Create circuit breaker config from template."""
        config_dict = template.circuit_defaults.copy()
        self._apply_circuit_overrides(config_dict, overrides)
        return CircuitConfig(name=service_name, **config_dict)
    
    def _apply_retry_overrides(
        self, 
        config_dict: Dict[str, Any], 
        overrides: Optional[Dict[str, Any]]
    ) -> None:
        """Apply retry configuration overrides."""
        if overrides and "retry" in overrides:
            config_dict.update(overrides["retry"])
    
    def _create_retry_config(
        self, 
        template: PolicyTemplate, 
        overrides: Optional[Dict[str, Any]]
    ) -> RetryConfig:
        """Create retry config from template."""
        config_dict = template.retry_defaults.copy()
        self._apply_retry_overrides(config_dict, overrides)
        return RetryConfig(**config_dict)
    
    def get_policy(self, service_name: str) -> Optional[ResiliencePolicy]:
        """Get policy for service."""
        return self.policies.get(service_name)
    
    def _apply_enabled_update(self, policy: ResiliencePolicy, updates: Dict[str, Any]) -> None:
        """Apply enabled status update."""
        if "enabled" in updates:
            policy.enabled = updates["enabled"]
    
    def _apply_config_updates(self, policy: ResiliencePolicy, updates: Dict[str, Any]) -> None:
        """Apply configuration updates to policy."""
        if "circuit" in updates:
            self._update_circuit_config(policy.circuit_config, updates["circuit"])
        if "retry" in updates:
            self._update_retry_config(policy.retry_config, updates["retry"])
    
    def update_policy(
        self, 
        service_name: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """Update existing policy."""
        policy = self.policies.get(service_name)
        if not policy:
            return False
        self._apply_enabled_update(policy, updates)
        self._apply_config_updates(policy, updates)
        logger.info(f"Updated policy for service: {service_name}")
        return True
    
    def _update_circuit_config(
        self, 
        config: CircuitConfig, 
        updates: Dict[str, Any]
    ) -> None:
        """Update circuit breaker configuration."""
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    def _update_retry_config(
        self, 
        config: RetryConfig, 
        updates: Dict[str, Any]
    ) -> None:
        """Update retry configuration."""
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    def remove_policy(self, service_name: str) -> bool:
        """Remove policy for service."""
        if service_name in self.policies:
            del self.policies[service_name]
            logger.info(f"Removed policy for service: {service_name}")
            return True
        return False
    
    def list_policies(self) -> List[str]:
        """List all registered policy names."""
        return list(self.policies.keys())
    
    def get_policies_by_tier(self, tier: ServiceTier) -> List[ResiliencePolicy]:
        """Get all policies for specific service tier."""
        return [p for p in self.policies.values() if p.service_tier == tier]
    
    def get_policies_by_environment(
        self, 
        environment: EnvironmentType
    ) -> List[ResiliencePolicy]:
        """Get all policies for specific environment."""
        return [p for p in self.policies.values() if p.environment == environment]
    
    def export_policies(self) -> Dict[str, Dict[str, Any]]:
        """Export all policies to dictionary."""
        exported = {}
        for name, policy in self.policies.items():
            exported[name] = self._policy_to_dict(policy)
        return exported
    
    def _policy_to_dict(self, policy: ResiliencePolicy) -> Dict[str, Any]:
        """Convert policy to dictionary."""
        return {
            "service_tier": policy.service_tier.value,
            "environment": policy.environment.value,
            "enabled": policy.enabled,
            "circuit_config": self._circuit_config_to_dict(policy.circuit_config),
            "retry_config": self._retry_config_to_dict(policy.retry_config)
        }
    
    def _circuit_config_to_dict(self, config: CircuitConfig) -> Dict[str, Any]:
        """Convert circuit config to dictionary."""
        return {
            "failure_threshold": config.failure_threshold,
            "recovery_timeout": config.recovery_timeout,
            "timeout_seconds": config.timeout_seconds,
            "adaptive_threshold": config.adaptive_threshold
        }
    
    def _retry_config_to_dict(self, config: RetryConfig) -> Dict[str, Any]:
        """Convert retry config to dictionary."""
        return {
            "max_attempts": config.max_attempts,
            "base_delay": config.base_delay,
            "max_delay": config.max_delay,
            "backoff_strategy": config.backoff_strategy.value
        }
    
    def _validate_circuit_timeout(self, policy: ResiliencePolicy, errors: List[str]) -> None:
        """Validate circuit timeout configuration."""
        if policy.circuit_config.timeout_seconds <= 0:
            errors.append("Circuit timeout must be positive")
    
    def _validate_retry_attempts(self, policy: ResiliencePolicy, errors: List[str]) -> None:
        """Validate retry attempts configuration."""
        if policy.retry_config.max_attempts <= 0:
            errors.append("Max retry attempts must be positive")
    
    def _validate_retry_delays(self, policy: ResiliencePolicy, errors: List[str]) -> None:
        """Validate retry delay configuration."""
        if policy.retry_config.base_delay >= policy.retry_config.max_delay:
            errors.append("Base delay must be less than max delay")
    
    def validate_policy(self, policy: ResiliencePolicy) -> List[str]:
        """Validate policy configuration."""
        errors: List[str] = []
        self._validate_circuit_timeout(policy, errors)
        self._validate_retry_attempts(policy, errors)
        self._validate_retry_delays(policy, errors)
        return errors
    
    def _calculate_policy_counts(self) -> tuple[int, int]:
        """Calculate total and enabled policy counts."""
        total_policies = len(self.policies)
        enabled_policies = sum(1 for p in self.policies.values() if p.enabled)
        return total_policies, enabled_policies
    
    def _calculate_tier_counts(self) -> Dict[str, int]:
        """Calculate policy counts by service tier."""
        tier_counts = {}
        for tier in ServiceTier:
            tier_counts[tier.value] = len(self.get_policies_by_tier(tier))
        return tier_counts
    
    def _build_summary_dict(
        self,
        total_policies: int,
        enabled_policies: int,
        tier_counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """Build summary dictionary from counts."""
        return {
            "total_policies": total_policies,
            "enabled_policies": enabled_policies,
            "disabled_policies": total_policies - enabled_policies,
            "policies_by_tier": tier_counts,
            "available_templates": list(self.templates.keys())
        }
    
    def get_policy_summary(self) -> Dict[str, Any]:
        """Get summary of all policies."""
        total_policies, enabled_policies = self._calculate_policy_counts()
        tier_counts = self._calculate_tier_counts()
        return self._build_summary_dict(total_policies, enabled_policies, tier_counts)


# Global policy manager instance
policy_manager = UnifiedPolicyManager()


# Predefined policy creation functions
def create_api_service_policy(
    service_name: str, 
    environment: EnvironmentType = EnvironmentType.PRODUCTION
) -> ResiliencePolicy:
    """Create policy for API services."""
    return policy_manager.create_policy_from_template(
        service_name, "essential_service", environment
    )


def create_database_service_policy(
    service_name: str, 
    environment: EnvironmentType = EnvironmentType.PRODUCTION
) -> ResiliencePolicy:
    """Create policy for database services."""
    return policy_manager.create_policy_from_template(
        service_name, "critical_service", environment
    )


def _get_llm_service_overrides() -> Dict[str, Dict[str, Any]]:
    """Get configuration overrides for LLM services."""
    return {
        "circuit": {"timeout_seconds": 30.0, "failure_threshold": 5},
        "retry": {"max_attempts": 4, "base_delay": 2.0, "max_delay": 120.0}
    }


def create_llm_service_policy(
    service_name: str, 
    environment: EnvironmentType = EnvironmentType.PRODUCTION
) -> ResiliencePolicy:
    """Create policy for LLM services."""
    overrides = _get_llm_service_overrides()
    return policy_manager.create_policy_from_template(
        service_name, "essential_service", environment, overrides
    )