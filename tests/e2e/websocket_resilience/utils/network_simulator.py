"""
Network simulation utilities for WebSocket resilience testing.

Business Value Justification (BVJ):
- Segment: All Segments
- Business Goal: Network Resilience Testing
- Value Impact: Simulates real-world network conditions for testing
- Strategic/Revenue Impact: Validates behavior under various network conditions
"""

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from tests.e2e.websocket_resilience.fixtures.shared_websocket_fixtures import (
    NetworkCondition,
)


class NetworkSimulator:
    """Simulates various network conditions for testing."""
    
    def __init__(self, condition: NetworkCondition):
        self.condition = condition
        self.is_connected = True
        self.packets_sent = 0
        self.packets_dropped = 0
        
    async def simulate_latency(self):
        """Simulate network latency."""
        base_latency = self.condition.latency_ms / 1000.0
        jitter = random.uniform(-self.condition.jitter_ms, self.condition.jitter_ms) / 1000.0
        total_latency = max(0, base_latency + jitter)
        
        if total_latency > 0:
            await asyncio.sleep(total_latency)
    
    def should_drop_packet(self) -> bool:
        """Determine if packet should be dropped."""
        self.packets_sent += 1
        
        if random.random() < self.condition.packet_loss_rate:
            self.packets_dropped += 1
            return True
        return False
    
    async def simulate_bandwidth_limit(self, data_size: int):
        """Simulate bandwidth limitations."""
        if self.condition.bandwidth_kbps <= 0:
            return
            
        # Calculate transmission time based on bandwidth
        bits = data_size * 8
        kbps = self.condition.bandwidth_kbps
        transmission_time = bits / (kbps * 1000)
        
        if transmission_time > 0:
            await asyncio.sleep(transmission_time)
    
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
            "packets_sent": self.packets_sent,
            "packets_dropped": self.packets_dropped,
            "actual_packet_loss_rate": packet_loss_rate,
            "is_connected": self.is_connected
        }
