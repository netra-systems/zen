"""
Base Test Interfaces: Foundation interfaces for test framework components.

This module provides base interfaces and protocols that all test framework
components should implement to ensure consistency and interoperability.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol

# Avoid circular imports by defining interfaces locally
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel


class TestExecutionState(str, Enum):
    """Test execution state enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestCategory(str, Enum):
    """Test category classification."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"
    AGENTS = "agents"
    CRITICAL = "critical"


@dataclass
class TestResult:
    """Individual test execution result."""
    test_id: str
    name: str
    category: TestCategory
    state: TestExecutionState
    duration: float = 0.0
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class TestConfiguration(BaseModel):
    """Unified test configuration."""
    parallel_execution: bool = True
    max_workers: int = 4
    timeout_seconds: int = 300
    retry_failed: bool = False
    max_retries: int = 1
    coverage_enabled: bool = False
    real_llm_enabled: bool = False
    environment: str = "test"
    log_level: str = "INFO"
    output_format: str = "json"


class BaseTestInterface:
    """Base interface for all test components."""
    
    def initialize(self) -> None:
        """Initialize the test component."""
        pass
    
    def cleanup(self) -> None:
        """Cleanup test component resources."""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the component."""
        return {"initialized": True}


class BaseTestComponent(BaseTestInterface):
    """Base test component with common functionality."""
    
    def __init__(self):
        self._initialized = False
        self._status = "created"
    
    def initialize(self) -> None:
        """Initialize the test component."""
        self._initialized = True
        self._status = "initialized"
    
    def cleanup(self) -> None:
        """Cleanup test component resources."""
        self._initialized = False
        self._status = "cleaned_up"
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the component."""
        return {
            "initialized": self._initialized,
            "status": self._status
        }


class ServiceStatus(str, Enum):
    """Service status enumeration."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ServiceConfig:
    """Service configuration for testing."""
    name: str
    image: str
    ports: Dict[str, int] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    volumes: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    health_check: Optional[str] = None
    timeout: int = 30


@dataclass
class TestEnvironment:
    """Test environment configuration."""
    name: str
    services: List[ServiceConfig] = field(default_factory=list)
    networks: List[str] = field(default_factory=list)
    volumes: Dict[str, str] = field(default_factory=dict)
    environment_vars: Dict[str, str] = field(default_factory=dict)


class IContainerManager(Protocol):
    """Protocol for container managers."""
    
    async def start_service(self, service_config: ServiceConfig) -> bool:
        """Start a service container."""
        ...
    
    async def stop_service(self, service_name: str) -> bool:
        """Stop a service container.""" 
        ...
    
    async def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get service status."""
        ...
    
    async def health_check(self, service_name: str) -> bool:
        """Check service health."""
        ...


class TestRunner(Protocol):
    """Protocol for test runners."""
    
    def run_tests(self, test_paths: List[str]) -> List[TestResult]:
        """Run tests and return results."""
        ...
    
    def setup(self) -> None:
        """Setup test runner."""
        ...
    
    def teardown(self) -> None:
        """Cleanup test runner."""
        ...


class TestReporter(Protocol):
    """Protocol for test reporters."""
    
    def generate_report(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate test report from results."""
        ...
    
    def save_report(self, report: Dict[str, Any], output_path: str) -> None:
        """Save report to file."""
        ...


class BaseTestRunner(BaseTestInterface):
    """Base implementation for test runners."""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize the test runner."""
        self._initialized = True
    
    def cleanup(self) -> None:
        """Cleanup test runner resources."""
        self._initialized = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the runner."""
        return {
            "initialized": self._initialized,
            "config": self.config.dict() if hasattr(self.config, 'dict') else str(self.config)
        }
    
    @abstractmethod
    def execute_test(self, test_path: str) -> TestResult:
        """Execute a single test."""
        pass


class BaseTestReporter(BaseTestInterface):
    """Base implementation for test reporters."""
    
    def __init__(self, output_format: str = "json"):
        self.output_format = output_format
        self._reports: List[Dict[str, Any]] = []
    
    def initialize(self) -> None:
        """Initialize the reporter."""
        self._reports.clear()
    
    def cleanup(self) -> None:
        """Cleanup reporter resources."""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the reporter."""
        return {
            "output_format": self.output_format,
            "reports_generated": len(self._reports)
        }
    
    def add_report(self, report: Dict[str, Any]) -> None:
        """Add a report to the collection."""
        self._reports.append(report)
    
    def get_reports(self) -> List[Dict[str, Any]]:
        """Get all generated reports."""
        return self._reports.copy()


# Export commonly used interfaces
__all__ = [
    "TestRunner",
    "TestReporter", 
    "BaseTestRunner",
    "BaseTestReporter",
    "BaseTestInterface",
    "BaseTestComponent",
    "ServiceStatus",
    "ServiceConfig",
    "TestEnvironment",
    "IContainerManager",
    "TestExecutionState",
    "TestCategory",
    "TestResult",
    "TestConfiguration"
]