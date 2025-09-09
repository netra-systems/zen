"""
Unified Test Framework: Central coordination for all testing activities.

This module provides unified interfaces and base classes for coordinating
test execution across the entire Netra platform.

Business Value Justification (BVJ):
- Segment: Platform/Internal (Development Velocity) 
- Business Goal: Reduce test execution time by 50%, improve CI/CD reliability
- Value Impact: Faster feedback loops enable rapid feature delivery
- Revenue Impact: 20% faster feature delivery = $15K additional MRR potential
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, TypedDict, Union

from pydantic import BaseModel


class TestExecutionState(str, Enum):
    """Test execution state enumeration."""
    __test__ = False  # Explicitly tell pytest not to collect this class
    
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed" 
    SKIPPED = "skipped"
    ERROR = "error"


class ExecutionCategory(str, Enum):
    """Test execution category classification for pytest organization."""
    __test__ = False  # Explicitly tell pytest not to collect this class
    
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"
    AGENTS = "agents"
    CRITICAL = "critical"


# Backward compatibility aliases - DEPRECATED: Use ExecutionCategory instead
TestExecutionCategory = ExecutionCategory
CategoryType = ExecutionCategory


@dataclass
class TestResult:
    """Individual test execution result."""
    test_id: str
    name: str
    category: ExecutionCategory
    state: TestExecutionState
    duration: float = 0.0
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class TestReport(BaseModel):
    """Unified test execution report."""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    timestamp: datetime = datetime.now(UTC)
    results: List[TestResult] = []
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_tests == 0:
            return 100.0
        return (self.passed / self.total_tests) * 100.0


class TestExecutor(Protocol):
    """Protocol for test executors."""
    
    def execute(self, tests: List[str]) -> TestReport:
        """Execute a list of tests and return results."""
        ...
    
    def can_execute(self, test_path: str) -> bool:
        """Check if executor can handle the given test."""
        ...


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
    
    # Category-specific settings
    enable_integration_tests: bool = True
    enable_e2e_tests: bool = False
    enable_performance_tests: bool = False
    enable_agent_tests: bool = True
    
    # Resource limits
    memory_limit_mb: int = 2048
    cpu_limit_percent: int = 80


class TestDiscovery:
    """Test discovery and categorization service."""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self._discovered_tests: Dict[ExecutionCategory, List[str]] = {}
    
    def discover_tests(self, paths: List[str]) -> Dict[ExecutionCategory, List[str]]:
        """Discover and categorize tests from given paths."""
        discovered = {category: [] for category in ExecutionCategory}
        
        for path in paths:
            category = self._categorize_test(path)
            discovered[category].append(path)
        
        self._discovered_tests = discovered
        return discovered
    
    def _categorize_test(self, test_path: str) -> ExecutionCategory:
        """Categorize a test based on its path and content."""
        path_lower = test_path.lower()
        
        if "integration" in path_lower:
            return ExecutionCategory.INTEGRATION
        elif "e2e" in path_lower or "end_to_end" in path_lower:
            return ExecutionCategory.E2E
        elif "performance" in path_lower or "perf" in path_lower:
            return ExecutionCategory.PERFORMANCE
        elif "security" in path_lower or "sec" in path_lower:
            return ExecutionCategory.SECURITY
        elif "agent" in path_lower:
            return ExecutionCategory.AGENTS
        elif "critical" in path_lower:
            return ExecutionCategory.CRITICAL
        else:
            return ExecutionCategory.UNIT
    
    def get_tests_by_category(self, category: ExecutionCategory) -> List[str]:
        """Get all tests in a specific category."""
        return self._discovered_tests.get(category, [])


class UnifiedTestOrchestrator:
    """Central orchestrator for all test execution."""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.discovery = TestDiscovery(config)
        self._executors: List[TestExecutor] = []
        self._results: List[TestResult] = []
    
    def add_executor(self, executor: TestExecutor) -> None:
        """Add a test executor to the orchestrator."""
        self._executors.append(executor)
    
    def execute_all(self, test_paths: List[str]) -> TestReport:
        """Execute all tests and return unified report."""
        discovered = self.discovery.discover_tests(test_paths)
        all_results = []
        
        for category, tests in discovered.items():
            if not self._should_execute_category(category):
                continue
                
            for test in tests:
                executor = self._find_executor(test)
                if executor:
                    report = executor.execute([test])
                    all_results.extend(report.results)
        
        return self._generate_report(all_results)
    
    def execute_category(self, category: ExecutionCategory, test_paths: List[str]) -> TestReport:
        """Execute tests in a specific category."""
        discovered = self.discovery.discover_tests(test_paths)
        category_tests = discovered.get(category, [])
        
        if not self._should_execute_category(category):
            return TestReport(total_tests=0)
        
        all_results = []
        for test in category_tests:
            executor = self._find_executor(test)
            if executor:
                report = executor.execute([test])
                all_results.extend(report.results)
        
        return self._generate_report(all_results)
    
    def _should_execute_category(self, category: ExecutionCategory) -> bool:
        """Check if category should be executed based on config."""
        if category == ExecutionCategory.INTEGRATION:
            return self.config.enable_integration_tests
        elif category == ExecutionCategory.E2E:
            return self.config.enable_e2e_tests
        elif category == ExecutionCategory.PERFORMANCE:
            return self.config.enable_performance_tests
        elif category == ExecutionCategory.AGENTS:
            return self.config.enable_agent_tests
        else:
            return True  # Unit, security, critical always enabled
    
    def _find_executor(self, test_path: str) -> Optional[TestExecutor]:
        """Find appropriate executor for a test."""
        for executor in self._executors:
            if executor.can_execute(test_path):
                return executor
        return None
    
    def _generate_report(self, results: List[TestResult]) -> TestReport:
        """Generate unified test report from results."""
        total = len(results)
        passed = sum(1 for r in results if r.state == TestExecutionState.PASSED)
        failed = sum(1 for r in results if r.state == TestExecutionState.FAILED)
        skipped = sum(1 for r in results if r.state == TestExecutionState.SKIPPED)
        errors = sum(1 for r in results if r.state == TestExecutionState.ERROR)
        duration = sum(r.duration for r in results)
        
        return TestReport(
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration,
            results=results
        )


# Base interfaces for backward compatibility
class BaseInterfaces:
    """Collection of base interfaces for test framework."""
    
    TestExecutor = TestExecutor
    BaseTestInterface = BaseTestInterface
    
    @staticmethod
    def create_test_result(test_id: str, name: str, passed: bool, duration: float = 0.0) -> TestResult:
        """Create a test result with basic information."""
        state = TestExecutionState.PASSED if passed else TestExecutionState.FAILED
        return TestResult(
            test_id=test_id,
            name=name,
            category=ExecutionCategory.UNIT,
            state=state,
            duration=duration
        )


# Commonly used aliases
base_interfaces = BaseInterfaces()

# CRITICAL FIX: Avoid pytest collection warning by not importing TestCategory class
# Comment out to prevent pytest from collecting TestCategory as a test class
# from test_framework.category_system import TestCategory

# Provide backward compatibility alias to prevent import errors
TestCategory = CategoryType  # Backward compatibility alias

# Export all main classes
__all__ = [
    'TestExecutionState',
    'ExecutionCategory',
    'TestExecutionCategory',  # Deprecated alias for backward compatibility
    'CategoryType',  # Deprecated alias for backward compatibility
    'TestResult', 
    'TestReport',
    'TestExecutor',
    'BaseTestInterface',
    'TestConfiguration',
    'TestDiscovery',
    'UnifiedTestOrchestrator',
    'BaseInterfaces',
    'base_interfaces',
    'TestCategory'  # For backward compatibility
]