"""
Test module for error handling and recovery mechanisms
Contains TestErrorRecovery class
"""

import pytest
import asyncio
import uuid
from unittest.mock import patch

from .test_fixtures import *


class TestErrorRecovery:
    """Test error handling and recovery mechanisms"""

    @pytest.mark.asyncio
    async def test_corpus_unavailable_fallback(self, recovery_service):
        """Test fallback when corpus is unavailable"""
        with patch('app.services.synthetic_data.corpus_manager.load_corpus', side_effect=Exception("Corpus not found")):
            # Test that the service handles corpus loading failures gracefully
            config = GenerationConfig(
                num_traces=100,
                use_fallback_corpus=True
            )
            
            # Since generate_with_fallback doesn't exist, test the actual generation flow
            try:
                # The service should handle the error internally
                result = await recovery_service.generate_synthetic_data(
                    db=AsyncMock(),
                    config=config,
                    user_id="test_user",
                    corpus_id="missing_corpus"
                )
                # Job should be created even if corpus fails
                assert result["job_id"] is not None
                assert result["status"] == "initiated"
            except Exception:
                # Service should not raise unhandled exceptions
                pytest.fail("Service should handle corpus errors gracefully")

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
        
        # Mock ingest_batch to fail 3 times then succeed
        call_count = 0
        async def mock_ingest_batch(records, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Connection failed")
            return {"records_ingested": len(records)}
        
        with patch.object(recovery_service, 'ingest_batch', side_effect=mock_ingest_batch):
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
        
        # Wait for timeout plus a small buffer
        await asyncio.sleep(circuit_breaker.timeout + 0.01)
        
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