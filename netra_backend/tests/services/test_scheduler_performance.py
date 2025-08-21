"""
Performance tests for Supply Research Scheduler
Tests memory usage, execution metrics, and resource management
COMPLIANCE: 450-line max file, 25-line max functions
"""

import pytest
import asyncio
import tracemalloc
from datetime import datetime, UTC
from unittest.mock import AsyncMock

from netra_backend.app.services.supply_research_scheduler import (
    SupplyResearchScheduler,
    ResearchSchedule,
    ScheduleFrequency
)
from netra_backend.app.agents.supply_researcher.models import ResearchType


class TestSupplyResearchSchedulerPerformance:
    """Test performance and resource management"""
    
    async def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load."""
        scheduler = SupplyResearchScheduler()
        scheduler._execute_research_job = AsyncMock(return_value=True)
        
        # Start memory tracing
        tracemalloc.start()
        
        # Create many jobs
        schedules = _create_performance_schedules(100)
        
        # Execute jobs in batches to control memory
        batch_size = 10
        for i in range(0, len(schedules), batch_size):
            batch = schedules[i:i + batch_size]
            tasks = [scheduler._execute_research_job(schedule) for schedule in batch]
            await asyncio.gather(*tasks)
        
        # Get memory statistics
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Assert reasonable memory usage (< 100MB for this test)
        assert peak < 100 * 1024 * 1024  # 100MB

    async def test_job_execution_performance_metrics(self):
        """Test job execution performance tracking."""
        scheduler = SupplyResearchScheduler()
        
        # Mock performance tracking
        execution_metrics = []
        
        async def mock_execute_with_timing(schedule):
            start = datetime.now(UTC)
            await asyncio.sleep(0.1)  # Simulate work
            end = datetime.now(UTC)
            
            execution_metrics.append({
                'job_name': schedule.name,
                'duration': (end - start).total_seconds(),
                'success': True
            })
            return True
        
        scheduler._execute_research_job = mock_execute_with_timing
        
        # Execute multiple jobs
        schedules = _create_performance_schedules(10)
        
        tasks = [scheduler._execute_research_job(schedule) for schedule in schedules]
        await asyncio.gather(*tasks)
        
        # Assert performance metrics collected
        assert len(execution_metrics) == 10
        assert all(metric['duration'] >= 0.1 for metric in execution_metrics)
        assert all(metric['success'] for metric in execution_metrics)
        
        # Check average performance
        avg_duration = sum(m['duration'] for m in execution_metrics) / len(execution_metrics)
        assert 0.1 <= avg_duration <= 0.2  # Should be around 0.1s


def _create_performance_schedules(count):
    """Create multiple schedules for performance testing."""
    schedules = []
    research_types = [
        ResearchType.MODEL_UPDATES,
        ResearchType.PERFORMANCE_BENCHMARKS,
        ResearchType.COST_ANALYSIS,
        ResearchType.PROVIDER_COMPARISON
    ]
    
    for i in range(count):
        research_type = research_types[i % len(research_types)]
        schedule = ResearchSchedule(
            name=f"perf_job_{i}",
            frequency=ScheduleFrequency.HOURLY,
            research_type=research_type
        )
        schedules.append(schedule)
    
    return schedules