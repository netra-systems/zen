"""
Single Source of Truth (SSOT) Orchestration Enums and Data Classes

This module consolidates ALL orchestration enums, constants, and data classes
into a single canonical location, eliminating SSOT violations across the system.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
Ensures consistent enum definitions, prevents duplication bugs, and provides single update point.

CRITICAL: This is the ONLY source for orchestration enums and data classes in the system.
ALL orchestration modules must import from this module to maintain SSOT compliance.

CONSOLIDATED Enums:
- BackgroundTaskStatus: Status of background E2E tasks
- E2ETestCategory: E2E test categories handled by background system
- ExecutionStrategy: Category execution strategies within layers
- ProgressOutputMode: Output modes for progress streaming
- ProgressEventType: Extended progress event types for streaming
- OrchestrationMode: Master orchestration execution modes
- ResourceStatus: Resource management status types
- ServiceStatus: Service dependency status types
- ServiceAvailability: Service availability states for integration testing

Previous Locations (Now CONSOLIDATED):
- test_framework/orchestration/background_e2e_agent.py (BackgroundTaskStatus, E2ETestCategory)
- test_framework/orchestration/background_e2e_manager.py (BackgroundTaskStatus, E2ETestCategory)
- test_framework/orchestration/layer_execution_agent.py (ExecutionStrategy)
- test_framework/orchestration/layer_execution_manager.py (ExecutionStrategy)
- test_framework/orchestration/progress_streaming_agent.py (ProgressOutputMode, ProgressEventType)
- test_framework/orchestration/progress_streaming_manager.py (ProgressOutputMode, ProgressEventType)
- test_framework/service_abstraction/integration_service_abstraction.py (ServiceAvailability)
- test_framework/service_aware_testing.py (ServiceAvailability)
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ========== Background E2E Task Management ==========

class BackgroundTaskStatus(Enum):
    """
    Status of background E2E tasks.
    
    CONSOLIDATED from:
    - test_framework/orchestration/background_e2e_agent.py:77
    - test_framework/orchestration/background_e2e_manager.py:77
    
    This enum tracks the lifecycle status of long-running background E2E tests
    through their execution pipeline.
    """
    QUEUED = "queued"          # Task is in the execution queue
    STARTING = "starting"      # Task is being initialized
    RUNNING = "running"        # Task is actively executing
    COMPLETED = "completed"    # Task finished successfully
    FAILED = "failed"          # Task failed with errors
    CANCELLED = "cancelled"    # Task was manually cancelled
    TIMEOUT = "timeout"        # Task exceeded time limit


class E2ETestCategory(Enum):
    """
    E2E test categories handled by background orchestration system.
    
    CONSOLIDATED from:
    - test_framework/orchestration/background_e2e_agent.py:88
    - test_framework/orchestration/background_e2e_manager.py:88
    
    These categories define different types of end-to-end tests with varying
    execution requirements and resource usage patterns.
    """
    CYPRESS = "cypress"                # Cypress E2E tests (20+ minutes, requires full stack)
    E2E = "e2e"                       # Full end-to-end user journey tests (30+ minutes)
    PERFORMANCE = "performance"        # Load and performance tests (30+ minutes)
    E2E_CRITICAL = "e2e_critical"     # Critical E2E tests that can run in foreground (5 minutes)


# ========== Layer Execution Strategies ==========

class ExecutionStrategy(Enum):
    """
    Category execution strategies within orchestration layers.
    
    CONSOLIDATED from:
    - test_framework/orchestration/layer_execution_agent.py:82
    - test_framework/orchestration/layer_execution_manager.py:85
    
    These strategies define how test categories within a layer should be executed
    to optimize for speed, resource usage, and reliability.
    """
    SEQUENTIAL = "sequential"                   # Execute categories one after another
    PARALLEL_UNLIMITED = "parallel_unlimited"  # Execute all categories in parallel
    PARALLEL_LIMITED = "parallel_limited"      # Execute with limited parallelism
    HYBRID_SMART = "hybrid_smart"              # Intelligent hybrid strategy based on category characteristics


# ========== Progress Streaming and Output ==========

class ProgressOutputMode(Enum):
    """
    Output modes for progress streaming across orchestration system.
    
    CONSOLIDATED from:
    - test_framework/orchestration/progress_streaming_agent.py:75
    - test_framework/orchestration/progress_streaming_manager.py:75
    
    These modes control how progress information is formatted and delivered
    during orchestration execution.
    """
    CONSOLE = "console"        # Human-readable console output with colors and formatting
    JSON = "json"             # Structured JSON output for programmatic consumption
    WEBSOCKET = "websocket"    # Real-time WebSocket streaming for UI integration
    LOG = "log"               # Structured logging format for persistent storage
    SILENT = "silent"         # Minimal output, errors only


class ProgressEventType(Enum):
    """
    Extended progress event types for orchestration progress streaming.
    
    CONSOLIDATED from:
    - test_framework/orchestration/progress_streaming_agent.py:84
    - test_framework/orchestration/progress_streaming_manager.py:84
    
    These events provide fine-grained progress tracking throughout the
    orchestration execution pipeline.
    """
    # Layer-level events
    LAYER_STARTED = "layer_started"
    LAYER_COMPLETED = "layer_completed"
    LAYER_FAILED = "layer_failed"
    LAYER_SKIPPED = "layer_skipped"
    LAYER_PROGRESS = "layer_progress"
    
    # Category-level events
    CATEGORY_STARTED = "category_started"
    CATEGORY_COMPLETED = "category_completed"
    CATEGORY_FAILED = "category_failed"
    CATEGORY_SKIPPED = "category_skipped"
    CATEGORY_PROGRESS = "category_progress"
    
    # Test-level events
    TEST_STARTED = "test_started"
    TEST_COMPLETED = "test_completed"
    TEST_FAILED = "test_failed"
    TEST_SKIPPED = "test_skipped"
    
    # Background E2E events
    BACKGROUND_TASK_QUEUED = "background_task_queued"
    BACKGROUND_TASK_STARTED = "background_task_started"
    BACKGROUND_TASK_PROGRESS = "background_task_progress"
    BACKGROUND_TASK_COMPLETED = "background_task_completed"
    BACKGROUND_TASK_FAILED = "background_task_failed"
    
    # System events
    ORCHESTRATION_STARTED = "orchestration_started"
    ORCHESTRATION_COMPLETED = "orchestration_completed"
    ORCHESTRATION_FAILED = "orchestration_failed"
    SERVICE_DEPENDENCY_CHECK = "service_dependency_check"
    RESOURCE_ALLOCATION = "resource_allocation"
    
    # Error and warning events
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


# ========== Master Orchestration Modes ==========

class OrchestrationMode(Enum):
    """
    Master orchestration execution modes.

    These modes define different orchestration strategies that balance
    execution time, resource usage, and test coverage.
    """
    FAST_FEEDBACK = "fast_feedback"    # Quick 2-minute feedback cycle (smoke, unit)
    NIGHTLY = "nightly"                # Full layered execution (default comprehensive mode)
    BACKGROUND = "background"          # Background E2E only (long-running tests)
    HYBRID = "hybrid"                  # Foreground layers + background E2E
    LEGACY = "legacy"                  # Legacy category-based execution
    CUSTOM = "custom"                  # Custom layer configuration


class DockerOrchestrationMode(Enum):
    """
    Docker orchestration modes for test environment management.

    These modes define how Docker environments should be orchestrated
    during test execution, providing different levels of isolation and
    resource usage patterns.

    SSOT Enhancement: Centralizes Docker orchestration mode definitions
    that were previously scattered across different orchestration modules.
    """
    # Environment Management Modes
    DEDICATED = "dedicated"            # Each test run gets dedicated environment
    SHARED = "shared"                  # Multiple test runs share environment
    PERSISTENT = "persistent"          # Long-lived environment across sessions

    # Execution Strategy Modes
    PARALLEL = "parallel"              # Multiple Docker environments in parallel
    SEQUENTIAL = "sequential"          # One Docker environment at a time
    BACKGROUND = "background"          # Docker management in background

    # Resource Management Modes
    MINIMAL = "minimal"                # Minimal Docker resource allocation
    STANDARD = "standard"              # Standard Docker resource allocation
    INTENSIVE = "intensive"            # High Docker resource allocation for heavy tests

    # Special Modes
    CLEANUP_ONLY = "cleanup_only"      # Only perform cleanup operations
    VALIDATION_ONLY = "validation_only"  # Only validate Docker setup
    DISABLED = "disabled"              # Docker orchestration disabled


# ========== Resource and Service Management ==========

class ResourceStatus(Enum):
    """
    Resource management status types for orchestration system.
    
    Tracks the status of computational resources (CPU, memory, disk, network)
    throughout orchestration execution.
    """
    AVAILABLE = "available"        # Resource is available for allocation
    ALLOCATED = "allocated"        # Resource is currently allocated to a task
    EXHAUSTED = "exhausted"        # Resource is fully utilized
    RESERVED = "reserved"          # Resource is reserved for high-priority tasks
    ERROR = "error"               # Resource is in an error state
    MONITORING = "monitoring"      # Resource usage is being monitored
    CLEANUP = "cleanup"           # Resource is being cleaned up after use


class ServiceStatus(Enum):
    """
    Service dependency status types for orchestration coordination.
    
    Tracks the status of external service dependencies (databases, APIs, etc.)
    required by different orchestration layers and categories.
    """
    HEALTHY = "healthy"            # Service is healthy and responsive
    UNHEALTHY = "unhealthy"        # Service is not responding properly
    STARTING = "starting"          # Service is in startup phase
    STOPPING = "stopping"          # Service is shutting down
    UNAVAILABLE = "unavailable"    # Service is not available
    DEGRADED = "degraded"          # Service is available but performance is degraded
    MAINTENANCE = "maintenance"    # Service is in maintenance mode
    UNKNOWN = "unknown"           # Service status cannot be determined


class ServiceAvailability(Enum):
    """
    Service availability states for integration testing.
    
    CONSOLIDATED from:
    - test_framework/service_abstraction/integration_service_abstraction.py:45
    - test_framework/service_aware_testing.py:48
    
    This enum provides standardized availability states used throughout the test
    framework for service availability detection and testing logic.
    """
    AVAILABLE = "available"        # Service is available for testing
    UNAVAILABLE = "unavailable"    # Service is not available
    DEGRADED = "degraded"          # Service is available but with reduced functionality
    UNKNOWN = "unknown"           # Service availability status cannot be determined


# ========== Data Classes for Complex Types ==========

@dataclass
class LayerExecutionResult:
    """
    Result of layer execution within orchestration system.
    
    CONSOLIDATED from various layer execution modules to provide
    consistent result reporting across all orchestration components.
    """
    layer_name: str
    execution_strategy: ExecutionStrategy
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    categories_executed: Set[str] = field(default_factory=set)
    categories_failed: Set[str] = field(default_factory=set)
    categories_skipped: Set[str] = field(default_factory=set)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_message: Optional[str] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate execution duration."""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100.0


