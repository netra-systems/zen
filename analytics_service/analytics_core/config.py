"""
Analytics Service Configuration
Handles environment variable loading and validation for analytics service

**UPDATED**: Uses analytics_service's own IsolatedEnvironment for unified environment management.
Follows SPEC/unified_environment_management.xml and SPEC/independent_services.xml for consistent 
environment access while maintaining complete microservice independence.
"""
import logging
from typing import Dict, Any

# Use analytics_service's own isolated environment management - NEVER import from other services
from analytics_service.analytics_core.isolated_environment import get_env

logger = logging.getLogger(__name__)

class AnalyticsConfig:
    """Centralized configuration for analytics service"""
    
    # Class-level attributes for settings compatibility
    _env = get_env()  # Use IsolatedEnvironment singleton
    ENVIRONMENT = _env.get("ENVIRONMENT", "development").lower()
    
    @staticmethod
    def get_environment() -> str:
        """Get current environment"""
        env = get_env().get("ENVIRONMENT", "development").lower()
        if env in ["staging", "production", "development", "test"]:
            return env
        return "development"
    
    @staticmethod
    def get_port() -> int:
        """Get analytics service port"""
        return int(get_env().get("ANALYTICS_SERVICE_PORT", 
                                get_env().get("PORT", "8090")))
    
    @staticmethod
    def get_clickhouse_url() -> str:
        """Get ClickHouse connection URL for analytics data storage"""
        env = AnalyticsConfig.get_environment()
        
        # Check for explicit URL first
        clickhouse_url = get_env().get("CLICKHOUSE_ANALYTICS_URL")
        if clickhouse_url:
            return clickhouse_url
        
        # Fallback construction for development/test
        if env in ["development", "test"]:
            host = get_env().get("CLICKHOUSE_HOST", "localhost")
            port = get_env().get("CLICKHOUSE_PORT", "8123")
            database = get_env().get("CLICKHOUSE_DATABASE", "analytics")
            return f"clickhouse://{host}:{port}/{database}"
        
        # Require explicit configuration in staging/production
        if env in ["staging", "production"]:
            raise ValueError(
                f"CLICKHOUSE_ANALYTICS_URL must be explicitly set in {env} environment"
            )
        
        return ""
    
    @staticmethod
    def get_clickhouse_user() -> str:
        """Get ClickHouse username"""
        return get_env().get("CLICKHOUSE_USER", "default")
    
    @staticmethod
    def get_clickhouse_password() -> str:
        """Get ClickHouse password"""
        password = get_env().get("CLICKHOUSE_PASSWORD", "")
        env = AnalyticsConfig.get_environment()
        
        # Require password in staging/production
        if env in ["staging", "production"] and not password:
            raise ValueError(f"CLICKHOUSE_PASSWORD must be set in {env} environment")
        
        return password
    
    @staticmethod
    def get_redis_url() -> str:
        """Get Redis URL for real-time caching and rate limiting"""
        env = AnalyticsConfig.get_environment()
        
        # Check for explicit URL first
        redis_url = get_env().get("REDIS_ANALYTICS_URL")
        if redis_url:
            return redis_url
        
        # Check for generic Redis URL
        redis_url = get_env().get("REDIS_URL")
        if redis_url:
            # Modify to use analytics database (typically db=2 for analytics)
            if redis_url.endswith("/0") or redis_url.count("/") == 3:
                # Replace database number with 2 for analytics
                base_url = redis_url.rsplit("/", 1)[0]
                return f"{base_url}/2"
            return redis_url
        
        # Fallback construction for development/test
        if env in ["development", "test"]:
            host = get_env().get("REDIS_HOST", "localhost")
            port = get_env().get("REDIS_PORT", "6379")
            return f"redis://{host}:{port}/2"
        
        # Require explicit configuration in staging/production
        if env in ["staging", "production"]:
            raise ValueError(
                f"REDIS_ANALYTICS_URL must be explicitly set in {env} environment"
            )
        
        return ""
    
    @staticmethod
    def get_event_batch_size() -> int:
        """Get event batch size for processing"""
        return int(get_env().get("EVENT_BATCH_SIZE", "100"))
    
    @staticmethod
    def get_event_flush_interval_ms() -> int:
        """Get event flush interval in milliseconds"""
        return int(get_env().get("EVENT_FLUSH_INTERVAL_MS", "5000"))
    
    @staticmethod
    def get_max_events_per_user_per_minute() -> int:
        """Get rate limit for events per user per minute"""
        return int(get_env().get("MAX_EVENTS_PER_USER_PER_MINUTE", "1000"))
    
    @staticmethod
    def get_grafana_api_url() -> str:
        """Get Grafana API URL for dashboard integration"""
        env = AnalyticsConfig.get_environment()
        
        grafana_url = get_env().get("GRAFANA_API_URL")
        if grafana_url:
            return grafana_url
        
        # Environment-specific defaults
        if env == "staging":
            return "https://grafana.staging.netrasystems.ai"
        elif env == "production":
            return "https://grafana.netrasystems.ai"
        
        # Development/test default
        return get_env().get("GRAFANA_URL", "http://localhost:3000")
    
    @staticmethod
    def get_data_retention_days() -> int:
        """Get data retention period in days"""
        return int(get_env().get("ANALYTICS_DATA_RETENTION_DAYS", "90"))
    
    @staticmethod
    def get_aggregated_data_retention_days() -> int:
        """Get aggregated data retention period in days"""
        return int(get_env().get("ANALYTICS_AGGREGATED_RETENTION_DAYS", "730"))  # 2 years
    
    @staticmethod
    def is_privacy_mode_enabled() -> bool:
        """Check if privacy mode is enabled (enhanced PII filtering)"""
        return get_env().get("ANALYTICS_PRIVACY_MODE", "true").lower() == "true"
    
    @staticmethod
    def get_event_validation_level() -> str:
        """Get event validation level (strict/normal/permissive)"""
        level = get_env().get("EVENT_VALIDATION_LEVEL", "normal").lower()
        if level in ["strict", "normal", "permissive"]:
            return level
        return "normal"
    
    @staticmethod
    def get_cors_origins() -> list:
        """Get CORS origins for analytics API"""
        env = AnalyticsConfig.get_environment()
        
        origins = get_env().get("ANALYTICS_CORS_ORIGINS", "")
        if origins:
            return [origin.strip() for origin in origins.split(",")]
        
        # Environment-specific defaults
        if env == "staging":
            return [
                "https://app.staging.netrasystems.ai",
                "https://api.staging.netrasystems.ai"
            ]
        elif env == "production":
            return [
                "https://netrasystems.ai",
                "https://app.netrasystems.ai",
                "https://api.netrasystems.ai"
            ]
        
        # Development/test - allow localhost
        return [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080"
        ]
    
    @staticmethod
    def get_service_health_check_interval() -> int:
        """Get health check interval in seconds"""
        return int(get_env().get("HEALTH_CHECK_INTERVAL_SECONDS", "30"))
    
    @staticmethod
    def is_debug_mode() -> bool:
        """Check if debug mode is enabled"""
        return get_env().get("DEBUG", "false").lower() == "true"
    
    @staticmethod
    def get_log_level() -> str:
        """Get logging level"""
        level = get_env().get("LOG_LEVEL", "INFO").upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        return level if level in valid_levels else "INFO"
    
    @staticmethod
    def validate_configuration() -> Dict[str, Any]:
        """Validate analytics service configuration"""
        env_manager = get_env()
        validation = env_manager.validate_analytics_configuration()
        
        # Additional service-specific validations
        env = AnalyticsConfig.get_environment()
        
        # Check critical service URLs
        try:
            clickhouse_url = AnalyticsConfig.get_clickhouse_url()
            if not clickhouse_url and env in ["staging", "production"]:
                validation["valid"] = False
                validation["issues"].append("ClickHouse URL is required in staging/production")
        except ValueError as e:
            validation["valid"] = False
            validation["issues"].append(f"ClickHouse configuration error: {str(e)}")
        
        try:
            redis_url = AnalyticsConfig.get_redis_url()
            if not redis_url and env in ["staging", "production"]:
                validation["valid"] = False
                validation["issues"].append("Redis URL is required in staging/production")
        except ValueError as e:
            validation["valid"] = False
            validation["issues"].append(f"Redis configuration error: {str(e)}")
        
        # Validate rate limiting parameters
        max_events = AnalyticsConfig.get_max_events_per_user_per_minute()
        if max_events < 1 or max_events > 10000:
            validation["warnings"].append(f"MAX_EVENTS_PER_USER_PER_MINUTE={max_events} may be too restrictive or permissive")
        
        # Validate batch processing parameters
        batch_size = AnalyticsConfig.get_event_batch_size()
        if batch_size < 1 or batch_size > 1000:
            validation["warnings"].append(f"EVENT_BATCH_SIZE={batch_size} may impact performance")
        
        flush_interval = AnalyticsConfig.get_event_flush_interval_ms()
        if flush_interval < 100 or flush_interval > 60000:
            validation["warnings"].append(f"EVENT_FLUSH_INTERVAL_MS={flush_interval} may impact real-time processing")
        
        return validation
    
    @staticmethod
    def log_configuration():
        """Log current configuration (without secrets)"""
        env = AnalyticsConfig.get_environment()
        logger.info(f"Analytics Service Configuration:")
        logger.info(f"  Environment: {env}")
        logger.info(f"  Port: {AnalyticsConfig.get_port()}")
        logger.info(f"  Debug Mode: {AnalyticsConfig.is_debug_mode()}")
        logger.info(f"  Log Level: {AnalyticsConfig.get_log_level()}")
        
        # Log service URLs (masked for security)
        clickhouse_url = AnalyticsConfig.get_clickhouse_url()
        redis_url = AnalyticsConfig.get_redis_url()
        grafana_url = AnalyticsConfig.get_grafana_api_url()
        
        logger.info(f"  ClickHouse URL: {AnalyticsConfig._mask_url(clickhouse_url)}")
        logger.info(f"  Redis URL: {AnalyticsConfig._mask_url(redis_url)}")
        logger.info(f"  Grafana URL: {AnalyticsConfig._mask_url(grafana_url)}")
        
        # Log processing configuration
        logger.info(f"  Event Batch Size: {AnalyticsConfig.get_event_batch_size()}")
        logger.info(f"  Event Flush Interval: {AnalyticsConfig.get_event_flush_interval_ms()}ms")
        logger.info(f"  Max Events per User/Minute: {AnalyticsConfig.get_max_events_per_user_per_minute()}")
        
        # Log data retention
        logger.info(f"  Data Retention: {AnalyticsConfig.get_data_retention_days()} days")
        logger.info(f"  Aggregated Data Retention: {AnalyticsConfig.get_aggregated_data_retention_days()} days")
        
        # Log privacy settings
        logger.info(f"  Privacy Mode: {AnalyticsConfig.is_privacy_mode_enabled()}")
        logger.info(f"  Event Validation Level: {AnalyticsConfig.get_event_validation_level()}")
        
        # Log CORS origins count
        origins = AnalyticsConfig.get_cors_origins()
        logger.info(f"  CORS Origins: {len(origins)} configured")
    
    @staticmethod
    def _mask_url(url: str) -> str:
        """Mask sensitive parts of URLs for logging"""
        if not url:
            return "NOT SET"
        
        # Mask passwords in URLs
        import re
        # Match patterns like://user:password@host
        masked = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', url)
        
        # If no credentials, just show the basic structure
        if masked == url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                return f"{parsed.scheme}://{parsed.netloc}/{parsed.path.lstrip('/')}"
            except:
                # Fallback: just hide query parameters and fragments
                return url.split('?')[0].split('#')[0]
        
        return masked


def get_config() -> AnalyticsConfig:
    """Get analytics service configuration instance.
    
    Provides compatibility with test imports that expect get_config function.
    Returns a singleton instance of AnalyticsConfig for consistent configuration access.
    """
    return AnalyticsConfig()