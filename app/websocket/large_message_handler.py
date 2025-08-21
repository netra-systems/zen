"""
Large Message Handler for WebSocket Communications

Handles:
- Message chunking for payloads > 64KB
- Message compression (permessage-deflate, gzip, lz4)
- Binary message support
- Memory-efficient streaming
- Configurable size limits
- Progress tracking for large transfers

Business Value: Mid/Enterprise - Enables file uploads and large data transfers
worth $5K MRR feature completeness.
"""

import asyncio
import gzip
import hashlib
import json
import lz4.frame
import time
import uuid
import zlib
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Union, AsyncIterator, Callable
import base64

from app.logging_config import central_logger
from app.core.network_constants import ServicePorts

logger = central_logger.get_logger(__name__)


class CompressionAlgorithm(Enum):
    """Supported compression algorithms."""
    NONE = "none"
    GZIP = "gzip" 
    DEFLATE = "deflate"
    LZ4 = "lz4"


class MessageType(Enum):
    """Message types for large message handling."""
    SINGLE = "single"              # Normal message
    CHUNKED_START = "chunked_start"  # Start of chunked message
    CHUNKED_DATA = "chunked_data"    # Chunk data
    CHUNKED_END = "chunked_end"      # End of chunked message
    BINARY = "binary"              # Binary message
    COMPRESSED = "compressed"       # Compressed message
    UPLOAD_INIT = "upload_init"     # File upload initialization
    UPLOAD_CHUNK = "upload_chunk"   # File upload chunk
    UPLOAD_COMPLETE = "upload_complete"  # File upload completion
    UPLOAD_PROGRESS = "upload_progress"  # Upload progress update


@dataclass
class MessageLimits:
    """Configuration for message size limits."""
    max_message_size: int = 10 * 1024 * 1024  # 10MB max
    chunk_size: int = 64 * 1024               # 64KB chunks
    compression_threshold: int = 1024          # 1KB compression threshold
    max_chunks: int = 1000                     # Max chunks per message
    timeout_seconds: int = 300                 # 5 minutes timeout


@dataclass
class ChunkMetadata:
    """Metadata for message chunks."""
    chunk_id: str
    message_id: str
    chunk_index: int
    total_chunks: int
    chunk_size: int
    chunk_hash: str
    compression: CompressionAlgorithm
    timestamp: float
    is_final: bool = False


@dataclass
class MessageAssembly:
    """Tracks assembly of chunked messages."""
    message_id: str
    total_chunks: int
    received_chunks: Dict[int, bytes]
    metadata: Dict[str, Any]
    started_at: float
    last_update: float
    compression: CompressionAlgorithm
    total_size: int = 0
    is_binary: bool = False


@dataclass
class CompressionStats:
    """Statistics for compression operations."""
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_time: float
    algorithm: CompressionAlgorithm


