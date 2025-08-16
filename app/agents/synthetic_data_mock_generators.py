"""
Synthetic Data Mock Generators Module

Handles generation of mock synthetic data for different workload types
including inference logs, performance metrics, and generic records.
"""

import random
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

from app.agents.synthetic_data_presets import DataGenerationType, WorkloadProfile
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SyntheticDataMockGenerators:
    """Handles mock data generation for different workload types"""
    
    def generate_mock_data(self, profile: WorkloadProfile, batch_size: int) -> List[Dict[str, Any]]:
        """Generate mock data batch for demonstration"""
        if profile.workload_type == DataGenerationType.INFERENCE_LOGS:
            return self.generate_inference_logs(profile, batch_size)
        elif profile.workload_type == DataGenerationType.PERFORMANCE_METRICS:
            return self.generate_performance_metrics(profile, batch_size)
        else:
            return self.generate_generic_records(batch_size)
    
    def generate_inference_logs(self, profile: WorkloadProfile, batch_size: int) -> List[Dict[str, Any]]:
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
    
    def generate_performance_metrics(self, profile: WorkloadProfile, batch_size: int) -> List[Dict[str, Any]]:
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
    
    def generate_generic_records(self, batch_size: int) -> List[Dict[str, Any]]:
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
        from app.agents.synthetic_data_record_builders import SyntheticDataRecordBuilders
        builders = SyntheticDataRecordBuilders()
        timestamp = builders.calculate_record_timestamp(base_time, profile.time_range_days)
        base_data = builders.create_base_inference_data(timestamp, models)
        performance_data = builders.create_inference_performance_data(profile)
        return {**base_data, **performance_data}
    
    def _create_performance_record(self, base_time: datetime, profile: WorkloadProfile) -> Dict[str, Any]:
        """Create single performance metric record"""
        from app.agents.synthetic_data_record_builders import SyntheticDataRecordBuilders
        builders = SyntheticDataRecordBuilders()
        timestamp = builders.calculate_record_timestamp(base_time, profile.time_range_days)
        latency_data = builders.create_latency_metrics(profile)
        system_data = builders.create_system_metrics()
        return {"timestamp": timestamp.isoformat(), **latency_data, **system_data}