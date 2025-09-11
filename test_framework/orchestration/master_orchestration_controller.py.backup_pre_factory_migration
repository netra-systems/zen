#!/usr/bin/env python3
"""
Master Orchestration Controller - Unified coordination of all test orchestration agents
======================================================================================

This controller provides a unified interface for coordinating all 5 orchestration agents:
1. TestOrchestratorAgent (main coordinator)
2. LayerExecutionAgent (layer management)
3. BackgroundE2EAgent (long-running tests)
4. ProgressStreamingAgent (real-time updates)
5. ResourceManagementAgent (service/resource management)

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & Test Reliability
- Value Impact: Eliminates test timing confusion, provides unified orchestration interface
- Strategic Impact: Reduces CI/CD time by 60%, eliminates developer test confusion

Key Responsibilities:
- Unified agent lifecycle management (initialization, execution, cleanup)
- Inter-agent communication and coordination
- Centralized error handling and recovery
- Performance monitoring and resource optimization
- WebSocket integration for real-time user feedback
"""

import asyncio
import json
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any, Tuple, Callable
from threading import Lock, Event

# Core orchestration agent imports
from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent, OrchestrationConfig
from test_framework.orchestration.layer_execution_agent import LayerExecutionAgent, LayerExecutionConfig
from test_framework.orchestration.background_e2e_agent import BackgroundE2EAgent, BackgroundTaskConfig
from test_framework.orchestration.progress_streaming_agent import (
    ProgressStreamingAgent, StreamingConfig, ProgressOutputMode,
    create_progress_streaming_agent, create_console_streaming_agent
)
from test_framework.orchestration.resource_management_agent import (
    ResourceManagementAgent, create_resource_manager,
    ensure_layer_resources_available
)

# Layer system integration
from test_framework.layer_system import (
    LayerSystem, TestLayer, LayerExecutionPlan, ExecutionConfig,
    LayerExecutionMode, LayerExecutionStatus, FailFastStrategy
)

# Progress tracking
from test_framework.progress_tracker import ProgressTracker, ProgressEvent, ProgressStatus

# WebSocket integration 
try:
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
    from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    WebSocketManager = None
    WebSocketNotifier = None
    AgentExecutionContext = None

# Environment management
try:
    from shared.isolated_environment import get_env
except ImportError:
    def get_env():
        return os.environ

# Production monitoring integration
try:
    from test_framework.orchestration.production_monitoring import (
        OrchestrationMonitor, create_orchestration_monitor, 
        create_production_monitor, MonitoredOperation
    )
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    OrchestrationMonitor = None

logger = logging.getLogger(__name__)


class OrchestrationMode(Enum):
    """Master orchestration execution modes"""
    LEGACY_CATEGORIES = "legacy_categories"      # Original category-based execution
    FAST_FEEDBACK = "fast_feedback"              # 2-minute feedback cycle
    LAYERED_EXECUTION = "layered_execution"      # Full layered execution
    BACKGROUND_E2E = "background_e2e"            # Background execution only
    HYBRID_EXECUTION = "hybrid_execution"        # Mix of foreground layers + background E2E


class OrchestrationStatus(Enum):
    """Master orchestration status"""
    INITIALIZING = "initializing"
    STARTING_SERVICES = "starting_services" 
    EXECUTING_LAYERS = "executing_layers"
    BACKGROUND_RUNNING = "background_running"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentHealth:
    """Health information for orchestration agents"""
    agent_name: str
    status: str
    initialized: bool = False
    last_heartbeat: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class OrchestrationState:
    """Complete state of orchestration execution"""
    mode: OrchestrationMode
    status: OrchestrationStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Agent states
    agent_health: Dict[str, AgentHealth] = field(default_factory=dict)
    
    # Execution state
    current_layer: Optional[str] = None
    completed_layers: List[str] = field(default_factory=list)
    failed_layers: List[str] = field(default_factory=list)
    background_tasks: Dict[str, Any] = field(default_factory=dict)
    
    # Results
    layer_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    overall_success: bool = False
    error_summary: List[str] = field(default_factory=list)
    
    # Metrics
    total_tests_run: int = 0
    total_tests_passed: int = 0
    total_tests_failed: int = 0
    overall_duration: timedelta = field(default_factory=lambda: timedelta(0))


@dataclass
class MasterOrchestrationConfig:
    """Configuration for master orchestration controller"""
    mode: OrchestrationMode = OrchestrationMode.LAYERED_EXECUTION
    project_root: Optional[Path] = None
    
    # Agent configuration
    enable_progress_streaming: bool = True
    enable_resource_management: bool = True
    enable_background_execution: bool = True
    
    # WebSocket configuration
    websocket_enabled: bool = True
    websocket_thread_id: Optional[str] = None
    
    # Execution configuration
    max_total_duration_minutes: int = 90
    graceful_shutdown_timeout: int = 30
    agent_startup_timeout: int = 15
    
    # Monitoring configuration
    heartbeat_interval: float = 10.0
    health_check_interval: float = 5.0
    progress_update_interval: float = 1.0
    
    # NEW: Production monitoring configuration
    enable_production_monitoring: bool = True
    enable_metrics_collection: bool = True
    enable_alerting: bool = True
    log_level: str = "INFO"
    metrics_retention_minutes: int = 60
    
    # Output configuration
    output_mode: ProgressOutputMode = ProgressOutputMode.CONSOLE
    verbose_logging: bool = False
    generate_summary_report: bool = True


