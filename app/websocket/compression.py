"""WebSocket Message Compression System.

Implements efficient compression for large WebSocket payloads
with multiple compression algorithms and automatic threshold detection.
"""

import gzip
import zlib
import lz4.frame
import json
import base64
from typing import Dict, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass
from enum import Enum

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CompressionAlgorithm(str, Enum):
    """Available compression algorithms."""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    LZ4 = "lz4"


@dataclass
class CompressionConfig:
    """Compression configuration."""
    algorithm: CompressionAlgorithm = CompressionAlgorithm.LZ4
    min_size_bytes: int = 1024  # Only compress messages larger than 1KB
    compression_level: int = 1  # Fast compression by default
    auto_select_algorithm: bool = True
    max_compression_time_ms: float = 10.0


@dataclass
class CompressionResult:
    """Result of compression operation."""
    original_size: int
    compressed_size: int
    compression_ratio: float
    algorithm: CompressionAlgorithm
    compression_time_ms: float
    is_compressed: bool


class WebSocketCompressor:
    """Handles WebSocket message compression."""
    
    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
        self.stats = self._initialize_compression_stats()

    def _initialize_compression_stats(self) -> Dict[str, Any]:
        """Initialize compression statistics."""
        return {
            "total_messages": 0, "compressed_messages": 0, "total_bytes_original": 0,
            "total_bytes_compressed": 0, "compression_time_ms": 0.0,
            "algorithm_usage": {alg.value: 0 for alg in CompressionAlgorithm}
        }
    
    def compress_message(self, message: Dict[str, Any]) -> Tuple[Union[str, bytes], CompressionResult]:
        """Compress a WebSocket message if beneficial."""
        start_time = self._start_compression_timer()
        json_data, original_size = self._serialize_and_track(message)
        if self._should_skip_compression(original_size):
            return self._create_uncompressed_result(json_data, original_size, start_time)
        return self._attempt_compression(json_data, original_size, start_time)

    def _should_skip_compression(self, size: int) -> bool:
        """Check if compression should be skipped based on size."""
        return size < self.config.min_size_bytes
    
    def decompress_message(self, compressed_data: str) -> Dict[str, Any]:
        """Decompress a WebSocket message."""
        try:
            message_data = json.loads(compressed_data)
            return self._process_message_data(message_data)
        except Exception as e:
            return self._handle_decompression_error(compressed_data, e)

    def _process_message_data(self, message_data: Any) -> Dict[str, Any]:
        """Process message data for decompression."""
        if not self._is_compressed_message(message_data):
            return message_data
        return self._perform_decompression(message_data)

    def _is_compressed_message(self, message_data: Any) -> bool:
        """Check if message data is a compressed message."""
        return (isinstance(message_data, dict) and 
               message_data.get("compressed", False))

    def _perform_decompression(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform the actual decompression of message data."""
        algorithm = CompressionAlgorithm(message_data["algorithm"])
        compressed_bytes = base64.b64decode(message_data["data"])
        decompressed_data = self._decompress_data(compressed_bytes, algorithm)
        return json.loads(decompressed_data)

    def _handle_decompression_error(self, compressed_data: str, error: Exception) -> Dict[str, Any]:
        """Handle decompression errors with fallback."""
        logger.error(f"Decompression failed: {error}")
        try:
            return json.loads(compressed_data)
        except:
            raise ValueError(f"Failed to decompress message: {error}")
    
    def _select_algorithm(self, data: str) -> CompressionAlgorithm:
        """Select the best compression algorithm for the data."""
        if not self.config.auto_select_algorithm:
            return self.config.algorithm
        return self._get_default_algorithm()

    def _get_default_algorithm(self) -> CompressionAlgorithm:
        """Get default compression algorithm."""
        return CompressionAlgorithm.LZ4
    
    def _compress_data(self, data: str, algorithm: CompressionAlgorithm) -> bytes:
        """Compress data using the specified algorithm."""
        data_bytes = data.encode('utf-8')
        handler = self._get_compression_handler(algorithm)
        return handler(data_bytes)

    def _get_compression_handler(self, algorithm: CompressionAlgorithm) -> Callable:
        """Get compression handler for algorithm."""
        handlers = self._get_compression_handlers()
        handler = handlers.get(algorithm)
        if not handler:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")
        return handler

    def _get_compression_handlers(self) -> Dict[CompressionAlgorithm, Callable]:
        """Get compression algorithm handlers."""
        return {
            CompressionAlgorithm.GZIP: self._compress_with_gzip,
            CompressionAlgorithm.ZLIB: self._compress_with_zlib,
            CompressionAlgorithm.LZ4: self._compress_with_lz4
        }

    def _compress_with_gzip(self, data_bytes: bytes) -> bytes:
        """Compress data using GZIP algorithm."""
        return gzip.compress(data_bytes, compresslevel=self.config.compression_level)

    def _compress_with_zlib(self, data_bytes: bytes) -> bytes:
        """Compress data using ZLIB algorithm."""
        return zlib.compress(data_bytes, level=self.config.compression_level)

    def _compress_with_lz4(self, data_bytes: bytes) -> bytes:
        """Compress data using LZ4 algorithm."""
        compression_level = min(self.config.compression_level * 3, 12)
        return lz4.frame.compress(data_bytes, compression_level=compression_level)
    
    def _decompress_data(self, compressed_data: bytes, algorithm: CompressionAlgorithm) -> str:
        """Decompress data using the specified algorithm."""
        decompression_handlers = self._get_decompression_handlers()
        handler = decompression_handlers.get(algorithm)
        if not handler:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")
        return handler(compressed_data).decode('utf-8')

    def _get_decompression_handlers(self) -> Dict[CompressionAlgorithm, Callable]:
        """Get decompression algorithm handlers."""
        return {
            CompressionAlgorithm.GZIP: gzip.decompress,
            CompressionAlgorithm.ZLIB: zlib.decompress,
            CompressionAlgorithm.LZ4: lz4.frame.decompress
        }
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        stats_components = self._get_stats_components()
        return {**stats_components, "algorithm_usage": self.stats["algorithm_usage"].copy(),
               "config": self.config.__dict__}

    def _get_stats_components(self) -> Dict[str, Any]:
        """Get combined stats components."""
        basic_stats = self._calculate_basic_compression_stats()
        byte_stats = self._calculate_byte_compression_stats()
        timing_stats = self._calculate_timing_compression_stats()
        return {**basic_stats, **byte_stats, **timing_stats}

    def _calculate_basic_compression_stats(self) -> Dict[str, Any]:
        """Calculate basic compression statistics."""
        total_messages = self.stats["total_messages"]
        compressed_messages = self.stats["compressed_messages"]
        compression_rate = compressed_messages / total_messages if total_messages > 0 else 0.0
        return {"total_messages": total_messages, "compressed_messages": compressed_messages,
               "compression_rate": compression_rate}

    def _calculate_byte_compression_stats(self) -> Dict[str, Any]:
        """Calculate byte-related compression statistics."""
        original_bytes, compressed_bytes = self._get_byte_totals()
        ratios_and_savings = self._calculate_compression_ratios(original_bytes, compressed_bytes)
        return self._build_byte_stats_result(original_bytes, compressed_bytes, ratios_and_savings)

    def _calculate_compression_ratios(self, original_bytes: int, compressed_bytes: int) -> Dict[str, Any]:
        """Calculate compression ratios and savings."""
        uncompressed_bytes = original_bytes - (self.stats["total_bytes_original"] - compressed_bytes)
        overall_compression_ratio = compressed_bytes / original_bytes if original_bytes > 0 else 1.0
        bytes_saved = original_bytes - compressed_bytes - uncompressed_bytes
        return {"uncompressed_bytes": uncompressed_bytes, "overall_compression_ratio": overall_compression_ratio, "bytes_saved": bytes_saved}

    def _build_byte_stats_result(self, original_bytes: int, compressed_bytes: int, ratios: Dict[str, Any]) -> Dict[str, Any]:
        """Build byte statistics result dictionary."""
        return {"total_bytes_original": original_bytes, "total_bytes_after_compression": compressed_bytes + ratios["uncompressed_bytes"],
               "bytes_saved": ratios["bytes_saved"], "overall_compression_ratio": ratios["overall_compression_ratio"]}

    def _get_byte_totals(self) -> Tuple[int, int]:
        """Get original and compressed byte totals."""
        return self.stats["total_bytes_original"], self.stats["total_bytes_compressed"]

    def _calculate_timing_compression_stats(self) -> Dict[str, Any]:
        """Calculate timing-related compression statistics."""
        compressed_messages = self.stats["compressed_messages"]
        avg_compression_time = (self.stats["compression_time_ms"] / compressed_messages 
                              if compressed_messages > 0 else 0.0)
        return {"average_compression_time_ms": avg_compression_time}
    
    def reset_stats(self) -> None:
        """Reset compression statistics."""
        self.stats = self._create_fresh_stats()
        logger.info("Compression statistics reset")

    def _create_fresh_stats(self) -> Dict[str, Any]:
        """Create fresh statistics dictionary."""
        return {
            "total_messages": 0, "compressed_messages": 0, "total_bytes_original": 0,
            "total_bytes_compressed": 0, "compression_time_ms": 0.0,
            "algorithm_usage": {alg.value: 0 for alg in CompressionAlgorithm}
        }
    
    def update_config(self, new_config: CompressionConfig) -> None:
        """Update compression configuration."""
        self.config = new_config
        logger.info(f"Updated compression configuration: {new_config}")
    
    def _start_compression_timer(self) -> float:
        """Start compression timing."""
        import time
        return time.time()
    
    def _serialize_and_track(self, message: Dict[str, Any]) -> Tuple[str, int]:
        """Serialize message and update tracking stats."""
        json_data = json.dumps(message, default=str)
        original_size = len(json_data.encode('utf-8'))
        self.stats["total_messages"] += 1
        self.stats["total_bytes_original"] += original_size
        return json_data, original_size
    
    def _create_uncompressed_result(self, json_data: str, original_size: int, start_time: float) -> Tuple[str, CompressionResult]:
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
    
    def _attempt_compression(self, json_data: str, original_size: int, start_time: float) -> Tuple[Union[str, bytes], CompressionResult]:
        """Attempt to compress data with fallback."""
        algorithm = self._select_algorithm(json_data)
        try:
            return self._perform_compression(json_data, original_size, algorithm, start_time)
        except Exception as e:
            return self._handle_compression_failure(e, algorithm, json_data, original_size, start_time)

    def _handle_compression_failure(self, error: Exception, algorithm: CompressionAlgorithm, 
                                  json_data: str, original_size: int, start_time: float) -> Tuple[str, CompressionResult]:
        """Handle compression failure with fallback."""
        logger.warning(f"Compression failed with {algorithm.value}: {error}")
        return self._create_uncompressed_result(json_data, original_size, start_time)
    
    def _perform_compression(self, json_data: str, original_size: int, algorithm: CompressionAlgorithm, start_time: float) -> Tuple[str, CompressionResult]:
        """Perform actual compression operation."""
        compressed_data = self._compress_data(json_data, algorithm)
        compressed_size = len(compressed_data)
        compression_ratio = compressed_size / original_size
        if compression_ratio > 0.9:
            return self._create_uncompressed_result(json_data, original_size, start_time)
        return self._create_compressed_result(json_data, original_size, compressed_data, compressed_size, algorithm, start_time)
    
    def _create_compressed_result(self, json_data: str, original_size: int, compressed_data: bytes, compressed_size: int, algorithm: CompressionAlgorithm, start_time: float) -> Tuple[str, CompressionResult]:
        """Create result for successfully compressed data."""
        compressed_message = self._create_compressed_message(compressed_data, algorithm, original_size)
        compression_time = self._calculate_compression_time(start_time)
        self._update_compression_stats(compressed_size, compression_time, algorithm)
        result = self._build_compression_result(original_size, compressed_size, algorithm, compression_time)
        return json.dumps(compressed_message), result

    def _calculate_compression_time(self, start_time: float) -> float:
        """Calculate compression time in milliseconds."""
        import time
        return (time.time() - start_time) * 1000

    def _build_compression_result(self, original_size: int, compressed_size: int, algorithm: CompressionAlgorithm, compression_time: float) -> CompressionResult:
        """Build CompressionResult object."""
        return CompressionResult(
            original_size=original_size, compressed_size=compressed_size,
            compression_ratio=compressed_size / original_size, algorithm=algorithm,
            compression_time_ms=compression_time, is_compressed=True
        )
    
    def _create_compressed_message(self, compressed_data: bytes, algorithm: CompressionAlgorithm, original_size: int) -> Dict[str, Any]:
        """Create compressed message wrapper."""
        return {
            "compressed": True, "algorithm": algorithm.value,
            "original_size": original_size,
            "data": base64.b64encode(compressed_data).decode('utf-8')
        }
    
    def _update_compression_stats(self, compressed_size: int, compression_time: float, algorithm: CompressionAlgorithm) -> None:
        """Update internal compression statistics."""
        self.stats["compressed_messages"] += 1
        self.stats["total_bytes_compressed"] += compressed_size
        self.stats["compression_time_ms"] += compression_time
        self.stats["algorithm_usage"][algorithm.value] += 1
    
    def benchmark_algorithms(self, test_data: str) -> Dict[str, Any]:
        """Benchmark different compression algorithms on test data."""
        results = {}
        test_algorithms = [CompressionAlgorithm.GZIP, CompressionAlgorithm.ZLIB, CompressionAlgorithm.LZ4]
        for algorithm in test_algorithms:
            results[algorithm.value] = self._benchmark_single_algorithm(algorithm, test_data)
        return results

    def _benchmark_single_algorithm(self, algorithm: CompressionAlgorithm, test_data: str) -> Dict[str, Any]:
        """Benchmark a single compression algorithm."""
        try:
            timing_data = self._measure_compression_performance(algorithm, test_data)
            return self._compile_benchmark_results(timing_data, test_data)
        except Exception as e:
            return {"error": str(e)}

    def _compile_benchmark_results(self, timing_data: Dict[str, Any], test_data: str) -> Dict[str, Any]:
        """Compile complete benchmark results."""
        size_data = self._calculate_compression_metrics(test_data, timing_data['compressed_data'])
        integrity_data = self._check_data_integrity(test_data, timing_data['decompressed_data'])
        total_time = timing_data['compression_time_ms'] + timing_data['decompression_time_ms']
        return {**timing_data, **size_data, **integrity_data, 'total_time_ms': total_time}

    def _measure_compression_performance(self, algorithm: CompressionAlgorithm, test_data: str) -> Dict[str, Any]:
        """Measure compression and decompression performance."""
        compression_metrics = self._measure_compression_time(algorithm, test_data)
        decompression_time, decompressed_data = self._measure_decompression_time(compression_metrics["compressed_data"], algorithm)
        return self._build_performance_result(compression_metrics["compressed_data"], decompressed_data, compression_metrics["compression_time"], decompression_time)

    def _measure_compression_time(self, algorithm: CompressionAlgorithm, test_data: str) -> Dict[str, Any]:
        """Measure compression time and return data."""
        import time
        compression_start = time.time()
        compressed_data = self._compress_data(test_data, algorithm)
        compression_time = (time.time() - compression_start) * 1000
        return {"compressed_data": compressed_data, "compression_time": compression_time}

    def _build_performance_result(self, compressed_data: bytes, decompressed_data: str, 
                                compression_time: float, decompression_time: float) -> Dict[str, Any]:
        """Build performance measurement result."""
        return {
            'compressed_data': compressed_data, 'decompressed_data': decompressed_data,
            'compression_time_ms': compression_time, 'decompression_time_ms': decompression_time
        }

    def _measure_decompression_time(self, compressed_data: bytes, algorithm: CompressionAlgorithm) -> Tuple[float, str]:
        """Measure decompression time and return data."""
        import time
        start_time = time.time()
        decompressed_data = self._decompress_data(compressed_data, algorithm)
        decompression_time = (time.time() - start_time) * 1000
        return decompression_time, decompressed_data

    def _calculate_compression_metrics(self, test_data: str, compressed_data: bytes) -> Dict[str, Any]:
        """Calculate compression size and integrity metrics."""
        original_size = len(test_data.encode('utf-8'))
        compressed_size = len(compressed_data)
        return {'original_size': original_size, 'compressed_size': compressed_size,
               'compression_ratio': compressed_size / original_size}

    def _check_data_integrity(self, original_data: str, decompressed_data: str) -> Dict[str, Any]:
        """Check data integrity after compression/decompression cycle."""
        return {'data_integrity': decompressed_data == original_data}