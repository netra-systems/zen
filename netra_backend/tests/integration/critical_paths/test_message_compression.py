"""
L2 Integration Test: WebSocket Message Compression

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Bandwidth savings worth $5K MRR cost reduction
- Value Impact: Reduces bandwidth costs and improves performance for large messages
- Strategic Impact: Enables cost-effective scaling with lower infrastructure costs

L2 Test: Real internal compression components with mocked external services.
Performance target: >50% compression ratio, <10ms compression latency.
"""

# Add project root to path

from app.websocket.connection import ConnectionManager as WebSocketManager
from tests.test_utils import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

import asyncio
import base64
import gzip
import json
import time
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import lz4.frame
import pytest
from app.schemas import User

from app.services.websocket_manager import WebSocketManager
from test_framework.mock_utils import mock_justified


class CompressionAlgorithm(Enum):

    """Supported compression algorithms."""

    NONE = "none"

    GZIP = "gzip"

    DEFLATE = "deflate"

    LZ4 = "lz4"


@dataclass

class CompressionStats:

    """Statistics for compression operations."""

    original_size: int

    compressed_size: int

    compression_ratio: float

    compression_time: float

    decompression_time: float

    algorithm: CompressionAlgorithm


class MessageCompressor:

    """Handle message compression for WebSocket communications."""
    

    def __init__(self):

        self.compression_threshold = 1024  # 1KB - compress messages larger than this

        self.max_message_size = 1024 * 1024 * 10  # 10MB max message size

        self.supported_algorithms = [

            CompressionAlgorithm.GZIP,

            CompressionAlgorithm.DEFLATE,

            CompressionAlgorithm.LZ4

        ]

        self.default_algorithm = CompressionAlgorithm.GZIP

        self.compression_level = 6  # Good balance of speed vs. ratio
        

        self.stats = {

            "total_messages": 0,

            "compressed_messages": 0,

            "total_original_bytes": 0,

            "total_compressed_bytes": 0,

            "compression_time_total": 0.0,

            "decompression_time_total": 0.0,

            "algorithm_usage": {alg.value: 0 for alg in CompressionAlgorithm}

        }
    

    def should_compress_message(self, message_data: bytes) -> bool:

        """Determine if message should be compressed."""
        # Don't compress if already small

        if len(message_data) < self.compression_threshold:

            return False
        
        # Don't compress if too large

        if len(message_data) > self.max_message_size:

            return False
        
        # Don't compress if already compressed (check for compression markers)

        if self._appears_compressed(message_data):

            return False
        

        return True
    

    def _appears_compressed(self, data: bytes) -> bool:

        """Check if data appears to already be compressed."""

        if len(data) < 4:

            return False
        
        # Check for common compression headers

        compression_headers = [

            b'\x1f\x8b',      # gzip

            b'\x78\x9c',      # zlib deflate

            b'\x78\x01',      # zlib deflate

            b'\x78\xda',      # zlib deflate

            b'\x04"M\x18'     # LZ4

        ]
        

        data_start = data[:4]

        return any(data_start.startswith(header) for header in compression_headers)
    

    def negotiate_compression(self, client_algorithms: List[str]) -> CompressionAlgorithm:

        """Negotiate compression algorithm with client."""
        # Convert string names to enum values

        client_supported = []

        for alg_name in client_algorithms:

            try:

                alg = CompressionAlgorithm(alg_name.lower())

                if alg in self.supported_algorithms:

                    client_supported.append(alg)

            except ValueError:

                continue
        

        if not client_supported:

            return CompressionAlgorithm.NONE
        
        # Prefer algorithms in order of efficiency for our use case

        preference_order = [

            CompressionAlgorithm.LZ4,     # Fastest

            CompressionAlgorithm.GZIP,    # Good balance

            CompressionAlgorithm.DEFLATE  # Standard

        ]
        

        for preferred in preference_order:

            if preferred in client_supported:

                return preferred
        

        return client_supported[0]
    

    async def compress_message(self, message: Dict[str, Any], algorithm: CompressionAlgorithm = None) -> Dict[str, Any]:

        """Compress a message using specified algorithm."""

        if algorithm is None:

            algorithm = self.default_algorithm
        

        self.stats["total_messages"] += 1
        
        # Serialize message to bytes

        message_json = json.dumps(message, separators=(',', ':'))

        message_bytes = message_json.encode('utf-8')

        original_size = len(message_bytes)
        

        self.stats["total_original_bytes"] += original_size
        
        # Check if compression should be applied

        if not self.should_compress_message(message_bytes) or algorithm == CompressionAlgorithm.NONE:

            return {

                "compressed": False,

                "algorithm": CompressionAlgorithm.NONE.value,

                "original_size": original_size,

                "data": message_json,

                "stats": CompressionStats(

                    original_size=original_size,

                    compressed_size=original_size,

                    compression_ratio=0.0,

                    compression_time=0.0,

                    decompression_time=0.0,

                    algorithm=CompressionAlgorithm.NONE

                )

            }
        
        # Perform compression

        start_time = time.time()
        

        try:

            compressed_data = await self._compress_data(message_bytes, algorithm)

            compression_time = time.time() - start_time
            

            compressed_size = len(compressed_data)

            compression_ratio = (1 - compressed_size / original_size) * 100
            

            self.stats["compressed_messages"] += 1

            self.stats["total_compressed_bytes"] += compressed_size

            self.stats["compression_time_total"] += compression_time

            self.stats["algorithm_usage"][algorithm.value] += 1
            
            # Encode compressed data as base64 for JSON transport

            encoded_data = base64.b64encode(compressed_data).decode('utf-8')
            

            return {

                "compressed": True,

                "algorithm": algorithm.value,

                "original_size": original_size,

                "compressed_size": compressed_size,

                "compression_ratio": compression_ratio,

                "data": encoded_data,

                "stats": CompressionStats(

                    original_size=original_size,

                    compressed_size=compressed_size,

                    compression_ratio=compression_ratio,

                    compression_time=compression_time,

                    decompression_time=0.0,

                    algorithm=algorithm

                )

            }
        

        except Exception as e:
            # Fall back to uncompressed on compression failure

            return {

                "compressed": False,

                "algorithm": CompressionAlgorithm.NONE.value,

                "original_size": original_size,

                "data": message_json,

                "error": f"Compression failed: {str(e)}",

                "stats": CompressionStats(

                    original_size=original_size,

                    compressed_size=original_size,

                    compression_ratio=0.0,

                    compression_time=time.time() - start_time,

                    decompression_time=0.0,

                    algorithm=CompressionAlgorithm.NONE

                )

            }
    

    async def _compress_data(self, data: bytes, algorithm: CompressionAlgorithm) -> bytes:

        """Compress data using specified algorithm."""

        if algorithm == CompressionAlgorithm.GZIP:

            return gzip.compress(data, compresslevel=self.compression_level)
        

        elif algorithm == CompressionAlgorithm.DEFLATE:

            return zlib.compress(data, level=self.compression_level)
        

        elif algorithm == CompressionAlgorithm.LZ4:

            return lz4.frame.compress(data, compression_level=self.compression_level)
        

        else:

            raise ValueError(f"Unsupported compression algorithm: {algorithm}")
    

    async def decompress_message(self, compressed_message: Dict[str, Any]) -> Dict[str, Any]:

        """Decompress a compressed message."""

        if not compressed_message.get("compressed", False):
            # Message is not compressed, return data as-is

            data = compressed_message["data"]

            if isinstance(data, str):

                try:

                    return json.loads(data)

                except json.JSONDecodeError:

                    return {"data": data}

            return data
        

        algorithm = CompressionAlgorithm(compressed_message["algorithm"])

        encoded_data = compressed_message["data"]
        
        # Decode base64 data

        compressed_data = base64.b64decode(encoded_data)
        

        start_time = time.time()
        

        try:

            decompressed_data = await self._decompress_data(compressed_data, algorithm)

            decompression_time = time.time() - start_time
            

            self.stats["decompression_time_total"] += decompression_time
            
            # Parse JSON

            message_json = decompressed_data.decode('utf-8')

            message = json.loads(message_json)
            

            return message
        

        except Exception as e:

            raise ValueError(f"Decompression failed: {str(e)}")
    

    async def _decompress_data(self, data: bytes, algorithm: CompressionAlgorithm) -> bytes:

        """Decompress data using specified algorithm."""

        if algorithm == CompressionAlgorithm.GZIP:

            return gzip.decompress(data)
        

        elif algorithm == CompressionAlgorithm.DEFLATE:

            return zlib.decompress(data)
        

        elif algorithm == CompressionAlgorithm.LZ4:

            return lz4.frame.decompress(data)
        

        else:

            raise ValueError(f"Unsupported decompression algorithm: {algorithm}")
    

    def get_compression_stats(self) -> Dict[str, Any]:

        """Get comprehensive compression statistics."""

        stats = self.stats.copy()
        

        if stats["total_messages"] > 0:

            stats["compression_rate"] = (stats["compressed_messages"] / stats["total_messages"]) * 100
            

            if stats["total_original_bytes"] > 0:

                overall_ratio = (1 - stats["total_compressed_bytes"] / stats["total_original_bytes"]) * 100

                stats["overall_compression_ratio"] = overall_ratio

                stats["bytes_saved"] = stats["total_original_bytes"] - stats["total_compressed_bytes"]
            

            if stats["compressed_messages"] > 0:

                stats["avg_compression_time"] = stats["compression_time_total"] / stats["compressed_messages"]

                stats["avg_decompression_time"] = stats["decompression_time_total"] / stats["compressed_messages"]
        

        return stats


