# Shim module for backward compatibility
from netra_backend.app.websocket_core.utils import compress, decompress
from typing import Any, Dict, Union


class WebSocketCompressor:
    """
    Stub WebSocket compressor class for backward compatibility.
    
    Currently provides no-op compression/decompression.
    Can be extended with actual compression logic when needed.
    """
    
    def __init__(self, compression_level: int = 6):
        """Initialize compressor with optional compression level."""
        self.compression_level = compression_level
        self.enabled = False  # Compression disabled by default
    
    def compress_message(self, data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """
        Compress message data.
        
        Currently returns data as-is (no compression).
        """
        return data
    
    def decompress_message(self, data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """
        Decompress message data.
        
        Currently returns data as-is (no decompression).
        """
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
