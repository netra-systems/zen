import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent

# Import existing fixtures
from tests.e2e.integration.fixtures.error_propagation_fixtures import ErrorPropagationTester

# Import from error propagation module
from tests.e2e.helpers.resilience.error_propagation import *

# Enhanced ErrorPropagationTester for e2e tests
import asyncio
import time
from typing import Dict, Any


class EnhancedErrorPropagationTester(ErrorPropagationTester):
    """Enhanced ErrorPropagationTester with additional e2e test methods."""
    
    def __init__(self):
        super().__init__()
        self.circuit_breaker_states = {}
        self.failure_counts = {}
        
    async def call_failing_service(self, service_name: str) -> Any:
        """Simulate calling a service that can fail."""
        # Track failure count for circuit breaker logic
        if service_name not in self.failure_counts:
            self.failure_counts[service_name] = 0
            
        self.failure_counts[service_name] += 1
        
        # After 5 failures, trip circuit breaker
        if self.failure_counts[service_name] >= 5:
            self.circuit_breaker_states[service_name] = "OPEN"
            
        # If circuit breaker is open, fail fast
        if self.circuit_breaker_states.get(service_name) == "OPEN":
            raise Exception("Circuit breaker is open")
            
        # Otherwise, simulate service failure
        raise Exception(f"Service {service_name} is failing")
    
    async def get_circuit_state(self, service_name: str) -> str:
        """Get circuit breaker state for service."""
        return self.circuit_breaker_states.get(service_name, "CLOSED")
    
    async def call_with_exponential_backoff(self, service_name: str) -> Dict[str, Any]:
        """Simulate calling service with exponential backoff retry."""
        retry_count = 0
        base_delay = 0.1
        
        while retry_count < 3:
            try:
                # Simulate the patched service call behavior
                await asyncio.sleep(base_delay * (2 ** retry_count))
                retry_count += 1
                
                # On third retry, succeed
                if retry_count >= 3:
                    return {"status": "success"}
                    
                raise Exception("Service still failing")
                
            except Exception as e:
                if retry_count >= 3:
                    raise
                continue
    
    async def call_cross_service_operation(self, operation: str) -> Any:
        """Simulate cross-service operation that can propagate errors."""
        # This will be patched in tests to raise exceptions
        await asyncio.sleep(0.1)
        return {"status": "success", "operation": operation}


# Use the enhanced version for all imports
ErrorPropagationTester = EnhancedErrorPropagationTester

# Mock service call function for testing
async def call_service_endpoint(service_name: str, endpoint: str = None) -> Dict[str, Any]:
    """Mock service endpoint call."""
    await asyncio.sleep(0.1)
    return {"service": service_name, "status": "healthy"}

# Export main classes
__all__ = [
    'ErrorPropagationTester',
    'call_service_endpoint'
]
