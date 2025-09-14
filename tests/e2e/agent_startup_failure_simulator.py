"""Agent Startup Failure Simulator - Supporting Module

Failure simulation utilities for agent startup E2E tests.
Simulates database failures, state corruption, and network issues.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Ensure agent resilience under failure conditions
- Value Impact: Validates system recovery and fault tolerance
- Revenue Impact: Prevents revenue loss through improved system reliability

Architecture:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Focused on failure scenario simulation
- Comprehensive coverage of failure modes
"""

import asyncio
import logging
import uuid
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class FailureSimulator:
    """Simulates various failure scenarios for testing."""
    
    def __init__(self):
        self.active_failures: List[str] = []
        self.corruption_handlers: Dict[str, Callable] = {}
        self.failure_history: List[Dict[str, str]] = []
        self.simulation_enabled = True
        
    async def simulate_database_failure(self, duration: int = 5) -> str:
        """Simulate database connectivity failure."""
        failure_id = f"db_failure_{uuid.uuid4().hex[:8]}"
        self.active_failures.append(failure_id)
        self._log_failure_start("database", failure_id, duration)
        
        await asyncio.sleep(duration)
        
        self.active_failures.remove(failure_id)
        self._log_failure_end("database", failure_id)
        return failure_id
        
    async def simulate_network_partition(self, duration: int = 3) -> str:
        """Simulate network partition between services."""
        partition_id = f"partition_{uuid.uuid4().hex[:8]}"
        self.active_failures.append(partition_id)
        self._log_failure_start("network_partition", partition_id, duration)
        
        await asyncio.sleep(duration)
        
        self.active_failures.remove(partition_id)
        self._log_failure_end("network_partition", partition_id)
        return partition_id
        
    async def simulate_memory_exhaustion(self, duration: int = 2) -> str:
        """Simulate memory exhaustion scenario."""
        memory_failure_id = f"memory_{uuid.uuid4().hex[:8]}"
        self.active_failures.append(memory_failure_id)
        self._log_failure_start("memory_exhaustion", memory_failure_id, duration)
        
        await asyncio.sleep(duration)
        
        self.active_failures.remove(memory_failure_id)
        self._log_failure_end("memory_exhaustion", memory_failure_id)
        return memory_failure_id
        
    async def simulate_service_unavailable(self, service_name: str, duration: int = 4) -> str:
        """Simulate specific service being unavailable."""
        unavailable_id = f"{service_name}_unavailable_{uuid.uuid4().hex[:8]}"
        self.active_failures.append(unavailable_id)
        self._log_failure_start(f"{service_name}_unavailable", unavailable_id, duration)
        
        await asyncio.sleep(duration)
        
        self.active_failures.remove(unavailable_id)
        self._log_failure_end(f"{service_name}_unavailable", unavailable_id)
        return unavailable_id
        
    async def corrupt_agent_state(self, corruption_type: str) -> str:
        """Corrupt agent state to test recovery."""
        corruption_id = f"corrupt_{corruption_type}_{uuid.uuid4().hex[:8]}"
        corruption_actions = {
            "memory": self._corrupt_memory_state,
            "config": self._corrupt_config_state,
            "connections": self._corrupt_connection_state,
            "cache": self._corrupt_cache_state
        }
        
        if corruption_type in corruption_actions:
            await corruption_actions[corruption_type](corruption_id)
            
        return corruption_id
        
    async def simulate_cascading_failure(self, initial_service: str, duration: int = 6) -> List[str]:
        """Simulate cascading failure across services."""
        cascade_failures = []
        services = ["auth", "backend", "database"]
        
        # Start with initial service failure
        initial_failure = await self.simulate_service_unavailable(initial_service, duration)
        cascade_failures.append(initial_failure)
        
        # Simulate cascade effect
        for service in services:
            if service != initial_service:
                cascade_id = await self.simulate_service_unavailable(service, duration // 2)
                cascade_failures.append(cascade_id)
                await asyncio.sleep(1)  # Stagger cascade
                
        return cascade_failures
        
    def is_failure_active(self, failure_id: str) -> bool:
        """Check if specific failure is currently active."""
        return failure_id in self.active_failures
        
    def get_active_failures(self) -> List[str]:
        """Get list of currently active failures."""
        return self.active_failures.copy()
        
    def get_failure_history(self) -> List[Dict[str, str]]:
        """Get history of all simulated failures."""
        return self.failure_history.copy()
        
    def clear_failure_history(self) -> None:
        """Clear failure history records."""
        self.failure_history.clear()
        
    def enable_simulation(self) -> None:
        """Enable failure simulation."""
        self.simulation_enabled = True
        
    def disable_simulation(self) -> None:
        """Disable failure simulation."""
        self.simulation_enabled = False
        
    async def _corrupt_memory_state(self, corruption_id: str) -> None:
        """Simulate memory state corruption."""
        logger.info(f"Simulating memory state corruption: {corruption_id}")
        self.active_failures.append(corruption_id)
        
    async def _corrupt_config_state(self, corruption_id: str) -> None:
        """Simulate configuration corruption."""
        logger.info(f"Simulating config state corruption: {corruption_id}")
        self.active_failures.append(corruption_id)
        
    async def _corrupt_connection_state(self, corruption_id: str) -> None:
        """Simulate connection state corruption."""
        logger.info(f"Simulating connection state corruption: {corruption_id}")
        self.active_failures.append(corruption_id)
        
    async def _corrupt_cache_state(self, corruption_id: str) -> None:
        """Simulate cache corruption."""
        logger.info(f"Simulating cache state corruption: {corruption_id}")
        self.active_failures.append(corruption_id)
        
    def _log_failure_start(self, failure_type: str, failure_id: str, duration: int) -> None:
        """Log failure simulation start."""
        logger.info(f"Starting {failure_type} failure: {failure_id} for {duration}s")
        self.failure_history.append({
            "type": failure_type,
            "id": failure_id,
            "status": "started",
            "duration": str(duration)
        })
        
    def _log_failure_end(self, failure_type: str, failure_id: str) -> None:
        """Log failure simulation end."""
        logger.info(f"Ended {failure_type} failure: {failure_id}")
        self.failure_history.append({
            "type": failure_type,
            "id": failure_id,
            "status": "ended"
        })
