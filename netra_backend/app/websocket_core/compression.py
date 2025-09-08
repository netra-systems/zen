"""WebSocket Compression Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Bandwidth optimization and cost reduction
- Value Impact: Reduces data transfer costs and improves performance for users with limited bandwidth
- Strategic Impact: Enables real-time chat for users on mobile networks and reduces infrastructure costs

Implements message compression to optimize data transfer for cost-effective real-time communication.
"""

import asyncio
import gzip
import json
import time
import zlib
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType

logger = central_logger.get_logger(__name__)


class UnsupportedCompressionError(Exception):
    """Raised when an unsupported compression algorithm is requested."""
    pass


class CompressionConfig(BaseModel):
    """Configuration for WebSocket compression."""
    compression_enabled: bool = True
    compression_threshold_bytes: int = 100
    compression_level: int = 6
    supported_algorithms: List[str] = Field(default_factory=lambda: ['gzip', 'deflate'])
    max_uncompressed_size_mb: int = 10
    preferred_algorithm: str = 'gzip'
    enable_integrity_checks: bool = True
    
    def model_post_init(self, __context: Any) -> None:
        """Post-init validation."""
        if self.preferred_algorithm not in self.supported_algorithms:
            self.preferred_algorithm = self.supported_algorithms[0] if self.supported_algorithms else 'gzip'


class CompressionResult(BaseModel):
    """Result of a compression operation."""
    was_compressed: bool
    original_size: int
    compressed_size: int
    compression_algorithm: Optional[str] = None
    compression_ratio: float = 1.0
    compressed_data: Optional[bytes] = None
    integrity_hash: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_ms: float = 0.0
    
    def model_post_init(self, __context: Any) -> None:
        """Calculate compression ratio."""
        if self.original_size > 0:
            self.compression_ratio = self.compressed_size / self.original_size


class CompressionStats(BaseModel):
    """Statistics for compression operations."""
    total_messages_processed: int = 0
    messages_compressed: int = 0
    messages_skipped: int = 0
    messages_rejected_size: int = 0
    total_original_bytes: int = 0
    total_compressed_bytes: int = 0
    total_bytes_saved: int = 0
    average_compression_ratio: float = 1.0
    bandwidth_savings_percent: float = 0.0
    processing_time_ms: float = 0.0
    
    def update_stats(self) -> None:
        """Update calculated statistics."""
        if self.total_original_bytes > 0:
            self.total_bytes_saved = max(0, self.total_original_bytes - self.total_compressed_bytes)
            self.average_compression_ratio = self.total_compressed_bytes / self.total_original_bytes
            self.bandwidth_savings_percent = (self.total_bytes_saved / self.total_original_bytes) * 100


class PerformanceReport(BaseModel):
    """Performance report for compression operations."""
    total_messages_processed: int
    compression_rate_percent: float
    total_bandwidth_saved_bytes: int
    average_compression_ratio: float
    compression_efficiency_rating: str
    estimated_cost_savings: Dict[str, float]
    
    def model_post_init(self, __context: Any) -> None:
        """Calculate efficiency rating and cost savings."""
        # Determine efficiency rating based on compression ratio
        if self.average_compression_ratio <= 0.5:
            self.compression_efficiency_rating = 'excellent'
        elif self.average_compression_ratio <= 0.7:
            self.compression_efficiency_rating = 'good'
        elif self.average_compression_ratio <= 0.9:
            self.compression_efficiency_rating = 'fair'
        else:
            self.compression_efficiency_rating = 'poor'
        
        # Calculate estimated cost savings (simplified model)
        # Assume $0.10 per GB of data transfer
        gb_saved = self.total_bandwidth_saved_bytes / (1024 * 1024 * 1024)
        monthly_savings = gb_saved * 0.10 * 30  # 30 days
        self.estimated_cost_savings = {
            'monthly_savings_usd': round(monthly_savings, 2)
        }


