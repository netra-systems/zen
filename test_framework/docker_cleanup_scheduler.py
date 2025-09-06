from shared.isolated_environment import get_env
"""
Docker Cleanup Scheduler - Automated resource management for Docker environments

Prevents Docker crashes due to resource accumulation by implementing scheduled cleanup
operations with intelligent monitoring and circuit breaker patterns.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity, Risk Reduction
2. Business Goal: Prevent Docker daemon crashes, reduce developer downtime
3. Value Impact: Eliminates 4-8 hours/week of downtime, maintains CI/CD reliability
4. Revenue Impact: Protects $2M+ ARR by ensuring development infrastructure stability
"""

import threading
import time
import logging
import json
import subprocess
import psutil
import os
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
from contextlib import contextmanager

from test_framework.docker_rate_limiter import (
    DockerRateLimiter, 
    get_docker_rate_limiter,
    DockerCommandResult
)

logger = logging.getLogger(__name__)


class CleanupType(Enum):
    """Types of cleanup operations."""
    CONTAINERS = "containers"
    IMAGES = "images"
    VOLUMES = "volumes"
    NETWORKS = "networks"
    BUILD_CACHE = "build_cache"
    SYSTEM = "system"


class SchedulerState(Enum):
    """Scheduler operational states."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    cleanup_type: CleanupType
    success: bool
    items_removed: int
    space_freed_mb: float
    duration_seconds: float
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ResourceThresholds:
    """Configurable resource thresholds for automatic cleanup."""
    disk_usage_percent: float = 85.0  # Trigger cleanup at 85% disk usage
    container_count: int = 50  # Max containers before cleanup
    image_count: int = 100  # Max images before cleanup
    volume_count: int = 30  # Max volumes before cleanup
    memory_usage_percent: float = 90.0  # Memory usage threshold


@dataclass
class ScheduleConfig:
    """Configuration for cleanup scheduling."""
    business_hours_start: int = 8  # 8 AM
    business_hours_end: int = 18  # 6 PM
    cleanup_interval_hours: int = 1  # Every hour during business hours
    off_hours_interval_hours: int = 4  # Every 4 hours off business hours
    enable_threshold_cleanup: bool = True
    enable_post_test_cleanup: bool = True
    max_cleanup_duration_minutes: int = 10


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration for cleanup operations."""
    failure_threshold: int = 3  # Open circuit after 3 consecutive failures
    recovery_timeout_minutes: int = 15  # Wait 15 minutes before attempting recovery
    half_open_test_operations: int = 1  # Test with 1 operation when half-open


