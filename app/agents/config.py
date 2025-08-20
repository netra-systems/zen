"""Agent Configuration Module - Centralized configuration for all agents."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.schemas.shared_types import RetryConfig, BaseAgentConfig
from app.config import get_config


class AgentCacheConfig(BaseModel):
    """Configuration for caching behavior."""
    default_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    max_cache_size: int = Field(default=1000, description="Maximum cache entries")
    redis_ttl: int = Field(default=3600, description="Redis cache TTL in seconds")
    
    @classmethod
    def from_unified_config(cls) -> 'AgentCacheConfig':
        """Create config from unified configuration system."""
        config = get_config()
        return cls(
            default_ttl=getattr(config, 'agent_cache_ttl', 300),
            max_cache_size=getattr(config, 'agent_max_cache_size', 1000),
            redis_ttl=getattr(config, 'agent_redis_ttl', 3600)
        )


# RetryConfig now imported from shared_types.py


class TimeoutConfig(BaseModel):
    """Configuration for timeout behavior."""
    default_timeout: float = Field(default=30.0, description="Default operation timeout")
    long_timeout: float = Field(default=300.0, description="Long operation timeout")
    recovery_timeout: float = Field(default=30.0, description="Recovery timeout")
    
    @classmethod
    def from_unified_config(cls) -> 'TimeoutConfig':
        """Create config from unified configuration system."""
        config = get_config()
        return cls(
            default_timeout=getattr(config, 'agent_default_timeout', 30.0),
            long_timeout=getattr(config, 'agent_long_timeout', 300.0),
            recovery_timeout=getattr(config, 'agent_recovery_timeout', 45.0)
        )


class UserConfig(BaseModel):
    """Configuration for user handling."""
    default_user_id: str = Field(default="default_user", description="Default user ID")
    admin_user_id: str = Field(default="admin", description="Admin user ID")
    
    @classmethod
    def from_unified_config(cls) -> 'UserConfig':
        """Create config from unified configuration system."""
        config = get_config()
        return cls(
            default_user_id=getattr(config, 'agent_default_user_id', 'default_user'),
            admin_user_id=getattr(config, 'agent_admin_user_id', 'admin')
        )


class AgentConfig(BaseAgentConfig):
    """Extended agent configuration with additional components."""
    cache: AgentCacheConfig = Field(default_factory=AgentCacheConfig)
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig)
    user: UserConfig = Field(default_factory=UserConfig)
    
    @classmethod
    def from_unified_config(cls) -> 'AgentConfig':
        """Create complete config from unified configuration system."""
        config = get_config()
        return cls(
            cache=AgentCacheConfig.from_unified_config(),
            retry=RetryConfig(
                max_retries=getattr(config, 'agent_max_retries', 3),
                base_delay=getattr(config, 'agent_base_delay', 1.0),
                max_delay=getattr(config, 'agent_max_delay', 60.0),
                backoff_factor=getattr(config, 'agent_backoff_factor', 2.0)
            ),
            timeout=TimeoutConfig.from_unified_config(),
            user=UserConfig.from_unified_config(),
            failure_threshold=getattr(config, 'agent_failure_threshold', 3),
            reset_timeout=getattr(config, 'agent_reset_timeout', 30.0),
            max_concurrent_operations=getattr(config, 'agent_max_concurrent', 10),
            batch_size=getattr(config, 'agent_batch_size', 100)
        )


# Global configuration instance
agent_config = AgentConfig.from_unified_config()