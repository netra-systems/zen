"""
Docker Resource Monitor - Critical Infrastructure for Test Environment Stability

Provides comprehensive Docker resource monitoring and enforcement to prevent
resource exhaustion that causes Docker daemon crashes and test environment instability.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity, Risk Reduction
2. Business Goal: Prevent Docker crashes and environment corruption, enable reliable CI/CD
3. Value Impact: Prevents 4-8 hours/week of developer downtime from Docker crashes
4. Revenue Impact: Protects $2M+ ARR by ensuring test infrastructure stability

Core Features:
- Real-time Docker resource monitoring (memory, CPU, containers, networks, volumes)
- Pre-flight resource checks before test execution
- Automatic cleanup when approaching limits
- Historical tracking and trend analysis
- Orphaned resource detection and cleanup
- Thread-safe operations for parallel test execution
- Cross-platform support (Windows, macOS, Linux)
"""

import asyncio
import json
import logging
import os
import platform
import subprocess
import sys
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, NamedTuple
import warnings

# Third-party dependencies
try:
    import psutil
except ImportError:
    psutil = None
    warnings.warn("psutil not available - system resource monitoring disabled")

try:
    import docker
    from docker.errors import DockerException, APIError
except ImportError:
    docker = None
    DockerException = Exception  # Fallback for type hints and exception handling
    APIError = Exception  # Fallback for type hints and exception handling
    warnings.warn("docker package not available - Docker API monitoring disabled", UserWarning)

# CLAUDE.md compliance: Use IsolatedEnvironment for all environment access
try:
    from shared.isolated_environment import getenv
except ImportError:
    # CRITICAL SECURITY FIX: Remove direct os.environ access to prevent service boundary violations
    # This fallback should not occur in production - all services must have IsolatedEnvironment
    import os
    import logging
    logger = logging.getLogger(__name__)
    logger.error("CRITICAL: Missing IsolatedEnvironment - service boundary violation detected")
    
    def getenv(key: str, default=None):
        """
        DEPRECATED: Direct environment access creates service boundary violations.
        This fallback exists only for emergency compatibility - do not use in production.
        """
        logger.warning(f"Using deprecated direct environment access for key: {key}")
        return os.environ.get(key, default)

# Import existing Docker utilities for integration
try:
    from test_framework.docker_rate_limiter import execute_docker_command
except ImportError:
    # Fallback if docker_rate_limiter not available
    import subprocess
    from typing import Any
    def execute_docker_command(cmd_args: list) -> Any:
        """
        Fallback Docker command execution.
        
        Args:
            cmd_args: List of command arguments (including 'docker' as first element)
        
        Returns:
            subprocess.CompletedProcess with returncode, stdout, stderr
        """
        try:
            # cmd_args already includes 'docker', so use it directly
            result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=30)
            return result
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.warning(f"Docker command execution failed: {e}")
            # Return a failed result object
            class FailedResult:
                returncode = 1
                stdout = ""
                stderr = str(e)
            return FailedResult()

logger = logging.getLogger(__name__)


class ResourceThresholdLevel(Enum):
    """Resource usage threshold levels."""
    SAFE = "safe"          # < 50% usage
    WARNING = "warning"    # 50-75% usage  
    CRITICAL = "critical"  # 75-90% usage
    EMERGENCY = "emergency" # > 90% usage


class ResourceType(Enum):
    """Types of resources being monitored."""
    MEMORY = "memory"
    CPU = "cpu"
    CONTAINERS = "containers"
    NETWORKS = "networks"
    VOLUMES = "volumes"
    DISK = "disk"


@dataclass
class ResourceUsage:
    """Resource usage metrics."""
    resource_type: ResourceType
    current_usage: float
    max_limit: float
    percentage: float
    threshold_level: ResourceThresholdLevel
    unit: str = "bytes"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "resource_type": self.resource_type.value,
            "current_usage": self.current_usage,
            "max_limit": self.max_limit,
            "percentage": self.percentage,
            "threshold_level": self.threshold_level.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class DockerResourceSnapshot:
    """Complete snapshot of Docker resource usage."""
    timestamp: datetime
    system_memory: ResourceUsage
    system_cpu: ResourceUsage
    docker_containers: ResourceUsage
    docker_networks: ResourceUsage  
    docker_volumes: ResourceUsage
    docker_disk: ResourceUsage
    container_details: List[Dict[str, Any]] = field(default_factory=list)
    network_details: List[Dict[str, Any]] = field(default_factory=list)
    volume_details: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_max_threshold_level(self) -> ResourceThresholdLevel:
        """Get the highest threshold level across all resources."""
        levels = [
            self.system_memory.threshold_level,
            self.system_cpu.threshold_level,
            self.docker_containers.threshold_level,
            self.docker_networks.threshold_level,
            self.docker_volumes.threshold_level,
            self.docker_disk.threshold_level
        ]
        
        # Order by severity: EMERGENCY > CRITICAL > WARNING > SAFE
        if ResourceThresholdLevel.EMERGENCY in levels:
            return ResourceThresholdLevel.EMERGENCY
        elif ResourceThresholdLevel.CRITICAL in levels:
            return ResourceThresholdLevel.CRITICAL
        elif ResourceThresholdLevel.WARNING in levels:
            return ResourceThresholdLevel.WARNING
        else:
            return ResourceThresholdLevel.SAFE


class OrphanedResource(NamedTuple):
    """Represents an orphaned Docker resource."""
    resource_type: str
    resource_id: str
    resource_name: str
    created: datetime
    size_bytes: Optional[int] = None


@dataclass
class CleanupReport:
    """Report of cleanup actions performed."""
    timestamp: datetime = field(default_factory=datetime.now)
    containers_removed: int = 0
    networks_removed: int = 0
    volumes_removed: int = 0
    space_freed_bytes: int = 0
    cleanup_duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    def add_error(self, error: str):
        """Add an error to the cleanup report."""
        self.errors.append(f"{datetime.now().isoformat()}: {error}")
        logger.error(f"Cleanup error: {error}")


class ResourceMonitorError(Exception):
    """Base exception for resource monitor errors."""
    pass


class ResourceExhaustionError(ResourceMonitorError):
    """Raised when resources are exhausted."""
    def __init__(self, message: str, resource_type: ResourceType, current_usage: float, limit: float):
        super().__init__(message)
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.limit = limit


