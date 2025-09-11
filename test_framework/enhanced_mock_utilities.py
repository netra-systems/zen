"""
Enhanced Mock Utilities for PR-F Test Infrastructure Improvements
Provides enhanced mocking capabilities with realistic behavior simulation.
"""
import asyncio
import random
import time
from typing import Dict, Any, Optional, List, Callable, Union
from unittest.mock import Mock, AsyncMock, MagicMock
from dataclasses import dataclass, field
from enum import Enum
import logging


class MockBehaviorType(Enum):
    """Types of mock behavior patterns."""
    REALISTIC = "realistic"
    FAST = "fast"  
    ERROR_PRONE = "error_prone"
    SLOW = "slow"
    INTERMITTENT = "intermittent"


@dataclass
class MockConfiguration:
    """Configuration for enhanced mock behavior."""
    behavior_type: MockBehaviorType = MockBehaviorType.REALISTIC
    base_latency: float = 0.01  # Base latency in seconds
    latency_variation: float = 0.005  # Latency variation
    error_rate: float = 0.0  # Error rate (0.0 to 1.0)
    intermittent_failure_rate: float = 0.0  # Intermittent failure rate
    state_persistence: bool = True  # Whether to persist state across calls
    custom_behaviors: Dict[str, Callable] = field(default_factory=dict)


