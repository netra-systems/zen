"""
Unit tests for WebSocket Compression Handler - Testing message compression and optimization.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Bandwidth optimization and cost reduction
- Value Impact: Reduces data transfer costs and improves performance for users with limited bandwidth
- Strategic Impact: Enables real-time chat for users on mobile networks and reduces infrastructure costs

These tests focus on compression algorithms, bandwidth savings, and ensuring message integrity
while optimizing data transfer for cost-effective real-time communication.
"""

import pytest
import asyncio
import json
import gzip
import zlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from netra_backend.app.websocket_core.compression import (
    WebSocketCompressionHandler,
    CompressionConfig,
    CompressionResult,
    CompressionStats,
    UnsupportedCompressionError
)
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType


class TestWebSocketCompressionHandler:
    """Unit tests for WebSocket compression handling."""
    
    @pytest.fixture
    def compression_config(self):
        """Create compression configuration."""
        return CompressionConfig(
            compression_enabled=True,
            compression_threshold_bytes=100,
            compression_level=6,
            supported_algorithms=['gzip', 'deflate'],
            max_uncompressed_size_mb=10
        )
    
    @pytest.fixture
    def compression_handler(self, compression_config):
        """Create WebSocketCompressionHandler instance."""
        return WebSocketCompressionHandler(config=compression_config)
    
    @pytest.fixture
    def large_message(self):
        """Create large message suitable for compression testing."""
        large_payload = {
            "agent_result": {
                "analysis": "This is a detailed cost analysis with many repeated patterns and text that should compress well. " * 20,
                "recommendations": ["recommendation " + str(i) for i in range(50)],
                "data_points": [{"metric": f"metric_{i}", "value": i * 1.5, "timestamp": datetime.now(timezone.utc).isoformat()} for i in range(100)]
            }
        }
        return WebSocketMessage(
            message_type=MessageType.AGENT_COMPLETED,
            payload=large_payload,
            user_id="user_123"
        )
    
    @pytest.fixture
    def small_message(self):
        """Create small message that shouldn't trigger compression."""
        return WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={"content": "Hello"},
            user_id="user_123"
        )
    
    def test_initializes_with_correct_configuration(self, compression_handler, compression_config):
        """Test CompressionHandler initializes with proper configuration."""
        assert compression_handler.config == compression_config
        assert compression_handler.compression_enabled is True
        assert compression_handler.stats is not None
        assert isinstance(compression_handler.stats, CompressionStats)
        assert compression_handler.stats.total_messages_processed == 0
    
    @pytest.mark.asyncio
    async def test_compresses_large_messages(self, compression_handler, large_message):
        """Test compression of messages exceeding size threshold."""
        # Convert message to JSON for size calculation
        message_json = json.dumps(large_message.to_dict())
        original_size = len(message_json.encode('utf-8'))
        
        # Should exceed threshold and trigger compression
        assert original_size > compression_handler.config.compression_threshold_bytes
        
        # Compress message
        result = await compression_handler.compress_message(large_message)
        
        # Verify compression applied
        assert isinstance(result, CompressionResult)
        assert result.was_compressed is True
        assert result.compression_algorithm in ['gzip', 'deflate']
        assert result.compressed_size < result.original_size
        assert result.compression_ratio > 0
        
        # Verify significant compression achieved
        compression_ratio = result.compressed_size / result.original_size
        assert compression_ratio < 0.8  # Should achieve at least 20% compression
    
    @pytest.mark.asyncio
    async def test_skips_compression_for_small_messages(self, compression_handler, small_message):
        """Test that small messages skip compression."""
        # Convert message to JSON for size calculation
        message_json = json.dumps(small_message.to_dict())
        original_size = len(message_json.encode('utf-8'))
        
        # Should be below threshold
        assert original_size <= compression_handler.config.compression_threshold_bytes
        
        # Process message
        result = await compression_handler.compress_message(small_message)
        
        # Verify compression skipped
        assert isinstance(result, CompressionResult)
        assert result.was_compressed is False
        assert result.compression_algorithm is None
        assert result.compressed_size == result.original_size
        assert result.compression_ratio == 1.0  # No compression
    
    @pytest.mark.asyncio
    async def test_decompresses_messages_correctly(self, compression_handler, large_message):
        """Test decompression maintains message integrity."""
        # Compress message first
        compression_result = await compression_handler.compress_message(large_message)
        
        # Decompress the compressed data
        decompressed_message = await compression_handler.decompress_message(
            compression_result.compressed_data,
            compression_result.compression_algorithm
        )
        
        # Verify perfect reconstruction
        assert isinstance(decompressed_message, WebSocketMessage)
        assert decompressed_message.message_type == large_message.message_type
        assert decompressed_message.user_id == large_message.user_id
        assert decompressed_message.payload == large_message.payload
        
        # Verify specific payload content integrity
        assert decompressed_message.payload["agent_result"]["analysis"] == large_message.payload["agent_result"]["analysis"]
        assert len(decompressed_message.payload["agent_result"]["recommendations"]) == 50
        assert len(decompressed_message.payload["agent_result"]["data_points"]) == 100
    
    @pytest.mark.asyncio
    async def test_handles_different_compression_algorithms(self, compression_handler, large_message):
        """Test support for different compression algorithms."""
        algorithms_to_test = ['gzip', 'deflate']
        results = {}
        
        for algorithm in algorithms_to_test:
            # Configure handler to use specific algorithm
            compression_handler.config.preferred_algorithm = algorithm
            
            # Compress with specific algorithm
            result = await compression_handler.compress_message(large_message)
            results[algorithm] = result
            
            # Verify correct algorithm used
            assert result.compression_algorithm == algorithm
            assert result.was_compressed is True
            
            # Verify decompression works
            decompressed = await compression_handler.decompress_message(
                result.compressed_data, algorithm
            )
            assert decompressed.payload == large_message.payload
        
        # Compare algorithm effectiveness
        gzip_ratio = results['gzip'].compression_ratio
        deflate_ratio = results['deflate'].compression_ratio
        
        # Both should achieve compression (ratios < 1.0)
        assert gzip_ratio < 1.0
        assert deflate_ratio < 1.0
        
        # Ratios should be relatively similar for same content
        assert abs(gzip_ratio - deflate_ratio) < 0.2
    
    @pytest.mark.asyncio
    async def test_tracks_compression_statistics(self, compression_handler, large_message, small_message):
        """Test compression statistics tracking and reporting."""
        initial_stats = compression_handler.stats
        assert initial_stats.total_messages_processed == 0
        
        # Process several messages
        messages = [large_message, small_message, large_message]
        
        for message in messages:
            await compression_handler.compress_message(message)
        
        # Verify stats updated
        stats = compression_handler.stats
        assert stats.total_messages_processed == 3
        assert stats.messages_compressed == 2  # 2 large messages
        assert stats.messages_skipped == 1     # 1 small message
        assert stats.total_bytes_saved > 0
        
        # Verify compression ratio calculation
        assert stats.average_compression_ratio < 1.0
        assert stats.bandwidth_savings_percent > 0
        
        # Verify detailed metrics
        assert stats.total_original_bytes > 0
        assert stats.total_compressed_bytes > 0
        assert stats.total_compressed_bytes < stats.total_original_bytes
    
    @pytest.mark.asyncio
    async def test_enforces_message_size_limits(self, compression_handler):
        """Test enforcement of maximum message size limits."""
        # Create extremely large message exceeding limit
        huge_payload = {
            "enormous_data": "x" * (11 * 1024 * 1024)  # 11MB > 10MB limit
        }
        huge_message = WebSocketMessage(
            message_type=MessageType.AGENT_COMPLETED,
            payload=huge_payload,
            user_id="user_123"
        )
        
        # Should reject message due to size
        with pytest.raises(ValueError) as exc_info:
            await compression_handler.compress_message(huge_message)
        
        assert "exceeds maximum size" in str(exc_info.value).lower()
        
        # Stats should track rejection
        stats = compression_handler.stats
        assert stats.messages_rejected_size >= 1
    
    @pytest.mark.asyncio
    async def test_handles_compression_errors_gracefully(self, compression_handler, large_message):
        """Test graceful handling of compression errors."""
        # Mock compression failure
        with patch('gzip.compress', side_effect=Exception("Compression failed")):
            # Should fall back to uncompressed
            result = await compression_handler.compress_message(large_message)
            
            # Should return uncompressed result
            assert result.was_compressed is False
            assert result.compression_algorithm is None
            assert result.error_message is not None
            assert "compression failed" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_validates_compression_integrity(self, compression_handler, large_message):
        """Test validation of compression/decompression integrity."""
        # Compress message
        result = await compression_handler.compress_message(large_message)
        
        # Verify internal integrity check passes
        assert result.integrity_hash is not None
        
        # Decompress and verify integrity
        decompressed = await compression_handler.decompress_message(
            result.compressed_data, 
            result.compression_algorithm,
            expected_hash=result.integrity_hash
        )
        
        # Should successfully validate integrity
        assert decompressed is not None
        assert decompressed.payload == large_message.payload
    
    @pytest.mark.asyncio
    async def test_optimizes_compression_for_message_types(self, compression_handler):
        """Test optimization of compression based on message types."""
        # Test different message types with similar content
        base_content = {"large_text": "This is repeated content that compresses well. " * 50}
        
        message_types = [
            MessageType.AGENT_COMPLETED,
            MessageType.AGENT_THINKING,
            MessageType.TOOL_COMPLETED,
            MessageType.USER_MESSAGE
        ]
        
        results = {}
        for msg_type in message_types:
            message = WebSocketMessage(
                message_type=msg_type,
                payload=base_content,
                user_id="user_123"
            )
            result = await compression_handler.compress_message(message)
            results[msg_type] = result
        
        # All should be compressed (large content)
        for msg_type, result in results.items():
            assert result.was_compressed is True
            assert result.compression_ratio < 1.0
        
        # Agent result messages might get better compression due to structure
        agent_result = results[MessageType.AGENT_COMPLETED]
        user_message = results[MessageType.USER_MESSAGE]
        
        # Both should achieve good compression
        assert agent_result.compression_ratio < 0.8
        assert user_message.compression_ratio < 0.8
    
    @pytest.mark.asyncio
    async def test_concurrent_compression_operations(self, compression_handler, large_message):
        """Test thread-safe concurrent compression operations."""
        # Create multiple concurrent compression tasks
        tasks = []
        for i in range(10):
            # Create variant of message
            message = WebSocketMessage(
                message_type=large_message.message_type,
                payload={**large_message.payload, "iteration": i},
                user_id=f"user_{i}"
            )
            task = asyncio.create_task(
                compression_handler.compress_message(message)
            )
            tasks.append(task)
        
        # Wait for all compressions to complete
        results = await asyncio.gather(*tasks)
        
        # Verify all succeeded
        assert len(results) == 10
        for result in results:
            assert isinstance(result, CompressionResult)
            assert result.was_compressed is True
            assert result.compression_ratio < 1.0
        
        # Verify stats consistency despite concurrent access
        stats = compression_handler.stats
        assert stats.total_messages_processed >= 10
        assert stats.messages_compressed >= 10
    
    @pytest.mark.asyncio
    async def test_generates_compression_performance_report(self, compression_handler, large_message, small_message):
        """Test generation of compression performance reports."""
        # Generate activity with mixed message sizes
        messages = [large_message] * 5 + [small_message] * 3
        
        for message in messages:
            await compression_handler.compress_message(message)
        
        # Generate performance report
        report = await compression_handler.generate_performance_report()
        
        # Verify report completeness
        assert report is not None
        assert report.total_messages_processed == 8
        assert report.compression_rate_percent > 0  # Some messages compressed
        assert report.total_bandwidth_saved_bytes > 0
        assert report.average_compression_ratio < 1.0
        
        # Should include efficiency metrics
        assert hasattr(report, 'compression_efficiency_rating')
        assert report.compression_efficiency_rating in ['excellent', 'good', 'fair', 'poor']
        
        # Should include cost savings estimation
        assert hasattr(report, 'estimated_cost_savings')
        assert report.estimated_cost_savings.monthly_savings_usd >= 0