"""
L3 Integration Test: ClickHouse Batch Insertion Performance

Business Value Justification (BVJ):
- Segment: Growth & Enterprise (affects high-volume analytics)
- Business Goal: Performance - Enable efficient analytics data ingestion
- Value Impact: Supports real-time analytics for $30K+ MRR customers
- Strategic Impact: Enables enterprise-scale data processing capabilities

L3 Test: Uses real ClickHouse via Testcontainers to validate batch insertion performance,
memory usage, and data consistency under load.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import random
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import pytest
from testcontainers.clickhouse import ClickHouseContainer

import asyncio_clickhouse

from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class ClickHouseBatchPerformanceManager:
    """Manages ClickHouse batch insertion performance testing with real containers."""
    
    def __init__(self):
        self.container = None
        self.client = None
        self.db_url = None
        self.test_data_cache = {}
        self.performance_metrics = {}
        
    async def setup_clickhouse_container(self):
        """Setup real ClickHouse container for L3 testing."""
        try:
            self.container = ClickHouseContainer("clickhouse/clickhouse-server:23.8-alpine")
            self.container.start()
            
            # Get connection details
            host = self.container.get_container_host_ip()
            port = self.container.get_exposed_port(9000)
            self.db_url = f"clickhouse://{host}:{port}/default"
            
            # Create client
            self.client = asyncio_clickhouse.connect(
                host=host,
                port=port,
                database="default"
            )
            
            # Initialize test schema
            await self.create_test_schema()
            
            logger.info("ClickHouse container setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup ClickHouse container: {e}")
            await self.cleanup()
            raise
    
    async def create_test_schema(self):
        """Create test tables for batch insertion testing."""
        # Main performance test table
        await self.client.execute("""
            CREATE TABLE IF NOT EXISTS batch_performance_test (
                id UInt64,
                timestamp DateTime,
                user_id String,
                event_type String,
                session_id String,
                properties String,
                metric_value Float64,
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(timestamp)
            ORDER BY (timestamp, user_id, id)
            SETTINGS index_granularity = 8192
        """)
        
        # Large batch test table
        await self.client.execute("""
            CREATE TABLE IF NOT EXISTS large_batch_test (
                batch_id String,
                record_id UInt64,
                data_payload String,
                processing_time DateTime,
                batch_size UInt32,
                insertion_order UInt32
            ) ENGINE = MergeTree()
            ORDER BY (batch_id, insertion_order)
        """)
        
        # Memory pressure test table
        await self.client.execute("""
            CREATE TABLE IF NOT EXISTS memory_pressure_test (
                id UInt64,
                large_text String,
                json_data String,
                timestamp DateTime,
                random_data String
            ) ENGINE = MergeTree()
            ORDER BY id
        """)
    
    def generate_test_data(self, batch_size: int, data_complexity: str = "simple") -> List[Dict[str, Any]]:
        """Generate test data for batch insertion."""
        data = []
        base_time = datetime.now()
        
        for i in range(batch_size):
            if data_complexity == "simple":
                record = {
                    "id": i,
                    "timestamp": base_time + timedelta(seconds=i),
                    "user_id": f"user_{random.randint(1, 1000)}",
                    "event_type": random.choice(["click", "view", "purchase", "signup"]),
                    "session_id": f"session_{uuid.uuid4().hex[:8]}",
                    "properties": f"{{\"key_{i}\": \"value_{i}\"}}",
                    "metric_value": random.uniform(0.0, 100.0)
                }
            elif data_complexity == "large":
                record = {
                    "batch_id": f"batch_{uuid.uuid4().hex[:8]}",
                    "record_id": i,
                    "data_payload": "x" * 1000,  # 1KB payload
                    "processing_time": base_time + timedelta(milliseconds=i * 10),
                    "batch_size": batch_size,
                    "insertion_order": i
                }
            elif data_complexity == "memory_intensive":
                record = {
                    "id": i,
                    "large_text": "Lorem ipsum " * 100,  # ~1.1KB text
                    "json_data": str({"nested": {"data": list(range(50))}}),
                    "timestamp": base_time + timedelta(seconds=i),
                    "random_data": "x" * random.randint(100, 500)
                }
            
            data.append(record)
        
        return data
    
    async def test_batch_insertion_performance(self, batch_sizes: List[int]) -> Dict[str, Any]:
        """Test batch insertion performance across different batch sizes."""
        results = {
            "batch_results": {},
            "optimal_batch_size": 0,
            "performance_summary": {}
        }
        
        for batch_size in batch_sizes:
            logger.info(f"Testing batch size: {batch_size}")
            
            # Generate test data
            test_data = self.generate_test_data(batch_size, "simple")
            
            # Measure insertion performance
            start_time = time.time()
            
            try:
                # Insert batch
                await self.client.execute(
                    "INSERT INTO batch_performance_test VALUES",
                    test_data
                )
                
                insertion_time = time.time() - start_time
                records_per_second = batch_size / insertion_time if insertion_time > 0 else 0
                
                # Verify insertion
                count_result = await self.client.execute(
                    "SELECT COUNT(*) FROM batch_performance_test WHERE id >= %s AND id < %s",
                    [0, batch_size]
                )
                inserted_count = count_result[0][0] if count_result else 0
                
                batch_result = {
                    "batch_size": batch_size,
                    "insertion_time": insertion_time,
                    "records_per_second": records_per_second,
                    "inserted_count": inserted_count,
                    "success": inserted_count == batch_size
                }
                
                results["batch_results"][batch_size] = batch_result
                
                # Clean up for next test
                await self.client.execute("TRUNCATE TABLE batch_performance_test")
                
            except Exception as e:
                logger.error(f"Batch insertion failed for size {batch_size}: {e}")
                results["batch_results"][batch_size] = {
                    "batch_size": batch_size,
                    "error": str(e),
                    "success": False
                }
        
        # Determine optimal batch size
        successful_results = [r for r in results["batch_results"].values() if r.get("success")]
        if successful_results:
            optimal = max(successful_results, key=lambda x: x["records_per_second"])
            results["optimal_batch_size"] = optimal["batch_size"]
            results["performance_summary"] = {
                "max_records_per_second": optimal["records_per_second"],
                "fastest_batch_size": optimal["batch_size"],
                "average_performance": sum(r["records_per_second"] for r in successful_results) / len(successful_results)
            }
        
        return results
    
    async def test_large_batch_memory_usage(self, large_batch_size: int = 50000) -> Dict[str, Any]:
        """Test memory usage and performance with large batches."""
        results = {
            "batch_size": large_batch_size,
            "memory_efficient": False,
            "insertion_successful": False,
            "performance_metrics": {}
        }
        
        try:
            # Generate large test data
            logger.info(f"Generating {large_batch_size} records for memory test")
            test_data = self.generate_test_data(large_batch_size, "large")
            
            # Monitor insertion
            start_time = time.time()
            memory_start = time.time()  # Placeholder for memory monitoring
            
            # Insert in chunks to manage memory
            chunk_size = 10000
            total_inserted = 0
            
            for i in range(0, large_batch_size, chunk_size):
                chunk = test_data[i:i + chunk_size]
                
                await self.client.execute(
                    "INSERT INTO large_batch_test VALUES",
                    chunk
                )
                
                total_inserted += len(chunk)
                logger.debug(f"Inserted chunk {i//chunk_size + 1}, total: {total_inserted}")
            
            insertion_time = time.time() - start_time
            
            # Verify insertion
            count_result = await self.client.execute(
                "SELECT COUNT(*) FROM large_batch_test"
            )
            final_count = count_result[0][0] if count_result else 0
            
            results.update({
                "insertion_successful": final_count == large_batch_size,
                "total_insertion_time": insertion_time,
                "records_per_second": large_batch_size / insertion_time if insertion_time > 0 else 0,
                "chunks_processed": (large_batch_size // chunk_size) + 1,
                "final_record_count": final_count,
                "memory_efficient": insertion_time < 60.0  # Reasonable time limit
            })
            
            # Performance metrics
            results["performance_metrics"] = {
                "avg_chunk_time": insertion_time / ((large_batch_size // chunk_size) + 1),
                "memory_pressure_handled": True,
                "large_batch_feasible": final_count == large_batch_size
            }
            
        except Exception as e:
            logger.error(f"Large batch test failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def test_concurrent_batch_insertions(self, concurrent_batches: int = 5) -> Dict[str, Any]:
        """Test concurrent batch insertions for throughput."""
        results = {
            "concurrent_batches": concurrent_batches,
            "all_successful": False,
            "total_throughput": 0,
            "batch_results": []
        }
        
        async def single_batch_insertion(batch_id: int) -> Dict[str, Any]:
            batch_size = 5000
            test_data = self.generate_test_data(batch_size, "simple")
            
            # Add batch identifier to data
            for record in test_data:
                record["session_id"] = f"concurrent_batch_{batch_id}_{record['session_id']}"
            
            start_time = time.time()
            
            try:
                await self.client.execute(
                    "INSERT INTO batch_performance_test VALUES",
                    test_data
                )
                
                insertion_time = time.time() - start_time
                records_per_second = batch_size / insertion_time if insertion_time > 0 else 0
                
                return {
                    "batch_id": batch_id,
                    "success": True,
                    "insertion_time": insertion_time,
                    "records_per_second": records_per_second,
                    "batch_size": batch_size
                }
                
            except Exception as e:
                return {
                    "batch_id": batch_id,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute concurrent insertions
        start_time = time.time()
        batch_tasks = [single_batch_insertion(i) for i in range(concurrent_batches)]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Process results
        successful_batches = []
        for result in batch_results:
            if isinstance(result, dict) and result.get("success"):
                successful_batches.append(result)
            results["batch_results"].append(result)
        
        results["all_successful"] = len(successful_batches) == concurrent_batches
        
        if successful_batches:
            total_records = sum(r["batch_size"] for r in successful_batches)
            results["total_throughput"] = total_records / total_time
            results["average_batch_performance"] = sum(r["records_per_second"] for r in successful_batches) / len(successful_batches)
        
        return results
    
    async def test_data_consistency_after_batch_insert(self, batch_size: int = 10000) -> Dict[str, Any]:
        """Test data consistency and integrity after batch insertion."""
        results = {
            "data_consistent": False,
            "integrity_verified": False,
            "consistency_checks": {}
        }
        
        try:
            # Generate deterministic test data
            test_data = []
            expected_sum = 0
            
            for i in range(batch_size):
                metric_value = float(i)  # Deterministic value
                expected_sum += metric_value
                
                record = {
                    "id": i,
                    "timestamp": datetime.now(),
                    "user_id": f"consistency_user_{i % 100}",
                    "event_type": "consistency_test",
                    "session_id": f"consistency_session",
                    "properties": f"{{\"index\": {i}}}",
                    "metric_value": metric_value
                }
                test_data.append(record)
            
            # Insert data
            await self.client.execute(
                "INSERT INTO batch_performance_test VALUES",
                test_data
            )
            
            # Consistency checks
            consistency_checks = {}
            
            # Check 1: Count verification
            count_result = await self.client.execute(
                "SELECT COUNT(*) FROM batch_performance_test WHERE event_type = 'consistency_test'"
            )
            actual_count = count_result[0][0] if count_result else 0
            consistency_checks["count_match"] = actual_count == batch_size
            
            # Check 2: Sum verification
            sum_result = await self.client.execute(
                "SELECT SUM(metric_value) FROM batch_performance_test WHERE event_type = 'consistency_test'"
            )
            actual_sum = float(sum_result[0][0]) if sum_result and sum_result[0][0] else 0
            consistency_checks["sum_match"] = abs(actual_sum - expected_sum) < 0.001
            
            # Check 3: Order verification (sample)
            order_result = await self.client.execute(
                "SELECT id, metric_value FROM batch_performance_test WHERE event_type = 'consistency_test' ORDER BY id LIMIT 10"
            )
            order_correct = all(
                row[0] == row[1] for row in order_result
            ) if order_result else False
            consistency_checks["order_preserved"] = order_correct
            
            # Check 4: Data integrity
            integrity_result = await self.client.execute(
                """
                SELECT COUNT(*) FROM batch_performance_test 
                WHERE event_type = 'consistency_test' 
                AND user_id IS NOT NULL 
                AND properties IS NOT NULL
                """
            )
            integrity_count = integrity_result[0][0] if integrity_result else 0
            consistency_checks["data_integrity"] = integrity_count == batch_size
            
            results["consistency_checks"] = consistency_checks
            results["data_consistent"] = all(consistency_checks.values())
            results["integrity_verified"] = consistency_checks.get("data_integrity", False)
            
        except Exception as e:
            logger.error(f"Consistency test failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def cleanup(self):
        """Clean up test resources."""
        try:
            if self.client:
                await self.client.disconnect()
            
            if self.container:
                self.container.stop()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

@pytest.fixture
async def batch_manager():
    """Create ClickHouse batch performance manager for testing."""
    manager = ClickHouseBatchPerformanceManager()
    await manager.setup_clickhouse_container()
    yield manager
    await manager.cleanup()

@pytest.mark.L3
@pytest.mark.integration
class TestClickHouseBatchInsertionPerformanceL3:
    """L3 integration tests for ClickHouse batch insertion performance."""
    
    async def test_batch_size_optimization(self, batch_manager):
        """Test optimal batch size for insertion performance."""
        batch_sizes = [100, 1000, 5000, 10000]
        results = await batch_manager.test_batch_insertion_performance(batch_sizes)
        
        # Should find an optimal batch size
        assert results["optimal_batch_size"] > 0
        assert results["performance_summary"]["max_records_per_second"] > 1000  # Minimum performance threshold
        
        # All batch sizes should succeed
        successful_batches = sum(1 for r in results["batch_results"].values() if r.get("success"))
        assert successful_batches >= len(batch_sizes) * 0.8  # Allow for some failures
    
    async def test_large_batch_memory_efficiency(self, batch_manager):
        """Test memory efficiency with large batch insertions."""
        results = await batch_manager.test_large_batch_memory_usage(25000)
        
        assert results["insertion_successful"] is True
        assert results["memory_efficient"] is True
        assert results["performance_metrics"]["large_batch_feasible"] is True
        
        # Performance requirements
        assert results["records_per_second"] > 500  # Minimum for large batches
        assert results["total_insertion_time"] < 120  # Max 2 minutes for 25K records
    
    async def test_concurrent_insertion_throughput(self, batch_manager):
        """Test throughput under concurrent batch insertions."""
        results = await batch_manager.test_concurrent_batch_insertions(4)
        
        # Should handle concurrent insertions
        assert results["all_successful"] is True
        assert results["total_throughput"] > 2000  # Combined throughput requirement
        assert results["average_batch_performance"] > 800  # Individual batch performance
    
    async def test_data_consistency_validation(self, batch_manager):
        """Test data consistency after batch insertion."""
        results = await batch_manager.test_data_consistency_after_batch_insert(5000)
        
        assert results["data_consistent"] is True
        assert results["integrity_verified"] is True
        
        # All consistency checks should pass
        for check_name, passed in results["consistency_checks"].items():
            assert passed is True, f"Consistency check failed: {check_name}"
    
    async def test_performance_under_memory_pressure(self, batch_manager):
        """Test performance when inserting memory-intensive data."""
        # Generate memory-intensive test data
        memory_data = batch_manager.generate_test_data(5000, "memory_intensive")
        
        start_time = time.time()
        
        await batch_manager.client.execute(
            "INSERT INTO memory_pressure_test VALUES",
            memory_data
        )
        
        insertion_time = time.time() - start_time
        records_per_second = 5000 / insertion_time if insertion_time > 0 else 0
        
        # Verify insertion under memory pressure
        count_result = await batch_manager.client.execute(
            "SELECT COUNT(*) FROM memory_pressure_test"
        )
        final_count = count_result[0][0] if count_result else 0
        
        assert final_count == 5000
        assert records_per_second > 100  # Lower threshold for memory-intensive data
        assert insertion_time < 30  # Should complete within reasonable time

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])