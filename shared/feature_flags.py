"""
Production Feature Flags for Zero-Downtime Rollout
==================================================

This module provides a production-ready feature flag system for gradual rollout
of the isolation features with zero downtime and full rollback capabilities.

Business Value: Production Stability & Risk Mitigation
- Zero-downtime deployment of isolation features
- Gradual traffic rollout with monitoring
- Instant rollback capability
- Per-user isolation score monitoring

Key Features:
- Redis-backed feature flags for real-time control
- Per-user percentage-based rollout
- Circuit breaker pattern for safety
- Comprehensive metrics and monitoring
- Environment-aware configuration
"""

# MIGRATED: from netra_backend.app.services.redis_client import get_redis_client
import json
import time
import hashlib
import logging
from typing import Dict, Optional, Any, List, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager
import threading
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class RolloutStage(Enum):
    """Rollout stages for production deployment."""
    OFF = "off"                    # 0% - Features disabled
    INTERNAL_ONLY = "internal"     # Internal users only
    CANARY = "canary"             # 10% of traffic
    STAGED = "staged"             # 50% of traffic  
    FULL = "full"                 # 100% deployment


@dataclass
class FeatureFlagConfig:
    """Configuration for a feature flag."""
    name: str
    enabled: bool = False
    rollout_percentage: float = 0.0
    rollout_stage: RolloutStage = RolloutStage.OFF
    internal_users_only: bool = False
    circuit_breaker_threshold: float = 0.95  # Isolation score threshold
    circuit_breaker_open: bool = False
    last_updated: float = 0.0
    updated_by: str = "system"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.last_updated == 0.0:
            self.last_updated = time.time()


