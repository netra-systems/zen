"""
Test module for admin monitoring and visibility features
Contains TestAdminVisibility class
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta, UTC
from unittest.mock import patch

from .test_fixtures import *


class TestAdminVisibility:
    """Test admin monitoring and visibility features"""

    @pytest.mark.asyncio
    async def test_generation_job_monitoring(self, admin_service):
        """Test real-time job monitoring for admins"""
        job_id = str(uuid.uuid4())
        
        # Start generation
        generation_task = asyncio.create_task(
            admin_service.generate_monitored(
                GenerationConfig(num_traces=1000),
                job_id=job_id
            )
        )
        
        # Monitor job
        await asyncio.sleep(0.1)
        status = await admin_service.get_job_status(job_id)
        
        assert status["state"] == "running"
        assert "progress_percentage" in status
        assert "estimated_completion" in status
        
        await generation_task

    # @pytest.mark.asyncio
    # async def test_detailed_metrics_dashboard(self, admin_service):
    #     """Test detailed metrics dashboard for admins"""
    #     metrics = await admin_service.get_generation_metrics(
    #         time_range_hours=24
    #     )
    #     
    #     assert "total_jobs" in metrics
    #     assert "success_rate" in metrics
    #     assert "avg_generation_time" in metrics
    #     assert "records_per_second" in metrics
    #     assert "resource_utilization" in metrics

    @pytest.mark.asyncio
    async def test_corpus_usage_analytics(self, admin_service):
        """Test corpus usage analytics for admins"""
        analytics = await admin_service.get_corpus_analytics()
        
        assert "most_used_corpora" in analytics
        assert "corpus_coverage" in analytics
        assert "content_distribution" in analytics
        assert "access_patterns" in analytics

    @pytest.mark.asyncio
    async def test_audit_log_generation(self, admin_service):
        """Test audit logging of generation activities"""
        job_id = str(uuid.uuid4())
        
        await admin_service.generate_with_audit(
            GenerationConfig(num_traces=100),
            job_id=job_id,
            user_id="admin_user"
        )
        
        audit_logs = await admin_service.get_audit_logs(job_id=job_id)
        
        assert len(audit_logs) > 0
        assert all("timestamp" in log for log in audit_logs)
        assert all("action" in log for log in audit_logs)
        assert all("user_id" in log for log in audit_logs)

    @pytest.mark.asyncio
    async def test_performance_profiling(self, admin_service):
        """Test performance profiling for optimization"""
        profile = await admin_service.profile_generation(
            GenerationConfig(num_traces=1000)
        )
        
        assert "generation_time_breakdown" in profile
        assert "bottlenecks" in profile
        assert "optimization_suggestions" in profile
        assert profile["generation_time_breakdown"]["total"] > 0

    @pytest.mark.asyncio
    async def test_alert_configuration(self, admin_service):
        """Test alert configuration for admins"""
        alert_config = {
            "slow_generation": {"threshold_seconds": 60},
            "high_error_rate": {"threshold_percentage": 5},
            "resource_exhaustion": {"memory_threshold_mb": 1000}
        }
        
        await admin_service.configure_alerts(alert_config)
        
        # Trigger alert condition
        with patch.object(admin_service, 'send_alert') as mock_alert:
            await admin_service.generate_synthetic_data(
                GenerationConfig(num_traces=10000)  # Will be slow
            )
            
            mock_alert.assert_called()

    @pytest.mark.asyncio
    async def test_job_cancellation_by_admin(self, admin_service):
        """Test admin ability to cancel running jobs"""
        job_id = str(uuid.uuid4())
        
        # Start long-running job
        generation_task = asyncio.create_task(
            admin_service.generate_synthetic_data(
                GenerationConfig(num_traces=100000),
                job_id=job_id
            )
        )
        
        await asyncio.sleep(0.1)
        
        # Admin cancels job
        result = await admin_service.cancel_job(job_id, reason="Testing cancellation")
        
        assert result["cancelled"] == True
        assert result["records_completed"] < 100000
        
        generation_task.cancel()

    @pytest.mark.asyncio
    async def test_resource_usage_tracking(self, admin_service):
        """Test tracking of resource usage during generation"""
        resource_tracker = await admin_service.start_resource_tracking()
        
        await admin_service.generate_synthetic_data(
            GenerationConfig(num_traces=1000)
        )
        
        usage = await resource_tracker.get_usage_summary()
        
        assert "peak_memory_mb" in usage
        assert "avg_cpu_percent" in usage
        assert "total_io_operations" in usage
        assert "clickhouse_queries" in usage

    @pytest.mark.asyncio
    async def test_admin_diagnostic_tools(self, admin_service):
        """Test diagnostic tools for troubleshooting"""
        diagnostics = await admin_service.run_diagnostics()
        
        assert diagnostics["corpus_connectivity"] == "healthy"
        assert diagnostics["clickhouse_connectivity"] == "healthy"
        assert diagnostics["websocket_status"] == "active"
        assert "worker_pool_status" in diagnostics
        assert "cache_hit_rate" in diagnostics

    @pytest.mark.asyncio
    async def test_batch_job_management(self, admin_service):
        """Test batch job management interface for admins"""
        # Schedule multiple jobs
        job_ids = []
        for i in range(5):
            job_id = await admin_service.schedule_generation(
                GenerationConfig(num_traces=1000),
                scheduled_time=datetime.now(UTC) + timedelta(minutes=i)
            )
            job_ids.append(job_id)
        
        # Get batch status
        batch_status = await admin_service.get_batch_status(job_ids)
        
        assert len(batch_status) == 5
        assert all(s["state"] == "scheduled" for s in batch_status)
        
        # Cancel batch
        await admin_service.cancel_batch(job_ids)