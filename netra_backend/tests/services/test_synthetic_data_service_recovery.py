"""
Error Recovery Test Suite for Synthetic Data Service
Testing error handling and recovery mechanisms
"""

import sys
from pathlib import Path

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import pytest

from netra_backend.app.services.synthetic_data_service import SyntheticDataService
from netra_backend.tests.services.test_synthetic_data_service_basic import GenerationConfig

@pytest.fixture
def recovery_service():
    return SyntheticDataService()

# ==================== Test Suite: Error Recovery ====================

class TestErrorRecovery:
    """Test error handling and recovery mechanisms"""
    @pytest.mark.asyncio
    async def test_corpus_unavailable_fallback(self, recovery_service):
        """Test fallback when corpus is unavailable"""
        with patch.object(recovery_service, 'get_corpus_content', side_effect=Exception("Corpus not found")):
            config = GenerationConfig(
                num_traces=100,
                use_fallback_corpus=True
            )
            
            records = await recovery_service.generate_with_fallback(config)
            
            assert len(records) == 100
            assert all(r.get("source") == "fallback_corpus" for r in records)
    @pytest.mark.asyncio
    async def test_clickhouse_connection_recovery(self, recovery_service):
        """Test recovery from ClickHouse connection failures"""
        failure_count = 0
        
        async def flaky_connection(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise Exception("Connection failed")
            return AsyncMock()
        
        with patch('app.services.synthetic_data_service.get_clickhouse_client', side_effect=flaky_connection):
            result = await recovery_service.ingest_with_retry(
                [{"id": 1}],
                max_retries=5,
                retry_delay_ms=10
            )
            
            assert result["success"] == True
            assert result["retry_count"] == 3
    @pytest.mark.asyncio
    async def test_generation_checkpoint_recovery(self, recovery_service):
        """Test recovery from generation crashes using checkpoints"""
        # Simulate crash at 50%
        with patch.object(recovery_service, 'generate_batch') as mock_gen:
            mock_gen.side_effect = [
                [{"id": i} for i in range(100)],  # First batch OK
                Exception("Generation crashed"),  # Crash
            ]
            
            config = GenerationConfig(
                num_traces=200,
                checkpoint_interval=100
            )
            
            try:
                await recovery_service.generate_with_checkpoints(config)
            except Exception:
                pass  # Expected to fail for testing recovery
            
            # Resume from checkpoint
            resumed_result = await recovery_service.resume_from_checkpoint(config)
            
            assert resumed_result["resumed_from_record"] == 100
            assert len(resumed_result["records"]) == 200
    @pytest.mark.asyncio
    async def test_websocket_disconnect_recovery(self, recovery_service):
        """Test recovery from WebSocket disconnections"""
        ws_manager = MagicMock()
        disconnect_count = 0
        
        async def flaky_send(job_id, data):
            nonlocal disconnect_count
            disconnect_count += 1
            if disconnect_count == 3:
                raise Exception("WebSocket disconnected")
            return None
        
        ws_manager.broadcast_to_job = flaky_send
        
        # Should continue generation despite WS failures
        result = await recovery_service.generate_with_ws_updates(
            GenerationConfig(num_traces=100),
            ws_manager=ws_manager
        )
        
        assert result["generation_complete"] == True
        assert result["ws_failures"] == 1
    @pytest.mark.asyncio
    async def test_memory_overflow_handling(self, recovery_service):
        """Test handling of memory overflow conditions"""
        config = GenerationConfig(
            num_traces=1000000,  # Very large
            memory_limit_mb=50
        )
        
        result = await recovery_service.generate_with_memory_limit(config)
        
        # Should complete with reduced batch sizes
        assert result["completed"] == True
        assert result["memory_overflow_prevented"] == True
        assert result["batch_size_reduced"] == True
    @pytest.mark.asyncio
    async def test_circuit_breaker_operation(self, recovery_service):
        """Test circuit breaker preventing cascade failures"""
        circuit_breaker = recovery_service.get_circuit_breaker()
        
        # Simulate repeated failures
        for _ in range(5):
            try:
                await circuit_breaker.call(lambda: 1/0)
            except (ZeroDivisionError, Exception):
                pass  # Expected division by zero for testing
        
        # Circuit should open
        assert circuit_breaker.state == "open"
        
        # Wait for timeout
        await asyncio.sleep(circuit_breaker.timeout)
        
        # Should transition to half-open
        assert circuit_breaker.state == "half_open"
    @pytest.mark.asyncio
    async def test_dead_letter_queue_processing(self, recovery_service):
        """Test dead letter queue for failed records"""
        records = [{"id": i, "fail": i % 10 == 0} for i in range(100)]
        
        async def process_with_failures(record):
            if record.get("fail"):
                raise Exception("Processing failed")
            return record
        
        result = await recovery_service.process_with_dlq(
            records,
            process_fn=process_with_failures
        )
        
        assert len(result["processed"]) == 90
        assert len(result["dead_letter_queue"]) == 10
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, recovery_service):
        """Test transaction rollback on failures"""
        async def failing_operation():
            # Start transaction
            tx = await recovery_service.begin_transaction()
            
            # Partial success
            await tx.insert_records([{"id": 1}, {"id": 2}])
            
            # Failure
            raise Exception("Operation failed")
        
        try:
            await failing_operation()
        except Exception:
            pass  # Expected to fail for testing fallback
        
        # Should have rolled back
        result = await recovery_service.query_records()
        assert len(result) == 0
    @pytest.mark.asyncio
    async def test_idempotent_generation(self, recovery_service):
        """Test idempotent generation to prevent duplicates"""
        job_id = str(uuid.uuid4())
        config = GenerationConfig(
            num_traces=100,
            job_id=job_id
        )
        
        # First generation
        result1 = await recovery_service.generate_idempotent(config)
        
        # Duplicate request with same job_id
        result2 = await recovery_service.generate_idempotent(config)
        
        # Should return cached result
        assert result2["cached"] == True
        assert result1["records"] == result2["records"]
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, recovery_service):
        """Test graceful degradation under failures"""
        config = GenerationConfig(
            num_traces=1000,
            required_features=["corpus_sampling", "tool_simulation", "clustering"],
            degradation_allowed=True
        )
        
        # Simulate feature failures
        with patch.object(recovery_service, 'enable_clustering', side_effect=Exception("Clustering unavailable")):
            result = await recovery_service.generate_with_degradation(config)
        
        assert result["completed"] == True
        assert "clustering" in result["disabled_features"]
        assert len(result["records"]) == 1000

# ==================== Test Runner ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])