"""

Shared fixtures for WebSocket resilience E2E tests.



Business Value Justification (BVJ):

- Segment: All Segments

- Business Goal: WebSocket Infrastructure

- Value Impact: Shared test infrastructure for WebSocket resilience testing

- Strategic/Revenue Impact: Enables comprehensive WebSocket reliability validation

"""



import asyncio

import json

import time

import uuid

from dataclasses import dataclass, field

from datetime import datetime, timezone

from enum import Enum

from typing import Any, Dict, List, Optional



import pytest

from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler

from netra_backend.app.db.database_manager import DatabaseManager

from netra_backend.app.clients.auth_client_core import AuthServiceClient

from shared.isolated_environment import get_env





class ConnectionState(Enum):

    """WebSocket connection states for testing."""

    DISCONNECTED = "disconnected"

    CONNECTING = "connecting"

    CONNECTED = "connected"

    STREAMING = "streaming"

    INTERRUPTED = "interrupted"

    RECOVERING = "recovering"

    FAILED = "failed"



class ResponseType(Enum):

    """Types of streaming responses for testing."""

    TEXT = "text"

    JSON = "json"

    MULTIPART = "multipart"

    BINARY = "binary"



@dataclass

class StreamBuffer:

    """Buffer for streaming response data."""

    data: List[str] = field(default_factory=list)

    total_size: int = 0

    chunks_received: int = 0

    last_chunk_time: Optional[datetime] = None

    checksum: Optional[str] = None

    

    def add_chunk(self, chunk: str):

        """Add chunk to buffer."""

        self.data.append(chunk)

        self.total_size += len(chunk)

        self.chunks_received += 1

        self.last_chunk_time = datetime.now(timezone.utc)

        

    def get_full_data(self) -> str:

        """Get complete buffered data."""

        return "".join(self.data)

        

    def calculate_checksum(self) -> str:

        """Calculate checksum of buffered data."""

        import hashlib

        data = self.get_full_data()

        return hashlib.md5(data.encode()).hexdigest()



@dataclass

class NetworkCondition:

    """Network condition simulation parameters."""

    name: str = "default"

    packet_loss_rate: float = 0.0

    latency_ms: int = 50

    bandwidth_kbps: int = 1000

    jitter_ms: int = 10

    

    def __init__(self, name: str = "default", packet_loss_rate: float = 0.0, 

                 latency_ms: int = 50, bandwidth_kbps: int = 1000, jitter_ms: int = 10):

        self.name = name

        self.packet_loss_rate = packet_loss_rate

        self.latency_ms = latency_ms

        self.bandwidth_kbps = bandwidth_kbps

        self.jitter_ms = jitter_ms



@pytest.fixture

def network_condition():

    """Create network condition configuration."""

    return NetworkCondition()



@pytest.fixture

def stream_buffer():

    """Create stream buffer for testing."""

    return StreamBuffer()



@pytest.fixture

def test_user_id():

    """Generate test user ID."""

    return f"test_user_{uuid.uuid4().hex[:8]}"



@pytest.fixture

def response_configs():

    """Create response configuration for testing."""

    return {

        "text_response": {

            "type": ResponseType.TEXT,

            "size": 1024,

            "chunk_size": 64,

            "delay_between_chunks": 0.1

        },

        "json_response": {

            "type": ResponseType.JSON,

            "size": 2048,

            "chunk_size": 128,

            "delay_between_chunks": 0.05

        },

        "large_response": {

            "type": ResponseType.TEXT,

            "size": 10240,

            "chunk_size": 256,

            "delay_between_chunks": 0.02

        }

    }