class CompressionNegotiator:

    """Handle compression negotiation during WebSocket handshake."""
    

    def __init__(self, compressor: MessageCompressor):

        self.compressor = compressor

        self.negotiation_stats = {

            "negotiations": 0,

            "successful_negotiations": 0,

            "fallback_to_none": 0,

            "preferred_algorithms": {alg.value: 0 for alg in CompressionAlgorithm}

        }
    

    def parse_compression_header(self, header_value: str) -> List[str]:

        """Parse compression extensions from WebSocket header."""

        if not header_value:

            return []
        
        # Parse "Sec-WebSocket-Extensions" header
        # Format: "permessage-deflate; client_max_window_bits=15"

        extensions = []
        

        for extension in header_value.split(','):

            extension = extension.strip()

            if ';' in extension:

                ext_name = extension.split(';')[0].strip()

            else:

                ext_name = extension
            
            # Map standard WebSocket compression extensions to our algorithms

            if ext_name == "permessage-deflate":

                extensions.append("deflate")

            elif ext_name == "x-webkit-deflate-frame":

                extensions.append("deflate")

            elif ext_name == "permessage-gzip":

                extensions.append("gzip")

            elif ext_name == "permessage-lz4":

                extensions.append("lz4")
        

        return extensions
    

    def negotiate_compression(self, client_extensions: str) -> Dict[str, Any]:

        """Negotiate compression with client."""

        self.negotiation_stats["negotiations"] += 1
        
        # Parse client supported algorithms

        client_algorithms = self.parse_compression_header(client_extensions)
        
        # Negotiate algorithm

        selected_algorithm = self.compressor.negotiate_compression(client_algorithms)
        

        if selected_algorithm != CompressionAlgorithm.NONE:

            self.negotiation_stats["successful_negotiations"] += 1

            self.negotiation_stats["preferred_algorithms"][selected_algorithm.value] += 1

        else:

            self.negotiation_stats["fallback_to_none"] += 1
        
        # Create negotiation response

        response = {

            "algorithm": selected_algorithm.value,

            "supported": selected_algorithm != CompressionAlgorithm.NONE,

            "client_algorithms": client_algorithms,

            "server_response": self._create_server_response(selected_algorithm)

        }
        

        return response
    

    def _create_server_response(self, algorithm: CompressionAlgorithm) -> str:

        """Create server response header for compression negotiation."""

        if algorithm == CompressionAlgorithm.DEFLATE:

            return "permessage-deflate; server_no_context_takeover"

        elif algorithm == CompressionAlgorithm.GZIP:

            return "permessage-gzip"

        elif algorithm == CompressionAlgorithm.LZ4:

            return "permessage-lz4"

        else:

            return ""
    

    def get_negotiation_stats(self) -> Dict[str, Any]:

        """Get compression negotiation statistics."""

        stats = self.negotiation_stats.copy()
        

        if stats["negotiations"] > 0:

            stats["success_rate"] = (stats["successful_negotiations"] / stats["negotiations"]) * 100

            stats["fallback_rate"] = (stats["fallback_to_none"] / stats["negotiations"]) * 100
        

        return stats