class EnhancedMockService:
    """
    Enhanced mock service with realistic behavior simulation.
    
    Provides:
    - Realistic latency simulation
    - Error injection capabilities  
    - State persistence
    - Custom behavior patterns
    - Performance metrics
    """
    
    def __init__(self, service_name: str, config: MockConfiguration = None):
        """Initialize enhanced mock service."""
        self.service_name = service_name
        self.config = config or MockConfiguration()
        self.state = {}
        self.call_history = []
        self.performance_metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "average_latency": 0.0,
            "total_latency": 0.0
        }
        self.logger = logging.getLogger(f"mock.{service_name}")
    
    async def _simulate_latency(self, operation: str) -> None:
        """Simulate realistic latency for operations."""
        if self.config.behavior_type == MockBehaviorType.FAST:
            return  # No latency for fast mode
        
        base_latency = self.config.base_latency
        variation = random.uniform(
            -self.config.latency_variation, 
            self.config.latency_variation
        )
        
        # Adjust latency based on behavior type
        latency_multipliers = {
            MockBehaviorType.REALISTIC: 1.0,
            MockBehaviorType.SLOW: 3.0,
            MockBehaviorType.ERROR_PRONE: 1.2,
            MockBehaviorType.INTERMITTENT: 1.5
        }
        
        multiplier = latency_multipliers.get(self.config.behavior_type, 1.0)
        total_latency = max(0, (base_latency + variation) * multiplier)
        
        if total_latency > 0:
            await asyncio.sleep(total_latency)
        
        # Update performance metrics
        self.performance_metrics["total_latency"] += total_latency
    
    def _should_inject_error(self, operation: str) -> bool:
        """Determine if an error should be injected."""
        base_error_rate = self.config.error_rate
        
        # Adjust error rate based on behavior type
        if self.config.behavior_type == MockBehaviorType.ERROR_PRONE:
            base_error_rate *= 2.0
        elif self.config.behavior_type == MockBehaviorType.INTERMITTENT:
            # Intermittent failures come in bursts
            if random.random() < self.config.intermittent_failure_rate:
                base_error_rate = 0.5  # 50% failure rate during burst
        
        return random.random() < base_error_rate
    
    def _record_call(self, operation: str, args: tuple, kwargs: dict, success: bool, error: Optional[Exception] = None):
        """Record call for history and metrics."""
        call_record = {
            "timestamp": time.time(),
            "operation": operation,
            "args": args,
            "kwargs": kwargs,
            "success": success,
            "error": str(error) if error else None
        }
        
        self.call_history.append(call_record)
        self.performance_metrics["total_calls"] += 1
        
        if success:
            self.performance_metrics["successful_calls"] += 1
        else:
            self.performance_metrics["failed_calls"] += 1
        
        # Update average latency
        if self.performance_metrics["total_calls"] > 0:
            self.performance_metrics["average_latency"] = (
                self.performance_metrics["total_latency"] / 
                self.performance_metrics["total_calls"]
            )
    
    async def mock_operation(self, operation: str, *args, **kwargs) -> Any:
        """Execute a mock operation with realistic behavior."""
        start_time = time.time()
        
        try:
            # Simulate latency
            await self._simulate_latency(operation)
            
            # Check for custom behavior
            if operation in self.config.custom_behaviors:
                result = await self.config.custom_behaviors[operation](*args, **kwargs)
                self._record_call(operation, args, kwargs, True)
                return result
            
            # Check for error injection
            if self._should_inject_error(operation):
                error = Exception(f"Mock error in {self.service_name}.{operation}")
                self._record_call(operation, args, kwargs, False, error)
                raise error
            
            # Default successful response
            result = f"Mock {operation} successful"
            self._record_call(operation, args, kwargs, True)
            
            # Update state if persistence enabled
            if self.config.state_persistence:
                self.state[f"last_{operation}"] = {
                    "args": args,
                    "kwargs": kwargs,
                    "result": result,
                    "timestamp": time.time()
                }
            
            return result
            
        except Exception as e:
            self._record_call(operation, args, kwargs, False, e)
            raise
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance metrics report."""
        return {
            "service_name": self.service_name,
            "configuration": {
                "behavior_type": self.config.behavior_type.value,
                "base_latency": self.config.base_latency,
                "error_rate": self.config.error_rate
            },
            "metrics": self.performance_metrics.copy(),
            "state_keys": list(self.state.keys()),
            "recent_calls": self.call_history[-10:] if self.call_history else []
        }


class EnhancedWebSocketMock:
    """Enhanced WebSocket mock with realistic connection behavior."""
    
    def __init__(self, config: MockConfiguration = None):
        """Initialize enhanced WebSocket mock."""
        self.config = config or MockConfiguration()
        self.connected = False
        self.connection_history = []
        self.message_history = []
        self.event_handlers = {}
    
    async def connect(self, url: str) -> bool:
        """Mock WebSocket connection with realistic behavior."""
        # Simulate connection latency
        await asyncio.sleep(self.config.base_latency)
        
        # Simulate connection failures
        if random.random() < self.config.error_rate:
            self.connection_history.append({
                "timestamp": time.time(),
                "url": url,
                "success": False,
                "error": "Connection refused"
            })
            raise ConnectionError("Mock WebSocket connection failed")
        
        self.connected = True
        self.connection_history.append({
            "timestamp": time.time(),
            "url": url,
            "success": True
        })
        
        return True
    
    async def send(self, message: Dict[str, Any]) -> bool:
        """Mock sending WebSocket message."""
        if not self.connected:
            raise ConnectionError("WebSocket not connected")
        
        # Simulate send latency
        await asyncio.sleep(self.config.base_latency * 0.5)
        
        # Simulate send failures
        if random.random() < self.config.error_rate:
            raise Exception("Mock message send failed")
        
        self.message_history.append({
            "timestamp": time.time(),
            "direction": "sent",
            "message": message
        })
        
        return True
    
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Mock receiving WebSocket message."""
        if not self.connected:
            return None
        
        # Simulate receive latency  
        await asyncio.sleep(self.config.base_latency * 0.3)
        
        # Generate mock response based on behavior type
        if self.config.behavior_type == MockBehaviorType.REALISTIC:
            mock_response = {
                "type": "agent_message",
                "data": "Mock agent response",
                "timestamp": time.time()
            }
        else:
            mock_response = {"type": "ping"}
        
        self.message_history.append({
            "timestamp": time.time(),
            "direction": "received",
            "message": mock_response
        })
        
        return mock_response
    
    def disconnect(self):
        """Mock WebSocket disconnection."""
        self.connected = False


