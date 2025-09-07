"""
ClickHouse Permissions Test Module
Contains utility functions for checking ClickHouse permissions
"""

import logging
from typing import Dict, Any, Tuple
import asyncio

logger = logging.getLogger(__name__)


async def _check_table_create_permission(client, table_name: str = None) -> Tuple[bool, str]:
    """
    Check if the current user has permission to create tables in ClickHouse
    
    Args:
        client: ClickHouse async client
        table_name: Optional table name to check specific permissions
        
    Returns:
        Tuple of (has_permission: bool, message: str)
    """
    if not client:
        return False, "ClickHouse client not provided"
    
    try:
        # Test table creation permission by attempting to create a temporary test table
        test_table_name = table_name or f"test_permissions_table_{int(asyncio.get_event_loop().time())}"
        
        # Try to create a simple test table
        create_query = f"""
        CREATE TABLE IF NOT EXISTS {test_table_name} (
            id UInt32,
            test_field String,
            timestamp DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY id
        """
        
        await client.execute(create_query)
        
        # If successful, clean up the test table
        drop_query = f"DROP TABLE IF EXISTS {test_table_name}"
        await client.execute(drop_query)
        
        logger.info(f"Table creation permission verified for table: {test_table_name}")
        return True, f"Permission granted for table creation: {test_table_name}"
        
    except Exception as e:
        error_msg = f"Table creation permission denied: {str(e)}"
        logger.warning(error_msg)
        return False, error_msg


async def _check_table_read_permission(client, table_name: str) -> Tuple[bool, str]:
    """
    Check if the current user has permission to read from a specific table
    
    Args:
        client: ClickHouse async client  
        table_name: Table name to check read permissions for
        
    Returns:
        Tuple of (has_permission: bool, message: str)
    """
    if not client:
        return False, "ClickHouse client not provided"
    
    try:
        # Try to read from the table
        query = f"SELECT COUNT(*) FROM {table_name} LIMIT 1"
        result = await client.execute(query)
        
        logger.info(f"Read permission verified for table: {table_name}")
        return True, f"Read permission granted for table: {table_name}"
        
    except Exception as e:
        error_msg = f"Read permission denied for table {table_name}: {str(e)}"
        logger.warning(error_msg)
        return False, error_msg


async def _check_table_write_permission(client, table_name: str) -> Tuple[bool, str]:
    """
    Check if the current user has permission to write to a specific table
    
    Args:
        client: ClickHouse async client
        table_name: Table name to check write permissions for
        
    Returns:
        Tuple of (has_permission: bool, message: str)
    """
    if not client:
        return False, "ClickHouse client not provided"
    
    try:
        # Try to insert a test record
        test_data = {
            'id': 999999,
            'test_field': 'permission_test',
            'timestamp': 'now()'
        }
        
        insert_query = f"""
        INSERT INTO {table_name} (id, test_field, timestamp) 
        VALUES (%(id)s, %(test_field)s, %(timestamp)s)
        """
        
        await client.execute(insert_query, test_data)
        
        # Clean up test data
        cleanup_query = f"DELETE FROM {table_name} WHERE id = 999999 AND test_field = 'permission_test'"
        await client.execute(cleanup_query)
        
        logger.info(f"Write permission verified for table: {table_name}")
        return True, f"Write permission granted for table: {table_name}"
        
    except Exception as e:
        error_msg = f"Write permission denied for table {table_name}: {str(e)}"
        logger.warning(error_msg)
        return False, error_msg


def get_permission_summary(permissions_result: Dict[str, Tuple[bool, str]]) -> str:
    """
    Generate a human-readable summary of permission check results
    
    Args:
        permissions_result: Dict mapping permission type to (success, message) tuple
        
    Returns:
        Formatted summary string
    """
    summary_lines = ["ClickHouse Permissions Summary:"]
    
    for permission_type, (success, message) in permissions_result.items():
        status = "✓ GRANTED" if success else "✗ DENIED"
        summary_lines.append(f"  {permission_type}: {status} - {message}")
    
    return "\n".join(summary_lines)