"""Circuit Breaker Service for service mesh"""

import asyncio
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failing, blocking requests
    HALF_OPEN = "half_open" # Testing if service recovered


class CircuitBreakerService:
    """Circuit breaker for protecting services from cascading failures"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, test_requests: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout  # seconds
        self.test_requests = test_requests
        
        self.circuits: Dict[str, Dict[str, Any]] = {}
        self.call_stats: Dict[str, Dict[str, int]] = {}
    
    async def register_service(self, service_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Register a service with circuit breaker protection"""
        circuit_config = config or {}
        
        self.circuits[service_name] = {
            "state": CircuitState.CLOSED,
            "failure_count": 0,
            "last_failure_time": None,
            "test_request_count": 0,
            "failure_threshold": circuit_config.get("failure_threshold", self.failure_threshold),
            "recovery_timeout": circuit_config.get("recovery_timeout", self.recovery_timeout),
            "test_requests": circuit_config.get("test_requests", self.test_requests),
            "created_at": datetime.now(UTC).isoformat()
        }
        
        self.call_stats[service_name] = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "blocked_calls": 0
        }
        
        return True
    
    async def can_execute(self, service_name: str) -> bool:
        """Check if request can be executed (circuit not open)"""
        if service_name not in self.circuits:
            # Auto-register if not exists
            await self.register_service(service_name)
        
        circuit = self.circuits[service_name]
        current_state = circuit["state"]
        
        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.OPEN:
            return await self._check_recovery_time(service_name, circuit)
        elif current_state == CircuitState.HALF_OPEN:
            return circuit["test_request_count"] < circuit["test_requests"]
        
        return False
    
    async def _check_recovery_time(self, service_name: str, circuit: Dict[str, Any]) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if circuit["last_failure_time"]:
            last_failure = datetime.fromisoformat(circuit["last_failure_time"])
            recovery_time = timedelta(seconds=circuit["recovery_timeout"])
            
            if datetime.now(UTC) - last_failure >= recovery_time:
                # Transition to half-open
                circuit["state"] = CircuitState.HALF_OPEN
                circuit["test_request_count"] = 0
                return True
        
        return False
    
    async def record_success(self, service_name: str) -> None:
        """Record successful execution"""
        if service_name not in self.circuits:
            return
        
        circuit = self.circuits[service_name]
        stats = self.call_stats[service_name]
        
        stats["total_calls"] += 1
        stats["successful_calls"] += 1
        
        if circuit["state"] == CircuitState.HALF_OPEN:
            circuit["test_request_count"] += 1
            
            # If enough test requests succeeded, close the circuit
            if circuit["test_request_count"] >= circuit["test_requests"]:
                circuit["state"] = CircuitState.CLOSED
                circuit["failure_count"] = 0
                circuit["test_request_count"] = 0
        elif circuit["state"] == CircuitState.CLOSED:
            # Reset failure count on success
            circuit["failure_count"] = 0
    
    async def record_failure(self, service_name: str, error: Optional[str] = None) -> None:
        """Record failed execution"""
        if service_name not in self.circuits:
            return
        
        circuit = self.circuits[service_name]
        stats = self.call_stats[service_name]
        
        stats["total_calls"] += 1
        stats["failed_calls"] += 1
        
        circuit["failure_count"] += 1
        circuit["last_failure_time"] = datetime.now(UTC).isoformat()
        
        # Check if we should open the circuit
        if circuit["failure_count"] >= circuit["failure_threshold"]:
            circuit["state"] = CircuitState.OPEN
            circuit["test_request_count"] = 0
    
    async def record_blocked(self, service_name: str) -> None:
        """Record blocked request due to open circuit"""
        if service_name not in self.call_stats:
            return
        
        self.call_stats[service_name]["blocked_calls"] += 1
    
    async def execute_with_circuit_breaker(self, service_name: str, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with circuit breaker protection"""
        if not await self.can_execute(service_name):
            await self.record_blocked(service_name)
            raise Exception(f"Circuit breaker is OPEN for service: {service_name}")
        
        try:
            result = await operation(*args, **kwargs)
            await self.record_success(service_name)
            return result
        except Exception as e:
            await self.record_failure(service_name, str(e))
            raise
    
    async def get_circuit_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a circuit breaker"""
        if service_name not in self.circuits:
            return None
        
        circuit = self.circuits[service_name]
        stats = self.call_stats[service_name]
        
        return {
            "service_name": service_name,
            "state": circuit["state"].value,
            "failure_count": circuit["failure_count"],
            "failure_threshold": circuit["failure_threshold"],
            "last_failure_time": circuit["last_failure_time"],
            "test_request_count": circuit.get("test_request_count", 0),
            "statistics": stats
        }
    
    async def force_open(self, service_name: str) -> bool:
        """Manually open a circuit breaker"""
        if service_name not in self.circuits:
            return False
        
        self.circuits[service_name]["state"] = CircuitState.OPEN
        self.circuits[service_name]["last_failure_time"] = datetime.now(UTC).isoformat()
        return True
    
    async def force_close(self, service_name: str) -> bool:
        """Manually close a circuit breaker"""
        if service_name not in self.circuits:
            return False
        
        circuit = self.circuits[service_name]
        circuit["state"] = CircuitState.CLOSED
        circuit["failure_count"] = 0
        circuit["test_request_count"] = 0
        return True
    
    async def get_all_circuit_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        status = {}
        for service_name in self.circuits:
            status[service_name] = await self.get_circuit_status(service_name)
        return status
    
    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """Get overall circuit breaker statistics"""
        total_circuits = len(self.circuits)
        open_circuits = sum(1 for c in self.circuits.values() if c["state"] == CircuitState.OPEN)
        half_open_circuits = sum(1 for c in self.circuits.values() if c["state"] == CircuitState.HALF_OPEN)
        closed_circuits = total_circuits - open_circuits - half_open_circuits
        
        total_calls = sum(stats["total_calls"] for stats in self.call_stats.values())
        total_failures = sum(stats["failed_calls"] for stats in self.call_stats.values())
        total_blocked = sum(stats["blocked_calls"] for stats in self.call_stats.values())
        
        return {
            "total_circuits": total_circuits,
            "open_circuits": open_circuits,
            "half_open_circuits": half_open_circuits,
            "closed_circuits": closed_circuits,
            "total_calls": total_calls,
            "total_failures": total_failures,
            "total_blocked": total_blocked,
            "success_rate": (total_calls - total_failures) / total_calls if total_calls > 0 else 0
        }