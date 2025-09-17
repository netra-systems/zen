"""PostgreSQL configuration and connection parameters module.

⚠️  DEPRECATED - SSOT REMEDIATION NOTICE (Issue #1075)
This file contains duplicate configuration that violates SSOT principles.
Use netra_backend.app.config.get_config() instead for all configuration access.

This file will be removed in a future release.
Migration guide: All configuration should use the unified SSOT configuration system.
"""
import warnings

warnings.warn(
    "postgres_config.py is deprecated. Use netra_backend.app.config.get_config() instead.",
    DeprecationWarning,
    stacklevel=2
)

from typing import Optional


class DatabaseConfig:
    """Database configuration with enhanced connection pooling settings."""
    # Production-optimized pool settings
    POOL_SIZE = 20  # Increased base pool size for production loads
    MAX_OVERFLOW = 30  # Allow more overflow connections under load
    POOL_TIMEOUT = 30  # Timeout waiting for connection from pool
    POOL_RECYCLE = 1800  # Recycle connections every 30 minutes
    POOL_PRE_PING = True  # Test connections before using
    ECHO = False
    ECHO_POOL = False
    
    # Connection limits for protection
    MAX_CONNECTIONS = 100  # Hard limit on total connections
    CONNECTION_TIMEOUT = 10  # Timeout for establishing new connections
    STATEMENT_TIMEOUT = 30000  # 30 seconds max statement execution time (ms)
    
    # Read/write splitting configuration
    ENABLE_READ_WRITE_SPLIT = False
    READ_DB_URL: Optional[str] = None
    WRITE_DB_URL: Optional[str] = None
    
    # Query caching configuration
    ENABLE_QUERY_CACHE = True
    QUERY_CACHE_TTL = 300  # 5 minutes
    QUERY_CACHE_SIZE = 1000  # Max cached queries
    
    # Transaction retry configuration
    TRANSACTION_RETRY_ATTEMPTS = 3
    TRANSACTION_RETRY_DELAY = 0.1  # Base delay in seconds
    TRANSACTION_RETRY_BACKOFF = 2.0  # Exponential backoff multiplier