"""
Synthetic Data Generation Utilities

This module handles the actual generation of synthetic data based on
workload profiles, including mock data generation and progress tracking.
"""

import json
import time
import random
import hashlib
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field

from app.agents.synthetic_data_presets import (
    DataGenerationType, WorkloadProfile
)
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.logging_config import central_logger

# Import consolidated types from single source of truth
from app.schemas.Generation import GenerationStatus, SyntheticDataResult

logger = central_logger.get_logger(__name__)

class SyntheticDataGenerator:
    """Handles synthetic data generation operations"""
    
    def __init__(self, tool_dispatcher: ToolDispatcher):
        self.tool_dispatcher = tool_dispatcher
    
    async def generate_data(
        self, 
        profile: WorkloadProfile,
        run_id: str,
        stream_updates: bool = True
    ) -> SyntheticDataResult:
        """Generate synthetic data based on profile"""
        status, table_name = self._setup_generation(profile)
        try:
            data = await self._generate_batched_data(
                profile, status, run_id, stream_updates
            )
            return self._create_success_result(
                profile, status, data, table_name
            )
        except Exception as e:
            return self._create_error_result(profile, str(e))
    
    def _setup_generation(self, profile: WorkloadProfile) -> tuple[GenerationStatus, str]:
        """Setup generation status and table name"""
        status = self._create_initial_status(profile)
        table_name = self._generate_table_name(profile)
        status.table_name = table_name
        return status, table_name
    
    def _create_initial_status(self, profile: WorkloadProfile) -> GenerationStatus:
        """Create initial generation status"""
        return GenerationStatus(
            status="generating",
            total_records=profile.volume
        )
    
    def _generate_table_name(self, profile: WorkloadProfile) -> str:
        """Generate unique table name for data"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"synthetic_{profile.workload_type.value}_{timestamp}"
    
    async def _generate_batched_data(
        self,
        profile: WorkloadProfile,
        status: GenerationStatus,
        run_id: str,
        stream_updates: bool
    ) -> List[Dict[str, Any]]:
        """Generate data in batches with progress tracking"""
        batch_size = self._calculate_batch_size(profile.volume)
        generated_data = await self._process_all_batches(
            profile, status, run_id, stream_updates, batch_size
        )
        self._finalize_generation(status)
        return generated_data
    
    async def _process_all_batches(
        self,
        profile: WorkloadProfile,
        status: GenerationStatus,
        run_id: str,
        stream_updates: bool,
        batch_size: int
    ) -> List[Dict[str, Any]]:
        """Process all batches for data generation"""
        generated_data = []
        for batch_start in range(0, profile.volume, batch_size):
            await self._process_single_batch(
                profile, status, run_id, stream_updates, batch_start, 
                batch_size, generated_data
            )
        return generated_data
    
    async def _process_single_batch(
        self,
        profile: WorkloadProfile,
        status: GenerationStatus,
        run_id: str,
        stream_updates: bool,
        batch_start: int,
        batch_size: int,
        generated_data: List[Dict[str, Any]]
    ) -> None:
        """Process a single batch and update progress"""
        batch_data = await self._generate_batch(
            profile, batch_start, batch_size, run_id
        )
        generated_data.extend(batch_data)
        self._update_progress(status, len(generated_data), profile.volume)
        await self._handle_progress_update(
            run_id, status, stream_updates, batch_start, batch_size
        )
        await asyncio.sleep(0.01)  # Prevent overwhelming
    
    async def _handle_progress_update(
        self,
        run_id: str,
        status: GenerationStatus,
        stream_updates: bool,
        batch_start: int,
        batch_size: int
    ) -> None:
        """Handle progress update if needed"""
        if stream_updates and self._should_send_update(batch_start, batch_size):
            await self._send_progress_update(run_id, status)
    
    def _finalize_generation(self, status: GenerationStatus) -> None:
        """Finalize generation status"""
        status.status = "completed"
        status.progress_percentage = 100.0
    
    def _calculate_batch_size(self, total_volume: int) -> int:
        """Calculate optimal batch size"""
        return min(1000, max(10, total_volume // 10))
    
    async def _generate_batch(
        self,
        profile: WorkloadProfile,
        start_index: int,
        batch_size: int,
        run_id: str
    ) -> List[Dict[str, Any]]:
        """Generate a single batch of data"""
        actual_size = self._calculate_actual_batch_size(
            batch_size, profile.volume, start_index
        )
        self._validate_tool_availability()
        return await self._generate_via_tool(
            profile, actual_size, run_id
        )
    
    def _calculate_actual_batch_size(
        self, batch_size: int, total_volume: int, start_index: int
    ) -> int:
        """Calculate actual batch size based on remaining volume"""
        return min(batch_size, total_volume - start_index)
    
    def _validate_tool_availability(self) -> None:
        """Validate that required tool is available"""
        if not self.tool_dispatcher.has_tool("generate_synthetic_data_batch"):
            raise RuntimeError(
                "generate_synthetic_data_batch tool not available - "
                "real synthetic data generation required for demo"
            )
    
    async def _generate_via_tool(
        self,
        profile: WorkloadProfile,
        batch_size: int,
        run_id: str
    ) -> List[Dict[str, Any]]:
        """Generate batch using tool dispatcher"""
        result = await self._dispatch_generation_tool(
            profile, batch_size, run_id
        )
        return result.get("data", [])
    
    async def _dispatch_generation_tool(
        self,
        profile: WorkloadProfile,
        batch_size: int,
        run_id: str
    ) -> Dict[str, Any]:
        """Dispatch synthetic data generation tool"""
        return await self.tool_dispatcher.dispatch_tool(
            tool_name="generate_synthetic_data_batch",
            parameters=self._create_tool_params(profile, batch_size),
            state=DeepAgentState(),
            run_id=run_id
        )
    
    def _create_tool_params(self, profile: WorkloadProfile, batch_size: int) -> Dict[str, Any]:
        """Create parameters for tool dispatcher"""
        return self._build_tool_parameter_dict(
            profile, batch_size
        )
    
    def _build_tool_parameter_dict(
        self, profile: WorkloadProfile, batch_size: int
    ) -> Dict[str, Any]:
        """Build tool parameter dictionary"""
        return {
            "workload_type": profile.workload_type.value,
            "batch_size": batch_size,
            "distribution": profile.distribution,
            "noise_level": profile.noise_level,
            "custom_parameters": profile.custom_parameters
        }
    
    def _generate_mock_data(self, profile: WorkloadProfile, batch_size: int) -> List[Dict[str, Any]]:
        """Generate mock data batch for demonstration"""
        if profile.workload_type == DataGenerationType.INFERENCE_LOGS:
            return self._generate_inference_logs(profile, batch_size)
        elif profile.workload_type == DataGenerationType.PERFORMANCE_METRICS:
            return self._generate_performance_metrics(profile, batch_size)
        else:
            return self._generate_generic_records(batch_size)
    
    def _generate_inference_logs(self, profile: WorkloadProfile, batch_size: int) -> List[Dict[str, Any]]:
        """Generate inference log records"""
        base_time = self._get_base_timestamp(profile)
        models = self._get_models_list(profile)
        return self._build_inference_batch(
            base_time, profile, models, batch_size
        )
    
    def _build_inference_batch(
        self,
        base_time: datetime,
        profile: WorkloadProfile,
        models: List[str],
        batch_size: int
    ) -> List[Dict[str, Any]]:
        """Build batch of inference log records"""
        batch = []
        for i in range(batch_size):
            record = self._create_inference_record(
                base_time, profile, models
            )
            batch.append(record)
        return batch
    
    def _generate_performance_metrics(self, profile: WorkloadProfile, batch_size: int) -> List[Dict[str, Any]]:
        """Generate performance metric records"""
        base_time = self._get_base_timestamp(profile)
        return self._build_performance_batch(
            base_time, profile, batch_size
        )
    
    def _build_performance_batch(
        self, base_time: datetime, profile: WorkloadProfile, batch_size: int
    ) -> List[Dict[str, Any]]:
        """Build batch of performance metric records"""
        batch = []
        for i in range(batch_size):
            record = self._create_performance_record(
                base_time, profile
            )
            batch.append(record)
        return batch
    
    def _generate_generic_records(self, batch_size: int) -> List[Dict[str, Any]]:
        """Generate generic records"""
        return [
            self._create_generic_record(i)
            for i in range(batch_size)
        ]
    
    def _create_generic_record(self, index: int) -> Dict[str, Any]:
        """Create a single generic record"""
        return {
            "id": f"record_{index}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "value": random.random()
        }
    
    def _get_base_timestamp(self, profile: WorkloadProfile) -> datetime:
        """Get base timestamp for data generation"""
        return datetime.now(timezone.utc) - timedelta(
            days=profile.time_range_days
        )
    
    def _get_models_list(self, profile: WorkloadProfile) -> List[str]:
        """Get list of models from profile"""
        return profile.custom_parameters.get("models", ["gpt-4"])
    
    def _create_inference_record(self, base_time: datetime, profile: WorkloadProfile, models: List[str]) -> Dict[str, Any]:
        """Create single inference log record"""
        timestamp = self._calculate_record_timestamp(base_time, profile.time_range_days)
        base_data = self._create_base_inference_data(timestamp, models)
        performance_data = self._create_inference_performance_data(profile)
        return {**base_data, **performance_data}
    
    def _calculate_record_timestamp(self, base_time: datetime, time_range_days: int) -> datetime:
        """Calculate timestamp for record with random offset"""
        time_offset = random.randint(0, time_range_days * 86400)
        return base_time + timedelta(seconds=time_offset)
    
    def _create_base_inference_data(self, timestamp: datetime, models: List[str]) -> Dict[str, Any]:
        """Create base inference data fields"""
        return {
            "timestamp": timestamp.isoformat(),
            "model": random.choice(models),
            "tokens_input": random.randint(10, 2000),
            "tokens_output": random.randint(10, 1000)
        }
    
    def _create_inference_performance_data(self, profile: WorkloadProfile) -> Dict[str, Any]:
        """Create performance-related inference data"""
        return {
            "latency_ms": random.gauss(100, 20 * profile.noise_level),
            "status": "success" if random.random() > 0.02 else "error",
            "cost_usd": round(random.uniform(0.01, 1.0), 4)
        }
    
    def _create_performance_record(self, base_time: datetime, profile: WorkloadProfile) -> Dict[str, Any]:
        """Create single performance metric record"""
        timestamp = self._calculate_record_timestamp(base_time, profile.time_range_days)
        latency_data = self._create_latency_metrics(profile)
        system_data = self._create_system_metrics()
        return {"timestamp": timestamp.isoformat(), **latency_data, **system_data}
    
    def _create_latency_metrics(self, profile: WorkloadProfile) -> Dict[str, Any]:
        """Create latency-related performance metrics"""
        return {
            "throughput_rps": random.gauss(1000, 100 * profile.noise_level),
            "p50_latency_ms": random.gauss(50, 10 * profile.noise_level),
            "p95_latency_ms": random.gauss(150, 30 * profile.noise_level),
            "p99_latency_ms": random.gauss(300, 50 * profile.noise_level)
        }
    
    def _create_system_metrics(self) -> Dict[str, Any]:
        """Create system resource metrics"""
        return {
            "error_rate": random.uniform(0, 0.05),
            "cpu_usage": random.uniform(20, 80),
            "memory_usage": random.uniform(30, 70)
        }
    
    def _update_progress(self, status: GenerationStatus, current: int, total: int) -> None:
        """Update generation progress"""
        status.records_generated = current
        status.progress_percentage = (current / total) * 100
    
    def _should_send_update(self, batch_start: int, batch_size: int) -> bool:
        """Determine if progress update should be sent"""
        return batch_start % (batch_size * 5) == 0
    
    async def _send_progress_update(self, run_id: str, status: GenerationStatus) -> None:
        """Send progress update via WebSocket manager"""
        try:
            from app.ws_manager import manager as ws_manager
            await self._send_websocket_update(ws_manager, run_id, status)
        except ImportError:
            logger.debug("WebSocket manager not available, logging progress locally")
            self._log_progress_update(status)
    
    async def _send_websocket_update(self, ws_manager, run_id: str, status: GenerationStatus) -> None:
        """Send update via WebSocket manager"""
        message = self._create_progress_message(status)
        await ws_manager.send_message(run_id, message)
    
    def _log_progress_update(self, status: GenerationStatus) -> None:
        """Log progress update locally"""
        logger.info(
            f"Progress: {status.records_generated:,}/{status.total_records:,} "
            f"({status.progress_percentage:.1f}%)"
        )
    
    def _create_progress_message(self, status: GenerationStatus) -> Dict[str, Any]:
        """Create progress message for WebSocket"""
        return {
            "type": "synthetic_data_progress",
            "data": self._create_progress_data(status)
        }
    
    def _create_progress_data(self, status: GenerationStatus) -> Dict[str, Any]:
        """Create progress data dictionary"""
        return {
            "status": status.status,
            "records_generated": status.records_generated,
            "total_records": status.total_records,
            "progress_percentage": status.progress_percentage,
            "table_name": status.table_name
        }
    
    def _create_success_result(
        self,
        profile: WorkloadProfile,
        status: GenerationStatus,
        data: List[Dict[str, Any]],
        table_name: str
    ) -> SyntheticDataResult:
        """Create successful generation result"""
        return SyntheticDataResult(
            success=True,
            workload_profile=profile,
            generation_status=status,
            sample_data=data[:10],
            metadata=self._create_result_metadata(table_name, data)
        )
    
    def _create_result_metadata(
        self, table_name: str, data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create metadata for successful result"""
        return {
            "table_name": table_name,
            "generation_time_ms": int(time.time() * 1000),
            "checksum": self._calculate_checksum(data)
        }
    
    def _create_error_result(self, profile: WorkloadProfile, error: str) -> SyntheticDataResult:
        """Create error result"""
        return SyntheticDataResult(
            success=False,
            workload_profile=profile,
            generation_status=GenerationStatus(
                status="failed",
                errors=[error]
            )
        )
    
    def _calculate_checksum(self, data: List[Dict[str, Any]]) -> str:
        """Calculate checksum for generated data"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