class LargeMessageHandler:
    """Handles large WebSocket messages with chunking, compression, and binary support."""
    
    def __init__(self, limits: Optional[MessageLimits] = None):
        """Initialize large message handler."""
        self.limits = limits or MessageLimits()
        self.active_assemblies: Dict[str, MessageAssembly] = {}
        self.compression_stats: Dict[str, Any] = {
            "total_messages": 0,
            "compressed_messages": 0,
            "total_original_bytes": 0,
            "total_compressed_bytes": 0,
            "compression_time_total": 0.0,
            "algorithm_usage": {alg.value: 0 for alg in CompressionAlgorithm}
        }
        
        # Cleanup task for expired assemblies
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_started = False
    
    def _start_cleanup_task(self) -> None:
        """Start periodic cleanup of expired message assemblies."""
        if self._cleanup_task is None and not self._cleanup_started:
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
                self._cleanup_started = True
            except RuntimeError:
                # No event loop running yet, will be started later
                pass
    
    async def initialize(self) -> None:
        """Initialize async components when event loop is available."""
        if not self._cleanup_started:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            self._cleanup_started = True
    
    async def _periodic_cleanup(self) -> None:
        """Periodically clean up expired message assemblies."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._cleanup_expired_assemblies()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def _cleanup_expired_assemblies(self) -> None:
        """Clean up expired message assemblies."""
        current_time = time.time()
        expired_ids = []
        
        for message_id, assembly in self.active_assemblies.items():
            if current_time - assembly.last_update > self.limits.timeout_seconds:
                expired_ids.append(message_id)
        
        for message_id in expired_ids:
            logger.warning(f"Cleaning up expired message assembly: {message_id}")
            del self.active_assemblies[message_id]
    
    def should_compress(self, data: bytes) -> bool:
        """Determine if data should be compressed."""
        if len(data) < self.limits.compression_threshold:
            return False
        
        if len(data) > self.limits.max_message_size:
            return False
        
        # Check if data appears already compressed
        return not self._appears_compressed(data)
    
    def _appears_compressed(self, data: bytes) -> bool:
        """Check if data appears to already be compressed."""
        if len(data) < 4:
            return False
        
        # Common compression headers
        compression_headers = [
            b'\x1f\x8b',      # gzip
            b'\x78\x9c',      # zlib deflate
            b'\x78\x01',      # zlib deflate
            b'\x78\xda',      # zlib deflate
            b'\x04"M\x18'     # LZ4
        ]
        
        data_start = data[:4]
        return any(data_start.startswith(header) for header in compression_headers)
    
    def should_chunk(self, data: bytes) -> bool:
        """Determine if data should be chunked."""
        return len(data) > self.limits.chunk_size
    
    async def compress_data(self, data: bytes, algorithm: CompressionAlgorithm) -> bytes:
        """Compress data using specified algorithm."""
        if algorithm == CompressionAlgorithm.GZIP:
            return gzip.compress(data, compresslevel=6)
        elif algorithm == CompressionAlgorithm.DEFLATE:
            return zlib.compress(data, level=6)
        elif algorithm == CompressionAlgorithm.LZ4:
            return lz4.frame.compress(data, compression_level=6)
        else:
            return data
    
    async def decompress_data(self, data: bytes, algorithm: CompressionAlgorithm) -> bytes:
        """Decompress data using specified algorithm."""
        if algorithm == CompressionAlgorithm.GZIP:
            return gzip.decompress(data)
        elif algorithm == CompressionAlgorithm.DEFLATE:
            return zlib.decompress(data)
        elif algorithm == CompressionAlgorithm.LZ4:
            return lz4.frame.decompress(data)
        else:
            return data
    
    def negotiate_compression(self, client_algorithms: List[str]) -> CompressionAlgorithm:
        """Negotiate compression algorithm with client."""
        client_supported = []
        for alg_name in client_algorithms:
            try:
                alg = CompressionAlgorithm(alg_name.lower())
                client_supported.append(alg)
            except ValueError:
                continue
        
        if not client_supported:
            return CompressionAlgorithm.NONE
        
        # Prefer algorithms in order of efficiency
        preference_order = [
            CompressionAlgorithm.LZ4,     # Fastest
            CompressionAlgorithm.GZIP,    # Good balance
            CompressionAlgorithm.DEFLATE  # Standard
        ]
        
        for preferred in preference_order:
            if preferred in client_supported:
                return preferred
        
        return client_supported[0]
    
    async def prepare_message(
        self, 
        message: Union[Dict[str, Any], bytes], 
        compression: CompressionAlgorithm = CompressionAlgorithm.NONE,
        is_binary: bool = False
    ) -> List[Dict[str, Any]]:
        """Prepare message for transmission with compression and chunking."""
        
        # Convert message to bytes
        if isinstance(message, dict):
            message_bytes = json.dumps(message, separators=(',', ':')).encode('utf-8')
        else:
            message_bytes = message
            is_binary = True
        
        # Validate size
        if len(message_bytes) > self.limits.max_message_size:
            raise ValueError(f"Message size {len(message_bytes)} exceeds limit {self.limits.max_message_size}")
        
        # Apply compression if needed
        compressed_data = message_bytes
        actual_compression = CompressionAlgorithm.NONE
        
        if compression != CompressionAlgorithm.NONE and self.should_compress(message_bytes):
            start_time = time.time()
            compressed_data = await self.compress_data(message_bytes, compression)
            compression_time = time.time() - start_time
            
            # Only use compression if it provides benefit
            if len(compressed_data) < len(message_bytes) * 0.9:  # At least 10% reduction
                actual_compression = compression
                self._update_compression_stats(
                    len(message_bytes), len(compressed_data), compression_time, compression
                )
            else:
                compressed_data = message_bytes
        
        # Check if chunking is needed
        if not self.should_chunk(compressed_data):
            # Single message
            return [self._create_single_message(compressed_data, actual_compression, is_binary)]
        
        # Create chunked messages
        return await self._create_chunked_messages(compressed_data, actual_compression, is_binary)
    
    def _create_single_message(
        self, 
        data: bytes, 
        compression: CompressionAlgorithm, 
        is_binary: bool
    ) -> Dict[str, Any]:
        """Create a single message."""
        if is_binary or compression != CompressionAlgorithm.NONE:
            # Encode binary/compressed data as base64
            encoded_data = base64.b64encode(data).decode('utf-8')
            return {
                "message_type": MessageType.BINARY.value if is_binary else MessageType.COMPRESSED.value,
                "data": encoded_data,
                "compression": compression.value,
                "original_size": len(data),
                "encoding": "base64"
            }
        else:
            # Text message
            return {
                "message_type": MessageType.SINGLE.value,
                "data": data.decode('utf-8'),
                "compression": CompressionAlgorithm.NONE.value
            }
    
    async def _create_chunked_messages(
        self, 
        data: bytes, 
        compression: CompressionAlgorithm, 
        is_binary: bool
    ) -> List[Dict[str, Any]]:
        """Create chunked messages for large data."""
        message_id = str(uuid.uuid4())
        total_chunks = (len(data) + self.limits.chunk_size - 1) // self.limits.chunk_size
        
        if total_chunks > self.limits.max_chunks:
            raise ValueError(f"Message requires {total_chunks} chunks, exceeds limit {self.limits.max_chunks}")
        
        messages = []
        
        # Start message
        start_message = {
            "message_type": MessageType.CHUNKED_START.value,
            "message_id": message_id,
            "total_chunks": total_chunks,
            "total_size": len(data),
            "compression": compression.value,
            "is_binary": is_binary,
            "timestamp": time.time()
        }
        messages.append(start_message)
        
        # Chunk messages
        for i in range(0, len(data), self.limits.chunk_size):
            chunk_data = data[i:i + self.limits.chunk_size]
            chunk_index = i // self.limits.chunk_size
            chunk_hash = hashlib.md5(chunk_data).hexdigest()
            
            chunk_metadata = ChunkMetadata(
                chunk_id=str(uuid.uuid4()),
                message_id=message_id,
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                chunk_size=len(chunk_data),
                chunk_hash=chunk_hash,
                compression=compression,
                timestamp=time.time(),
                is_final=(chunk_index == total_chunks - 1)
            )
            
            chunk_message = {
                "message_type": MessageType.CHUNKED_DATA.value,
                "metadata": asdict(chunk_metadata),
                "data": base64.b64encode(chunk_data).decode('utf-8'),
                "encoding": "base64"
            }
            messages.append(chunk_message)
        
        # End message
        end_message = {
            "message_type": MessageType.CHUNKED_END.value,
            "message_id": message_id,
            "total_chunks": total_chunks,
            "timestamp": time.time()
        }
        messages.append(end_message)
        
        return messages
    
    async def process_incoming_message(self, message: Dict[str, Any]) -> Optional[Union[Dict[str, Any], bytes]]:
        """Process incoming message, handling chunking and compression."""
        message_type = MessageType(message.get("message_type", MessageType.SINGLE.value))
        
        if message_type == MessageType.SINGLE:
            return await self._process_single_message(message)
        
        elif message_type == MessageType.BINARY or message_type == MessageType.COMPRESSED:
            return await self._process_binary_compressed_message(message)
        
        elif message_type == MessageType.CHUNKED_START:
            return await self._process_chunked_start(message)
        
        elif message_type == MessageType.CHUNKED_DATA:
            return await self._process_chunked_data(message)
        
        elif message_type == MessageType.CHUNKED_END:
            return await self._process_chunked_end(message)
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return None
    
    async def _process_single_message(self, message: Dict[str, Any]) -> Union[Dict[str, Any], bytes]:
        """Process a single message."""
        if "data" in message:
            data = message["data"]
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return data
            return data
        return message
    
    async def _process_binary_compressed_message(self, message: Dict[str, Any]) -> Union[Dict[str, Any], bytes]:
        """Process binary or compressed message."""
        data = base64.b64decode(message["data"])
        compression = CompressionAlgorithm(message.get("compression", CompressionAlgorithm.NONE.value))
        
        if compression != CompressionAlgorithm.NONE:
            data = await self.decompress_data(data, compression)
        
        # If it's binary data, return as bytes
        if message.get("message_type") == MessageType.BINARY.value:
            return data
        
        # Try to parse as JSON
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return data
    
    async def _process_chunked_start(self, message: Dict[str, Any]) -> None:
        """Process chunked message start."""
        message_id = message["message_id"]
        total_chunks = message["total_chunks"]
        compression = CompressionAlgorithm(message.get("compression", CompressionAlgorithm.NONE.value))
        
        assembly = MessageAssembly(
            message_id=message_id,
            total_chunks=total_chunks,
            received_chunks={},
            metadata=message,
            started_at=time.time(),
            last_update=time.time(),
            compression=compression,
            total_size=message.get("total_size", 0),
            is_binary=message.get("is_binary", False)
        )
        
        self.active_assemblies[message_id] = assembly
        logger.debug(f"Started chunked message assembly: {message_id} ({total_chunks} chunks)")
    
    async def _process_chunked_data(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process chunked message data."""
        metadata = ChunkMetadata(**message["metadata"])
        message_id = metadata.message_id
        
        if message_id not in self.active_assemblies:
            logger.warning(f"Received chunk for unknown message: {message_id}")
            return None
        
        assembly = self.active_assemblies[message_id]
        assembly.last_update = time.time()
        
        # Decode and verify chunk
        chunk_data = base64.b64decode(message["data"])
        expected_hash = hashlib.md5(chunk_data).hexdigest()
        
        if metadata.chunk_hash != expected_hash:
            logger.error(f"Chunk corruption detected for {message_id} chunk {metadata.chunk_index}")
            return None
        
        # Store chunk
        assembly.received_chunks[metadata.chunk_index] = chunk_data
        
        # Return progress update
        progress = {
            "message_type": MessageType.UPLOAD_PROGRESS.value,
            "message_id": message_id,
            "chunks_received": len(assembly.received_chunks),
            "total_chunks": assembly.total_chunks,
            "progress_percent": (len(assembly.received_chunks) / assembly.total_chunks) * 100,
            "timestamp": time.time()
        }
        
        return progress
    
    async def _process_chunked_end(self, message: Dict[str, Any]) -> Optional[Union[Dict[str, Any], bytes]]:
        """Process chunked message end and assemble final message."""
        message_id = message["message_id"]
        
        if message_id not in self.active_assemblies:
            logger.warning(f"Received end for unknown message: {message_id}")
            return None
        
        assembly = self.active_assemblies[message_id]
        
        # Check if all chunks received
        if len(assembly.received_chunks) != assembly.total_chunks:
            missing_chunks = set(range(assembly.total_chunks)) - set(assembly.received_chunks.keys())
            logger.error(f"Missing chunks for message {message_id}: {missing_chunks}")
            return None
        
        # Assemble message
        try:
            assembled_data = b''.join(
                assembly.received_chunks[i] for i in range(assembly.total_chunks)
            )
            
            # Decompress if needed
            if assembly.compression != CompressionAlgorithm.NONE:
                assembled_data = await self.decompress_data(assembled_data, assembly.compression)
            
            # Clean up assembly
            del self.active_assemblies[message_id]
            
            logger.info(f"Successfully assembled message: {message_id} ({len(assembled_data)} bytes)")
            
            # Return assembled data
            if assembly.is_binary:
                return assembled_data
            else:
                try:
                    return json.loads(assembled_data.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return assembled_data
                    
        except Exception as e:
            logger.error(f"Failed to assemble message {message_id}: {e}")
            del self.active_assemblies[message_id]
            return None
    
    def _update_compression_stats(
        self, 
        original_size: int, 
        compressed_size: int, 
        compression_time: float, 
        algorithm: CompressionAlgorithm
    ) -> None:
        """Update compression statistics."""
        self.compression_stats["total_messages"] += 1
        self.compression_stats["compressed_messages"] += 1
        self.compression_stats["total_original_bytes"] += original_size
        self.compression_stats["total_compressed_bytes"] += compressed_size
        self.compression_stats["compression_time_total"] += compression_time
        self.compression_stats["algorithm_usage"][algorithm.value] += 1
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        stats = self.compression_stats.copy()
        
        if stats["total_messages"] > 0:
            stats["compression_rate"] = (stats["compressed_messages"] / stats["total_messages"]) * 100
            
            if stats["total_original_bytes"] > 0:
                overall_ratio = (1 - stats["total_compressed_bytes"] / stats["total_original_bytes"]) * 100
                stats["overall_compression_ratio"] = overall_ratio
                stats["bytes_saved"] = stats["total_original_bytes"] - stats["total_compressed_bytes"]
            
            if stats["compressed_messages"] > 0:
                stats["avg_compression_time"] = stats["compression_time_total"] / stats["compressed_messages"]
        
        return stats
    
    def get_assembly_stats(self) -> Dict[str, Any]:
        """Get message assembly statistics."""
        return {
            "active_assemblies": len(self.active_assemblies),
            "assemblies_by_age": {
                assembly.message_id: time.time() - assembly.started_at
                for assembly in self.active_assemblies.values()
            }
        }
    
    async def shutdown(self) -> None:
        """Shutdown large message handler."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.active_assemblies.clear()
        logger.info("Large message handler shutdown complete")


# Global instance
_large_message_handler: Optional[LargeMessageHandler] = None

def get_large_message_handler() -> LargeMessageHandler:
    """Get global large message handler instance."""
    global _large_message_handler
    if _large_message_handler is None:
        _large_message_handler = LargeMessageHandler()
    return _large_message_handler