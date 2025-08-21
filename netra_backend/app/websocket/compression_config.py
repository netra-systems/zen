"""WebSocket Compression Configuration and Data Structures.

Defines compression algorithms, configuration, and result data structures
for WebSocket message compression system.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any


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


class CompressionStatsManager:
    """Manages compression statistics and metrics."""
    
    def __init__(self):
        self.stats = self._initialize_compression_stats()
    
    def _initialize_compression_stats(self) -> Dict[str, Any]:
        """Initialize compression statistics."""
        return {
            "total_messages": 0, "compressed_messages": 0, "total_bytes_original": 0,
            "total_bytes_compressed": 0, "compression_time_ms": 0.0,
            "algorithm_usage": {alg.value: 0 for alg in CompressionAlgorithm}
        }
    
    def update_message_stats(self, original_size: int) -> None:
        """Update message tracking statistics."""
        self.stats["total_messages"] += 1
        self.stats["total_bytes_original"] += original_size
    
    def update_compression_stats(self, compressed_size: int, compression_time: float, 
                               algorithm: CompressionAlgorithm) -> None:
        """Update internal compression statistics."""
        self.stats["compressed_messages"] += 1
        self.stats["total_bytes_compressed"] += compressed_size
        self.stats["compression_time_ms"] += compression_time
        self.stats["algorithm_usage"][algorithm.value] += 1
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        stats_components = self._get_stats_components()
        return {**stats_components, "algorithm_usage": self.stats["algorithm_usage"].copy()}
    
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
        return {
            "total_messages": total_messages, "compressed_messages": compressed_messages,
            "compression_rate": compression_rate
        }
    
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
        return {
            "uncompressed_bytes": uncompressed_bytes,
            "overall_compression_ratio": overall_compression_ratio, 
            "bytes_saved": bytes_saved
        }
    
    def _build_byte_stats_result(self, original_bytes: int, compressed_bytes: int, 
                               ratios: Dict[str, Any]) -> Dict[str, Any]:
        """Build byte statistics result dictionary."""
        return {
            "total_bytes_original": original_bytes,
            "total_bytes_after_compression": compressed_bytes + ratios["uncompressed_bytes"],
            "bytes_saved": ratios["bytes_saved"],
            "overall_compression_ratio": ratios["overall_compression_ratio"]
        }
    
    def _get_byte_totals(self) -> tuple[int, int]:
        """Get original and compressed byte totals."""
        return self.stats["total_bytes_original"], self.stats["total_bytes_compressed"]
    
    def _calculate_timing_compression_stats(self) -> Dict[str, Any]:
        """Calculate timing-related compression statistics."""
        compressed_messages = self.stats["compressed_messages"]
        avg_compression_time = (
            self.stats["compression_time_ms"] / compressed_messages 
            if compressed_messages > 0 else 0.0
        )
        return {"average_compression_time_ms": avg_compression_time}
    
    def reset_stats(self) -> None:
        """Reset compression statistics."""
        self.stats = self._create_fresh_stats()
    
    def _create_fresh_stats(self) -> Dict[str, Any]:
        """Create fresh statistics dictionary."""
        return {
            "total_messages": 0, "compressed_messages": 0, "total_bytes_original": 0,
            "total_bytes_compressed": 0, "compression_time_ms": 0.0,
            "algorithm_usage": {alg.value: 0 for alg in CompressionAlgorithm}
        }