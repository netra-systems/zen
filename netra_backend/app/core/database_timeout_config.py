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
            # CRITICAL FIX Issue #1278: VPC Connector Capacity Constraints - Further extended timeout configuration
            # Root cause analysis: Previous 45.0s still insufficient for compound infrastructure failures
            # New evidence from Issue #1278: VPC connector scaling + Cloud SQL capacity pressure creates compound delays
            # VPC connector capacity pressure: 30s delay during peak scaling events 
            # Cloud SQL resource constraints: 25s delay under concurrent connection pressure
            # Network latency amplification: 10s additional delay during infrastructure stress
            # Safety margin for cascading failures: 15s buffer
            "initialization_timeout": 75.0,    # CRITICAL: Extended to handle compound VPC+CloudSQL delays (increased from 45.0)
            "table_setup_timeout": 25.0,       # Extended for schema operations under load (increased from 15.0)
            "connection_timeout": 35.0,        # Extended for VPC connector peak scaling delays (increased from 25.0)
            "pool_timeout": 45.0,              # Extended for connection pool exhaustion + VPC delays (increased from 30.0)
            "health_check_timeout": 20.0,      # Extended for compound infrastructure health checks (increased from 15.0)
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
            # Pool configuration for Cloud SQL with capacity constraints (Issue #1278)
            "pool_config": {
                "pool_size": 10,              # Reduced to respect Cloud SQL connection limits (reduced from 15)
                "max_overflow": 15,           # Reduced to stay within 80% of Cloud SQL capacity (reduced from 25)
                "pool_timeout": 90.0,         # Extended for VPC connector + Cloud SQL delays (increased from 60.0)
                "pool_recycle": 3600,         # 1 hour recycle for stability
                "pool_pre_ping": True,        # Always verify connections
                "pool_reset_on_return": "rollback",  # Safe connection resets
                # New: VPC connector capacity awareness
                "vpc_connector_capacity_buffer": 5,   # Reserve connections for VPC connector scaling
                "cloud_sql_capacity_limit": 100,     # Track Cloud SQL instance connection limit
                "capacity_safety_margin": 0.8,       # Use only 80% of available connections
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


def get_vpc_connector_capacity_config(environment: str) -> Dict[str, any]:
    """Get VPC connector capacity configuration for Issue #1278.
    
    VPC connectors have throughput limits and scaling delays that affect
    database connection establishment under load conditions.
    
    Args:
        environment: Environment name
        
    Returns:
        Dictionary with VPC connector capacity configuration
    """
    if is_cloud_sql_environment(environment):
        return {
            "throughput_baseline_gbps": 2.0,      # VPC connector baseline throughput
            "throughput_max_gbps": 10.0,          # VPC connector maximum throughput
            "scaling_delay_seconds": 30.0,        # Time for VPC connector auto-scaling
            "concurrent_connection_limit": 50,    # Practical concurrent connection limit
            "capacity_pressure_threshold": 0.7,   # Threshold for capacity pressure monitoring
            "scaling_buffer_timeout": 20.0,       # Additional timeout during scaling events
            "monitoring_enabled": True,           # Enable VPC connector monitoring
            "capacity_aware_timeouts": True,      # Adjust timeouts based on VPC capacity
        }
    else:
        return {
            "throughput_baseline_gbps": None,     # No VPC connector in local/test
            "scaling_delay_seconds": 0.0,
            "concurrent_connection_limit": 1000,  # No practical limit for local
            "capacity_pressure_threshold": 1.0,
            "scaling_buffer_timeout": 0.0,
            "monitoring_enabled": False,
            "capacity_aware_timeouts": False,
        }


def calculate_capacity_aware_timeout(environment: str, base_timeout: float) -> float:
    """Calculate timeout with VPC connector capacity awareness.
    
    Adjusts base timeout based on VPC connector capacity constraints
    to prevent Issue #1278 recurrence.
    
    Args:
        environment: Environment name
        base_timeout: Base timeout value
        
    Returns:
        Adjusted timeout accounting for VPC connector capacity
    """
    vpc_config = get_vpc_connector_capacity_config(environment)
    
    if not vpc_config["capacity_aware_timeouts"]:
        return base_timeout
    
    # Add VPC connector scaling buffer
    scaling_buffer = vpc_config["scaling_buffer_timeout"]
    
    # Add capacity pressure buffer (20% increase under pressure)
    capacity_buffer = base_timeout * 0.2
    
    adjusted_timeout = base_timeout + scaling_buffer + capacity_buffer
    
    logger.debug(f"Timeout adjustment for {environment}: {base_timeout}s -> {adjusted_timeout}s "
                f"(scaling: +{scaling_buffer}s, capacity: +{capacity_buffer}s)")
    
    return adjusted_timeout


def log_timeout_configuration(environment: str) -> None:
    """Log the current timeout configuration for debugging.
    
    Args:
        environment: Environment name
    """
    timeout_config = get_database_timeout_config(environment)
    cloud_sql_config = get_cloud_sql_optimized_config(environment)
    retry_config = get_progressive_retry_config(environment)
    vpc_config = get_vpc_connector_capacity_config(environment)
    
    logger.info(f"Database Configuration Summary for {environment}:")
    logger.info(f"  Timeout Configuration: {timeout_config}")
    logger.info(f"  Cloud SQL Optimized: {is_cloud_sql_environment(environment)}")
    logger.info(f"  Pool Configuration: {cloud_sql_config['pool_config']}")
    logger.info(f"  Retry Configuration: {retry_config}")
    logger.info(f"  VPC Connector Configuration: {vpc_config}")