"""Network Failure Simulator for E2E Tests

Simulates various network failure scenarios for resilience testing.
"""

import asyncio
import random
from typing import Optional, Dict, Any
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class NetworkFailureSimulator:
    """Simulates network failures for testing resilience."""
    
    def __init__(self):
        self.failure_active = False
        self.failure_type = None
        self.failure_probability = 0.0
        
    async def simulate_network_outage(self, duration: float = 1.0):
        """Simulate a complete network outage."""
        self.failure_active = True
        self.failure_type = "outage"
        await asyncio.sleep(duration)
        self.failure_active = False
        self.failure_type = None
        
    async def simulate_packet_loss(self, probability: float = 0.5):
        """Simulate packet loss with given probability."""
        self.failure_active = True
        self.failure_type = "packet_loss"
        self.failure_probability = probability
        
    async def simulate_latency(self, min_delay: float = 0.1, max_delay: float = 1.0):
        """Simulate network latency."""
        self.failure_active = True
        self.failure_type = "latency"
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
        
    def reset(self):
        """Reset all failure simulations."""
        self.failure_active = False
        self.failure_type = None
        self.failure_probability = 0.0
        
    def should_drop_packet(self) -> bool:
        """Determine if a packet should be dropped."""
        if self.failure_type == "packet_loss":
            return random.random() < self.failure_probability
        return self.failure_type == "outage"