class WebSocketCompressionHandler:
    """Handles WebSocket message compression and decompression."""
    
    def __init__(self, config: CompressionConfig):
        """Initialize compression handler with configuration."""
        self.config = config
        self.stats = CompressionStats()
        self._lock = asyncio.Lock()
    
    @property
    def compression_enabled(self) -> bool:
        """Check if compression is enabled."""
        return self.config.compression_enabled
    
    async def compress_message(self, message: WebSocketMessage) -> CompressionResult:
        """Compress a WebSocket message if it meets criteria."""
        start_time = time.time()
        
        async with self._lock:
            try:
                # Convert message to JSON for size calculation
                message_json = json.dumps(message.model_dump())
                original_data = message_json.encode('utf-8')
                original_size = len(original_data)
                
                # Update stats
                self.stats.total_messages_processed += 1
                self.stats.total_original_bytes += original_size
                
                # Check size limits - do this BEFORE updating other stats
                max_size_bytes = self.config.max_uncompressed_size_mb * 1024 * 1024
                if original_size > max_size_bytes:
                    # Update stats for rejection but don't update other counters
                    self.stats.messages_rejected_size += 1
                    raise ValueError(f"Message size {original_size} bytes exceeds maximum size {max_size_bytes} bytes")
                
                # Check if compression should be applied
                if (not self.config.compression_enabled or 
                    original_size <= self.config.compression_threshold_bytes):
                    self.stats.messages_skipped += 1
                    processing_time = (time.time() - start_time) * 1000
                    return CompressionResult(
                        was_compressed=False,
                        original_size=original_size,
                        compressed_size=original_size,
                        compression_ratio=1.0,
                        compressed_data=original_data,
                        processing_time_ms=processing_time
                    )
                
                # Perform compression
                algorithm = self.config.preferred_algorithm
                if algorithm not in self.config.supported_algorithms:
                    raise UnsupportedCompressionError(f"Algorithm '{algorithm}' not supported")
                
                compressed_data = await self._compress_data(original_data, algorithm)
                compressed_size = len(compressed_data)
                
                # Calculate integrity hash if enabled
                integrity_hash = None
                if self.config.enable_integrity_checks:
                    integrity_hash = hashlib.sha256(original_data).hexdigest()
                
                # Update stats
                self.stats.messages_compressed += 1
                self.stats.total_compressed_bytes += compressed_size
                self.stats.update_stats()  # Recalculate derived stats
                
                processing_time = (time.time() - start_time) * 1000
                self.stats.processing_time_ms += processing_time
                
                return CompressionResult(
                    was_compressed=True,
                    original_size=original_size,
                    compressed_size=compressed_size,
                    compression_algorithm=algorithm,
                    compressed_data=compressed_data,
                    integrity_hash=integrity_hash,
                    processing_time_ms=processing_time
                )
                
            except ValueError as e:
                # Size limit violations should be re-raised, not handled as compression errors
                if "exceeds maximum size" in str(e):
                    raise  # Re-raise size limit violations
                else:
                    # Handle other ValueError as compression errors
                    logger.warning(f"Compression failed with ValueError, using uncompressed data: {e}")
                    processing_time = (time.time() - start_time) * 1000
                    return CompressionResult(
                        was_compressed=False,
                        original_size=len(message_json.encode('utf-8')),
                        compressed_size=len(message_json.encode('utf-8')),
                        compression_ratio=1.0,
                        error_message=f"Compression failed: {str(e)}",
                        processing_time_ms=processing_time
                    )
            except Exception as e:
                # Handle other compression errors gracefully - fallback to uncompressed
                logger.warning(f"Compression failed, using uncompressed data: {e}")
                processing_time = (time.time() - start_time) * 1000
                
                return CompressionResult(
                    was_compressed=False,
                    original_size=len(message_json.encode('utf-8')),
                    compressed_size=len(message_json.encode('utf-8')),
                    compression_ratio=1.0,
                    error_message=f"Compression failed: {str(e)}",
                    processing_time_ms=processing_time
                )
    
    async def decompress_message(self, compressed_data: bytes, algorithm: str, 
                               expected_hash: Optional[str] = None) -> WebSocketMessage:
        """Decompress compressed data back to WebSocket message."""
        try:
            # Decompress the data
            decompressed_data = await self._decompress_data(compressed_data, algorithm)
            
            # Verify integrity if hash provided
            if expected_hash and self.config.enable_integrity_checks:
                actual_hash = hashlib.sha256(decompressed_data).hexdigest()
                if actual_hash != expected_hash:
                    raise ValueError(f"Integrity check failed: expected {expected_hash}, got {actual_hash}")
            
            # Parse back to WebSocket message
            message_data = json.loads(decompressed_data.decode('utf-8'))
            
            # Create WebSocketMessage from parsed data
            return WebSocketMessage(
                type=MessageType(message_data['type']),
                payload=message_data['payload'],
                timestamp=message_data.get('timestamp'),
                message_id=message_data.get('message_id'),
                user_id=message_data.get('user_id'),
                thread_id=message_data.get('thread_id')
            )
            
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            raise ValueError(f"Failed to decompress message: {str(e)}")
    
    async def _compress_data(self, data: bytes, algorithm: str) -> bytes:
        """Compress data using specified algorithm."""
        try:
            if algorithm == 'gzip':
                return gzip.compress(data, compresslevel=self.config.compression_level)
            elif algorithm == 'deflate':
                return zlib.compress(data, level=self.config.compression_level)
            else:
                raise UnsupportedCompressionError(f"Unsupported compression algorithm: {algorithm}")
        except Exception as e:
            raise Exception(f"Compression failed with {algorithm}: {str(e)}")
    
    async def _decompress_data(self, data: bytes, algorithm: str) -> bytes:
        """Decompress data using specified algorithm."""
        try:
            if algorithm == 'gzip':
                return gzip.decompress(data)
            elif algorithm == 'deflate':
                return zlib.decompress(data)
            else:
                raise UnsupportedCompressionError(f"Unsupported decompression algorithm: {algorithm}")
        except Exception as e:
            raise Exception(f"Decompression failed with {algorithm}: {str(e)}")
    
    async def generate_performance_report(self) -> PerformanceReport:
        """Generate comprehensive performance report."""
        async with self._lock:
            total_messages = self.stats.total_messages_processed
            if total_messages == 0:
                compression_rate = 0.0
            else:
                compression_rate = (self.stats.messages_compressed / total_messages) * 100
            
            # Update stats before generating report
            self.stats.update_stats()
            
            return PerformanceReport(
                total_messages_processed=total_messages,
                compression_rate_percent=compression_rate,
                total_bandwidth_saved_bytes=self.stats.total_bytes_saved,
                average_compression_ratio=self.stats.average_compression_ratio,
                compression_efficiency_rating='good',  # Will be calculated in model_post_init
                estimated_cost_savings={'monthly_savings_usd': 0.0}  # Will be calculated in model_post_init
            )


# Backward compatibility
class WebSocketCompressor:
    """Legacy WebSocket compressor class for backward compatibility."""
    
    def __init__(self, compression_level: int = 6):
        """Initialize compressor with optional compression level."""
        self.compression_level = compression_level
        self.enabled = False  # Compression disabled by default
    
    def compress_message(self, data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """Compress message data. Currently returns data as-is (no compression)."""
        return data
    
    def decompress_message(self, data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """Decompress message data. Currently returns data as-is (no decompression)."""
        return data
    
    def enable_compression(self) -> None:
        """Enable compression (currently no-op)."""
        self.enabled = True
    
    def disable_compression(self) -> None:
        """Disable compression."""
        self.enabled = False
    
    def is_compression_enabled(self) -> bool:
        """Check if compression is enabled."""
        return self.enabled
    
    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        return {
            "compression_enabled": self.enabled,
            "compression_level": self.compression_level,
            "messages_compressed": 0,
            "messages_decompressed": 0,
            "compression_ratio": 1.0,
            "total_bytes_saved": 0
        }
