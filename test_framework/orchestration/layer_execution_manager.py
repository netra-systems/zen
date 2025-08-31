#!/usr/bin/env python3
"""
Layer Execution Manager - Individual test layer execution management

This manager manages individual test layer execution within the orchestration system,
handling category execution, resource allocation, progress tracking, and integration
with the existing UnifiedTestRunner functionality.

Key Responsibilities:
- Execute individual test layers (fast_feedback, core_integration, service_integration, e2e_background)
- Manage category execution within layers  
- Handle parallel vs sequential execution modes
- Coordinate with existing UnifiedTestRunner functionality
- Provide detailed execution reporting per layer
- Resource allocation and conflict management
- Integration with existing test framework components
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any, Callable, Tuple, NamedTuple
import threading
from threading import Lock, Event

# Core test framework imports
from test_framework.layer_system import (
    LayerSystem, TestLayer, LayerExecutionPlan, ExecutionConfig,
    LayerExecutionMode, LayerExecutionStatus, FailFastStrategy, ResourceLimits,
    CategoryConfig
)
from test_framework.category_system import CategorySystem, TestCategory, CategoryPriority

# Import existing test runner components for integration
try:
    from scripts.unified_test_runner import UnifiedTestRunner as LegacyUnifiedTestRunner
except ImportError:
    LegacyUnifiedTestRunner = None

# Environment management
try:
    from shared.isolated_environment import get_env
except ImportError:
    # Fallback for test environments
    def get_env():
        return os.environ


class LayerExecutionResult(NamedTuple):
    """Result of layer execution"""
    success: bool
    layer_name: str
    categories_executed: List[str]
    total_duration: timedelta
    category_results: Dict[str, Dict[str, Any]]
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_summary: Optional[str]
    resource_usage: Dict[str, Any]


class CategoryExecutionResult(NamedTuple):
    """Result of individual category execution"""
    success: bool
    category_name: str
    duration: timedelta
    test_counts: Dict[str, int]
    output: str
    errors: str
    metadata: Dict[str, Any]


class ExecutionStrategy(Enum):
    """Category execution strategies within layers"""
    SEQUENTIAL = "sequential"
    PARALLEL_UNLIMITED = "parallel_unlimited"
    PARALLEL_LIMITED = "parallel_limited"
    HYBRID_SMART = "hybrid_smart"


@dataclass
class LayerExecutionConfig:
    """Configuration for layer execution"""
    layer_name: str
    execution_strategy: ExecutionStrategy = ExecutionStrategy.HYBRID_SMART
    max_parallel_categories: int = 4
    timeout_multiplier: float = 1.0
    fail_fast_enabled: bool = False
    retry_failed_categories: bool = False
    max_retries: int = 1
    resource_limits: Optional[ResourceLimits] = None
    environment: str = "development"
    use_real_services: bool = False
    use_real_llm: bool = False
    background_execution: bool = False


class LayerExecutionManager:
    """
    Manager responsible for executing individual test layers
    
    This manager manages the execution of test layers, coordinating category execution,
    resource allocation, and progress reporting while integrating with existing
    test framework components.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.manager_id = f"layer_executor_{int(time.time())}"
        self.logger = logging.getLogger(f"LayerExecutionManager.{self.manager_id}")
        
        # Initialize core systems
        self.layer_system = LayerSystem(self.project_root)
        self.category_system = CategorySystem(self.project_root)
        
        # Execution state
        self.current_execution: Optional[LayerExecutionConfig] = None
        self.execution_lock = Lock()
        self.cancel_event = Event()
        self.category_results: Dict[str, CategoryExecutionResult] = {}
        self.execution_stats = {
            "layers_executed": 0,
            "categories_executed": 0, 
            "total_duration": timedelta(0),
            "success_rate": 0.0
        }
        
        # Communication protocol (placeholder for orchestrator integration)
        self.communication_enabled = False
        self.message_handlers = {}
        
        # Resource tracking
        self.allocated_resources = {}
        self.resource_lock = Lock()
        
        # Integration with existing test runner
        self._initialize_test_runner_integration()
        
    def _initialize_test_runner_integration(self):
        """Initialize integration with existing unified test runner"""
        self.test_runner_path = self.project_root / "scripts" / "unified_test_runner.py"
        self.python_executable = sys.executable
        
        # Detect optimal execution environment
        self._setup_execution_environment()
        
    def _setup_execution_environment(self):
        """Setup optimal execution environment for test categories"""
        env = get_env()
        
        # Set base environment variables for test execution
        env.set("PYTHONPATH", str(self.project_root), "layer_execution_agent")
        env.set("TEST_ORCHESTRATOR_ACTIVE", "true", "layer_execution_agent")
        
    async def execute_layer(self, layer_name: str, config: LayerExecutionConfig) -> LayerExecutionResult:
        """
        Execute a complete test layer
        
        Args:
            layer_name: Name of the layer to execute
            config: Execution configuration
            
        Returns:
            LayerExecutionResult with comprehensive execution results
        """
        with self.execution_lock:
            if self.current_execution:
                raise RuntimeError(f"Layer execution already in progress: {self.current_execution.layer_name}")
            
            self.current_execution = config
            self.cancel_event.clear()
            
        self.logger.info(f"Starting layer execution: {layer_name}")
        execution_start = datetime.now()
        
        try:
            # Validate layer exists
            layer = self.layer_system.layers.get(layer_name)
            if not layer:
                raise ValueError(f"Layer not found: {layer_name}")
                
            # Apply execution configuration to layer
            self._apply_execution_config(layer, config)
            
            # Request resource allocation
            resources_allocated = await self._allocate_resources(layer, config)
            if not resources_allocated:
                raise RuntimeError(f"Failed to allocate resources for layer: {layer_name}")
                
            # Notify start (for orchestrator integration)
            await self._notify_layer_start(layer_name)
            
            # Execute layer based on its execution mode
            if layer.execution_mode == LayerExecutionMode.SEQUENTIAL:
                layer_result = await self._execute_sequential(layer, config)
            elif layer.execution_mode == LayerExecutionMode.PARALLEL:
                layer_result = await self._execute_parallel(layer, config)
            else:  # HYBRID
                layer_result = await self._execute_hybrid(layer, config)
                
            # Release resources
            await self._release_resources(layer)
            
            # Calculate final statistics
            total_duration = datetime.now() - execution_start
            
            # Build comprehensive result
            result = LayerExecutionResult(
                success=layer_result["success"],
                layer_name=layer_name,
                categories_executed=list(layer_result["categories"].keys()),
                total_duration=total_duration,
                category_results=layer_result["categories"],
                total_tests=layer_result.get("total_tests", 0),
                passed_tests=layer_result.get("passed_tests", 0),
                failed_tests=layer_result.get("failed_tests", 0),
                skipped_tests=layer_result.get("skipped_tests", 0),
                error_summary=layer_result.get("error_summary"),
                resource_usage=layer_result.get("resource_usage", {})
            )
            
            # Update execution stats
            self._update_execution_stats(result)
            
            # Notify completion
            await self._notify_layer_complete(layer_name, result.success)
            
            self.logger.info(f"Layer execution completed: {layer_name}, success: {result.success}")
            return result
            
        except Exception as e:
            self.logger.error(f"Layer execution failed: {layer_name}: {e}")
            await self._notify_layer_failed(layer_name, str(e))
            
            # Return failure result
            total_duration = datetime.now() - execution_start
            return LayerExecutionResult(
                success=False,
                layer_name=layer_name,
                categories_executed=[],
                total_duration=total_duration,
                category_results={},
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                error_summary=str(e),
                resource_usage={}
            )
            
        finally:
            # Clean up execution state
            with self.execution_lock:
                self.current_execution = None
                
    def _apply_execution_config(self, layer: TestLayer, config: LayerExecutionConfig):
        """Apply execution configuration to layer"""
        # Apply timeout multiplier
        if config.timeout_multiplier != 1.0:
            layer.max_duration_minutes = int(layer.max_duration_minutes * config.timeout_multiplier)
            for category in layer.categories:
                category.timeout_seconds = int(category.timeout_seconds * config.timeout_multiplier)
                
        # Apply resource limits override
        if config.resource_limits:
            layer.resource_limits = config.resource_limits
            
        # Set background execution if requested
        if config.background_execution:
            layer.background_execution = True
            
    async def _execute_sequential(self, layer: TestLayer, config: LayerExecutionConfig) -> Dict[str, Any]:
        """Execute layer categories sequentially"""
        self.logger.info(f"Executing layer sequentially: {layer.name}")
        
        results = {
            "success": True,
            "categories": {},
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "execution_mode": "sequential"
        }
        
        # Execute categories in priority order
        sorted_categories = sorted(layer.categories, key=lambda c: c.priority_order)
        
        for category_config in sorted_categories:
            if self.cancel_event.is_set():
                self.logger.info("Execution cancelled, stopping sequential execution")
                break
                
            category_name = category_config.name
            self.logger.info(f"Executing category: {category_name}")
            
            try:
                category_result = await self._execute_single_category(category_name, layer, config)
                results["categories"][category_name] = category_result._asdict()
                
                # Update totals
                self._update_result_totals(results, category_result)
                
                # Check fail-fast condition
                if not category_result.success and config.fail_fast_enabled:
                    self.logger.warning(f"Fail-fast triggered by category: {category_name}")
                    results["success"] = False
                    break
                    
                if not category_result.success:
                    results["success"] = False
                    
            except Exception as e:
                self.logger.error(f"Category execution failed: {category_name}: {e}")
                results["categories"][category_name] = {
                    "success": False,
                    "category_name": category_name,
                    "duration": timedelta(0),
                    "test_counts": {"total": 0, "passed": 0, "failed": 1, "skipped": 0},
                    "output": "",
                    "errors": str(e),
                    "metadata": {"error": "execution_exception"}
                }
                results["success"] = False
                
                if config.fail_fast_enabled:
                    break
                    
        return results
        
    async def _execute_parallel(self, layer: TestLayer, config: LayerExecutionConfig) -> Dict[str, Any]:
        """Execute layer categories in parallel"""
        self.logger.info(f"Executing layer in parallel: {layer.name}")
        
        results = {
            "success": True,
            "categories": {},
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "execution_mode": "parallel"
        }
        
        # Determine parallel execution limit
        max_parallel = min(
            len(layer.categories),
            config.max_parallel_categories,
            layer.resource_limits.max_parallel_instances
        )
        
        # Create semaphore for controlling parallel execution
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def execute_with_semaphore(category_config: CategoryConfig):
            """Execute category with semaphore control"""
            async with semaphore:
                if self.cancel_event.is_set():
                    return None
                    
                try:
                    return await self._execute_single_category(category_config.name, layer, config)
                except Exception as e:
                    self.logger.error(f"Parallel category execution failed: {category_config.name}: {e}")
                    return CategoryExecutionResult(
                        success=False,
                        category_name=category_config.name,
                        duration=timedelta(0),
                        test_counts={"total": 0, "passed": 0, "failed": 1, "skipped": 0},
                        output="",
                        errors=str(e),
                        metadata={"error": "parallel_execution_exception"}
                    )
                    
        # Create tasks for all categories
        tasks = [execute_with_semaphore(cat_config) for cat_config in layer.categories]
        
        # Wait for all tasks to complete
        category_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(category_results):
            if result is None:  # Cancelled
                continue
                
            if isinstance(result, Exception):
                category_name = layer.categories[i].name
                self.logger.error(f"Parallel execution exception: {category_name}: {result}")
                result = CategoryExecutionResult(
                    success=False,
                    category_name=category_name,
                    duration=timedelta(0),
                    test_counts={"total": 0, "passed": 0, "failed": 1, "skipped": 0},
                    output="",
                    errors=str(result),
                    metadata={"error": "gather_exception"}
                )
                
            results["categories"][result.category_name] = result._asdict()
            self._update_result_totals(results, result)
            
            if not result.success:
                results["success"] = False
                
        return results
        
    async def _execute_hybrid(self, layer: TestLayer, config: LayerExecutionConfig) -> Dict[str, Any]:
        """Execute layer using hybrid strategy (smart parallel/sequential)"""
        self.logger.info(f"Executing layer in hybrid mode: {layer.name}")
        
        # Analyze category dependencies and resource requirements
        execution_groups = self._analyze_execution_groups(layer.categories)
        
        results = {
            "success": True,
            "categories": {},
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "execution_mode": "hybrid"
        }
        
        # Execute groups in sequence, categories within groups in parallel
        for group_num, category_group in enumerate(execution_groups):
            self.logger.info(f"Executing group {group_num + 1}: {[c.name for c in category_group]}")
            
            if self.cancel_event.is_set():
                break
                
            # Execute group in parallel
            group_semaphore = asyncio.Semaphore(min(len(category_group), config.max_parallel_categories))
            
            async def execute_group_category(cat_config: CategoryConfig):
                async with group_semaphore:
                    if self.cancel_event.is_set():
                        return None
                    return await self._execute_single_category(cat_config.name, layer, config)
                    
            group_tasks = [execute_group_category(cat_config) for cat_config in category_group]
            group_results = await asyncio.gather(*group_tasks, return_exceptions=True)
            
            # Process group results
            group_success = True
            for i, result in enumerate(group_results):
                if result is None:
                    continue
                    
                if isinstance(result, Exception):
                    category_name = category_group[i].name
                    result = CategoryExecutionResult(
                        success=False,
                        category_name=category_name,
                        duration=timedelta(0),
                        test_counts={"total": 0, "passed": 0, "failed": 1, "skipped": 0},
                        output="",
                        errors=str(result),
                        metadata={"error": "hybrid_group_exception"}
                    )
                    
                results["categories"][result.category_name] = result._asdict()
                self._update_result_totals(results, result)
                
                if not result.success:
                    group_success = False
                    results["success"] = False
                    
            # Check fail-fast at group level
            if not group_success and config.fail_fast_enabled:
                self.logger.warning(f"Fail-fast triggered by group {group_num + 1}")
                break
                
        return results
        
    def _analyze_execution_groups(self, categories: List[CategoryConfig]) -> List[List[CategoryConfig]]:
        """Analyze categories to create optimal execution groups for hybrid mode"""
        # Simple implementation: group by priority order for now
        # More sophisticated dependency analysis could be added later
        
        groups = []
        current_group = []
        current_priority = None
        
        sorted_categories = sorted(categories, key=lambda c: c.priority_order)
        
        for category in sorted_categories:
            if current_priority is None or category.priority_order == current_priority:
                current_group.append(category)
                current_priority = category.priority_order
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [category]
                current_priority = category.priority_order
                
        if current_group:
            groups.append(current_group)
            
        return groups
        
    async def _execute_single_category(self, category_name: str, layer: TestLayer, 
                                     config: LayerExecutionConfig) -> CategoryExecutionResult:
        """Execute a single test category using the existing test runner"""
        self.logger.info(f"Executing category: {category_name} in layer: {layer.name}")
        
        execution_start = datetime.now()
        
        try:
            # Build command to execute category using unified test runner
            cmd = self._build_category_command(category_name, config)
            
            # Execute command
            result = await self._execute_command(cmd, config)
            
            # Parse execution result
            test_counts = self._parse_test_counts(result.get("output", ""))
            
            execution_duration = datetime.now() - execution_start
            
            return CategoryExecutionResult(
                success=result.get("success", False),
                category_name=category_name,
                duration=execution_duration,
                test_counts=test_counts,
                output=result.get("output", ""),
                errors=result.get("errors", ""),
                metadata={
                    "layer": layer.name,
                    "execution_mode": config.execution_strategy.value,
                    "command": " ".join(cmd) if isinstance(cmd, list) else str(cmd),
                    "timeout_used": result.get("timeout_used", False),
                    "retry_count": result.get("retry_count", 0)
                }
            )
            
        except Exception as e:
            execution_duration = datetime.now() - execution_start
            self.logger.error(f"Category execution exception: {category_name}: {e}")
            
            return CategoryExecutionResult(
                success=False,
                category_name=category_name,
                duration=execution_duration,
                test_counts={"total": 0, "passed": 0, "failed": 1, "skipped": 0},
                output="",
                errors=str(e),
                metadata={
                    "layer": layer.name,
                    "exception": True,
                    "error_type": type(e).__name__
                }
            )
            
    def _build_category_command(self, category_name: str, config: LayerExecutionConfig) -> List[str]:
        """Build command to execute category using unified test runner"""
        cmd = [
            self.python_executable,
            str(self.test_runner_path),
            "--category", category_name,
            "--env", config.environment
        ]
        
        # Add configuration flags
        if config.use_real_services:
            cmd.append("--real-services")
            
        if config.use_real_llm:
            cmd.append("--real-llm")
            
        # Add performance flags
        cmd.extend(["--no-coverage"])  # Disable coverage for performance
        
        # Add timeout handling
        if config.timeout_multiplier != 1.0:
            cmd.extend(["--timeout-multiplier", str(config.timeout_multiplier)])
            
        # Add parallel execution if appropriate
        if config.execution_strategy in [ExecutionStrategy.PARALLEL_UNLIMITED, ExecutionStrategy.PARALLEL_LIMITED]:
            cmd.append("--parallel")
            
        return cmd
        
    async def _execute_command(self, cmd: List[str], config: LayerExecutionConfig) -> Dict[str, Any]:
        """Execute command asynchronously with proper error handling"""
        try:
            # Prepare environment
            env = get_env()
            process_env = dict(os.environ)  # Copy current environment
            process_env.update({
                "PYTHONPATH": str(self.project_root),
                "TEST_LAYER_EXECUTION": "true",
                "TEST_ORCHESTRATOR_ACTIVE": "true",
                "LAYER_EXECUTION_AGENT_ID": self.manager_id
            })
            
            # Calculate timeout
            timeout_seconds = 1200  # Default 20 minutes
            if hasattr(config, 'timeout_multiplier'):
                timeout_seconds = int(timeout_seconds * config.timeout_multiplier)
                
            # Execute command
            self.logger.debug(f"Executing command: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
                cwd=str(self.project_root)
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout_seconds
                )
                
                # Decode output
                stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ""
                stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ""
                
                return {
                    "success": process.returncode == 0,
                    "output": stdout_text,
                    "errors": stderr_text,
                    "return_code": process.returncode,
                    "timeout_used": False
                }
                
            except asyncio.TimeoutError:
                # Handle timeout
                self.logger.warning(f"Command timed out after {timeout_seconds} seconds")
                process.kill()
                await process.wait()
                
                return {
                    "success": False,
                    "output": "",
                    "errors": f"Command timed out after {timeout_seconds} seconds",
                    "return_code": -1,
                    "timeout_used": True
                }
                
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return {
                "success": False,
                "output": "",
                "errors": str(e),
                "return_code": -1,
                "timeout_used": False
            }
            
    def _parse_test_counts(self, output: str) -> Dict[str, int]:
        """Parse test counts from pytest/jest output"""
        test_counts = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0
        }
        
        # Parse pytest output patterns
        import re
        
        # Look for pytest summary patterns
        pytest_patterns = [
            r'(\d+) passed',
            r'(\d+) failed',
            r'(\d+) error',
            r'(\d+) skipped'
        ]
        
        for i, pattern in enumerate(pytest_patterns):
            matches = re.findall(pattern, output)
            if matches:
                count = sum(int(match) for match in matches)
                if i == 0:
                    test_counts["passed"] = count
                elif i == 1:
                    test_counts["failed"] = count
                elif i == 2:
                    test_counts["errors"] = count
                elif i == 3:
                    test_counts["skipped"] = count
                    
        # Calculate total
        test_counts["total"] = (
            test_counts["passed"] + 
            test_counts["failed"] + 
            test_counts["errors"] + 
            test_counts["skipped"]
        )
        
        # Handle Jest output patterns (for frontend tests)
        jest_pattern = r'Tests:\s*(\d+) failed,\s*(\d+) passed,\s*(\d+) total'
        jest_match = re.search(jest_pattern, output)
        if jest_match:
            test_counts["failed"] = int(jest_match.group(1))
            test_counts["passed"] = int(jest_match.group(2))
            test_counts["total"] = int(jest_match.group(3))
            test_counts["skipped"] = test_counts["total"] - test_counts["passed"] - test_counts["failed"]
            
        return test_counts
        
    def _update_result_totals(self, results: Dict[str, Any], category_result: CategoryExecutionResult):
        """Update result totals with category execution results"""
        test_counts = category_result.test_counts
        results["total_tests"] += test_counts.get("total", 0)
        results["passed_tests"] += test_counts.get("passed", 0) 
        results["failed_tests"] += test_counts.get("failed", 0)
        results["skipped_tests"] += test_counts.get("skipped", 0)
        
    def _update_execution_stats(self, result: LayerExecutionResult):
        """Update internal execution statistics"""
        self.execution_stats["layers_executed"] += 1
        self.execution_stats["categories_executed"] += len(result.categories_executed)
        self.execution_stats["total_duration"] += result.total_duration
        
        # Update success rate
        total_layers = self.execution_stats["layers_executed"]
        successful_layers = sum(1 for r in [result] if r.success)  # Simplified for this one result
        self.execution_stats["success_rate"] = successful_layers / total_layers if total_layers > 0 else 0.0
        
    async def _allocate_resources(self, layer: TestLayer, config: LayerExecutionConfig) -> bool:
        """Request resource allocation for layer execution"""
        with self.resource_lock:
            resource_key = f"{layer.name}_{config.layer_name}"
            
            # Check if resources are already allocated
            if resource_key in self.allocated_resources:
                return True
                
            # Simple resource allocation (more sophisticated logic could be added)
            required_resources = {
                "memory_mb": layer.resource_limits.max_memory_mb,
                "cpu_percent": layer.resource_limits.max_cpu_percent,
                "parallel_instances": layer.resource_limits.max_parallel_instances
            }
            
            # For now, always approve resource allocation
            # In a real system, this would check system resources
            self.allocated_resources[resource_key] = required_resources
            
            self.logger.info(f"Allocated resources for {resource_key}: {required_resources}")
            return True
            
    async def _release_resources(self, layer: TestLayer):
        """Release allocated resources after layer execution"""
        with self.resource_lock:
            resource_keys = [key for key in self.allocated_resources.keys() if key.startswith(layer.name)]
            for key in resource_keys:
                del self.allocated_resources[key]
                self.logger.debug(f"Released resources: {key}")
                
    # Communication protocol methods (for orchestrator integration)
    
    async def _notify_layer_start(self, layer_name: str):
        """Notify orchestrator of layer start"""
        if self.communication_enabled:
            # Placeholder for actual communication protocol
            self.logger.debug(f"Notifying layer start: {layer_name}")
            
    async def _notify_layer_complete(self, layer_name: str, success: bool):
        """Notify orchestrator of layer completion"""
        if self.communication_enabled:
            # Placeholder for actual communication protocol
            self.logger.debug(f"Notifying layer complete: {layer_name}, success: {success}")
            
    async def _notify_layer_failed(self, layer_name: str, error: str):
        """Notify orchestrator of layer failure"""
        if self.communication_enabled:
            # Placeholder for actual communication protocol
            self.logger.debug(f"Notifying layer failed: {layer_name}, error: {error}")
            
    # Public API methods
    
    def cancel_execution(self):
        """Cancel current layer execution"""
        self.logger.info("Cancelling layer execution")
        self.cancel_event.set()
        
    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status"""
        with self.execution_lock:
            return {
                "active": self.current_execution is not None,
                "current_layer": self.current_execution.layer_name if self.current_execution else None,
                "execution_stats": self.execution_stats.copy(),
                "allocated_resources": len(self.allocated_resources),
                "categories_in_progress": len(self.category_results)
            }
            
    def get_available_layers(self) -> List[str]:
        """Get list of available layers"""
        return list(self.layer_system.layers.keys())
        
    def get_layer_categories(self, layer_name: str) -> List[str]:
        """Get categories for a specific layer"""
        return self.layer_system.get_layer_categories(layer_name)
        
    def validate_layer_configuration(self, layer_name: str) -> List[str]:
        """Validate layer configuration and return issues"""
        layer = self.layer_system.layers.get(layer_name)
        if not layer:
            return [f"Layer not found: {layer_name}"]
            
        issues = []
        
        # Check categories exist in category system
        for category_config in layer.categories:
            if not self.category_system.get_category(category_config.name):
                issues.append(f"Category not found in category system: {category_config.name}")
                
        # Check resource limits are reasonable
        if layer.resource_limits.max_memory_mb > 8192:
            issues.append(f"Memory limit too high: {layer.resource_limits.max_memory_mb}MB")
            
        if layer.resource_limits.max_cpu_percent > 95:
            issues.append(f"CPU limit too high: {layer.resource_limits.max_cpu_percent}%")
            
        return issues
        
    def enable_communication(self, communication_protocol):
        """Enable communication with orchestrator"""
        self.communication_enabled = True
        # Additional setup could be added here for actual protocol integration
        
    def disable_communication(self):
        """Disable communication with orchestrator"""
        self.communication_enabled = False
        
    # Integration methods for orchestrator
    
    async def handle_orchestrator_message(self, message_type: str, payload: Dict[str, Any]):
        """Handle messages from orchestrator"""
        handler = self.message_handlers.get(message_type)
        if handler:
            await handler(payload)
        else:
            self.logger.warning(f"No handler for message type: {message_type}")
            
    def register_message_handler(self, message_type: str, handler: Callable):
        """Register message handler for orchestrator communication"""
        self.message_handlers[message_type] = handler
        
    # Utility methods
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get comprehensive execution summary"""
        return {
            "manager_id": self.manager_id,
            "project_root": str(self.project_root),
            "execution_stats": self.execution_stats,
            "available_layers": self.get_available_layers(),
            "current_status": self.get_execution_status(),
            "resource_allocation": self.allocated_resources,
            "layer_system_summary": self.layer_system.get_system_summary(),
            "communication_enabled": self.communication_enabled
        }
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the agent"""
        health = {
            "status": "healthy",
            "issues": [],
            "checks": {}
        }
        
        # Check layer system
        try:
            validation_issues = self.layer_system.validate_configuration()
            health["checks"]["layer_system"] = len(validation_issues) == 0
            if validation_issues:
                health["issues"].extend(validation_issues)
                health["status"] = "degraded"
        except Exception as e:
            health["checks"]["layer_system"] = False
            health["issues"].append(f"Layer system error: {e}")
            health["status"] = "unhealthy"
            
        # Check test runner integration
        try:
            test_runner_exists = self.test_runner_path.exists()
            health["checks"]["test_runner_integration"] = test_runner_exists
            if not test_runner_exists:
                health["issues"].append("Unified test runner not found")
                health["status"] = "degraded"
        except Exception as e:
            health["checks"]["test_runner_integration"] = False
            health["issues"].append(f"Test runner check error: {e}")
            
        # Check execution environment
        try:
            python_available = True  # We're already running in Python
            health["checks"]["execution_environment"] = python_available
        except Exception as e:
            health["checks"]["execution_environment"] = False
            health["issues"].append(f"Execution environment error: {e}")
            health["status"] = "unhealthy"
            
        return health


# Helper functions for integration with existing test runner

def create_layer_execution_config(
    layer_name: str,
    execution_mode: str = "hybrid_smart",
    environment: str = "development", 
    **kwargs
) -> LayerExecutionConfig:
    """Create layer execution configuration from parameters"""
    return LayerExecutionConfig(
        layer_name=layer_name,
        execution_strategy=ExecutionStrategy(execution_mode),
        environment=environment,
        **kwargs
    )


async def execute_layer_async(layer_name: str, config: Optional[LayerExecutionConfig] = None) -> LayerExecutionResult:
    """Standalone function to execute a layer asynchronously"""
    agent = LayerExecutionManager()
    
    if config is None:
        config = create_layer_execution_config(layer_name)
        
    return await agent.execute_layer(layer_name, config)


def execute_layer_sync(layer_name: str, config: Optional[LayerExecutionConfig] = None) -> LayerExecutionResult:
    """Standalone function to execute a layer synchronously"""
    return asyncio.run(execute_layer_async(layer_name, config))


# CLI integration for testing

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Layer Execution Agent")
    parser.add_argument("--layer", required=True, help="Layer name to execute")
    parser.add_argument("--mode", default="hybrid_smart", help="Execution mode")
    parser.add_argument("--env", default="development", help="Environment")
    parser.add_argument("--real-services", action="store_true", help="Use real services")
    parser.add_argument("--real-llm", action="store_true", help="Use real LLM")
    parser.add_argument("--parallel", type=int, default=4, help="Max parallel categories")
    parser.add_argument("--timeout-multiplier", type=float, default=1.0, help="Timeout multiplier")
    parser.add_argument("--fail-fast", action="store_true", help="Enable fail-fast")
    parser.add_argument("--list-layers", action="store_true", help="List available layers")
    parser.add_argument("--health-check", action="store_true", help="Perform health check")
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = LayerExecutionManager()
    
    if args.list_layers:
        layers = agent.get_available_layers()
        print(f"Available layers: {', '.join(layers)}")
        sys.exit(0)
        
    if args.health_check:
        health = asyncio.run(agent.health_check())
        print(f"Health status: {health['status']}")
        if health['issues']:
            print(f"Issues: {', '.join(health['issues'])}")
        sys.exit(0 if health['status'] == 'healthy' else 1)
        
    # Create configuration
    config = LayerExecutionConfig(
        layer_name=args.layer,
        execution_strategy=ExecutionStrategy(args.mode),
        environment=args.env,
        max_parallel_categories=args.parallel,
        timeout_multiplier=args.timeout_multiplier,
        fail_fast_enabled=args.fail_fast,
        use_real_services=args.real_services,
        use_real_llm=args.real_llm
    )
    
    # Execute layer
    try:
        result = asyncio.run(agent.execute_layer(args.layer, config))
        
        print(f"Layer execution completed: {result.success}")
        print(f"Duration: {result.total_duration}")
        print(f"Categories executed: {len(result.categories_executed)}")
        print(f"Tests: {result.total_tests} total, {result.passed_tests} passed, {result.failed_tests} failed")
        
        if result.error_summary:
            print(f"Errors: {result.error_summary}")
            
        sys.exit(0 if result.success else 1)
        
    except Exception as e:
        print(f"Layer execution failed: {e}", file=sys.stderr)
        sys.exit(1)