class DockerCleanupScheduler:
    """
    Automated Docker cleanup scheduler with intelligent monitoring and circuit breaker.
    
    Features:
    - Scheduled cleanup during business hours and off-hours
    - Resource threshold monitoring for automatic cleanup
    - Circuit breaker pattern for fault tolerance
    - Integration with existing Docker rate limiter
    - Cross-platform compatibility
    - Comprehensive logging and metrics
    """
    
    def __init__(self,
                 docker_manager=None,
                 rate_limiter: Optional[DockerRateLimiter] = None,
                 schedule_config: Optional[ScheduleConfig] = None,
                 resource_thresholds: Optional[ResourceThresholds] = None,
                 circuit_breaker_config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize the Docker cleanup scheduler.
        
        Args:
            docker_manager: UnifiedDockerManager instance (optional, will be imported if needed)
            rate_limiter: Docker rate limiter instance (uses global if None)
            schedule_config: Schedule configuration
            resource_thresholds: Resource monitoring thresholds
            circuit_breaker_config: Circuit breaker configuration
        """
        self.docker_manager = docker_manager
        self.rate_limiter = rate_limiter or get_docker_rate_limiter()
        self.schedule_config = schedule_config or ScheduleConfig()
        self.resource_thresholds = resource_thresholds or ResourceThresholds()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        
        # State management
        self.state = SchedulerState.STOPPED
        self._lock = threading.RLock()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._active_test_sessions: Set[str] = set()
        
        # Circuit breaker state
        self._consecutive_failures = 0
        self._circuit_open_time: Optional[datetime] = None
        self._half_open_test_count = 0
        
        # Metrics and history
        self._cleanup_history: List[CleanupResult] = []
        self._last_cleanup_times: Dict[CleanupType, datetime] = {}
        self._total_space_freed_mb = 0.0
        self._total_items_removed = 0
        
        # Callbacks
        self._pre_cleanup_callbacks: List[Callable[[], bool]] = []
        self._post_cleanup_callbacks: List[Callable[[List[CleanupResult]], None]] = []
        
        # State persistence
        if os.name != 'nt':
            self.state_file = Path("/tmp/docker_cleanup_scheduler.json")
        else:
            # Windows: use TEMP directory, with IsolatedEnvironment if available
            try:
                from shared.isolated_environment import get_env
                temp_dir = get_env().get('TEMP', '.')
            except ImportError:
                temp_dir = os.environ.get('TEMP', '.')
            self.state_file = Path(temp_dir) / "docker_cleanup_scheduler.json"
        
        self._load_state()
        logger.info("DockerCleanupScheduler initialized")
    
    def start(self) -> bool:
        """
        Start the cleanup scheduler.
        
        Returns:
            True if started successfully
        """
        with self._lock:
            if self.state == SchedulerState.RUNNING:
                logger.warning("Scheduler is already running")
                return True
            
            try:
                # Verify Docker is available
                if not self.rate_limiter.health_check():
                    logger.error("Docker is not available - cannot start scheduler")
                    return False
                
                self._stop_event.clear()
                self.state = SchedulerState.RUNNING
                
                # Start scheduler thread
                self._scheduler_thread = threading.Thread(
                    target=self._scheduler_loop,
                    name="DockerCleanupScheduler",
                    daemon=True
                )
                self._scheduler_thread.start()
                
                self._save_state()
                logger.info("DockerCleanupScheduler started successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start scheduler: {e}")
                self.state = SchedulerState.STOPPED
                return False
    
    def stop(self) -> bool:
        """
        Stop the cleanup scheduler.
        
        Returns:
            True if stopped successfully
        """
        with self._lock:
            if self.state == SchedulerState.STOPPED:
                return True
            
            self.state = SchedulerState.STOPPED
            self._stop_event.set()
            
            if self._scheduler_thread and self._scheduler_thread.is_alive():
                self._scheduler_thread.join(timeout=30)
                if self._scheduler_thread.is_alive():
                    logger.warning("Scheduler thread did not stop gracefully")
            
            self._scheduler_thread = None
            self._save_state()
            logger.info("DockerCleanupScheduler stopped")
            return True
    
    def pause(self) -> None:
        """Pause the scheduler (stops automatic cleanup but keeps thread running)."""
        with self._lock:
            if self.state == SchedulerState.RUNNING:
                self.state = SchedulerState.PAUSED
                self._save_state()
                logger.info("DockerCleanupScheduler paused")
    
    def resume(self) -> None:
        """Resume the scheduler from paused state."""
        with self._lock:
            if self.state == SchedulerState.PAUSED:
                self.state = SchedulerState.RUNNING
                self._save_state()
                logger.info("DockerCleanupScheduler resumed")
    
    def register_test_session(self, test_id: str) -> None:
        """
        Register an active test session to prevent cleanup during tests.
        
        Args:
            test_id: Unique identifier for the test session
        """
        with self._lock:
            self._active_test_sessions.add(test_id)
            logger.debug(f"Registered test session: {test_id}")
    
    def unregister_test_session(self, test_id: str, trigger_cleanup: bool = True) -> None:
        """
        Unregister a test session and optionally trigger post-test cleanup.
        
        Args:
            test_id: Test session identifier
            trigger_cleanup: Whether to trigger cleanup after test completion
        """
        with self._lock:
            self._active_test_sessions.discard(test_id)
            logger.debug(f"Unregistered test session: {test_id}")
            
            if trigger_cleanup and self.schedule_config.enable_post_test_cleanup:
                # Trigger cleanup in background thread
                cleanup_thread = threading.Thread(
                    target=self._perform_post_test_cleanup,
                    name=f"PostTestCleanup-{test_id}",
                    daemon=True
                )
                cleanup_thread.start()
    
    def trigger_manual_cleanup(self, 
                              cleanup_types: Optional[List[CleanupType]] = None,
                              force: bool = False) -> List[CleanupResult]:
        """
        Manually trigger cleanup operations.
        
        Args:
            cleanup_types: Specific cleanup types to perform (all if None)
            force: Force cleanup even during active tests
            
        Returns:
            List of cleanup results
        """
        if not force and self._has_active_tests():
            logger.warning("Skipping manual cleanup due to active test sessions")
            return []
        
        cleanup_types = cleanup_types or list(CleanupType)
        return self._perform_cleanup(cleanup_types, manual=True)
    
    def check_resource_thresholds(self) -> Dict[str, Any]:
        """
        Check current resource usage against thresholds.
        
        Returns:
            Dictionary with threshold check results
        """
        try:
            # Disk usage
            disk_usage = psutil.disk_usage('/')
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Docker resource counts
            container_count = self._get_docker_resource_count("containers")
            image_count = self._get_docker_resource_count("images")
            volume_count = self._get_docker_resource_count("volumes")
            
            return {
                "disk_usage_percent": disk_percent,
                "disk_threshold_exceeded": disk_percent > self.resource_thresholds.disk_usage_percent,
                "memory_usage_percent": memory_percent,
                "memory_threshold_exceeded": memory_percent > self.resource_thresholds.memory_usage_percent,
                "container_count": container_count,
                "container_threshold_exceeded": container_count > self.resource_thresholds.container_count,
                "image_count": image_count,
                "image_threshold_exceeded": image_count > self.resource_thresholds.image_count,
                "volume_count": volume_count,
                "volume_threshold_exceeded": volume_count > self.resource_thresholds.volume_count,
                "any_threshold_exceeded": any([
                    disk_percent > self.resource_thresholds.disk_usage_percent,
                    memory_percent > self.resource_thresholds.memory_usage_percent,
                    container_count > self.resource_thresholds.container_count,
                    image_count > self.resource_thresholds.image_count,
                    volume_count > self.resource_thresholds.volume_count
                ])
            }
            
        except Exception as e:
            logger.error(f"Error checking resource thresholds: {e}")
            return {"error": str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive scheduler statistics."""
        with self._lock:
            # Calculate success rate
            total_operations = len(self._cleanup_history)
            successful_operations = sum(1 for result in self._cleanup_history if result.success)
            success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0
            
            # Recent operations (last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_operations = [
                result for result in self._cleanup_history 
                if result.timestamp and result.timestamp > cutoff_time
            ]
            
            return {
                "scheduler_state": self.state.value,
                "active_test_sessions": len(self._active_test_sessions),
                "circuit_breaker": {
                    "consecutive_failures": self._consecutive_failures,
                    "circuit_open": self.state == SchedulerState.CIRCUIT_OPEN,
                    "circuit_open_time": self._circuit_open_time.isoformat() if self._circuit_open_time else None
                },
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "success_rate_percent": success_rate,
                "total_space_freed_mb": self._total_space_freed_mb,
                "total_items_removed": self._total_items_removed,
                "recent_operations_24h": len(recent_operations),
                "last_cleanup_times": {
                    cleanup_type.value: time.isoformat() if time else None
                    for cleanup_type, time in self._last_cleanup_times.items()
                },
                "resource_thresholds": self.check_resource_thresholds()
            }
    
    def add_pre_cleanup_callback(self, callback: Callable[[], bool]) -> None:
        """
        Add a callback that runs before cleanup operations.
        
        Args:
            callback: Function that returns True to proceed with cleanup
        """
        self._pre_cleanup_callbacks.append(callback)
    
    def add_post_cleanup_callback(self, callback: Callable[[List[CleanupResult]], None]) -> None:
        """
        Add a callback that runs after cleanup operations.
        
        Args:
            callback: Function that receives cleanup results
        """
        self._post_cleanup_callbacks.append(callback)
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop running in background thread."""
        logger.info("Scheduler loop started")
        
        while not self._stop_event.is_set():
            try:
                if self.state == SchedulerState.RUNNING:
                    self._check_and_cleanup()
                elif self.state == SchedulerState.CIRCUIT_OPEN:
                    self._check_circuit_breaker_recovery()
                
                # Calculate next check interval
                now = datetime.now()
                is_business_hours = (
                    self.schedule_config.business_hours_start <= now.hour < 
                    self.schedule_config.business_hours_end
                )
                
                interval_hours = (
                    self.schedule_config.cleanup_interval_hours if is_business_hours
                    else self.schedule_config.off_hours_interval_hours
                )
                
                # Sleep in small intervals to allow responsive shutdown
                sleep_seconds = interval_hours * 3600
                while sleep_seconds > 0 and not self._stop_event.is_set():
                    sleep_time = min(60, sleep_seconds)  # Check every minute for stop event
                    time.sleep(sleep_time)
                    sleep_seconds -= sleep_time
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                self._handle_scheduler_error(e)
                time.sleep(60)  # Wait before retrying
        
        logger.info("Scheduler loop stopped")
    
    def _check_and_cleanup(self) -> None:
        """Check if cleanup is needed and perform it if appropriate."""
        if self._has_active_tests():
            logger.debug("Skipping cleanup due to active test sessions")
            return
        
        # Check if threshold-based cleanup is needed
        if self.schedule_config.enable_threshold_cleanup:
            thresholds = self.check_resource_thresholds()
            if thresholds.get("any_threshold_exceeded", False):
                logger.info("Resource thresholds exceeded, triggering cleanup")
                cleanup_types = self._determine_cleanup_types_from_thresholds(thresholds)
                self._perform_cleanup(cleanup_types, manual=False)
                return
        
        # Check if scheduled cleanup is needed
        now = datetime.now()
        is_business_hours = (
            self.schedule_config.business_hours_start <= now.hour < 
            self.schedule_config.business_hours_end
        )
        
        interval_hours = (
            self.schedule_config.cleanup_interval_hours if is_business_hours
            else self.schedule_config.off_hours_interval_hours
        )
        
        # Check if any cleanup type is due
        for cleanup_type in CleanupType:
            last_cleanup = self._last_cleanup_times.get(cleanup_type)
            if not last_cleanup or (now - last_cleanup).total_seconds() > (interval_hours * 3600):
                logger.info(f"Scheduled cleanup due for {cleanup_type.value}")
                self._perform_cleanup([cleanup_type], manual=False)
                break  # Only do one type per cycle to spread load
    
    def _perform_cleanup(self, cleanup_types: List[CleanupType], manual: bool = False) -> List[CleanupResult]:
        """
        Perform cleanup operations with circuit breaker protection.
        
        Args:
            cleanup_types: Types of cleanup to perform
            manual: Whether this is a manual cleanup request
            
        Returns:
            List of cleanup results
        """
        if self.state == SchedulerState.CIRCUIT_OPEN and not manual:
            logger.warning("Skipping cleanup - circuit breaker is open")
            return []
        
        # Run pre-cleanup callbacks
        for callback in self._pre_cleanup_callbacks:
            try:
                if not callback():
                    logger.info("Cleanup cancelled by pre-cleanup callback")
                    return []
            except Exception as e:
                logger.warning(f"Pre-cleanup callback error: {e}")
        
        results = []
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting cleanup operations: {[t.value for t in cleanup_types]}")
            
            for cleanup_type in cleanup_types:
                # Check timeout
                if (datetime.now() - start_time).total_seconds() > (self.schedule_config.max_cleanup_duration_minutes * 60):
                    logger.warning("Cleanup timeout reached, stopping")
                    break
                
                try:
                    result = self._perform_single_cleanup(cleanup_type)
                    results.append(result)
                    
                    if result.success:
                        self._last_cleanup_times[cleanup_type] = datetime.now()
                        self._total_space_freed_mb += result.space_freed_mb
                        self._total_items_removed += result.items_removed
                        self._reset_circuit_breaker()
                    else:
                        self._handle_cleanup_failure(cleanup_type, result.error_message)
                        
                except Exception as e:
                    error_msg = f"Unexpected error during {cleanup_type.value} cleanup: {e}"
                    logger.error(error_msg)
                    result = CleanupResult(
                        cleanup_type=cleanup_type,
                        success=False,
                        items_removed=0,
                        space_freed_mb=0.0,
                        duration_seconds=0.0,
                        error_message=error_msg
                    )
                    results.append(result)
                    self._handle_cleanup_failure(cleanup_type, error_msg)
            
            # Update history
            self._cleanup_history.extend(results)
            
            # Trim history to last 1000 entries
            if len(self._cleanup_history) > 1000:
                self._cleanup_history = self._cleanup_history[-1000:]
            
            self._save_state()
            
            # Run post-cleanup callbacks
            for callback in self._post_cleanup_callbacks:
                try:
                    callback(results)
                except Exception as e:
                    logger.warning(f"Post-cleanup callback error: {e}")
            
            logger.info(f"Cleanup completed: {len(results)} operations, "
                       f"{sum(r.items_removed for r in results)} items removed, "
                       f"{sum(r.space_freed_mb for r in results):.1f} MB freed")
            
            return results
            
        except Exception as e:
            logger.error(f"Critical error during cleanup: {e}")
            self._handle_cleanup_failure(CleanupType.SYSTEM, str(e))
            return results
    
    def _perform_single_cleanup(self, cleanup_type: CleanupType) -> CleanupResult:
        """
        Perform a single type of cleanup operation.
        
        Args:
            cleanup_type: Type of cleanup to perform
            
        Returns:
            Cleanup result
        """
        start_time = time.time()
        logger.debug(f"Performing {cleanup_type.value} cleanup")
        
        try:
            if cleanup_type == CleanupType.CONTAINERS:
                return self._cleanup_containers()
            elif cleanup_type == CleanupType.IMAGES:
                return self._cleanup_images()
            elif cleanup_type == CleanupType.VOLUMES:
                return self._cleanup_volumes()
            elif cleanup_type == CleanupType.NETWORKS:
                return self._cleanup_networks()
            elif cleanup_type == CleanupType.BUILD_CACHE:
                return self._cleanup_build_cache()
            elif cleanup_type == CleanupType.SYSTEM:
                return self._cleanup_system()
            else:
                raise ValueError(f"Unknown cleanup type: {cleanup_type}")
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error in {cleanup_type.value} cleanup: {e}")
            return CleanupResult(
                cleanup_type=cleanup_type,
                success=False,
                items_removed=0,
                space_freed_mb=0.0,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def _cleanup_containers(self) -> CleanupResult:
        """Clean up stopped containers."""
        start_time = time.time()
        
        # Get list of stopped containers
        result = self.rate_limiter.execute_docker_command([
            "docker", "container", "ls", "-a", "-f", "status=exited", "--format", "{{.ID}}"
        ])
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to list containers: {result.stderr}")
        
        container_ids = [cid.strip() for cid in result.stdout.strip().split('\n') if cid.strip()]
        
        if not container_ids:
            return CleanupResult(
                cleanup_type=CleanupType.CONTAINERS,
                success=True,
                items_removed=0,
                space_freed_mb=0.0,
                duration_seconds=time.time() - start_time
            )
        
        # Remove containers
        cmd = ["docker", "container", "rm"] + container_ids
        result = self.rate_limiter.execute_docker_command(cmd)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to remove containers: {result.stderr}")
        
        # Estimate space freed (rough estimate)
        space_freed_mb = len(container_ids) * 10  # 10MB per container estimate
        
        return CleanupResult(
            cleanup_type=CleanupType.CONTAINERS,
            success=True,
            items_removed=len(container_ids),
            space_freed_mb=space_freed_mb,
            duration_seconds=time.time() - start_time
        )
    
    def _cleanup_images(self) -> CleanupResult:
        """Clean up dangling and unused images."""
        start_time = time.time()
        
        # Get disk usage before cleanup
        space_before = self._get_docker_space_usage()
        
        # Remove dangling images
        result = self.rate_limiter.execute_docker_command([
            "docker", "image", "prune", "-f"
        ])
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to prune images: {result.stderr}")
        
        # Parse output for removed items count
        items_removed = 0
        if "deleted" in result.stdout.lower():
            # Try to extract count from output
            try:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "deleted" in line.lower():
                        items_removed += 1
            except:
                items_removed = 1  # At least something was deleted
        
        # Get disk usage after cleanup
        space_after = self._get_docker_space_usage()
        space_freed_mb = max(0, space_before - space_after)
        
        return CleanupResult(
            cleanup_type=CleanupType.IMAGES,
            success=True,
            items_removed=items_removed,
            space_freed_mb=space_freed_mb,
            duration_seconds=time.time() - start_time
        )
    
    def _cleanup_volumes(self) -> CleanupResult:
        """Clean up unused volumes."""
        start_time = time.time()
        
        # Get space usage before
        space_before = self._get_docker_space_usage()
        
        # Remove unused volumes
        result = self.rate_limiter.execute_docker_command([
            "docker", "volume", "prune", "-f"
        ])
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to prune volumes: {result.stderr}")
        
        # Parse output for removed items
        items_removed = 0
        if "deleted" in result.stdout.lower():
            try:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "deleted" in line.lower() or "removed" in line.lower():
                        items_removed += 1
            except:
                items_removed = 1
        
        space_after = self._get_docker_space_usage()
        space_freed_mb = max(0, space_before - space_after)
        
        return CleanupResult(
            cleanup_type=CleanupType.VOLUMES,
            success=True,
            items_removed=items_removed,
            space_freed_mb=space_freed_mb,
            duration_seconds=time.time() - start_time
        )
    
    def _cleanup_networks(self) -> CleanupResult:
        """Clean up unused networks."""
        start_time = time.time()
        
        result = self.rate_limiter.execute_docker_command([
            "docker", "network", "prune", "-f"
        ])
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to prune networks: {result.stderr}")
        
        items_removed = 0
        if "deleted" in result.stdout.lower():
            try:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "deleted" in line.lower() or "removed" in line.lower():
                        items_removed += 1
            except:
                items_removed = 1
        
        # Networks don't use significant disk space
        space_freed_mb = 0.0
        
        return CleanupResult(
            cleanup_type=CleanupType.NETWORKS,
            success=True,
            items_removed=items_removed,
            space_freed_mb=space_freed_mb,
            duration_seconds=time.time() - start_time
        )
    
    def _cleanup_build_cache(self) -> CleanupResult:
        """Clean up Docker build cache."""
        start_time = time.time()
        
        space_before = self._get_docker_space_usage()
        
        result = self.rate_limiter.execute_docker_command([
            "docker", "builder", "prune", "-f"
        ])
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to prune build cache: {result.stderr}")
        
        space_after = self._get_docker_space_usage()
        space_freed_mb = max(0, space_before - space_after)
        
        # Build cache cleanup doesn't report item counts clearly
        items_removed = 1 if space_freed_mb > 0 else 0
        
        return CleanupResult(
            cleanup_type=CleanupType.BUILD_CACHE,
            success=True,
            items_removed=items_removed,
            space_freed_mb=space_freed_mb,
            duration_seconds=time.time() - start_time
        )
    
    def _cleanup_system(self) -> CleanupResult:
        """Perform comprehensive system cleanup."""
        start_time = time.time()
        
        space_before = self._get_docker_space_usage()
        
        # Use docker system prune for comprehensive cleanup
        result = self.rate_limiter.execute_docker_command([
            "docker", "system", "prune", "-f", "--volumes"
        ])
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to perform system prune: {result.stderr}")
        
        space_after = self._get_docker_space_usage()
        space_freed_mb = max(0, space_before - space_after)
        
        # System prune affects multiple resource types
        items_removed = 1 if space_freed_mb > 0 else 0
        
        return CleanupResult(
            cleanup_type=CleanupType.SYSTEM,
            success=True,
            items_removed=items_removed,
            space_freed_mb=space_freed_mb,
            duration_seconds=time.time() - start_time
        )
    
    def _perform_post_test_cleanup(self) -> None:
        """Perform lightweight cleanup after test completion."""
        logger.info("Performing post-test cleanup")
        try:
            # Light cleanup - only containers and networks
            self._perform_cleanup([CleanupType.CONTAINERS, CleanupType.NETWORKS], manual=False)
        except Exception as e:
            logger.error(f"Error in post-test cleanup: {e}")
    
    def _get_docker_resource_count(self, resource_type: str) -> int:
        """Get count of Docker resources."""
        try:
            if resource_type == "containers":
                result = self.rate_limiter.execute_docker_command([
                    "docker", "container", "ls", "-aq"
                ])
            elif resource_type == "images":
                result = self.rate_limiter.execute_docker_command([
                    "docker", "image", "ls", "-aq"
                ])
            elif resource_type == "volumes":
                result = self.rate_limiter.execute_docker_command([
                    "docker", "volume", "ls", "-q"
                ])
            else:
                return 0
            
            if result.returncode != 0:
                logger.warning(f"Failed to count {resource_type}: {result.stderr}")
                return 0
            
            return len([line for line in result.stdout.strip().split('\n') if line.strip()])
            
        except Exception as e:
            logger.warning(f"Error counting {resource_type}: {e}")
            return 0
    
    def _get_docker_space_usage(self) -> float:
        """Get Docker space usage in MB."""
        try:
            result = self.rate_limiter.execute_docker_command([
                "docker", "system", "df", "--format", "json"
            ])
            
            if result.returncode != 0:
                return 0.0
            
            try:
                data = json.loads(result.stdout)
                total_size = 0
                
                for category in data:
                    if 'Size' in category:
                        # Parse size string (e.g., "1.5GB", "500MB")
                        size_str = category['Size'].replace('B', '')
                        if 'G' in size_str:
                            size_mb = float(size_str.replace('G', '')) * 1024
                        elif 'M' in size_str:
                            size_mb = float(size_str.replace('M', ''))
                        elif 'K' in size_str:
                            size_mb = float(size_str.replace('K', '')) / 1024
                        else:
                            size_mb = float(size_str) / (1024 * 1024)
                        
                        total_size += size_mb
                
                return total_size
                
            except (json.JSONDecodeError, KeyError, ValueError):
                return 0.0
                
        except Exception:
            return 0.0
    
    def _determine_cleanup_types_from_thresholds(self, thresholds: Dict[str, Any]) -> List[CleanupType]:
        """Determine which cleanup types to run based on exceeded thresholds."""
        cleanup_types = []
        
        if thresholds.get("container_threshold_exceeded", False):
            cleanup_types.append(CleanupType.CONTAINERS)
        
        if thresholds.get("image_threshold_exceeded", False):
            cleanup_types.append(CleanupType.IMAGES)
        
        if thresholds.get("volume_threshold_exceeded", False):
            cleanup_types.append(CleanupType.VOLUMES)
        
        if thresholds.get("disk_threshold_exceeded", False):
            # Comprehensive cleanup for disk space issues
            cleanup_types.extend([CleanupType.BUILD_CACHE, CleanupType.SYSTEM])
        
        # Always include networks for general cleanup
        cleanup_types.append(CleanupType.NETWORKS)
        
        # Remove duplicates while preserving order
        seen = set()
        return [ct for ct in cleanup_types if not (ct in seen or seen.add(ct))]
    
    def _has_active_tests(self) -> bool:
        """Check if there are active test sessions."""
        return len(self._active_test_sessions) > 0
    
    def _handle_cleanup_failure(self, cleanup_type: CleanupType, error_message: str) -> None:
        """Handle cleanup failure with circuit breaker logic."""
        with self._lock:
            self._consecutive_failures += 1
            logger.warning(f"Cleanup failure #{self._consecutive_failures} for {cleanup_type.value}: {error_message}")
            
            if self._consecutive_failures >= self.circuit_breaker_config.failure_threshold:
                self.state = SchedulerState.CIRCUIT_OPEN
                self._circuit_open_time = datetime.now()
                logger.error(f"Circuit breaker opened after {self._consecutive_failures} failures")
                self._save_state()
    
    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker after successful operation."""
        with self._lock:
            if self._consecutive_failures > 0:
                self._consecutive_failures = 0
                if self.state == SchedulerState.CIRCUIT_OPEN:
                    self.state = SchedulerState.RUNNING
                    self._circuit_open_time = None
                    logger.info("Circuit breaker reset after successful operation")
                    self._save_state()
    
    def _check_circuit_breaker_recovery(self) -> None:
        """Check if circuit breaker can attempt recovery."""
        if not self._circuit_open_time:
            return
        
        recovery_time = self._circuit_open_time + timedelta(
            minutes=self.circuit_breaker_config.recovery_timeout_minutes
        )
        
        if datetime.now() >= recovery_time:
            logger.info("Attempting circuit breaker recovery")
            self.state = SchedulerState.RUNNING
            self._half_open_test_count = 0
            # Don't reset failure count yet - wait for successful operation
    
    def _handle_scheduler_error(self, error: Exception) -> None:
        """Handle general scheduler errors."""
        logger.error(f"Scheduler error: {error}")
        # Could implement additional error handling logic here
    
    def _save_state(self) -> None:
        """Save scheduler state to disk."""
        try:
            state_data = {
                "state": self.state.value,
                "consecutive_failures": self._consecutive_failures,
                "circuit_open_time": self._circuit_open_time.isoformat() if self._circuit_open_time else None,
                "total_space_freed_mb": self._total_space_freed_mb,
                "total_items_removed": self._total_items_removed,
                "last_cleanup_times": {
                    cleanup_type.value: time.isoformat() if time else None
                    for cleanup_type, time in self._last_cleanup_times.items()
                }
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save scheduler state: {e}")
    
    def _load_state(self) -> None:
        """Load scheduler state from disk."""
        try:
            if not self.state_file.exists():
                return
            
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)
            
            # Restore state (but don't auto-start)
            if state_data.get("state") == "running":
                self.state = SchedulerState.STOPPED  # Require explicit start
            else:
                self.state = SchedulerState(state_data.get("state", "stopped"))
            
            self._consecutive_failures = state_data.get("consecutive_failures", 0)
            self._total_space_freed_mb = state_data.get("total_space_freed_mb", 0.0)
            self._total_items_removed = state_data.get("total_items_removed", 0)
            
            circuit_open_str = state_data.get("circuit_open_time")
            if circuit_open_str:
                self._circuit_open_time = datetime.fromisoformat(circuit_open_str)
            
            # Restore last cleanup times
            last_cleanup_data = state_data.get("last_cleanup_times", {})
            for cleanup_type_str, time_str in last_cleanup_data.items():
                if time_str:
                    cleanup_type = CleanupType(cleanup_type_str)
                    self._last_cleanup_times[cleanup_type] = datetime.fromisoformat(time_str)
            
            logger.info("Scheduler state loaded from disk")
            
        except Exception as e:
            logger.warning(f"Failed to load scheduler state: {e}")


