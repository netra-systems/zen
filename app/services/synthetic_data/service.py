"""
Main Synthetic Data Service
"""

import asyncio
import json
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, AsyncGenerator, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.Generation import SyntheticDataGenParams
    from app.schemas.data_ingestion_types import IngestionConfig
from sqlalchemy.orm import Session

from .enums import WorkloadCategory, GenerationStatus
from .tools import initialize_default_tools, generate_tool_invocations, calculate_metrics
from .content_generator import (
    select_workload_type, generate_timestamp, select_agent_type, 
    generate_content, generate_child_spans
)
from .validators import validate_schema
from .corpus_manager import load_corpus
from .ingestion import create_destination_table, ingest_batch_to_clickhouse
from .metrics import calculate_generation_rate

from ...db import models_postgres as models
from ... import schemas
from ...ws_manager import manager
from ...db.clickhouse import get_clickhouse_client
from app.logging_config import central_logger


class SyntheticDataService:
    """Service for generating synthetic AI workload data"""
    
    def __init__(self):
        self.active_jobs: Dict[str, Dict] = {}
        self.corpus_cache: Dict[str, List[Dict]] = {}
        self.default_tools = initialize_default_tools()
        
    async def generate_synthetic_data(
        self,
        db: Session,
        config: schemas.LogGenParams,
        user_id: str,
        corpus_id: Optional[str] = None
    ) -> Dict:
        """
        Generate synthetic data based on configuration
        
        Args:
            db: Database session
            config: Generation configuration
            user_id: User ID initiating generation
            corpus_id: Optional corpus to use for content
            
        Returns:
            Job information dictionary
        """
        job_id = str(uuid.uuid4())
        
        # Create destination table name
        table_name = f"netra_synthetic_data_{job_id.replace('-', '_')}"
        
        # Initialize job tracking
        self.active_jobs[job_id] = {
            "status": GenerationStatus.INITIATED.value,
            "config": config,
            "corpus_id": corpus_id or config.corpus_id,
            "start_time": datetime.now(UTC),
            "records_generated": 0,
            "records_ingested": 0,
            "errors": [],
            "table_name": table_name,
            "user_id": user_id
        }
        
        # Create database record
        db_synthetic_data = models.Corpus(
            name=f"Synthetic Data {datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            description=f"Synthetic data generation job {job_id}",
            table_name=table_name,
            status="pending",
            created_by_id=user_id
        )
        db.add(db_synthetic_data)
        db.commit()
        db.refresh(db_synthetic_data)
        
        # Start generation in background
        asyncio.create_task(
            self._generate_worker(job_id, config, corpus_id or config.corpus_id, db, db_synthetic_data.id)
        )
        
        return {
            "job_id": job_id,
            "status": GenerationStatus.INITIATED.value,
            "table_name": table_name,
            "websocket_channel": f"generation_{job_id}"
        }
    
    async def _generate_worker(
        self,
        job_id: str,
        config: schemas.LogGenParams,
        corpus_id: Optional[str],
        db: Session,
        synthetic_data_id: str
    ):
        """Worker function for generating synthetic data"""
        try:
            self.active_jobs[job_id]["status"] = GenerationStatus.RUNNING.value
            
            # Update database status
            db.query(models.Corpus).filter(models.Corpus.id == synthetic_data_id).update({"status": "running"})
            db.commit()
            
            # Send WebSocket update
            await manager.broadcast({
                "type": "generation:started",
                "payload": {
                    "job_id": job_id,
                    "total_records": config.num_logs,
                    "start_time": datetime.now(UTC).isoformat()
                }
            })
            
            # Load corpus if specified
            corpus_content = await load_corpus(corpus_id, db, self.corpus_cache, 
                                              get_clickhouse_client, central_logger) if corpus_id else None
            
            # Create destination table
            table_name = self.active_jobs[job_id]["table_name"]
            await create_destination_table(table_name, get_clickhouse_client)
            
            # Generate data in batches
            batch_size = 100
            total_records = config.num_logs
            
            async for batch_num, batch in enumerate(self._generate_batches(
                config, corpus_content, batch_size, total_records
            )):
                # Ingest batch to ClickHouse
                await ingest_batch_to_clickhouse(table_name, batch, get_clickhouse_client)
                
                # Update progress
                self.active_jobs[job_id]["records_generated"] += len(batch)
                self.active_jobs[job_id]["records_ingested"] += len(batch)
                
                progress = (self.active_jobs[job_id]["records_generated"] / total_records * 100)
                
                # Update database
                db.query(models.Corpus).filter(models.Corpus.id == synthetic_data_id).update({
                    "status": f"running: {progress:.2f}%"
                })
                db.commit()
                
                # Send progress update via WebSocket
                if self.active_jobs[job_id]["records_generated"] % 100 == 0:
                    await manager.broadcast({
                        "type": "generation:progress",
                        "payload": {
                            "job_id": job_id,
                            "progress_percentage": progress,
                            "records_generated": self.active_jobs[job_id]["records_generated"],
                            "records_ingested": self.active_jobs[job_id]["records_ingested"],
                            "current_batch": batch_num,
                            "generation_rate": calculate_generation_rate(self.active_jobs[job_id])
                        }
                    })
            
            # Mark job as completed
            self.active_jobs[job_id]["status"] = GenerationStatus.COMPLETED.value
            self.active_jobs[job_id]["end_time"] = datetime.now(UTC)
            
            # Update database
            db.query(models.Corpus).filter(models.Corpus.id == synthetic_data_id).update({"status": "completed"})
            db.commit()
            
            # Send completion notification
            await manager.broadcast({
                "type": "generation:complete",
                "payload": {
                    "job_id": job_id,
                    "total_records": self.active_jobs[job_id]["records_generated"],
                    "duration_seconds": (self.active_jobs[job_id]["end_time"] - 
                                       self.active_jobs[job_id]["start_time"]).total_seconds(),
                    "destination_table": table_name
                }
            })
            
            central_logger.info(f"Generation job {job_id} completed successfully")
            
        except Exception as e:
            central_logger.error(f"Generation job {job_id} failed: {str(e)}")
            self.active_jobs[job_id]["status"] = GenerationStatus.FAILED.value
            self.active_jobs[job_id]["errors"].append(str(e))
            
            # Update database
            db.query(models.Corpus).filter(models.Corpus.id == synthetic_data_id).update({"status": "failed"})
            db.commit()
            
            # Send error notification
            await manager.broadcast({
                "type": "generation:error",
                "payload": {
                    "job_id": job_id,
                    "error_type": "generation_failure",
                    "error_message": str(e),
                    "recoverable": False
                }
            })
    
    async def _generate_batches(
        self,
        config: schemas.LogGenParams,
        corpus_content: Optional[List[Dict]],
        batch_size: int,
        total_records: int
    ) -> AsyncGenerator[List[Dict], None]:
        """Generate data in batches"""
        records_generated = 0
        batch_num = 0
        
        while records_generated < total_records:
            batch = []
            batch_end = min(records_generated + batch_size, total_records)
            
            for i in range(records_generated, batch_end):
                # Generate synthetic record
                record = await self._generate_single_record(
                    config, corpus_content, i
                )
                batch.append(record)
            
            yield batch_num, batch
            batch_num += 1
            records_generated = batch_end
            
            # Small delay to prevent overwhelming the system
            await asyncio.sleep(0.01)
    
    async def _generate_single_record(
        self,
        config: schemas.LogGenParams,
        corpus_content: Optional[List[Dict]],
        index: int
    ) -> Dict:
        """Generate a single synthetic record"""
        # Determine workload type
        workload_type = select_workload_type()
        
        # Generate trace and span IDs
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        # Generate timestamp with realistic distribution
        timestamp = generate_timestamp(config, index)
        
        # Generate tool invocations based on workload type
        tool_invocations = generate_tool_invocations(workload_type, self.default_tools)
        
        # Generate request/response from corpus or synthetic
        request, response = generate_content(workload_type, corpus_content)
        
        # Calculate metrics
        metrics = calculate_metrics(tool_invocations)
        
        return {
            "event_id": str(uuid.uuid4()),
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": None,
            "timestamp_utc": timestamp,
            "workload_type": workload_type,
            "agent_type": select_agent_type(workload_type),
            "tool_invocations": [t["name"] for t in tool_invocations],
            "request_payload": {"prompt": request},
            "response_payload": {"completion": response},
            "metrics": metrics,
            "corpus_reference_id": None
        }
    
    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a generation job"""
        return self.active_jobs.get(job_id)
    
    async def cancel_job(self, job_id: str, reason: str = None) -> Dict:
        """Cancel a generation job"""
        if job_id in self.active_jobs:
            self.active_jobs[job_id]["status"] = GenerationStatus.CANCELLED.value
            if reason:
                self.active_jobs[job_id]["cancel_reason"] = reason
            return {
                "cancelled": True,
                "records_completed": self.active_jobs[job_id].get("records_generated", 0)
            }
        return {"cancelled": False}
    
    async def get_preview(
        self,
        corpus_id: Optional[str],
        workload_type: str,
        sample_size: int = 10
    ) -> List[Dict]:
        """Generate preview samples"""
        config = schemas.LogGenParams(
            num_logs=sample_size,
            corpus_id=corpus_id
        )
        
        samples = []
        corpus_content = None  # Will be loaded if needed
        
        for i in range(sample_size):
            record = await self._generate_single_record(config, corpus_content, i)
            samples.append(record)
        
        return samples
    
    async def generate_batch(self, config: Union['SyntheticDataGenParams', 'IngestionConfig'], batch_size: int = 100) -> List[Dict[str, Any]]:
        """Generate a single batch of records"""
        batch = []
        for i in range(batch_size):
            record = await self._generate_single_record(config, None, i)
            batch.append(record)
        return batch


# Create a singleton instance
synthetic_data_service = SyntheticDataService()