"""
Synthetic Data Generation Service
Generates realistic AI agent workload data with real-time ClickHouse ingestion
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
from enum import Enum
import numpy as np
from sqlalchemy.orm import Session

from ..db import models_postgres as models
from .. import schemas
from ..ws_manager import manager
from ..db.clickhouse import get_clickhouse_client
from ..db.models_clickhouse import get_llm_events_table_schema
from app.logging_config import central_logger


class WorkloadCategory(Enum):
    """Categories of workload patterns"""
    SIMPLE_CHAT = "simple_chat"
    RAG_PIPELINE = "rag_pipeline"
    TOOL_USE = "tool_use"
    MULTI_TURN_TOOL_USE = "multi_turn_tool_use"
    FAILED_REQUEST = "failed_request"
    CUSTOM_DOMAIN = "custom_domain"


class GenerationStatus(Enum):
    """Status of a generation job"""
    INITIATED = "initiated"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyntheticDataService:
    """Service for generating synthetic AI workload data"""
    
    def __init__(self):
        self.active_jobs: Dict[str, Dict] = {}
        self.corpus_cache: Dict[str, List[Dict]] = {}
        self.default_tools = self._initialize_default_tools()
        
    def _initialize_default_tools(self) -> List[Dict]:
        """Initialize default tool catalog"""
        return [
            {
                "name": "clickhouse_query",
                "type": "query",
                "latency_ms_range": (50, 500),
                "failure_rate": 0.01
            },
            {
                "name": "postgres_lookup",
                "type": "query",
                "latency_ms_range": (20, 200),
                "failure_rate": 0.005
            },
            {
                "name": "llm_analysis",
                "type": "analysis",
                "latency_ms_range": (1000, 5000),
                "failure_rate": 0.02
            },
            {
                "name": "external_api_call",
                "type": "external_api",
                "latency_ms_range": (100, 2000),
                "failure_rate": 0.05
            },
            {
                "name": "cache_lookup",
                "type": "query",
                "latency_ms_range": (5, 50),
                "failure_rate": 0.001
            },
            {
                "name": "vector_search",
                "type": "query",
                "latency_ms_range": (100, 1000),
                "failure_rate": 0.01
            }
        ]
    
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
            "start_time": datetime.utcnow(),
            "records_generated": 0,
            "records_ingested": 0,
            "errors": [],
            "table_name": table_name,
            "user_id": user_id
        }
        
        # Create database record
        db_synthetic_data = models.Corpus(
            name=f"Synthetic Data {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
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
            await manager.broadcast(json.dumps({
                "type": "generation:started",
                "payload": {
                    "job_id": job_id,
                    "total_records": config.num_logs,
                    "start_time": datetime.utcnow().isoformat()
                }
            }))
            
            # Load corpus if specified
            corpus_content = await self._load_corpus(corpus_id, db) if corpus_id else None
            
            # Create destination table
            table_name = self.active_jobs[job_id]["table_name"]
            await self._create_destination_table(table_name)
            
            # Generate data in batches
            batch_size = 100
            total_records = config.num_logs
            
            async for batch_num, batch in enumerate(self._generate_batches(
                config, corpus_content, batch_size, total_records
            )):
                # Ingest batch to ClickHouse
                await self._ingest_batch(table_name, batch)
                
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
                    await manager.broadcast(json.dumps({
                        "type": "generation:progress",
                        "payload": {
                            "job_id": job_id,
                            "progress_percentage": progress,
                            "records_generated": self.active_jobs[job_id]["records_generated"],
                            "records_ingested": self.active_jobs[job_id]["records_ingested"],
                            "current_batch": batch_num,
                            "generation_rate": self._calculate_generation_rate(job_id)
                        }
                    }))
            
            # Mark job as completed
            self.active_jobs[job_id]["status"] = GenerationStatus.COMPLETED.value
            self.active_jobs[job_id]["end_time"] = datetime.utcnow()
            
            # Update database
            db.query(models.Corpus).filter(models.Corpus.id == synthetic_data_id).update({"status": "completed"})
            db.commit()
            
            # Send completion notification
            await manager.broadcast(json.dumps({
                "type": "generation:complete",
                "payload": {
                    "job_id": job_id,
                    "total_records": self.active_jobs[job_id]["records_generated"],
                    "duration_seconds": (self.active_jobs[job_id]["end_time"] - self.active_jobs[job_id]["start_time"]).total_seconds(),
                    "destination_table": table_name
                }
            }))
            
            central_logger.info(f"Generation job {job_id} completed successfully")
            
        except Exception as e:
            central_logger.error(f"Generation job {job_id} failed: {str(e)}")
            self.active_jobs[job_id]["status"] = GenerationStatus.FAILED.value
            self.active_jobs[job_id]["errors"].append(str(e))
            
            # Update database
            db.query(models.Corpus).filter(models.Corpus.id == synthetic_data_id).update({"status": "failed"})
            db.commit()
            
            # Send error notification
            await manager.broadcast(json.dumps({
                "type": "generation:error",
                "payload": {
                    "job_id": job_id,
                    "error_type": "generation_failure",
                    "error_message": str(e),
                    "recoverable": False
                }
            }))
    
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
        workload_type = self._select_workload_type()
        
        # Generate trace and span IDs
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        # Generate timestamp with realistic distribution
        timestamp = self._generate_timestamp(config, index)
        
        # Generate tool invocations based on workload type
        tool_invocations = self._generate_tool_invocations(workload_type)
        
        # Generate request/response from corpus or synthetic
        request, response = self._generate_content(workload_type, corpus_content)
        
        # Calculate metrics
        metrics = self._calculate_metrics(tool_invocations)
        
        return {
            "event_id": str(uuid.uuid4()),
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": None,
            "timestamp_utc": timestamp,
            "workload_type": workload_type,
            "agent_type": self._select_agent_type(workload_type),
            "tool_invocations": [t["name"] for t in tool_invocations],
            "request_payload": {"prompt": request},
            "response_payload": {"completion": response},
            "metrics": metrics,
            "corpus_reference_id": None
        }
    
    def _select_workload_type(self) -> str:
        """Select workload type based on distribution"""
        distribution = {
            "simple_queries": 0.30,
            "tool_orchestration": 0.25,
            "data_analysis": 0.20,
            "optimization_workflows": 0.15,
            "error_scenarios": 0.10
        }
        
        types = list(distribution.keys())
        weights = list(distribution.values())
        return np.random.choice(types, p=weights)
    
    def _generate_timestamp(self, config: schemas.LogGenParams, index: int) -> datetime:
        """Generate realistic timestamp with patterns"""
        base_time = datetime.utcnow() - timedelta(hours=24)
        
        # Add some variation with business hours pattern
        hour_offset = (index / config.num_logs) * 24
        timestamp = base_time + timedelta(hours=hour_offset)
        
        # Add jitter
        jitter_seconds = random.uniform(-60, 60)
        timestamp += timedelta(seconds=jitter_seconds)
        
        return timestamp
    
    def _generate_tool_invocations(self, workload_type: str) -> List[Dict]:
        """Generate tool invocation pattern based on workload type"""
        invocations = []
        
        if workload_type == "simple_queries":
            # Single tool invocation
            tool = random.choice(self.default_tools)
            invocations.append(self._create_tool_invocation(tool))
            
        elif workload_type == "tool_orchestration":
            # Multiple sequential tools
            num_tools = random.randint(2, 5)
            for _ in range(num_tools):
                tool = random.choice(self.default_tools)
                invocations.append(self._create_tool_invocation(tool))
                
        elif workload_type == "data_analysis":
            # Query followed by analysis
            query_tools = [t for t in self.default_tools if t["type"] == "query"]
            analysis_tools = [t for t in self.default_tools if t["type"] == "analysis"]
            
            if query_tools:
                invocations.append(self._create_tool_invocation(random.choice(query_tools)))
            if analysis_tools:
                invocations.append(self._create_tool_invocation(random.choice(analysis_tools)))
                
        elif workload_type == "optimization_workflows":
            # Complex multi-step workflow
            num_tools = random.randint(3, 7)
            for _ in range(num_tools):
                tool = random.choice(self.default_tools)
                invocations.append(self._create_tool_invocation(tool))
                
        else:  # error_scenarios
            # Tool with failure
            tool = random.choice(self.default_tools)
            invocation = self._create_tool_invocation(tool)
            invocation["status"] = "failed"
            invocation["error"] = "Simulated error"
            invocations.append(invocation)
        
        return invocations
    
    def _create_tool_invocation(self, tool: Dict) -> Dict:
        """Create a single tool invocation"""
        # Determine if tool fails based on failure rate
        failed = random.random() < tool["failure_rate"]
        
        # Generate realistic latency
        latency = random.uniform(
            tool["latency_ms_range"][0],
            tool["latency_ms_range"][1]
        )
        
        return {
            "name": tool["name"],
            "type": tool["type"],
            "latency_ms": latency,
            "status": "failed" if failed else "success",
            "error": "Tool execution failed" if failed else None
        }
    
    def _generate_content(
        self,
        workload_type: str,
        corpus_content: Optional[List[Dict]]
    ) -> tuple[str, str]:
        """Generate request/response content"""
        if corpus_content and random.random() < 0.7:  # 70% chance to use corpus
            entry = random.choice(corpus_content)
            return entry.get("prompt", ""), entry.get("response", "")
        
        # Generate synthetic content based on workload type
        content_map = {
            "simple_queries": (
                [
                    "What is the weather today?",
                    "How do I reset my password?",
                    "What are your business hours?",
                    "Can you help me with my order?"
                ],
                [
                    "I can help you with that information.",
                    "Here's what you need to know.",
                    "Let me look that up for you.",
                    "I've found the answer to your question."
                ]
            ),
            "tool_orchestration": (
                [
                    "Analyze my system performance and provide recommendations",
                    "Generate a report on last week's metrics",
                    "Optimize my database queries",
                    "Debug this application issue"
                ],
                [
                    "I've completed the analysis with multiple tools.",
                    "Report generated successfully after data processing.",
                    "Optimization complete with significant improvements.",
                    "Issue identified and resolved using diagnostic tools."
                ]
            ),
            "data_analysis": (
                [
                    "What are the trends in our data?",
                    "Analyze the performance metrics",
                    "Generate insights from the logs",
                    "Compare this week to last week"
                ],
                [
                    "Analysis shows significant patterns in the data.",
                    "Performance metrics indicate positive trends.",
                    "Key insights have been extracted from the logs.",
                    "Comparison reveals notable improvements."
                ]
            )
        }
        
        prompts, responses = content_map.get(workload_type, (["Generic request"], ["Generic response"]))
        return random.choice(prompts), random.choice(responses)
    
    def _select_agent_type(self, workload_type: str) -> str:
        """Select appropriate agent type for workload"""
        agent_mapping = {
            "simple_queries": "triage",
            "tool_orchestration": "supervisor",
            "data_analysis": "data_analysis",
            "optimization_workflows": "optimization",
            "error_scenarios": "triage"
        }
        return agent_mapping.get(workload_type, "general")
    
    def _calculate_metrics(self, tool_invocations: List[Dict]) -> Dict:
        """Calculate metrics from tool invocations"""
        if not tool_invocations:
            return {
                "total_latency_ms": 0,
                "tool_count": 0,
                "success_rate": 1.0
            }
        
        total_latency = sum(t["latency_ms"] for t in tool_invocations)
        success_count = sum(1 for t in tool_invocations if t["status"] == "success")
        
        return {
            "total_latency_ms": total_latency,
            "tool_count": len(tool_invocations),
            "success_rate": success_count / len(tool_invocations),
            "avg_latency_ms": total_latency / len(tool_invocations)
        }
    
    def _calculate_generation_rate(self, job_id: str) -> float:
        """Calculate current generation rate in records/second"""
        job = self.active_jobs.get(job_id)
        if not job:
            return 0.0
        
        elapsed = (datetime.utcnow() - job["start_time"]).total_seconds()
        if elapsed == 0:
            return 0.0
        
        return job["records_generated"] / elapsed
    
    async def _load_corpus(self, corpus_id: str, db: Session) -> Optional[List[Dict]]:
        """Load corpus content from database or ClickHouse"""
        if corpus_id in self.corpus_cache:
            return self.corpus_cache[corpus_id]
        
        try:
            # First check PostgreSQL for corpus metadata
            db_corpus = db.query(models.Corpus).filter(models.Corpus.id == corpus_id).first()
            if not db_corpus or db_corpus.status != "completed":
                return None
            
            # Query corpus table from ClickHouse
            table_name = db_corpus.table_name
            
            async with get_clickhouse_client() as client:
                query = f"""
                    SELECT workload_type, prompt, response, metadata
                    FROM {table_name}
                    LIMIT 10000
                """
                
                result = await client.execute(query)
                
                if result:
                    # Convert to list of dicts
                    corpus_data = []
                    for row in result:
                        corpus_data.append({
                            "workload_type": row[0],
                            "prompt": row[1],
                            "response": row[2],
                            "metadata": row[3]
                        })
                    
                    self.corpus_cache[corpus_id] = corpus_data
                    return corpus_data
                
        except Exception as e:
            central_logger.warning(f"Failed to load corpus {corpus_id}: {str(e)}")
        
        return None
    
    async def _create_destination_table(self, table_name: str):
        """Create ClickHouse table for synthetic data"""
        create_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                event_id UUID,
                trace_id UUID,
                span_id UUID,
                parent_span_id Nullable(UUID),
                timestamp_utc DateTime64(3),
                workload_type String,
                agent_type String,
                tool_invocations Array(String),
                request_payload String,
                response_payload String,
                metrics String,
                corpus_reference_id Nullable(UUID)
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(timestamp_utc)
            ORDER BY (timestamp_utc, trace_id)
        """
        
        async with get_clickhouse_client() as client:
            await client.execute(create_query)
    
    async def _ingest_batch(self, table_name: str, batch: List[Dict]):
        """Ingest batch of records to ClickHouse"""
        if not batch:
            return
        
        # Convert complex fields to JSON strings
        for record in batch:
            record["request_payload"] = json.dumps(record["request_payload"])
            record["response_payload"] = json.dumps(record["response_payload"])
            record["metrics"] = json.dumps(record["metrics"])
        
        # Insert batch
        async with get_clickhouse_client() as client:
            # Prepare values for insertion
            values = []
            for record in batch:
                values.append([
                    record["event_id"],
                    record["trace_id"],
                    record["span_id"],
                    record["parent_span_id"],
                    record["timestamp_utc"],
                    record["workload_type"],
                    record["agent_type"],
                    record["tool_invocations"],
                    record["request_payload"],
                    record["response_payload"],
                    record["metrics"],
                    record["corpus_reference_id"]
                ])
            
            await client.execute(
                f"""INSERT INTO {table_name} 
                (event_id, trace_id, span_id, parent_span_id, timestamp_utc, 
                 workload_type, agent_type, tool_invocations, request_payload, 
                 response_payload, metrics, corpus_reference_id)
                VALUES""",
                values
            )
    
    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a generation job"""
        return self.active_jobs.get(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running generation job"""
        if job_id in self.active_jobs:
            self.active_jobs[job_id]["status"] = GenerationStatus.CANCELLED.value
            return True
        return False
    
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


# Create a singleton instance
synthetic_data_service = SyntheticDataService()


# Legacy function for backward compatibility
def generate_synthetic_data(db: Session, params: schemas.LogGenParams, user_id: str):
    """Legacy function for generating synthetic data"""
    return asyncio.run(
        synthetic_data_service.generate_synthetic_data(db, params, user_id)
    )


async def generate_synthetic_data_task(synthetic_data_id: str, source_table: str, destination_table: str, num_logs: int, db: Session):
    """Legacy task function for compatibility"""
    # This is kept for backward compatibility but uses the new service
    config = schemas.LogGenParams(num_logs=num_logs)
    await synthetic_data_service._generate_worker(
        synthetic_data_id, config, None, db, synthetic_data_id
    )