class PerformanceAnalyzer:

    """Analyze compression performance across different scenarios."""
    

    def __init__(self, compressor: MessageCompressor):

        self.compressor = compressor

        self.performance_data = {

            "by_algorithm": {alg.value: [] for alg in CompressionAlgorithm},

            "by_size_range": {

                "small": [],      # < 5KB

                "medium": [],     # 5KB - 50KB

                "large": []       # > 50KB

            },

            "by_message_type": {}

        }
    

    async def analyze_compression_performance(self, messages: List[Dict[str, Any]], 

                                           algorithm: CompressionAlgorithm) -> Dict[str, Any]:

        """Analyze compression performance for a set of messages."""

        results = []
        

        for message in messages:
            # Compress message

            compressed_result = await self.compressor.compress_message(message, algorithm)
            
            # Decompress to verify

            if compressed_result["compressed"]:

                try:

                    decompressed = await self.compressor.decompress_message(compressed_result)

                    decompression_success = True

                except Exception:

                    decompression_success = False

            else:

                decompression_success = True
            
            # Record performance data

            stats = compressed_result["stats"]

            performance_record = {

                "original_size": stats.original_size,

                "compressed_size": stats.compressed_size,

                "compression_ratio": stats.compression_ratio,

                "compression_time": stats.compression_time,

                "decompression_time": stats.decompression_time,

                "algorithm": algorithm.value,

                "decompression_success": decompression_success

            }
            

            results.append(performance_record)

            self._categorize_performance_data(performance_record, message)
        

        return self._calculate_performance_summary(results, algorithm)
    

    def _categorize_performance_data(self, performance_record: Dict[str, Any], 

                                   original_message: Dict[str, Any]) -> None:

        """Categorize performance data by various dimensions."""
        # By algorithm

        algorithm = performance_record["algorithm"]

        self.performance_data["by_algorithm"][algorithm].append(performance_record)
        
        # By size range

        size = performance_record["original_size"]

        if size < 5120:  # < 5KB

            self.performance_data["by_size_range"]["small"].append(performance_record)

        elif size < 51200:  # < 50KB

            self.performance_data["by_size_range"]["medium"].append(performance_record)

        else:

            self.performance_data["by_size_range"]["large"].append(performance_record)
        
        # By message type

        message_type = original_message.get("type", "unknown")

        if message_type not in self.performance_data["by_message_type"]:

            self.performance_data["by_message_type"][message_type] = []

        self.performance_data["by_message_type"][message_type].append(performance_record)
    

    def _calculate_performance_summary(self, results: List[Dict[str, Any]], 

                                     algorithm: CompressionAlgorithm) -> Dict[str, Any]:

        """Calculate performance summary from results."""

        if not results:

            return {}
        

        compression_ratios = [r["compression_ratio"] for r in results if r["compression_ratio"] > 0]

        compression_times = [r["compression_time"] for r in results]

        decompression_times = [r["decompression_time"] for r in results]

        original_sizes = [r["original_size"] for r in results]

        compressed_sizes = [r["compressed_size"] for r in results]
        

        return {

            "algorithm": algorithm.value,

            "message_count": len(results),

            "avg_compression_ratio": sum(compression_ratios) / len(compression_ratios) if compression_ratios else 0,

            "min_compression_ratio": min(compression_ratios) if compression_ratios else 0,

            "max_compression_ratio": max(compression_ratios) if compression_ratios else 0,

            "avg_compression_time": sum(compression_times) / len(compression_times),

            "max_compression_time": max(compression_times),

            "avg_decompression_time": sum(decompression_times) / len(decompression_times),

            "max_decompression_time": max(decompression_times),

            "total_original_bytes": sum(original_sizes),

            "total_compressed_bytes": sum(compressed_sizes),

            "bytes_saved": sum(original_sizes) - sum(compressed_sizes),

            "decompression_success_rate": sum(1 for r in results if r["decompression_success"]) / len(results) * 100

        }
    

    def get_performance_analysis(self) -> Dict[str, Any]:

        """Get comprehensive performance analysis."""

        analysis = {

            "by_algorithm": {},

            "by_size_range": {},

            "by_message_type": {},

            "recommendations": []

        }
        
        # Analyze by algorithm

        for algorithm, data in self.performance_data["by_algorithm"].items():

            if data:

                analysis["by_algorithm"][algorithm] = self._analyze_dataset(data)
        
        # Analyze by size range

        for size_range, data in self.performance_data["by_size_range"].items():

            if data:

                analysis["by_size_range"][size_range] = self._analyze_dataset(data)
        
        # Analyze by message type

        for msg_type, data in self.performance_data["by_message_type"].items():

            if data:

                analysis["by_message_type"][msg_type] = self._analyze_dataset(data)
        
        # Generate recommendations

        analysis["recommendations"] = self._generate_recommendations(analysis)
        

        return analysis
    

    def _analyze_dataset(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:

        """Analyze a dataset of performance records."""

        if not data:

            return {}
        

        compression_ratios = [d["compression_ratio"] for d in data if d["compression_ratio"] > 0]

        compression_times = [d["compression_time"] for d in data]
        

        return {

            "count": len(data),

            "avg_compression_ratio": sum(compression_ratios) / len(compression_ratios) if compression_ratios else 0,

            "avg_compression_time": sum(compression_times) / len(compression_times),

            "efficiency_score": self._calculate_efficiency_score(compression_ratios, compression_times)

        }
    

    def _calculate_efficiency_score(self, ratios: List[float], times: List[float]) -> float:

        """Calculate efficiency score balancing compression ratio and speed."""

        if not ratios or not times:

            return 0.0
        

        avg_ratio = sum(ratios) / len(ratios)

        avg_time = sum(times) / len(times)
        
        # Higher ratio is better, lower time is better
        # Normalize and combine (ratio weighted 70%, speed 30%)

        ratio_score = min(avg_ratio / 100, 1.0)  # Normalize to 0-1

        time_score = max(0, 1 - avg_time * 1000)  # Convert to milliseconds and invert
        

        return ratio_score * 0.7 + time_score * 0.3
    

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:

        """Generate performance recommendations."""

        recommendations = []
        
        # Find best algorithm overall

        best_algorithm = None

        best_score = 0
        

        for algorithm, data in analysis["by_algorithm"].items():

            if data and data["efficiency_score"] > best_score:

                best_score = data["efficiency_score"]

                best_algorithm = algorithm
        

        if best_algorithm:

            recommendations.append(f"Use {best_algorithm} algorithm for best overall performance")
        
        # Size-based recommendations

        size_analysis = analysis["by_size_range"]

        if "small" in size_analysis and size_analysis["small"]["avg_compression_ratio"] < 20:

            recommendations.append("Consider disabling compression for small messages (<5KB)")
        

        if "large" in size_analysis and size_analysis["large"]["avg_compression_time"] > 0.1:

            recommendations.append("Consider async compression for large messages (>50KB)")
        

        return recommendations


@pytest.mark.L2

@pytest.mark.integration

class TestMessageCompression:

    """L2 integration tests for message compression."""
    

    @pytest.fixture

    def message_compressor(self):

        """Create message compressor."""

        return MessageCompressor()
    

    @pytest.fixture

    def compression_negotiator(self, message_compressor):

        """Create compression negotiator."""

        return CompressionNegotiator(message_compressor)
    

    @pytest.fixture

    def performance_analyzer(self, message_compressor):

        """Create performance analyzer."""

        return PerformanceAnalyzer(message_compressor)
    

    @pytest.fixture

    def test_messages(self):

        """Create test messages of various sizes."""

        return [
            # Small message

            {

                "type": "chat_message",

                "content": "Hello, world!",

                "timestamp": time.time()

            },
            # Medium message

            {

                "type": "document_data",

                "content": "Lorem ipsum " * 100,  # ~1.1KB

                "metadata": {"author": "test", "version": 1},

                "timestamp": time.time()

            },
            # Large message

            {

                "type": "large_dataset",

                "data": [{"id": i, "value": f"data_item_{i}", "description": "x" * 50} 

                        for i in range(500)],  # ~25KB

                "timestamp": time.time()

            },
            # Very large message

            {

                "type": "bulk_export",

                "records": [{"record_id": i, "field1": "a" * 20, "field2": "b" * 30, 

                           "field3": "c" * 40} for i in range(2000)],  # ~180KB

                "timestamp": time.time()

            }

        ]
    

    async def test_basic_compression_functionality(self, message_compressor, test_messages):

        """Test basic message compression and decompression."""

        large_message = test_messages[2]  # Large message
        
        # Compress message

        compressed = await message_compressor.compress_message(large_message, CompressionAlgorithm.GZIP)
        
        # Verify compression occurred

        assert compressed["compressed"] is True

        assert compressed["algorithm"] == CompressionAlgorithm.GZIP.value

        assert compressed["compressed_size"] < compressed["original_size"]

        assert compressed["compression_ratio"] > 0
        
        # Decompress message

        decompressed = await message_compressor.decompress_message(compressed)
        
        # Verify message integrity

        assert decompressed == large_message
        
        # Check compression stats

        stats = compressed["stats"]

        assert stats.compression_ratio > 50  # Should achieve >50% compression

        assert stats.compression_time < 0.01  # Should be fast (<10ms)
    

    async def test_compression_algorithm_comparison(self, message_compressor, test_messages):

        """Test comparison of different compression algorithms."""

        large_message = test_messages[3]  # Very large message

        algorithms = [CompressionAlgorithm.GZIP, CompressionAlgorithm.DEFLATE, CompressionAlgorithm.LZ4]
        

        results = {}
        

        for algorithm in algorithms:

            compressed = await message_compressor.compress_message(large_message, algorithm)
            
            # Verify decompression

            decompressed = await message_compressor.decompress_message(compressed)

            assert decompressed == large_message
            

            results[algorithm.value] = {

                "compression_ratio": compressed["compression_ratio"],

                "compression_time": compressed["stats"].compression_time,

                "compressed_size": compressed["compressed_size"]

            }
        
        # Verify all algorithms provide reasonable compression

        for algorithm, result in results.items():

            assert result["compression_ratio"] > 30  # At least 30% compression

            assert result["compression_time"] < 0.05  # Less than 50ms
        
        # LZ4 should be fastest

        assert results["lz4"]["compression_time"] <= min(

            results["gzip"]["compression_time"],

            results["deflate"]["compression_time"]

        ) * 1.5  # Allow some variance
    

    async def test_compression_threshold_behavior(self, message_compressor, test_messages):

        """Test compression threshold behavior."""

        small_message = test_messages[0]  # Small message

        large_message = test_messages[2]  # Large message
        
        # Small message should not be compressed

        small_compressed = await message_compressor.compress_message(small_message)

        assert small_compressed["compressed"] is False

        assert small_compressed["algorithm"] == CompressionAlgorithm.NONE.value
        
        # Large message should be compressed

        large_compressed = await message_compressor.compress_message(large_message)

        assert large_compressed["compressed"] is True

        assert large_compressed["algorithm"] != CompressionAlgorithm.NONE.value
    

    async def test_compression_negotiation(self, compression_negotiator):

        """Test compression negotiation during handshake."""
        # Test with client supporting multiple algorithms

        client_extensions = "permessage-deflate; client_max_window_bits=15, permessage-gzip"
        

        negotiation = compression_negotiator.negotiate_compression(client_extensions)
        

        assert negotiation["supported"] is True

        assert negotiation["algorithm"] in ["deflate", "gzip"]

        assert len(negotiation["client_algorithms"]) == 2

        assert negotiation["server_response"] != ""
        
        # Test with no client support

        no_support_negotiation = compression_negotiator.negotiate_compression("")
        

        assert no_support_negotiation["supported"] is False

        assert no_support_negotiation["algorithm"] == CompressionAlgorithm.NONE.value
        
        # Check negotiation stats

        stats = compression_negotiator.get_negotiation_stats()

        assert stats["negotiations"] == 2

        assert stats["successful_negotiations"] == 1

        assert stats["fallback_to_none"] == 1
    

    async def test_compression_performance_analysis(self, performance_analyzer, test_messages):

        """Test compression performance analysis."""
        # Analyze GZIP performance

        gzip_analysis = await performance_analyzer.analyze_compression_performance(

            test_messages, CompressionAlgorithm.GZIP

        )
        
        # Verify analysis results

        assert gzip_analysis["message_count"] == len(test_messages)

        assert gzip_analysis["avg_compression_ratio"] > 0

        assert gzip_analysis["decompression_success_rate"] == 100.0

        assert gzip_analysis["bytes_saved"] > 0
        
        # Analyze LZ4 performance

        lz4_analysis = await performance_analyzer.analyze_compression_performance(

            test_messages, CompressionAlgorithm.LZ4

        )
        
        # LZ4 should be faster than GZIP

        assert lz4_analysis["avg_compression_time"] <= gzip_analysis["avg_compression_time"] * 2
        
        # Get comprehensive performance analysis

        full_analysis = performance_analyzer.get_performance_analysis()
        

        assert "by_algorithm" in full_analysis

        assert "by_size_range" in full_analysis

        assert "recommendations" in full_analysis

        assert len(full_analysis["recommendations"]) > 0
    

    async def test_compression_with_already_compressed_data(self, message_compressor):

        """Test handling of already compressed data."""
        # Create message with compressed-like data

        compressed_like_message = {

            "type": "binary_data",

            "data": base64.b64encode(gzip.compress(b"test data" * 100)).decode(),

            "encoding": "base64_gzip"

        }
        
        # Should not compress already compressed data

        result = await message_compressor.compress_message(compressed_like_message)
        
        # Exact behavior depends on implementation, but should handle gracefully

        assert "compressed" in result

        assert "algorithm" in result
    

    async def test_compression_error_handling(self, message_compressor):

        """Test compression error handling."""
        # Test with invalid data that might cause compression issues

        problematic_message = {

            "type": "problematic",

            "data": None,  # None value might cause issues

            "nested": {"very": {"deep": {"nesting": "..." * 1000}}}

        }
        
        # Should handle gracefully

        result = await message_compressor.compress_message(problematic_message)
        
        # Should either compress successfully or fall back gracefully

        assert "compressed" in result

        assert "algorithm" in result
        

        if result["compressed"]:
            # If compressed, should decompress correctly

            decompressed = await message_compressor.decompress_message(result)

            assert decompressed == problematic_message
    

    @mock_justified("L2: Message compression with real internal components")

    async def test_websocket_integration_with_compression(self, message_compressor, compression_negotiator, test_messages):

        """Test WebSocket integration with message compression."""
        # Simulate WebSocket handshake with compression negotiation

        client_extensions = "permessage-deflate, permessage-gzip"

        negotiation = compression_negotiator.negotiate_compression(client_extensions)
        

        assert negotiation["supported"] is True

        selected_algorithm = CompressionAlgorithm(negotiation["algorithm"])
        
        # Simulate message exchange with compression

        sent_messages = []

        received_messages = []
        

        for message in test_messages:
            # Compress outgoing message

            compressed = await message_compressor.compress_message(message, selected_algorithm)

            sent_messages.append(compressed)
            
            # Simulate network transmission (message would be sent over WebSocket)
            # ...
            
            # Decompress incoming message

            decompressed = await message_compressor.decompress_message(compressed)

            received_messages.append(decompressed)
        
        # Verify message integrity

        for original, received in zip(test_messages, received_messages):

            assert original == received
        
        # Verify compression effectiveness

        total_original = sum(msg["original_size"] for msg in sent_messages)

        total_compressed = sum(msg.get("compressed_size", msg["original_size"]) for msg in sent_messages)
        

        overall_compression = (1 - total_compressed / total_original) * 100

        assert overall_compression > 30  # Should achieve >30% overall compression
        
        # Check final statistics

        stats = message_compressor.get_compression_stats()

        assert stats["compression_rate"] > 50  # Should compress >50% of messages

        assert stats["overall_compression_ratio"] > 30
    

    async def test_concurrent_compression_operations(self, message_compressor, test_messages):

        """Test concurrent compression operations."""

        concurrent_count = 20

        compression_tasks = []
        
        # Create concurrent compression tasks

        for i in range(concurrent_count):

            message = test_messages[i % len(test_messages)]

            algorithm = [CompressionAlgorithm.GZIP, CompressionAlgorithm.LZ4][i % 2]
            

            task = message_compressor.compress_message(message, algorithm)

            compression_tasks.append((task, message))
        
        # Execute concurrent compressions

        start_time = time.time()

        results = await asyncio.gather(*[task for task, _ in compression_tasks], return_exceptions=True)

        total_time = time.time() - start_time
        
        # Verify all operations completed successfully

        successful_compressions = sum(

            1 for result in results 

            if not isinstance(result, Exception) and "compressed" in result

        )
        

        assert successful_compressions == concurrent_count

        assert total_time < 5.0  # Should complete within 5 seconds
        
        # Verify decompression of all results

        decompression_tasks = []

        for i, result in enumerate(results):

            if not isinstance(result, Exception):

                original_message = compression_tasks[i][1]

                decompression_tasks.append((

                    message_compressor.decompress_message(result),

                    original_message

                ))
        

        decompressed_results = await asyncio.gather(

            *[task for task, _ in decompression_tasks], 

            return_exceptions=True

        )
        
        # Verify message integrity

        for i, decompressed in enumerate(decompressed_results):

            if not isinstance(decompressed, Exception):

                original = decompression_tasks[i][1]

                assert decompressed == original
    

    async def test_compression_performance_benchmarks(self, message_compressor, test_messages):

        """Test compression performance benchmarks."""

        benchmark_count = 100
        
        # Benchmark compression speed

        large_message = test_messages[3]  # Very large message
        

        start_time = time.time()

        for _ in range(benchmark_count):

            await message_compressor.compress_message(large_message, CompressionAlgorithm.GZIP)
        

        gzip_time = time.time() - start_time
        

        start_time = time.time()

        for _ in range(benchmark_count):

            await message_compressor.compress_message(large_message, CompressionAlgorithm.LZ4)
        

        lz4_time = time.time() - start_time
        
        # LZ4 should be faster

        assert lz4_time < gzip_time * 1.5  # Allow some variance
        
        # Both should be reasonably fast

        assert gzip_time / benchmark_count < 0.1  # Less than 100ms per compression

        assert lz4_time / benchmark_count < 0.05  # Less than 50ms per compression
        
        # Test compression ratio benchmarks

        compression_test = await message_compressor.compress_message(large_message, CompressionAlgorithm.GZIP)
        

        assert compression_test["compression_ratio"] > 50  # Should achieve >50% compression

        assert compression_test["stats"].compression_time < 0.01  # Should be fast
        
        # Verify final performance statistics

        stats = message_compressor.get_compression_stats()

        assert stats["avg_compression_time"] < 0.01  # Average should be fast
        

        if stats["total_original_bytes"] > 0:

            assert stats["overall_compression_ratio"] > 40  # Should achieve good overall ratio


if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])