"""
Base interfaces and abstract classes for the unified Cloud Run test framework.

This module defines the core contracts and patterns that all test components must follow.
Adheres to SPEC/type_safety.xml and SPEC/conventions.xml.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Protocol, TypeVar, Generic
from datetime import datetime
import asyncio


class TestEnvironment(Enum):
    """Test environment types."""
    LOCAL = "local"
    DOCKER = "docker" 
    STAGING = "staging"
    PRODUCTION = "production"


class TestLevel(Enum):
    """Test execution levels."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    SMOKE = "smoke"
    PERFORMANCE = "performance"
    HEALTH = "health"


class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    STARTING = "starting"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass
class ServiceConfig:
    """Configuration for a single service."""
    name: str
    environment: TestEnvironment
    url: Optional[str] = None
    health_endpoint: str = "/health"
    port: Optional[int] = None
    container_name: Optional[str] = None
    timeout: int = 30
    retry_count: int = 3
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class TestResult:
    """Result of a test execution."""
    test_name: str
    level: TestLevel
    environment: TestEnvironment
    status: bool
    duration_ms: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    service_name: str
    status: ServiceStatus
    response_time_ms: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}


class ITestExecutor(ABC):
    """Interface for test executors."""
    
    @abstractmethod
    async def setup(self) -> None:
        """Set up the test environment."""
        pass
    
    @abstractmethod
    async def execute(self, test_config: Dict[str, Any]) -> TestResult:
        """Execute a test and return results."""
        pass
    
    @abstractmethod
    async def teardown(self) -> None:
        """Clean up the test environment."""
        pass
    
    @abstractmethod
    def get_environment(self) -> TestEnvironment:
        """Get the current test environment."""
        pass


class IHealthMonitor(ABC):
    """Interface for health monitoring."""
    
    @abstractmethod
    async def check_health(self, service_config: ServiceConfig) -> HealthCheckResult:
        """Check health of a service."""
        pass
    
    @abstractmethod
    async def monitor_continuous(
        self, 
        service_configs: List[ServiceConfig],
        interval_seconds: int = 30
    ) -> AsyncIterator[List[HealthCheckResult]]:
        """Continuously monitor service health."""
        pass
    
    @abstractmethod
    async def get_status_summary(self) -> Dict[str, ServiceStatus]:
        """Get current status summary of all monitored services."""
        pass


class ILogAnalyzer(ABC):
    """Interface for log analysis."""
    
    @abstractmethod
    async def fetch_logs(
        self,
        filter_query: str,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch logs based on filter criteria."""
        pass
    
    @abstractmethod
    async def analyze_errors(
        self,
        service_name: str,
        duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """Analyze errors for a service."""
        pass
    
    @abstractmethod
    async def get_metrics(
        self,
        service_name: str,
        metric_types: List[str]
    ) -> Dict[str, Any]:
        """Get performance metrics from logs."""
        pass


class IDeploymentValidator(ABC):
    """Interface for deployment validation."""
    
    @abstractmethod
    async def validate_deployment(
        self,
        service_configs: List[ServiceConfig]
    ) -> Dict[str, bool]:
        """Validate that services are properly deployed."""
        pass
    
    @abstractmethod
    async def validate_api_contracts(
        self,
        openapi_spec_path: str
    ) -> Dict[str, List[str]]:
        """Validate API contracts against OpenAPI spec."""
        pass
    
    @abstractmethod
    async def validate_dependencies(
        self,
        service_configs: List[ServiceConfig]
    ) -> Dict[str, List[str]]:
        """Validate service dependencies are met."""
        pass


class IContainerManager(ABC):
    """Interface for container management."""
    
    @abstractmethod
    async def start_containers(
        self,
        services: Optional[List[str]] = None
    ) -> bool:
        """Start containers for specified services."""
        pass
    
    @abstractmethod
    async def stop_containers(
        self,
        services: Optional[List[str]] = None
    ) -> bool:
        """Stop containers for specified services."""
        pass
    
    @abstractmethod
    async def wait_for_healthy(
        self,
        timeout_seconds: int = 300
    ) -> bool:
        """Wait for all containers to be healthy."""
        pass
    
    @abstractmethod
    async def get_container_logs(
        self,
        container_name: str,
        tail_lines: int = 100
    ) -> str:
        """Get logs from a container."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up all containers and resources."""
        pass


class IConfigurationManager(Protocol):
    """Protocol for configuration management."""
    
    def load_config(self, environment: TestEnvironment) -> Dict[str, Any]:
        """Load configuration for an environment."""
        ...
    
    def get_service_configs(self, environment: TestEnvironment) -> List[ServiceConfig]:
        """Get service configurations for an environment."""
        ...
    
    def get_test_config(self, test_level: TestLevel) -> Dict[str, Any]:
        """Get test configuration for a level."""
        ...
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure."""
        ...


T = TypeVar('T')


class ITestOrchestrator(Generic[T], ABC):
    """Generic interface for test orchestration."""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the orchestrator with configuration."""
        pass
    
    @abstractmethod
    async def run_test_suite(
        self,
        test_level: TestLevel,
        environment: TestEnvironment
    ) -> List[TestResult]:
        """Run a complete test suite."""
        pass
    
    @abstractmethod
    async def run_single_test(
        self,
        test_name: str,
        test_config: T
    ) -> TestResult:
        """Run a single test."""
        pass
    
    @abstractmethod
    async def generate_report(
        self,
        results: List[TestResult]
    ) -> Dict[str, Any]:
        """Generate a test report from results."""
        pass
    
    @abstractmethod
    def get_test_registry(self) -> Dict[str, T]:
        """Get registry of available tests."""
        pass


class BaseTestComponent(ABC):
    """Base class for all test components."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._initialized = False
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the component."""
        self._initialized = True
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if component is initialized."""
        return self._initialized
    
    def validate_initialized(self) -> None:
        """Ensure component is initialized."""
        if not self._initialized:
            raise RuntimeError(f"{self.__class__.__name__} not initialized")


class ITestReporter(ABC):
    """Interface for test reporting."""
    
    @abstractmethod
    async def report_results(
        self,
        results: List[TestResult],
        format: str = "json"
    ) -> str:
        """Generate test report in specified format."""
        pass
    
    @abstractmethod
    async def send_alerts(
        self,
        failures: List[TestResult],
        channels: List[str]
    ) -> bool:
        """Send alerts for test failures."""
        pass
    
    @abstractmethod
    async def archive_results(
        self,
        results: List[TestResult],
        archive_path: str
    ) -> bool:
        """Archive test results for historical analysis."""
        pass


class IPerformanceTester(ABC):
    """Interface for performance testing."""
    
    @abstractmethod
    async def run_load_test(
        self,
        endpoint: str,
        concurrent_users: int,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """Run load test on an endpoint."""
        pass
    
    @abstractmethod
    async def measure_latency(
        self,
        endpoint: str,
        iterations: int = 100
    ) -> Dict[str, float]:
        """Measure endpoint latency statistics."""
        pass
    
    @abstractmethod
    async def profile_memory(
        self,
        service_name: str,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """Profile memory usage of a service."""
        pass


class TestHook(ABC):
    """Base class for test hooks."""
    
    @abstractmethod
    async def before_test(self, test_name: str, config: Dict[str, Any]) -> None:
        """Hook executed before test."""
        pass
    
    @abstractmethod
    async def after_test(
        self,
        test_name: str,
        result: TestResult
    ) -> None:
        """Hook executed after test."""
        pass
    
    @abstractmethod
    async def on_failure(
        self,
        test_name: str,
        error: Exception
    ) -> None:
        """Hook executed on test failure."""
        pass