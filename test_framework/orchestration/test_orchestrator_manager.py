#!/usr/bin/env python3
"""
Test Orchestrator Manager - Main coordinator for layered test orchestration system

This manager serves as the central coordinator for the comprehensive test execution system,
managing layer execution, agent delegation, resource allocation, and progress tracking.

Key Features:
- Coordinates execution across all test layers (fast_feedback, core_integration, service_integration, e2e_background)
- Manages manager delegation and inter-manager communication
- Handles execution modes (commit, ci, nightly, weekend)
- Provides unified API for test orchestration
- Integrates with existing unified_test_runner.py
- Supports background execution for long-running E2E tests
- Real-time progress streaming and resource conflict management

Integration with Existing System:
- Enhances current category system without breaking compatibility
- Works with existing test_framework/ modules
- Supports all existing CLI arguments plus new layer-based ones
"""

import asyncio
import json
import logging
import os
import signal
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
from threading import Event, Lock
import yaml

# Core test framework imports
from test_framework.layer_system import (
    LayerSystem, TestLayer, LayerExecutionPlan, ExecutionConfig,
    LayerExecutionMode, LayerExecutionStatus, FailFastStrategy, ResourceLimits
)
from test_framework.category_system import CategorySystem, TestCategory, CategoryPriority
from test_framework.progress_tracker import ProgressTracker, ProgressEvent
from test_framework.auto_splitter import TestSplitter, SplittingStrategy
from test_framework.test_discovery import TestDiscovery
from test_framework.real_services import RealServicesManager
from test_framework.service_availability import ServiceAvailabilityChecker


class ExecutionMode(Enum):
    """Test execution modes for different scenarios"""
    COMMIT = "commit"          # Fast validation for commits (layers 1-2)  
    CI = "ci"                  # CI pipeline execution (layers 1-3)
    NIGHTLY = "nightly"        # Full test suite including E2E (all layers)
    WEEKEND = "weekend"        # Comprehensive validation with extended timeouts
    DEVELOPMENT = "development" # Developer-focused execution with optimizations


class OrchestrationResult(NamedTuple):
    """Result of test orchestration execution"""
    success: bool
    layers_executed: List[str]
    total_duration: timedelta
    layer_results: Dict[str, Dict[str, Any]]
    background_tasks: List[str]
    error_summary: Optional[str]


class ManagerCommunicationMessage(NamedTuple):
    """Message structure for inter-manager communication"""
    sender: str
    recipient: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime


@dataclass
class OrchestrationConfig:
    """Configuration for test orchestration execution"""
    execution_mode: ExecutionMode = ExecutionMode.DEVELOPMENT
    layers: Optional[List[str]] = None  # None means all layers for the mode
    environment: str = "development"
    use_background_e2e: bool = True
    max_parallel_layers: int = 3
    enable_progress_streaming: bool = True
    resource_management: bool = True
    fail_fast_strategy: FailFastStrategy = FailFastStrategy.LAYER
    timeout_multiplier: float = 1.0
    force_real_services: bool = False
    force_real_llm: bool = False
    
    # Legacy category system compatibility
    legacy_categories: Optional[List[str]] = None
    legacy_mode: bool = False
    
    # Manager configuration
    manager_communication_enabled: bool = True
    progress_streaming_interval: int = 5  # seconds
    resource_check_interval: int = 30     # seconds


