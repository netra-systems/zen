"""Base interfaces for unified test framework - SSOT for all test component types."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class TestExecutor(Protocol):
    """Protocol for test executors."""
    
    def execute(self, tests: List[str]) -> Any:
        """Execute a list of tests and return results."""
        ...
    
    def can_execute(self, test_path: str) -> bool:
        """Check if executor can handle the given test."""
        ...


class TestEnvironment(Enum):
    """Unified environment enum for consistent environment handling."""
    TEST = "test"           # Local test environment with mocks
    DEV = "dev"            # Development environment with real services
    STAGING = "staging"    # Pre-production environment
    PROD = "prod"          # Production environment (restricted)
    
    @classmethod
    def from_string(cls, value: str) -> 'TestEnvironment':
        """Convert string to TestEnvironment enum with validation."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Invalid environment: {value}. Must be one of: {[e.value for e in cls]}")


class ServiceStatus(Enum):
    """Unified service status enum with legacy compatibility."""
    # Primary status values
    HEALTHY = "healthy"            # Service is healthy and responsive
    UNHEALTHY = "unhealthy"        # Service is not responding properly
    STARTING = "starting"          # Service is in startup phase
    STOPPING = "stopping"          # Service is shutting down
    UNAVAILABLE = "unavailable"    # Service is not available
    DEGRADED = "degraded"          # Service is available but performance is degraded
    MAINTENANCE = "maintenance"    # Service is in maintenance mode
    UNKNOWN = "unknown"           # Service status cannot be determined
    
    # Legacy compatibility aliases (maintains existing code compatibility)
    AVAILABLE = "healthy"          # Alias for HEALTHY
    ERROR = "unhealthy"            # Alias for UNHEALTHY
    TIMEOUT = "unhealthy"          # Timeout treated as unhealthy
    STOPPED = "unavailable"        # Stopped treated as unavailable
    RUNNING = "healthy"            # Running treated as healthy
    RESTARTING = "starting"        # Restarting treated as starting


@dataclass
class ServiceConfig:
    """Unified configuration dataclass for services across all test orchestration systems."""
    name: str                                          # Service name
    port: int                                          # Primary port for the service
    dockerfile: Optional[str] = None                   # Path to Dockerfile for container services
    build_context: str = "."                           # Build context for Docker
    ports: Dict[str, int] = field(default_factory=dict)  # Additional port mappings
    environment: Dict[str, str] = field(default_factory=dict)  # Environment variables
    depends_on: List[str] = field(default_factory=list)       # Service dependencies
    healthcheck: Optional[Dict[str, Any]] = None       # Health check configuration
    volumes: List[str] = field(default_factory=list)   # Volume mounts
    command: Optional[str] = None                       # Override command
    health_endpoint: Optional[str] = None               # Health check endpoint path
    required: bool = True                               # Whether service is required
    startup_timeout: int = 30                          # Startup timeout in seconds


class BaseTestInterface(ABC):
    """Base interface for all test components."""
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the test component."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup test component resources."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the component."""
        pass


class BaseTestComponent(BaseTestInterface):
    """SSOT base class for all test components requiring lifecycle management."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize base test component with configuration."""
        self._config = config.copy() if config else {}
        self._metrics: Dict[str, Any] = {}
        self._initialized = False
        self._start_time: Optional[datetime] = None
        self._last_health_check: Optional[datetime] = None
        self._status = ServiceStatus.UNKNOWN
        
    async def initialize(self) -> None:
        """Initialize the test component with lifecycle tracking."""
        if self._initialized:
            return
            
        try:
            self._start_time = datetime.now()
            self._status = ServiceStatus.STARTING
            
            # Allow subclasses to perform their initialization
            await self._do_initialize()
            
            self._initialized = True
            self._status = ServiceStatus.HEALTHY
            self._last_health_check = datetime.now()
            
        except Exception as e:
            self._status = ServiceStatus.UNHEALTHY
            raise e
    
    async def _do_initialize(self) -> None:
        """Override this method in subclasses for specific initialization."""
        pass
    
    async def cleanup(self) -> None:
        """Cleanup test component resources with error handling."""
        if not self._initialized:
            return
            
        try:
            self._status = ServiceStatus.STOPPING
            
            # Allow subclasses to perform their cleanup
            await self._do_cleanup()
            
            self._status = ServiceStatus.UNAVAILABLE
            self._initialized = False
            
        except Exception as e:
            self._status = ServiceStatus.ERROR
            # Log error but don't re-raise during cleanup
            print(f"Warning: Error during cleanup: {e}")
    
    async def _do_cleanup(self) -> None:
        """Override this method in subclasses for specific cleanup."""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the component."""
        return {
            "initialized": self._initialized,
            "status": self._status.value,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "config": self._config,
            "metrics": self._metrics.copy()
        }
    
    def record_metric(self, name: str, value: Any) -> None:
        """Record a metric for this component."""
        self._metrics[name] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_metric(self, name: str, default: Any = None) -> Any:
        """Get a recorded metric value."""
        metric = self._metrics.get(name)
        if metric is not None:
            return metric["value"]
        return default
    
    def is_healthy(self) -> bool:
        """Check if component is in a healthy state."""
        return self._status in [ServiceStatus.HEALTHY, ServiceStatus.AVAILABLE]