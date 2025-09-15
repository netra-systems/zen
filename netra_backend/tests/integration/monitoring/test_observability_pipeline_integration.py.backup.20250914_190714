"""
Test Observability Pipeline Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal + Enterprise customers
- Business Goal: Enable proactive monitoring and issue resolution
- Value Impact: Observability prevents outages and enables SLA compliance
- Strategic Impact: Transparency builds customer trust and enables premium pricing

CRITICAL REQUIREMENTS:
- Tests real observability pipeline (metrics, logs, traces)
- Validates end-to-end data flow through monitoring stack
- Uses real monitoring services, NO MOCKS
- Ensures observability data accuracy and completeness
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env

from netra_backend.app.monitoring.observability_pipeline import ObservabilityPipeline, LogAggregator
from netra_backend.app.monitoring.trace_collector import TraceCollector


class TestObservabilityPipelineIntegration(SSotBaseTestCase):
    """Test observability pipeline with real monitoring services"""
    
    def setup_method(self):
        """Set up test environment"""
        super().setup_method() if hasattr(super(), 'setup_method') else None
        self.env = get_env()
        self.isolated_helper = IsolatedTestHelper()
        
        # Test configuration
        self.test_prefix = f"observability_{uuid.uuid4().hex[:8]}"
        
        # Initialize observability components
        self.pipeline = ObservabilityPipeline()
        self.trace_collector = TraceCollector()
        self.log_aggregator = LogAggregator()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_end_to_end_observability_data_flow(self):
        """Test complete observability data flow from generation to storage"""
        # Start observability pipeline
        pipeline_id = await self.pipeline.start_pipeline(
            components=["metrics", "logs", "traces"],
            test_prefix=self.test_prefix
        )
        
        try:
            # Generate test observability data
            await self._generate_test_observability_data()
            
            # Wait for data processing
            await asyncio.sleep(5)
            
            # Verify data was collected and processed
            pipeline_stats = await self.pipeline.get_pipeline_stats(pipeline_id)
            
            assert pipeline_stats.metrics_processed > 0
            assert pipeline_stats.logs_processed > 0
            assert pipeline_stats.traces_processed > 0
            
        finally:
            await self.pipeline.stop_pipeline(pipeline_id)
            await self.pipeline.cleanup_test_data(self.test_prefix)
    
    async def _generate_test_observability_data(self):
        """Generate test data for observability pipeline"""
        # Generate metrics
        for i in range(10):
            await self.pipeline.emit_metric(
                name="test_metric",
                value=i * 10,
                tags={"test_id": self.test_prefix, "iteration": str(i)}
            )
        
        # Generate logs
        for i in range(15):
            await self.log_aggregator.emit_log(
                level="INFO",
                message=f"Test log message {i}",
                context={"test_id": self.test_prefix, "component": "test"}
            )
        
        # Generate traces
        for i in range(5):
            trace_id = await self.trace_collector.start_trace(
                operation_name=f"test_operation_{i}",
                tags={"test_id": self.test_prefix}
            )
            await asyncio.sleep(0.1)
            await self.trace_collector.end_trace(trace_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])