"""WebSocket heartbeat configuration and data structures.

Contains configuration classes and data structures for heartbeat functionality.
"""

from dataclasses import dataclass


@dataclass
class HeartbeatConfig:
    """Configuration for heartbeat functionality."""
    interval_seconds: int = 30  # How often to send pings
    timeout_seconds: int = 60   # How long to wait for pong before considering connection dead
    max_missed_heartbeats: int = 3  # Max consecutive missed heartbeats before disconnection