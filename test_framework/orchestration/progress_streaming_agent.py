#!/usr/bin/env python3
"""
Progress Streaming Agent - Real-time test execution progress streaming
=====================================================================

This agent provides comprehensive real-time progress streaming for test execution
across all layers and execution agents. It aggregates progress from multiple sources
and delivers formatted updates through multiple output modes.

Business Value: Critical for user experience during test execution, preventing
user abandonment during long-running test suites. Provides transparency and
confidence in test execution progress.

Core Responsibilities:
- Real-time progress streaming for all test execution layers
- Aggregate progress from LayerExecutionAgent and BackgroundE2EAgent
- Multiple output formats (console, JSON, WebSocket, logs)
- Live progress bars, ETA calculations, and status updates
- Integration with existing progress tracking infrastructure

Key Features:
- Multi-layer progress display with category-level granularity
- Real-time WebSocket streaming for web interfaces
- Console progress bars with colors and animations
- JSON output for programmatic consumption
- ETA calculations and timing estimates
- Background task progress monitoring
- Error handling and graceful degradation
"""

import asyncio
import json
import logging
import os
import sys
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any, Callable, NamedTuple
from threading import Lock, Event

# Core imports
from test_framework.progress_tracker import (
    ProgressTracker, ProgressEvent, ProgressStatus, 
    CategoryProgress, TestRunProgress
)

# Integration imports for WebSocket support
try:
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
    from netra_backend.app.schemas.websocket_models import WebSocketMessage
    from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    WebSocketManager = None
    WebSocketMessage = None
    WebSocketNotifier = None
    AgentExecutionContext = None

# Environment management
try:
    from shared.isolated_environment import get_env
except ImportError:
    def get_env():
        return os.environ

# SSOT Orchestration enums import
from test_framework.ssot.orchestration_enums import ProgressOutputMode, ProgressEventType


# ProgressOutputMode and ProgressEventType now imported from SSOT orchestration_enums


