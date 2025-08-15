"""ClickHouse database operations for DataSubAgent."""

import json
from typing import Dict, Optional, Any, List

from app.db.clickhouse import get_clickhouse_client
from app.db.clickhouse_init import create_workload_events_table_if_missing
from app.logging_config import central_logger as logger


class ClickHouseOperations:
    """Handle ClickHouse database operations."""
    
    async def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get schema information for a table."""
        # SECURITY: Validate table name to prevent SQL injection
        if not table_name or not table_name.replace('_', '').replace('.', '').isalnum():
            logger.error(f"Invalid table name format: {table_name}")
            return None
            
        try:
            async with get_clickhouse_client() as client:
                # Use parameterized query or escape table name properly
                query = "DESCRIBE TABLE {}"
                result = await client.execute_query(query.format(client.escape_identifier(table_name)))
                return {
                    "columns": [{"name": row[0], "type": row[1]} for row in result],
                    "table": table_name
                }
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            return None
    
    async def fetch_data(
        self,
        query: str,
        cache_key: Optional[str] = None,
        redis_manager = None,
        cache_ttl: int = 300
    ) -> Optional[List[Dict[str, Any]]]:
        """Execute ClickHouse query with caching support."""
        
        # Check cache if available
        if cache_key and redis_manager:
            try:
                cached = await redis_manager.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.debug(f"Cache retrieval failed: {e}")
        
        try:
            # Ensure table exists
            await create_workload_events_table_if_missing()
            
            # Execute query
            async with get_clickhouse_client() as client:
                result = await client.execute_query(query)
            
                # Convert to list of dicts
                if result:
                    columns = result[0]._fields if hasattr(result[0], '_fields') else list(range(len(result[0])))
                    data = [dict(zip(columns, row)) for row in result]
                    
                    # Cache result if key provided
                    if cache_key and redis_manager:
                        try:
                            await redis_manager.set(
                                cache_key,
                                json.dumps(data, default=str),
                                ex=cache_ttl
                            )
                        except Exception as e:
                            logger.debug(f"Cache storage failed: {e}")
                    
                    return data
                
                return []
            
        except Exception as e:
            logger.error(f"ClickHouse query failed: {e}")
            return None