"""
ClickHouse operations for corpus management
Handles table creation, management, and database-specific operations
"""

import asyncio
from typing import Dict
from sqlalchemy.orm import Session

from ...db import models_postgres as models
from ...db.clickhouse import get_clickhouse_client
from ...ws_manager import manager
from .base import CorpusStatus, ClickHouseOperationError
from app.logging_config import central_logger


class ClickHouseOperations:
    """Handles ClickHouse-specific operations for corpus management"""
    
    async def create_corpus_table(
        self,
        corpus_id: str,
        table_name: str,
        db: Session
    ):
        """Create ClickHouse table for corpus content"""
        try:
            async with get_clickhouse_client() as client:
                # Create table with comprehensive schema
                create_query = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        record_id UUID,
                        workload_type String,
                        prompt String,
                        response String,
                        metadata String,
                        domain String,
                        created_at DateTime64(3) DEFAULT now(),
                        version UInt32 DEFAULT 1
                    ) ENGINE = MergeTree()
                    PARTITION BY toYYYYMM(created_at)
                    ORDER BY (workload_type, created_at, record_id)
                """
                
                await client.execute(create_query)
                
                # Update status to available
                db.query(models.Corpus).filter(
                    models.Corpus.id == corpus_id
                ).update({"status": CorpusStatus.AVAILABLE.value})
                db.commit()
                
                # Send WebSocket notification
                await manager.broadcast({
                    "type": "corpus:created",
                    "payload": {
                        "corpus_id": corpus_id,
                        "table_name": table_name,
                        "status": CorpusStatus.AVAILABLE.value
                    }
                })
                
                central_logger.info(f"Created ClickHouse table {table_name} for corpus {corpus_id}")
                
        except Exception as e:
            central_logger.error(f"Failed to create ClickHouse table for corpus {corpus_id}: {str(e)}")
            
            # Update status to failed
            db.query(models.Corpus).filter(
                models.Corpus.id == corpus_id
            ).update({"status": CorpusStatus.FAILED.value})
            db.commit()
            
            # Send error notification
            await manager.broadcast({
                "type": "corpus:error",
                "payload": {
                    "corpus_id": corpus_id,
                    "error": str(e)
                }
            })
            
            raise ClickHouseOperationError(f"Failed to create table: {str(e)}")
    
    async def delete_corpus_table(
        self,
        table_name: str
    ):
        """Delete ClickHouse table for corpus"""
        try:
            async with get_clickhouse_client() as client:
                await client.execute(f"DROP TABLE IF EXISTS {table_name}")
                
                central_logger.info(f"Deleted ClickHouse table {table_name}")
                
        except Exception as e:
            central_logger.error(f"Failed to delete ClickHouse table {table_name}: {str(e)}")
            raise ClickHouseOperationError(f"Failed to delete table: {str(e)}")
    
    async def check_table_exists(
        self,
        table_name: str
    ) -> bool:
        """Check if ClickHouse table exists"""
        try:
            async with get_clickhouse_client() as client:
                query = f"""
                    SELECT COUNT(*) FROM system.tables 
                    WHERE name = '{table_name}'
                """
                result = await client.execute(query)
                return result[0][0] > 0 if result else False
                
        except Exception as e:
            central_logger.error(f"Failed to check table existence {table_name}: {str(e)}")
            raise ClickHouseOperationError(f"Failed to check table existence: {str(e)}")
    
    async def get_table_schema(
        self,
        table_name: str
    ) -> Dict:
        """Get ClickHouse table schema information"""
        try:
            async with get_clickhouse_client() as client:
                query = f"""
                    SELECT column, type, is_in_primary_key
                    FROM system.columns 
                    WHERE table = '{table_name}'
                    ORDER BY position
                """
                result = await client.execute(query)
                
                schema = {
                    "columns": [],
                    "primary_key_columns": []
                }
                
                for row in result:
                    column_info = {
                        "name": row[0],
                        "type": row[1],
                        "is_primary_key": bool(row[2])
                    }
                    schema["columns"].append(column_info)
                    
                    if column_info["is_primary_key"]:
                        schema["primary_key_columns"].append(column_info["name"])
                
                return schema
                
        except Exception as e:
            central_logger.error(f"Failed to get schema for table {table_name}: {str(e)}")
            raise ClickHouseOperationError(f"Failed to get table schema: {str(e)}")
    
    async def optimize_table(
        self,
        table_name: str
    ):
        """Optimize ClickHouse table for better performance"""
        try:
            async with get_clickhouse_client() as client:
                # Run OPTIMIZE to merge parts
                await client.execute(f"OPTIMIZE TABLE {table_name}")
                
                central_logger.info(f"Optimized ClickHouse table {table_name}")
                
        except Exception as e:
            central_logger.error(f"Failed to optimize table {table_name}: {str(e)}")
            raise ClickHouseOperationError(f"Failed to optimize table: {str(e)}")
    
    async def get_table_size(
        self,
        table_name: str
    ) -> Dict:
        """Get ClickHouse table size information"""
        try:
            async with get_clickhouse_client() as client:
                query = f"""
                    SELECT 
                        sum(rows) as total_rows,
                        sum(bytes_on_disk) as bytes_on_disk,
                        sum(data_compressed_bytes) as data_compressed_bytes,
                        sum(data_uncompressed_bytes) as data_uncompressed_bytes
                    FROM system.parts 
                    WHERE table = '{table_name}' AND active = 1
                """
                result = await client.execute(query)
                
                if result and result[0]:
                    row = result[0]
                    return {
                        "total_rows": row[0] or 0,
                        "bytes_on_disk": row[1] or 0,
                        "data_compressed_bytes": row[2] or 0,
                        "data_uncompressed_bytes": row[3] or 0,
                        "compression_ratio": (row[3] / row[2]) if row[2] and row[3] else 1.0
                    }
                
                return {
                    "total_rows": 0,
                    "bytes_on_disk": 0,
                    "data_compressed_bytes": 0,
                    "data_uncompressed_bytes": 0,
                    "compression_ratio": 1.0
                }
                
        except Exception as e:
            central_logger.error(f"Failed to get size for table {table_name}: {str(e)}")
            raise ClickHouseOperationError(f"Failed to get table size: {str(e)}")