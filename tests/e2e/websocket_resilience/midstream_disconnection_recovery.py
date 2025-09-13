"""
Midstream disconnection recovery utilities for WebSocket resilience testing.

Business Value Justification (BVJ):
- Segment: All Segments
- Business Goal: WebSocket Resilience Testing
- Value Impact: Provides utilities for testing midstream disconnection recovery
- Strategic/Revenue Impact: Ensures WebSocket reliability during interruptions
"""

import asyncio
import hashlib
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from tests.e2e.websocket_resilience.fixtures.shared_websocket_fixtures import (
    ConnectionState,
    ResponseType,
    NetworkCondition,
)


@dataclass
class StreamBuffer:
    """Enhanced buffer for streaming response data with integrity checking."""
    buffer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    response_type: ResponseType = ResponseType.TEXT
    content: List[str] = field(default_factory=list)
    sequence_numbers: List[int] = field(default_factory=list)
    total_size: int = 0
    received_size: int = 0
    is_complete: bool = False
    checksum: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    
    def add_chunk(self, chunk: str, sequence_num: int):
        """Add chunk to buffer with sequence tracking."""
        self.content.append(chunk)
        self.sequence_numbers.append(sequence_num)
        self.received_size += len(chunk)
        
    def get_content_hash(self) -> str:
        """Calculate content hash for integrity verification."""
        content = "".join(self.content)
        return hashlib.md5(content.encode()).hexdigest()
        
    def verify_integrity(self) -> bool:
        """Verify buffer integrity."""
        if not self.checksum:
            return True
        return self.get_content_hash() == self.checksum
        
    def get_missing_sequences(self, expected_total: int) -> List[int]:
        """Get list of missing sequence numbers."""
        expected_sequences = set(range(1, expected_total + 1))
        received_sequences = set(self.sequence_numbers)
        return list(expected_sequences - received_sequences)


class NetworkSimulator:
    """Enhanced network simulator for WebSocket resilience testing."""
    
    def __init__(self):
        self.conditions: Dict[str, NetworkCondition] = {}
        self.current_condition = "stable"
        self.is_connected = True
        self.packets_sent = 0
        self.packets_dropped = 0
        
    def add_condition(self, condition: NetworkCondition):
        """Add a network condition configuration."""
        self.conditions[condition.name if hasattr(condition, 'name') else "default"] = condition
        
    def set_condition(self, condition_name: str):
        """Set current network condition."""
        if condition_name in self.conditions:
            self.current_condition = condition_name
            
    def should_drop_packet(self) -> bool:
        """Determine if packet should be dropped based on current condition."""
        if self.current_condition not in self.conditions:
            return False
            
        condition = self.conditions[self.current_condition]
        self.packets_sent += 1
        
        packet_loss_rate = getattr(condition, 'packet_loss_rate', 0.0)
        if random.random() < packet_loss_rate:
            self.packets_dropped += 1
            return True
        return False
        
    def get_latency(self) -> float:
        """Get current network latency in seconds."""
        if self.current_condition not in self.conditions:
            return 0.0
            
        condition = self.conditions[self.current_condition]
        base_latency = getattr(condition, 'latency_ms', 0) / 1000.0
        jitter = getattr(condition, 'jitter_ms', 0) / 1000.0
        
        if jitter > 0:
            jitter_offset = random.uniform(-jitter, jitter)
            return max(0, base_latency + jitter_offset)
        return base_latency
        
    def disconnect(self):
        """Simulate network disconnection."""
        self.is_connected = False
        
    def reconnect(self):
        """Simulate network reconnection."""
        self.is_connected = True
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get network simulation statistics."""
        packet_loss_rate = (self.packets_dropped / self.packets_sent) if self.packets_sent > 0 else 0
        
        return {
            "current_condition": self.current_condition,
            "is_connected": self.is_connected,
            "packets_sent": self.packets_sent,
            "packets_dropped": self.packets_dropped,
            "actual_packet_loss_rate": packet_loss_rate
        }


class StreamingResponseGenerator:
    """Generates streaming responses for testing disconnection scenarios."""
    
    @staticmethod
    async def generate_text_stream(size: int, chunk_size: int) -> AsyncGenerator[tuple, None]:
        """Generate text stream with sequence numbers."""
        sequence_num = 0
        total_generated = 0
        
        while total_generated < size:
            remaining = min(chunk_size, size - total_generated)
            chunk = f"Chunk {sequence_num}: " + "x" * (remaining - 20)
            sequence_num += 1
            total_generated += len(chunk)
            
            yield chunk, sequence_num
            
    @staticmethod
    async def generate_json_stream(schema: Dict[str, str], progressive: bool, num_objects: int) -> AsyncGenerator[tuple, None]:
        """Generate JSON stream with sequence numbers."""
        import json
        
        for i in range(num_objects):
            obj = {}
            for field, field_type in schema.items():
                if field_type == "string":
                    obj[field] = f"value_{i}"
                elif field_type == "number":
                    obj[field] = i
                else:
                    obj[field] = f"data_{i}"
                    
            chunk = json.dumps(obj)
            yield chunk, i + 1
            
    @staticmethod
    async def generate_multipart_stream(components: List[Dict[str, Any]]) -> AsyncGenerator[tuple, None]:
        """Generate multipart stream with sequence numbers."""
        boundary = f"----boundary_{uuid.uuid4().hex[:8]}"
        
        # Start boundary
        yield f"Content-Type: multipart/mixed; boundary={boundary}\r\n\r\n", 0
        
        for idx, component in enumerate(components):
            part_header = f"--{boundary}\r\nContent-Type: {component.get('content_type', 'text/plain')}\r\n\r\n"
            part_data = component.get('data', f"Part {idx} data")
            part = part_header + part_data + "\r\n"
            
            yield part, idx + 1, component.get('id', f'component_{idx}')
            
        # End boundary
        yield f"--{boundary}--\r\n", len(components) + 1
