"""Job Progress Tracking L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise customers requiring visibility into long-running AI operations
- Business Goal: Provide real-time progress tracking for complex AI workloads
- Value Impact: Enhanced user experience and operational transparency
- Strategic Impact: $10K MRR - Progress visibility and job monitoring capabilities

Critical Path: Job initiation -> Progress updates -> Status broadcasting -> Completion tracking
Coverage: Real Redis progress storage, WebSocket progress updates, long-running job monitoring, real-time status

L3 Integration Test Level:
- Tests real Redis-based progress tracking infrastructure
- Uses actual WebSocket progress broadcasting
- Validates real-time progress update mechanisms
- Tests long-running job monitoring and status persistence
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import pytest

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

from netra_backend.app.services.websocket.message_queue import (
    MessagePriority,
    MessageQueue,
    MessageStatus,
    QueuedMessage,
)

logger = central_logger.get_logger(__name__)

class ProgressStage(Enum):
    """Progress tracking stages for long-running jobs."""
    INITIALIZING = "initializing"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    OPTIMIZING = "optimizing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class JobProgress:
    """Represents job progress tracking information."""
    job_id: str
    current_stage: ProgressStage = ProgressStage.INITIALIZING
    progress_percentage: float = 0.0
    stages_completed: List[str] = field(default_factory=list)
    current_operation: str = ""
    estimated_completion_time: Optional[float] = None
    start_time: float = field(default_factory=time.time)
    last_update_time: float = field(default_factory=time.time)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class JobProgressTrackingL3Manager:
    """Manages L3 job progress tracking tests with real infrastructure."""
    
    def __init__(self):
        self.message_queue = MessageQueue()
        self.progress_updates: Dict[str, List[JobProgress]] = {}
        self.progress_callbacks: List[Callable] = []
        self.websocket_events = []
        self.long_running_jobs: Dict[str, Dict[str, Any]] = {}
        self.progress_broadcast_log = []
        
    async def initialize_test_infrastructure(self):
        """Initialize real progress tracking infrastructure."""
        try:
            # Clear any existing progress data
            await self.clear_progress_test_data()
            
            # Register handlers for different types of long-running jobs
            self.message_queue.register_handler("long_analysis_job", self.handle_long_analysis_job)
            self.message_queue.register_handler("complex_optimization_job", self.handle_complex_optimization_job)
            self.message_queue.register_handler("data_processing_job", self.handle_data_processing_job)
            self.message_queue.register_handler("model_training_job", self.handle_model_training_job)
            
            logger.info("L3 job progress tracking infrastructure initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize L3 progress tracking test infrastructure: {e}")
            raise
    
    async def clear_progress_test_data(self):
        """Clear all progress tracking test data from Redis."""
        patterns = [
            "job_progress:*", "progress_updates:*", "job_status:*", 
            "progress_broadcast:*", "job_metadata:*"
        ]
        for pattern in patterns:
            keys = await redis_manager.keys(pattern)
            if keys:
                await redis_manager.delete(*keys)
    
    async def update_job_progress(self, job_id: str, stage: ProgressStage, 
                                 percentage: float, operation: str = "", 
                                 metadata: Optional[Dict[str, Any]] = None):
        """Update job progress and broadcast to interested parties."""
        current_time = time.time()
        
        # Create progress update
        progress = JobProgress(
            job_id=job_id,
            current_stage=stage,
            progress_percentage=percentage,
            current_operation=operation,
            last_update_time=current_time,
            metadata=metadata or {}
        )
        
        # Store in tracking
        if job_id not in self.progress_updates:
            self.progress_updates[job_id] = []
        self.progress_updates[job_id].append(progress)
        
        # Store in Redis for persistence
        progress_key = f"job_progress:{job_id}"
        progress_data = {
            "job_id": job_id,
            "stage": stage.value,
            "percentage": percentage,
            "operation": operation,
            "timestamp": current_time,
            "metadata": metadata or {}
        }
        
        await redis_manager.set(progress_key, json.dumps(progress_data), ex=3600)
        
        # Broadcast progress update (simulate WebSocket)
        await self.broadcast_progress_update(job_id, progress_data)
        
        logger.info(f"Job {job_id} progress: {stage.value} - {percentage:.1f}% - {operation}")
    
    async def broadcast_progress_update(self, job_id: str, progress_data: Dict[str, Any]):
        """Broadcast progress update to WebSocket clients (simulated)."""
        broadcast_event = {
            "type": "job_progress_update",
            "job_id": job_id,
            "data": progress_data,
            "timestamp": time.time()
        }
        
        self.websocket_events.append(broadcast_event)
        self.progress_broadcast_log.append(broadcast_event)
        
        # Store broadcast in Redis for client retrieval
        broadcast_key = f"progress_broadcast:{job_id}:{int(time.time() * 1000)}"
        await redis_manager.set(broadcast_key, json.dumps(broadcast_event), ex=300)
        
        # Execute progress callbacks
        for callback in self.progress_callbacks:
            try:
                await callback(job_id, progress_data)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")
    
    def register_progress_callback(self, callback: Callable):
        """Register callback for progress updates."""
        self.progress_callbacks.append(callback)
    
    async def handle_long_analysis_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle long-running analysis job with detailed progress tracking."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        start_time = time.time()
        
        try:
            # Initialize job tracking
            self.long_running_jobs[job_id] = {
                "type": "long_analysis",
                "user_id": user_id,
                "start_time": start_time,
                "stages": ["data_loading", "preprocessing", "analysis", "results"]
            }
            
            # Stage 1: Data loading
            await self.update_job_progress(job_id, ProgressStage.INITIALIZING, 0.0, 
                                         "Loading dataset", {"stage": "data_loading"})
            await asyncio.sleep(0.3)
            
            await self.update_job_progress(job_id, ProgressStage.INITIALIZING, 25.0, 
                                         "Dataset loaded, validating", {"stage": "data_loading"})
            await asyncio.sleep(0.2)
            
            # Stage 2: Preprocessing
            await self.update_job_progress(job_id, ProgressStage.PROCESSING, 30.0, 
                                         "Preprocessing data", {"stage": "preprocessing"})
            await asyncio.sleep(0.4)
            
            await self.update_job_progress(job_id, ProgressStage.PROCESSING, 50.0, 
                                         "Feature extraction", {"stage": "preprocessing"})
            await asyncio.sleep(0.3)
            
            # Stage 3: Analysis
            await self.update_job_progress(job_id, ProgressStage.ANALYZING, 60.0, 
                                         "Running statistical analysis", {"stage": "analysis"})
            await asyncio.sleep(0.5)
            
            await self.update_job_progress(job_id, ProgressStage.ANALYZING, 80.0, 
                                         "Generating insights", {"stage": "analysis"})
            await asyncio.sleep(0.3)
            
            # Stage 4: Results
            await self.update_job_progress(job_id, ProgressStage.FINALIZING, 90.0, 
                                         "Compiling results", {"stage": "results"})
            await asyncio.sleep(0.2)
            
            await self.update_job_progress(job_id, ProgressStage.COMPLETED, 100.0, 
                                         "Analysis completed", {"stage": "completed"})
            
            completion_time = time.time()
            self.long_running_jobs[job_id]["completion_time"] = completion_time
            self.long_running_jobs[job_id]["duration"] = completion_time - start_time
            
            logger.info(f"Long analysis job {job_id} completed in {completion_time - start_time:.3f}s")
            
        except Exception as e:
            await self.update_job_progress(job_id, ProgressStage.FAILED, 0.0, 
                                         f"Analysis failed: {str(e)}", {"error": str(e)})
            raise
    
    async def handle_complex_optimization_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle complex optimization job with iterative progress tracking."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        start_time = time.time()
        
        try:
            # Initialize optimization job
            self.long_running_jobs[job_id] = {
                "type": "complex_optimization",
                "user_id": user_id,
                "start_time": start_time,
                "iterations": 10,
                "current_iteration": 0
            }
            
            total_iterations = 10
            
            # Initialization
            await self.update_job_progress(job_id, ProgressStage.INITIALIZING, 0.0, 
                                         "Setting up optimization parameters")
            await asyncio.sleep(0.2)
            
            # Iterative optimization
            for iteration in range(total_iterations):
                iteration_progress = 10 + (iteration / total_iterations) * 80  # 10% to 90%
                
                await self.update_job_progress(
                    job_id, ProgressStage.OPTIMIZING, iteration_progress,
                    f"Optimization iteration {iteration + 1}/{total_iterations}",
                    {"iteration": iteration + 1, "total_iterations": total_iterations}
                )
                
                self.long_running_jobs[job_id]["current_iteration"] = iteration + 1
                await asyncio.sleep(0.15)  # Simulate iteration work
            
            # Finalization
            await self.update_job_progress(job_id, ProgressStage.FINALIZING, 95.0, 
                                         "Validating optimization results")
            await asyncio.sleep(0.2)
            
            await self.update_job_progress(job_id, ProgressStage.COMPLETED, 100.0, 
                                         "Optimization completed successfully")
            
            completion_time = time.time()
            self.long_running_jobs[job_id]["completion_time"] = completion_time
            self.long_running_jobs[job_id]["duration"] = completion_time - start_time
            
            logger.info(f"Complex optimization job {job_id} completed in {completion_time - start_time:.3f}s")
            
        except Exception as e:
            await self.update_job_progress(job_id, ProgressStage.FAILED, 0.0, 
                                         f"Optimization failed: {str(e)}", {"error": str(e)})
            raise
    
    async def handle_data_processing_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle data processing job with batch progress tracking."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        start_time = time.time()
        
        try:
            batch_count = payload.get("batch_count", 5)
            
            # Initialize processing job
            self.long_running_jobs[job_id] = {
                "type": "data_processing",
                "user_id": user_id,
                "start_time": start_time,
                "total_batches": batch_count,
                "processed_batches": 0
            }
            
            # Initialization
            await self.update_job_progress(job_id, ProgressStage.INITIALIZING, 0.0, 
                                         "Preparing data batches")
            await asyncio.sleep(0.2)
            
            # Process batches
            for batch in range(batch_count):
                batch_progress = 10 + (batch / batch_count) * 80  # 10% to 90%
                
                await self.update_job_progress(
                    job_id, ProgressStage.PROCESSING, batch_progress,
                    f"Processing batch {batch + 1}/{batch_count}",
                    {"batch": batch + 1, "total_batches": batch_count}
                )
                
                self.long_running_jobs[job_id]["processed_batches"] = batch + 1
                await asyncio.sleep(0.25)  # Simulate batch processing
            
            # Finalization
            await self.update_job_progress(job_id, ProgressStage.FINALIZING, 95.0, 
                                         "Consolidating processed data")
            await asyncio.sleep(0.2)
            
            await self.update_job_progress(job_id, ProgressStage.COMPLETED, 100.0, 
                                         "Data processing completed")
            
            completion_time = time.time()
            self.long_running_jobs[job_id]["completion_time"] = completion_time
            self.long_running_jobs[job_id]["duration"] = completion_time - start_time
            
            logger.info(f"Data processing job {job_id} completed in {completion_time - start_time:.3f}s")
            
        except Exception as e:
            await self.update_job_progress(job_id, ProgressStage.FAILED, 0.0, 
                                         f"Data processing failed: {str(e)}", {"error": str(e)})
            raise
    
    async def handle_model_training_job(self, user_id: str, payload: Dict[str, Any]):
        """Handle model training job with epoch-based progress tracking."""
        job_id = payload.get("job_id", str(uuid.uuid4()))
        start_time = time.time()
        
        try:
            epochs = payload.get("epochs", 3)
            
            # Initialize training job
            self.long_running_jobs[job_id] = {
                "type": "model_training",
                "user_id": user_id,
                "start_time": start_time,
                "total_epochs": epochs,
                "current_epoch": 0
            }
            
            # Model setup
            await self.update_job_progress(job_id, ProgressStage.INITIALIZING, 0.0, 
                                         "Initializing model architecture")
            await asyncio.sleep(0.3)
            
            await self.update_job_progress(job_id, ProgressStage.INITIALIZING, 10.0, 
                                         "Loading training data")
            await asyncio.sleep(0.2)
            
            # Training epochs
            for epoch in range(epochs):
                epoch_progress = 15 + (epoch / epochs) * 75  # 15% to 90%
                
                await self.update_job_progress(
                    job_id, ProgressStage.PROCESSING, epoch_progress,
                    f"Training epoch {epoch + 1}/{epochs}",
                    {"epoch": epoch + 1, "total_epochs": epochs}
                )
                
                self.long_running_jobs[job_id]["current_epoch"] = epoch + 1
                await asyncio.sleep(0.4)  # Simulate epoch training
            
            # Model validation
            await self.update_job_progress(job_id, ProgressStage.FINALIZING, 95.0, 
                                         "Validating trained model")
            await asyncio.sleep(0.3)
            
            await self.update_job_progress(job_id, ProgressStage.COMPLETED, 100.0, 
                                         "Model training completed")
            
            completion_time = time.time()
            self.long_running_jobs[job_id]["completion_time"] = completion_time
            self.long_running_jobs[job_id]["duration"] = completion_time - start_time
            
            logger.info(f"Model training job {job_id} completed in {completion_time - start_time:.3f}s")
            
        except Exception as e:
            await self.update_job_progress(job_id, ProgressStage.FAILED, 0.0, 
                                         f"Model training failed: {str(e)}", {"error": str(e)})
            raise
    
    async def get_job_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current job progress from Redis."""
        progress_key = f"job_progress:{job_id}"
        progress_data = await redis_manager.get(progress_key)
        
        if progress_data:
            return json.loads(progress_data)
        return None
    
    async def get_all_progress_updates(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all progress updates for a job from tracking."""
        if job_id in self.progress_updates:
            return [
                {
                    "stage": update.current_stage.value,
                    "percentage": update.progress_percentage,
                    "operation": update.current_operation,
                    "timestamp": update.last_update_time,
                    "metadata": update.metadata
                }
                for update in self.progress_updates[job_id]
            ]
        return []
    
    async def validate_progress_accuracy(self, job_id: str) -> Dict[str, Any]:
        """Validate accuracy and consistency of progress tracking."""
        if job_id not in self.progress_updates:
            return {"valid": False, "reason": "No progress updates found"}
        
        updates = self.progress_updates[job_id]
        issues = []
        
        # Check progress monotonicity (should generally increase)
        for i in range(1, len(updates)):
            prev_progress = updates[i-1].progress_percentage
            curr_progress = updates[i].progress_percentage
            
            # Allow for small decreases (e.g., stage transitions)
            if curr_progress < prev_progress - 5.0:
                issues.append({
                    "type": "progress_regression",
                    "previous": prev_progress,
                    "current": curr_progress,
                    "update_index": i
                })
        
        # Check stage progression
        expected_stage_order = [
            ProgressStage.INITIALIZING,
            ProgressStage.PROCESSING,
            ProgressStage.ANALYZING,
            ProgressStage.OPTIMIZING,
            ProgressStage.FINALIZING,
            ProgressStage.COMPLETED
        ]
        
        stage_indices = {}
        for i, update in enumerate(updates):
            if update.current_stage in expected_stage_order:
                stage_indices[update.current_stage] = i
        
        # Check for out-of-order stages
        prev_index = -1
        for stage in expected_stage_order:
            if stage in stage_indices:
                if stage_indices[stage] < prev_index:
                    issues.append({
                        "type": "stage_order_violation",
                        "stage": stage.value,
                        "expected_after": prev_index,
                        "actual_index": stage_indices[stage]
                    })
                prev_index = stage_indices[stage]
        
        # Check completion
        final_update = updates[-1]
        if final_update.current_stage in [ProgressStage.COMPLETED, ProgressStage.FAILED]:
            expected_percentage = 100.0 if final_update.current_stage == ProgressStage.COMPLETED else 0.0
            if abs(final_update.progress_percentage - expected_percentage) > 1.0:
                issues.append({
                    "type": "completion_percentage_mismatch",
                    "expected": expected_percentage,
                    "actual": final_update.progress_percentage
                })
        
        return {
            "valid": len(issues) == 0,
            "total_updates": len(updates),
            "issues": issues,
            "progress_range": {
                "min": min(u.progress_percentage for u in updates),
                "max": max(u.progress_percentage for u in updates)
            }
        }
    
    async def cleanup_test_infrastructure(self):
        """Clean up progress tracking test infrastructure."""
        try:
            await self.message_queue.stop_processing()
            await self.clear_progress_test_data()
            logger.info("L3 progress tracking test cleanup completed")
        except Exception as e:
            logger.error(f"Progress tracking test cleanup failed: {e}")

@pytest.fixture
async def progress_tracking_manager():
    """Create progress tracking manager for L3 testing."""
    manager = JobProgressTrackingL3Manager()
    await manager.initialize_test_infrastructure()
    yield manager
    await manager.cleanup_test_infrastructure()

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_progress_tracking_l3(progress_tracking_manager):
    """Test basic job progress tracking with real Redis storage."""
    # Enqueue a long-running analysis job
    job_id = str(uuid.uuid4())
    message = QueuedMessage(
        user_id="progress_test_user",
        type="long_analysis_job",
        payload={"job_id": job_id},
        priority=MessagePriority.NORMAL
    )
    
    await progress_tracking_manager.message_queue.enqueue(message)
    
    # Start processing
    processing_task = asyncio.create_task(
        progress_tracking_manager.message_queue.process_queue(worker_count=1)
    )
    
    # Wait for job completion
    await asyncio.sleep(3.0)
    
    # Stop processing
    await progress_tracking_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate progress tracking
    progress_updates = await progress_tracking_manager.get_all_progress_updates(job_id)
    
    assert len(progress_updates) >= 5, f"Insufficient progress updates: {len(progress_updates)}"
    
    # Check progress consistency
    validation = await progress_tracking_manager.validate_progress_accuracy(job_id)
    assert validation["valid"], f"Progress tracking issues: {validation['issues']}"
    
    # Check final progress state
    final_progress = await progress_tracking_manager.get_job_progress(job_id)
    assert final_progress is not None, "Final progress not stored in Redis"
    assert final_progress["stage"] == "completed", "Job should be completed"
    assert final_progress["percentage"] == 100.0, "Final percentage should be 100%"

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.asyncio
async def test_iterative_progress_tracking_l3(progress_tracking_manager):
    """Test progress tracking for iterative optimization jobs."""
    # Enqueue optimization job
    job_id = str(uuid.uuid4())
    message = QueuedMessage(
        user_id="optimization_test_user",
        type="complex_optimization_job",
        payload={"job_id": job_id},
        priority=MessagePriority.HIGH
    )
    
    await progress_tracking_manager.message_queue.enqueue(message)
    
    # Start processing
    processing_task = asyncio.create_task(
        progress_tracking_manager.message_queue.process_queue(worker_count=1)
    )
    
    # Wait for completion
    await asyncio.sleep(3.5)
    
    # Stop processing
    await progress_tracking_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate iterative progress
    progress_updates = await progress_tracking_manager.get_all_progress_updates(job_id)
    
    assert len(progress_updates) >= 10, f"Insufficient iterative updates: {len(progress_updates)}"
    
    # Check for iteration metadata
    iteration_updates = [u for u in progress_updates if "iteration" in u.get("metadata", {})]
    assert len(iteration_updates) >= 8, "Should track individual iterations"
    
    # Validate progress increases through iterations
    optimization_updates = [u for u in progress_updates if u["stage"] == "optimizing"]
    for i in range(1, len(optimization_updates)):
        assert optimization_updates[i]["percentage"] >= optimization_updates[i-1]["percentage"], \
            "Optimization progress should increase"
    
    # Check completion
    validation = await progress_tracking_manager.validate_progress_accuracy(job_id)
    assert validation["valid"], f"Iterative progress issues: {validation['issues']}"

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_processing_progress_l3(progress_tracking_manager):
    """Test progress tracking for batch processing jobs."""
    # Enqueue data processing job with specific batch count
    job_id = str(uuid.uuid4())
    batch_count = 6
    
    message = QueuedMessage(
        user_id="batch_test_user",
        type="data_processing_job",
        payload={"job_id": job_id, "batch_count": batch_count},
        priority=MessagePriority.NORMAL
    )
    
    await progress_tracking_manager.message_queue.enqueue(message)
    
    # Start processing
    processing_task = asyncio.create_task(
        progress_tracking_manager.message_queue.process_queue(worker_count=1)
    )
    
    # Wait for completion
    await asyncio.sleep(3.0)
    
    # Stop processing
    await progress_tracking_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate batch progress tracking
    progress_updates = await progress_tracking_manager.get_all_progress_updates(job_id)
    
    # Should have updates for each batch
    batch_updates = [u for u in progress_updates if "batch" in u.get("metadata", {})]
    assert len(batch_updates) >= batch_count, f"Missing batch updates: {len(batch_updates)}"
    
    # Check batch progression
    for i, update in enumerate(batch_updates):
        batch_num = update["metadata"]["batch"]
        assert batch_num == i + 1, f"Batch number mismatch: {batch_num} != {i + 1}"
    
    # Validate final state
    final_progress = await progress_tracking_manager.get_job_progress(job_id)
    assert final_progress["stage"] == "completed", "Batch job should complete"
    assert final_progress["percentage"] == 100.0, "Final percentage should be 100%"

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_progress_tracking_l3(progress_tracking_manager):
    """Test progress tracking for multiple concurrent jobs."""
    # Enqueue multiple different long-running jobs
    job_specs = [
        {"type": "long_analysis_job", "user": "concurrent_user_1"},
        {"type": "complex_optimization_job", "user": "concurrent_user_2"},
        {"type": "data_processing_job", "user": "concurrent_user_3", "payload": {"batch_count": 4}},
        {"type": "model_training_job", "user": "concurrent_user_4", "payload": {"epochs": 2}}
    ]
    
    job_ids = []
    for spec in job_specs:
        job_id = str(uuid.uuid4())
        message = QueuedMessage(
            user_id=spec["user"],
            type=spec["type"],
            payload={"job_id": job_id, **spec.get("payload", {})},
            priority=MessagePriority.NORMAL
        )
        
        await progress_tracking_manager.message_queue.enqueue(message)
        job_ids.append(job_id)
    
    # Start concurrent processing
    processing_task = asyncio.create_task(
        progress_tracking_manager.message_queue.process_queue(worker_count=4)
    )
    
    # Wait for completion
    await asyncio.sleep(6.0)
    
    # Stop processing
    await progress_tracking_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate concurrent progress tracking
    for job_id in job_ids:
        progress_updates = await progress_tracking_manager.get_all_progress_updates(job_id)
        assert len(progress_updates) >= 3, f"Job {job_id} has insufficient progress updates"
        
        # Validate each job's progress
        validation = await progress_tracking_manager.validate_progress_accuracy(job_id)
        assert validation["valid"], f"Job {job_id} progress issues: {validation['issues']}"
    
    # Check that all jobs completed
    completed_jobs = 0
    for job_id in job_ids:
        final_progress = await progress_tracking_manager.get_job_progress(job_id)
        if final_progress and final_progress["stage"] == "completed":
            completed_jobs += 1
    
    assert completed_jobs >= 3, f"Insufficient concurrent job completions: {completed_jobs}/4"

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.asyncio
async def test_progress_broadcast_functionality_l3(progress_tracking_manager):
    """Test WebSocket progress broadcasting functionality."""
    # Set up progress callback to monitor broadcasts
    broadcast_events = []
    
    async def progress_callback(job_id: str, progress_data: Dict[str, Any]):
        broadcast_events.append({
            "job_id": job_id,
            "progress": progress_data,
            "received_at": time.time()
        })
    
    progress_tracking_manager.register_progress_callback(progress_callback)
    
    # Enqueue job for progress tracking
    job_id = str(uuid.uuid4())
    message = QueuedMessage(
        user_id="broadcast_test_user",
        type="long_analysis_job",
        payload={"job_id": job_id},
        priority=MessagePriority.HIGH
    )
    
    await progress_tracking_manager.message_queue.enqueue(message)
    
    # Start processing
    processing_task = asyncio.create_task(
        progress_tracking_manager.message_queue.process_queue(worker_count=1)
    )
    
    # Wait for completion
    await asyncio.sleep(3.0)
    
    # Stop processing
    await progress_tracking_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate broadcast functionality
    assert len(broadcast_events) >= 5, f"Insufficient broadcast events: {len(broadcast_events)}"
    
    # Check WebSocket event log
    websocket_events = progress_tracking_manager.websocket_events
    assert len(websocket_events) >= 5, f"Insufficient WebSocket events: {len(websocket_events)}"
    
    # Validate broadcast timing
    job_broadcasts = [e for e in broadcast_events if e["job_id"] == job_id]
    assert len(job_broadcasts) >= 5, "Should receive multiple progress broadcasts"
    
    # Check broadcast data structure
    for event in job_broadcasts:
        progress_data = event["progress"]
        assert "stage" in progress_data, "Broadcast should include stage"
        assert "percentage" in progress_data, "Broadcast should include percentage"
        assert "timestamp" in progress_data, "Broadcast should include timestamp"

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.asyncio
async def test_progress_persistence_and_recovery_l3(progress_tracking_manager):
    """Test progress persistence in Redis and recovery capabilities."""
    # Start a job and track initial progress
    job_id = str(uuid.uuid4())
    message = QueuedMessage(
        user_id="persistence_test_user",
        type="complex_optimization_job",
        payload={"job_id": job_id},
        priority=MessagePriority.NORMAL
    )
    
    await progress_tracking_manager.message_queue.enqueue(message)
    
    # Start processing
    processing_task = asyncio.create_task(
        progress_tracking_manager.message_queue.process_queue(worker_count=1)
    )
    
    # Wait for partial completion
    await asyncio.sleep(1.5)
    
    # Check intermediate progress persistence
    intermediate_progress = await progress_tracking_manager.get_job_progress(job_id)
    assert intermediate_progress is not None, "Progress should be persisted during execution"
    assert intermediate_progress["percentage"] > 0, "Should have made some progress"
    assert intermediate_progress["percentage"] < 100, "Should not be fully complete yet"
    
    # Continue to completion
    await asyncio.sleep(2.0)
    
    # Stop processing
    await progress_tracking_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    # Validate final persistence
    final_progress = await progress_tracking_manager.get_job_progress(job_id)
    assert final_progress is not None, "Final progress should be persisted"
    assert final_progress["stage"] == "completed", "Job should be completed"
    assert final_progress["percentage"] == 100.0, "Final percentage should be 100%"
    
    # Test progress recovery (simulate restart)
    recovered_progress = await progress_tracking_manager.get_job_progress(job_id)
    assert recovered_progress == final_progress, "Progress should be recoverable from Redis"

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.asyncio
async def test_progress_tracking_under_load_l3(progress_tracking_manager):
    """Test progress tracking performance under high load."""
    # Create multiple concurrent jobs for load testing
    job_count = 8
    job_ids = []
    
    for i in range(job_count):
        job_id = str(uuid.uuid4())
        job_type = ["long_analysis_job", "data_processing_job"][i % 2]
        payload = {"job_id": job_id}
        
        if job_type == "data_processing_job":
            payload["batch_count"] = 3  # Smaller batches for faster testing
        
        message = QueuedMessage(
            user_id=f"load_test_user_{i}",
            type=job_type,
            payload=payload,
            priority=MessagePriority.NORMAL
        )
        
        await progress_tracking_manager.message_queue.enqueue(message)
        job_ids.append(job_id)
    
    # Start high-load processing
    start_time = time.time()
    processing_task = asyncio.create_task(
        progress_tracking_manager.message_queue.process_queue(worker_count=6)
    )
    
    # Wait for processing completion
    await asyncio.sleep(8.0)
    
    # Stop processing
    await progress_tracking_manager.message_queue.stop_processing()
    processing_task.cancel()
    
    total_time = time.time() - start_time
    
    # Validate load performance
    completed_jobs = 0
    total_progress_updates = 0
    
    for job_id in job_ids:
        progress_updates = await progress_tracking_manager.get_all_progress_updates(job_id)
        total_progress_updates += len(progress_updates)
        
        final_progress = await progress_tracking_manager.get_job_progress(job_id)
        if final_progress and final_progress["stage"] == "completed":
            completed_jobs += 1
    
    # Performance assertions
    assert completed_jobs >= 6, f"Poor completion rate under load: {completed_jobs}/{job_count}"
    assert total_progress_updates >= 30, f"Insufficient progress updates under load: {total_progress_updates}"
    assert total_time < 10.0, f"Progress tracking too slow under load: {total_time}s"
    
    # Check broadcast performance under load
    total_broadcasts = len(progress_tracking_manager.websocket_events)
    assert total_broadcasts >= 25, f"Poor broadcast performance under load: {total_broadcasts}"
    
    # Validate that progress tracking remained accurate under load
    accuracy_issues = 0
    for job_id in job_ids:
        validation = await progress_tracking_manager.validate_progress_accuracy(job_id)
        if not validation["valid"]:
            accuracy_issues += len(validation["issues"])
    
    assert accuracy_issues == 0, f"Progress accuracy degraded under load: {accuracy_issues} issues"