@dataclass 
class IsolationMetrics:
    """Metrics for request isolation monitoring."""
    total_requests: int = 0
    isolated_requests: int = 0
    failed_requests: int = 0
    cascade_failures: int = 0
    isolation_score: float = 1.0  # 0.0 to 1.0
    last_cascade_failure: Optional[float] = None
    error_rate: float = 0.0
    response_time_p95: float = 0.0
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class ProductionFeatureFlags:
    """
    Production-ready feature flag system with Redis backend.
    
    Provides zero-downtime rollout capabilities with monitoring and rollback.
    """
    
    def __init__(self, environment: Optional[str] = None):
        self.env = IsolatedEnvironment.get_instance()
        self.environment = environment or self.env.get("ENVIRONMENT", "development")
        self._redis_client = None
        self._lock = threading.RLock()
        
        # Configuration
        self.redis_prefix = f"feature_flags:{self.environment}"
        self.metrics_prefix = f"isolation_metrics:{self.environment}"
        self.internal_user_domains = {"netrasystems.ai", "netra.ai"}
        
        # Circuit breaker settings
        self.circuit_breaker_window_seconds = 300  # 5 minutes
        self.min_requests_for_circuit_breaker = 100
        
        logger.info(f"Initialized ProductionFeatureFlags for {self.environment}")

    @property
    def redis(self) -> redis.Redis:
        """Get Redis client with lazy initialization."""
        if self._redis_client is None:
            with self._lock:
                if self._redis_client is None:
                    redis_url = self.env.get("REDIS_URL")
                    if not redis_url:
                        # Fallback for development
                        redis_host = self.env.get("REDIS_HOST", "localhost")
                        redis_port = int(self.env.get("REDIS_PORT", "6379"))
                        redis_db = int(self.env.get("REDIS_DB", "0"))
                        self._redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(
                            host=redis_host,
                            port=redis_port,
                            db=redis_db,
                            decode_responses=True,
                            socket_connect_timeout=5,
                            socket_timeout=5
                        )
                    else:
                        self._redis_client = redis.from_url(
                            redis_url,
                            decode_responses=True,
                            socket_connect_timeout=5,
                            socket_timeout=5
                        )
        return self._redis_client

    def create_flag(self, name: str, config: FeatureFlagConfig) -> bool:
        """Create or update a feature flag."""
        try:
            key = f"{self.redis_prefix}:{name}"
            config.name = name
            config.last_updated = time.time()
            
            self.redis.hset(key, mapping=asdict(config))
            
            # Log flag creation
            logger.info(f"Feature flag created/updated: {name}", extra={
                "flag_name": name,
                "rollout_stage": config.rollout_stage.value,
                "rollout_percentage": config.rollout_percentage,
                "enabled": config.enabled
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create feature flag {name}: {e}")
            return False

    def get_flag(self, name: str) -> Optional[FeatureFlagConfig]:
        """Get feature flag configuration."""
        try:
            key = f"{self.redis_prefix}:{name}"
            data = self.redis.hgetall(key)
            
            if not data:
                return None
            
            # Convert Redis data back to FeatureFlagConfig
            config = FeatureFlagConfig(
                name=data.get("name", name),
                enabled=data.get("enabled", "false").lower() == "true",
                rollout_percentage=float(data.get("rollout_percentage", "0.0")),
                rollout_stage=RolloutStage(data.get("rollout_stage", "off")),
                internal_users_only=data.get("internal_users_only", "false").lower() == "true",
                circuit_breaker_threshold=float(data.get("circuit_breaker_threshold", "0.95")),
                circuit_breaker_open=data.get("circuit_breaker_open", "false").lower() == "true",
                last_updated=float(data.get("last_updated", "0.0")),
                updated_by=data.get("updated_by", "system"),
                metadata=json.loads(data.get("metadata", "{}"))
            )
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to get feature flag {name}: {e}")
            return None

    def is_enabled_for_user(self, flag_name: str, user_id: str, 
                           user_email: Optional[str] = None) -> bool:
        """
        Check if a feature flag is enabled for a specific user.
        
        Args:
            flag_name: Name of the feature flag
            user_id: User identifier
            user_email: User email (for internal user detection)
            
        Returns:
            True if the feature is enabled for this user
        """
        try:
            config = self.get_flag(flag_name)
            if not config:
                logger.warning(f"Feature flag not found: {flag_name}")
                return False
            
            # Check if flag is globally disabled
            if not config.enabled:
                return False
            
            # Check circuit breaker
            if config.circuit_breaker_open:
                logger.warning(f"Circuit breaker open for flag: {flag_name}")
                return False
            
            # Check isolation score threshold
            if not self._check_isolation_score_threshold(config.circuit_breaker_threshold):
                logger.warning(f"Isolation score below threshold for flag: {flag_name}")
                return False
            
            # Internal users only
            if config.internal_users_only:
                if user_email and self._is_internal_user(user_email):
                    return True
                else:
                    return False
            
            # Percentage-based rollout
            if config.rollout_percentage <= 0:
                return False
            
            if config.rollout_percentage >= 100:
                return True
            
            # Hash-based deterministic rollout
            user_hash = hashlib.md5(f"{flag_name}:{user_id}".encode()).hexdigest()
            hash_value = int(user_hash[:8], 16) % 10000
            threshold = config.rollout_percentage * 100
            
            return hash_value < threshold
            
        except Exception as e:
            logger.error(f"Error checking feature flag {flag_name} for user {user_id}: {e}")
            return False

    def _is_internal_user(self, email: str) -> bool:
        """Check if user is internal (Netra team member)."""
        if not email:
            return False
        
        domain = email.split("@")[-1].lower()
        return domain in self.internal_user_domains

    def _check_isolation_score_threshold(self, threshold: float) -> bool:
        """Check if current isolation score meets threshold."""
        try:
            metrics = self.get_current_isolation_metrics()
            if not metrics:
                # No metrics available - assume healthy
                return True
            
            return metrics.isolation_score >= threshold
            
        except Exception as e:
            logger.error(f"Error checking isolation score: {e}")
            return True  # Fail open

    def update_rollout_stage(self, flag_name: str, stage: RolloutStage, 
                           updated_by: str = "system") -> bool:
        """Update feature flag to a specific rollout stage."""
        try:
            config = self.get_flag(flag_name)
            if not config:
                logger.error(f"Feature flag not found: {flag_name}")
                return False
            
            # Update configuration based on stage
            config.rollout_stage = stage
            config.updated_by = updated_by
            config.last_updated = time.time()
            
            if stage == RolloutStage.OFF:
                config.enabled = False
                config.rollout_percentage = 0.0
                config.internal_users_only = False
                
            elif stage == RolloutStage.INTERNAL_ONLY:
                config.enabled = True
                config.rollout_percentage = 100.0
                config.internal_users_only = True
                
            elif stage == RolloutStage.CANARY:
                config.enabled = True
                config.rollout_percentage = 10.0
                config.internal_users_only = False
                
            elif stage == RolloutStage.STAGED:
                config.enabled = True
                config.rollout_percentage = 50.0
                config.internal_users_only = False
                
            elif stage == RolloutStage.FULL:
                config.enabled = True
                config.rollout_percentage = 100.0
                config.internal_users_only = False
            
            # Save updated configuration
            success = self.create_flag(flag_name, config)
            
            if success:
                logger.info(f"Updated rollout stage for {flag_name} to {stage.value}", extra={
                    "flag_name": flag_name,
                    "rollout_stage": stage.value,
                    "rollout_percentage": config.rollout_percentage,
                    "updated_by": updated_by
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update rollout stage for {flag_name}: {e}")
            return False

    def record_isolation_metrics(self, metrics: IsolationMetrics) -> bool:
        """Record isolation metrics for monitoring."""
        try:
            key = f"{self.metrics_prefix}:current"
            metrics.timestamp = time.time()
            
            # Store current metrics
            self.redis.hset(key, mapping=asdict(metrics))
            
            # Store historical data (last 24 hours)
            historical_key = f"{self.metrics_prefix}:history"
            timestamp = int(metrics.timestamp)
            self.redis.zadd(historical_key, {json.dumps(asdict(metrics)): timestamp})
            
            # Keep only last 24 hours of data
            cutoff = timestamp - (24 * 60 * 60)
            self.redis.zremrangebyscore(historical_key, 0, cutoff)
            
            # Check for circuit breaker conditions
            self._check_circuit_breaker_conditions(metrics)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record isolation metrics: {e}")
            return False

    def get_current_isolation_metrics(self) -> Optional[IsolationMetrics]:
        """Get current isolation metrics."""
        try:
            key = f"{self.metrics_prefix}:current"
            data = self.redis.hgetall(key)
            
            if not data:
                return None
            
            return IsolationMetrics(
                total_requests=int(data.get("total_requests", "0")),
                isolated_requests=int(data.get("isolated_requests", "0")),
                failed_requests=int(data.get("failed_requests", "0")),
                cascade_failures=int(data.get("cascade_failures", "0")),
                isolation_score=float(data.get("isolation_score", "1.0")),
                last_cascade_failure=float(data.get("last_cascade_failure", "0.0")) or None,
                error_rate=float(data.get("error_rate", "0.0")),
                response_time_p95=float(data.get("response_time_p95", "0.0")),
                timestamp=float(data.get("timestamp", "0.0"))
            )
            
        except Exception as e:
            logger.error(f"Failed to get isolation metrics: {e}")
            return None

    def _check_circuit_breaker_conditions(self, metrics: IsolationMetrics) -> None:
        """Check if circuit breaker should be triggered."""
        try:
            # Get all active feature flags
            pattern = f"{self.redis_prefix}:*"
            flag_keys = self.redis.keys(pattern)
            
            for key in flag_keys:
                flag_data = self.redis.hgetall(key)
                if not flag_data:
                    continue
                
                flag_name = flag_data.get("name", key.split(":")[-1])
                enabled = flag_data.get("enabled", "false").lower() == "true"
                threshold = float(flag_data.get("circuit_breaker_threshold", "0.95"))
                circuit_open = flag_data.get("circuit_breaker_open", "false").lower() == "true"
                
                if not enabled:
                    continue
                
                # Check isolation score threshold
                should_open = (
                    metrics.isolation_score < threshold and
                    metrics.total_requests >= self.min_requests_for_circuit_breaker
                )
                
                # Check error rate threshold
                if metrics.error_rate > 0.01:  # 1% error rate
                    should_open = True
                
                # Check cascade failure detection
                if metrics.cascade_failures > 0:
                    should_open = True
                
                # Update circuit breaker state if needed
                if should_open != circuit_open:
                    self.redis.hset(key, "circuit_breaker_open", str(should_open).lower())
                    
                    action = "opened" if should_open else "closed"
                    logger.warning(f"Circuit breaker {action} for flag: {flag_name}", extra={
                        "flag_name": flag_name,
                        "circuit_breaker_open": should_open,
                        "isolation_score": metrics.isolation_score,
                        "error_rate": metrics.error_rate,
                        "cascade_failures": metrics.cascade_failures
                    })
                    
        except Exception as e:
            logger.error(f"Error checking circuit breaker conditions: {e}")

    def get_all_flags(self) -> Dict[str, FeatureFlagConfig]:
        """Get all feature flags."""
        try:
            flags = {}
            pattern = f"{self.redis_prefix}:*"
            flag_keys = self.redis.keys(pattern)
            
            for key in flag_keys:
                flag_name = key.split(":")[-1]
                config = self.get_flag(flag_name)
                if config:
                    flags[flag_name] = config
            
            return flags
            
        except Exception as e:
            logger.error(f"Failed to get all flags: {e}")
            return {}

    def emergency_disable_all(self, reason: str, updated_by: str = "emergency") -> bool:
        """Emergency disable all feature flags."""
        try:
            logger.critical(f"EMERGENCY: Disabling all feature flags. Reason: {reason}", extra={
                "reason": reason,
                "updated_by": updated_by,
                "timestamp": time.time()
            })
            
            flags = self.get_all_flags()
            disabled_count = 0
            
            for flag_name, config in flags.items():
                if config.enabled:
                    config.enabled = False
                    config.rollout_percentage = 0.0
                    config.rollout_stage = RolloutStage.OFF
                    config.updated_by = updated_by
                    config.metadata["emergency_disable"] = {
                        "reason": reason,
                        "timestamp": time.time()
                    }
                    
                    if self.create_flag(flag_name, config):
                        disabled_count += 1
            
            logger.critical(f"Emergency disable completed. Disabled {disabled_count} flags.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to emergency disable flags: {e}")
            return False

    @contextmanager
    def rollout_context(self, flag_name: str, user_id: str, user_email: Optional[str] = None):
        """
        Context manager for feature flag usage with automatic metrics tracking.
        
        Usage:
            with feature_flags.rollout_context("request_isolation", user_id) as enabled:
                if enabled:
                    # New isolation logic
                    pass
                else:
                    # Legacy logic
                    pass
        """
        enabled = False
        start_time = time.time()
        error_occurred = False
        
        try:
            enabled = self.is_enabled_for_user(flag_name, user_id, user_email)
            yield enabled
            
        except Exception as e:
            error_occurred = True
            logger.error(f"Error in rollout context for {flag_name}: {e}")
            raise
            
        finally:
            # Record usage metrics
            try:
                duration = time.time() - start_time
                self._record_flag_usage(flag_name, user_id, enabled, error_occurred, duration)
            except Exception as e:
                logger.error(f"Failed to record flag usage metrics: {e}")

    def _record_flag_usage(self, flag_name: str, user_id: str, enabled: bool, 
                          error_occurred: bool, duration: float) -> None:
        """Record feature flag usage metrics."""
        try:
            usage_key = f"{self.redis_prefix}:usage:{flag_name}"
            timestamp = int(time.time())
            
            # Increment counters
            pipe = self.redis.pipeline()
            pipe.hincrby(usage_key, "total_uses", 1)
            
            if enabled:
                pipe.hincrby(usage_key, "enabled_uses", 1)
                
            if error_occurred:
                pipe.hincrby(usage_key, "error_count", 1)
            
            # Track response times (simplified histogram)
            if duration < 1.0:
                pipe.hincrby(usage_key, "fast_responses", 1)
            elif duration < 5.0:
                pipe.hincrby(usage_key, "medium_responses", 1)
            else:
                pipe.hincrby(usage_key, "slow_responses", 1)
            
            pipe.execute()
            
        except Exception as e:
            logger.error(f"Failed to record flag usage: {e}")


# Global instance for easy access
_feature_flags_instance = None
_instance_lock = threading.Lock()


def get_feature_flags() -> ProductionFeatureFlags:
    """Get the global ProductionFeatureFlags instance."""
    global _feature_flags_instance
    
    if _feature_flags_instance is None:
        with _instance_lock:
            if _feature_flags_instance is None:
                _feature_flags_instance = ProductionFeatureFlags()
    
    return _feature_flags_instance


# Convenience functions for common operations
def is_feature_enabled(flag_name: str, user_id: str, user_email: Optional[str] = None) -> bool:
    """Check if a feature is enabled for a user."""
    return get_feature_flags().is_enabled_for_user(flag_name, user_id, user_email)


def update_rollout_stage(flag_name: str, stage: RolloutStage, updated_by: str = "system") -> bool:
    """Update feature flag rollout stage."""
    return get_feature_flags().update_rollout_stage(flag_name, stage, updated_by)


def record_isolation_metrics(metrics: IsolationMetrics) -> bool:
    """Record isolation metrics."""
    return get_feature_flags().record_isolation_metrics(metrics)


def emergency_disable_all(reason: str, updated_by: str = "emergency") -> bool:
    """Emergency disable all feature flags."""
    return get_feature_flags().emergency_disable_all(reason, updated_by)