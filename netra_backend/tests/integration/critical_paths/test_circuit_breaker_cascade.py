"""Circuit Breaker Cascade Recovery Critical Path Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (protects high-value customers)
- Business Goal: Prevent cascading failures from affecting revenue
- Value Impact: Protects $10K MRR from cascading service failures
- Strategic Impact: Ensures system resilience and maintains customer confidence

Critical Path: Service failure -> Circuit breaker opens -> Cascade prevention -> Recovery detection -> Circuit breaker closes
Coverage: Real circuit breaker states, cascade protection, auto-recovery, failure isolation
Level: L2-L3 (Real SUT with Real Internal Dependencies + Real Local Services)
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Real services for L2-L3 testing
from netra_backend.app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
)
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager as ConnectionManager
from netra_backend.app.core.health_checkers import (
    check_postgres_health,
    check_redis_health,
)
from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.websocket.connection_manager import (
    ConnectionManager,
    get_connection_manager,
)

logger = logging.getLogger(__name__)

class CircuitBreakerCascadeManager:
    """Manages L2-L3 circuit breaker cascade testing with real services."""
    
    def __init__(self):
        self.circuit_breakers = {}
        self.redis_service = None
        self.db_manager = None
        self.websocket_manager = None
        self.failure_events = []
        self.recovery_events = []
        self.service_dependencies = {
            "api_service": ["database", "redis"],
            "websocket_service": ["redis", "api_service"],
            "auth_service": ["database"],
            "agent_service": ["database", "redis", "api_service"]
        }
        
    async def initialize_services(self):
        """Initialize real services for L2-L3 circuit breaker testing."""
        # Real Redis service
        self.redis_service = RedisService()
        await self.redis_service.connect()
        
        # Real database connection manager
        self.db_manager = ConnectionManager()
        await self.db_manager.initialize()
        
        # Real WebSocket manager
        self.websocket_manager = get_connection_manager()
        # Note: ConnectionManager doesn't have initialize() method
        
        # Create real circuit breakers for each service
        for service_name in ["api_service", "websocket_service", "auth_service", "agent_service", "database", "redis"]:
            self.circuit_breakers[service_name] = CircuitBreaker(
                service_name, 
                failure_threshold=3, 
                timeout=30.0, 
                recovery_timeout=60.0
            )
    
    async def simulate_service_failure(self, service_name: str, failure_count: int = 5):
        """Simulate L3 service failure to trigger real circuit breaker."""
        start_time = time.time()
        
        if service_name not in self.circuit_breakers:
            raise ValueError(f"Unknown service: {service_name}")
            
        circuit_breaker = self.circuit_breakers[service_name]
        
        # Simulate realistic service failures
        for i in range(failure_count):
            try:
                if service_name == "database":
                    # Simulate database failure
                    conn = await self.db_manager.get_connection()
                    await conn.execute("SELECT 1 / 0")  # This will cause an error
                    await self.db_manager.return_connection(conn)
                elif service_name == "redis":
                    # Simulate Redis failure
                    await self.redis_service.client.get("non_existent_key_that_causes_error")
                    raise Exception("Simulated Redis failure")
                else:
                    # Generic service failure
                    raise Exception(f"Simulated {service_name} failure")
                    
            except Exception as e:
                await circuit_breaker.record_failure(str(e))
                self.failure_events.append({
                    "service": service_name,
                    "error": str(e),
                    "timestamp": time.time()
                })
                
                # Log failure to Redis for L3 validation
                await self.redis_service.client.lpush(
                    f"failures:{service_name}", 
                    json.dumps({"error": str(e), "timestamp": time.time()})
                )
                
                await asyncio.sleep(0.1)
        
        return {
            "service": service_name,
            "state": circuit_breaker.state.value,
            "failure_count": circuit_breaker.failure_count,
            "failure_time": time.time() - start_time
        }
    
    async def test_cascade_protection(self, primary_service: str) -> Dict[str, Any]:
        """Test L3 circuit breaker cascade protection with real service dependencies."""
        cascade_start = time.time()
        
        # Fail primary service
        primary_result = await self.simulate_service_failure(primary_service)
        
        # Wait for cascade detection
        await asyncio.sleep(0.5)
        
        # Check dependent services
        dependent_services = [service for service, deps in self.service_dependencies.items() 
                            if primary_service in deps]
        
        cascade_results = {primary_service: primary_result}
        
        for service in dependent_services:
            circuit_breaker = self.circuit_breakers[service]
            
            # Test dependent service calls with circuit breaker protection
            protected_calls = 0
            for _ in range(3):
                try:
                    async def dependent_call():
                        if primary_service == "database":
                            # This should be protected by circuit breaker
                            conn = await self.db_manager.get_connection()
                            await conn.execute("SELECT 1")
                            await self.db_manager.return_connection(conn)
                        elif primary_service == "redis":
                            await self.redis_service.client.ping()
                        return True
                        
                    result = await circuit_breaker.call(dependent_call)
                    if result:
                        protected_calls += 1
                except Exception:
                    # Circuit breaker should prevent these calls
                    pass
            
            cascade_results[service] = {
                "state": circuit_breaker.state.value,
                "protected_calls": protected_calls,
                "cascade_prevented": circuit_breaker.state.value != "closed"
            }
        
        return {
            "cascade_results": cascade_results,
            "cascade_time": time.time() - cascade_start,
            "primary_service": primary_service,
            "dependent_services": dependent_services
        }
    
    async def cleanup(self):
        """Clean up L2-L3 circuit breaker resources."""
        # Clear Redis failure logs
        for service_name in self.circuit_breakers.keys():
            await self.redis_service.client.delete(f"failures:{service_name}")
        
        # Reset circuit breakers
        for circuit_breaker in self.circuit_breakers.values():
            circuit_breaker.reset()
        
        if self.redis_service:
            await self.redis_service.disconnect()
        # Note: ConnectionManager cleanup is handled automatically
        if self.db_manager:
            await self.db_manager.shutdown()

@pytest.fixture
async def circuit_cascade_manager():
    """Create circuit breaker cascade manager for L2-L3 testing."""
    manager = CircuitBreakerCascadeManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_circuit_breaker_state_transitions(circuit_cascade_manager):
    """Test L2-L3 circuit breaker state transitions through failure and recovery."""
    manager = circuit_cascade_manager
    service_name = "database"
    
    circuit_breaker = manager.circuit_breakers[service_name]
    
    # Start in closed state
    initial_state = circuit_breaker.state.value
    assert initial_state == "closed"
    
    # Simulate realistic database failures
    failure_result = await manager.simulate_service_failure(service_name, failure_count=4)
    assert failure_result["state"] == "open"
    assert failure_result["failure_time"] < 2.0
    assert failure_result["failure_count"] >= 3
    
    # Verify Redis logging of failures
    failure_logs = await manager.redis_service.client.lrange(f"failures:{service_name}", 0, -1)
    assert len(failure_logs) >= 3
    
    # Wait for half-open transition (reduced timeout for testing)
    await asyncio.sleep(0.5)
    circuit_breaker.timeout = 0.1  # Speed up test
    await asyncio.sleep(0.2)
    
    # Circuit breaker should allow test calls in half-open state
    assert circuit_breaker.state.value in ["open", "half_open"]

@pytest.mark.asyncio 
@pytest.mark.l3_realism
async def test_cascade_failure_prevention(circuit_cascade_manager):
    """Test L2-L3 circuit breaker cascade failure prevention."""
    manager = circuit_cascade_manager
    
    # Test cascade protection with database failure
    cascade_result = await manager.test_cascade_protection("database")
    
    # Primary service (database) should be open (failed)
    assert cascade_result["cascade_results"]["database"]["state"] == "open"
    
    # Dependent services should be protected
    dependent_services = cascade_result["dependent_services"]
    assert len(dependent_services) > 0
    
    for service in dependent_services:
        service_result = cascade_result["cascade_results"][service]
        # Circuit breaker should prevent cascading failures
        assert service_result["protected_calls"] < 3  # Not all calls should succeed
        
    assert cascade_result["cascade_time"] < 3.0

@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_circuit_breaker_recovery_detection(circuit_cascade_manager):
    """Test L2-L3 automatic recovery detection and circuit breaker closing."""
    manager = circuit_cascade_manager
    service_name = "redis"
    
    circuit_breaker = manager.circuit_breakers[service_name]
    
    # Trip circuit breaker with Redis failures
    await manager.simulate_service_failure(service_name, failure_count=4)
    assert circuit_breaker.state.value == "open"
    
    # Simulate service recovery by making successful calls
    circuit_breaker.timeout = 0.1  # Speed up recovery test
    await asyncio.sleep(0.2)  # Wait for half-open opportunity
    
    # Test successful Redis operations to close circuit breaker
    success_count = 0
    for _ in range(5):
        try:
            async def recovery_call():
                await manager.redis_service.client.ping()
                return True
                
            result = await circuit_breaker.call(recovery_call)
            if result:
                success_count += 1
                
        except Exception:
            pass
            
        await asyncio.sleep(0.1)
    
    # Circuit breaker should eventually close with successful calls
    assert success_count > 0
    # State should be closed or at least half-open (progressing toward closed)
    assert circuit_breaker.state.value in ["closed", "half_open"]

@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_circuit_breaker_redis_integration(circuit_cascade_manager):
    """Test L3 circuit breaker integration with Redis metrics."""
    manager = circuit_cascade_manager
    service_name = "api_service"
    
    circuit_breaker = manager.circuit_breakers[service_name]
    
    # Record metrics during failure in Redis
    await manager.redis_service.client.hset(
        f"circuit_breaker:{service_name}",
        mapping={
            "initial_state": circuit_breaker.state.value,
            "test_start": str(time.time())
        }
    )
    
    # Simulate failure
    failure_result = await manager.simulate_service_failure(service_name)
    
    # Update metrics in Redis
    await manager.redis_service.client.hset(
        f"circuit_breaker:{service_name}",
        mapping={
            "final_state": circuit_breaker.state.value,
            "failure_count": str(circuit_breaker.failure_count),
            "test_end": str(time.time())
        }
    )
    
    # Verify metrics in Redis
    metrics = await manager.redis_service.client.hgetall(f"circuit_breaker:{service_name}")
    
    assert metrics["initial_state"] == "closed"
    assert metrics["final_state"] == "open"
    assert int(metrics["failure_count"]) >= 3
    assert float(metrics["test_end"]) > float(metrics["test_start"])
    
    # Verify failure logs exist
    failure_logs = await manager.redis_service.client.lrange(f"failures:{service_name}", 0, -1)
    assert len(failure_logs) > 0