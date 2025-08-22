"""WebSocket Message Compression System.

Implements efficient compression for large WebSocket payloads
with multiple compression algorithms and automatic threshold detection.
"""

import base64
import json
from typing import Any, Dict, Optional, Tuple, Union

from netra_backend.app.compression_algorithms import (
    CompressionAlgorithmHandler,
    CompressionAlgorithmSelector,
    CompressionBenchmark,
)
from netra_backend.app.compression_config import (
    CompressionAlgorithm,
    CompressionConfig,
    CompressionResult,
    CompressionStatsManager,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketCompressor:
    """Handles WebSocket message compression."""
    
    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
        self.stats_manager = CompressionStatsManager()
        self.algorithm_handler = CompressionAlgorithmHandler(self.config)
        self.algorithm_selector = CompressionAlgorithmSelector(self.config)
        self.benchmark = CompressionBenchmark(self.algorithm_handler)
    
    def compress_message(self, message: Dict[str, Any]) -> Tuple[Union[str, bytes], CompressionResult]:
        """Compress a WebSocket message if beneficial."""
        start_time = self._start_compression_timer()
        json_data, original_size = self._serialize_and_track(message)
        if self._should_skip_compression(original_size):
            return self._create_uncompressed_result(json_data, original_size, start_time)
        return self._attempt_compression(json_data, original_size, start_time)
    
    def decompress_message(self, compressed_data: str) -> Dict[str, Any]:
        """Decompress a WebSocket message."""
        try:
            message_data = json.loads(compressed_data)
            return self._process_message_data(message_data)
        except Exception as e:
            return self._handle_decompression_error(compressed_data, e)
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        stats_components = self.stats_manager.get_compression_stats()
        return {**stats_components, "config": self.config.__dict__}
    
    def reset_stats(self) -> None:
        """Reset compression statistics."""
        self.stats_manager.reset_stats()
        logger.info("Compression statistics reset")
    
    def update_config(self, new_config: CompressionConfig) -> None:
        """Update compression configuration."""
        self.config = new_config
        logger.info(f"Updated compression configuration: {new_config}")
    
    def benchmark_algorithms(self, test_data: str) -> Dict[str, Any]:
        """Benchmark different compression algorithms on test data."""
        return self.benchmark.benchmark_algorithms(test_data)
    
    def _should_skip_compression(self, size: int) -> bool:
        """Check if compression should be skipped based on size."""
        return size < self.config.min_size_bytes
    
    def _process_message_data(self, message_data: Any) -> Dict[str, Any]:
        """Process message data for decompression."""
        if not self._is_compressed_message(message_data):
            return message_data
        return self._perform_decompression(message_data)
    
    def _is_compressed_message(self, message_data: Any) -> bool:
        """Check if message data is a compressed message."""
        return (isinstance(message_data, dict) and message_data.get("compressed", False))
    
    def _perform_decompression(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform the actual decompression of message data."""
        algorithm = CompressionAlgorithm(message_data["algorithm"])
        compressed_bytes = base64.b64decode(message_data["data"])
        decompressed_data = self.algorithm_handler.decompress_data(compressed_bytes, algorithm)
        return json.loads(decompressed_data)
    
    def _handle_decompression_error(self, compressed_data: str, error: Exception) -> Dict[str, Any]:
        """Handle decompression errors with fallback."""
        logger.error(f"Decompression failed: {error}")
        try:
            return json.loads(compressed_data)
        except:
            raise ValueError(f"Failed to decompress message: {error}")
    
    def _start_compression_timer(self) -> float:
        """Start compression timing."""
        import time
        return time.time()
    
    def _serialize_and_track(self, message: Dict[str, Any]) -> Tuple[str, int]:
        """Serialize message and update tracking stats."""
        json_data = json.dumps(message, default=str)
        original_size = len(json_data.encode('utf-8'))
        self.stats_manager.update_message_stats(original_size)
        return json_data, original_size
    
    def _create_uncompressed_result(self, json_data: str, original_size: int, 
                                  start_time: float) -> Tuple[str, CompressionResult]:
        """Create result for uncompressed data."""
        import time
        compression_time = (time.time() - start_time) * 1000
        result = self._build_uncompressed_result(original_size, compression_time)
        return json_data, result
    
    def _build_uncompressed_result(self, original_size: int, compression_time: float) -> CompressionResult:
        """Build CompressionResult for uncompressed data."""
        return CompressionResult(
            original_size=original_size, compressed_size=original_size,
            compression_ratio=1.0, algorithm=CompressionAlgorithm.NONE,
            compression_time_ms=compression_time, is_compressed=False
        )
    
    def _attempt_compression(self, json_data: str, original_size: int, 
                           start_time: float) -> Tuple[Union[str, bytes], CompressionResult]:
        """Attempt to compress data with fallback."""
        algorithm = self.algorithm_selector.select_algorithm(json_data)
        try:
            return self._perform_compression(json_data, original_size, algorithm, start_time)
        except Exception as e:
            return self._handle_compression_failure(e, algorithm, json_data, original_size, start_time)
    
    def _handle_compression_failure(self, error: Exception, algorithm: CompressionAlgorithm, 
                                  json_data: str, original_size: int, 
                                  start_time: float) -> Tuple[str, CompressionResult]:
        """Handle compression failure with fallback."""
        logger.warning(f"Compression failed with {algorithm.value}: {error}")
        return self._create_uncompressed_result(json_data, original_size, start_time)
    
    def _perform_compression(self, json_data: str, original_size: int, 
                           algorithm: CompressionAlgorithm, start_time: float) -> Tuple[str, CompressionResult]:
        """Perform actual compression operation."""
        compressed_data = self.algorithm_handler.compress_data(json_data, algorithm)
        compressed_size = len(compressed_data)
        compression_ratio = compressed_size / original_size
        if compression_ratio > 0.9:
            return self._create_uncompressed_result(json_data, original_size, start_time)
        return self._create_compressed_result(
            json_data, original_size, compressed_data, compressed_size, algorithm, start_time
        )
    
    def _create_compressed_result(self, json_data: str, original_size: int, compressed_data: bytes, 
                                compressed_size: int, algorithm: CompressionAlgorithm, 
                                start_time: float) -> Tuple[str, CompressionResult]:
        """Create result for successfully compressed data."""
        compressed_message = self._create_compressed_message(compressed_data, algorithm, original_size)
        compression_time = self._calculate_compression_time(start_time)
        self.stats_manager.update_compression_stats(compressed_size, compression_time, algorithm)
        result = self._build_compression_result(original_size, compressed_size, algorithm, compression_time)
        return json.dumps(compressed_message), result
    
    def _calculate_compression_time(self, start_time: float) -> float:
        """Calculate compression time in milliseconds."""
        import time
        return (time.time() - start_time) * 1000
    
    def _build_compression_result(self, original_size: int, compressed_size: int, 
                                algorithm: CompressionAlgorithm, compression_time: float) -> CompressionResult:
        """Build CompressionResult object."""
        return CompressionResult(
            original_size=original_size, compressed_size=compressed_size,
            compression_ratio=compressed_size / original_size, algorithm=algorithm,
            compression_time_ms=compression_time, is_compressed=True
        )
    
    def _create_compressed_message(self, compressed_data: bytes, algorithm: CompressionAlgorithm, 
                                 original_size: int) -> Dict[str, Any]:
        """Create compressed message wrapper."""
        return {
            "compressed": True, "algorithm": algorithm.value, "original_size": original_size,
            "data": base64.b64encode(compressed_data).decode('utf-8')
        }


# Re-export classes for backward compatibility
from netra_backend.app.compression_algorithms import (
    CompressionAlgorithmHandler,
    CompressionAlgorithmSelector,
    CompressionBenchmark,
)
from netra_backend.app.compression_config import (
    CompressionAlgorithm,
    CompressionConfig,
    CompressionResult,
    CompressionStatsManager,
)

__all__ = [
    "WebSocketCompressor", "CompressionAlgorithm", "CompressionConfig", "CompressionResult",
    "CompressionStatsManager", "CompressionAlgorithmHandler", "CompressionAlgorithmSelector",
    "CompressionBenchmark"
]