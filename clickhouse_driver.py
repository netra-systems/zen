"""
Minimal clickhouse_driver compatibility module.

This module provides the basic clickhouse_driver.Client interface needed by tests
that haven't been migrated to the SSOT ClickHouse implementation yet.

The Client implementation uses our SSOT ClickHouseService internally for 
consistency with the rest of the codebase.
"""

import logging
import warnings

logger = logging.getLogger(__name__)

# Import our SSOT ClickHouse implementation
from netra_backend.app.db.clickhouse_client import ClickHouseDriverCompatAdapter

# Issue warning about using clickhouse_driver directly
warnings.warn(
    "Direct import of 'clickhouse_driver' is deprecated. "
    "Use 'from netra_backend.app.db.clickhouse import ClickHouseService' instead "
    "for better integration with the SSOT implementation.",
    DeprecationWarning,
    stacklevel=2
)

def Client(host='localhost', port=8123, user='default', password='', database='default', **kwargs):
    """
    Factory function to create a ClickHouse client compatible with clickhouse_driver.Client.
    
    This implementation uses our SSOT ClickHouseService internally.
    """
    logger.info(f"[clickhouse_driver compatibility] Creating client for {host}:{port}")
    return ClickHouseDriverCompatAdapter(
        host=host, port=port, user=user, password=password, database=database, **kwargs
    )

# Make Client available at module level for import compatibility
__all__ = ['Client']