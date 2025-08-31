#!/usr/bin/env python3
"""
Background E2E Manager - Non-blocking execution of long-running E2E tests

This manager manages the execution of resource-intensive E2E tests (cypress, e2e, performance)
in background processes without blocking development workflows.

CORE RESPONSIBILITIES:
1. Execute long-running E2E tests in detached background processes
2. Manage test queues and scheduling for resource-intensive tests
3. Provide non-blocking execution with real-time progress monitoring
4. Handle service dependencies and resource coordination
5. Persist test results and provide status tracking

E2E TEST CATEGORIES HANDLED:
- cypress: Cypress E2E tests (20+ minutes, requires full stack)
- e2e: Full end-to-end user journey tests (30+ minutes)
- performance: Load and performance tests (30+ minutes)
- e2e_critical: Critical E2E tests that can run in foreground (5 minutes)

INTEGRATION:
- Works with existing Cypress runner from test_framework/cypress_runner.py
- Integrates with unified_test_runner.py execution pipeline
- Uses existing service availability checks
- Coordinates with ResourceManagementManager for service dependencies
- Reports to ProgressStreamingManager for real-time updates

FEATURES:
- FIFO queue system for background test execution
- Process lifecycle management (start, monitor, cleanup)
- Real-time status tracking of running/queued tests
- Persistent storage of background test results
- Graceful failure recovery and resource cleanup
- CPU/memory limits for background processes
- Service coordination and dependency management
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from queue import Queue, Empty
from threading import Lock, Event
from typing import Dict, List, Optional, Set, Union, Any, Callable, Tuple, NamedTuple
import uuid
import psutil

# Core imports
from test_framework.cypress_runner import CypressTestRunner, CypressExecutionOptions
from test_framework.service_availability import ServiceAvailabilityChecker, require_real_services

# Environment management
try:
    from shared.isolated_environment import get_env
except ImportError:
    get_env = lambda k, d=None: os.environ.get(k, d)

# Progress tracking integration
try:
    from test_framework.orchestration.test_orchestrator_manager import ManagerCommunicationMessage
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False
    ManagerCommunicationMessage = None


class BackgroundTaskStatus(Enum):
    """Status of background E2E tasks"""
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class E2ETestCategory(Enum):
    """E2E test categories handled by background manager"""
    CYPRESS = "cypress"
    E2E = "e2e"
    PERFORMANCE = "performance"
    E2E_CRITICAL = "e2e_critical"


@dataclass
class BackgroundTaskConfig:
    """Configuration for background E2E task execution"""
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


@dataclass
class BackgroundTaskResult:
    """Result of background E2E task execution"""
    task_id: str
    category: E2ETestCategory
    status: BackgroundTaskStatus
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    test_counts: Dict[str, int] = field(default_factory=dict)
    error_message: Optional[str] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueuedTask:
    """Queued background E2E task"""
    task_id: str
    category: E2ETestCategory
    config: BackgroundTaskConfig
    created_at: datetime
    priority: int = 1
    
    def __lt__(self, other):
        """For priority queue ordering (lower priority number = higher priority)"""
        return self.priority < other.priority


class BackgroundProcessManager:
    """Manages background subprocess lifecycle with resource monitoring"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logger = logging.getLogger(f"BackgroundProcessManager")
        self.processes: Dict[str, subprocess.Popen] = {}
        self.process_info: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        
    def start_background_process(self, task_id: str, cmd: List[str], 
                                config: BackgroundTaskConfig,
                                cwd: Optional[Path] = None) -> subprocess.Popen:
        """Start a background process with resource monitoring"""
        with self.lock:
            try:
                # Prepare environment
                env = os.environ.copy()
                env.update(config.env_vars)
                
                # Set resource limits if specified
                preexec_fn = None
                if config.cpu_limit_percent or config.memory_limit_gb:
                    preexec_fn = self._create_resource_limiter(config)
                
                # Start process
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=env,
                    cwd=str(cwd or self.project_root),
                    preexec_fn=preexec_fn
                )
                
                # Track process
                self.processes[task_id] = process
                self.process_info[task_id] = {
                    "pid": process.pid,
                    "cmd": cmd,
                    "start_time": datetime.now(),
                    "config": config
                }
                
                self.logger.info(f"Started background process for task {task_id} (PID: {process.pid})")
                return process
                
            except Exception as e:
                self.logger.error(f"Failed to start background process for task {task_id}: {e}")
                raise
    
    def _create_resource_limiter(self, config: BackgroundTaskConfig) -> Callable:
        """Create resource limiting function for subprocess"""
        def limit_resources():
            try:
                import resource
                
                # Set CPU limit (nice value)
                if config.cpu_limit_percent:
                    # Higher nice value = lower priority
                    nice_value = min(19, max(0, int((100 - config.cpu_limit_percent) / 5)))
                    os.nice(nice_value)
                
                # Set memory limit
                if config.memory_limit_gb:
                    memory_bytes = config.memory_limit_gb * 1024 * 1024 * 1024
                    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                    
            except Exception as e:
                # Resource limiting is best-effort
                pass
                
        return limit_resources
    
    def get_process_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of background process"""
        with self.lock:
            if task_id not in self.processes:
                return None
                
            process = self.processes[task_id]
            info = self.process_info[task_id]
            
            try:
                # Get resource usage if process is still running
                resource_usage = {}
                if process.poll() is None:
                    try:
                        ps_process = psutil.Process(process.pid)
                        resource_usage = {
                            "cpu_percent": ps_process.cpu_percent(),
                            "memory_mb": ps_process.memory_info().rss / 1024 / 1024,
                            "status": ps_process.status()
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                return {
                    "pid": process.pid,
                    "returncode": process.returncode,
                    "running": process.poll() is None,
                    "start_time": info["start_time"].isoformat(),
                    "duration_seconds": (datetime.now() - info["start_time"]).total_seconds(),
                    "resource_usage": resource_usage
                }
                
            except Exception as e:
                self.logger.error(f"Error getting process status for task {task_id}: {e}")
                return None
    
    def terminate_process(self, task_id: str, timeout: int = 10) -> bool:
        """Terminate background process gracefully"""
        with self.lock:
            if task_id not in self.processes:
                return True
                
            process = self.processes[task_id]
            
            try:
                if process.poll() is None:
                    # Try graceful termination first
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        # Force kill if graceful termination fails
                        process.kill()
                        process.wait(timeout=5)
                
                # Clean up
                del self.processes[task_id]
                del self.process_info[task_id]
                
                self.logger.info(f"Terminated background process for task {task_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error terminating process for task {task_id}: {e}")
                return False
    
    def cleanup_all_processes(self):
        """Clean up all tracked processes"""
        task_ids = list(self.processes.keys())
        for task_id in task_ids:
            self.terminate_process(task_id)


class BackgroundResultsManager:
    """Manages persistent storage and retrieval of background test results"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results_dir = project_root / "test_reports" / "background_e2e"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("BackgroundResultsManager")
        self.lock = Lock()
    
    def save_result(self, result: BackgroundTaskResult):
        """Save background task result to persistent storage"""
        with self.lock:
            try:
                result_file = self.results_dir / f"{result.task_id}.json"
                result_data = asdict(result)
                
                # Convert datetime objects to ISO strings
                if result_data.get("start_time"):
                    result_data["start_time"] = result.start_time.isoformat()
                if result_data.get("end_time"):
                    result_data["end_time"] = result.end_time.isoformat()
                
                # Convert enum to string
                result_data["status"] = result.status.value
                result_data["category"] = result.category.value
                
                with open(result_file, 'w') as f:
                    json.dump(result_data, f, indent=2)
                    
                self.logger.debug(f"Saved result for task {result.task_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to save result for task {result.task_id}: {e}")
    
    def load_result(self, task_id: str) -> Optional[BackgroundTaskResult]:
        """Load background task result from persistent storage"""
        with self.lock:
            try:
                result_file = self.results_dir / f"{task_id}.json"
                if not result_file.exists():
                    return None
                    
                with open(result_file, 'r') as f:
                    result_data = json.load(f)
                
                # Convert ISO strings back to datetime objects
                if result_data.get("start_time"):
                    result_data["start_time"] = datetime.fromisoformat(result_data["start_time"])
                if result_data.get("end_time"):
                    result_data["end_time"] = datetime.fromisoformat(result_data["end_time"])
                
                # Convert strings back to enums
                result_data["status"] = BackgroundTaskStatus(result_data["status"])
                result_data["category"] = E2ETestCategory(result_data["category"])
                
                return BackgroundTaskResult(**result_data)
                
            except Exception as e:
                self.logger.error(f"Failed to load result for task {task_id}: {e}")
                return None
    
    def list_results(self, category: Optional[E2ETestCategory] = None, 
                    since: Optional[datetime] = None) -> List[BackgroundTaskResult]:
        """List background task results with optional filtering"""
        with self.lock:
            results = []
            try:
                for result_file in self.results_dir.glob("*.json"):
                    result = self.load_result(result_file.stem)
                    if result:
                        # Apply filters
                        if category and result.category != category:
                            continue
                        if since and result.start_time and result.start_time < since:
                            continue
                        results.append(result)
                
                # Sort by start time (newest first)
                results.sort(key=lambda r: r.start_time or datetime.min, reverse=True)
                return results
                
            except Exception as e:
                self.logger.error(f"Failed to list results: {e}")
                return []
    
    def cleanup_old_results(self, keep_days: int = 30):
        """Clean up old result files"""
        with self.lock:
            try:
                cutoff_time = datetime.now() - timedelta(days=keep_days)
                cleaned = 0
                
                for result_file in self.results_dir.glob("*.json"):
                    if result_file.stat().st_mtime < cutoff_time.timestamp():
                        result_file.unlink()
                        cleaned += 1
                
                if cleaned > 0:
                    self.logger.info(f"Cleaned up {cleaned} old result files")
                    
            except Exception as e:
                self.logger.error(f"Failed to cleanup old results: {e}")