class EnhancedBackgroundJobMock:
    """Enhanced background job mock with queue simulation."""
    
    def __init__(self, config: MockConfiguration = None):
        """Initialize enhanced background job mock."""
        self.config = config or MockConfiguration()
        self.job_queue = []
        self.completed_jobs = []
        self.failed_jobs = []
        self.is_processing = False
    
    async def enqueue_job(self, job_type: str, job_data: Dict[str, Any]) -> str:
        """Enqueue a mock background job."""
        job_id = f"job_{len(self.job_queue)}_{int(time.time())}"
        
        job = {
            "id": job_id,
            "type": job_type,
            "data": job_data,
            "enqueued_at": time.time(),
            "status": "queued"
        }
        
        self.job_queue.append(job)
        
        # Start processing if not already processing
        if not self.is_processing:
            asyncio.create_task(self._process_jobs())
        
        return job_id
    
    async def _process_jobs(self):
        """Process jobs from the queue."""
        self.is_processing = True
        
        while self.job_queue:
            job = self.job_queue.pop(0)
            
            # Simulate job processing time
            processing_time = self.config.base_latency * random.uniform(5, 15)
            await asyncio.sleep(processing_time)
            
            # Simulate job failures
            if random.random() < self.config.error_rate:
                job["status"] = "failed"
                job["completed_at"] = time.time()
                job["error"] = "Mock job processing error"
                self.failed_jobs.append(job)
            else:
                job["status"] = "completed"
                job["completed_at"] = time.time()
                job["result"] = f"Mock result for {job['type']}"
                self.completed_jobs.append(job)
        
        self.is_processing = False
    
    def get_job_status(self, job_id: str) -> Optional[str]:
        """Get status of a background job."""
        # Check all job lists
        all_jobs = self.job_queue + self.completed_jobs + self.failed_jobs
        
        for job in all_jobs:
            if job["id"] == job_id:
                return job["status"]
        
        return None


class MockServiceRegistry:
    """Registry for managing enhanced mock services."""
    
    def __init__(self):
        """Initialize mock service registry."""
        self.services: Dict[str, EnhancedMockService] = {}
        self.websockets: Dict[str, EnhancedWebSocketMock] = {}
        self.background_jobs: Dict[str, EnhancedBackgroundJobMock] = {}
    
    def create_service_mock(self, service_name: str, config: MockConfiguration = None) -> EnhancedMockService:
        """Create and register an enhanced service mock."""
        service = EnhancedMockService(service_name, config)
        self.services[service_name] = service
        return service
    
    def create_websocket_mock(self, name: str, config: MockConfiguration = None) -> EnhancedWebSocketMock:
        """Create and register an enhanced WebSocket mock."""
        websocket = EnhancedWebSocketMock(config)
        self.websockets[name] = websocket
        return websocket
    
    def create_background_job_mock(self, name: str, config: MockConfiguration = None) -> EnhancedBackgroundJobMock:
        """Create and register an enhanced background job mock."""
        job_mock = EnhancedBackgroundJobMock(config)
        self.background_jobs[name] = job_mock
        return job_mock
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive report of all mock services."""
        return {
            "services": {
                name: service.get_performance_report() 
                for name, service in self.services.items()
            },
            "websockets": {
                name: {
                    "connected": ws.connected,
                    "connections": len(ws.connection_history),
                    "messages": len(ws.message_history)
                }
                for name, ws in self.websockets.items()
            },
            "background_jobs": {
                name: {
                    "queued": len(job.job_queue),
                    "completed": len(job.completed_jobs),
                    "failed": len(job.failed_jobs),
                    "processing": job.is_processing
                }
                for name, job in self.background_jobs.items()
            }
        }


# Convenience functions for quick mock setup
def create_realistic_mock(service_name: str) -> EnhancedMockService:
    """Create a mock with realistic behavior."""
    config = MockConfiguration(behavior_type=MockBehaviorType.REALISTIC)
    return EnhancedMockService(service_name, config)


def create_fast_mock(service_name: str) -> EnhancedMockService:
    """Create a fast mock for quick testing."""
    config = MockConfiguration(
        behavior_type=MockBehaviorType.FAST,
        base_latency=0.0
    )
    return EnhancedMockService(service_name, config)


def create_error_prone_mock(service_name: str, error_rate: float = 0.1) -> EnhancedMockService:
    """Create a mock prone to errors for failure testing."""
    config = MockConfiguration(
        behavior_type=MockBehaviorType.ERROR_PRONE,
        error_rate=error_rate
    )
    return EnhancedMockService(service_name, config)


# Global registry instance
mock_registry = MockServiceRegistry()