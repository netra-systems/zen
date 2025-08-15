"""WebSocket Message Compression System.

Implements efficient compression for large WebSocket payloads
with multiple compression algorithms and automatic threshold detection.
"""

import gzip
import zlib
import lz4.frame
import json
import base64
from typing import Dict, Any, Optional, Tuple, Union
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
        self.stats = {
            "total_messages": 0,
            "compressed_messages": 0,
            "total_bytes_original": 0,
            "total_bytes_compressed": 0,
            "compression_time_ms": 0.0,
            "algorithm_usage": {alg.value: 0 for alg in CompressionAlgorithm}
        }
    
    def compress_message(self, message: Dict[str, Any]) -> Tuple[Union[str, bytes], CompressionResult]:
        """Compress a WebSocket message if beneficial."""
        start_time = self._start_compression_timer()
        json_data, original_size = self._serialize_and_track(message)
        
        if original_size < self.config.min_size_bytes:
            return self._create_uncompressed_result(json_data, original_size, start_time)
        
        return self._attempt_compression(json_data, original_size, start_time)
    
    def decompress_message(self, compressed_data: str) -> Dict[str, Any]:
        """Decompress a WebSocket message."""
        try:
            # Parse the message
            message_data = json.loads(compressed_data)
            
            # Check if it's a compressed message
            if not isinstance(message_data, dict) or not message_data.get("compressed", False):
                return message_data
            
            # Extract compression info
            algorithm = CompressionAlgorithm(message_data["algorithm"])
            original_size = message_data["original_size"]
            compressed_bytes = base64.b64decode(message_data["data"])
            
            # Decompress the data
            decompressed_data = self._decompress_data(compressed_bytes, algorithm)
            
            # Parse and return the original message
            return json.loads(decompressed_data)
            
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            # Try to return the message as-is if decompression fails
            try:
                return json.loads(compressed_data)
            except:
                raise ValueError(f"Failed to decompress message: {e}")
    
    def _select_algorithm(self, data: str) -> CompressionAlgorithm:
        """Select the best compression algorithm for the data."""
        if not self.config.auto_select_algorithm:
            return self.config.algorithm
        
        # For now, use LZ4 for speed, but could implement auto-selection logic
        # based on data characteristics, size, etc.
        return CompressionAlgorithm.LZ4
    
    def _compress_data(self, data: str, algorithm: CompressionAlgorithm) -> bytes:
        """Compress data using the specified algorithm."""
        data_bytes = data.encode('utf-8')
        
        if algorithm == CompressionAlgorithm.GZIP:
            return gzip.compress(data_bytes, compresslevel=self.config.compression_level)
        elif algorithm == CompressionAlgorithm.ZLIB:
            return zlib.compress(data_bytes, level=self.config.compression_level)
        elif algorithm == CompressionAlgorithm.LZ4:
            # LZ4 uses different compression levels
            compression_level = min(self.config.compression_level * 3, 12)
            return lz4.frame.compress(data_bytes, compression_level=compression_level)
        else:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")
    
    def _decompress_data(self, compressed_data: bytes, algorithm: CompressionAlgorithm) -> str:
        """Decompress data using the specified algorithm."""
        if algorithm == CompressionAlgorithm.GZIP:
            decompressed_bytes = gzip.decompress(compressed_data)
        elif algorithm == CompressionAlgorithm.ZLIB:
            decompressed_bytes = zlib.decompress(compressed_data)
        elif algorithm == CompressionAlgorithm.LZ4:
            decompressed_bytes = lz4.frame.decompress(compressed_data)
        else:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")
        
        return decompressed_bytes.decode('utf-8')
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        total_messages = self.stats["total_messages"]
        compressed_messages = self.stats["compressed_messages"]
        
        compression_rate = compressed_messages / total_messages if total_messages > 0 else 0.0
        
        original_bytes = self.stats["total_bytes_original"]
        compressed_bytes = self.stats["total_bytes_compressed"]
        uncompressed_bytes = original_bytes - (self.stats["total_bytes_original"] - compressed_bytes)
        
        overall_compression_ratio = compressed_bytes / original_bytes if original_bytes > 0 else 1.0
        bytes_saved = original_bytes - compressed_bytes - uncompressed_bytes
        
        avg_compression_time = (
            self.stats["compression_time_ms"] / compressed_messages 
            if compressed_messages > 0 else 0.0
        )
        
        return {
            "total_messages": total_messages,
            "compressed_messages": compressed_messages,
            "compression_rate": compression_rate,
            "total_bytes_original": original_bytes,
            "total_bytes_after_compression": compressed_bytes + uncompressed_bytes,
            "bytes_saved": bytes_saved,
            "overall_compression_ratio": overall_compression_ratio,
            "average_compression_time_ms": avg_compression_time,
            "algorithm_usage": self.stats["algorithm_usage"].copy(),
            "config": self.config.__dict__
        }
    
    def reset_stats(self) -> None:
        """Reset compression statistics."""
        self.stats = {
            "total_messages": 0,
            "compressed_messages": 0,
            "total_bytes_original": 0,
            "total_bytes_compressed": 0,
            "compression_time_ms": 0.0,
            "algorithm_usage": {alg.value: 0 for alg in CompressionAlgorithm}
        }
        logger.info("Compression statistics reset")
    
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
        result = CompressionResult(
            original_size=original_size, compressed_size=original_size,
            compression_ratio=1.0, algorithm=CompressionAlgorithm.NONE,
            compression_time_ms=compression_time, is_compressed=False
        )
        return json_data, result
    
    def _attempt_compression(self, json_data: str, original_size: int, start_time: float) -> Tuple[Union[str, bytes], CompressionResult]:
        """Attempt to compress data with fallback."""
        algorithm = self._select_algorithm(json_data)
        try:
            return self._perform_compression(json_data, original_size, algorithm, start_time)
        except Exception as e:
            logger.warning(f"Compression failed with {algorithm.value}: {e}")
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
        import time
        compressed_message = self._create_compressed_message(compressed_data, algorithm, original_size)
        compression_time = (time.time() - start_time) * 1000
        self._update_compression_stats(compressed_size, compression_time, algorithm)
        
        result = CompressionResult(
            original_size=original_size, compressed_size=compressed_size,
            compression_ratio=compressed_size / original_size, algorithm=algorithm,
            compression_time_ms=compression_time, is_compressed=True
        )
        return json.dumps(compressed_message), result
    
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
        
        for algorithm in [CompressionAlgorithm.GZIP, CompressionAlgorithm.ZLIB, CompressionAlgorithm.LZ4]:
            try:
                import time
                start_time = time.time()
                
                compressed_data = self._compress_data(test_data, algorithm)
                compression_time = (time.time() - start_time) * 1000
                
                start_time = time.time()
                decompressed_data = self._decompress_data(compressed_data, algorithm)
                decompression_time = (time.time() - start_time) * 1000
                
                original_size = len(test_data.encode('utf-8'))
                compressed_size = len(compressed_data)
                
                results[algorithm.value] = {
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "compression_ratio": compressed_size / original_size,
                    "compression_time_ms": compression_time,
                    "decompression_time_ms": decompression_time,
                    "total_time_ms": compression_time + decompression_time,
                    "data_integrity": decompressed_data == test_data
                }
                
            except Exception as e:
                results[algorithm.value] = {
                    "error": str(e)
                }
        
        return results