class BackgroundE2EManager:
    """
    Background E2E Manager for non-blocking execution of long-running E2E tests
    
    This manager provides comprehensive background execution capabilities for:
    - Cypress E2E tests (20+ minutes)
    - Full E2E user journey tests (30+ minutes) 
    - Performance and load tests (30+ minutes)
    - Critical E2E tests (can also run in foreground, 5 minutes)
    
    KEY FEATURES:
    1. Queue System: FIFO queue with priority support for background test execution
    2. Process Management: Start, monitor, and cleanup background processes
    3. Status Tracking: Real-time status of running/queued background tests
    4. Result Storage: Persistent storage of background test results
    5. Failure Recovery: Handle background test failures gracefully
    6. Resource Management: CPU/memory limits for background processes
    7. Service Coordination: Ensure required services are available before execution
    """
    
    def __init__(self, project_root: Optional[Path] = None, manager_id: Optional[str] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.manager_id = manager_id or f"background_e2e_{int(time.time())}"
        self.logger = logging.getLogger(f"BackgroundE2EManager.{self.manager_id}")
        
        # Core components
        self.process_manager = BackgroundProcessManager(self.project_root)
        self.results_manager = BackgroundResultsManager(self.project_root)
        self.service_checker = ServiceAvailabilityChecker(self.project_root)
        
        # Queue management
        self.task_queue: Queue[QueuedTask] = Queue()
        self.active_tasks: Dict[str, QueuedTask] = {}
        self.task_results: Dict[str, BackgroundTaskResult] = {}
        self.queue_lock = Lock()
        
        # Execution state
        self.is_running = False
        self.shutdown_event = Event()
        self.worker_thread: Optional[threading.Thread] = None
        self.max_concurrent_tasks = 2  # Limit concurrent background tasks
        
        # Service integration
        self.cypress_runner: Optional[CypressTestRunner] = None
        self.communication = None  # Will be set if orchestrator is available
        
        # Initialize Cypress runner lazily to avoid Docker issues
        self._cypress_runner_initialized = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info(f"Initialized BackgroundE2EManager with ID: {self.manager_id}")
    
    def start(self):
        """Start the background E2E manager"""
        if self.is_running:
            self.logger.warning("BackgroundE2EManager is already running")
            return
            
        self.logger.info("Starting BackgroundE2EManager")
        self.is_running = True
        self.shutdown_event.clear()
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        self.logger.info("BackgroundE2EManager started successfully")
    
    def stop(self):
        """Stop the background E2E manager gracefully"""
        if not self.is_running:
            return
            
        self.logger.info("Stopping BackgroundE2EManager")
        self.is_running = False
        self.shutdown_event.set()
        
        # Wait for worker thread to finish
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=10)
        
        # Clean up active processes
        self.process_manager.cleanup_all_processes()
        
        self.logger.info("BackgroundE2EManager stopped successfully")
    
    def queue_e2e_test(self, category: E2ETestCategory, 
                      config: Optional[BackgroundTaskConfig] = None) -> str:
        """
        Queue an E2E test for background execution
        
        Args:
            category: E2E test category to execute
            config: Task configuration (uses defaults if not provided)
            
        Returns:
            Task ID for tracking the queued test
        """
        if config is None:
            config = BackgroundTaskConfig(category=category)
        else:
            config.category = category
        
        task_id = str(uuid.uuid4())
        queued_task = QueuedTask(
            task_id=task_id,
            category=category,
            config=config,
            created_at=datetime.now(),
            priority=config.priority
        )
        
        with self.queue_lock:
            self.task_queue.put(queued_task)
            
        self.logger.info(f"Queued {category.value} test with task ID: {task_id}")
        
        # Notify orchestrator if available
        if self.communication:
            asyncio.create_task(self._notify_orchestrator("task_queued", {
                "task_id": task_id,
                "category": category.value
            }))
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific background task"""
        # Check active tasks first
        with self.queue_lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                process_status = self.process_manager.get_process_status(task_id)
                
                return {
                    "task_id": task_id,
                    "category": task.category.value,
                    "status": BackgroundTaskStatus.RUNNING.value,
                    "created_at": task.created_at.isoformat(),
                    "process_info": process_status
                }
        
        # Check completed results
        if task_id in self.task_results:
            result = self.task_results[task_id]
            return {
                "task_id": task_id,
                "category": result.category.value,
                "status": result.status.value,
                "exit_code": result.exit_code,
                "duration_seconds": result.duration_seconds,
                "start_time": result.start_time.isoformat() if result.start_time else None,
                "end_time": result.end_time.isoformat() if result.end_time else None
            }
        
        # Check persistent storage
        result = self.results_manager.load_result(task_id)
        if result:
            return {
                "task_id": task_id,
                "category": result.category.value,
                "status": result.status.value,
                "exit_code": result.exit_code,
                "duration_seconds": result.duration_seconds,
                "start_time": result.start_time.isoformat() if result.start_time else None,
                "end_time": result.end_time.isoformat() if result.end_time else None
            }
        
        return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current status of the background queue"""
        with self.queue_lock:
            # Count queued tasks by category
            queued_by_category = {}
            temp_queue = Queue()
            
            while not self.task_queue.empty():
                try:
                    task = self.task_queue.get_nowait()
                    temp_queue.put(task)
                    category = task.category.value
                    queued_by_category[category] = queued_by_category.get(category, 0) + 1
                except Empty:
                    break
            
            # Restore queue
            while not temp_queue.empty():
                self.task_queue.put(temp_queue.get_nowait())
            
            return {
                "manager_running": self.is_running,
                "queued_tasks": self.task_queue.qsize(),
                "active_tasks": len(self.active_tasks),
                "queued_by_category": queued_by_category,
                "active_task_ids": list(self.active_tasks.keys())
            }
    
    def get_recent_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent background test results"""
        results = self.results_manager.list_results()[:limit]
        return [
            {
                "task_id": result.task_id,
                "category": result.category.value,
                "status": result.status.value,
                "exit_code": result.exit_code,
                "duration_seconds": result.duration_seconds,
                "start_time": result.start_time.isoformat() if result.start_time else None,
                "end_time": result.end_time.isoformat() if result.end_time else None,
                "test_counts": result.test_counts,
                "error_message": result.error_message
            }
            for result in results
        ]
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued or running background task"""
        # Try to remove from queue first
        with self.queue_lock:
            # Check if task is active
            if task_id in self.active_tasks:
                success = self.process_manager.terminate_process(task_id)
                if success:
                    del self.active_tasks[task_id]
                    
                    # Create cancelled result
                    result = BackgroundTaskResult(
                        task_id=task_id,
                        category=self.active_tasks.get(task_id, QueuedTask("", E2ETestCategory.E2E, BackgroundTaskConfig(E2ETestCategory.E2E), datetime.now())).category,
                        status=BackgroundTaskStatus.CANCELLED,
                        end_time=datetime.now()
                    )
                    self.task_results[task_id] = result
                    self.results_manager.save_result(result)
                    
                return success
        
        # Task might be in queue - this is harder to remove from Queue
        # For now, we'll mark it as cancelled when it gets processed
        self.logger.warning(f"Cannot cancel queued task {task_id} - will be cancelled when processed")
        return False
    
    def _worker_loop(self):
        """Main worker loop for processing background tasks"""
        self.logger.info("Background E2E worker loop started")
        
        while self.is_running and not self.shutdown_event.is_set():
            try:
                # Check if we can process more tasks
                with self.queue_lock:
                    active_count = len(self.active_tasks)
                
                if active_count >= self.max_concurrent_tasks:
                    # Wait a bit before checking again
                    time.sleep(5)
                    continue
                
                # Get next task from queue
                try:
                    task = self.task_queue.get(timeout=5)
                except Empty:
                    continue
                
                # Process the task
                self._process_task(task)
                
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
                time.sleep(5)
        
        self.logger.info("Background E2E worker loop ended")
    
    def _process_task(self, task: QueuedTask):
        """Process a single background task"""
        task_id = task.task_id
        self.logger.info(f"Processing background task {task_id} ({task.category.value})")
        
        # Add to active tasks
        with self.queue_lock:
            self.active_tasks[task_id] = task
        
        # Create initial result
        result = BackgroundTaskResult(
            task_id=task_id,
            category=task.category,
            status=BackgroundTaskStatus.STARTING,
            start_time=datetime.now()
        )
        
        try:
            # Check service dependencies
            if not self._ensure_services_available(task.config):
                result.status = BackgroundTaskStatus.FAILED
                result.error_message = "Required services not available"
                result.end_time = datetime.now()
                self._complete_task(task_id, result)
                return
            
            # Execute the task based on category
            result.status = BackgroundTaskStatus.RUNNING
            self.task_results[task_id] = result
            
            if task.category == E2ETestCategory.CYPRESS:
                success = self._execute_cypress_task(task, result)
            elif task.category in [E2ETestCategory.E2E, E2ETestCategory.E2E_CRITICAL]:
                success = self._execute_e2e_task(task, result)
            elif task.category == E2ETestCategory.PERFORMANCE:
                success = self._execute_performance_task(task, result)
            else:
                self.logger.error(f"Unknown task category: {task.category}")
                success = False
            
            # Update final result
            result.status = BackgroundTaskStatus.COMPLETED if success else BackgroundTaskStatus.FAILED
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            
        except Exception as e:
            self.logger.error(f"Task {task_id} failed with exception: {e}")
            result.status = BackgroundTaskStatus.FAILED
            result.error_message = str(e)
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
        
        finally:
            self._complete_task(task_id, result)
    
    def _ensure_services_available(self, config: BackgroundTaskConfig) -> bool:
        """Ensure required services are available for task execution"""
        try:
            for service in config.services_required:
                available = False
                try:
                    if service == "postgres" or service == "postgresql":
                        available = self.service_checker.check_postgresql()
                    elif service == "redis":
                        available = self.service_checker.check_redis()
                    elif service == "docker":
                        available = self.service_checker.check_docker()
                    elif service == "backend":
                        # Quick socket check for backend service
                        import socket
                        try:
                            backend_port = int(os.environ.get("BACKEND_PORT", "8000"))
                            with socket.create_connection(("localhost", backend_port), timeout=2):
                                available = True
                        except (socket.error, ConnectionRefusedError):
                            available = False
                    elif service == "frontend":
                        # Quick socket check for frontend service
                        import socket
                        try:
                            frontend_port = int(os.environ.get("FRONTEND_PORT", "3000"))
                            with socket.create_connection(("localhost", frontend_port), timeout=2):
                                available = True
                        except (socket.error, ConnectionRefusedError):
                            available = False
                    elif service == "clickhouse":
                        # Quick socket check for ClickHouse
                        import socket
                        try:
                            ch_port = int(os.environ.get("CLICKHOUSE_PORT", "8123"))
                            with socket.create_connection(("localhost", ch_port), timeout=2):
                                available = True
                        except (socket.error, ConnectionRefusedError):
                            available = False
                    else:
                        # For unknown services, assume available (don't block)
                        self.logger.warning(f"Unknown service type: {service}, assuming available")
                        available = True
                        
                    if not available:
                        self.logger.warning(f"Required service not available: {service}")
                        return False
                        
                except Exception as service_error:
                    self.logger.error(f"Error checking {service}: {service_error}")
                    return False
                    
            return True
        except Exception as e:
            self.logger.error(f"Service availability check failed: {e}")
            return False
    
    def _execute_cypress_task(self, task: QueuedTask, result: BackgroundTaskResult) -> bool:
        """Execute Cypress E2E task in background"""
        try:
            # Initialize Cypress runner if needed
            if not self._cypress_runner_initialized:
                self.cypress_runner = CypressTestRunner(self.project_root)
                self._cypress_runner_initialized = True
            
            # Create Cypress execution options
            options = CypressExecutionOptions(
                headed=False,  # Always headless in background
                browser="chrome",
                timeout=task.config.timeout_minutes * 60,
                retries=task.config.max_retries,
                env_vars=task.config.env_vars
            )
            
            # Run Cypress tests
            self.logger.info(f"Starting Cypress execution for task {task.task_id}")
            
            # Build command
            cmd = [
                sys.executable, "scripts/unified_test_runner.py",
                "--category", "cypress",
                "--env", task.config.environment,
                "--no-coverage",
                "--real-services" if task.config.use_real_services else "--mock-services",
                "--real-llm" if task.config.use_real_llm else "--mock-llm"
            ]
            cmd.extend(task.config.additional_args)
            
            # Start background process
            process = self.process_manager.start_background_process(
                task.task_id, cmd, task.config
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=task.config.timeout_minutes * 60)
                result.exit_code = process.returncode
                result.stdout = stdout or ""
                result.stderr = stderr or ""
                
                # Parse test counts from output
                result.test_counts = self._parse_test_counts(stdout)
                
                return process.returncode == 0
                
            except subprocess.TimeoutExpired:
                self.logger.error(f"Cypress task {task.task_id} timed out")
                result.status = BackgroundTaskStatus.TIMEOUT
                result.error_message = f"Timed out after {task.config.timeout_minutes} minutes"
                self.process_manager.terminate_process(task.task_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Cypress task execution failed: {e}")
            result.error_message = str(e)
            return False
    
    def _execute_e2e_task(self, task: QueuedTask, result: BackgroundTaskResult) -> bool:
        """Execute E2E task in background"""
        try:
            self.logger.info(f"Starting E2E execution for task {task.task_id}")
            
            # Build command
            cmd = [
                sys.executable, "scripts/unified_test_runner.py",
                "--category", task.category.value,
                "--env", task.config.environment,
                "--no-coverage",
                "--real-services" if task.config.use_real_services else "--mock-services",
                "--real-llm" if task.config.use_real_llm else "--mock-llm"
            ]
            cmd.extend(task.config.additional_args)
            
            # Start background process
            process = self.process_manager.start_background_process(
                task.task_id, cmd, task.config
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=task.config.timeout_minutes * 60)
                result.exit_code = process.returncode
                result.stdout = stdout or ""
                result.stderr = stderr or ""
                
                # Parse test counts from output
                result.test_counts = self._parse_test_counts(stdout)
                
                return process.returncode == 0
                
            except subprocess.TimeoutExpired:
                self.logger.error(f"E2E task {task.task_id} timed out")
                result.status = BackgroundTaskStatus.TIMEOUT
                result.error_message = f"Timed out after {task.config.timeout_minutes} minutes"
                self.process_manager.terminate_process(task.task_id)
                return False
                
        except Exception as e:
            self.logger.error(f"E2E task execution failed: {e}")
            result.error_message = str(e)
            return False
    
    def _execute_performance_task(self, task: QueuedTask, result: BackgroundTaskResult) -> bool:
        """Execute performance task in background"""
        try:
            self.logger.info(f"Starting performance execution for task {task.task_id}")
            
            # Build command
            cmd = [
                sys.executable, "scripts/unified_test_runner.py",
                "--category", "performance",
                "--env", task.config.environment,
                "--no-coverage",
                "--real-services" if task.config.use_real_services else "--mock-services"
            ]
            cmd.extend(task.config.additional_args)
            
            # Start background process
            process = self.process_manager.start_background_process(
                task.task_id, cmd, task.config
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=task.config.timeout_minutes * 60)
                result.exit_code = process.returncode
                result.stdout = stdout or ""
                result.stderr = stderr or ""
                
                # Parse test counts and performance metrics
                result.test_counts = self._parse_test_counts(stdout)
                
                return process.returncode == 0
                
            except subprocess.TimeoutExpired:
                self.logger.error(f"Performance task {task.task_id} timed out")
                result.status = BackgroundTaskStatus.TIMEOUT
                result.error_message = f"Timed out after {task.config.timeout_minutes} minutes"
                self.process_manager.terminate_process(task.task_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Performance task execution failed: {e}")
            result.error_message = str(e)
            return False
    
    def _parse_test_counts(self, output: str) -> Dict[str, int]:
        """Parse test counts from test output"""
        counts = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
        
        try:
            # Look for pytest-style output
            import re
            
            # Pattern: "collected 5 items"
            collected_match = re.search(r"collected (\d+) items?", output)
            if collected_match:
                counts["total"] = int(collected_match.group(1))
            
            # Pattern: "5 passed, 0 failed, 0 skipped"
            result_match = re.search(r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) skipped)?", output)
            if result_match:
                counts["passed"] = int(result_match.group(1) or 0)
                counts["failed"] = int(result_match.group(2) or 0)
                counts["skipped"] = int(result_match.group(3) or 0)
                
        except Exception as e:
            self.logger.debug(f"Could not parse test counts: {e}")
        
        return counts
    
    def _complete_task(self, task_id: str, result: BackgroundTaskResult):
        """Complete a background task and clean up"""
        # Remove from active tasks
        with self.queue_lock:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
        
        # Store result
        self.task_results[task_id] = result
        self.results_manager.save_result(result)
        
        # Clean up process
        self.process_manager.terminate_process(task_id)
        
        # Notify orchestrator if available
        if self.communication:
            asyncio.create_task(self._notify_orchestrator("task_completed", {
                "task_id": task_id,
                "status": result.status.value,
                "success": result.status == BackgroundTaskStatus.COMPLETED
            }))
        
        self.logger.info(f"Completed background task {task_id} with status: {result.status.value}")
    
    async def _notify_orchestrator(self, message_type: str, payload: Dict[str, Any]):
        """Notify orchestrator about task events"""
        if self.communication and ORCHESTRATOR_AVAILABLE:
            try:
                await self.communication.send_message(
                    self.manager_id, "orchestrator", message_type, payload
                )
            except Exception as e:
                self.logger.error(f"Failed to notify orchestrator: {e}")
    
    def enable_communication(self, communication_protocol):
        """Enable communication with orchestrator"""
        self.communication = communication_protocol
        self.logger.info("Enabled communication with orchestrator")
    
    async def handle_message(self, message):
        """Handle messages from orchestrator"""
        if not ORCHESTRATOR_AVAILABLE or not message:
            return
            
        try:
            if message.message_type == "queue_e2e_test":
                category = E2ETestCategory(message.payload.get("category"))
                config_data = message.payload.get("config", {})
                config = BackgroundTaskConfig(category=category, **config_data)
                task_id = self.queue_e2e_test(category, config)
                
                await self.communication.send_message(
                    self.manager_id, message.sender, "task_queued",
                    {"task_id": task_id}
                )
                
            elif message.message_type == "get_task_status":
                task_id = message.payload.get("task_id")
                status = self.get_task_status(task_id)
                
                await self.communication.send_message(
                    self.manager_id, message.sender, "task_status",
                    {"task_id": task_id, "status": status}
                )
                
            elif message.message_type == "get_queue_status":
                status = self.get_queue_status()
                
                await self.communication.send_message(
                    self.manager_id, message.sender, "queue_status",
                    {"status": status}
                )
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        self.logger.info(f"Received signal {signum}, shutting down")
        self.stop()
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


# CLI Integration Functions

def add_background_e2e_arguments(parser):
    """Add background E2E arguments to CLI parser"""
    bg_group = parser.add_argument_group('Background E2E Manager Options')
    
    bg_group.add_argument(
        '--queue-e2e',
        action='store_true',
        help='Queue E2E tests for background execution using BackgroundE2EManager'
    )
    
    bg_group.add_argument(
        '--background-category',
        choices=['cypress', 'e2e', 'performance', 'e2e_critical'],
        help='Specific E2E category to run in background'
    )
    
    bg_group.add_argument(
        '--background-status',
        action='store_true',
        help='Show status of background E2E queue'
    )
    
    bg_group.add_argument(
        '--background-results',
        type=int,
        metavar='N',
        help='Show last N background test results'
    )
    
    bg_group.add_argument(
        '--kill-background',
        metavar='TASK_ID',
        help='Cancel/kill background task by ID'
    )
    
    bg_group.add_argument(
        '--background-timeout',
        type=int,
        default=30,
        help='Timeout for background tasks in minutes (default: 30)'
    )


def handle_background_e2e_commands(args, project_root: Path) -> Optional[int]:
    """
    Handle background E2E CLI commands
    
    Returns:
        Exit code if command was handled, None otherwise
    """
    manager = BackgroundE2EManager(project_root)
    
    try:
        # Start manager if needed
        if args.queue_e2e or args.background_status or args.background_results or args.kill_background:
            manager.start()
        
        # Handle status command
        if args.background_status:
            status = manager.get_queue_status()
            print(f"\n{'='*60}")
            print("BACKGROUND E2E QUEUE STATUS")
            print(f"{'='*60}")
            print(f"Manager Running: {status['manager_running']}")
            print(f"Queued Tasks: {status['queued_tasks']}")
            print(f"Active Tasks: {status['active_tasks']}")
            
            if status['queued_by_category']:
                print("\nQueued by Category:")
                for category, count in status['queued_by_category'].items():
                    print(f"  {category}: {count}")
            
            if status['active_task_ids']:
                print(f"\nActive Task IDs:")
                for task_id in status['active_task_ids']:
                    print(f"  {task_id}")
            
            return 0
        
        # Handle results command
        if args.background_results:
            results = manager.get_recent_results(args.background_results)
            print(f"\n{'='*60}")
            print(f"RECENT BACKGROUND TEST RESULTS (Last {args.background_results})")
            print(f"{'='*60}")
            
            if not results:
                print("No background test results found")
            else:
                for result in results:
                    print(f"\nTask ID: {result['task_id']}")
                    print(f"Category: {result['category']}")
                    print(f"Status: {result['status']}")
                    print(f"Duration: {result['duration_seconds']:.1f}s")
                    if result.get('test_counts'):
                        counts = result['test_counts']
                        print(f"Tests: {counts.get('passed', 0)} passed, {counts.get('failed', 0)} failed")
                    if result.get('error_message'):
                        print(f"Error: {result['error_message']}")
            
            return 0
        
        # Handle kill command
        if args.kill_background:
            success = manager.cancel_task(args.kill_background)
            if success:
                print(f"Successfully cancelled background task: {args.kill_background}")
                return 0
            else:
                print(f"Failed to cancel background task: {args.kill_background}")
                return 1
        
        # Handle background execution
        if args.queue_e2e:
            category = E2ETestCategory(args.background_category or 'e2e')
            config = BackgroundTaskConfig(
                category=category,
                timeout_minutes=args.background_timeout,
                environment=getattr(args, 'env', 'development'),
                use_real_services=getattr(args, 'real_services', True),
                use_real_llm=getattr(args, 'real_llm', True)
            )
            
            task_id = manager.queue_e2e_test(category, config)
            print(f"\n{'='*60}")
            print("BACKGROUND E2E TEST QUEUED")
            print(f"{'='*60}")
            print(f"Task ID: {task_id}")
            print(f"Category: {category.value}")
            print(f"Timeout: {config.timeout_minutes} minutes")
            print(f"\nUse --background-status to check progress")
            print(f"Use --background-results 5 to see results when complete")
            
            return 0
        
        return None
        
    finally:
        manager.stop()


if __name__ == "__main__":
    # Simple CLI for testing the BackgroundE2EManager
    import argparse
    
    parser = argparse.ArgumentParser(description="Background E2E Manager")
    add_background_e2e_arguments(parser)
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent.parent
    exit_code = handle_background_e2e_commands(args, project_root)
    
    if exit_code is not None:
        sys.exit(exit_code)
    else:
        print("No background E2E command specified. Use --help for options.")
        sys.exit(1)