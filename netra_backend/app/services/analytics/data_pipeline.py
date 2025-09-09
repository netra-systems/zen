"""Data pipeline service for analytics processing.

Business Value Justification (BVJ):
- Segment: Mid and Enterprise customers (advanced analytics)  
- Business Goal: Enable real-time data processing and analytics pipelines
- Value Impact: Provides ETL capabilities and data transformation for business insights
- Revenue Impact: Supports premium analytics features and data-driven decision making
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.database.postgresql_pool_manager import PostgreSQLPoolManager
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


class DataPipeline:
    """Handles data processing pipelines for analytics."""

    def __init__(self):
        """Initialize data pipeline."""
        self.db_pool = PostgreSQLPoolManager()
        self.redis_client = None
        self._active_pipelines: Dict[str, Dict[str, Any]] = {}

    async def _get_redis(self):
        """Get Redis client lazily."""
        if not self.redis_client:
            self.redis_client = await redis_manager.get_client()
        return self.redis_client

    async def start_pipeline(
        self,
        source_table: str,
        destination_table: str,
        processing_rules: List[str],
        test_prefix: Optional[str] = None
    ) -> str:
        """Start a data processing pipeline.
        
        Args:
            source_table: Source table name
            destination_table: Destination table name  
            processing_rules: List of processing rules to apply
            test_prefix: Optional test prefix for isolation
            
        Returns:
            Pipeline ID for tracking
        """
        pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(f"Starting data pipeline {pipeline_id} from {source_table} to {destination_table}")
            
            # Store pipeline configuration
            pipeline_config = {
                "id": pipeline_id,
                "source_table": source_table,
                "destination_table": destination_table,
                "processing_rules": processing_rules,
                "test_prefix": test_prefix,
                "status": "running",
                "started_at": datetime.now(UTC).isoformat(),
                "last_processed": None
            }
            
            self._active_pipelines[pipeline_id] = pipeline_config
            
            # Start background processing task
            asyncio.create_task(self._process_pipeline_data(pipeline_config))
            
            return pipeline_id
            
        except Exception as e:
            logger.error(f"Failed to start pipeline {pipeline_id}: {str(e)}")
            raise

    async def _process_pipeline_data(self, config: Dict[str, Any]) -> None:
        """Process data through the pipeline.
        
        Args:
            config: Pipeline configuration
        """
        pipeline_id = config["id"]
        source_table = config["source_table"]
        destination_table = config["destination_table"]
        processing_rules = config["processing_rules"]
        
        try:
            logger.info(f"Processing data for pipeline {pipeline_id}")
            
            # Get database connection
            async with self.db_pool.get_connection() as conn:
                # Read source data
                source_data = await conn.fetch(f"SELECT * FROM {source_table}")
                logger.debug(f"Retrieved {len(source_data)} records from {source_table}")
                
                # Apply processing rules
                processed_data = await self._apply_processing_rules(source_data, processing_rules)
                
                # Write to destination
                if processed_data:
                    await self._write_processed_data(conn, destination_table, processed_data)
                    
                # Update pipeline status
                config["last_processed"] = datetime.now(UTC).isoformat()
                config["processed_records"] = len(processed_data)
                
            logger.info(f"Pipeline {pipeline_id} processing completed")
            
        except Exception as e:
            logger.error(f"Pipeline {pipeline_id} processing failed: {str(e)}")
            config["status"] = "failed"
            config["error"] = str(e)

    async def _apply_processing_rules(
        self, 
        data: List[Dict[str, Any]], 
        rules: List[str]
    ) -> List[Dict[str, Any]]:
        """Apply processing rules to transform data.
        
        Args:
            data: Source data records
            rules: Processing rules to apply
            
        Returns:
            Processed data records
        """
        processed_records = []
        
        try:
            if "aggregate_by_user" in rules:
                # Group by user and aggregate metrics
                user_metrics = {}
                
                for record in data:
                    user_id = record.get("user_id")
                    event_type = record.get("event_type")
                    event_data = record.get("event_data", {})
                    
                    if user_id not in user_metrics:
                        user_metrics[user_id] = {
                            "user_id": user_id,
                            "event_counts": {},
                            "total_events": 0,
                            "session_duration": 0
                        }
                    
                    # Count events by type
                    user_metrics[user_id]["event_counts"][event_type] = \
                        user_metrics[user_id]["event_counts"].get(event_type, 0) + 1
                    user_metrics[user_id]["total_events"] += 1
                    
                    # Extract session duration if available
                    if "session_duration" in event_data:
                        user_metrics[user_id]["session_duration"] += event_data["session_duration"]
                    elif "duration" in event_data:
                        user_metrics[user_id]["session_duration"] += event_data["duration"]
                
                # Convert to records
                for user_id, metrics in user_metrics.items():
                    processed_records.append({
                        "metric_name": "user_activity_count",
                        "metric_value": metrics["total_events"],
                        "dimensions": {
                            "user_id": user_id,
                            "event_breakdown": metrics["event_counts"]
                        }
                    })
                    
                    if metrics["session_duration"] > 0:
                        processed_records.append({
                            "metric_name": "session_duration",
                            "metric_value": metrics["session_duration"],
                            "dimensions": {
                                "user_id": user_id
                            }
                        })
            
            if "calculate_metrics" in rules:
                # Calculate additional metrics from the data
                total_events = len(data)
                unique_users = len(set(record.get("user_id") for record in data if record.get("user_id")))
                
                processed_records.extend([
                    {
                        "metric_name": "total_events",
                        "metric_value": total_events,
                        "dimensions": {"aggregation_type": "count"}
                    },
                    {
                        "metric_name": "unique_users",
                        "metric_value": unique_users,
                        "dimensions": {"aggregation_type": "distinct_count"}
                    }
                ])
            
            logger.debug(f"Applied {len(rules)} processing rules, generated {len(processed_records)} records")
            return processed_records
            
        except Exception as e:
            logger.error(f"Failed to apply processing rules: {str(e)}")
            return []

    async def _write_processed_data(
        self, 
        conn,
        destination_table: str, 
        data: List[Dict[str, Any]]
    ) -> None:
        """Write processed data to destination table.
        
        Args:
            conn: Database connection
            destination_table: Destination table name
            data: Processed data records
        """
        try:
            # Insert processed records
            for record in data:
                await conn.execute(
                    f"""
                    INSERT INTO {destination_table} (metric_name, metric_value, dimensions)
                    VALUES ($1, $2, $3)
                    """,
                    record["metric_name"],
                    record["metric_value"],
                    record["dimensions"]
                )
            
            logger.debug(f"Wrote {len(data)} records to {destination_table}")
            
        except Exception as e:
            logger.error(f"Failed to write processed data: {str(e)}")
            raise

    async def stop_pipeline(self, pipeline_id: str) -> None:
        """Stop a running pipeline.
        
        Args:
            pipeline_id: Pipeline ID to stop
        """
        try:
            if pipeline_id in self._active_pipelines:
                config = self._active_pipelines[pipeline_id]
                config["status"] = "stopped"
                config["stopped_at"] = datetime.now(UTC).isoformat()
                logger.info(f"Stopped pipeline {pipeline_id}")
            else:
                logger.warning(f"Pipeline {pipeline_id} not found in active pipelines")
                
        except Exception as e:
            logger.error(f"Failed to stop pipeline {pipeline_id}: {str(e)}")
            raise

    async def get_pipeline_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a pipeline.
        
        Args:
            pipeline_id: Pipeline ID to check
            
        Returns:
            Pipeline status information or None if not found
        """
        return self._active_pipelines.get(pipeline_id)

    async def list_active_pipelines(self) -> List[Dict[str, Any]]:
        """List all active pipelines.
        
        Returns:
            List of active pipeline configurations
        """
        return list(self._active_pipelines.values())