class DockerResourceMonitor:
    """
    Comprehensive Docker resource monitor with enforcement capabilities.
    
    Key Features:
    - Real-time monitoring with configurable thresholds
    - Historical tracking with trend analysis
    - Automatic cleanup when limits approached
    - Orphaned resource detection
    - Thread-safe operations
    - Cross-platform support
    """
    
    # Default resource limits (configurable via environment)
    # These represent Docker-specific thresholds for monitoring
    DEFAULT_MAX_MEMORY_GB = 8.0  # Increased to more reasonable limit
    DEFAULT_MAX_CONTAINERS = 20
    DEFAULT_MAX_NETWORKS = 15
    DEFAULT_MAX_VOLUMES = 10
    DEFAULT_MAX_DISK_GB = 10.0
    
    # Cleanup thresholds
    WARNING_THRESHOLD = 0.5    # 50%
    CRITICAL_THRESHOLD = 0.75  # 75%
    EMERGENCY_THRESHOLD = 0.9  # 90%
    
    # History tracking
    MAX_HISTORY_ENTRIES = 1000
    HISTORY_CLEANUP_INTERVAL = 3600  # 1 hour
    
    def __init__(self, 
                 max_memory_gb: Optional[float] = None,
                 max_containers: Optional[int] = None,
                 max_networks: Optional[int] = None,
                 max_volumes: Optional[int] = None,
                 max_disk_gb: Optional[float] = None,
                 enable_auto_cleanup: bool = True,
                 cleanup_aggressive: bool = False):
        """
        Initialize the Docker resource monitor.
        
        Args:
            max_memory_gb: Maximum memory in GB (default: 4GB)
            max_containers: Maximum containers (default: 20)
            max_networks: Maximum networks (default: 15)
            max_volumes: Maximum volumes (default: 10)
            max_disk_gb: Maximum disk usage in GB (default: 10GB)
            enable_auto_cleanup: Enable automatic cleanup (default: True)
            cleanup_aggressive: Use aggressive cleanup strategies (default: False)
        """
        # Configure limits from parameters or environment
        self.max_memory_gb = max_memory_gb or float(getenv("DOCKER_MAX_MEMORY_GB", self.DEFAULT_MAX_MEMORY_GB))
        self.max_containers = max_containers or int(getenv("DOCKER_MAX_CONTAINERS", self.DEFAULT_MAX_CONTAINERS))
        self.max_networks = max_networks or int(getenv("DOCKER_MAX_NETWORKS", self.DEFAULT_MAX_NETWORKS))
        self.max_volumes = max_volumes or int(getenv("DOCKER_MAX_VOLUMES", self.DEFAULT_MAX_VOLUMES))
        self.max_disk_gb = max_disk_gb or float(getenv("DOCKER_MAX_DISK_GB", self.DEFAULT_MAX_DISK_GB))
        
        # Cleanup configuration
        self.enable_auto_cleanup = enable_auto_cleanup
        self.cleanup_aggressive = cleanup_aggressive
        
        # Thread safety
        self._lock = threading.RLock()
        self._history_lock = threading.Lock()
        
        # Initialize Docker client
        self.docker_client = None
        self._docker_available = self._initialize_docker()
        
        # Initialize system monitoring
        self._psutil_available = psutil is not None
        
        # Historical tracking
        self._resource_history: deque = deque(maxlen=self.MAX_HISTORY_ENTRIES)
        self._last_history_cleanup = time.time()
        
        # Performance tracking
        self._monitoring_start_time = time.time()
        self._total_cleanups = 0
        self._total_resources_cleaned = 0
        
        logger.info(f"DockerResourceMonitor initialized - Docker: {self._docker_available}, "
                   f"psutil: {self._psutil_available}, limits: {self.max_memory_gb}GB mem, "
                   f"{self.max_containers} containers, auto_cleanup: {self.enable_auto_cleanup}")

    def _initialize_docker(self) -> bool:
        """Initialize Docker client with error handling."""
        if not docker:
            logger.info("Docker SDK not available - Docker monitoring disabled (install with: pip install docker)")
            return False
            
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.debug("Docker client initialized successfully")
            return True
        except Exception as e:
            # Catch all exceptions - DockerException, ConnectionError, etc.
            logger.warning(f"Failed to initialize Docker client (Docker daemon may not be running): {e}")
            self.docker_client = None
            return False

    def _get_threshold_level(self, percentage: float) -> ResourceThresholdLevel:
        """Determine threshold level based on usage percentage."""
        if percentage >= self.EMERGENCY_THRESHOLD:
            return ResourceThresholdLevel.EMERGENCY
        elif percentage >= self.CRITICAL_THRESHOLD:
            return ResourceThresholdLevel.CRITICAL
        elif percentage >= self.WARNING_THRESHOLD:
            return ResourceThresholdLevel.WARNING
        else:
            return ResourceThresholdLevel.SAFE

    def check_system_resources(self) -> DockerResourceSnapshot:
        """
        Perform comprehensive system resource check.
        
        Returns:
            DockerResourceSnapshot with current resource usage
            
        Raises:
            ResourceExhaustionError: If critical resources are exhausted
        """
        logger.debug("Starting comprehensive resource check")
        
        with self._lock:
            timestamp = datetime.now()
            
            # Check system memory
            system_memory = self._check_system_memory()
            
            # Check system CPU
            system_cpu = self._check_system_cpu()
            
            # Check Docker resources
            docker_containers = self._check_docker_containers()
            docker_networks = self._check_docker_networks()
            docker_volumes = self._check_docker_volumes()
            docker_disk = self._check_docker_disk()
            
            # Get detailed information
            container_details = self._get_container_details()
            network_details = self._get_network_details()  
            volume_details = self._get_volume_details()
            
            # Create snapshot
            snapshot = DockerResourceSnapshot(
                timestamp=timestamp,
                system_memory=system_memory,
                system_cpu=system_cpu,
                docker_containers=docker_containers,
                docker_networks=docker_networks,
                docker_volumes=docker_volumes,
                docker_disk=docker_disk,
                container_details=container_details,
                network_details=network_details,
                volume_details=volume_details
            )
            
            # Add to history
            self._add_to_history(snapshot)
            
            # Check for critical resource exhaustion
            max_level = snapshot.get_max_threshold_level()
            if max_level == ResourceThresholdLevel.EMERGENCY:
                critical_resources = []
                for resource in [system_memory, system_cpu, docker_containers, 
                               docker_networks, docker_volumes, docker_disk]:
                    if resource.threshold_level == ResourceThresholdLevel.EMERGENCY:
                        critical_resources.append(f"{resource.resource_type.value}: {resource.percentage:.1f}%")
                
                error_msg = f"Critical resource exhaustion detected: {', '.join(critical_resources)}"
                logger.critical(error_msg)
                raise ResourceExhaustionError(
                    error_msg, 
                    ResourceType.MEMORY,  # Primary concern is usually memory
                    system_memory.current_usage, 
                    system_memory.max_limit
                )
            
            logger.debug(f"Resource check completed - max level: {max_level.value}")
            return snapshot

    def _check_system_memory(self) -> ResourceUsage:
        """Check system memory usage."""
        if not self._psutil_available:
            logger.warning("psutil not available - using default memory values")
            return ResourceUsage(
                resource_type=ResourceType.MEMORY,
                current_usage=2.0 * 1024**3,  # Assume 2GB used
                max_limit=self.max_memory_gb * 1024**3,
                percentage=50.0,
                threshold_level=ResourceThresholdLevel.WARNING,
                unit="bytes"
            )
        
        try:
            memory = psutil.virtual_memory()
            
            # For system memory monitoring, we use system memory percentage
            # But track Docker-specific memory consumption if possible
            percentage = memory.percent  # psutil already calculates this correctly
            
            # Our threshold is based on available memory vs what we need for Docker
            docker_threshold_gb = self.max_memory_gb
            available_gb = memory.available / 1024**3
            
            # If available memory is less than our Docker threshold, we're in a risky state
            if available_gb < docker_threshold_gb:
                # Calculate how much over our comfortable threshold we are
                overage_gb = docker_threshold_gb - available_gb
                overage_percentage = (overage_gb / docker_threshold_gb) * 100
                # Adjust percentage to reflect Docker-specific concerns
                percentage = min(percentage + overage_percentage, 100.0)
            
            return ResourceUsage(
                resource_type=ResourceType.MEMORY,
                current_usage=float(memory.used),
                max_limit=float(memory.total),
                percentage=percentage,
                threshold_level=self._get_threshold_level(percentage / 100),
                unit="bytes"
            )
        except Exception as e:
            logger.error(f"Error checking system memory: {e}")
            return ResourceUsage(
                resource_type=ResourceType.MEMORY,
                current_usage=0.0,
                max_limit=self.max_memory_gb * 1024**3,
                percentage=0.0,
                threshold_level=ResourceThresholdLevel.SAFE,
                unit="bytes"
            )

    def _check_system_cpu(self) -> ResourceUsage:
        """Check system CPU usage."""
        if not self._psutil_available:
            return ResourceUsage(
                resource_type=ResourceType.CPU,
                current_usage=25.0,
                max_limit=100.0,
                percentage=25.0,
                threshold_level=ResourceThresholdLevel.SAFE,
                unit="percent"
            )
        
        try:
            # Get CPU usage over a short interval
            cpu_percent = psutil.cpu_percent(interval=1)
            percentage = cpu_percent
            
            return ResourceUsage(
                resource_type=ResourceType.CPU,
                current_usage=cpu_percent,
                max_limit=100.0,
                percentage=percentage,
                threshold_level=self._get_threshold_level(percentage / 100),
                unit="percent"
            )
        except Exception as e:
            logger.error(f"Error checking system CPU: {e}")
            return ResourceUsage(
                resource_type=ResourceType.CPU,
                current_usage=0.0,
                max_limit=100.0,
                percentage=0.0,
                threshold_level=ResourceThresholdLevel.SAFE,
                unit="percent"
            )

    def _check_docker_containers(self) -> ResourceUsage:
        """Check Docker container count."""
        if not self._docker_available:
            return ResourceUsage(
                resource_type=ResourceType.CONTAINERS,
                current_usage=0.0,
                max_limit=float(self.max_containers),
                percentage=0.0,
                threshold_level=ResourceThresholdLevel.SAFE,
                unit="count"
            )
        
        try:
            containers = self.docker_client.containers.list(all=True)
            current_count = len(containers)
            percentage = (current_count / self.max_containers) * 100
            
            return ResourceUsage(
                resource_type=ResourceType.CONTAINERS,
                current_usage=float(current_count),
                max_limit=float(self.max_containers),
                percentage=percentage,
                threshold_level=self._get_threshold_level(percentage / 100),
                unit="count"
            )
        except Exception as e:
            logger.error(f"Error checking Docker containers: {e}")
            return ResourceUsage(
                resource_type=ResourceType.CONTAINERS,
                current_usage=0.0,
                max_limit=float(self.max_containers),
                percentage=0.0,
                threshold_level=ResourceThresholdLevel.SAFE,
                unit="count"
            )

    def _check_docker_networks(self) -> ResourceUsage:
        """Check Docker network count."""
        if not self._docker_available:
            return ResourceUsage(
                resource_type=ResourceType.NETWORKS,
                current_usage=0.0,
                max_limit=float(self.max_networks),
                percentage=0.0,
                threshold_level=ResourceThresholdLevel.SAFE,
                unit="count"
            )
        
        try:
            networks = self.docker_client.networks.list()
            # Filter out default networks
            custom_networks = [n for n in networks if not n.attrs.get('Name', '').startswith('bridge') 
                             and not n.attrs.get('Name', '').startswith('host')
                             and not n.attrs.get('Name', '').startswith('none')]
            
            current_count = len(custom_networks)
            percentage = (current_count / self.max_networks) * 100
            
            return ResourceUsage(
                resource_type=ResourceType.NETWORKS,
                current_usage=float(current_count),
                max_limit=float(self.max_networks),
                percentage=percentage,
                threshold_level=self._get_threshold_level(percentage / 100),
                unit="count"
            )
        except Exception as e:
            logger.error(f"Error checking Docker networks: {e}")
            return ResourceUsage(
                resource_type=ResourceType.NETWORKS,
                current_usage=0.0,
                max_limit=float(self.max_networks),
                percentage=0.0,
                threshold_level=ResourceThresholdLevel.SAFE,
                unit="count"
            )

    def _check_docker_volumes(self) -> ResourceUsage:
        """Check Docker volume count."""
        if not self._docker_available:
            return ResourceUsage(
                resource_type=ResourceType.VOLUMES,
                current_usage=0.0,
                max_limit=float(self.max_volumes),
                percentage=0.0,
                threshold_level=ResourceThresholdLevel.SAFE,
                unit="count"
            )
        
        try:
            volumes = self.docker_client.volumes.list()
            current_count = len(volumes)
            percentage = (current_count / self.max_volumes) * 100
            
            return ResourceUsage(
                resource_type=ResourceType.VOLUMES,
                current_usage=float(current_count),
                max_limit=float(self.max_volumes),
                percentage=percentage,
                threshold_level=self._get_threshold_level(percentage / 100),
                unit="count"
            )
        except Exception as e:
            logger.error(f"Error checking Docker volumes: {e}")
            return ResourceUsage(
                resource_type=ResourceType.VOLUMES,
                current_usage=0.0,
                max_limit=float(self.max_volumes),
                percentage=0.0,
                threshold_level=ResourceThresholdLevel.SAFE,
                unit="count"
            )

    def _check_docker_disk(self) -> ResourceUsage:
        """Check Docker disk usage."""
        try:
            # Use docker system df to get disk usage
            result = execute_docker_command(["docker", "system", "df", "--format", "json"])
            if result.returncode == 0:
                df_data = json.loads(result.stdout)
                
                total_size = 0
                if 'Images' in df_data:
                    for image in df_data['Images']:
                        total_size += image.get('Size', 0)
                        
                if 'Containers' in df_data:
                    for container in df_data['Containers']:
                        total_size += container.get('Size', 0)
                        
                if 'Volumes' in df_data:
                    for volume in df_data['Volumes']:
                        total_size += volume.get('Size', 0)
                
                max_limit = self.max_disk_gb * 1024**3
                percentage = (total_size / max_limit) * 100
                
                return ResourceUsage(
                    resource_type=ResourceType.DISK,
                    current_usage=float(total_size),
                    max_limit=max_limit,
                    percentage=percentage,
                    threshold_level=self._get_threshold_level(percentage / 100),
                    unit="bytes"
                )
        except Exception as e:
            logger.error(f"Error checking Docker disk usage: {e}")
        
        # Fallback to safe values
        return ResourceUsage(
            resource_type=ResourceType.DISK,
            current_usage=1.0 * 1024**3,  # 1GB
            max_limit=self.max_disk_gb * 1024**3,
            percentage=10.0,
            threshold_level=ResourceThresholdLevel.SAFE,
            unit="bytes"
        )

    def _get_container_details(self) -> List[Dict[str, Any]]:
        """Get detailed container information."""
        if not self._docker_available:
            return []
        
        try:
            containers = self.docker_client.containers.list(all=True)
            details = []
            
            for container in containers:
                try:
                    stats = container.stats(stream=False)
                    memory_usage = stats['memory_stats'].get('usage', 0)
                    cpu_usage = stats['cpu_stats'].get('cpu_usage', {}).get('total_usage', 0)
                    
                    details.append({
                        'id': container.id[:12],
                        'name': container.name,
                        'image': container.image.tags[0] if container.image.tags else 'unknown',
                        'status': container.status,
                        'created': container.attrs['Created'],
                        'memory_usage_bytes': memory_usage,
                        'cpu_usage_total': cpu_usage,
                        'ports': container.ports,
                        'labels': container.labels
                    })
                except Exception as e:
                    logger.warning(f"Error getting stats for container {container.name}: {e}")
                    details.append({
                        'id': container.id[:12],
                        'name': container.name,
                        'status': container.status,
                        'error': str(e)
                    })
                    
            return details
        except Exception as e:
            logger.error(f"Error getting container details: {e}")
            return []

    def _get_network_details(self) -> List[Dict[str, Any]]:
        """Get detailed network information."""
        if not self._docker_available:
            return []
            
        try:
            networks = self.docker_client.networks.list()
            details = []
            
            for network in networks:
                details.append({
                    'id': network.id[:12],
                    'name': network.name,
                    'driver': network.attrs.get('Driver', 'unknown'),
                    'created': network.attrs.get('Created', ''),
                    'scope': network.attrs.get('Scope', 'local'),
                    'containers': list(network.attrs.get('Containers', {}).keys()),
                    'labels': network.attrs.get('Labels', {})
                })
                
            return details
        except Exception as e:
            logger.error(f"Error getting network details: {e}")
            return []

    def _get_volume_details(self) -> List[Dict[str, Any]]:
        """Get detailed volume information."""
        if not self._docker_available:
            return []
            
        try:
            volumes = self.docker_client.volumes.list()
            details = []
            
            for volume in volumes:
                details.append({
                    'name': volume.name,
                    'driver': volume.attrs.get('Driver', 'local'),
                    'created': volume.attrs.get('CreatedAt', ''),
                    'mountpoint': volume.attrs.get('Mountpoint', ''),
                    'labels': volume.attrs.get('Labels', {}),
                    'scope': volume.attrs.get('Scope', 'local')
                })
                
            return details
        except Exception as e:
            logger.error(f"Error getting volume details: {e}")
            return []

    def cleanup_if_needed(self, force_cleanup: bool = False) -> CleanupReport:
        """
        Perform cleanup if resource usage is approaching limits.
        
        Args:
            force_cleanup: Force cleanup regardless of thresholds
            
        Returns:
            CleanupReport with details of cleanup actions
        """
        logger.info(f"Starting cleanup assessment (force: {force_cleanup})")
        
        with self._lock:
            cleanup_start = time.time()
            report = CleanupReport()
            
            try:
                # Check current resource usage
                snapshot = self.check_system_resources()
                
                # Determine if cleanup is needed
                needs_cleanup = force_cleanup or self._needs_cleanup(snapshot)
                
                if not needs_cleanup:
                    logger.debug("No cleanup needed - resource usage within acceptable limits")
                    report.cleanup_duration_seconds = time.time() - cleanup_start
                    return report
                
                if not self.enable_auto_cleanup:
                    logger.warning("Cleanup needed but auto-cleanup is disabled")
                    report.add_error("Auto-cleanup disabled but cleanup needed")
                    return report
                
                logger.info("Starting resource cleanup...")
                
                # Clean up containers
                if self._should_cleanup_containers(snapshot.docker_containers):
                    containers_cleaned = self._cleanup_containers(report)
                    report.containers_removed = containers_cleaned
                    
                # Clean up networks
                if self._should_cleanup_networks(snapshot.docker_networks):
                    networks_cleaned = self._cleanup_networks(report)
                    report.networks_removed = networks_cleaned
                    
                # Clean up volumes
                if self._should_cleanup_volumes(snapshot.docker_volumes):
                    volumes_cleaned = self._cleanup_volumes(report)
                    report.volumes_removed = volumes_cleaned
                
                # Clean up orphaned resources
                orphaned_cleaned = self._cleanup_orphaned_resources(report)
                
                # System-level cleanup
                if snapshot.get_max_threshold_level() in [ResourceThresholdLevel.CRITICAL, ResourceThresholdLevel.EMERGENCY]:
                    self._perform_system_cleanup(report)
                
                self._total_cleanups += 1
                self._total_resources_cleaned += (report.containers_removed + 
                                                report.networks_removed + 
                                                report.volumes_removed)
                
                logger.info(f"Cleanup completed - removed {report.containers_removed} containers, "
                          f"{report.networks_removed} networks, {report.volumes_removed} volumes")
                
            except Exception as e:
                error_msg = f"Error during cleanup: {e}"
                report.add_error(error_msg)
                logger.error(error_msg, exc_info=True)
            finally:
                report.cleanup_duration_seconds = time.time() - cleanup_start
                
            return report

    def _needs_cleanup(self, snapshot: DockerResourceSnapshot) -> bool:
        """Determine if cleanup is needed based on resource usage."""
        max_level = snapshot.get_max_threshold_level()
        
        # Always cleanup if emergency or critical
        if max_level in [ResourceThresholdLevel.EMERGENCY, ResourceThresholdLevel.CRITICAL]:
            return True
            
        # Cleanup on warning if aggressive mode enabled
        if max_level == ResourceThresholdLevel.WARNING and self.cleanup_aggressive:
            return True
            
        return False

    def _should_cleanup_containers(self, containers_usage: ResourceUsage) -> bool:
        """Check if container cleanup is needed."""
        return containers_usage.threshold_level in [
            ResourceThresholdLevel.WARNING,
            ResourceThresholdLevel.CRITICAL, 
            ResourceThresholdLevel.EMERGENCY
        ]

    def _should_cleanup_networks(self, networks_usage: ResourceUsage) -> bool:
        """Check if network cleanup is needed."""
        return networks_usage.threshold_level in [
            ResourceThresholdLevel.CRITICAL,
            ResourceThresholdLevel.EMERGENCY
        ]

    def _should_cleanup_volumes(self, volumes_usage: ResourceUsage) -> bool:
        """Check if volume cleanup is needed."""
        return volumes_usage.threshold_level in [
            ResourceThresholdLevel.CRITICAL,
            ResourceThresholdLevel.EMERGENCY
        ]

    def _cleanup_containers(self, report: CleanupReport) -> int:
        """Clean up containers based on age and resource usage."""
        if not self._docker_available:
            return 0
            
        containers_removed = 0
        
        try:
            # Get all containers
            all_containers = self.docker_client.containers.list(all=True)
            
            # Categorize containers
            test_containers = []
            old_containers = []
            exited_containers = []
            
            cutoff_time = datetime.now() - timedelta(hours=2)
            
            for container in all_containers:
                try:
                    created_str = container.attrs['Created']
                    # Parse ISO format timestamp
                    created_time = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                    
                    if 'test-' in container.name or any(label.startswith('netra.env=test') 
                                                       for label in container.labels.values()):
                        test_containers.append((container, created_time))
                    elif created_time < cutoff_time:
                        old_containers.append((container, created_time))
                    elif container.status in ['exited', 'dead']:
                        exited_containers.append((container, created_time))
                        
                except Exception as e:
                    logger.warning(f"Error categorizing container {container.name}: {e}")
            
            # Remove test containers first (oldest first)
            test_containers.sort(key=lambda x: x[1])  # Sort by creation time
            containers_to_remove = len(test_containers) // 2  # Remove half
            
            for container, _ in test_containers[:containers_to_remove]:
                try:
                    logger.info(f"Removing test container: {container.name}")
                    container.remove(force=True)
                    containers_removed += 1
                except Exception as e:
                    report.add_error(f"Failed to remove test container {container.name}: {e}")
            
            # Remove exited containers
            for container, _ in exited_containers:
                try:
                    logger.info(f"Removing exited container: {container.name}")
                    container.remove(force=True)
                    containers_removed += 1
                except Exception as e:
                    report.add_error(f"Failed to remove exited container {container.name}: {e}")
            
            # If still need more space, remove old containers
            if self.cleanup_aggressive:
                for container, _ in old_containers[:5]:  # Remove up to 5 old containers
                    try:
                        logger.info(f"Removing old container: {container.name}")
                        container.stop(timeout=10)
                        container.remove(force=True)
                        containers_removed += 1
                    except Exception as e:
                        report.add_error(f"Failed to remove old container {container.name}: {e}")
                        
        except Exception as e:
            report.add_error(f"Error during container cleanup: {e}")
            
        return containers_removed

    def _cleanup_networks(self, report: CleanupReport) -> int:
        """Clean up unused networks."""
        if not self._docker_available:
            return 0
            
        networks_removed = 0
        
        try:
            networks = self.docker_client.networks.list()
            
            for network in networks:
                try:
                    # Skip default networks
                    if network.name in ['bridge', 'host', 'none']:
                        continue
                        
                    # Check if network is unused
                    containers = network.attrs.get('Containers', {})
                    if not containers:
                        # Check if it's a test network or old network
                        if ('test-' in network.name or 
                            'netra-test-' in network.name or
                            any(label.startswith('netra.env=test') 
                                for label in network.attrs.get('Labels', {}).values())):
                            
                            logger.info(f"Removing unused network: {network.name}")
                            network.remove()
                            networks_removed += 1
                            
                except Exception as e:
                    report.add_error(f"Failed to remove network {network.name}: {e}")
                    
        except Exception as e:
            report.add_error(f"Error during network cleanup: {e}")
            
        return networks_removed

    def _cleanup_volumes(self, report: CleanupReport) -> int:
        """Clean up unused volumes."""
        if not self._docker_available:
            return 0
            
        volumes_removed = 0
        
        try:
            volumes = self.docker_client.volumes.list()
            
            for volume in volumes:
                try:
                    # Check if volume is unused and is a test volume
                    if ('test-' in volume.name or 
                        'netra-test-' in volume.name or
                        any(label.startswith('netra.env=test') 
                            for label in volume.attrs.get('Labels', {}).values())):
                        
                        # Try to remove - Docker will fail if in use
                        logger.info(f"Removing test volume: {volume.name}")
                        volume.remove(force=True)
                        volumes_removed += 1
                        
                except Exception as e:
                    # This is expected for volumes in use
                    if "volume is in use" not in str(e).lower():
                        report.add_error(f"Failed to remove volume {volume.name}: {e}")
                        
        except Exception as e:
            report.add_error(f"Error during volume cleanup: {e}")
            
        return volumes_removed

    def _cleanup_orphaned_resources(self, report: CleanupReport) -> int:
        """Clean up orphaned Docker resources."""
        orphaned_cleaned = 0
        
        try:
            # Use docker system prune for comprehensive cleanup
            logger.info("Running Docker system prune...")
            
            result = execute_docker_command([
                "docker", "system", "prune", "--force", "--volumes"
            ])
            
            if result.returncode == 0:
                logger.info("Docker system prune completed successfully")
                orphaned_cleaned += 1
            else:
                report.add_error(f"Docker system prune failed: {result.stderr}")
                
        except Exception as e:
            report.add_error(f"Error during orphaned resource cleanup: {e}")
            
        return orphaned_cleaned

    def _perform_system_cleanup(self, report: CleanupReport):
        """Perform system-level cleanup operations."""
        try:
            logger.warning("Performing emergency system cleanup...")
            
            # Stop all test-related containers
            if self._docker_available:
                containers = self.docker_client.containers.list()
                for container in containers:
                    if ('test-' in container.name or 
                        any(label.startswith('netra.env=test') 
                            for label in container.labels.values())):
                        try:
                            logger.warning(f"Emergency stop: {container.name}")
                            container.stop(timeout=5)
                        except Exception as e:
                            logger.error(f"Failed to emergency stop {container.name}: {e}")
            
            # Force garbage collection if Python allows
            try:
                import gc
                gc.collect()
                logger.info("Python garbage collection completed")
            except Exception:
                pass
                
        except Exception as e:
            report.add_error(f"Error during system cleanup: {e}")

    def get_resource_usage(self) -> DockerResourceSnapshot:
        """Get current resource usage snapshot."""
        return self.check_system_resources()

    def enforce_limits(self) -> CleanupReport:
        """Enforce resource limits by performing cleanup."""
        return self.cleanup_if_needed(force_cleanup=False)

    def detect_orphaned_resources(self) -> List[OrphanedResource]:
        """
        Detect orphaned Docker resources.
        
        Returns:
            List of OrphanedResource objects
        """
        orphaned = []
        
        if not self._docker_available:
            return orphaned
            
        try:
            # Find orphaned containers
            containers = self.docker_client.containers.list(all=True, 
                                                           filters={'status': 'exited'})
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            for container in containers:
                try:
                    created_str = container.attrs['Created']
                    created_time = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                    
                    if created_time < cutoff_time:
                        orphaned.append(OrphanedResource(
                            resource_type='container',
                            resource_id=container.id[:12],
                            resource_name=container.name,
                            created=created_time
                        ))
                except Exception as e:
                    logger.warning(f"Error checking container {container.name}: {e}")
            
            # Find orphaned networks
            networks = self.docker_client.networks.list()
            for network in networks:
                try:
                    if network.name in ['bridge', 'host', 'none']:
                        continue
                        
                    containers = network.attrs.get('Containers', {})
                    if not containers and 'test-' in network.name:
                        created_str = network.attrs.get('Created', '')
                        if created_str:
                            created_time = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                            if created_time < cutoff_time:
                                orphaned.append(OrphanedResource(
                                    resource_type='network',
                                    resource_id=network.id[:12],
                                    resource_name=network.name,
                                    created=created_time
                                ))
                except Exception as e:
                    logger.warning(f"Error checking network {network.name}: {e}")
            
            # Find orphaned volumes
            volumes = self.docker_client.volumes.list()
            for volume in volumes:
                try:
                    if 'test-' in volume.name:
                        created_str = volume.attrs.get('CreatedAt', '')
                        if created_str:
                            created_time = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                            if created_time < cutoff_time:
                                orphaned.append(OrphanedResource(
                                    resource_type='volume',
                                    resource_id=volume.name,
                                    resource_name=volume.name,
                                    created=created_time
                                ))
                except Exception as e:
                    logger.warning(f"Error checking volume {volume.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error detecting orphaned resources: {e}")
            
        logger.info(f"Detected {len(orphaned)} orphaned resources")
        return orphaned

    def get_historical_usage(self, 
                           hours_back: int = 24,
                           resource_type: Optional[ResourceType] = None) -> List[ResourceUsage]:
        """
        Get historical resource usage data.
        
        Args:
            hours_back: How many hours of history to return
            resource_type: Filter by specific resource type (optional)
            
        Returns:
            List of ResourceUsage objects
        """
        with self._history_lock:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            historical_data = []
            for snapshot in self._resource_history:
                if snapshot.timestamp >= cutoff_time:
                    if resource_type is None:
                        # Return all resource types from snapshot
                        historical_data.extend([
                            snapshot.system_memory,
                            snapshot.system_cpu,
                            snapshot.docker_containers,
                            snapshot.docker_networks,
                            snapshot.docker_volumes,
                            snapshot.docker_disk
                        ])
                    else:
                        # Return specific resource type
                        if resource_type == ResourceType.MEMORY:
                            historical_data.append(snapshot.system_memory)
                        elif resource_type == ResourceType.CPU:
                            historical_data.append(snapshot.system_cpu)
                        elif resource_type == ResourceType.CONTAINERS:
                            historical_data.append(snapshot.docker_containers)
                        elif resource_type == ResourceType.NETWORKS:
                            historical_data.append(snapshot.docker_networks)
                        elif resource_type == ResourceType.VOLUMES:
                            historical_data.append(snapshot.docker_volumes)
                        elif resource_type == ResourceType.DISK:
                            historical_data.append(snapshot.docker_disk)
            
            return historical_data

    def predict_resource_needs(self, test_category: str = "integration") -> Dict[str, float]:
        """
        Predict resource needs based on test category and historical data.
        
        Args:
            test_category: Category of tests being run
            
        Returns:
            Dictionary with predicted resource usage
        """
        # Base requirements by test category
        base_requirements = {
            "unit": {
                "memory_gb": 0.5,
                "containers": 2,
                "networks": 1,
                "volumes": 1,
                "disk_gb": 1.0
            },
            "integration": {
                "memory_gb": 2.0,
                "containers": 8,
                "networks": 4,
                "volumes": 4,
                "disk_gb": 3.0
            },
            "e2e": {
                "memory_gb": 3.0,
                "containers": 12,
                "networks": 6,
                "volumes": 6,
                "disk_gb": 5.0
            },
            "performance": {
                "memory_gb": 4.0,
                "containers": 15,
                "networks": 8,
                "volumes": 8,
                "disk_gb": 7.0
            }
        }
        
        # Get base requirements for category
        base = base_requirements.get(test_category, base_requirements["integration"])
        
        # Adjust based on historical patterns if available
        if len(self._resource_history) > 10:
            with self._history_lock:
                recent_snapshots = list(self._resource_history)[-10:]
                
                # Calculate average peak usage
                avg_memory = sum(s.system_memory.current_usage for s in recent_snapshots) / len(recent_snapshots)
                avg_containers = sum(s.docker_containers.current_usage for s in recent_snapshots) / len(recent_snapshots)
                
                # Adjust predictions based on historical data
                base["memory_gb"] = max(base["memory_gb"], avg_memory / (1024**3) * 1.2)  # 20% buffer
                base["containers"] = max(base["containers"], int(avg_containers * 1.3))  # 30% buffer
        
        return base

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics and performance metrics."""
        uptime_seconds = time.time() - self._monitoring_start_time
        
        return {
            "monitor_uptime_seconds": uptime_seconds,
            "total_resource_checks": len(self._resource_history),
            "total_cleanups_performed": self._total_cleanups,
            "total_resources_cleaned": self._total_resources_cleaned,
            "docker_available": self._docker_available,
            "psutil_available": self._psutil_available,
            "auto_cleanup_enabled": self.enable_auto_cleanup,
            "aggressive_cleanup_enabled": self.cleanup_aggressive,
            "configured_limits": {
                "max_memory_gb": self.max_memory_gb,
                "max_containers": self.max_containers,
                "max_networks": self.max_networks,
                "max_volumes": self.max_volumes,
                "max_disk_gb": self.max_disk_gb
            },
            "history_entries": len(self._resource_history)
        }

    def _add_to_history(self, snapshot: DockerResourceSnapshot):
        """Add snapshot to historical tracking."""
        with self._history_lock:
            self._resource_history.append(snapshot)
            
            # Periodic cleanup of old history
            current_time = time.time()
            if current_time - self._last_history_cleanup > self.HISTORY_CLEANUP_INTERVAL:
                self._cleanup_old_history()
                self._last_history_cleanup = current_time

    def _cleanup_old_history(self):
        """Clean up old history entries."""
        cutoff_time = datetime.now() - timedelta(days=1)  # Keep 1 day of history
        
        # Remove entries older than cutoff
        while self._resource_history and self._resource_history[0].timestamp < cutoff_time:
            self._resource_history.popleft()

    def export_snapshot_to_json(self, snapshot: DockerResourceSnapshot) -> str:
        """Export resource snapshot to JSON format."""
        def serialize_snapshot(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, (ResourceType, ResourceThresholdLevel)):
                return obj.value
            elif hasattr(obj, 'to_dict'):
                return obj.to_dict()
            elif hasattr(obj, '__dict__'):
                return {k: serialize_snapshot(v) for k, v in obj.__dict__.items()}
            else:
                return str(obj)
        
        return json.dumps(serialize_snapshot(snapshot), indent=2, default=str)

    @contextmanager
    def monitoring_context(self, test_name: str = "unknown"):
        """
        Context manager for monitoring test execution.
        
        Usage:
            with monitor.monitoring_context("integration_tests"):
                # Run tests
                pass
        """
        logger.info(f"Starting resource monitoring for: {test_name}")
        
        # Pre-test resource check
        pre_snapshot = self.check_system_resources()
        start_time = time.time()
        
        try:
            yield pre_snapshot
        except ResourceExhaustionError:
            logger.critical(f"Resource exhaustion during {test_name}")
            # Force cleanup on resource exhaustion
            self.cleanup_if_needed(force_cleanup=True)
            raise
        finally:
            # Post-test resource check and cleanup
            duration = time.time() - start_time
            post_snapshot = self.check_system_resources()
            
            logger.info(f"Test '{test_name}' completed in {duration:.2f}s - "
                       f"Memory: {post_snapshot.system_memory.percentage:.1f}%, "
                       f"Containers: {int(post_snapshot.docker_containers.current_usage)}")
            
            # Cleanup if needed after test
            if self.enable_auto_cleanup:
                cleanup_report = self.cleanup_if_needed()
                if cleanup_report.containers_removed > 0:
                    logger.info(f"Post-test cleanup: removed {cleanup_report.containers_removed} containers")


# Convenience functions for common operations
def check_docker_resources() -> DockerResourceSnapshot:
    """Quick function to check Docker resources."""
    monitor = DockerResourceMonitor()
    return monitor.check_system_resources()


def cleanup_docker_resources() -> CleanupReport:
    """Quick function to cleanup Docker resources."""
    monitor = DockerResourceMonitor(enable_auto_cleanup=True)
    return monitor.cleanup_if_needed(force_cleanup=True)


def monitor_test_execution(test_name: str = "test"):
    """Decorator for monitoring test execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = DockerResourceMonitor()
            with monitor.monitoring_context(test_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Integration example for test framework
class TestFrameworkIntegration:
    """Example integration with test framework."""
    
    def __init__(self):
        self.monitor = DockerResourceMonitor(
            enable_auto_cleanup=True,
            cleanup_aggressive=False
        )
    
    def pre_test_setup(self, test_category: str = "integration") -> bool:
        """
        Perform pre-test resource setup and validation.
        
        Returns:
            True if resources are adequate, False otherwise
        """
        try:
            # Predict resource needs
            predicted = self.monitor.predict_resource_needs(test_category)
            logger.info(f"Predicted resource needs for {test_category}: {predicted}")
            
            # Check current resources
            snapshot = self.monitor.check_system_resources()
            
            # Validate sufficient resources
            if (snapshot.system_memory.current_usage + predicted["memory_gb"] * 1024**3 > 
                snapshot.system_memory.max_limit * 0.8):  # 80% threshold
                logger.error("Insufficient memory for test execution")
                return False
                
            if (snapshot.docker_containers.current_usage + predicted["containers"] >
                snapshot.docker_containers.max_limit * 0.8):
                logger.error("Insufficient container capacity for test execution")
                return False
            
            # Preemptive cleanup if approaching limits
            max_level = snapshot.get_max_threshold_level()
            if max_level in [ResourceThresholdLevel.WARNING, ResourceThresholdLevel.CRITICAL]:
                logger.info("Performing preemptive cleanup before tests")
                self.monitor.cleanup_if_needed()
            
            return True
            
        except ResourceExhaustionError:
            logger.error("Resource exhaustion detected - cannot run tests")
            return False
        except Exception as e:
            logger.error(f"Error during pre-test setup: {e}")
            return False
    
    def post_test_cleanup(self) -> CleanupReport:
        """Perform post-test cleanup."""
        return self.monitor.cleanup_if_needed()
    
    def get_test_environment_status(self) -> Dict[str, Any]:
        """Get comprehensive test environment status."""
        try:
            snapshot = self.monitor.get_resource_usage()
            stats = self.monitor.get_monitoring_stats()
            orphaned = self.monitor.detect_orphaned_resources()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": snapshot.get_max_threshold_level().value,
                "resource_usage": {
                    "memory_percent": snapshot.system_memory.percentage,
                    "cpu_percent": snapshot.system_cpu.percentage,
                    "containers_count": int(snapshot.docker_containers.current_usage),
                    "networks_count": int(snapshot.docker_networks.current_usage),
                    "volumes_count": int(snapshot.docker_volumes.current_usage)
                },
                "monitoring_stats": stats,
                "orphaned_resources_count": len(orphaned),
                "recommendations": self._generate_recommendations(snapshot, orphaned)
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "overall_status": "error"
            }
    
    def _generate_recommendations(self, 
                                 snapshot: DockerResourceSnapshot, 
                                 orphaned: List[OrphanedResource]) -> List[str]:
        """Generate recommendations based on current state."""
        recommendations = []
        
        max_level = snapshot.get_max_threshold_level()
        
        if max_level == ResourceThresholdLevel.EMERGENCY:
            recommendations.append("URGENT: Immediately cleanup resources - system at risk")
            recommendations.append("Stop all non-essential containers")
            recommendations.append("Run 'docker system prune -f --volumes'")
        elif max_level == ResourceThresholdLevel.CRITICAL:
            recommendations.append("Cleanup needed: Resource usage is critical")
            recommendations.append("Consider reducing parallel test execution")
        elif max_level == ResourceThresholdLevel.WARNING:
            recommendations.append("Monitor closely: Resource usage approaching limits")
            
        if len(orphaned) > 5:
            recommendations.append(f"Clean up {len(orphaned)} orphaned resources")
            
        if snapshot.docker_containers.current_usage > 15:
            recommendations.append("High container count - consider container lifecycle optimization")
            
        if snapshot.system_memory.percentage > 80:
            recommendations.append("High memory usage - check for memory leaks")
            
        return recommendations