# Global scheduler instance for easy access
_global_scheduler: Optional[DockerCleanupScheduler] = None
_scheduler_lock = threading.Lock()


def get_cleanup_scheduler() -> DockerCleanupScheduler:
    """
    Get the global Docker cleanup scheduler instance.
    
    Returns:
        Singleton DockerCleanupScheduler instance
    """
    global _global_scheduler
    
    if _global_scheduler is None:
        with _scheduler_lock:
            if _global_scheduler is None:
                _global_scheduler = DockerCleanupScheduler()
    
    return _global_scheduler


def start_cleanup_scheduler() -> bool:
    """
    Start the global cleanup scheduler.
    
    Returns:
        True if started successfully
    """
    scheduler = get_cleanup_scheduler()
    return scheduler.start()


def stop_cleanup_scheduler() -> bool:
    """
    Stop the global cleanup scheduler.
    
    Returns:
        True if stopped successfully
    """
    scheduler = get_cleanup_scheduler()
    return scheduler.stop()


# Context manager for test session registration
@contextmanager
def test_session_context(test_id: str):
    """
    Context manager for registering test sessions with the cleanup scheduler.
    
    Args:
        test_id: Unique test session identifier
    """
    scheduler = get_cleanup_scheduler()
    scheduler.register_test_session(test_id)
    try:
        yield scheduler
    finally:
        scheduler.unregister_test_session(test_id, trigger_cleanup=True)
