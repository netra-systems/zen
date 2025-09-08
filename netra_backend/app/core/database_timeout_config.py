"""
Database Timeout Configuration - Environment-Aware Timeout Settings

This module provides environment-specific database timeout configurations
to handle different connection requirements for local development vs. Cloud SQL.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Staging Environment Stability
- Value Impact: Ensures database connections work reliably across all environments
- Strategic Impact: Prevents staging deployment failures and enables reliable CI/CD
"""

from typing import Dict
import logging

logger = logging.getLogger(__name__)


def get_database_timeout_config(environment: str) -> Dict[str, float]:
    """Get database timeout configuration based on environment.
    
    Different environments have different connection characteristics:
    - Local development: Fast localhost connections
    - Test: Memory databases or fast local connections  
    - Staging: Cloud SQL requires more time for socket establishment
    - Production: Cloud SQL with high availability requirements
    
    Args:
        environment: Environment name (development, test, staging, production)
        
    Returns:
        Dictionary with timeout values in seconds
    """
    environment = environment.lower() if environment else "development"
    
    timeout_configs = {
        "development": {
            "initialization_timeout": 30.0,    # Local PostgreSQL is fast
            "table_setup_timeout": 15.0,       # Local database operations
            "connection_timeout": 20.0,        # Quick connection establishment
            "pool_timeout": 30.0,              # Connection pool operations
            "health_check_timeout": 10.0,      # Health check queries
        },
        "test": {
            "initialization_timeout": 25.0,    # Memory DB or test containers
            "table_setup_timeout": 10.0,       # Test operations should be fast
            "connection_timeout": 15.0,        # Test connections
            "pool_timeout": 20.0,              # Minimal pool operations
            "health_check_timeout": 5.0,       # Fast test health checks
        },
        "staging": {
            # CRITICAL: Staging uses Cloud SQL which requires more time
            "initialization_timeout": 60.0,    # Cloud SQL socket establishment
            "table_setup_timeout": 30.0,       # Cloud SQL table operations
            "connection_timeout": 45.0,        # Unix socket + SSL negotiation
            "pool_timeout": 50.0,              # Connection pool with Cloud SQL
            "health_check_timeout": 20.0,      # Cloud SQL health checks
        },
        "production": {
            # CRITICAL: Production needs maximum reliability
            "initialization_timeout": 90.0,    # High availability requirements
            "table_setup_timeout": 45.0,       # Production stability
            "connection_timeout": 60.0,        # Robust connection handling
            "pool_timeout": 70.0,              # Production connection pool
            "health_check_timeout": 30.0,      # Comprehensive health checks
        }
    }
    
    config = timeout_configs.get(environment, timeout_configs["development"])
    
    logger.debug(f"Database timeout configuration for {environment}: {config}")
    
    return config


def get_cloud_sql_optimized_config(environment: str) -> Dict[str, any]:
    """Get Cloud SQL specific configuration optimizations.
    
    Cloud SQL connections have different characteristics than TCP connections:
    - Uses Unix sockets (/cloudsql/...) instead of TCP
    - Requires specific connection parameters for optimal performance
    - Benefits from larger connection pools due to higher latency
    
    Args:
        environment: Environment name
        
    Returns:
        Dictionary with Cloud SQL specific configuration
    """
    if environment.lower() in ["staging", "production"]:
        return {
            # Connection arguments optimized for Cloud SQL
            "connect_args": {
                "server_settings": {
                    "application_name": f"netra_{environment}",
                    # Cloud SQL optimized keepalives
                    "tcp_keepalives_idle": "600",    # 10 minutes
                    "tcp_keepalives_interval": "30", # 30 seconds  
                    "tcp_keepalives_count": "3",     # 3 failed probes
                    # Connection optimization
                    "statement_timeout": "300000",   # 5 minutes for long operations
                    "idle_in_transaction_session_timeout": "300000",  # 5 minutes
                }
            },
            # Pool configuration for Cloud SQL
            "pool_config": {
                "pool_size": 15,              # Larger pool for Cloud SQL latency
                "max_overflow": 25,           # Higher overflow for bursts
                "pool_timeout": 60.0,         # Longer timeout for Cloud SQL
                "pool_recycle": 3600,         # 1 hour recycle for stability
                "pool_pre_ping": True,        # Always verify connections
                "pool_reset_on_return": "rollback",  # Safe connection resets
            }
        }
    else:
        # Development/test configuration
        return {
            "connect_args": {
                "server_settings": {
                    "application_name": f"netra_{environment}",
                }
            },
            "pool_config": {
                "pool_size": 5,
                "max_overflow": 10, 
                "pool_timeout": 30.0,
                "pool_recycle": 3600,
                "pool_pre_ping": True,
                "pool_reset_on_return": "rollback",
            }
        }


def is_cloud_sql_environment(environment: str) -> bool:
    """Check if environment typically uses Cloud SQL.
    
    Args:
        environment: Environment name
        
    Returns:
        True if environment typically uses Cloud SQL
    """
    return environment.lower() in ["staging", "production"]


def get_progressive_retry_config(environment: str) -> Dict[str, any]:
    """Get progressive retry configuration for database connections.
    
    Different environments need different retry strategies:
    - Local: Fast retries with short delays
    - Cloud SQL: Slower retries with exponential backoff
    
    Args:
        environment: Environment name
        
    Returns:
        Dictionary with retry configuration
    """
    if is_cloud_sql_environment(environment):
        return {
            "max_retries": 5,
            "base_delay": 2.0,      # Start with 2 second delay
            "max_delay": 30.0,      # Cap at 30 seconds
            "exponential_base": 2,  # Double delay each retry
            "jitter": True,         # Add randomization to prevent thundering herd
        }
    else:
        return {
            "max_retries": 3,
            "base_delay": 1.0,      # Start with 1 second delay
            "max_delay": 10.0,      # Cap at 10 seconds  
            "exponential_base": 2,
            "jitter": True,
        }


def log_timeout_configuration(environment: str) -> None:
    """Log the current timeout configuration for debugging.
    
    Args:
        environment: Environment name
    """
    timeout_config = get_database_timeout_config(environment)
    cloud_sql_config = get_cloud_sql_optimized_config(environment)
    retry_config = get_progressive_retry_config(environment)
    
    logger.info(f"Database Configuration Summary for {environment}:")
    logger.info(f"  Timeout Configuration: {timeout_config}")
    logger.info(f"  Cloud SQL Optimized: {is_cloud_sql_environment(environment)}")
    logger.info(f"  Pool Configuration: {cloud_sql_config['pool_config']}")
    logger.info(f"  Retry Configuration: {retry_config}")