class ManagerCommunicationProtocol:
    """Protocol for inter-manager communication and coordination"""
    
    def __init__(self, orchestrator_id: str):
        self.orchestrator_id = orchestrator_id
        self.managers: Dict[str, Any] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.subscriptions: Dict[str, Set[str]] = {}  # message_type -> manager_ids
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger(f"ManagerComm.{orchestrator_id}")
        
    async def register_manager(self, manager_id: str, manager_instance: Any):
        """Register a manager in the communication protocol"""
        async with self.lock:
            self.managers[manager_id] = manager_instance
            self.logger.debug(f"Registered manager: {manager_id}")
            
    async def send_message(self, sender: str, recipient: str, message_type: str, payload: Dict[str, Any]):
        """Send a message between managers"""
        message = ManagerCommunicationMessage(
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
            timestamp=datetime.now()
        )
        await self.message_queue.put(message)
        self.logger.debug(f"Message sent: {sender} -> {recipient} ({message_type})")
        
    async def broadcast_message(self, sender: str, message_type: str, payload: Dict[str, Any]):
        """Broadcast a message to all registered agents"""
        for manager_id in self.managers.keys():
            if manager_id != sender:
                await self.send_message(sender, manager_id, message_type, payload)
                
    async def subscribe_to_messages(self, manager_id: str, message_types: List[str]):
        """Subscribe a manager to specific message types"""
        async with self.lock:
            for msg_type in message_types:
                if msg_type not in self.subscriptions:
                    self.subscriptions[msg_type] = set()
                self.subscriptions[msg_type].add(manager_id)
                
    async def process_messages(self):
        """Process messages in the communication queue"""
        while True:
            try:
                message = await self.message_queue.get()
                await self._deliver_message(message)
                self.message_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
                
    async def _deliver_message(self, message: ManagerCommunicationMessage):
        """Deliver a message to the appropriate agent"""
        if message.recipient in self.managers:
            manager = self.managers[message.recipient]
            if hasattr(manager, 'handle_message'):
                await manager.handle_message(message)


# Import the new LayerExecutionManager
from test_framework.orchestration.layer_execution_manager import (
    LayerExecutionManager as NewLayerExecutionManager, LayerExecutionConfig, ExecutionStrategy
)


