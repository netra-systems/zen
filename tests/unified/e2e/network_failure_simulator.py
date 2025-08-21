"""Network Failure Simulator for E2E Testing

Utilities for simulating network failures and connection issues
for WebSocket resilience testing.
"""

import asyncio
import random
from enum import Enum
from typing import Any, Dict, Optional


class FailureType(Enum):
    """Types of network failures to simulate."""
    CONNECTION_DROP = "connection_drop"
    TIMEOUT = "timeout"
    SLOW_NETWORK = "slow_network"
    INTERMITTENT = "intermittent"


class NetworkFailureSimulator:
    """Simulator for network failure scenarios."""
    
    def __init__(self):
        """Initialize failure simulator."""
        self.active_failures: Dict[str, Any] = {}
        self.failure_probability = 0.1  # 10% chance of failure
    
    async def simulate_connection_drop(self, connection) -> Dict[str, Any]:
        """Simulate sudden connection drop."""
        if hasattr(connection, '_websocket') and connection._websocket:
            await connection._websocket.close(code=1006, reason="Simulated network failure")
        
        return {
            "failure_type": FailureType.CONNECTION_DROP.value,
            "timestamp": asyncio.get_event_loop().time(),
            "recovery_possible": True
        }
    
    async def simulate_timeout(self, delay: float = 5.0) -> Dict[str, Any]:
        """Simulate network timeout."""
        await asyncio.sleep(delay)
        return {
            "failure_type": FailureType.TIMEOUT.value,
            "delay": delay,
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def simulate_slow_network(self, min_delay: float = 0.5, 
                                  max_delay: float = 2.0) -> float:
        """Simulate slow network conditions."""
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
        return delay
    
    def should_fail(self) -> bool:
        """Determine if operation should fail based on probability."""
        return random.random() < self.failure_probability
    
    async def simulate_intermittent_failure(self, operation_func, 
                                          max_attempts: int = 3) -> Any:
        """Simulate intermittent failures for operations."""
        for attempt in range(max_attempts):
            if self.should_fail() and attempt < max_attempts - 1:
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                continue
            
            try:
                return await operation_func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(0.1 * (attempt + 1))
        
        return None