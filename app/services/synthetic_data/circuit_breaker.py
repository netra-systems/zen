"""
Circuit breaker implementation for preventing cascade failures
"""

import asyncio


class CircuitBreaker:
    """Circuit breaker for preventing cascade failures"""
    
    def __init__(self):
        self._state = "closed"
        self.failure_count = 0
        self.timeout = 0.1
        self._open_time = None
    
    @property
    def state(self):
        """Get current state, transitioning from open to half_open if timeout expired"""
        if self._state == "open" and self._open_time:
            if (asyncio.get_event_loop().time() - self._open_time) >= self.timeout:
                self._state = "half_open"
        return self._state
    
    @state.setter
    def state(self, value):
        """Set circuit breaker state"""
        self._state = value
    
    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is in open state."""
        return self.state == "open"
        
    async def call(self, func):
        """Call function with circuit breaker"""
        current_state = self.state
        try:
            self._check_circuit_state(current_state)
            result = await self._execute_function(func)
            self._handle_success(current_state)
            return result
        except Exception as e:
            self._handle_failure()
            raise e
    
    def _check_circuit_state(self, current_state: str) -> None:
        """Check if circuit breaker allows execution"""
        if current_state == "open":
            raise Exception("Circuit breaker is open")
    
    async def _execute_function(self, func):
        """Execute function based on its type"""
        return await func() if asyncio.iscoroutinefunction(func) else func()
    
    def _handle_success(self, current_state: str) -> None:
        """Handle successful function execution"""
        self.failure_count = 0
        if current_state == "half_open":
            self.state = "closed"
    
    def _handle_failure(self) -> None:
        """Handle function execution failure"""
        self.failure_count += 1
        if self.failure_count >= 5:
            self.state = "open"
            self._open_time = asyncio.get_event_loop().time()
    
    def record_success(self) -> None:
        """Record successful execution"""
        self._handle_success(self.state)
    
    def record_failure(self) -> None:
        """Record failed execution"""
        self._handle_failure()