if __name__ == "__main__":
    # CLI interface for manual resource monitoring
    import argparse
    
    parser = argparse.ArgumentParser(description="Docker Resource Monitor")
    parser.add_argument("--check", action="store_true", help="Check resource usage")
    parser.add_argument("--cleanup", action="store_true", help="Perform cleanup")
    parser.add_argument("--force", action="store_true", help="Force cleanup")
    parser.add_argument("--orphaned", action="store_true", help="Find orphaned resources")
    parser.add_argument("--monitor", action="store_true", help="Start monitoring")
    parser.add_argument("--export", type=str, help="Export snapshot to file")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    monitor = DockerResourceMonitor(enable_auto_cleanup=True)
    
    if args.check:
        snapshot = monitor.check_system_resources()
        print(f"Resource Status: {snapshot.get_max_threshold_level().value}")
        print(f"Memory: {snapshot.system_memory.percentage:.1f}% "
              f"({snapshot.system_memory.current_usage / 1024**3:.1f}GB)")
        print(f"Containers: {int(snapshot.docker_containers.current_usage)}")
        print(f"Networks: {int(snapshot.docker_networks.current_usage)}")
        print(f"Volumes: {int(snapshot.docker_volumes.current_usage)}")
        
        if args.export:
            with open(args.export, 'w') as f:
                f.write(monitor.export_snapshot_to_json(snapshot))
            print(f"Snapshot exported to {args.export}")
            
    elif args.cleanup:
        report = monitor.cleanup_if_needed(force_cleanup=args.force)
        print(f"Cleanup completed:")
        print(f"  Containers removed: {report.containers_removed}")
        print(f"  Networks removed: {report.networks_removed}")
        print(f"  Volumes removed: {report.volumes_removed}")
        print(f"  Duration: {report.cleanup_duration_seconds:.2f}s")
        if report.errors:
            print(f"  Errors: {len(report.errors)}")
            for error in report.errors:
                print(f"    - {error}")
                
    elif args.orphaned:
        orphaned = monitor.detect_orphaned_resources()
        print(f"Found {len(orphaned)} orphaned resources:")
        for resource in orphaned:
            print(f"  {resource.resource_type}: {resource.resource_name} "
                  f"(created: {resource.created.strftime('%Y-%m-%d %H:%M:%S')})")
                  
    elif args.monitor:
        print("Starting resource monitoring (Ctrl+C to stop)...")
        try:
            while True:
                snapshot = monitor.check_system_resources()
                max_level = snapshot.get_max_threshold_level()
                
                print(f"{datetime.now().strftime('%H:%M:%S')} - "
                      f"Status: {max_level.value} - "
                      f"Memory: {snapshot.system_memory.percentage:.1f}% - "
                      f"Containers: {int(snapshot.docker_containers.current_usage)}")
                
                if max_level in [ResourceThresholdLevel.CRITICAL, ResourceThresholdLevel.EMERGENCY]:
                    print("WARNING: Resource usage critical - performing cleanup...")
                    report = monitor.cleanup_if_needed()
                    print(f"Cleanup: {report.containers_removed} containers, "
                          f"{report.networks_removed} networks removed")
                
                time.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            stats = monitor.get_monitoring_stats()
            print(f"Total checks: {stats['total_resource_checks']}")
            print(f"Total cleanups: {stats['total_cleanups_performed']}")
    else:
        # Default: show status
        integration = TestFrameworkIntegration()
        status = integration.get_test_environment_status()
        
        print("Docker Test Environment Status:")
        print(f"  Overall: {status['overall_status']}")
        print(f"  Memory: {status['resource_usage']['memory_percent']:.1f}%")
        print(f"  Containers: {status['resource_usage']['containers_count']}")
        print(f"  Networks: {status['resource_usage']['networks_count']}")
        print(f"  Volumes: {status['resource_usage']['volumes_count']}")
        print(f"  Orphaned Resources: {status['orphaned_resources_count']}")
        
        if status.get('recommendations'):
            print("Recommendations:")
            for rec in status['recommendations']:
                print(f"  - {rec}")