"""WebSocket Compression Algorithms Implementation.

Implements different compression algorithms with handlers for
compression and decompression operations.
"""

import gzip
import zlib
import lz4.frame
from typing import Callable, Dict

from .compression_config import CompressionAlgorithm, CompressionConfig


class CompressionAlgorithmHandler:
    """Handles compression algorithm operations."""
    
    def __init__(self, config: CompressionConfig):
        self.config = config
    
    def compress_data(self, data: str, algorithm: CompressionAlgorithm) -> bytes:
        """Compress data using the specified algorithm."""
        data_bytes = data.encode('utf-8')
        handler = self._get_compression_handler(algorithm)
        return handler(data_bytes)
    
    def decompress_data(self, compressed_data: bytes, algorithm: CompressionAlgorithm) -> str:
        """Decompress data using the specified algorithm."""
        decompression_handlers = self._get_decompression_handlers()
        handler = decompression_handlers.get(algorithm)
        if not handler:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")
        return handler(compressed_data).decode('utf-8')
    
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
    
    def _get_decompression_handlers(self) -> Dict[CompressionAlgorithm, Callable]:
        """Get decompression algorithm handlers."""
        return {
            CompressionAlgorithm.GZIP: gzip.decompress,
            CompressionAlgorithm.ZLIB: zlib.decompress,
            CompressionAlgorithm.LZ4: lz4.frame.decompress
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


class CompressionAlgorithmSelector:
    """Selects optimal compression algorithm based on configuration."""
    
    def __init__(self, config: CompressionConfig):
        self.config = config
    
    def select_algorithm(self, data: str) -> CompressionAlgorithm:
        """Select the best compression algorithm for the data."""
        if not self.config.auto_select_algorithm:
            return self.config.algorithm
        return self._get_default_algorithm()
    
    def _get_default_algorithm(self) -> CompressionAlgorithm:
        """Get default compression algorithm."""
        return CompressionAlgorithm.LZ4


class CompressionBenchmark:
    """Benchmarks compression algorithms for performance testing."""
    
    def __init__(self, algorithm_handler: CompressionAlgorithmHandler):
        self.algorithm_handler = algorithm_handler
    
    def benchmark_algorithms(self, test_data: str) -> Dict[str, any]:
        """Benchmark different compression algorithms on test data."""
        results = {}
        test_algorithms = [CompressionAlgorithm.GZIP, CompressionAlgorithm.ZLIB, CompressionAlgorithm.LZ4]
        for algorithm in test_algorithms:
            results[algorithm.value] = self._benchmark_single_algorithm(algorithm, test_data)
        return results
    
    def _benchmark_single_algorithm(self, algorithm: CompressionAlgorithm, test_data: str) -> Dict[str, any]:
        """Benchmark a single compression algorithm."""
        try:
            timing_data = self._measure_compression_performance(algorithm, test_data)
            return self._compile_benchmark_results(timing_data, test_data)
        except Exception as e:
            return {"error": str(e)}
    
    def _measure_compression_performance(self, algorithm: CompressionAlgorithm, test_data: str) -> Dict[str, any]:
        """Measure compression and decompression performance."""
        compression_metrics = self._measure_compression_time(algorithm, test_data)
        decompression_time, decompressed_data = self._measure_decompression_time(
            compression_metrics["compressed_data"], algorithm
        )
        return self._build_performance_result(
            compression_metrics["compressed_data"], decompressed_data, 
            compression_metrics["compression_time"], decompression_time
        )
    
    def _compile_benchmark_results(self, timing_data: Dict[str, any], test_data: str) -> Dict[str, any]:
        """Compile complete benchmark results."""
        size_data = self._calculate_compression_metrics(test_data, timing_data['compressed_data'])
        integrity_data = self._check_data_integrity(test_data, timing_data['decompressed_data'])
        total_time = timing_data['compression_time_ms'] + timing_data['decompression_time_ms']
        return {**timing_data, **size_data, **integrity_data, 'total_time_ms': total_time}
    
    def _measure_compression_time(self, algorithm: CompressionAlgorithm, test_data: str) -> Dict[str, any]:
        """Measure compression time and return data."""
        import time
        compression_start = time.time()
        compressed_data = self.algorithm_handler.compress_data(test_data, algorithm)
        compression_time = (time.time() - compression_start) * 1000
        return {"compressed_data": compressed_data, "compression_time": compression_time}
    
    def _measure_decompression_time(self, compressed_data: bytes, 
                                  algorithm: CompressionAlgorithm) -> tuple[float, str]:
        """Measure decompression time and return data."""
        import time
        start_time = time.time()
        decompressed_data = self.algorithm_handler.decompress_data(compressed_data, algorithm)
        decompression_time = (time.time() - start_time) * 1000
        return decompression_time, decompressed_data
    
    def _build_performance_result(self, compressed_data: bytes, decompressed_data: str, 
                                compression_time: float, decompression_time: float) -> Dict[str, any]:
        """Build performance measurement result."""
        return {
            'compressed_data': compressed_data, 'decompressed_data': decompressed_data,
            'compression_time_ms': compression_time, 'decompression_time_ms': decompression_time
        }
    
    def _calculate_compression_metrics(self, test_data: str, compressed_data: bytes) -> Dict[str, any]:
        """Calculate compression size and integrity metrics."""
        original_size = len(test_data.encode('utf-8'))
        compressed_size = len(compressed_data)
        return {
            'original_size': original_size, 'compressed_size': compressed_size,
            'compression_ratio': compressed_size / original_size
        }
    
    def _check_data_integrity(self, original_data: str, decompressed_data: str) -> Dict[str, any]:
        """Check data integrity after compression/decompression cycle."""
        return {'data_integrity': decompressed_data == original_data}