class BackgroundE2EManager:
    """Manager responsible for managing long-running E2E tests in background"""
    
    def __init__(self, manager_id: str, communication_protocol: ManagerCommunicationProtocol):
        self.manager_id = manager_id
        self.communication = communication_protocol
        self.logger = logging.getLogger(f"BackgroundE2E.{manager_id}")
        self.background_tasks: Dict[str, asyncio.Task] = {}
        self.background_processes: Dict[str, subprocess.Popen] = {}
        
    async def start_background_execution(self, layer_name: str, config: OrchestrationConfig) -> str:
        """Start background execution of E2E layer"""
        task_id = f"bg_{layer_name}_{int(time.time())}"
        
        self.logger.info(f"Starting background execution: {task_id}")
        
        # Create background task
        task = asyncio.create_task(self._execute_background_layer(layer_name, task_id, config))
        self.background_tasks[task_id] = task
        
        # Notify orchestrator
        await self.communication.send_message(
            self.manager_id, "orchestrator", "background_started",
            {
                "task_id": task_id,
                "layer": layer_name,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return task_id
        
    async def _execute_background_layer(self, layer_name: str, task_id: str, config: OrchestrationConfig):
        """Execute layer in background"""
        try:
            # In real implementation, this would spawn a subprocess with the unified_test_runner
            # configured for the specific layer/categories
            
            cmd = [
                sys.executable, "scripts/unified_test_runner.py",
                "--categories", *self._get_layer_categories(layer_name),
                "--env", config.environment,
                "--background-mode"
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=Path(__file__).parent.parent.parent
            )
            
            self.background_processes[task_id] = process
            
            # Monitor the process
            stdout, stderr = await asyncio.create_subprocess_exec(*cmd).communicate()
            
            success = process.returncode == 0
            
            # Notify completion
            await self.communication.send_message(
                self.manager_id, "orchestrator", "background_completed",
                {
                    "task_id": task_id,
                    "success": success,
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else ""
                }
            )
            
        except Exception as e:
            self.logger.error(f"Background execution failed: {task_id}: {e}")
            await self.communication.send_message(
                self.manager_id, "orchestrator", "background_failed",
                {
                    "task_id": task_id,
                    "error": str(e)
                }
            )
            
    def _get_layer_categories(self, layer_name: str) -> List[str]:
        """Get categories for a specific layer"""
        # This would map layer names to their categories
        layer_category_mapping = {
            "fast_feedback": ["smoke", "unit"],
            "core_integration": ["database", "api", "websocket", "integration"],
            "service_integration": ["agent", "e2e_critical", "frontend"],
            "e2e_background": ["cypress", "e2e", "performance"]
        }
        return layer_category_mapping.get(layer_name, [])
        
    async def get_background_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of background task"""
        if task_id in self.background_tasks:
            task = self.background_tasks[task_id]
            return {
                "task_id": task_id,
                "status": "running" if not task.done() else "completed",
                "done": task.done()
            }
        return None
        
    async def cancel_background_task(self, task_id: str) -> bool:
        """Cancel a running background task"""
        if task_id in self.background_tasks:
            task = self.background_tasks[task_id]
            task.cancel()
            
            # Kill subprocess if exists
            if task_id in self.background_processes:
                process = self.background_processes[task_id]
                process.terminate()
                
            return True
        return False
        
    async def handle_message(self, message: ManagerCommunicationMessage):
        """Handle incoming messages"""
        if message.message_type == "get_background_status":
            task_id = message.payload.get("task_id")
            status = await self.get_background_status(task_id)
            await self.communication.send_message(
                self.manager_id, message.sender, "background_status", 
                {"task_id": task_id, "status": status}
            )


class ProgressStreamingManager:
    """Manager responsible for real-time progress updates and streaming"""
    
    def __init__(self, manager_id: str, communication_protocol: ManagerCommunicationProtocol, project_root: Optional[Path] = None):
        self.manager_id = manager_id
        self.communication = communication_protocol
        self.logger = logging.getLogger(f"Progress.{manager_id}")
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.progress_tracker = ProgressTracker(self.project_root)
        self.streaming_enabled = True
        self.update_interval = 5  # seconds
        
    async def start_progress_streaming(self, config: OrchestrationConfig):
        """Start real-time progress streaming"""
        self.streaming_enabled = True
        self.update_interval = config.progress_streaming_interval
        
        # Start streaming task
        asyncio.create_task(self._stream_progress_updates())
        
    async def _stream_progress_updates(self):
        """Stream progress updates at regular intervals"""
        while self.streaming_enabled:
            try:
                current_progress = self.progress_tracker.get_current_progress()
                
                await self.communication.broadcast_message(
                    self.manager_id, "progress_update", 
                    {
                        "timestamp": datetime.now().isoformat(),
                        "progress": current_progress
                    }
                )
                
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Progress streaming error: {e}")
                await asyncio.sleep(self.update_interval)
                
    async def handle_message(self, message: ManagerCommunicationMessage):
        """Handle progress-related messages"""
        if message.message_type == "layer_started":
            layer = message.payload.get("layer")
            self.progress_tracker.start_category(layer)
            
        elif message.message_type == "layer_completed":
            layer = message.payload.get("layer")
            success = message.payload.get("success", False)
            if success:
                self.progress_tracker.complete_category(layer)
            else:
                self.progress_tracker.fail_category(layer, message.payload.get("error", "Unknown error"))
                
    def stop_streaming(self):
        """Stop progress streaming"""
        self.streaming_enabled = False


class ResourceManagementManager:
    """Manager responsible for resource allocation and conflict management"""
    
    def __init__(self, manager_id: str, communication_protocol: ManagerCommunicationProtocol):
        self.manager_id = manager_id
        self.communication = communication_protocol
        self.logger = logging.getLogger(f"Resource.{manager_id}")
        self.allocated_resources: Dict[str, Dict[str, Any]] = {}
        self.resource_lock = asyncio.Lock()
        self.service_manager = RealServicesManager()
        
    async def handle_message(self, message: ManagerCommunicationMessage):
        """Handle resource management messages"""
        if message.message_type == "request_resources":
            success = await self._allocate_resources(message.sender, message.payload)
            await self.communication.send_message(
                self.manager_id, message.sender, "resource_allocation",
                {"success": success, "resources": message.payload}
            )
            
        elif message.message_type == "release_resources":
            await self._release_resources(message.sender, message.payload)
            
    async def _allocate_resources(self, requester: str, resource_request: Dict[str, Any]) -> bool:
        """Allocate resources for a requester"""
        async with self.resource_lock:
            try:
                # Check if services are available
                services_required = resource_request.get("services_required", [])
                for service in services_required:
                    if not await self._ensure_service_available(service):
                        self.logger.warning(f"Service not available: {service}")
                        return False
                        
                # Allocate resources (simplified)
                self.allocated_resources[requester] = resource_request
                return True
                
            except Exception as e:
                self.logger.error(f"Resource allocation failed: {e}")
                return False
                
    async def _release_resources(self, requester: str, resource_info: Dict[str, Any]):
        """Release allocated resources"""
        async with self.resource_lock:
            if requester in self.allocated_resources:
                del self.allocated_resources[requester]
                self.logger.debug(f"Released resources for: {requester}")
                
    async def _ensure_service_available(self, service: str) -> bool:
        """Ensure a required service is available"""
        try:
            # Use existing service availability checker
            checker = ServiceAvailabilityChecker()
            return await asyncio.get_event_loop().run_in_executor(
                None, checker.check_service_health, service
            )
        except Exception as e:
            self.logger.error(f"Service check failed for {service}: {e}")
            return False


class TestOrchestratorManager:
    """
    Main coordinator agent for layered test orchestration system
    
    This is the central agent that coordinates all test execution activities,
    managing layer execution, agent delegation, resource allocation, and progress tracking.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.manager_id = f"orchestrator_{int(time.time())}"
        self.logger = logging.getLogger(f"TestOrchestrator.{self.manager_id}")
        
        # Initialize core systems
        self.layer_system = LayerSystem(self.project_root / "test_framework" / "config")
        self.category_system = CategorySystem(self.project_root)
        
        # Initialize manager communication protocol
        self.communication = ManagerCommunicationProtocol(self.manager_id)
        
        # Initialize specialized managers
        self.layer_manager = NewLayerExecutionManager(self.project_root)
        self.layer_manager.enable_communication(self.communication)
        self.background_manager = BackgroundE2EManager("background_e2e", self.communication)
        self.progress_manager = ProgressStreamingManager("progress_streamer", self.communication, self.project_root)
        self.resource_manager = ResourceManagementManager("resource_manager", self.communication)
        
        # Execution state
        self.current_execution: Optional[OrchestrationConfig] = None
        self.execution_results: Dict[str, Any] = {}
        self.background_tasks: List[str] = []
        self._shutdown_event = Event()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    async def initialize(self):
        """Initialize the orchestrator and all agents"""
        self.logger.info("Initializing Test Orchestrator Agent")
        
        # Layer system configuration is already loaded in constructor
        
        # Register all agents in communication protocol
        await self.communication.register_manager("orchestrator", self)
        await self.communication.register_manager("layer_executor", self.layer_manager)
        await self.communication.register_manager("background_e2e", self.background_manager)
        await self.communication.register_manager("progress_streamer", self.progress_manager)
        await self.communication.register_manager("resource_manager", self.resource_manager)
        
        # Setup message subscriptions
        await self.communication.subscribe_to_messages("orchestrator", [
            "layer_started", "layer_completed", "layer_failed",
            "background_started", "background_completed", "background_failed"
        ])
        
        # Start communication processor
        asyncio.create_task(self.communication.process_messages())
        
        self.logger.info("Test Orchestrator Manager initialized successfully")
        
    def create_execution_config(self, **kwargs) -> OrchestrationConfig:
        """Create execution configuration from parameters"""
        return OrchestrationConfig(**kwargs)
        
    async def execute_tests(self, config: OrchestrationConfig) -> OrchestrationResult:
        """
        Main entry point for test execution
        
        Args:
            config: Orchestration configuration specifying how to run tests
            
        Returns:
            OrchestrationResult with complete execution results
        """
        self.logger.info(f"Starting test execution with mode: {config.execution_mode}")
        self.current_execution = config
        execution_start = datetime.now()
        
        try:
            # Determine layers to execute based on execution mode
            layers_to_execute = self._determine_layers(config)
            self.logger.info(f"Layers to execute: {layers_to_execute}")
            
            # Start progress streaming if enabled
            if config.enable_progress_streaming:
                await self.progress_manager.start_progress_streaming(config)
                
            # Handle legacy category mode if specified
            if config.legacy_mode and config.legacy_categories:
                return await self._execute_legacy_categories(config)
                
            # Execute layers according to plan
            # Create execution config with appropriate parameters
            exec_config = ExecutionConfig()
            if config.timeout_multiplier != 1.0:
                exec_config.global_timeout_minutes = int(exec_config.global_timeout_minutes * config.timeout_multiplier)
                
            execution_plan = self.layer_system.create_execution_plan(
                selected_layers=layers_to_execute,
                environment=config.environment
            )
            
            layer_results = {}
            success = True
            
            # Execute each phase of the execution plan
            for phase_num, phase_layers in enumerate(execution_plan.execution_sequence):
                self.logger.info(f"Executing phase {phase_num + 1}: {phase_layers}")
                
                phase_success = await self._execute_layer_phase(phase_layers, config)
                if not phase_success:
                    success = False
                    if config.fail_fast_strategy in [FailFastStrategy.IMMEDIATE, FailFastStrategy.LAYER]:
                        break
                        
                # Collect results from each layer
                for layer_name in phase_layers:
                    if layer_name in self.execution_results:
                        layer_results[layer_name] = self.execution_results[layer_name]
                        
            # Handle background E2E execution
            if config.use_background_e2e and "e2e_background" in layers_to_execute:
                bg_task_id = await self.background_manager.start_background_execution("e2e_background", config)
                self.background_tasks.append(bg_task_id)
                
            total_duration = datetime.now() - execution_start
            
            return OrchestrationResult(
                success=success,
                layers_executed=layers_to_execute,
                total_duration=total_duration,
                layer_results=layer_results,
                background_tasks=self.background_tasks,
                error_summary=None if success else "Some layers failed execution"
            )
            
        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            total_duration = datetime.now() - execution_start
            
            return OrchestrationResult(
                success=False,
                layers_executed=[],
                total_duration=total_duration,
                layer_results={},
                background_tasks=self.background_tasks,
                error_summary=str(e)
            )
            
        finally:
            # Cleanup
            if config.enable_progress_streaming:
                self.progress_manager.stop_streaming()
                
    def _determine_layers(self, config: OrchestrationConfig) -> List[str]:
        """Determine which layers to execute based on configuration"""
        if config.layers:
            return config.layers
            
        # Default layers based on execution mode
        mode_layers = {
            ExecutionMode.COMMIT: ["fast_feedback", "core_integration"],
            ExecutionMode.CI: ["fast_feedback", "core_integration", "service_integration"],
            ExecutionMode.NIGHTLY: ["fast_feedback", "core_integration", "service_integration", "e2e_background"],
            ExecutionMode.WEEKEND: ["fast_feedback", "core_integration", "service_integration", "e2e_background"],
            ExecutionMode.DEVELOPMENT: ["fast_feedback", "core_integration"]
        }
        
        return mode_layers.get(config.execution_mode, ["fast_feedback"])
        
    async def _execute_layer_phase(self, phase_layers: List[str], config: OrchestrationConfig) -> bool:
        """Execute a phase of layers (can be parallel or sequential)"""
        if len(phase_layers) == 1:
            # Single layer - execute directly
            try:
                # Create layer execution config
                layer_config = LayerExecutionConfig(
                    layer_name=phase_layers[0],
                    environment=config.environment,
                    use_real_services=config.force_real_services,
                    use_real_llm=config.force_real_llm,
                    timeout_multiplier=config.timeout_multiplier,
                    fail_fast_enabled=(config.fail_fast_strategy == FailFastStrategy.IMMEDIATE)
                )
                
                result = await self.layer_manager.execute_layer(phase_layers[0], layer_config)
                self.execution_results[phase_layers[0]] = result._asdict()
                return result.success
            except Exception as e:
                self.logger.error(f"Layer execution failed: {phase_layers[0]}: {e}")
                return False
                
        else:
            # Multiple layers - execute in parallel up to the limit
            max_parallel = min(len(phase_layers), config.max_parallel_layers)
            semaphore = asyncio.Semaphore(max_parallel)
            
            async def execute_with_semaphore(layer_name: str):
                async with semaphore:
                    try:
                        # Create layer execution config
                        layer_config = LayerExecutionConfig(
                            layer_name=layer_name,
                            environment=config.environment,
                            use_real_services=config.force_real_services,
                            use_real_llm=config.force_real_llm,
                            timeout_multiplier=config.timeout_multiplier,
                            fail_fast_enabled=(config.fail_fast_strategy == FailFastStrategy.IMMEDIATE)
                        )
                        
                        result = await self.layer_manager.execute_layer(layer_name, layer_config)
                        self.execution_results[layer_name] = result._asdict()
                        return result.success
                    except Exception as e:
                        self.logger.error(f"Layer execution failed: {layer_name}: {e}")
                        return False
                        
            tasks = [execute_with_semaphore(layer) for layer in phase_layers]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check if all layers succeeded
            success = all(isinstance(r, bool) and r for r in results)
            return success
            
    async def _execute_legacy_categories(self, config: OrchestrationConfig) -> OrchestrationResult:
        """Execute tests using legacy category system for backward compatibility"""
        self.logger.info("Executing in legacy category mode")
        
        # This would integrate with the existing unified_test_runner.py category execution
        # For now, return a placeholder result
        
        return OrchestrationResult(
            success=True,
            layers_executed=[],
            total_duration=timedelta(seconds=0),
            layer_results={"legacy": {"categories": config.legacy_categories}},
            background_tasks=[],
            error_summary=None
        )
        
    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status"""
        return {
            "active": self.current_execution is not None,
            "execution_mode": self.current_execution.execution_mode.value if self.current_execution else None,
            "background_tasks": len(self.background_tasks),
            "layer_results": len(self.execution_results)
        }
        
    def get_available_layers(self) -> List[str]:
        """Get list of available test layers"""
        # Delegate to the layer execution agent
        return self.layer_manager.get_available_layers()
        
    def get_layer_configuration(self, layer_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific layer"""
        # Delegate to the layer execution agent
        if hasattr(self.layer_manager, 'layer_system'):
            layer = self.layer_manager.layer_system.layers.get(layer_name)
            if layer:
                # Convert categories to strings (they are CategoryConfig objects)
                category_names = [cat.name if hasattr(cat, 'name') else str(cat) for cat in layer.categories]
                services_required = getattr(layer, 'required_services', set())
                
                return {
                    "name": layer.name,
                    "categories": category_names,
                    "execution_mode": layer.execution_mode.value,
                    "estimated_duration": f"{layer.max_duration_minutes} minutes",
                    "dependencies": list(layer.dependencies),
                    "services_required": list(services_required)
                }
        return None
        
    async def cancel_execution(self):
        """Cancel current test execution"""
        self.logger.info("Cancelling test execution")
        
        # Cancel background tasks
        for task_id in self.background_tasks:
            await self.background_manager.cancel_background_task(task_id)
            
        # Notify all agents to cancel
        await self.communication.broadcast_message("orchestrator", "cancel_execution", {})
        
        # Reset execution state
        self.current_execution = None
        self.execution_results.clear()
        self.background_tasks.clear()
        
    async def handle_message(self, message: ManagerCommunicationMessage):
        """Handle messages from other agents"""
        if message.message_type == "layer_started":
            self.logger.info(f"Layer started: {message.payload.get('layer')}")
            
        elif message.message_type == "layer_completed":
            layer = message.payload.get("layer")
            success = message.payload.get("success")
            self.logger.info(f"Layer completed: {layer}, success: {success}")
            
        elif message.message_type == "layer_failed":
            layer = message.payload.get("layer")
            error = message.payload.get("error")
            self.logger.error(f"Layer failed: {layer}, error: {error}")
            
        elif message.message_type == "background_started":
            task_id = message.payload.get("task_id")
            self.logger.info(f"Background task started: {task_id}")
            
        elif message.message_type == "background_completed":
            task_id = message.payload.get("task_id")
            success = message.payload.get("success")
            self.logger.info(f"Background task completed: {task_id}, success: {success}")
            
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        self.logger.info(f"Received signal {signum}, initiating shutdown")
        self._shutdown_event.set()
        
        # Cancel current execution
        if self.current_execution:
            asyncio.create_task(self.cancel_execution())
            
    async def shutdown(self):
        """Graceful shutdown of the orchestrator"""
        self.logger.info("Shutting down Test Orchestrator Agent")
        
        # Cancel current execution
        if self.current_execution:
            await self.cancel_execution()
            
        # Stop progress streaming
        self.progress_manager.stop_streaming()
        
        # Cleanup resources
        # (Add any necessary cleanup here)
        
        self.logger.info("Test Orchestrator Manager shutdown complete")


# CLI Integration Functions for unified_test_runner.py

def add_orchestrator_arguments(parser: 'argparse.ArgumentParser'):
    """Add orchestrator-specific arguments to the CLI parser"""
    orchestrator_group = parser.add_argument_group('Test Orchestrator Options')
    
    orchestrator_group.add_argument(
        '--use-layers',
        action='store_true',
        help='Use layered test orchestration system'
    )
    
    orchestrator_group.add_argument(
        '--layers',
        nargs='*',
        choices=['fast_feedback', 'core_integration', 'service_integration', 'e2e_background'],
        help='Specific layers to execute (default: determined by mode)'
    )
    
    orchestrator_group.add_argument(
        '--execution-mode',
        choices=['commit', 'ci', 'nightly', 'weekend', 'development'],
        default='development',
        help='Execution mode determining layer selection and configuration'
    )
    
    orchestrator_group.add_argument(
        '--show-layers',
        action='store_true',
        help='Show available layers and their configuration'
    )
    
    orchestrator_group.add_argument(
        '--background-e2e',
        action='store_true',
        help='Run E2E tests in background (non-blocking)'
    )
    
    orchestrator_group.add_argument(
        '--no-progress-streaming',
        action='store_true',
        help='Disable real-time progress streaming'
    )
    
    orchestrator_group.add_argument(
        '--max-parallel-layers',
        type=int,
        default=3,
        help='Maximum number of parallel layer executions'
    )


async def execute_with_orchestrator(args: 'argparse.Namespace') -> int:
    """
    Execute tests using the orchestrator system
    
    This function provides the integration point between unified_test_runner.py
    and the TestOrchestratorManager system.
    """
    # Initialize orchestrator
    orchestrator = TestOrchestratorManager()
    await orchestrator.initialize()
    
    try:
        # Handle special show commands
        if args.show_layers:
            layers = orchestrator.get_available_layers()
            print(f"\n{'='*60}")
            print("AVAILABLE TEST LAYERS")
            print(f"{'='*60}")
            
            for layer_name in layers:
                config = orchestrator.get_layer_configuration(layer_name)
                if config:
                    print(f"\n{layer_name}:")
                    print(f"  Categories: {', '.join(config['categories'])}")
                    print(f"  Execution Mode: {config['execution_mode']}")
                    print(f"  Estimated Duration: {config['estimated_duration']}")
                    print(f"  Dependencies: {', '.join(config['dependencies'])}")
                    print(f"  Services Required: {', '.join(config['services_required'])}")
            
            print(f"\nTotal Layers: {len(layers)}")
            return 0
            
        # Create orchestration config from arguments
        config = OrchestrationConfig(
            execution_mode=ExecutionMode(args.execution_mode),
            layers=args.layers if args.layers else None,
            environment=getattr(args, 'env', 'development'),
            use_background_e2e=args.background_e2e,
            enable_progress_streaming=not args.no_progress_streaming,
            max_parallel_layers=args.max_parallel_layers,
            force_real_services=getattr(args, 'real_services', False),
            force_real_llm=getattr(args, 'real_llm', False)
        )
        
        # Execute tests using orchestrator
        result = await orchestrator.execute_tests(config)
        
        # Print results
        print(f"\n{'='*60}")
        print("TEST EXECUTION RESULTS")
        print(f"{'='*60}")
        print(f"Success: {result.success}")
        print(f"Duration: {result.total_duration}")
        print(f"Layers Executed: {', '.join(result.layers_executed)}")
        print(f"Background Tasks: {len(result.background_tasks)}")
        
        if result.error_summary:
            print(f"Errors: {result.error_summary}")
            
        # Print layer-specific results
        for layer_name, layer_result in result.layer_results.items():
            print(f"\n{layer_name}:")
            if isinstance(layer_result, dict):
                print(f"  Success: {layer_result.get('success', False)}")
                print(f"  Total Tests: {layer_result.get('total_tests', 0)}")
                print(f"  Passed: {layer_result.get('passed_tests', 0)}")
                print(f"  Failed: {layer_result.get('failed_tests', 0)}")
                
        return 0 if result.success else 1
        
    except Exception as e:
        print(f"Orchestrator execution failed: {e}", file=sys.stderr)
        return 1
        
    finally:
        await orchestrator.shutdown()


def integrate_orchestrator_with_existing_runner():
    """
    Integration function to be called from unified_test_runner.py
    
    This function modifies the existing argument parser and execution flow
    to support the orchestrator system alongside the existing category system.
    """
    # This would be integrated into the main() function of unified_test_runner.py
    pass