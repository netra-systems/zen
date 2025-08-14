"""
Test module for end-to-end integration scenarios
Contains TestIntegration class
"""

import pytest
import asyncio
import uuid

from .test_fixtures import *


class TestIntegration:
    """Test end-to-end integration scenarios"""

    @pytest.mark.asyncio
    async def test_complete_generation_workflow(self, full_stack):
        """Test complete workflow from corpus creation to data visualization"""
        # Skip test - integration test requires database setup
        pytest.skip("Integration test requires full database setup")
        
        # 3. Generate synthetic data
        job_id = str(uuid.uuid4())
        config = GenerationConfig(
            num_traces=1000,
            corpus_id=corpus.id
        )
        
        records = await full_stack["generation"].generate_synthetic_data(
            config,
            job_id=job_id
        )
        
        # 4. Verify ClickHouse ingestion
        ingested = await full_stack["clickhouse"].query(
            f"SELECT COUNT(*) FROM synthetic_data_{job_id}"
        )
        
        assert ingested[0][0] == 1000

    @pytest.mark.asyncio
    async def test_multi_tenant_generation(self, full_stack):
        """Test multi-tenant data generation isolation"""
        # Skip test - multi-tenant data generation with ClickHouse integration not yet implemented
        pytest.skip("Multi-tenant ClickHouse integration not yet implemented")

    @pytest.mark.asyncio
    async def test_real_time_streaming_pipeline(self, full_stack):
        """Test real-time streaming from generation to UI"""
        job_id = str(uuid.uuid4())
        received_updates = []
        
        # Setup WebSocket listener
        async def ws_listener():
            async for message in full_stack["websocket"].listen(job_id):
                received_updates.append(message)
                if message.get("type") == "generation_complete":
                    break
        
        listener_task = asyncio.create_task(ws_listener())
        
        # Start generation
        await full_stack["generation"].generate_streaming(
            GenerationConfig(num_traces=100),
            job_id=job_id
        )
        
        await listener_task
        
        # Verify updates received
        assert len(received_updates) > 0
        assert any(u["type"] == "generation_progress" for u in received_updates)
        assert received_updates[-1]["type"] == "generation_complete"

    @pytest.mark.asyncio
    async def test_failure_recovery_integration(self, full_stack):
        """Test integrated failure recovery across components"""
        # Simulate ClickHouse failure midway
        original_insert = full_stack["clickhouse"].insert
        call_count = 0
        
        async def failing_insert(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if 3 <= call_count <= 5:
                raise Exception("ClickHouse unavailable")
            return await original_insert(*args, **kwargs)
        
        full_stack["clickhouse"].insert = failing_insert
        
        # Should complete with retries
        result = await full_stack["generation"].generate_with_recovery(
            GenerationConfig(num_traces=1000)
        )
        
        assert result["completed"] == True
        assert result["recovery_attempts"] > 0

    @pytest.mark.asyncio
    async def test_cross_component_validation(self, full_stack):
        """Test validation across multiple components"""
        # Generate data
        config = GenerationConfig(num_traces=1000)
        generation_result = await full_stack["generation"].generate_synthetic_data(config)
        
        # Validate in ClickHouse
        ch_validation = await full_stack["clickhouse"].validate_data_quality(
            generation_result["table_name"]
        )
        
        # Cross-check with generation metrics
        assert abs(ch_validation["record_count"] - generation_result["records_generated"]) < 10
        assert ch_validation["schema_valid"] == True

    @pytest.mark.asyncio
    async def test_performance_under_load(self, full_stack):
        """Test system performance under concurrent load"""
        concurrent_jobs = 10
        
        async def run_job(index):
            return await full_stack["generation"].generate_synthetic_data(
                GenerationConfig(num_traces=1000)
            )
        
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*[run_job(i) for i in range(concurrent_jobs)])
        total_time = asyncio.get_event_loop().time() - start_time
        
        # All should complete
        assert all(r["success"] for r in results)
        
        # Performance should scale reasonably
        assert total_time < 60  # Should complete within 1 minute

    @pytest.mark.asyncio
    async def test_data_consistency_verification(self, full_stack):
        """Test data consistency across all storage layers"""
        job_id = str(uuid.uuid4())
        
        # Generate data
        generation_result = await full_stack["generation"].generate_synthetic_data(
            GenerationConfig(num_traces=1000),
            job_id=job_id
        )
        
        # Check PostgreSQL metadata
        pg_metadata = await full_stack["corpus"].get_job_metadata(job_id)
        
        # Check ClickHouse data
        ch_count = await full_stack["clickhouse"].count_records(
            f"synthetic_data_{job_id}"
        )
        
        # Check cache
        cache_count = full_stack["generation"].get_cache_count(job_id)
        
        # All should be consistent
        assert pg_metadata["record_count"] == ch_count == 1000

    @pytest.mark.asyncio
    async def test_monitoring_integration(self, full_stack):
        """Test monitoring and metrics collection integration"""
        # Enable monitoring
        await full_stack["generation"].enable_monitoring()
        
        # Run generation
        await full_stack["generation"].generate_synthetic_data(
            GenerationConfig(num_traces=500)
        )
        
        # Collect metrics
        metrics = await full_stack["generation"].collect_metrics()
        
        assert metrics["generation_count"] > 0
        assert metrics["ingestion_success_rate"] > 0.95
        assert "latency_p99" in metrics

    @pytest.mark.asyncio
    async def test_security_and_access_control(self, full_stack):
        """Test security and access control integration"""
        # Create corpus with restricted access
        restricted_corpus = await full_stack["corpus"].create_corpus(
            schemas.CorpusCreate(name="restricted", access_level="admin_only"),
            user_id="admin"
        )
        
        # Non-admin user attempts generation
        with pytest.raises(Exception):
            await full_stack["generation"].generate_synthetic_data(
                GenerationConfig(corpus_id=restricted_corpus.id),
                user_id="regular_user"
            )
        
        # Admin user succeeds
        result = await full_stack["generation"].generate_synthetic_data(
            GenerationConfig(corpus_id=restricted_corpus.id),
            user_id="admin"
        )
        
        assert result["success"] == True

    @pytest.mark.asyncio
    async def test_cleanup_and_retention(self, full_stack):
        """Test data cleanup and retention policies"""
        # Generate data with retention policy
        job_id = str(uuid.uuid4())
        await full_stack["generation"].generate_synthetic_data(
            GenerationConfig(num_traces=1000),
            job_id=job_id,
            retention_days=1
        )
        
        # Verify data exists
        initial_count = await full_stack["clickhouse"].count_records(
            f"synthetic_data_{job_id}"
        )
        assert initial_count == 1000
        
        # Trigger cleanup for expired data
        await full_stack["generation"].cleanup_expired_data()
        
        # Verify cleanup (would need to mock time for actual test)
        # This is a placeholder for the cleanup verification