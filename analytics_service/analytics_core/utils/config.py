"""Analytics Configuration

Configuration management for analytics service.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsConfig:
    """Analytics service configuration"""
    
    # Service settings
    service_port: int = 8090
    service_host: str = "localhost"
    debug: bool = False
    
    # ClickHouse settings
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_database: str = "analytics"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_secure: bool = False
    
    # Redis settings
    redis_url: str = "redis://localhost:6379/2"
    redis_max_connections: int = 20
    
    # Processing settings
    batch_size: int = 100
    flush_interval_ms: int = 5000
    max_retries: int = 3
    retry_delay_seconds: int = 1
    max_events_per_user_per_minute: int = 1000
    
    # Privacy settings
    enable_privacy_filtering: bool = True
    hash_ip_addresses: bool = True
    sanitize_prompts: bool = True
    
    # Feature flags
    enable_analytics: bool = True
    enable_realtime_metrics: bool = True
    enable_hot_prompts: bool = True
    
    @classmethod
    def from_env(cls) -> 'AnalyticsConfig':
        """Create configuration from environment variables"""
        env = get_env()
        
        return cls(
            service_port=int(env.get('ANALYTICS_SERVICE_PORT', '8090')),
            service_host=env.get('ANALYTICS_SERVICE_HOST', 'localhost'),
            debug=env.get('ANALYTICS_DEBUG', 'false').lower() == 'true',
            
            clickhouse_host=env.get('CLICKHOUSE_HOST', 'localhost'),
            clickhouse_port=int(env.get('CLICKHOUSE_PORT', '9000')),
            clickhouse_database=env.get('CLICKHOUSE_DB', 'analytics'),
            clickhouse_user=env.get('CLICKHOUSE_USER', 'default'),
            clickhouse_password=env.get('CLICKHOUSE_PASSWORD', ''),
            clickhouse_secure=env.get('CLICKHOUSE_SECURE', 'false').lower() == 'true',
            
            redis_url=env.get('REDIS_ANALYTICS_URL', 'redis://localhost:6379/2'),
            redis_max_connections=int(env.get('REDIS_MAX_CONNECTIONS', '20')),
            
            batch_size=int(env.get('EVENT_BATCH_SIZE', '100')),
            flush_interval_ms=int(env.get('EVENT_FLUSH_INTERVAL_MS', '5000')),
            max_retries=int(env.get('EVENT_MAX_RETRIES', '3')),
            retry_delay_seconds=int(env.get('EVENT_RETRY_DELAY_SECONDS', '1')),
            max_events_per_user_per_minute=int(env.get('MAX_EVENTS_PER_USER_PER_MINUTE', '1000')),
            
            enable_privacy_filtering=env.get('ENABLE_PRIVACY_FILTERING', 'true').lower() == 'true',
            hash_ip_addresses=env.get('HASH_IP_ADDRESSES', 'true').lower() == 'true',
            sanitize_prompts=env.get('SANITIZE_PROMPTS', 'true').lower() == 'true',
            
            enable_analytics=env.get('ENABLE_ANALYTICS', 'true').lower() == 'true',
            enable_realtime_metrics=env.get('ENABLE_REALTIME_METRICS', 'true').lower() == 'true',
            enable_hot_prompts=env.get('ENABLE_HOT_PROMPTS', 'true').lower() == 'true',
        )
    
    def get_clickhouse_url(self) -> str:
        """Get ClickHouse connection URL"""
        protocol = "clickhouses" if self.clickhouse_secure else "clickhouse"
        auth_part = f"{self.clickhouse_user}:{self.clickhouse_password}@" if self.clickhouse_password else f"{self.clickhouse_user}@"
        return f"{protocol}://{auth_part}{self.clickhouse_host}:{self.clickhouse_port}/{self.clickhouse_database}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'service_port': self.service_port,
            'service_host': self.service_host,
            'debug': self.debug,
            'clickhouse_host': self.clickhouse_host,
            'clickhouse_port': self.clickhouse_port,
            'clickhouse_database': self.clickhouse_database,
            'clickhouse_user': self.clickhouse_user,
            'clickhouse_secure': self.clickhouse_secure,
            'redis_url': self.redis_url,
            'redis_max_connections': self.redis_max_connections,
            'batch_size': self.batch_size,
            'flush_interval_ms': self.flush_interval_ms,
            'max_retries': self.max_retries,
            'retry_delay_seconds': self.retry_delay_seconds,
            'max_events_per_user_per_minute': self.max_events_per_user_per_minute,
            'enable_privacy_filtering': self.enable_privacy_filtering,
            'hash_ip_addresses': self.hash_ip_addresses,
            'sanitize_prompts': self.sanitize_prompts,
            'enable_analytics': self.enable_analytics,
            'enable_realtime_metrics': self.enable_realtime_metrics,
            'enable_hot_prompts': self.enable_hot_prompts,
        }


# Global configuration instance
_config_instance: Optional[AnalyticsConfig] = None


def get_analytics_config(reload: bool = False) -> AnalyticsConfig:
    """Get analytics configuration singleton"""
    global _config_instance
    
    if _config_instance is None or reload:
        _config_instance = AnalyticsConfig.from_env()
        logger.info("Loaded analytics configuration from environment")
    
    return _config_instance


def validate_config(config: AnalyticsConfig) -> List[str]:
    """Validate analytics configuration"""
    errors = []
    
    # Validate service settings
    if config.service_port < 1 or config.service_port > 65535:
        errors.append("Invalid service port")
    
    # Validate ClickHouse settings
    if not config.clickhouse_host:
        errors.append("ClickHouse host is required")
    
    if config.clickhouse_port < 1 or config.clickhouse_port > 65535:
        errors.append("Invalid ClickHouse port")
    
    if not config.clickhouse_database:
        errors.append("ClickHouse database is required")
    
    # Validate Redis settings
    if not config.redis_url:
        errors.append("Redis URL is required")
    
    # Validate processing settings
    if config.batch_size < 1 or config.batch_size > 1000:
        errors.append("Batch size must be between 1 and 1000")
    
    if config.flush_interval_ms < 1000:
        errors.append("Flush interval must be at least 1000ms")
    
    if config.max_retries < 0 or config.max_retries > 10:
        errors.append("Max retries must be between 0 and 10")
    
    if config.max_events_per_user_per_minute < 1:
        errors.append("Max events per user per minute must be positive")
    
    return errors