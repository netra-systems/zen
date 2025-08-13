"""
Tests for DataSubAgent processing methods - batch processing, retry logic, streaming
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from app.agents.data_sub_agent import DataSubAgent


class TestDataSubAgentProcessing:
    """Test DataSubAgent processing and utility methods"""
    
    @pytest.mark.asyncio
    async def test_process_data_valid(self, agent):
        """Test process_data with valid data"""
        data = {"valid": True, "content": "test"}
        result = await agent.process_data(data)
        
        assert result["status"] == "success"
        assert result["processed"] == True
        
    @pytest.mark.asyncio
    async def test_process_data_invalid(self, agent):
        """Test process_data with invalid data"""
        data = {"valid": False, "content": "test"}
        result = await agent.process_data(data)
        
        assert result["status"] == "error"
        assert result["message"] == "Invalid data"
        
    @pytest.mark.asyncio
    async def test_process_internal_success(self, agent):
        """Test _process_internal with successful processing"""
        data = {"content": "test"}
        result = await agent._process_internal(data)
        
        assert result["success"] == True
        assert result["data"] == data
        
    @pytest.mark.asyncio
    async def test_process_with_retry_immediate_success(self, agent):
        """Test process_with_retry with immediate success"""
        agent.config = {'max_retries': 3}
        data = {"content": "test"}
        result = await agent.process_with_retry(data)
        
        assert result["success"] == True
        
    @pytest.mark.asyncio
    async def test_process_with_retry_success_after_failures(self, agent):
        """Test process_with_retry succeeds after failures"""
        agent.config = {'max_retries': 3}
        data = {"content": "test"}
        
        with patch.object(agent, '_process_internal', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = [
                Exception("Error 1"),
                Exception("Error 2"),
                {"success": True, "data": data}
            ]
            
            result = await agent.process_with_retry(data)
            
        assert result["success"] == True
        assert mock_process.call_count == 3
        
    @pytest.mark.asyncio
    async def test_process_with_retry_all_failures(self, agent):
        """Test process_with_retry fails after max retries"""
        agent.config = {'max_retries': 2}
        data = {"content": "test"}
        
        with patch.object(agent, '_process_internal', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = Exception("Persistent error")
            
            with pytest.raises(Exception, match="Persistent error"):
                await agent.process_with_retry(data)
                
        assert mock_process.call_count == 2
        
    @pytest.mark.asyncio
    async def test_process_batch_safe_mixed_results(self, agent):
        """Test process_batch_safe with mixed valid/invalid items"""
        batch = [
            {"id": 1, "valid": True, "data": "item1"},
            {"id": 2, "valid": False, "data": "item2"},
            {"id": 3, "valid": True, "data": "item3"}
        ]
        
        results = await agent.process_batch_safe(batch)
        
        assert len(results) == 3
        assert results[0]["status"] == "success"
        assert results[1]["status"] == "error"
        assert results[2]["status"] == "success"
        
    @pytest.mark.asyncio
    async def test_process_batch_safe_with_exception(self, agent):
        """Test process_batch_safe handling exceptions"""
        batch = [{"id": 1, "data": "item1"}]
        
        with patch.object(agent, 'process_data', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = Exception("Processing failed")
            
            results = await agent.process_batch_safe(batch)
            
        assert results[0]["status"] == "error"
        assert "Processing failed" in results[0]["message"]
        
    @pytest.mark.asyncio
    async def test_process_with_cache_hit(self, agent):
        """Test process_with_cache with cache hit"""
        data = {"id": "test_cache"}
        
        # First call populates cache
        result1 = await agent.process_with_cache(data)
        
        # Second call should use cache
        with patch.object(agent, '_process_internal', new_callable=AsyncMock) as mock_process:
            result2 = await agent.process_with_cache(data)
            
        assert result1 == result2
        mock_process.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_process_with_cache_different_keys(self, agent):
        """Test process_with_cache with different cache keys"""
        data1 = {"id": "cache1"}
        data2 = {"id": "cache2"}
        
        result1 = await agent.process_with_cache(data1)
        result2 = await agent.process_with_cache(data2)
        
        # Different IDs should have different cache entries
        assert result1["data"]["id"] == "cache1"
        assert result2["data"]["id"] == "cache2"
        
    @pytest.mark.asyncio
    async def test_process_and_stream(self, agent):
        """Test process_and_stream method"""
        data = {"content": "stream test"}
        mock_ws = Mock()
        mock_ws.send = AsyncMock()
        
        await agent.process_and_stream(data, mock_ws)
        
        mock_ws.send.assert_called_once()
        sent_data = mock_ws.send.call_args[0][0]
        parsed = json.loads(sent_data)
        assert parsed["processed"] == True
        
    @pytest.mark.asyncio
    async def test_process_and_persist(self, agent):
        """Test process_and_persist method"""
        data = {"content": "persist test"}
        
        result = await agent.process_and_persist(data)
        
        assert result["processed"] == True
        assert result["persisted"] == True
        assert result["id"] == "saved_123"
        
    @pytest.mark.asyncio
    async def test_handle_supervisor_request_process_data(self, agent):
        """Test handle_supervisor_request with process_data action"""
        callback = AsyncMock()
        request = {
            "action": "process_data",
            "data": {"content": "supervisor data"},
            "callback": callback
        }
        
        result = await agent.handle_supervisor_request(request)
        
        assert result["status"] == "completed"
        callback.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_handle_supervisor_request_no_callback(self, agent):
        """Test handle_supervisor_request without callback"""
        request = {
            "action": "unknown_action",
            "data": {"content": "test"}
        }
        
        result = await agent.handle_supervisor_request(request)
        
        assert result["status"] == "completed"
        
    @pytest.mark.asyncio
    async def test_process_concurrent(self, agent):
        """Test process_concurrent method"""
        items = [{"id": i} for i in range(5)]
        
        results = await agent.process_concurrent(items, max_concurrent=2)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["data"]["id"] == i
            
    @pytest.mark.asyncio
    async def test_process_concurrent_empty(self, agent):
        """Test process_concurrent with empty list"""
        results = await agent.process_concurrent([], max_concurrent=10)
        assert results == []
        
    @pytest.mark.asyncio
    async def test_process_stream(self, agent):
        """Test process_stream generator method"""
        dataset = range(250)
        chunks = []
        
        async for chunk in agent.process_stream(dataset, chunk_size=100):
            chunks.append(chunk)
            
        assert len(chunks) == 3
        assert len(chunks[0]) == 100
        assert len(chunks[1]) == 100
        assert len(chunks[2]) == 50
        
    @pytest.mark.asyncio
    async def test_process_stream_exact_chunks(self, agent):
        """Test process_stream with exact chunk size"""
        dataset = range(200)
        chunks = []
        
        async for chunk in agent.process_stream(dataset, chunk_size=100):
            chunks.append(chunk)
            
        assert len(chunks) == 2
        assert len(chunks[0]) == 100
        assert len(chunks[1]) == 100