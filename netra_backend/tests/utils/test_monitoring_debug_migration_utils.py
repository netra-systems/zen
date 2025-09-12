"""
Tests for monitoring, debug, and migration utilities (Tests 98-100).
Each function  <= 8 lines, using helper functions for setup and assertions.
"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import time
from datetime import datetime

import pytest

from netra_backend.tests.helpers.debug_migration_test_helpers import (
    DebugTestHelpers,
    MigrationTestHelpers,
)

from netra_backend.tests.helpers.rate_retry_monitoring_test_helpers import (
    MonitoringTestHelpers,
)

# Test 98: Monitoring utils metrics
class TestMonitoringUtilsMetrics:
    """test_monitoring_utils_metrics - Test metric collection and aggregation"""
    
    @pytest.mark.asyncio
    async def test_metric_collection(self):
        from netra_backend.app.utils.monitoring_utils import MonitoringUtils
        utils = MonitoringUtils()
        
        MonitoringTestHelpers.record_test_metrics(utils)
        MonitoringTestHelpers.assert_counter_value(utils, "api_requests", 2)
        assert utils.get_gauge("memory_usage") == 75.5
        
        self._assert_histogram_metrics(utils)
    
    @pytest.mark.asyncio
    async def test_metric_aggregation(self):
        from netra_backend.app.utils.monitoring_utils import MonitoringUtils
        utils = MonitoringUtils()
        
        self._record_time_based_metrics(utils)
        self._assert_time_window_average(utils)
        self._assert_metrics_export(utils)
    
    def _assert_histogram_metrics(self, utils):
        """Assert histogram metrics are recorded correctly."""
        stats = utils.get_histogram_stats("response_time")
        assert stats["mean"] == 30
        assert stats["median"] == 30
        assert stats["p95"] >= 40
    
    def _record_time_based_metrics(self, utils):
        """Record time-based metrics for testing."""
        start_time = time.time()
        for i in range(10):
            utils.record_metric("cpu_usage", 50 + i, timestamp=start_time + i)
    
    def _assert_time_window_average(self, utils):
        """Assert time window average calculation."""
        start_time = time.time()
        avg = utils.get_time_window_average(
            "cpu_usage", start_time, start_time + 5
        )
        assert avg == pytest.approx(52, rel=0.1)
    
    def _assert_metrics_export(self, utils):
        """Assert metrics can be exported."""
        metrics = utils.export_metrics()
        assert "cpu_usage" in metrics
        assert "api_requests" in metrics

# Test 99: Debug utils profiling
class TestDebugUtilsProfiling:
    """test_debug_utils_profiling - Test profiling utilities and performance metrics"""
    
    @pytest.mark.asyncio
    async def test_profiling_utilities(self):
        from netra_backend.app.utils.debug_utils import DebugUtils
        utils = DebugUtils()
        
        await self._test_function_profiling(utils)
        self._test_memory_profiling(utils)
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        from netra_backend.app.utils.debug_utils import DebugUtils
        utils = DebugUtils()
        
        await self._test_timing_context_manager(utils)
        await self._test_performance_tracking(utils)
    
    async def _test_function_profiling(self, utils):
        """Test function profiling capabilities."""
        @utils.profile_function
        async def slow_function():
            await asyncio.sleep(0.1)
            return "result"
        
        result = await slow_function()
        assert result == "result"
        self._assert_profile_data(utils, "slow_function")
    
    def _test_memory_profiling(self, utils):
        """Test memory profiling capabilities."""
        memory_intensive = DebugTestHelpers.create_memory_intensive_function()
        profiled_function = utils.profile_memory(memory_intensive)
        
        result = profiled_function()
        assert result == 1000000
        self._assert_memory_profile(utils, "memory_intensive")
    
    async def _test_timing_context_manager(self, utils):
        """Test timing context manager."""
        async with utils.timer("database_query") as timer:
            await asyncio.sleep(0.05)
        assert timer.elapsed >= 0.05
    
    async def _test_performance_tracking(self, utils):
        """Test performance tracking across multiple calls."""
        for i in range(5):
            async with utils.timer("api_call"):
                await asyncio.sleep(0.01 * (i + 1))
        
        self._assert_timing_stats(utils)
    
    def _assert_profile_data(self, utils, function_name: str):
        """Assert profile data is collected."""
        profile_data = utils.get_profile_data(function_name)
        assert profile_data["call_count"] == 1
        assert profile_data["total_time"] >= 0.1
    
    def _assert_memory_profile(self, utils, function_name: str):
        """Assert memory profile is collected."""
        memory_data = utils.get_memory_profile(function_name)
        assert memory_data["peak_memory"] > 0
    
    def _assert_timing_stats(self, utils):
        """Assert timing statistics are calculated."""
        stats = utils.get_timing_stats("api_call")
        assert stats["count"] == 5
        assert stats["mean"] > 0
        assert stats["max"] >= stats["min"]

# Test 100: Migration utils scripts
class TestMigrationUtilsScripts:
    """test_migration_utils_scripts - Test migration utilities and data transformation"""
    
    @pytest.mark.asyncio
    async def test_migration_utilities(self):
        from netra_backend.app.utils.migration_utils import MigrationUtils
        utils = MigrationUtils()
        
        old_schema = MigrationTestHelpers.create_old_schema()
        new_schema = MigrationTestHelpers.create_new_schema()
        migration_plan = utils.generate_migration_plan(old_schema, new_schema)
        self._assert_migration_plan(migration_plan)
        
        self._test_data_migration(utils, migration_plan)
    
    @pytest.mark.asyncio
    async def test_data_transformation(self):
        from netra_backend.app.utils.migration_utils import MigrationUtils
        utils = MigrationUtils()
        
        self._test_field_transformation(utils)
        await self._test_batch_processing(utils)
    
    def _assert_migration_plan(self, migration_plan):
        """Assert migration plan is correct."""
        assert migration_plan["add_fields"] == ["phone"]
        assert migration_plan["remove_fields"] == []
    
    def _test_data_migration(self, utils, migration_plan):
        """Test data migration with defaults."""
        old_data = MigrationTestHelpers.create_test_data()
        migrated_data = utils.migrate_data(
            old_data, migration_plan, defaults={"phone": None}
        )
        
        assert all("phone" in item for item in migrated_data)
        assert migrated_data[0]["phone"] == None
    
    def _test_field_transformation(self, utils):
        """Test field transformation capabilities."""
        transformations = {
            "full_name": lambda row: f"{row['first_name']} {row['last_name']}",
            "age": lambda row: datetime.now().year - row["birth_year"]
        }
        
        data = MigrationTestHelpers.create_transformation_data()
        transformed = utils.transform_data(data, transformations)
        self._assert_transformation_results(transformed)
    
    async def _test_batch_processing(self, utils):
        """Test batch processing of large datasets."""
        large_dataset = [{"id": i} for i in range(10000)]
        processed_count = 0
        
        async for batch in utils.process_in_batches(large_dataset, batch_size=100):
            processed_count += len(batch)
            assert len(batch) <= 100
        
        assert processed_count == 10000
    
    def _assert_transformation_results(self, transformed):
        """Assert transformation results are correct."""
        assert transformed[0]["full_name"] == "John Doe"
        assert transformed[0]["age"] == datetime.now().year - 1990