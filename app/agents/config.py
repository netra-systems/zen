"""Agent Configuration Module - Centralized configuration for all agents."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import os

from app.schemas.shared_types import RetryConfig, AgentConfig as BaseAgentConfig


class CacheConfig(BaseModel):
    """Configuration for caching behavior."""
    default_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    max_cache_size: int = Field(default=1000, description="Maximum cache entries")
    redis_ttl: int = Field(default=3600, description="Redis cache TTL in seconds")
    
    @classmethod
    def from_env(cls) -> 'CacheConfig':
        """Create config from environment variables."""
        return cls(
            default_ttl=int(os.getenv('AGENT_CACHE_TTL', 300)),
            max_cache_size=int(os.getenv('AGENT_MAX_CACHE_SIZE', 1000)),
            redis_ttl=int(os.getenv('AGENT_REDIS_TTL', 3600))
        )


# RetryConfig now imported from shared_types.py


class TimeoutConfig(BaseModel):
    """Configuration for timeout behavior."""
    default_timeout: float = Field(default=30.0, description="Default operation timeout")
    long_timeout: float = Field(default=300.0, description="Long operation timeout")
    recovery_timeout: float = Field(default=30.0, description="Recovery timeout")
    
    @classmethod
    def from_env(cls) -> 'TimeoutConfig':
        """Create config from environment variables."""
        return cls(
            default_timeout=float(os.getenv('AGENT_DEFAULT_TIMEOUT', 30.0)),
            long_timeout=float(os.getenv('AGENT_LONG_TIMEOUT', 300.0)),
            recovery_timeout=float(os.getenv('AGENT_RECOVERY_TIMEOUT', 45.0))
        )


class UserConfig(BaseModel):
    """Configuration for user handling."""
    default_user_id: str = Field(default="default_user", description="Default user ID")
    admin_user_id: str = Field(default="admin", description="Admin user ID")
    
    @classmethod
    def from_env(cls) -> 'UserConfig':
        """Create config from environment variables."""
        return cls(
            default_user_id=os.getenv('AGENT_DEFAULT_USER_ID', 'default_user'),
            admin_user_id=os.getenv('AGENT_ADMIN_USER_ID', 'admin')
        )


class AgentConfig(BaseAgentConfig):
    """Extended agent configuration with additional components."""
    cache: CacheConfig = Field(default_factory=CacheConfig)
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig)
    user: UserConfig = Field(default_factory=UserConfig)
    
    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """Create complete config from environment variables."""
        return cls(
            cache=CacheConfig.from_env(),
            retry=RetryConfig(
                max_retries=int(os.getenv('AGENT_MAX_RETRIES', 3)),
                base_delay=float(os.getenv('AGENT_BASE_DELAY', 1.0)),
                max_delay=float(os.getenv('AGENT_MAX_DELAY', 60.0)),
                backoff_factor=float(os.getenv('AGENT_BACKOFF_FACTOR', 2.0))
            ),
            timeout=TimeoutConfig.from_env(),
            user=UserConfig.from_env(),
            failure_threshold=int(os.getenv('AGENT_FAILURE_THRESHOLD', 3)),
            reset_timeout=float(os.getenv('AGENT_RESET_TIMEOUT', 30.0)),
            max_concurrent_operations=int(os.getenv('AGENT_MAX_CONCURRENT', 10)),
            batch_size=int(os.getenv('AGENT_BATCH_SIZE', 100))
        )


# Global configuration instance
agent_config = AgentConfig.from_env()