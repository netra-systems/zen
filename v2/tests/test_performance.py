"""Performance and load tests for critical functionality"""

import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, AsyncMock, patch
import uuid

class TestPerformance:
    """Performance test suite for critical operations"""
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections(self, mock_websocket_manager):
        """Test handling multiple concurrent WebSocket connections"""
        
        async def connect_client(client_id):
            start_time = time.time()
            await mock_websocket_manager.connect(f"user_{client_id}", MagicMock())
            connection_time = time.time() - start_time
            return connection_time
        
        # Simulate 100 concurrent connections
        num_connections = 100
        tasks = [connect_client(i) for i in range(num_connections)]
        
        start_time = time.time()
        connection_times = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        avg_connection_time = statistics.mean(connection_times)
        max_connection_time = max(connection_times)
        
        # Performance assertions
        assert total_time < 5.0, f"100 connections took {total_time:.2f}s (should be < 5s)"
        assert avg_connection_time < 0.1, f"Avg connection time {avg_connection_time:.3f}s (should be < 0.1s)"
        assert max_connection_time < 0.5, f"Max connection time {max_connection_time:.3f}s (should be < 0.5s)"
    
    @pytest.mark.asyncio
    async def test_message_throughput(self, mock_agent_service):
        """Test message processing throughput"""
        
        mock_agent_service.process_message = AsyncMock(return_value={"response": "ok"})
        
        async def process_message(msg_id):
            start_time = time.time()
            await mock_agent_service.process_message(
                thread_id=str(uuid.uuid4()),
                message=f"Message {msg_id}",
                user_id="test_user"
            )
            return time.time() - start_time
        
        # Process 500 messages
        num_messages = 500
        tasks = [process_message(i) for i in range(num_messages)]
        
        start_time = time.time()
        processing_times = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        throughput = num_messages / total_time
        avg_processing_time = statistics.mean(processing_times)
        
        # Performance assertions
        assert throughput > 100, f"Throughput {throughput:.1f} msg/s (should be > 100 msg/s)"
        assert avg_processing_time < 0.05, f"Avg processing {avg_processing_time:.3f}s (should be < 0.05s)"
    
    @pytest.mark.asyncio
    async def test_database_query_performance(self, async_session):
        """Test database query performance under load"""
        
        # Insert test data
        from app.db.models_postgres import Thread, Message
        
        threads = []
        for i in range(100):
            thread = Thread(
                id=str(uuid.uuid4()),
                object="thread",
                created_at=int(time.time()),
                metadata_={"test": True}
            )
            threads.append(thread)
            async_session.add(thread)
        
        await async_session.commit()
        
        # Test query performance
        query_times = []
        for _ in range(50):
            start_time = time.time()
            
            from sqlalchemy import select
            result = await async_session.execute(
                select(Thread).limit(10)
            )
            result.scalars().all()
            
            query_times.append(time.time() - start_time)
        
        avg_query_time = statistics.mean(query_times)
        max_query_time = max(query_times)
        
        # Performance assertions
        assert avg_query_time < 0.01, f"Avg query time {avg_query_time:.3f}s (should be < 0.01s)"
        assert max_query_time < 0.05, f"Max query time {max_query_time:.3f}s (should be < 0.05s)"
    
    @pytest.mark.asyncio
    async def test_token_generation_performance(self):
        """Test JWT token generation performance"""
        
        from app.auth.auth import create_access_token
        
        token_times = []
        for i in range(1000):
            start_time = time.time()
            token = create_access_token({"sub": f"user_{i}@test.com"})
            token_times.append(time.time() - start_time)
        
        avg_token_time = statistics.mean(token_times)
        total_time = sum(token_times)
        
        # Performance assertions
        assert avg_token_time < 0.001, f"Avg token generation {avg_token_time:.4f}s (should be < 0.001s)"
        assert total_time < 1.0, f"1000 tokens took {total_time:.2f}s (should be < 1s)"
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, mock_redis_manager):
        """Test cache read/write performance"""
        
        mock_redis_manager.get = AsyncMock(return_value="cached_value")
        mock_redis_manager.set = AsyncMock(return_value=True)
        
        # Test cache writes
        write_times = []
        for i in range(500):
            start_time = time.time()
            await mock_redis_manager.set(f"key_{i}", f"value_{i}")
            write_times.append(time.time() - start_time)
        
        # Test cache reads
        read_times = []
        for i in range(500):
            start_time = time.time()
            await mock_redis_manager.get(f"key_{i}")
            read_times.append(time.time() - start_time)
        
        avg_write_time = statistics.mean(write_times)
        avg_read_time = statistics.mean(read_times)
        
        # Performance assertions
        assert avg_write_time < 0.005, f"Avg cache write {avg_write_time:.4f}s (should be < 0.005s)"
        assert avg_read_time < 0.003, f"Avg cache read {avg_read_time:.4f}s (should be < 0.003s)"
    
    @pytest.mark.asyncio
    async def test_llm_response_streaming(self, mock_llm_manager):
        """Test LLM response streaming performance"""
        
        async def mock_stream():
            for i in range(10):
                await asyncio.sleep(0.01)
                yield f"chunk_{i}"
        
        mock_llm_manager.stream_completion = mock_stream
        
        chunks_received = []
        chunk_times = []
        
        start_time = time.time()
        async for chunk in mock_llm_manager.stream_completion():
            chunk_times.append(time.time() - start_time)
            chunks_received.append(chunk)
        
        total_time = time.time() - start_time
        
        # Calculate inter-chunk delays
        inter_chunk_delays = []
        for i in range(1, len(chunk_times)):
            inter_chunk_delays.append(chunk_times[i] - chunk_times[i-1])
        
        avg_delay = statistics.mean(inter_chunk_delays) if inter_chunk_delays else 0
        
        # Performance assertions
        assert len(chunks_received) == 10
        assert total_time < 0.2, f"Streaming took {total_time:.2f}s (should be < 0.2s)"
        assert avg_delay < 0.02, f"Avg inter-chunk delay {avg_delay:.3f}s (should be < 0.02s)"
    
    @pytest.mark.asyncio
    async def test_parallel_api_requests(self, client, auth_headers):
        """Test handling parallel API requests"""
        
        with patch("app.services.agent_service.AgentService.list_threads") as mock_list:
            mock_list.return_value = []
            
            async def make_request():
                return client.get("/api/threads", headers=auth_headers)
            
            # Make 50 parallel requests
            num_requests = 50
            with ThreadPoolExecutor(max_workers=10) as executor:
                start_time = time.time()
                futures = [executor.submit(make_request) for _ in range(num_requests)]
                
                response_times = []
                for future in as_completed(futures):
                    response_times.append(time.time() - start_time)
                
                total_time = time.time() - start_time
            
            requests_per_second = num_requests / total_time
            
            # Performance assertions
            assert requests_per_second > 50, f"RPS {requests_per_second:.1f} (should be > 50)"
            assert total_time < 2.0, f"50 requests took {total_time:.2f}s (should be < 2s)"
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test memory efficiency of large operations"""
        
        import sys
        
        # Test large list handling
        large_list = list(range(1000000))
        list_size = sys.getsizeof(large_list)
        
        # Process in chunks to avoid memory spike
        chunk_size = 10000
        processed = 0
        
        for i in range(0, len(large_list), chunk_size):
            chunk = large_list[i:i+chunk_size]
            processed += len(chunk)
        
        assert processed == len(large_list)
        assert list_size < 10 * 1024 * 1024, f"List size {list_size/1024/1024:.1f}MB (should be < 10MB)"
    
    @pytest.mark.asyncio
    async def test_error_recovery_performance(self, mock_agent_service):
        """Test system recovery performance after errors"""
        
        call_count = 0
        
        async def flaky_process(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise Exception("Temporary error")
            return {"success": True}
        
        mock_agent_service.process_message = flaky_process
        
        success_count = 0
        error_count = 0
        recovery_times = []
        
        for i in range(30):
            start_time = time.time()
            try:
                await mock_agent_service.process_message(
                    thread_id="test",
                    message=f"msg_{i}",
                    user_id="user"
                )
                success_count += 1
                if error_count > 0:
                    recovery_times.append(time.time() - start_time)
                    error_count = 0
            except:
                error_count += 1
        
        avg_recovery_time = statistics.mean(recovery_times) if recovery_times else 0
        
        # Performance assertions
        assert success_count >= 20, f"Success count {success_count} (should be >= 20)"
        assert avg_recovery_time < 0.1, f"Avg recovery {avg_recovery_time:.3f}s (should be < 0.1s)"