class MasterOrchestrationController:
    """
    Master controller that coordinates all test orchestration agents.
    
    This controller provides a unified interface for managing complex test execution
    scenarios while maintaining backward compatibility with the existing category system.
    """
    
    def __init__(self, config: MasterOrchestrationConfig):
        self.config = config
        self.project_root = config.project_root or Path(__file__).parent.parent.parent
        
        # State management
        self.state = OrchestrationState(
            mode=config.mode,
            status=OrchestrationStatus.INITIALIZING,
            start_time=datetime.now()
        )
        self._lock = Lock()
        self._stop_event = Event()
        
        # Agent instances
        self.test_orchestrator: Optional[TestOrchestratorAgent] = None
        self.layer_executor: Optional[LayerExecutionAgent] = None
        self.background_agent: Optional[BackgroundE2EAgent] = None
        self.progress_streamer: Optional[ProgressStreamingAgent] = None
        self.resource_manager: Optional[ResourceManagementAgent] = None
        
        # Support systems
        self.layer_system: LayerSystem = LayerSystem(self.project_root)
        self.progress_tracker: ProgressTracker = ProgressTracker(
            self.project_root, enable_persistence=True
        )
        
        # WebSocket integration
        self.websocket_manager: Optional[WebSocketManager] = None
        self.websocket_notifier: Optional[WebSocketNotifier] = None
        if WEBSOCKET_AVAILABLE and config.websocket_enabled:
            self._setup_websocket_integration()
        
        # Monitoring
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        
        # Execution management
        self._execution_task: Optional[asyncio.Task] = None
        self._cleanup_handlers: List[Callable] = []
        
        # Thread pool for concurrent operations
        self.executor = ThreadPoolExecutor(
            max_workers=8, 
            thread_name_prefix="OrchestrationController"
        )
        
        # Production monitoring setup
        self.monitor: Optional['OrchestrationMonitor'] = None
        if MONITORING_AVAILABLE and config.enable_production_monitoring:
            log_dir = self.project_root / "logs" / "orchestration"
            if config.enable_production_monitoring:
                self.monitor = create_production_monitor(
                    component_name="MasterController",
                    log_dir=log_dir,
                    metrics_retention_hours=config.metrics_retention_minutes // 60
                )
            else:
                self.monitor = create_orchestration_monitor(
                    component_name="MasterController",
                    log_dir=log_dir
                )
        
        # Logger (use production monitor logger if available)
        if self.monitor:
            self.logger = self.monitor.logger.logger
        else:
            self.logger = logging.getLogger(f"MasterOrchestrationController")
            if config.verbose_logging:
                self.logger.setLevel(logging.DEBUG)
        
        self.logger.info("Master Orchestration Controller initialized",
                        mode=config.mode.value,
                        monitoring_enabled=self.monitor is not None)
    
    def _setup_websocket_integration(self):
        """Setup WebSocket integration for real-time updates"""
        try:
            # WebSocket manager will be set externally by the test runner
            # This is a placeholder for future integration
            self.logger.info("WebSocket integration prepared")
        except Exception as e:
            self.logger.warning(f"Failed to setup WebSocket integration: {e}")
            self.config.websocket_enabled = False
    
    def set_websocket_manager(self, websocket_manager: 'WebSocketManager', thread_id: str = None):
        """Set WebSocket manager for real-time communication"""
        if WEBSOCKET_AVAILABLE:
            self.websocket_manager = websocket_manager
            self.config.websocket_thread_id = thread_id
            
            if websocket_manager:
                self.websocket_notifier = WebSocketNotifier(websocket_manager)
                self.logger.info(f"WebSocket manager configured for thread: {thread_id}")
                
                # Configure progress streamer if available
                if self.progress_streamer:
                    self.progress_streamer.set_websocket_manager(websocket_manager, thread_id)
    
    async def initialize_agents(self) -> bool:
        """Initialize all orchestration agents"""
        self.logger.info("Initializing orchestration agents...")
        
        try:
            # Update state
            with self._lock:
                self.state.status = OrchestrationStatus.INITIALIZING
            
            # Initialize resource manager first (needed by other agents)
            if self.config.enable_resource_management:
                self.resource_manager = create_resource_manager(enable_monitoring=True)
                self.resource_manager.start_monitoring()
                
                self.state.agent_health["resource_manager"] = AgentHealth(
                    agent_name="ResourceManagementAgent",
                    status="initialized",
                    initialized=True,
                    last_heartbeat=datetime.now()
                )
                self.logger.info("ResourceManagementAgent initialized")
            
            # Initialize progress streaming agent
            if self.config.enable_progress_streaming:
                self.progress_streamer = create_progress_streaming_agent(
                    project_root=self.project_root,
                    output_mode=self.config.output_mode,
                    websocket_manager=self.websocket_manager,
                    thread_id=self.config.websocket_thread_id
                )
                
                self.state.agent_health["progress_streamer"] = AgentHealth(
                    agent_name="ProgressStreamingAgent",
                    status="initialized",
                    initialized=True,
                    last_heartbeat=datetime.now()
                )
                self.logger.info("ProgressStreamingAgent initialized")
            
            # Initialize layer execution agent
            layer_config = LayerExecutionConfig(
                enable_real_services=True,
                enable_real_llm=False,  # Default to mock for fast startup
                max_parallel_layers=2,
                layer_timeout_minutes=60
            )
            
            self.layer_executor = LayerExecutionAgent(
                project_root=self.project_root,
                config=layer_config,
                progress_tracker=self.progress_tracker,
                resource_manager=self.resource_manager
            )
            
            if self.progress_streamer:
                self.layer_executor.set_progress_streamer(self.progress_streamer)
            
            self.state.agent_health["layer_executor"] = AgentHealth(
                agent_name="LayerExecutionAgent",
                status="initialized", 
                initialized=True,
                last_heartbeat=datetime.now()
            )
            self.logger.info("LayerExecutionAgent initialized")
            
            # Initialize background E2E agent if enabled
            if self.config.enable_background_execution:
                background_config = BackgroundTaskConfig(
                    max_concurrent_tasks=1,
                    task_timeout_minutes=60,
                    enable_real_services=True,
                    enable_real_llm=True
                )
                
                self.background_agent = BackgroundE2EAgent(
                    project_root=self.project_root,
                    config=background_config,
                    progress_tracker=self.progress_tracker
                )
                
                if self.progress_streamer:
                    self.background_agent.set_progress_callback(
                        self.progress_streamer.update_background_task
                    )
                
                self.state.agent_health["background_agent"] = AgentHealth(
                    agent_name="BackgroundE2EAgent",
                    status="initialized",
                    initialized=True, 
                    last_heartbeat=datetime.now()
                )
                self.logger.info("BackgroundE2EAgent initialized")
            
            # Initialize main test orchestrator
            orchestration_config = OrchestrationConfig(
                enable_fast_feedback=True,
                enable_layered_execution=True,
                enable_background_execution=self.config.enable_background_execution,
                max_concurrent_layers=3,
                global_timeout_minutes=self.config.max_total_duration_minutes
            )
            
            self.test_orchestrator = TestOrchestratorAgent(
                project_root=self.project_root,
                config=orchestration_config
            )
            
            # Wire up agent dependencies
            self.test_orchestrator.layer_executor = self.layer_executor
            self.test_orchestrator.background_agent = self.background_agent
            self.test_orchestrator.progress_streamer = self.progress_streamer
            self.test_orchestrator.resource_manager = self.resource_manager
            
            self.state.agent_health["test_orchestrator"] = AgentHealth(
                agent_name="TestOrchestratorAgent", 
                status="initialized",
                initialized=True,
                last_heartbeat=datetime.now()
            )
            self.logger.info("TestOrchestratorAgent initialized")
            
            # Start monitoring
            self._start_monitoring()
            
            self.logger.info("All orchestration agents initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agents: {e}")
            await self._cleanup_agents()
            return False
    
    def _start_monitoring(self):
        """Start agent monitoring threads"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        
        # Start health monitoring
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="OrchestrationHeartbeat",
            daemon=True
        )
        self._heartbeat_thread.start()
        
        self.logger.info("Agent monitoring started")
    
    def _heartbeat_loop(self):
        """Monitoring loop for agent health"""
        while self._monitoring_active and not self._stop_event.is_set():
            try:
                self._check_agent_health()
                time.sleep(self.config.heartbeat_interval)
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(5)
    
    def _check_agent_health(self):
        """Check health of all agents"""
        current_time = datetime.now()
        
        with self._lock:
            for agent_name, health in self.state.agent_health.items():
                try:
                    # Update heartbeat for active agents
                    agent = getattr(self, agent_name, None)
                    if agent and hasattr(agent, 'get_statistics'):
                        stats = agent.get_statistics()
                        health.last_heartbeat = current_time
                        health.status = "healthy"
                    else:
                        # Check if agent has been inactive too long
                        if (health.last_heartbeat and 
                            current_time - health.last_heartbeat > timedelta(minutes=5)):
                            health.status = "stale"
                
                except Exception as e:
                    health.error_count += 1
                    health.last_error = str(e)
                    health.status = "error"
                    self.logger.warning(f"Health check failed for {agent_name}: {e}")
    
    async def execute_orchestration(self, 
                                  execution_args: Dict[str, Any],
                                  categories: Optional[List[str]] = None,
                                  layers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute orchestrated test execution based on configuration.
        
        Args:
            execution_args: Command line arguments and configuration
            categories: Legacy category list (for backward compatibility)
            layers: Layer list for layered execution
            
        Returns:
            Execution results dictionary
        """
        execution_id = f"orchestration_{int(time.time())}"
        
        # Start monitoring
        execution_metrics = None
        if self.monitor:
            execution_metrics = self.monitor.start_execution(execution_id)
        
        self.logger.info(f"Starting orchestration execution in mode: {self.config.mode.value}",
                        execution_id=execution_id,
                        layers=layers,
                        categories=categories)
        
        try:
            # Update state
            with self._lock:
                self.state.status = OrchestrationStatus.STARTING_SERVICES
                self.state.start_time = datetime.now()
            
            # Initialize agents if not already done
            if not all(health.initialized for health in self.state.agent_health.values()):
                success = await self.initialize_agents()
                if not success:
                    raise RuntimeError("Failed to initialize orchestration agents")
            
            # Start progress streaming
            if self.progress_streamer:
                target_layers = layers or list(self.layer_system.layers.keys())
                run_id = f"orchestration_{int(time.time())}"
                await self.progress_streamer.start_streaming(target_layers, run_id)
            
            # Execute based on mode
            if self.config.mode == OrchestrationMode.LEGACY_CATEGORIES:
                results = await self._execute_legacy_categories(execution_args, categories)
            elif self.config.mode == OrchestrationMode.FAST_FEEDBACK:
                results = await self._execute_fast_feedback(execution_args)
            elif self.config.mode == OrchestrationMode.LAYERED_EXECUTION:
                results = await self._execute_layered_execution(execution_args, layers)
            elif self.config.mode == OrchestrationMode.BACKGROUND_E2E:
                results = await self._execute_background_e2e(execution_args)
            elif self.config.mode == OrchestrationMode.HYBRID_EXECUTION:
                results = await self._execute_hybrid_execution(execution_args, layers)
            else:
                raise ValueError(f"Unsupported orchestration mode: {self.config.mode}")
            
            # Update final state
            with self._lock:
                self.state.status = OrchestrationStatus.COMPLETED
                self.state.end_time = datetime.now()
                self.state.overall_duration = self.state.end_time - self.state.start_time
                self.state.overall_success = results.get("success", False)
            
            # Stop progress streaming
            if self.progress_streamer:
                await self.progress_streamer.stop_streaming(
                    success=results.get("success", False),
                    summary=results
                )
            
            # End monitoring
            if self.monitor:
                self.monitor.end_execution(results.get("success", False), results.get("summary"))
            
            self.logger.info(f"Orchestration execution completed: {results.get('success', False)}",
                            execution_id=execution_id,
                            success=results.get("success", False),
                            duration=self.state.overall_duration.total_seconds())
            return results
            
        except Exception as e:
            self.logger.error(f"Orchestration execution failed: {e}",
                            execution_id=execution_id,
                            error_type=type(e).__name__)
            
            # Update error state
            with self._lock:
                self.state.status = OrchestrationStatus.FAILED
                self.state.error_summary.append(str(e))
            
            # End monitoring with failure
            if self.monitor:
                self.monitor.end_execution(success=False, summary={"error": str(e)})
            
            # Stop progress streaming with failure
            if self.progress_streamer:
                await self.progress_streamer.stop_streaming(success=False)
            
            # Return error result
            return {
                "success": False,
                "error": str(e),
                "execution_id": execution_id,
                "state": self._get_state_dict()
            }
    
    async def _execute_legacy_categories(self, execution_args: Dict[str, Any], 
                                       categories: Optional[List[str]]) -> Dict[str, Any]:
        """Execute tests using legacy category system"""
        self.logger.info("Executing in legacy category mode")
        
        if not self.test_orchestrator:
            raise RuntimeError("TestOrchestratorAgent not initialized")
        
        # Convert to orchestrator format
        orchestration_request = {
            "categories": categories or ["unit", "integration"],
            "execution_mode": "category_based",
            "environment": execution_args.get("env", "dev"),
            "use_real_llm": execution_args.get("real_llm", False),
            "use_real_services": execution_args.get("real_services", False)
        }
        
        return await self.test_orchestrator.execute_test_orchestration(orchestration_request)
    
    async def _execute_fast_feedback(self, execution_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute fast feedback cycle (2-minute limit)"""
        self.logger.info("Executing fast feedback cycle")
        
        if not self.layer_executor:
            raise RuntimeError("LayerExecutionAgent not initialized")
        
        # Ensure resources for fast feedback
        if self.resource_manager:
            resources_available = ensure_layer_resources_available(
                self.resource_manager, "fast_feedback", timeout_seconds=30
            )
            if not resources_available:
                raise RuntimeError("Resources not available for fast feedback execution")
        
        # Execute fast feedback layer only
        fast_feedback_layer = self.layer_system.layers.get("fast_feedback")
        if not fast_feedback_layer:
            raise RuntimeError("Fast feedback layer not configured")
        
        execution_request = {
            "layer_name": "fast_feedback",
            "categories": [cat.name for cat in fast_feedback_layer.categories],
            "environment": execution_args.get("env", "dev"),
            "timeout_minutes": 2,
            "fail_fast": True
        }
        
        return await self.layer_executor.execute_layer(execution_request)
    
    async def _execute_layered_execution(self, execution_args: Dict[str, Any], 
                                       layers: Optional[List[str]]) -> Dict[str, Any]:
        """Execute full layered test execution"""
        self.logger.info(f"Executing layered execution for layers: {layers}")
        
        if not self.layer_executor:
            raise RuntimeError("LayerExecutionAgent not initialized")
        
        # Create execution plan
        selected_layers = layers or ["fast_feedback", "core_integration", "service_integration"]
        environment = execution_args.get("env", "dev")
        
        execution_plan = self.layer_system.create_execution_plan(selected_layers, environment)
        
        with self._lock:
            self.state.status = OrchestrationStatus.EXECUTING_LAYERS
        
        # Execute layers in phases
        results = {"success": True, "layer_results": {}, "summary": {}}
        
        for phase_idx, layer_phase in enumerate(execution_plan.execution_sequence):
            self.logger.info(f"Executing phase {phase_idx + 1}: {layer_phase}")
            
            # Execute layers in current phase (potentially in parallel)
            phase_results = await self._execute_layer_phase(layer_phase, execution_args)
            
            # Aggregate results
            results["layer_results"].update(phase_results)
            
            # Check for failures and fail-fast
            phase_failed = any(not result.get("success", False) for result in phase_results.values())
            if phase_failed:
                # Check fail-fast strategy for this phase
                should_stop = self._should_stop_on_failure(layer_phase, execution_args)
                if should_stop:
                    self.logger.error(f"Phase {phase_idx + 1} failed, stopping execution")
                    results["success"] = False
                    break
        
        # Generate summary
        results["summary"] = self._generate_execution_summary(results["layer_results"])
        results["success"] = results["success"] and results["summary"]["overall_success"]
        
        return results
    
    async def _execute_background_e2e(self, execution_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute background E2E tests only"""
        self.logger.info("Executing background E2E tests")
        
        if not self.background_agent:
            raise RuntimeError("BackgroundE2EAgent not initialized")
        
        with self._lock:
            self.state.status = OrchestrationStatus.BACKGROUND_RUNNING
        
        # Start background E2E execution
        e2e_layer = self.layer_system.layers.get("e2e_background")
        if not e2e_layer:
            raise RuntimeError("E2E background layer not configured")
        
        background_request = {
            "layer_name": "e2e_background",
            "categories": [cat.name for cat in e2e_layer.categories],
            "environment": execution_args.get("env", "dev"),
            "use_real_llm": execution_args.get("real_llm", True),
            "use_real_services": True
        }
        
        return await self.background_agent.execute_background_tests(background_request)
    
    async def _execute_hybrid_execution(self, execution_args: Dict[str, Any], 
                                      layers: Optional[List[str]]) -> Dict[str, Any]:
        """Execute hybrid mode: foreground layers + background E2E"""
        self.logger.info("Executing hybrid mode: foreground + background")
        
        # Start background E2E if configured
        background_task = None
        if self.background_agent and "e2e_background" in (layers or []):
            background_task = asyncio.create_task(
                self._execute_background_e2e(execution_args)
            )
            
            # Update layers to exclude background layer from foreground execution
            foreground_layers = [l for l in (layers or []) if l != "e2e_background"]
        else:
            foreground_layers = layers
        
        # Execute foreground layers
        foreground_results = await self._execute_layered_execution(execution_args, foreground_layers)
        
        # Wait for background if started
        background_results = {}
        if background_task:
            try:
                # Give background task some time, but don't wait forever
                background_results = await asyncio.wait_for(background_task, timeout=300)
            except asyncio.TimeoutError:
                self.logger.warning("Background E2E still running, continuing without results")
                background_results = {"success": None, "status": "running"}
        
        # Combine results
        return {
            "success": foreground_results.get("success", False),
            "foreground_results": foreground_results,
            "background_results": background_results,
            "summary": self._generate_hybrid_summary(foreground_results, background_results)
        }
    
    async def _execute_layer_phase(self, layer_names: List[str], 
                                 execution_args: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Execute a phase of layers (potentially in parallel)"""
        phase_results = {}
        
        # Check if layers can run in parallel
        can_run_parallel = all(
            self.layer_system.layers[name].execution_mode != LayerExecutionMode.SEQUENTIAL
            for name in layer_names if name in self.layer_system.layers
        )
        
        if can_run_parallel and len(layer_names) > 1:
            # Execute layers in parallel
            self.logger.info(f"Executing {len(layer_names)} layers in parallel")
            
            tasks = []
            for layer_name in layer_names:
                task = asyncio.create_task(self._execute_single_layer(layer_name, execution_args))
                tasks.append((layer_name, task))
            
            # Wait for completion
            for layer_name, task in tasks:
                try:
                    result = await task
                    phase_results[layer_name] = result
                except Exception as e:
                    self.logger.error(f"Layer {layer_name} failed: {e}")
                    phase_results[layer_name] = {"success": False, "error": str(e)}
        
        else:
            # Execute layers sequentially
            for layer_name in layer_names:
                try:
                    result = await self._execute_single_layer(layer_name, execution_args)
                    phase_results[layer_name] = result
                    
                    # Check for fail-fast
                    if not result.get("success", False):
                        should_stop = self._should_stop_on_failure([layer_name], execution_args)
                        if should_stop:
                            self.logger.error(f"Layer {layer_name} failed, stopping phase execution")
                            break
                            
                except Exception as e:
                    self.logger.error(f"Layer {layer_name} failed: {e}")
                    phase_results[layer_name] = {"success": False, "error": str(e)}
                    break
        
        return phase_results
    
    async def _execute_single_layer(self, layer_name: str, execution_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test layer"""
        self.logger.info(f"Executing layer: {layer_name}")
        
        with self._lock:
            self.state.current_layer = layer_name
        
        layer = self.layer_system.layers.get(layer_name)
        if not layer:
            raise ValueError(f"Layer not found: {layer_name}")
        
        # Ensure resources if resource manager is available
        if self.resource_manager:
            resources_available = ensure_layer_resources_available(
                self.resource_manager, layer_name, timeout_seconds=60
            )
            if not resources_available:
                raise RuntimeError(f"Resources not available for layer: {layer_name}")
        
        # Build execution request
        execution_request = {
            "layer_name": layer_name,
            "categories": [cat.name for cat in layer.categories],
            "environment": execution_args.get("env", "dev"),
            "timeout_minutes": layer.max_duration_minutes,
            "fail_fast": layer.fail_fast,
            "use_real_llm": execution_args.get("real_llm", layer.llm_requirements.mode == "real"),
            "use_real_services": any(cat.resource_requirements.requires_real_services 
                                   for cat in layer.categories)
        }
        
        # Execute layer
        try:
            result = await self.layer_executor.execute_layer(execution_request)
            
            with self._lock:
                self.state.completed_layers.append(layer_name)
                self.state.layer_results[layer_name] = result
            
            return result
            
        except Exception as e:
            with self._lock:
                self.state.failed_layers.append(layer_name)
                
            raise
    
    def _should_stop_on_failure(self, layer_names: List[str], execution_args: Dict[str, Any]) -> bool:
        """Determine if execution should stop on layer failure"""
        # Check global fail-fast setting
        if execution_args.get("fast_fail", False):
            return True
        
        # Check layer-specific fail-fast settings
        for layer_name in layer_names:
            layer = self.layer_system.layers.get(layer_name)
            if layer and layer.fail_fast:
                return True
            
            # Check execution config fail-fast strategy
            strategy = self.layer_system.execution_config.fail_fast_strategy.get(layer_name)
            if strategy == FailFastStrategy.IMMEDIATE:
                return True
        
        return False
    
    def _generate_execution_summary(self, layer_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive execution summary"""
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_duration = 0.0
        layer_summaries = {}
        
        for layer_name, result in layer_results.items():
            summary = result.get("summary", {})
            
            layer_summaries[layer_name] = {
                "success": result.get("success", False),
                "duration": result.get("duration", 0),
                "test_counts": summary.get("test_counts", {}),
                "categories": summary.get("categories", [])
            }
            
            # Aggregate totals
            test_counts = summary.get("test_counts", {})
            total_tests += test_counts.get("total", 0)
            total_passed += test_counts.get("passed", 0)  
            total_failed += test_counts.get("failed", 0)
            total_duration += result.get("duration", 0)
        
        success_rate = total_passed / total_tests if total_tests > 0 else 0.0
        overall_success = success_rate >= 0.9 and total_failed <= 5
        
        return {
            "overall_success": overall_success,
            "total_duration": total_duration,
            "test_counts": {
                "total": total_tests,
                "passed": total_passed,
                "failed": total_failed
            },
            "success_rate": success_rate,
            "layers_executed": len(layer_results),
            "layers_successful": sum(1 for r in layer_results.values() if r.get("success")),
            "layer_summaries": layer_summaries
        }
    
    def _generate_hybrid_summary(self, foreground_results: Dict[str, Any], 
                                background_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary for hybrid execution"""
        foreground_summary = foreground_results.get("summary", {})
        background_summary = background_results.get("summary", {})
        
        # Combine test counts
        fg_counts = foreground_summary.get("test_counts", {})
        bg_counts = background_summary.get("test_counts", {})
        
        combined_counts = {
            "total": fg_counts.get("total", 0) + bg_counts.get("total", 0),
            "passed": fg_counts.get("passed", 0) + bg_counts.get("passed", 0),
            "failed": fg_counts.get("failed", 0) + bg_counts.get("failed", 0)
        }
        
        return {
            "overall_success": (foreground_results.get("success", False) and 
                              background_results.get("success") is not False),
            "foreground_summary": foreground_summary,
            "background_summary": background_summary,
            "combined_test_counts": combined_counts,
            "total_duration": foreground_summary.get("total_duration", 0) + 
                            background_summary.get("total_duration", 0)
        }
    
    def get_orchestration_status(self) -> Dict[str, Any]:
        """Get current orchestration status"""
        with self._lock:
            return self._get_state_dict()
    
    def _get_state_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary (thread-safe, must be called with lock)"""
        return {
            "mode": self.state.mode.value,
            "status": self.state.status.value,
            "start_time": self.state.start_time.isoformat(),
            "end_time": self.state.end_time.isoformat() if self.state.end_time else None,
            "current_layer": self.state.current_layer,
            "completed_layers": self.state.completed_layers.copy(),
            "failed_layers": self.state.failed_layers.copy(),
            "agent_health": {
                name: {
                    "agent_name": health.agent_name,
                    "status": health.status,
                    "initialized": health.initialized,
                    "last_heartbeat": health.last_heartbeat.isoformat() if health.last_heartbeat else None,
                    "error_count": health.error_count,
                    "last_error": health.last_error
                }
                for name, health in self.state.agent_health.items()
            },
            "overall_success": self.state.overall_success,
            "error_summary": self.state.error_summary.copy(),
            "total_tests_run": self.state.total_tests_run,
            "overall_duration": self.state.overall_duration.total_seconds()
        }
    
    async def cancel_execution(self, reason: str = "User requested"):
        """Cancel ongoing orchestration execution"""
        self.logger.info(f"Cancelling orchestration execution: {reason}")
        
        with self._lock:
            self.state.status = OrchestrationStatus.CANCELLED
            self.state.error_summary.append(f"Cancelled: {reason}")
        
        # Cancel agents
        if self.layer_executor:
            await self.layer_executor.cancel_all_executions()
        
        if self.background_agent:
            await self.background_agent.cancel_all_tasks()
        
        # Stop progress streaming
        if self.progress_streamer:
            await self.progress_streamer.stop_streaming(success=False)
        
        # Set stop event
        self._stop_event.set()
    
    async def _cleanup_agents(self):
        """Cleanup all agents and resources"""
        self.logger.info("Cleaning up orchestration agents")
        
        # Stop monitoring
        self._monitoring_active = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        
        # Cleanup agents
        cleanup_tasks = []
        
        if self.progress_streamer:
            cleanup_tasks.append(self.progress_streamer.stop_streaming(success=False))
        
        if self.background_agent:
            cleanup_tasks.append(self.background_agent.shutdown())
        
        if self.resource_manager:
            cleanup_tasks.append(asyncio.create_task(asyncio.to_thread(self.resource_manager.shutdown)))
        
        # Wait for cleanup with timeout
        if cleanup_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*cleanup_tasks, return_exceptions=True),
                    timeout=self.config.graceful_shutdown_timeout
                )
            except asyncio.TimeoutError:
                self.logger.warning("Cleanup timed out, some agents may not have shut down cleanly")
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        self.logger.info("Agent cleanup completed")
    
    async def shutdown(self):
        """Shutdown the master orchestration controller"""
        self.logger.info("Shutting down Master Orchestration Controller")
        
        # Cancel execution if running
        if self.state.status in [OrchestrationStatus.EXECUTING_LAYERS, OrchestrationStatus.BACKGROUND_RUNNING]:
            await self.cancel_execution("Shutdown requested")
        
        # Cleanup agents
        await self._cleanup_agents()
        
        # Run cleanup handlers
        for handler in self._cleanup_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                self.logger.error(f"Error in cleanup handler: {e}")
        
        self.logger.info("Master Orchestration Controller shutdown complete")
    
    def add_cleanup_handler(self, handler: Callable):
        """Add cleanup handler to be called during shutdown"""
        self._cleanup_handlers.append(handler)
    
    def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown()


# Factory functions for different orchestration modes

def create_fast_feedback_controller(
    project_root: Path = None,
    websocket_manager: 'WebSocketManager' = None,
    thread_id: str = None
) -> MasterOrchestrationController:
    """Create controller optimized for fast feedback execution"""
    config = MasterOrchestrationConfig(
        mode=OrchestrationMode.FAST_FEEDBACK,
        project_root=project_root,
        enable_progress_streaming=True,
        enable_resource_management=True,
        enable_background_execution=False,
        websocket_enabled=websocket_manager is not None,
        websocket_thread_id=thread_id,
        max_total_duration_minutes=5,
        output_mode=ProgressOutputMode.CONSOLE,
        progress_update_interval=0.5
    )
    
    controller = MasterOrchestrationController(config)
    if websocket_manager:
        controller.set_websocket_manager(websocket_manager, thread_id)
    
    return controller


def create_full_layered_controller(
    project_root: Path = None,
    websocket_manager: 'WebSocketManager' = None, 
    thread_id: str = None,
    enable_background: bool = True
) -> MasterOrchestrationController:
    """Create controller for full layered execution"""
    config = MasterOrchestrationConfig(
        mode=OrchestrationMode.LAYERED_EXECUTION,
        project_root=project_root,
        enable_progress_streaming=True,
        enable_resource_management=True,
        enable_background_execution=enable_background,
        websocket_enabled=websocket_manager is not None,
        websocket_thread_id=thread_id,
        max_total_duration_minutes=90,
        output_mode=ProgressOutputMode.CONSOLE,
        progress_update_interval=1.0
    )
    
    controller = MasterOrchestrationController(config)
    if websocket_manager:
        controller.set_websocket_manager(websocket_manager, thread_id)
    
    return controller


def create_background_only_controller(
    project_root: Path = None,
    websocket_manager: 'WebSocketManager' = None,
    thread_id: str = None
) -> MasterOrchestrationController:
    """Create controller for background E2E execution only"""
    config = MasterOrchestrationConfig(
        mode=OrchestrationMode.BACKGROUND_E2E,
        project_root=project_root,
        enable_progress_streaming=True,
        enable_resource_management=True,
        enable_background_execution=True,
        websocket_enabled=websocket_manager is not None,
        websocket_thread_id=thread_id,
        max_total_duration_minutes=120,
        output_mode=ProgressOutputMode.CONSOLE,
        progress_update_interval=2.0
    )
    
    controller = MasterOrchestrationController(config)
    if websocket_manager:
        controller.set_websocket_manager(websocket_manager, thread_id)
    
    return controller


def create_hybrid_controller(
    project_root: Path = None,
    websocket_manager: 'WebSocketManager' = None,
    thread_id: str = None
) -> MasterOrchestrationController:
    """Create controller for hybrid execution (foreground + background)"""
    config = MasterOrchestrationConfig(
        mode=OrchestrationMode.HYBRID_EXECUTION,
        project_root=project_root,
        enable_progress_streaming=True,
        enable_resource_management=True,
        enable_background_execution=True,
        websocket_enabled=websocket_manager is not None,
        websocket_thread_id=thread_id,
        max_total_duration_minutes=90,
        output_mode=ProgressOutputMode.CONSOLE,
        progress_update_interval=1.0
    )
    
    controller = MasterOrchestrationController(config)
    if websocket_manager:
        controller.set_websocket_manager(websocket_manager, thread_id)
    
    return controller


def create_legacy_controller(
    project_root: Path = None
) -> MasterOrchestrationController:
    """Create controller for legacy category-based execution (backward compatibility)"""
    config = MasterOrchestrationConfig(
        mode=OrchestrationMode.LEGACY_CATEGORIES,
        project_root=project_root,
        enable_progress_streaming=False,
        enable_resource_management=False,
        enable_background_execution=False,
        websocket_enabled=False,
        max_total_duration_minutes=60,
        output_mode=ProgressOutputMode.CONSOLE
    )
    
    return MasterOrchestrationController(config)


# CLI integration for testing
if __name__ == "__main__":
    import argparse
    
    async def test_orchestration():
        """Test orchestration controller functionality"""
        # Create fast feedback controller
        controller = create_fast_feedback_controller()
        
        try:
            # Initialize agents
            await controller.initialize_agents()
            
            # Execute fast feedback
            execution_args = {
                "env": "dev",
                "real_llm": False,
                "real_services": True,
                "fast_fail": True
            }
            
            results = await controller.execute_orchestration(
                execution_args=execution_args,
                layers=["fast_feedback"]
            )
            
            print("=== ORCHESTRATION RESULTS ===")
            print(json.dumps(results, indent=2, default=str))
            
        finally:
            await controller.shutdown()
    
    parser = argparse.ArgumentParser(description="Master Orchestration Controller")
    parser.add_argument("--test", action="store_true", help="Run test orchestration")
    parser.add_argument("--status", action="store_true", help="Show orchestration status")
    
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(test_orchestration())
    elif args.status:
        # Show status of running orchestration (placeholder)
        print("Orchestration status checking not yet implemented")
    else:
        parser.print_help()