@dataclass
class CategoryExecutionResult:
    """
    Result of category execution within orchestration layer.
    
    Provides detailed execution metrics for individual test categories
    within the orchestration system.
    """
    category_name: str
    layer_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    exit_code: Optional[int] = None
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    coverage_percentage: Optional[float] = None
    error_message: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate execution duration."""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None


@dataclass
class BackgroundTaskConfig:
    """
    Configuration for background E2E task execution.
    
    CONSOLIDATED and enhanced from background E2E modules to provide
    comprehensive configuration for long-running background tasks.
    """
    category: E2ETestCategory
    environment: str = "development"
    use_real_services: bool = True
    use_real_llm: bool = True
    timeout_minutes: int = 30
    max_retries: int = 2
    cpu_limit_percent: Optional[int] = None
    memory_limit_gb: Optional[int] = None
    priority: int = 1  # Lower numbers = higher priority
    
    # Service dependencies
    services_required: Set[str] = field(default_factory=lambda: {
        "postgres", "redis", "clickhouse", "backend", "frontend"
    })
    
    # Additional execution options
    additional_args: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    # Resource management
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "environment": self.environment,
            "use_real_services": self.use_real_services,
            "use_real_llm": self.use_real_llm,
            "timeout_minutes": self.timeout_minutes,
            "max_retries": self.max_retries,
            "cpu_limit_percent": self.cpu_limit_percent,
            "memory_limit_gb": self.memory_limit_gb,
            "priority": self.priority,
            "services_required": list(self.services_required),
            "additional_args": self.additional_args.copy(),
            "env_vars": self.env_vars.copy(),
            "resource_requirements": self.resource_requirements.copy()
        }


@dataclass
class BackgroundTaskResult:
    """
    Result of background E2E task execution.
    
    CONSOLIDATED from background E2E modules to provide comprehensive
    result tracking for long-running background tasks.
    """
    task_id: str
    category: E2ETestCategory
    status: BackgroundTaskStatus
    config: BackgroundTaskConfig
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    test_counts: Dict[str, int] = field(default_factory=dict)
    error_message: Optional[str] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    
    @property
    def success(self) -> bool:
        """Check if task completed successfully."""
        return self.status == BackgroundTaskStatus.COMPLETED and (self.exit_code == 0 if self.exit_code is not None else True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "category": self.category.value,
            "status": self.status.value,
            "config": self.config.to_dict(),
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "test_counts": self.test_counts.copy(),
            "error_message": self.error_message,
            "resource_usage": self.resource_usage.copy(),
            "retry_count": self.retry_count,
            "success": self.success
        }


@dataclass
class ProgressEvent:
    """
    Structured progress event for orchestration streaming.
    
    Provides comprehensive progress event structure for real-time
    monitoring and reporting of orchestration execution.
    """
    event_type: ProgressEventType
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    layer_name: Optional[str] = None
    category_name: Optional[str] = None
    task_id: Optional[str] = None
    message: Optional[str] = None
    level: str = "info"  # info, warning, error, debug
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data.copy(),
            "layer_name": self.layer_name,
            "category_name": self.category_name,
            "task_id": self.task_id,
            "message": self.message,
            "level": self.level
        }


# ========== Orchestration Layer Definitions ==========

class LayerType(Enum):
    """
    Types of orchestration layers with different characteristics.
    
    Defines the standard orchestration layers used in the Netra test system.
    """
    FAST_FEEDBACK = "fast_feedback"           # Quick validation (2 min) - smoke, unit
    CORE_INTEGRATION = "core_integration"     # Database, API tests (10 min) - database, api, websocket
    SERVICE_INTEGRATION = "service_integration"  # Agent workflows (20 min) - agent, e2e_critical, frontend
    E2E_BACKGROUND = "e2e_background"         # Full E2E + performance (60 min) - cypress, e2e, performance


@dataclass
class LayerDefinition:
    """
    Definition of an orchestration layer.
    
    Provides complete specification for an orchestration layer including
    categories, execution strategy, timeouts, and resource requirements.
    """
    name: str
    layer_type: LayerType
    categories: Set[str]
    execution_strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    timeout_minutes: int = 30
    max_parallel_categories: Optional[int] = None
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    service_dependencies: Set[str] = field(default_factory=set)
    environment_requirements: Dict[str, str] = field(default_factory=dict)
    
    # Execution conditions
    requires_real_services: bool = True
    requires_real_llm: bool = False
    can_run_in_parallel: bool = True
    is_background_eligible: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "layer_type": self.layer_type.value,
            "categories": list(self.categories),
            "execution_strategy": self.execution_strategy.value,
            "timeout_minutes": self.timeout_minutes,
            "max_parallel_categories": self.max_parallel_categories,
            "resource_requirements": self.resource_requirements.copy(),
            "service_dependencies": list(self.service_dependencies),
            "environment_requirements": self.environment_requirements.copy(),
            "requires_real_services": self.requires_real_services,
            "requires_real_llm": self.requires_real_llm,
            "can_run_in_parallel": self.can_run_in_parallel,
            "is_background_eligible": self.is_background_eligible
        }


# ========== Standard Layer Definitions ==========

# Pre-defined standard orchestration layers
STANDARD_LAYERS = {
    LayerType.FAST_FEEDBACK: LayerDefinition(
        name="fast_feedback",
        layer_type=LayerType.FAST_FEEDBACK,
        categories={"smoke", "startup", "unit"},
        execution_strategy=ExecutionStrategy.PARALLEL_LIMITED,
        timeout_minutes=5,
        max_parallel_categories=3,
        requires_real_services=False,
        requires_real_llm=False,
        can_run_in_parallel=True,
        is_background_eligible=False
    ),
    
    LayerType.CORE_INTEGRATION: LayerDefinition(
        name="core_integration",
        layer_type=LayerType.CORE_INTEGRATION,
        categories={"database", "api", "websocket", "security"},
        execution_strategy=ExecutionStrategy.SEQUENTIAL,
        timeout_minutes=15,
        service_dependencies={"postgres", "redis", "backend"},
        requires_real_services=True,
        requires_real_llm=False,
        can_run_in_parallel=True,
        is_background_eligible=False
    ),
    
    LayerType.SERVICE_INTEGRATION: LayerDefinition(
        name="service_integration",
        layer_type=LayerType.SERVICE_INTEGRATION,
        categories={"agent", "e2e_critical", "frontend", "integration"},
        execution_strategy=ExecutionStrategy.HYBRID_SMART,
        timeout_minutes=25,
        max_parallel_categories=2,
        service_dependencies={"postgres", "redis", "backend", "frontend"},
        requires_real_services=True,
        requires_real_llm=True,
        can_run_in_parallel=False,
        is_background_eligible=False
    ),
    
    LayerType.E2E_BACKGROUND: LayerDefinition(
        name="e2e_background",
        layer_type=LayerType.E2E_BACKGROUND,
        categories={"cypress", "e2e", "performance"},
        execution_strategy=ExecutionStrategy.SEQUENTIAL,
        timeout_minutes=90,
        service_dependencies={"postgres", "redis", "clickhouse", "backend", "frontend"},
        requires_real_services=True,
        requires_real_llm=True,
        can_run_in_parallel=False,
        is_background_eligible=True
    )
}


# ========== SSOT Import Re-exports ==========

# Import critical classes from their actual locations and re-export through SSOT
try:
    from netra_backend.app.websocket_core.manager import HeartbeatConfig as _HeartbeatConfig
    HeartbeatConfig = _HeartbeatConfig
    _heartbeat_config_available = True
except ImportError as e:
    # Create placeholder if import fails
    class HeartbeatConfig:
        """Placeholder HeartbeatConfig when actual class unavailable."""
        def __init__(self, **kwargs):
            pass

        @classmethod
        def for_environment(cls, env_name: str):
            return cls()

    _heartbeat_config_available = False

try:
    from netra_backend.app.services.service_mesh.retry_policy import RetryPolicy as _RetryPolicy
    RetryPolicy = _RetryPolicy
    _retry_policy_available = True
except ImportError as e:
    # Create placeholder if import fails
    class RetryPolicy:
        """Placeholder RetryPolicy when actual class unavailable."""
        def __init__(self, **kwargs):
            pass

    _retry_policy_available = False


# ========== Utility Functions ==========

def get_standard_layer(layer_type: LayerType) -> LayerDefinition:
    """
    Get a standard layer definition by type.
    
    Args:
        layer_type: Type of layer to retrieve
        
    Returns:
        LayerDefinition for the standard layer
        
    Raises:
        KeyError: If layer type is not found in standard layers
    """
    return STANDARD_LAYERS[layer_type]


def get_all_standard_layers() -> Dict[LayerType, LayerDefinition]:
    """
    Get all standard layer definitions.
    
    Returns:
        Dictionary mapping layer types to definitions
    """
    return STANDARD_LAYERS.copy()


def create_custom_layer(name: str, categories: Set[str], **kwargs) -> LayerDefinition:
    """
    Create a custom layer definition.
    
    Args:
        name: Name of the custom layer
        categories: Set of test categories for the layer
        **kwargs: Additional layer configuration options
        
    Returns:
        Custom LayerDefinition instance
    """
    # Set defaults for custom layers
    defaults = {
        "layer_type": LayerType.FAST_FEEDBACK,  # Default to fast feedback
        "execution_strategy": ExecutionStrategy.SEQUENTIAL,
        "timeout_minutes": 30,
        "requires_real_services": True,
        "requires_real_llm": False,
        "can_run_in_parallel": True,
        "is_background_eligible": False
    }
    
    # Merge with provided kwargs
    config = {**defaults, **kwargs}
    
    return LayerDefinition(
        name=name,
        categories=categories,
        **config
    )


def validate_layer_definition(layer_def: LayerDefinition) -> List[str]:
    """
    Validate a layer definition and return any issues found.
    
    Args:
        layer_def: Layer definition to validate
        
    Returns:
        List of validation issues (empty if valid)
    """
    issues = []
    
    # Check required fields
    if not layer_def.name:
        issues.append("Layer name cannot be empty")
    
    if not layer_def.categories:
        issues.append("Layer must have at least one category")
    
    # Check timeout
    if layer_def.timeout_minutes <= 0:
        issues.append("Timeout must be positive")
    
    # Check parallel limits
    if (layer_def.execution_strategy in [ExecutionStrategy.PARALLEL_LIMITED] and 
        layer_def.max_parallel_categories is not None and
        layer_def.max_parallel_categories <= 0):
        issues.append("Max parallel categories must be positive when using PARALLEL_LIMITED strategy")
    
    # Check background eligibility
    if (layer_def.is_background_eligible and 
        layer_def.execution_strategy == ExecutionStrategy.PARALLEL_UNLIMITED):
        issues.append("Background-eligible layers should not use PARALLEL_UNLIMITED strategy")
    
    return issues


# Export SSOT orchestration enums and data classes
__all__ = [
    # Enums
    'BackgroundTaskStatus',
    'E2ETestCategory',
    'ExecutionStrategy',
    'ProgressOutputMode',
    'ProgressEventType',
    'OrchestrationMode',
    'ResourceStatus',
    'ServiceStatus',
    'ServiceAvailability',
    'LayerType',

    # Data Classes
    'LayerExecutionResult',
    'CategoryExecutionResult',
    'BackgroundTaskConfig',
    'BackgroundTaskResult',
    'ProgressEvent',
    'LayerDefinition',

    # SSOT Re-exports
    'HeartbeatConfig',
    'RetryPolicy',

    # Constants
    'STANDARD_LAYERS',

    # Utility Functions
    'get_standard_layer',
    'get_all_standard_layers',
    'create_custom_layer',
    'validate_layer_definition'
]