#!/usr/bin/env python3
"""
Layered Test Execution System - Comprehensive test layer management
Provides structured, dependency-aware test execution with resource management
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any, Tuple
import yaml
import logging

from test_framework.category_system import TestCategory, CategoryPriority


class LayerExecutionMode(Enum):
    """Layer execution modes"""
    SEQUENTIAL = "sequential"           # Run categories one after another
    PARALLEL = "parallel"              # Run all categories simultaneously
    HYBRID = "hybrid"                  # Mix of parallel and sequential based on dependencies


class FailFastStrategy(Enum):
    """Fail-fast strategies per layer"""
    IMMEDIATE = "immediate"            # Stop immediately on any failure
    CATEGORY = "category"              # Stop layer when a category fails
    LAYER = "layer"                    # Complete layer, then decide
    DISABLED = "disabled"              # Never stop, run all tests


class LayerExecutionStatus(Enum):
    """Layer execution status"""
    PENDING = "pending"                # Not started yet
    STARTING = "starting"              # Initializing resources
    RUNNING = "running"                # Executing tests
    BACKGROUND = "background"          # Running in background
    COMPLETED = "completed"            # Successfully completed
    FAILED = "failed"                  # Failed with errors
    SKIPPED = "skipped"                # Skipped due to dependencies
    TIMEOUT = "timeout"                # Exceeded time limits
    CANCELLED = "cancelled"            # Cancelled by user or system


@dataclass
class ResourceLimits:
    """Resource limits for layer execution"""
    max_memory_mb: int = 1024
    max_cpu_percent: int = 70
    max_parallel_instances: int = 4


@dataclass 
class ResourceRequirements:
    """Resource requirements for test categories"""
    requires_postgresql: bool = False
    requires_redis: bool = False
    requires_backend_service: bool = False
    requires_auth_service: bool = False
    requires_frontend_service: bool = False
    requires_real_llm: bool = False
    requires_real_services: bool = False
    requires_websocket_server: bool = False
    requires_node_runtime: bool = False
    requires_frontend_build: bool = False
    min_memory_mb: int = 64
    dedicated_resources: bool = False


@dataclass
class TestFilters:
    """Test filters for category execution"""
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)


@dataclass
class SuccessCriteria:
    """Success criteria for layer completion"""
    min_pass_rate: float = 0.95
    max_failures: int = 5
    critical_tests_must_pass: bool = True
    allow_partial_success: bool = False


@dataclass
class LLMRequirements:
    """LLM requirements for layer execution"""
    mode: str = "mock"  # real, mock, hybrid
    timeout_seconds: int = 60
    fallback_to_mock: bool = True


@dataclass
class CategoryConfig:
    """Configuration for a category within a layer"""
    name: str
    timeout_seconds: int = 300
    max_parallel_instances: int = 2
    priority_order: int = 1
    resource_requirements: ResourceRequirements = field(default_factory=ResourceRequirements)
    filters: TestFilters = field(default_factory=TestFilters)


@dataclass
class TestLayer:
    """Test layer with execution configuration and categories"""
    name: str
    description: str
    priority: int = 1
    execution_order: int = 1
    max_duration_minutes: int = 10
    execution_mode: LayerExecutionMode = LayerExecutionMode.PARALLEL
    fail_fast: bool = False
    background_execution: bool = False
    
    # Resource management
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    
    # Categories in this layer
    categories: List[CategoryConfig] = field(default_factory=list)
    
    # Dependencies and conflicts
    dependencies: Set[str] = field(default_factory=set)
    conflicts: Set[str] = field(default_factory=set)
    
    # Success criteria
    success_criteria: SuccessCriteria = field(default_factory=SuccessCriteria)
    
    # Service requirements
    required_services: Set[str] = field(default_factory=set)
    llm_requirements: LLMRequirements = field(default_factory=LLMRequirements)
    
    # Environment-specific overrides
    environment_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Runtime state
    status: LayerExecutionStatus = LayerExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LayerExecutionPlan:
    """Execution plan for all test layers"""
    layers: List[TestLayer] = field(default_factory=list)
    execution_sequence: List[List[str]] = field(default_factory=list)  # Phases of parallel execution
    total_estimated_duration: timedelta = field(default_factory=lambda: timedelta(0))
    service_startup_order: List[str] = field(default_factory=list)
    resource_allocation: Dict[str, ResourceLimits] = field(default_factory=dict)


@dataclass
class ExecutionConfig:
    """Global execution configuration for the layer system"""
    layer_execution_mode: str = "waterfall_with_background"
    global_timeout_minutes: int = 90
    layer_startup_timeout_seconds: int = 30
    inter_layer_delay_seconds: int = 5
    max_global_parallel_tests: int = 8
    max_memory_usage_mb: int = 6144
    max_cpu_usage_percent: int = 90
    fail_fast_strategy: Dict[str, FailFastStrategy] = field(default_factory=dict)
    resource_conflict_resolution: str = "priority_based"
    background_execution_enabled: bool = True
    max_background_layers: int = 1
    background_layers: Set[str] = field(default_factory=set)


@dataclass
class LayerExecutionResult:
    """Result of layer execution"""
    layer_name: str
    status: LayerExecutionStatus
    start_time: datetime
    end_time: datetime
    duration: timedelta
    category_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    success_rate: float = 0.0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_message: Optional[str] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)


class LayerSystem:
    """Comprehensive layered test execution system"""
    
    def __init__(self, project_root: Path, config_path: Optional[Path] = None):
        self.project_root = project_root
        self.config_path = config_path or (project_root / "test_framework" / "config" / "test_layers.yaml")
        
        # Configuration
        self.layers: Dict[str, TestLayer] = {}
        self.execution_config: ExecutionConfig = ExecutionConfig()
        self.service_dependencies: Dict[str, Dict[str, Any]] = {}
        
        # Runtime state
        self.current_execution_plan: Optional[LayerExecutionPlan] = None
        self.execution_results: Dict[str, LayerExecutionResult] = {}
        self.background_tasks: Dict[str, asyncio.Task] = {}
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self._load_configuration()
    
    def _load_configuration(self):
        """Load layer configuration from YAML file"""
        if not self.config_path.exists():
            self.logger.warning(f"Layer configuration file not found: {self.config_path}")
            self._create_default_configuration()
            return
        
        try:
            with open(self.config_path) as f:
                config_data = yaml.safe_load(f)
            
            self._parse_configuration(config_data)
            self.logger.info(f"Loaded layer configuration from {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load layer configuration: {e}")
            self._create_default_configuration()
    
    def _parse_configuration(self, config_data: Dict[str, Any]):
        """Parse configuration data into layer objects"""
        # Parse layers
        layers_data = config_data.get("layers", {})
        for layer_id, layer_config in layers_data.items():
            layer = self._parse_layer_config(layer_id, layer_config)
            self.layers[layer_id] = layer
        
        # Parse execution configuration
        execution_data = config_data.get("execution_config", {})
        self.execution_config = ExecutionConfig(
            layer_execution_mode=execution_data.get("layer_execution_mode", "waterfall_with_background"),
            global_timeout_minutes=execution_data.get("global_timeout_minutes", 90),
            layer_startup_timeout_seconds=execution_data.get("layer_startup_timeout_seconds", 30),
            inter_layer_delay_seconds=execution_data.get("inter_layer_delay_seconds", 5),
            max_global_parallel_tests=execution_data.get("max_global_parallel_tests", 8),
            max_memory_usage_mb=execution_data.get("max_memory_usage_mb", 6144),
            max_cpu_usage_percent=execution_data.get("max_cpu_usage_percent", 90),
            resource_conflict_resolution=execution_data.get("resource_conflict_resolution", "priority_based"),
            background_execution_enabled=execution_data.get("background_execution", {}).get("enabled", True),
            max_background_layers=execution_data.get("background_execution", {}).get("max_background_layers", 1),
            background_layers=set(execution_data.get("background_execution", {}).get("background_layers", []))
        )
        
        # Parse fail-fast strategies
        fail_fast_data = execution_data.get("fail_fast_strategy", {})
        for layer_name, strategy_str in fail_fast_data.items():
            try:
                self.execution_config.fail_fast_strategy[layer_name] = FailFastStrategy(strategy_str)
            except ValueError:
                self.logger.warning(f"Invalid fail-fast strategy for layer {layer_name}: {strategy_str}")
        
        # Parse service dependencies
        self.service_dependencies = config_data.get("service_dependencies", {})
    
    def _parse_layer_config(self, layer_id: str, layer_config: Dict[str, Any]) -> TestLayer:
        """Parse individual layer configuration"""
        # Parse resource limits
        resource_limits_data = layer_config.get("resource_limits", {})
        resource_limits = ResourceLimits(
            max_memory_mb=resource_limits_data.get("max_memory_mb", 1024),
            max_cpu_percent=resource_limits_data.get("max_cpu_percent", 70),
            max_parallel_instances=resource_limits_data.get("max_parallel_instances", 4)
        )
        
        # Parse categories
        categories = []
        for category_data in layer_config.get("categories", []):
            category = self._parse_category_config(category_data)
            categories.append(category)
        
        # Parse success criteria
        success_data = layer_config.get("success_criteria", {})
        success_criteria = SuccessCriteria(
            min_pass_rate=success_data.get("min_pass_rate", 0.95),
            max_failures=success_data.get("max_failures", 5),
            critical_tests_must_pass=success_data.get("critical_tests_must_pass", True),
            allow_partial_success=success_data.get("allow_partial_success", False)
        )
        
        # Parse LLM requirements
        llm_data = layer_config.get("llm_requirements", {})
        llm_requirements = LLMRequirements(
            mode=llm_data.get("mode", "mock"),
            timeout_seconds=llm_data.get("timeout_seconds", 60),
            fallback_to_mock=llm_data.get("fallback_to_mock", True)
        )
        
        # Parse execution mode
        execution_mode_str = layer_config.get("execution_mode", "parallel")
        try:
            execution_mode = LayerExecutionMode(execution_mode_str)
        except ValueError:
            execution_mode = LayerExecutionMode.PARALLEL
        
        return TestLayer(
            name=layer_config["name"],
            description=layer_config["description"],
            priority=layer_config.get("priority", 1),
            execution_order=layer_config["execution_order"],
            max_duration_minutes=layer_config["max_duration_minutes"],
            execution_mode=execution_mode,
            fail_fast=layer_config.get("fail_fast", False),
            background_execution=layer_config.get("background_execution", False),
            resource_limits=resource_limits,
            categories=categories,
            dependencies=set(layer_config.get("dependencies", [])),
            conflicts=set(layer_config.get("conflicts", [])),
            success_criteria=success_criteria,
            required_services=set(layer_config.get("required_services", [])),
            llm_requirements=llm_requirements,
            environment_overrides=layer_config.get("environment_overrides", {})
        )
    
    def _parse_category_config(self, category_data: Dict[str, Any]) -> CategoryConfig:
        """Parse category configuration within a layer"""
        # Parse resource requirements
        resource_req_data = category_data.get("resource_requirements", {})
        resource_requirements = ResourceRequirements(
            requires_postgresql=resource_req_data.get("requires_postgresql", False),
            requires_redis=resource_req_data.get("requires_redis", False),
            requires_backend_service=resource_req_data.get("requires_backend_service", False),
            requires_auth_service=resource_req_data.get("requires_auth_service", False),
            requires_frontend_service=resource_req_data.get("requires_frontend_service", False),
            requires_real_llm=resource_req_data.get("requires_real_llm", False),
            requires_real_services=resource_req_data.get("requires_real_services", False),
            requires_websocket_server=resource_req_data.get("requires_websocket_server", False),
            requires_node_runtime=resource_req_data.get("requires_node_runtime", False),
            requires_frontend_build=resource_req_data.get("requires_frontend_build", False),
            min_memory_mb=resource_req_data.get("min_memory_mb", 64),
            dedicated_resources=resource_req_data.get("dedicated_resources", False)
        )
        
        # Parse filters
        filters_data = category_data.get("filters", {})
        filters = TestFilters(
            include_patterns=filters_data.get("include_patterns", []),
            exclude_patterns=filters_data.get("exclude_patterns", [])
        )
        
        return CategoryConfig(
            name=category_data["name"],
            timeout_seconds=category_data["timeout_seconds"],
            max_parallel_instances=category_data["max_parallel_instances"],
            priority_order=category_data["priority_order"],
            resource_requirements=resource_requirements,
            filters=filters
        )
    
    def _create_default_configuration(self):
        """Create default layer configuration"""
        self.logger.info("Creating default layer configuration")
        
        # Create default layers based on current category system
        self._create_default_layers()
        
        # Save default configuration
        self._save_configuration()
    
    def _create_default_layers(self):
        """Create default layers matching the requirements"""
        # Layer 1: Fast Feedback
        fast_feedback = TestLayer(
            name="Fast Feedback",
            description="Quick validation tests for immediate developer feedback",
            priority=1,
            execution_order=1,
            max_duration_minutes=2,
            execution_mode=LayerExecutionMode.SEQUENTIAL,
            fail_fast=True,
            resource_limits=ResourceLimits(max_memory_mb=512, max_cpu_percent=50, max_parallel_instances=2),
            categories=[
                CategoryConfig(name="smoke", timeout_seconds=60, max_parallel_instances=2, priority_order=1),
                CategoryConfig(name="unit", timeout_seconds=120, max_parallel_instances=4, priority_order=2)
            ]
        )
        
        # Layer 2: Core Integration
        core_integration = TestLayer(
            name="Core Integration",
            description="Database, API, and core service integration tests",
            priority=2,
            execution_order=2,
            max_duration_minutes=10,
            execution_mode=LayerExecutionMode.PARALLEL,
            dependencies={"fast_feedback"},
            resource_limits=ResourceLimits(max_memory_mb=1024, max_cpu_percent=70, max_parallel_instances=4),
            categories=[
                CategoryConfig(name="database", timeout_seconds=300, max_parallel_instances=2, priority_order=1),
                CategoryConfig(name="api", timeout_seconds=300, max_parallel_instances=3, priority_order=2),
                CategoryConfig(name="websocket", timeout_seconds=300, max_parallel_instances=2, priority_order=3),
                CategoryConfig(name="integration", timeout_seconds=600, max_parallel_instances=2, priority_order=4)
            ],
            required_services={"postgresql", "redis", "backend_service"}
        )
        
        # Layer 3: Service Integration
        service_integration = TestLayer(
            name="Service Integration",
            description="Backend integration, agent workflows, and cross-service tests",
            priority=3,
            execution_order=3,
            max_duration_minutes=20,
            execution_mode=LayerExecutionMode.HYBRID,
            dependencies={"core_integration"},
            conflicts={"performance", "cypress"},
            resource_limits=ResourceLimits(max_memory_mb=2048, max_cpu_percent=80, max_parallel_instances=3),
            categories=[
                CategoryConfig(name="agent", timeout_seconds=600, max_parallel_instances=2, priority_order=1),
                CategoryConfig(name="e2e_critical", timeout_seconds=300, max_parallel_instances=2, priority_order=2),
                CategoryConfig(name="frontend", timeout_seconds=300, max_parallel_instances=3, priority_order=3)
            ],
            required_services={"postgresql", "redis", "backend_service", "auth_service"},
            llm_requirements=LLMRequirements(mode="real", timeout_seconds=60, fallback_to_mock=False)
        )
        
        # Layer 4: E2E & Performance
        e2e_performance = TestLayer(
            name="E2E & Performance",
            description="Full end-to-end tests and performance validation",
            priority=4,
            execution_order=4,
            max_duration_minutes=60,
            execution_mode=LayerExecutionMode.SEQUENTIAL,
            background_execution=True,
            dependencies={"service_integration"},
            conflicts={"fast_feedback", "core_integration"},
            resource_limits=ResourceLimits(max_memory_mb=4096, max_cpu_percent=90, max_parallel_instances=1),
            categories=[
                CategoryConfig(name="cypress", timeout_seconds=1800, max_parallel_instances=1, priority_order=1),
                CategoryConfig(name="e2e", timeout_seconds=1800, max_parallel_instances=1, priority_order=2),
                CategoryConfig(name="performance", timeout_seconds=1800, max_parallel_instances=1, priority_order=3)
            ],
            required_services={"postgresql", "redis", "backend_service", "auth_service", "frontend_service"},
            llm_requirements=LLMRequirements(mode="real", timeout_seconds=120, fallback_to_mock=False),
            success_criteria=SuccessCriteria(min_pass_rate=0.85, max_failures=10, allow_partial_success=True)
        )
        
        # Add layers to system
        self.layers = {
            "fast_feedback": fast_feedback,
            "core_integration": core_integration, 
            "service_integration": service_integration,
            "e2e_performance": e2e_performance
        }
    
    def create_execution_plan(self, selected_layers: Optional[List[str]] = None, 
                            environment: str = "dev") -> LayerExecutionPlan:
        """Create optimized execution plan for selected layers"""
        if selected_layers is None:
            selected_layers = list(self.layers.keys())
        
        # Validate selected layers
        valid_layers = [name for name in selected_layers if name in self.layers]
        if not valid_layers:
            raise ValueError("No valid layers selected for execution")
        
        # Apply environment overrides
        self._apply_environment_overrides(environment)
        
        # Resolve dependencies and create execution sequence
        execution_sequence = self._resolve_layer_dependencies(valid_layers)
        
        # Calculate total estimated duration
        total_duration = self._calculate_total_duration(execution_sequence)
        
        # Determine service startup order
        service_startup_order = self._determine_service_startup_order(valid_layers)
        
        # Allocate resources
        resource_allocation = self._allocate_resources(valid_layers)
        
        # Create execution plan
        plan = LayerExecutionPlan(
            layers=[self.layers[name] for name in valid_layers],
            execution_sequence=execution_sequence,
            total_estimated_duration=total_duration,
            service_startup_order=service_startup_order,
            resource_allocation=resource_allocation
        )
        
        self.current_execution_plan = plan
        return plan
    
    def _apply_environment_overrides(self, environment: str):
        """Apply environment-specific overrides to layer configurations"""
        for layer in self.layers.values():
            if environment in layer.environment_overrides:
                overrides = layer.environment_overrides[environment]
                
                # Apply overrides to layer properties
                for key, value in overrides.items():
                    if hasattr(layer, key):
                        setattr(layer, key, value)
    
    def _resolve_layer_dependencies(self, selected_layers: List[str]) -> List[List[str]]:
        """Resolve layer dependencies and create execution phases"""
        # Add dependencies automatically
        all_required = self._resolve_dependencies_recursive(selected_layers)
        
        # Topological sort
        sorted_layers = self._topological_sort_layers(all_required)
        
        # Group into parallel execution phases
        return self._group_into_phases(sorted_layers)
    
    def _resolve_dependencies_recursive(self, layer_names: List[str]) -> List[str]:
        """Recursively resolve all layer dependencies"""
        resolved = set()
        to_process = set(layer_names)
        
        while to_process:
            current = to_process.pop()
            if current in resolved or current not in self.layers:
                continue
            
            resolved.add(current)
            layer = self.layers[current]
            
            # Add dependencies
            for dep in layer.dependencies:
                if dep not in resolved and dep in self.layers:
                    to_process.add(dep)
        
        return list(resolved)
    
    def _topological_sort_layers(self, layer_names: List[str]) -> List[str]:
        """Topological sort of layers based on dependencies and execution order"""
        # Build adjacency list
        graph = {name: [] for name in layer_names}
        in_degree = {name: 0 for name in layer_names}
        
        for name in layer_names:
            if name not in self.layers:
                continue
            
            layer = self.layers[name]
            for dep in layer.dependencies:
                if dep in layer_names:
                    graph[dep].append(name)
                    in_degree[name] += 1
        
        # Kahn's algorithm with priority and execution order
        queue = []
        for name in layer_names:
            if in_degree[name] == 0:
                layer = self.layers[name]
                priority = (layer.priority, layer.execution_order)
                queue.append((priority, name))
        
        queue.sort()
        result = []
        
        while queue:
            priority, current = queue.pop(0)
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    neighbor_layer = self.layers[neighbor]
                    neighbor_priority = (neighbor_layer.priority, neighbor_layer.execution_order)
                    queue.append((neighbor_priority, neighbor))
                    queue.sort()
        
        if len(result) != len(layer_names):
            raise ValueError("Circular dependency detected in layers")
        
        return result
    
    def _group_into_phases(self, sorted_layers: List[str]) -> List[List[str]]:
        """Group layers into parallel execution phases"""
        phases = []
        remaining = sorted_layers.copy()
        
        while remaining:
            current_phase = []
            conflicts_in_phase = set()
            
            for layer_name in remaining[:]:
                layer = self.layers[layer_name]
                
                # Check if dependencies are satisfied
                deps_satisfied = all(
                    dep_name in [l for phase in phases for l in phase]
                    for dep_name in layer.dependencies
                    if dep_name in sorted_layers
                )
                
                if not deps_satisfied:
                    continue
                
                # Check conflicts
                if layer.conflicts.intersection(conflicts_in_phase):
                    continue
                
                # Add to current phase
                current_phase.append(layer_name)
                conflicts_in_phase.update(layer.conflicts)
                remaining.remove(layer_name)
                
                # If layer requires sequential execution mode, don't add more to this phase
                if layer.execution_mode == LayerExecutionMode.SEQUENTIAL:
                    break
            
            if current_phase:
                phases.append(current_phase)
            elif remaining:
                # Force add one layer to prevent infinite loop
                layer_name = remaining.pop(0)
                phases.append([layer_name])
        
        return phases
    
    def _calculate_total_duration(self, execution_sequence: List[List[str]]) -> timedelta:
        """Calculate total estimated duration considering parallel execution"""
        total_duration = timedelta(0)
        
        for phase in execution_sequence:
            phase_duration = timedelta(0)
            
            for layer_name in phase:
                layer = self.layers.get(layer_name)
                if layer:
                    duration = timedelta(minutes=layer.max_duration_minutes)
                    phase_duration = max(phase_duration, duration)
            
            total_duration += phase_duration
        
        return total_duration
    
    def _determine_service_startup_order(self, layer_names: List[str]) -> List[str]:
        """Determine optimal service startup order"""
        all_services = set()
        for layer_name in layer_names:
            layer = self.layers.get(layer_name)
            if layer:
                all_services.update(layer.required_services)
        
        # Sort services based on dependencies
        service_order = []
        dependencies = self.service_dependencies
        
        # Simple topological sort for services
        remaining_services = all_services.copy()
        while remaining_services:
            # Find services with no unmet dependencies
            ready_services = []
            for service in remaining_services:
                service_deps = set(dependencies.get(service, {}).get("depends_on", []))
                unmet_deps = service_deps - set(service_order)
                if not unmet_deps:
                    ready_services.append(service)
            
            if ready_services:
                # Sort by startup timeout (faster services first)
                ready_services.sort(key=lambda s: dependencies.get(s, {}).get("startup_timeout_seconds", 30))
                service_order.extend(ready_services)
                remaining_services -= set(ready_services)
            else:
                # Add remaining services (circular dependency handling)
                service_order.extend(list(remaining_services))
                break
        
        return service_order
    
    def _allocate_resources(self, layer_names: List[str]) -> Dict[str, ResourceLimits]:
        """Allocate resources to layers based on priority and requirements"""
        allocation = {}
        
        # Sort layers by priority
        sorted_layers = sorted(
            [(name, self.layers[name]) for name in layer_names],
            key=lambda x: (x[1].priority, x[1].execution_order)
        )
        
        # Allocate resources based on strategy
        if self.execution_config.resource_conflict_resolution == "priority_based":
            # Higher priority layers get preferred resource allocation
            for layer_name, layer in sorted_layers:
                allocation[layer_name] = layer.resource_limits
        else:
            # Equal allocation
            for layer_name, layer in sorted_layers:
                allocation[layer_name] = layer.resource_limits
        
        return allocation
    
    def get_layer_categories(self, layer_name: str) -> List[str]:
        """Get category names for a specific layer"""
        layer = self.layers.get(layer_name)
        if not layer:
            return []
        
        return [category.name for category in layer.categories]
    
    def get_layer_by_category(self, category_name: str) -> Optional[TestLayer]:
        """Find which layer contains a specific category"""
        for layer in self.layers.values():
            if any(cat.name == category_name for cat in layer.categories):
                return layer
        return None
    
    def validate_configuration(self) -> List[str]:
        """Validate layer configuration and return list of issues"""
        issues = []
        
        # Check for circular dependencies
        try:
            self._resolve_layer_dependencies(list(self.layers.keys()))
        except ValueError as e:
            issues.append(f"Dependency error: {e}")
        
        # Check for conflicting configurations
        for layer_name, layer in self.layers.items():
            # Check resource limits
            if layer.resource_limits.max_memory_mb > self.execution_config.max_memory_usage_mb:
                issues.append(f"Layer {layer_name} memory limit exceeds global limit")
            
            # Check category uniqueness
            category_names = [cat.name for cat in layer.categories]
            if len(category_names) != len(set(category_names)):
                issues.append(f"Layer {layer_name} has duplicate categories")
        
        # Check category uniqueness across layers
        all_categories = []
        for layer in self.layers.values():
            all_categories.extend([cat.name for cat in layer.categories])
        
        if len(all_categories) != len(set(all_categories)):
            issues.append("Categories appear in multiple layers")
        
        return issues
    
    def _save_configuration(self):
        """Save current configuration to file"""
        config_data = {
            "metadata": {
                "version": "1.0.0",
                "description": "Auto-generated layer configuration",
                "created_at": datetime.now().isoformat(),
                "config_schema_version": "1.0"
            },
            "layers": {},
            "execution_config": {
                "layer_execution_mode": self.execution_config.layer_execution_mode,
                "global_timeout_minutes": self.execution_config.global_timeout_minutes,
                "layer_startup_timeout_seconds": self.execution_config.layer_startup_timeout_seconds,
                "inter_layer_delay_seconds": self.execution_config.inter_layer_delay_seconds,
                "max_global_parallel_tests": self.execution_config.max_global_parallel_tests,
                "max_memory_usage_mb": self.execution_config.max_memory_usage_mb,
                "max_cpu_usage_percent": self.execution_config.max_cpu_usage_percent,
                "resource_conflict_resolution": self.execution_config.resource_conflict_resolution,
                "background_execution": {
                    "enabled": self.execution_config.background_execution_enabled,
                    "max_background_layers": self.execution_config.max_background_layers,
                    "background_layers": list(self.execution_config.background_layers)
                }
            },
            "service_dependencies": self.service_dependencies
        }
        
        # Convert layers to dict format
        for layer_name, layer in self.layers.items():
            layer_dict = {
                "name": layer.name,
                "description": layer.description,
                "priority": layer.priority,
                "execution_order": layer.execution_order,
                "max_duration_minutes": layer.max_duration_minutes,
                "execution_mode": layer.execution_mode.value,
                "fail_fast": layer.fail_fast,
                "background_execution": layer.background_execution,
                "resource_limits": {
                    "max_memory_mb": layer.resource_limits.max_memory_mb,
                    "max_cpu_percent": layer.resource_limits.max_cpu_percent,
                    "max_parallel_instances": layer.resource_limits.max_parallel_instances
                },
                "categories": [],
                "dependencies": list(layer.dependencies),
                "conflicts": list(layer.conflicts),
                "required_services": list(layer.required_services),
                "success_criteria": {
                    "min_pass_rate": layer.success_criteria.min_pass_rate,
                    "max_failures": layer.success_criteria.max_failures,
                    "critical_tests_must_pass": layer.success_criteria.critical_tests_must_pass,
                    "allow_partial_success": layer.success_criteria.allow_partial_success
                },
                "llm_requirements": {
                    "mode": layer.llm_requirements.mode,
                    "timeout_seconds": layer.llm_requirements.timeout_seconds,
                    "fallback_to_mock": layer.llm_requirements.fallback_to_mock
                },
                "environment_overrides": layer.environment_overrides
            }
            
            # Add categories
            for category in layer.categories:
                category_dict = {
                    "name": category.name,
                    "timeout_seconds": category.timeout_seconds,
                    "max_parallel_instances": category.max_parallel_instances,
                    "priority_order": category.priority_order
                }
                layer_dict["categories"].append(category_dict)
            
            config_data["layers"][layer_name] = layer_dict
        
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        with open(self.config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
    
    def export_execution_plan(self, plan: LayerExecutionPlan, output_path: Path):
        """Export execution plan to JSON for analysis"""
        plan_data = {
            "layers": [layer.name for layer in plan.layers],
            "execution_sequence": plan.execution_sequence,
            "total_estimated_duration": plan.total_estimated_duration.total_seconds(),
            "service_startup_order": plan.service_startup_order,
            "resource_allocation": {
                name: {
                    "max_memory_mb": limits.max_memory_mb,
                    "max_cpu_percent": limits.max_cpu_percent,
                    "max_parallel_instances": limits.max_parallel_instances
                }
                for name, limits in plan.resource_allocation.items()
            },
            "generated_at": datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(plan_data, f, indent=2)
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of the layer system"""
        return {
            "total_layers": len(self.layers),
            "layers_by_priority": {
                f"priority_{i}": len([l for l in self.layers.values() if l.priority == i])
                for i in range(1, 6)
            },
            "execution_modes": {
                mode.value: len([l for l in self.layers.values() if l.execution_mode == mode])
                for mode in LayerExecutionMode
            },
            "background_layers": len([l for l in self.layers.values() if l.background_execution]),
            "total_categories": sum(len(layer.categories) for layer in self.layers.values()),
            "required_services": list(set().union(*(layer.required_services for layer in self.layers.values()))),
            "estimated_total_duration": sum((layer.max_duration_minutes for layer in self.layers.values()), 0),
            "configuration_path": str(self.config_path),
            "configuration_valid": len(self.validate_configuration()) == 0
        }