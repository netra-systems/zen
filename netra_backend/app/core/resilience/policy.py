"""Policy Management for Unified Resilience Framework

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: System Stability - Define resilience policies per environment
- Value Impact: Ensures appropriate resilience behavior for different service tiers
- Strategic Impact: Enables consistent resilience policies across all services

This module provides policy templates and management for resilience behavior.
"""

from enum import Enum
from typing import Dict, Any, Optional

from pydantic import BaseModel
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class EnvironmentType(str, Enum):
    """Environment types for policy configuration."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ServiceTier(str, Enum):
    """Service tier classifications."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResiliencePolicy(BaseModel):
    """Resilience policy configuration."""
    name: str
    environment: EnvironmentType
    service_tier: ServiceTier
    circuit_breaker_enabled: bool = True
    circuit_failure_threshold: int = 5
    circuit_timeout_seconds: float = 30.0
    retry_enabled: bool = True
    retry_max_attempts: int = 3
    retry_backoff_seconds: float = 1.0
    fallback_enabled: bool = True
    fallback_timeout_seconds: float = 5.0
    monitoring_enabled: bool = True
    alert_threshold: int = 3


class PolicyTemplate:
    """Predefined policy templates for different service types."""
    
    @staticmethod
    def create_api_service_policy(environment: EnvironmentType, service_tier: ServiceTier = ServiceTier.MEDIUM) -> ResiliencePolicy:
        """Create a policy template for API services."""
        policies = {
            EnvironmentType.PRODUCTION: {
                ServiceTier.CRITICAL: ResiliencePolicy(
                    name="api_critical_production",
                    environment=environment,
                    service_tier=service_tier,
                    circuit_failure_threshold=3,
                    circuit_timeout_seconds=10.0,
                    retry_max_attempts=5,
                    retry_backoff_seconds=0.5
                ),
                ServiceTier.HIGH: ResiliencePolicy(
                    name="api_high_production", 
                    environment=environment,
                    service_tier=service_tier,
                    circuit_failure_threshold=5,
                    circuit_timeout_seconds=30.0,
                    retry_max_attempts=3,
                    retry_backoff_seconds=1.0
                ),
                ServiceTier.MEDIUM: ResiliencePolicy(
                    name="api_medium_production",
                    environment=environment,
                    service_tier=service_tier,
                    circuit_failure_threshold=10,
                    circuit_timeout_seconds=60.0,
                    retry_max_attempts=2,
                    retry_backoff_seconds=2.0
                ),
            },
            EnvironmentType.STAGING: {
                ServiceTier.MEDIUM: ResiliencePolicy(
                    name="api_staging",
                    environment=environment,
                    service_tier=service_tier,
                    circuit_failure_threshold=10,
                    circuit_timeout_seconds=60.0,
                    retry_max_attempts=2,
                    retry_backoff_seconds=1.0
                ),
            },
            EnvironmentType.DEVELOPMENT: {
                ServiceTier.MEDIUM: ResiliencePolicy(
                    name="api_development",
                    environment=environment,
                    service_tier=service_tier,
                    circuit_breaker_enabled=False,
                    retry_max_attempts=1,
                    fallback_enabled=False,
                    monitoring_enabled=False
                ),
            },
            EnvironmentType.TESTING: {
                ServiceTier.MEDIUM: ResiliencePolicy(
                    name="api_testing",
                    environment=environment,
                    service_tier=service_tier,
                    circuit_breaker_enabled=False,
                    retry_max_attempts=1,
                    fallback_enabled=False,
                    monitoring_enabled=False
                ),
            }
        }
        
        return policies.get(environment, {}).get(service_tier, policies[EnvironmentType.DEVELOPMENT][ServiceTier.MEDIUM])
    
    @staticmethod
    def create_database_service_policy(environment: EnvironmentType, service_tier: ServiceTier = ServiceTier.CRITICAL) -> ResiliencePolicy:
        """Create a policy template for database services."""
        base_policy = PolicyTemplate.create_api_service_policy(environment, service_tier)
        base_policy.name = f"database_{service_tier.value}_{environment.value}"
        base_policy.circuit_failure_threshold = max(2, base_policy.circuit_failure_threshold // 2)  # More sensitive for DB
        base_policy.retry_max_attempts = min(2, base_policy.retry_max_attempts)  # Fewer retries for DB
        return base_policy
    
    @staticmethod
    def create_llm_service_policy(environment: EnvironmentType, service_tier: ServiceTier = ServiceTier.HIGH) -> ResiliencePolicy:
        """Create a policy template for LLM services."""
        base_policy = PolicyTemplate.create_api_service_policy(environment, service_tier)
        base_policy.name = f"llm_{service_tier.value}_{environment.value}"
        base_policy.circuit_timeout_seconds = base_policy.circuit_timeout_seconds * 2  # LLM calls take longer
        base_policy.retry_backoff_seconds = base_policy.retry_backoff_seconds * 2  # Longer backoff for LLM
        base_policy.fallback_timeout_seconds = 10.0  # Longer fallback timeout for LLM
        return base_policy


class UnifiedPolicyManager:
    """Manages resilience policies for all services."""
    
    def __init__(self):
        """Initialize policy manager."""
        self._logger = logger
        self._policies: Dict[str, ResiliencePolicy] = {}
        self._service_policies: Dict[str, str] = {}  # service_name -> policy_name mapping
    
    def register_policy(self, policy: ResiliencePolicy) -> None:
        """Register a resilience policy."""
        self._policies[policy.name] = policy
        self._logger.info(f"Registered policy: {policy.name}")
    
    def assign_policy_to_service(self, service_name: str, policy_name: str) -> None:
        """Assign a policy to a service."""
        if policy_name not in self._policies:
            raise ValueError(f"Policy {policy_name} not found")
        
        self._service_policies[service_name] = policy_name
        self._logger.info(f"Assigned policy {policy_name} to service {service_name}")
    
    def get_policy(self, policy_name: str) -> Optional[ResiliencePolicy]:
        """Get a policy by name."""
        return self._policies.get(policy_name)
    
    def get_service_policy(self, service_name: str) -> Optional[ResiliencePolicy]:
        """Get the policy assigned to a service."""
        policy_name = self._service_policies.get(service_name)
        if policy_name:
            return self._policies.get(policy_name)
        return None
    
    def list_policies(self) -> Dict[str, ResiliencePolicy]:
        """List all registered policies."""
        return self._policies.copy()
    
    def remove_policy(self, policy_name: str) -> bool:
        """Remove a policy."""
        if policy_name in self._policies:
            del self._policies[policy_name]
            # Remove service assignments for this policy
            services_to_update = [s for s, p in self._service_policies.items() if p == policy_name]
            for service in services_to_update:
                del self._service_policies[service]
            self._logger.info(f"Removed policy: {policy_name}")
            return True
        return False


# Convenience functions for creating common policies
def create_api_service_policy(environment: EnvironmentType, service_tier: ServiceTier = ServiceTier.MEDIUM) -> ResiliencePolicy:
    """Create an API service policy."""
    return PolicyTemplate.create_api_service_policy(environment, service_tier)


def create_database_service_policy(environment: EnvironmentType, service_tier: ServiceTier = ServiceTier.CRITICAL) -> ResiliencePolicy:
    """Create a database service policy."""
    return PolicyTemplate.create_database_service_policy(environment, service_tier)


def create_llm_service_policy(environment: EnvironmentType, service_tier: ServiceTier = ServiceTier.HIGH) -> ResiliencePolicy:
    """Create an LLM service policy."""
    return PolicyTemplate.create_llm_service_policy(environment, service_tier)


# Global policy manager instance
policy_manager = UnifiedPolicyManager()


# Export all classes and functions
__all__ = [
    "EnvironmentType",
    "ServiceTier", 
    "ResiliencePolicy",
    "PolicyTemplate",
    "UnifiedPolicyManager",
    "create_api_service_policy",
    "create_database_service_policy", 
    "create_llm_service_policy",
    "policy_manager",
]