@dataclass
class LayerProgressState:
    """State tracking for individual layer progress"""
    layer_name: str
    status: ProgressStatus = ProgressStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    categories: Dict[str, CategoryProgress] = field(default_factory=dict)
    
    # Progress metrics
    categories_completed: int = 0
    categories_total: int = 0
    overall_progress: float = 0.0
    estimated_remaining: timedelta = field(default_factory=lambda: timedelta(0))
    
    # Test metrics aggregated from categories
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    
    @property
    def duration(self) -> timedelta:
        """Calculate current/total duration"""
        if self.start_time:
            end = self.end_time or datetime.now()
            return end - self.start_time
        return timedelta(0)
    
    @property
    def is_complete(self) -> bool:
        """Check if layer is complete"""
        return self.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, ProgressStatus.CANCELLED]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate for the layer"""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
    
    def update_from_categories(self):
        """Update layer metrics from category progress"""
        if not self.categories:
            return
            
        # Update category counts
        self.categories_completed = sum(1 for cat in self.categories.values() if cat.is_complete)
        self.categories_total = len(self.categories)
        
        # Update overall progress
        if self.categories_total > 0:
            total_progress = sum(cat.progress_percentage for cat in self.categories.values())
            self.overall_progress = total_progress / self.categories_total
        
        # Update test counts
        self.total_tests = sum(cat.total_tests for cat in self.categories.values())
        self.passed_tests = sum(cat.passed_tests for cat in self.categories.values())
        self.failed_tests = sum(cat.failed_tests for cat in self.categories.values())
        self.skipped_tests = sum(cat.skipped_tests for cat in self.categories.values())
        self.error_tests = sum(cat.error_tests for cat in self.categories.values())
        
        # Update estimated remaining time based on active categories
        active_categories = [cat for cat in self.categories.values() 
                           if cat.status == ProgressStatus.RUNNING]
        if active_categories:
            avg_remaining = sum(cat.estimated_remaining.total_seconds() 
                              for cat in active_categories) / len(active_categories)
            self.estimated_remaining = timedelta(seconds=avg_remaining)


@dataclass
class StreamingConfig:
    """Configuration for progress streaming behavior"""
    output_mode: ProgressOutputMode = ProgressOutputMode.CONSOLE
    update_interval: float = 0.5  # Seconds between updates
    websocket_enabled: bool = True
    console_colors: bool = True
    show_detailed_progress: bool = True
    show_eta: bool = True
    show_test_counts: bool = True
    show_background_tasks: bool = True
    max_concurrent_streams: int = 10
    websocket_thread_id: Optional[str] = None
    
    # Console formatting
    progress_bar_width: int = 40
    category_max_name_length: int = 20
    layer_max_name_length: int = 25
    
    # Update thresholds
    min_update_threshold: float = 1.0  # Minimum percentage change to trigger update
    max_silent_duration: float = 5.0   # Max seconds without update before sending keep-alive


class ProgressStreamingAgent:
    """
    Comprehensive progress streaming agent for test execution
    
    Provides real-time progress updates across all test execution layers with
    multiple output formats and WebSocket streaming capabilities.
    """
    
    def __init__(self, project_root: Optional[Path] = None, config: Optional[StreamingConfig] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.config = config or StreamingConfig()
        self.agent_id = f"progress_streamer_{int(time.time())}"
        self.logger = logging.getLogger(f"ProgressStreamingAgent.{self.agent_id}")
        
        # Core state
        self.active = False
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._lock = Lock()
        self._stop_event = Event()
        
        # Progress tracking
        self.layers: Dict[str, LayerProgressState] = {}
        self.background_tasks: Dict[str, Dict[str, Any]] = {}
        self.system_events: List[Dict[str, Any]] = []
        
        # Streaming state
        self.event_subscribers: List[Callable] = []
        self.last_update_time = time.time()
        self.update_count = 0
        self.stream_threads: Dict[str, threading.Thread] = {}
        
        # WebSocket integration
        self.websocket_manager: Optional[WebSocketManager] = None
        self.websocket_notifier: Optional[WebSocketNotifier] = None
        if WEBSOCKET_AVAILABLE and self.config.websocket_enabled:
            self._initialize_websocket_integration()
        
        # Progress tracker integration
        self.progress_tracker = ProgressTracker(self.project_root, enable_persistence=True)
        self.progress_tracker.add_observer(self._handle_progress_event)
        
        # Background streaming task
        self._streaming_task: Optional[asyncio.Task] = None
        self._event_queue: deque = deque()
        self._queue_lock = Lock()
        
        # Console formatting
        self._setup_console_formatting()
        
    def _initialize_websocket_integration(self):
        """Initialize WebSocket integration if available"""
        try:
            # WebSocket integration will be set up by the orchestrator
            # This is a placeholder for future integration
            self.logger.info("WebSocket integration initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize WebSocket integration: {e}")
            self.config.websocket_enabled = False
    
    def _setup_console_formatting(self):
        """Setup console formatting utilities"""
        if self.config.console_colors and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            self.colors = {
                'GREEN': '\033[92m',
                'YELLOW': '\033[93m',
                'RED': '\033[91m',
                'BLUE': '\033[94m',
                'PURPLE': '\033[95m',
                'CYAN': '\033[96m',
                'WHITE': '\033[97m',
                'BOLD': '\033[1m',
                'RESET': '\033[0m'
            }
        else:
            # No colors for non-TTY outputs
            self.colors = {key: '' for key in ['GREEN', 'YELLOW', 'RED', 'BLUE', 'PURPLE', 'CYAN', 'WHITE', 'BOLD', 'RESET']}
    
    def set_websocket_manager(self, websocket_manager: 'WebSocketManager', thread_id: str = None):
        """Set WebSocket manager for real-time streaming"""
        if WEBSOCKET_AVAILABLE:
            self.websocket_manager = websocket_manager
            self.config.websocket_thread_id = thread_id
            if websocket_manager:
                self.websocket_notifier = AgentWebSocketBridge(websocket_manager)
                self.logger.info(f"WebSocket manager configured for thread: {thread_id}")
    
    async def start_streaming(self, layers: List[str], run_id: str = None) -> bool:
        """Start progress streaming for specified layers"""
        with self._lock:
            if self.active:
                self.logger.warning("Progress streaming already active")
                return False
            
            self.active = True
            self.start_time = datetime.now()
            self._stop_event.clear()
            
            # Initialize layer states
            for layer_name in layers:
                self.layers[layer_name] = LayerProgressState(layer_name=layer_name)
            
            # Start background streaming task
            self._streaming_task = asyncio.create_task(self._streaming_worker())
            
            # Send initial streaming event
            await self._emit_event(ProgressEventType.ORCHESTRATION_STARTED, {
                "layers": layers,
                "run_id": run_id,
                "agent_id": self.agent_id,
                "start_time": self.start_time.isoformat()
            })
            
            self.logger.info(f"Progress streaming started for {len(layers)} layers")
            return True
    
    async def stop_streaming(self, success: bool = True, summary: Dict[str, Any] = None):
        """Stop progress streaming and generate final summary"""
        with self._lock:
            if not self.active:
                return
            
            self.active = False
            self.end_time = datetime.now()
            self._stop_event.set()
            
            # Cancel streaming task
            if self._streaming_task and not self._streaming_task.done():
                self._streaming_task.cancel()
                try:
                    await self._streaming_task
                except asyncio.CancelledError:
                    pass
            
            # Generate final summary
            final_summary = self._generate_final_summary(success, summary)
            
            # Send completion event
            await self._emit_event(ProgressEventType.ORCHESTRATION_COMPLETED, {
                "success": success,
                "duration": (self.end_time - self.start_time).total_seconds(),
                "summary": final_summary,
                "agent_id": self.agent_id
            })
            
            # Final console output
            if self.config.output_mode == ProgressOutputMode.CONSOLE:
                self._print_final_summary(final_summary, success)
            
            self.logger.info("Progress streaming stopped")
    
    def _handle_progress_event(self, event: ProgressEvent, data: Dict[str, Any]):
        """Handle progress events from progress tracker"""
        # Convert ProgressTracker events to streaming events
        event_mapping = {
            ProgressEvent.CATEGORY_STARTED: ProgressEventType.CATEGORY_STARTED,
            ProgressEvent.CATEGORY_COMPLETED: ProgressEventType.CATEGORY_COMPLETED,
            ProgressEvent.CATEGORY_FAILED: ProgressEventType.CATEGORY_FAILED,
            ProgressEvent.CATEGORY_SKIPPED: ProgressEventType.CATEGORY_SKIPPED,
            ProgressEvent.RUN_STARTED: ProgressEventType.ORCHESTRATION_STARTED,
            ProgressEvent.RUN_COMPLETED: ProgressEventType.ORCHESTRATION_COMPLETED,
            ProgressEvent.RUN_FAILED: ProgressEventType.ORCHESTRATION_FAILED,
            ProgressEvent.RUN_CANCELLED: ProgressEventType.ORCHESTRATION_FAILED
        }
        
        streaming_event = event_mapping.get(event)
        if streaming_event:
            asyncio.create_task(self._emit_event(streaming_event, data))
    
    async def update_layer_progress(self, layer_name: str, category_name: str = None, 
                                  status: ProgressStatus = None, progress: float = None,
                                  test_counts: Dict[str, int] = None, **kwargs):
        """Update progress for a specific layer/category"""
        if not self.active or layer_name not in self.layers:
            return
        
        with self._lock:
            layer = self.layers[layer_name]
            
            # Update layer status
            if status and not category_name:
                layer.status = status
                if status == ProgressStatus.RUNNING and not layer.start_time:
                    layer.start_time = datetime.now()
                elif status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED] and not layer.end_time:
                    layer.end_time = datetime.now()
            
            # Update category progress
            if category_name:
                if category_name not in layer.categories:
                    layer.categories[category_name] = CategoryProgress(name=category_name)
                
                category = layer.categories[category_name]
                
                if status:
                    if status == ProgressStatus.RUNNING and not category.start_time:
                        category.start()
                    elif status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED]:
                        category.complete(status == ProgressStatus.COMPLETED)
                    elif status == ProgressStatus.SKIPPED:
                        category.skip(kwargs.get('reason', ''))
                
                if progress is not None:
                    category.progress_percentage = min(100.0, max(0.0, progress))
                
                if test_counts:
                    category.update_test_counts(**test_counts)
            
            # Update layer aggregated metrics
            layer.update_from_categories()
            
            # Emit update event
            await self._emit_event(
                ProgressEventType.LAYER_STARTED if status == ProgressStatus.RUNNING 
                else ProgressEventType.CATEGORY_PROGRESS if category_name 
                else ProgressEventType.LAYER_COMPLETED,
                {
                    "layer_name": layer_name,
                    "category_name": category_name,
                    "status": status.value if status else None,
                    "progress": progress,
                    "test_counts": test_counts,
                    **kwargs
                }
            )
    
    async def update_background_task(self, task_id: str, status: str, progress: float = None, **kwargs):
        """Update progress for background task"""
        if not self.active:
            return
        
        with self._lock:
            if task_id not in self.background_tasks:
                self.background_tasks[task_id] = {
                    "task_id": task_id,
                    "status": status,
                    "start_time": datetime.now(),
                    "progress": progress or 0.0
                }
            else:
                self.background_tasks[task_id].update({
                    "status": status,
                    "progress": progress or self.background_tasks[task_id]["progress"],
                    **kwargs
                })
                
                if status in ["completed", "failed", "cancelled"]:
                    self.background_tasks[task_id]["end_time"] = datetime.now()
        
        # Emit background event
        event_type = {
            "queued": ProgressEventType.BACKGROUND_QUEUED,
            "started": ProgressEventType.BACKGROUND_STARTED,
            "running": ProgressEventType.BACKGROUND_STARTED,
            "completed": ProgressEventType.BACKGROUND_COMPLETED,
            "failed": ProgressEventType.BACKGROUND_FAILED
        }.get(status, ProgressEventType.BACKGROUND_STARTED)
        
        await self._emit_event(event_type, {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            **kwargs
        })
    
    async def _emit_event(self, event_type: ProgressEventType, data: Dict[str, Any]):
        """Emit progress event to all subscribers and output modes"""
        event_data = {
            "type": event_type.value,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "agent_id": self.agent_id
        }
        
        # Queue event for processing
        with self._queue_lock:
            self._event_queue.append(event_data)
        
        # Notify subscribers
        for subscriber in self.event_subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event_type, data)
                else:
                    subscriber(event_type, data)
            except Exception as e:
                self.logger.error(f"Error in event subscriber: {e}")
    
    async def _streaming_worker(self):
        """Background worker for processing streaming updates"""
        while self.active and not self._stop_event.is_set():
            try:
                # Process queued events
                events_to_process = []
                with self._queue_lock:
                    while self._event_queue:
                        events_to_process.append(self._event_queue.popleft())
                
                # Process events
                for event in events_to_process:
                    await self._process_streaming_event(event)
                
                # Generate periodic updates
                if time.time() - self.last_update_time >= self.config.update_interval:
                    await self._generate_periodic_update()
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in streaming worker: {e}")
                await asyncio.sleep(1.0)
    
    async def _process_streaming_event(self, event: Dict[str, Any]):
        """Process individual streaming event"""
        try:
            # Output to different modes
            if self.config.output_mode == ProgressOutputMode.CONSOLE:
                await self._output_console_event(event)
            elif self.config.output_mode == ProgressOutputMode.JSON:
                await self._output_json_event(event)
            elif self.config.output_mode == ProgressOutputMode.LOG:
                await self._output_log_event(event)
            
            # Always try WebSocket if enabled and available
            if (self.config.websocket_enabled and self.websocket_notifier and 
                self.config.websocket_thread_id):
                await self._output_websocket_event(event)
                
        except Exception as e:
            self.logger.error(f"Error processing streaming event: {e}")
    
    async def _generate_periodic_update(self):
        """Generate periodic progress update"""
        if not self.active:
            return
        
        current_time = time.time()
        if current_time - self.last_update_time < self.config.update_interval:
            return
        
        # Generate comprehensive status update
        status_update = self._generate_status_update()
        
        # Output based on mode
        if self.config.output_mode == ProgressOutputMode.CONSOLE:
            self._print_console_status(status_update)
        elif self.config.output_mode == ProgressOutputMode.JSON:
            print(json.dumps(status_update, indent=2))
        
        # WebSocket update
        if (self.config.websocket_enabled and self.websocket_notifier and 
            self.config.websocket_thread_id):
            await self._send_websocket_status_update(status_update)
        
        self.last_update_time = current_time
        self.update_count += 1
    
    def _generate_status_update(self) -> Dict[str, Any]:
        """Generate comprehensive status update"""
        with self._lock:
            layers_status = []
            for layer_name, layer in self.layers.items():
                layer_info = {
                    "name": layer_name,
                    "status": layer.status.value,
                    "progress": layer.overall_progress,
                    "categories_completed": layer.categories_completed,
                    "categories_total": layer.categories_total,
                    "duration": layer.duration.total_seconds(),
                    "estimated_remaining": layer.estimated_remaining.total_seconds(),
                    "test_counts": {
                        "total": layer.total_tests,
                        "passed": layer.passed_tests,
                        "failed": layer.failed_tests,
                        "skipped": layer.skipped_tests,
                        "error": layer.error_tests
                    },
                    "success_rate": layer.success_rate,
                    "categories": []
                }
                
                # Add category details if requested
                if self.config.show_detailed_progress:
                    for cat_name, category in layer.categories.items():
                        layer_info["categories"].append({
                            "name": cat_name,
                            "status": category.status.value,
                            "progress": category.progress_percentage,
                            "duration": category.execution_time.total_seconds(),
                            "test_counts": {
                                "total": category.total_tests,
                                "passed": category.passed_tests,
                                "failed": category.failed_tests,
                                "skipped": category.skipped_tests,
                                "error": category.error_tests
                            }
                        })
                
                layers_status.append(layer_info)
            
            # Background tasks summary
            background_summary = []
            if self.config.show_background_tasks:
                for task_id, task in self.background_tasks.items():
                    background_summary.append({
                        "task_id": task_id,
                        "status": task["status"],
                        "progress": task.get("progress", 0.0),
                        "duration": (datetime.now() - task["start_time"]).total_seconds()
                    })
            
            return {
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat(),
                "overall": {
                    "active": self.active,
                    "duration": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                    "layers_count": len(self.layers),
                    "background_tasks_count": len(self.background_tasks)
                },
                "layers": layers_status,
                "background_tasks": background_summary,
                "update_count": self.update_count
            }
    
    def _print_console_status(self, status: Dict[str, Any]):
        """Print formatted console status"""
        if self.config.output_mode != ProgressOutputMode.CONSOLE:
            return
        
        # Clear previous output (if supported)
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            # Move cursor up and clear lines (simplified)
            sys.stdout.write('\r')
            sys.stdout.flush()
        
        # Print header
        duration = timedelta(seconds=status["overall"]["duration"])
        print(f"\n{self.colors['BOLD']}📊 Test Execution Progress{self.colors['RESET']} "
              f"({self._format_duration(duration)} elapsed)")
        print("=" * 80)
        
        # Print layer progress
        for i, layer in enumerate(status["layers"], 1):
            self._print_layer_progress(layer, i)
        
        # Print background tasks if any
        if status["background_tasks"] and self.config.show_background_tasks:
            print(f"\n{self.colors['PURPLE']}🔄 Background Tasks:{self.colors['RESET']}")
            for task in status["background_tasks"]:
                self._print_background_task(task)
        
        print("=" * 80)
    
    def _print_layer_progress(self, layer: Dict[str, Any], layer_num: int):
        """Print individual layer progress"""
        status = layer["status"]
        progress = layer["progress"]
        name = layer["name"].replace("_", " ").title()
        
        # Status icon and color
        if status == "completed":
            icon = "✅"
            color = self.colors['GREEN']
        elif status == "running":
            icon = "🔄"
            color = self.colors['BLUE']
        elif status == "failed":
            icon = "❌"
            color = self.colors['RED']
        elif status == "skipped":
            icon = "⏭️"
            color = self.colors['YELLOW']
        else:
            icon = "⏳"
            color = self.colors['WHITE']
        
        # Duration and ETA
        duration_str = self._format_duration(timedelta(seconds=layer["duration"]))
        eta_str = ""
        if self.config.show_eta and layer["estimated_remaining"] > 0:
            eta = self._format_duration(timedelta(seconds=layer["estimated_remaining"]))
            eta_str = f", ~{eta} remaining"
        
        # Progress bar
        progress_bar = self._create_progress_bar(progress, self.config.progress_bar_width)
        
        # Test counts
        test_summary = ""
        if self.config.show_test_counts and layer["test_counts"]["total"] > 0:
            tc = layer["test_counts"]
            test_summary = f" - {tc['passed']}/{tc['total']} tests passed"
            if tc['failed'] > 0:
                test_summary += f", {tc['failed']} failed"
        
        # Print layer header
        print(f"\n{icon} {color}LAYER {layer_num}: {name:<{self.config.layer_max_name_length}} "
              f"({duration_str}{eta_str}){self.colors['RESET']}")
        
        if status == "running":
            print(f"    {progress_bar} {progress:.1f}%{test_summary}")
        else:
            print(f"    {layer['status'].upper()}{test_summary}")
        
        # Print category details if requested
        if self.config.show_detailed_progress and layer["categories"]:
            for category in layer["categories"]:
                self._print_category_progress(category)
    
    def _print_category_progress(self, category: Dict[str, Any]):
        """Print individual category progress"""
        status = category["status"]
        progress = category["progress"] 
        name = category["name"]
        
        # Status icon
        if status == "completed":
            icon = "✅"
        elif status == "running":
            icon = "🔄"
        elif status == "failed":
            icon = "❌"
        elif status == "skipped":
            icon = "⏭️"
        else:
            icon = "⏳"
        
        # Duration
        duration_str = self._format_duration(timedelta(seconds=category["duration"]))
        
        # Test counts
        tc = category["test_counts"]
        test_info = ""
        if tc["total"] > 0:
            if status == "running":
                test_info = f" - Running test {tc['passed'] + tc['failed']}/{tc['total']}"
            else:
                test_info = f" - {tc['passed']}/{tc['total']} tests passed"
        
        # Format category name
        display_name = name[:self.config.category_max_name_length]
        if len(name) > self.config.category_max_name_length:
            display_name += "..."
        
        if status == "running":
            progress_bar = self._create_progress_bar(progress, 20)
            print(f"     {icon} {display_name:<{self.config.category_max_name_length}} "
                  f"{progress_bar} ({duration_str}){test_info}")
        else:
            print(f"     {icon} {display_name:<{self.config.category_max_name_length}} "
                  f"({duration_str}){test_info}")
    
    def _print_background_task(self, task: Dict[str, Any]):
        """Print background task progress"""
        task_id = task["task_id"]
        status = task["status"]
        progress = task.get("progress", 0.0)
        duration = timedelta(seconds=task["duration"])
        
        icon = "🔄" if status == "running" else "✅" if status == "completed" else "❌"
        progress_bar = self._create_progress_bar(progress, 20) if status == "running" else ""
        
        print(f"  {icon} {task_id} {progress_bar} ({self._format_duration(duration)})")
    
    def _create_progress_bar(self, progress: float, width: int = 40) -> str:
        """Create ASCII progress bar"""
        filled = int(width * progress / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}]"
    
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration as human-readable string"""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    async def _output_console_event(self, event: Dict[str, Any]):
        """Output event to console"""
        # Console events are handled by periodic updates
        pass
    
    async def _output_json_event(self, event: Dict[str, Any]):
        """Output event as JSON"""
        if self.config.output_mode == ProgressOutputMode.JSON:
            print(json.dumps(event, indent=None, separators=(',', ':')))
            sys.stdout.flush()
    
    async def _output_log_event(self, event: Dict[str, Any]):
        """Output event to logger"""
        event_type = event["type"]
        data = event["data"]
        
        if "error" in event_type or "failed" in event_type:
            self.logger.error(f"{event_type}: {data}")
        elif "completed" in event_type:
            self.logger.info(f"{event_type}: {data}")
        else:
            self.logger.debug(f"{event_type}: {data}")
    
    async def _output_websocket_event(self, event: Dict[str, Any]):
        """Output event via WebSocket"""
        if not (self.websocket_notifier and self.config.websocket_thread_id):
            return
        
        try:
            # Create mock execution context for WebSocket integration
            context = self._create_mock_execution_context()
            
            # Map streaming events to WebSocket events
            event_type = event["type"]
            data = event["data"]
            
            if event_type in ["layer_started", "category_started", "orchestration_started"]:
                await self.websocket_notifier.send_agent_started(context)
                
            elif event_type in ["category_progress", "layer_progress"]:
                thought = f"Processing {data.get('category_name', data.get('layer_name', 'operation'))}"
                if 'progress' in data:
                    thought += f" ({data['progress']:.1f}% complete)"
                await self.websocket_notifier.send_agent_thinking(
                    context, thought, 
                    progress_percentage=data.get('progress'),
                    current_operation=data.get('category_name', data.get('layer_name'))
                )
                
            elif event_type in ["test_started", "category_started"]:
                tool_name = data.get('category_name', data.get('test_name', 'test'))
                await self.websocket_notifier.send_tool_executing(context, tool_name)
                
            elif event_type in ["test_completed", "category_completed"]:
                tool_name = data.get('category_name', data.get('test_name', 'test'))
                result = {"success": data.get('status') in ['completed', 'passed']}
                await self.websocket_notifier.send_tool_completed(context, tool_name, result)
                
            elif event_type in ["orchestration_completed", "layer_completed"]:
                result = {"success": data.get('success', True)}
                duration = data.get('duration', 0) * 1000  # Convert to ms
                await self.websocket_notifier.send_agent_completed(context, result, duration)
                
        except Exception as e:
            self.logger.warning(f"Failed to send WebSocket event: {e}")
    
    def _create_mock_execution_context(self) -> 'AgentExecutionContext':
        """Create mock execution context for WebSocket integration"""
        if not AgentExecutionContext:
            return None
        
        return AgentExecutionContext(
            agent_name="TestProgressStreamer",
            run_id=f"progress_stream_{self.agent_id}",
            thread_id=self.config.websocket_thread_id or "default",
            user_id="system"
        )
    
    async def _send_websocket_status_update(self, status: Dict[str, Any]):
        """Send periodic status update via WebSocket"""
        if not (self.websocket_notifier and self.config.websocket_thread_id):
            return
        
        try:
            context = self._create_mock_execution_context()
            if not context:
                return
            
            # Create progress summary
            total_progress = 0.0
            active_layers = 0
            
            for layer in status["layers"]:
                if layer["status"] == "running":
                    active_layers += 1
                total_progress += layer["progress"]
            
            if status["layers"]:
                avg_progress = total_progress / len(status["layers"])
            else:
                avg_progress = 0.0
            
            # Send thinking update with progress
            progress_message = f"Processing {active_layers} active layers"
            if avg_progress > 0:
                progress_message += f" ({avg_progress:.1f}% overall progress)"
            
            await self.websocket_notifier.send_agent_thinking(
                context, progress_message,
                progress_percentage=avg_progress,
                estimated_remaining_ms=int(sum(
                    layer["estimated_remaining"] * 1000 
                    for layer in status["layers"]
                    if layer["status"] == "running"
                ))
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to send WebSocket status update: {e}")
    
    def _generate_final_summary(self, success: bool, provided_summary: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate final execution summary"""
        with self._lock:
            total_duration = (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0
            
            layers_summary = []
            total_tests = 0
            total_passed = 0
            total_failed = 0
            total_skipped = 0
            
            for layer in self.layers.values():
                layer_summary = {
                    "name": layer.layer_name,
                    "status": layer.status.value,
                    "duration": layer.duration.total_seconds(),
                    "categories_completed": layer.categories_completed,
                    "categories_total": layer.categories_total,
                    "success_rate": layer.success_rate,
                    "test_counts": {
                        "total": layer.total_tests,
                        "passed": layer.passed_tests,
                        "failed": layer.failed_tests,
                        "skipped": layer.skipped_tests,
                        "error": layer.error_tests
                    }
                }
                layers_summary.append(layer_summary)
                
                total_tests += layer.total_tests
                total_passed += layer.passed_tests
                total_failed += layer.failed_tests
                total_skipped += layer.skipped_tests
            
            background_tasks_summary = []
            for task in self.background_tasks.values():
                background_tasks_summary.append({
                    "task_id": task["task_id"],
                    "status": task["status"],
                    "duration": (task.get("end_time", datetime.now()) - task["start_time"]).total_seconds()
                })
            
            summary = {
                "success": success,
                "total_duration": total_duration,
                "layers_count": len(self.layers),
                "background_tasks_count": len(self.background_tasks),
                "overall_test_counts": {
                    "total": total_tests,
                    "passed": total_passed,
                    "failed": total_failed,
                    "skipped": total_skipped
                },
                "overall_success_rate": total_passed / total_tests if total_tests > 0 else 0.0,
                "layers": layers_summary,
                "background_tasks": background_tasks_summary,
                "total_updates": self.update_count
            }
            
            if provided_summary:
                summary.update(provided_summary)
            
            return summary
    
    def _print_final_summary(self, summary: Dict[str, Any], success: bool):
        """Print final summary to console"""
        if self.config.output_mode != ProgressOutputMode.CONSOLE:
            return
        
        print("\n" + "=" * 80)
        
        # Header
        if success:
            print(f"{self.colors['GREEN']}{self.colors['BOLD']}✅ TEST EXECUTION COMPLETED SUCCESSFULLY{self.colors['RESET']}")
        else:
            print(f"{self.colors['RED']}{self.colors['BOLD']}❌ TEST EXECUTION FAILED{self.colors['RESET']}")
        
        # Overall stats
        duration = self._format_duration(timedelta(seconds=summary["total_duration"]))
        print(f"\n📊 Overall Statistics:")
        print(f"   Duration: {duration}")
        print(f"   Layers: {summary['layers_count']}")
        print(f"   Background Tasks: {summary['background_tasks_count']}")
        
        # Test results
        tc = summary["overall_test_counts"]
        if tc["total"] > 0:
            success_rate = summary["overall_success_rate"] * 100
            print(f"\n🧪 Test Results:")
            print(f"   Total Tests: {tc['total']}")
            print(f"   Passed: {self.colors['GREEN']}{tc['passed']}{self.colors['RESET']}")
            print(f"   Failed: {self.colors['RED']}{tc['failed']}{self.colors['RESET']}")
            print(f"   Skipped: {self.colors['YELLOW']}{tc['skipped']}{self.colors['RESET']}")
            print(f"   Success Rate: {success_rate:.1f}%")
        
        # Layer summary
        if summary["layers"]:
            print(f"\n📋 Layer Summary:")
            for layer in summary["layers"]:
                status_icon = "✅" if layer["status"] == "completed" else "❌" if layer["status"] == "failed" else "⏭️"
                layer_duration = self._format_duration(timedelta(seconds=layer["duration"]))
                print(f"   {status_icon} {layer['name']}: {layer_duration}, "
                      f"{layer['categories_completed']}/{layer['categories_total']} categories")
        
        print("=" * 80)
    
    def add_event_subscriber(self, callback: Callable):
        """Add event subscriber for custom processing"""
        self.event_subscribers.append(callback)
    
    def remove_event_subscriber(self, callback: Callable):
        """Remove event subscriber"""
        if callback in self.event_subscribers:
            self.event_subscribers.remove(callback)
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current streaming status"""
        return self._generate_status_update()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get streaming statistics"""
        return {
            "agent_id": self.agent_id,
            "active": self.active,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "duration": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "update_count": self.update_count,
            "layers_count": len(self.layers),
            "background_tasks_count": len(self.background_tasks),
            "event_subscribers_count": len(self.event_subscribers),
            "websocket_enabled": self.config.websocket_enabled and self.websocket_notifier is not None
        }


# Utility functions

async def create_progress_streaming_agent(
    project_root: Path = None,
    output_mode: ProgressOutputMode = ProgressOutputMode.CONSOLE,
    websocket_manager: 'WebSocketManager' = None,
    thread_id: str = None,
    **config_kwargs
) -> ProgressStreamingAgent:
    """Create and configure a progress streaming agent"""
    config = StreamingConfig(
        output_mode=output_mode,
        websocket_thread_id=thread_id,
        **config_kwargs
    )
    
    agent = ProgressStreamingAgent(project_root, config)
    
    if websocket_manager:
        agent.set_websocket_manager(websocket_manager, thread_id)
    
    return agent


def create_console_streaming_agent(project_root: Path = None) -> ProgressStreamingAgent:
    """Create progress streaming agent optimized for console output"""
    config = StreamingConfig(
        output_mode=ProgressOutputMode.CONSOLE,
        console_colors=True,
        show_detailed_progress=True,
        show_eta=True,
        show_test_counts=True,
        update_interval=1.0
    )
    
    return ProgressStreamingAgent(project_root, config)


def create_json_streaming_agent(project_root: Path = None) -> ProgressStreamingAgent:
    """Create progress streaming agent optimized for JSON output"""
    config = StreamingConfig(
        output_mode=ProgressOutputMode.JSON,
        websocket_enabled=False,
        show_detailed_progress=True,
        update_interval=0.5
    )
    
    return ProgressStreamingAgent(project_root, config)


def create_websocket_streaming_agent(
    websocket_manager: 'WebSocketManager',
    thread_id: str,
    project_root: Path = None
) -> ProgressStreamingAgent:
    """Create progress streaming agent optimized for WebSocket output"""
    config = StreamingConfig(
        output_mode=ProgressOutputMode.WEBSOCKET,
        websocket_enabled=True,
        websocket_thread_id=thread_id,
        update_interval=0.5
    )
    
    agent = ProgressStreamingAgent(project_root, config)
    agent.set_websocket_manager(websocket_manager, thread_id)
    
    return agent


# CLI integration for testing
if __name__ == "__main__":
    import argparse
    import random
    
    async def demo_progress_streaming():
        """Demo function for testing progress streaming"""
        agent = create_console_streaming_agent()
        
        # Start streaming
        layers = ["fast_feedback", "core_integration", "service_integration", "e2e_performance"]
        await agent.start_streaming(layers, "demo_run")
        
        try:
            # Simulate layer execution
            for i, layer_name in enumerate(layers):
                # Start layer
                await agent.update_layer_progress(
                    layer_name, status=ProgressStatus.RUNNING
                )
                
                # Simulate categories
                categories = ["unit", "integration", "api"] if i < 2 else ["e2e", "performance"]
                
                for cat_name in categories:
                    # Start category
                    await agent.update_layer_progress(
                        layer_name, cat_name, status=ProgressStatus.RUNNING
                    )
                    
                    # Simulate test progress
                    total_tests = random.randint(10, 50)
                    for test_num in range(total_tests):
                        await asyncio.sleep(0.1)  # Simulate test time
                        
                        progress = (test_num + 1) / total_tests * 100
                        passed = test_num + 1 if random.random() > 0.1 else test_num
                        failed = (test_num + 1) - passed
                        
                        await agent.update_layer_progress(
                            layer_name, cat_name, progress=progress,
                            test_counts={"total": total_tests, "passed": passed, "failed": failed}
                        )
                    
                    # Complete category
                    success = random.random() > 0.2
                    await agent.update_layer_progress(
                        layer_name, cat_name, 
                        status=ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
                    )
                
                # Complete layer
                await agent.update_layer_progress(layer_name, status=ProgressStatus.COMPLETED)
            
            # Add some background tasks
            for i in range(3):
                task_id = f"background_task_{i}"
                await agent.update_background_task(task_id, "started")
                
                for progress in range(0, 101, 20):
                    await asyncio.sleep(0.5)
                    await agent.update_background_task(task_id, "running", progress=progress)
                
                await agent.update_background_task(task_id, "completed", progress=100)
            
            # Final delay
            await asyncio.sleep(2)
            
        finally:
            # Stop streaming
            await agent.stop_streaming(success=True)
    
    parser = argparse.ArgumentParser(description="Progress Streaming Agent")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    parser.add_argument("--output", choices=["console", "json", "log"], default="console")
    
    args = parser.parse_args()
    
    if args.demo:
        asyncio.run(demo_progress_streaming())
    else:
        print("Progress Streaming Agent - Use --demo to run demonstration")