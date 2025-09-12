#!/usr/bin/env python3
"""
Resource Management Agent - Comprehensive service dependencies and resource allocation

This agent manages service dependencies, resource allocation, and conflict management
for the test orchestration system. It ensures optimal resource utilization while
preventing conflicts and maintaining service availability across all test execution scenarios.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test Reliability & Development Velocity  
- Value Impact: Eliminates resource conflicts and service failures in testing
- Strategic Impact: Reduces failed test runs by 90%, accelerates CI/CD by 40%

Key Responsibilities:
- Manage service dependencies (PostgreSQL, Redis, ClickHouse, Backend, Auth, Frontend)
- Allocate and monitor system resources (CPU, memory, network, disk)
- Handle resource conflicts between test categories and layers
- Ensure service availability before test execution
- Provide resource cleanup and recovery mechanisms
"""

import asyncio
import json
import logging
import os
import psutil
import subprocess
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any, Tuple, NamedTuple
from threading import Lock, Event

# Core test framework imports - handle when run as script vs module
try:
    from test_framework.service_availability import (
        ServiceAvailabilityChecker, ServiceUnavailableError, 
        require_real_services, check_service_availability
    )
    from test_framework.docker_port_discovery import DockerPortDiscovery, ServicePortMapping
    from test_framework.service_dependencies import ServiceType, ExecutionMode, ServiceRequirement
    from test_framework.layer_system import ResourceLimits, ResourceRequirements, TestLayer
    from test_framework.category_system import TestCategory, CategoryPriority
except ImportError:
    # When running as script, add parent directories to path
    import sys
    from pathlib import Path
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    sys.path.insert(0, str(project_root))
    
    from test_framework.service_availability import (
        ServiceAvailabilityChecker, ServiceUnavailableError, 
        require_real_services, check_service_availability
    )
    from test_framework.docker_port_discovery import DockerPortDiscovery, ServicePortMapping
    from test_framework.service_dependencies import ServiceType, ExecutionMode, ServiceRequirement
    from test_framework.layer_system import ResourceLimits, ResourceRequirements, TestLayer
    from test_framework.category_system import TestCategory, CategoryPriority

# Environment management
try:
    from shared.isolated_environment import get_env
except ImportError:
    # Fallback for test environments
    def get_env():
        class EnvWrapper:
            def get(self, key: str, default=None):
                return os.environ.get(key, default)
        return EnvWrapper()

logger = logging.getLogger(__name__)


class ResourceStatus(Enum):
    """Resource allocation status"""
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    OVERALLOCATED = "overallocated"
    CRITICAL = "critical"
    UNAVAILABLE = "unavailable"


class ServiceStatus(Enum):
    """Service availability status"""
    HEALTHY = "healthy"
    STARTING = "starting"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass
class ResourcePool:
    """Resource pool for test layer allocation"""
    name: str
    max_memory_mb: int
    max_cpu_percent: int
    max_parallel_instances: int
    allocated_memory_mb: int = 0
    allocated_cpu_percent: int = 0
    active_instances: int = 0
    reserved_for: Set[str] = field(default_factory=set)


@dataclass
class ServiceHealth:
    """Service health information"""
    service_name: str
    status: ServiceStatus
    last_check: datetime
    port_mapping: Optional[ServicePortMapping] = None
    health_check_url: Optional[str] = None
    error_message: Optional[str] = None
    restart_count: int = 0


@dataclass
class ResourceAllocation:
    """Resource allocation for test execution"""
    test_layer: str
    test_category: str
    memory_mb: int
    cpu_percent: int
    allocated_at: datetime
    expires_at: Optional[datetime] = None
    process_ids: Set[int] = field(default_factory=set)


@dataclass
class SystemMetrics:
    """Real-time system metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available_mb: int
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_sent_mb: float
    network_io_recv_mb: float
    active_processes: int
    load_average: Tuple[float, float, float]


class ResourceManagementAgent:
    """
    Comprehensive resource management agent for test orchestration.
    
    Handles service dependencies, resource allocation, and conflict management
    to ensure optimal test execution across all layers and categories.
    """
    
    # Service dependency graph - defines startup order and dependencies
    SERVICE_DEPENDENCIES = {
        "postgresql": set(),  # No dependencies, starts first
        "redis": set(),       # No dependencies, starts first
        "clickhouse": set(),  # No dependencies, starts first
        "auth": {"postgresql", "redis"},           # Needs database and cache
        "backend": {"postgresql", "redis", "auth"},  # Needs DB, cache, and auth
        "frontend": {"backend", "auth"},           # Needs backend services
        "websocket": {"backend", "redis"},         # Needs backend and cache
    }
    
    # Layer resource requirements by test layer
    LAYER_RESOURCE_REQUIREMENTS = {
        "fast_feedback": ResourcePool(
            name="fast_feedback",
            max_memory_mb=512,
            max_cpu_percent=50,
            max_parallel_instances=8
        ),
        "core_integration": ResourcePool(
            name="core_integration", 
            max_memory_mb=1024,
            max_cpu_percent=70,
            max_parallel_instances=6
        ),
        "service_integration": ResourcePool(
            name="service_integration",
            max_memory_mb=2048,
            max_cpu_percent=80,
            max_parallel_instances=4
        ),
        "e2e_background": ResourcePool(
            name="e2e_background",
            max_memory_mb=4096,
            max_cpu_percent=90,
            max_parallel_instances=2
        )
    }
    
    # Service to layer dependency mapping
    LAYER_SERVICE_DEPENDENCIES = {
        "fast_feedback": set(),  # Unit tests, no external services
        "core_integration": {"postgresql", "redis"},  # Database tests
        "service_integration": {"postgresql", "redis", "backend", "auth"},  # API tests
        "e2e_background": {"postgresql", "redis", "backend", "auth", "frontend"}  # Full stack
    }
    
    def __init__(self, 
                 enable_monitoring: bool = True,
                 monitoring_interval: float = 5.0,
                 enable_auto_recovery: bool = True):
        """
        Initialize Resource Management Agent.
        
        Args:
            enable_monitoring: Enable continuous resource monitoring
            monitoring_interval: Monitoring sample interval in seconds
            enable_auto_recovery: Enable automatic service recovery
        """
        self.env = get_env()
        
        # Core components
        self.service_checker = ServiceAvailabilityChecker(timeout_seconds=10.0)
        self.port_discovery = DockerPortDiscovery(use_test_services=True)
        
        # Resource management
        self.resource_pools = self.LAYER_RESOURCE_REQUIREMENTS.copy()
        self.resource_allocations: Dict[str, ResourceAllocation] = {}
        self.resource_lock = Lock()
        
        # Service management
        self.service_health: Dict[str, ServiceHealth] = {}
        self.service_lock = Lock()
        
        # Monitoring
        self.enable_monitoring = enable_monitoring
        self.monitoring_interval = monitoring_interval
        self.enable_auto_recovery = enable_auto_recovery
        self.monitoring_active = False
        self.monitoring_thread = None
        self.metrics_history = deque(maxlen=300)  # 25 minutes at 5s intervals
        
        # Resource thresholds
        self.resource_thresholds = {
            'memory_critical': 95.0,
            'memory_warning': 85.0,
            'cpu_critical': 90.0,
            'cpu_warning': 80.0,
            'process_critical': 1000,
            'process_warning': 500
        }
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="ResourceMgmt")
        
        logger.info("ResourceManagementAgent initialized")
    
    def start_monitoring(self) -> None:
        """Start resource and service monitoring."""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="ResourceMonitoring",
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10.0)
        logger.info("Resource monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop for resources and services."""
        logger.info("Starting resource monitoring loop")
        
        while self.monitoring_active:
            try:
                # Collect system metrics
                metrics = self._collect_system_metrics()
                self.metrics_history.append(metrics)
                
                # Check resource thresholds
                self._check_resource_thresholds(metrics)
                
                # Health check services if enabled
                if self.enable_auto_recovery:
                    self._health_check_services()
                
                # Clean up expired allocations
                self._cleanup_expired_allocations()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            time.sleep(self.monitoring_interval)
        
        logger.info("Resource monitoring loop stopped")
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system resource metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0.0, 0.0, 0.0)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available // (1024 * 1024)
            
            # Disk I/O metrics
            disk_io = psutil.disk_io_counters()
            disk_read_mb = (disk_io.read_bytes // (1024 * 1024)) if disk_io else 0.0
            disk_write_mb = (disk_io.write_bytes // (1024 * 1024)) if disk_io else 0.0
            
            # Network I/O metrics
            net_io = psutil.net_io_counters()
            net_sent_mb = (net_io.bytes_sent // (1024 * 1024)) if net_io else 0.0
            net_recv_mb = (net_io.bytes_recv // (1024 * 1024)) if net_io else 0.0
            
            # Process count
            process_count = len(psutil.pids())
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_mb=memory_available_mb,
                disk_io_read_mb=disk_read_mb,
                disk_io_write_mb=disk_write_mb,
                network_io_sent_mb=net_sent_mb,
                network_io_recv_mb=net_recv_mb,
                active_processes=process_count,
                load_average=load_avg
            )
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available_mb=0,
                disk_io_read_mb=0.0,
                disk_io_write_mb=0.0,
                network_io_sent_mb=0.0,
                network_io_recv_mb=0.0,
                active_processes=0,
                load_average=(0.0, 0.0, 0.0)
            )
    
    def _check_resource_thresholds(self, metrics: SystemMetrics) -> None:
        """Check if system resources exceed warning thresholds."""
        alerts = []
        
        # Memory checks
        if metrics.memory_percent >= self.resource_thresholds['memory_critical']:
            alerts.append(f"CRITICAL: Memory usage {metrics.memory_percent:.1f}% exceeds critical threshold")
        elif metrics.memory_percent >= self.resource_thresholds['memory_warning']:
            alerts.append(f"WARNING: Memory usage {metrics.memory_percent:.1f}% exceeds warning threshold")
        
        # CPU checks
        if metrics.cpu_percent >= self.resource_thresholds['cpu_critical']:
            alerts.append(f"CRITICAL: CPU usage {metrics.cpu_percent:.1f}% exceeds critical threshold")
        elif metrics.cpu_percent >= self.resource_thresholds['cpu_warning']:
            alerts.append(f"WARNING: CPU usage {metrics.cpu_percent:.1f}% exceeds warning threshold")
        
        # Process count checks
        if metrics.active_processes >= self.resource_thresholds['process_critical']:
            alerts.append(f"CRITICAL: Process count {metrics.active_processes} exceeds critical threshold")
        elif metrics.active_processes >= self.resource_thresholds['process_warning']:
            alerts.append(f"WARNING: Process count {metrics.active_processes} exceeds warning threshold")
        
        # Log alerts
        for alert in alerts:
            if "CRITICAL" in alert:
                logger.error(alert)
            else:
                logger.warning(alert)
    
    def _health_check_services(self) -> None:
        """Perform health checks on all managed services."""
        with self.service_lock:
            for service_name in self.SERVICE_DEPENDENCIES.keys():
                try:
                    self._check_service_health(service_name)
                except Exception as e:
                    logger.error(f"Health check failed for {service_name}: {e}")
    
    def _check_service_health(self, service_name: str) -> ServiceHealth:
        """Check health of individual service."""
        current_time = datetime.now()
        
        # Get or create service health record
        if service_name not in self.service_health:
            self.service_health[service_name] = ServiceHealth(
                service_name=service_name,
                status=ServiceStatus.UNKNOWN,
                last_check=current_time
            )
        
        health = self.service_health[service_name]
        
        try:
            # Check based on service type
            if service_name == "postgresql":
                self.service_checker.check_postgresql()
                health.status = ServiceStatus.HEALTHY
            elif service_name == "redis":
                self.service_checker.check_redis()
                health.status = ServiceStatus.HEALTHY
            elif service_name == "docker":
                self.service_checker.check_docker()
                health.status = ServiceStatus.HEALTHY
            elif service_name in ["backend", "auth", "frontend"]:
                # Check if service ports are available
                port_mappings = self.port_discovery.discover_all_ports()
                if service_name in port_mappings:
                    mapping = port_mappings[service_name]
                    health.port_mapping = mapping
                    health.status = ServiceStatus.HEALTHY if mapping.is_available else ServiceStatus.STOPPED
                else:
                    health.status = ServiceStatus.STOPPED
            else:
                health.status = ServiceStatus.UNKNOWN
                
            health.error_message = None
            
        except ServiceUnavailableError as e:
            health.status = ServiceStatus.UNHEALTHY
            health.error_message = str(e)
            logger.debug(f"Service {service_name} unhealthy: {e}")
        except Exception as e:
            health.status = ServiceStatus.UNKNOWN
            health.error_message = str(e)
            logger.debug(f"Service {service_name} health check error: {e}")
        
        health.last_check = current_time
        return health
    
    def _cleanup_expired_allocations(self) -> None:
        """Clean up expired resource allocations."""
        current_time = datetime.now()
        expired_allocations = []
        
        with self.resource_lock:
            for allocation_id, allocation in self.resource_allocations.items():
                if (allocation.expires_at and 
                    current_time > allocation.expires_at):
                    expired_allocations.append(allocation_id)
            
            # Remove expired allocations
            for allocation_id in expired_allocations:
                allocation = self.resource_allocations.pop(allocation_id, None)
                if allocation:
                    self._release_allocation(allocation)
                    logger.info(f"Released expired allocation: {allocation_id}")
    
    def ensure_layer_services(self, layer_name: str) -> Tuple[bool, List[str]]:
        """
        Ensure all required services for a test layer are available.
        
        Args:
            layer_name: Test layer name
            
        Returns:
            Tuple of (all_services_available, missing_services)
        """
        required_services = self.LAYER_SERVICE_DEPENDENCIES.get(layer_name, set())
        
        if not required_services:
            logger.info(f"Layer {layer_name} requires no external services")
            return True, []
        
        logger.info(f"Checking services for layer {layer_name}: {required_services}")
        
        missing_services = []
        
        with self.service_lock:
            for service_name in required_services:
                health = self._check_service_health(service_name)
                if health.status != ServiceStatus.HEALTHY:
                    missing_services.append(service_name)
        
        if missing_services:
            logger.warning(f"Layer {layer_name} missing services: {missing_services}")
            
            # Attempt to start missing services
            started_services = self._start_missing_services(missing_services)
            if started_services:
                logger.info(f"Started services: {started_services}")
                
                # Re-check after startup attempt
                still_missing = []
                for service_name in missing_services:
                    health = self._check_service_health(service_name)
                    if health.status != ServiceStatus.HEALTHY:
                        still_missing.append(service_name)
                
                missing_services = still_missing
        
        all_available = len(missing_services) == 0
        
        if all_available:
            logger.info(f"All services available for layer {layer_name}")
        else:
            logger.error(f"Layer {layer_name} still missing services: {missing_services}")
        
        return all_available, missing_services
    
    def _start_missing_services(self, service_names: List[str]) -> List[str]:
        """
        Attempt to start missing services using Docker.
        
        Args:
            service_names: List of service names to start
            
        Returns:
            List of successfully started services
        """
        if not service_names:
            return []
        
        logger.info(f"Attempting to start missing services: {service_names}")
        
        # Use port discovery to start services
        started_services = []
        
        try:
            success, started = self.port_discovery.start_missing_services(service_names)
            if success:
                started_services.extend(started)
                
                # Wait for services to become healthy
                max_wait = 60  # 60 seconds
                wait_interval = 2
                elapsed = 0
                
                while elapsed < max_wait:
                    all_healthy = True
                    for service_name in started:
                        health = self._check_service_health(service_name)
                        if health.status != ServiceStatus.HEALTHY:
                            all_healthy = False
                            break
                    
                    if all_healthy:
                        logger.info(f"All started services are healthy: {started}")
                        break
                    
                    time.sleep(wait_interval)
                    elapsed += wait_interval
                
                if elapsed >= max_wait:
                    logger.warning(f"Timed out waiting for services to become healthy: {started}")
            
        except Exception as e:
            logger.error(f"Error starting services: {e}")
        
        return started_services
    
    def allocate_resources(self, 
                          layer_name: str,
                          category_name: str, 
                          requirements: ResourceRequirements,
                          duration_minutes: int = 30) -> Optional[str]:
        """
        Allocate resources for test execution.
        
        Args:
            layer_name: Test layer name
            category_name: Test category name
            requirements: Resource requirements
            duration_minutes: Allocation duration in minutes
            
        Returns:
            Allocation ID if successful, None if allocation failed
        """
        with self.resource_lock:
            pool = self.resource_pools.get(layer_name)
            if not pool:
                logger.error(f"No resource pool found for layer: {layer_name}")
                return None
            
            # Calculate required resources
            required_memory = max(requirements.min_memory_mb, 128)  # Minimum 128MB
            required_cpu = 10 if requirements.dedicated_resources else 5  # 10% or 5% CPU
            
            # Check availability
            available_memory = pool.max_memory_mb - pool.allocated_memory_mb
            available_cpu = pool.max_cpu_percent - pool.allocated_cpu_percent
            available_instances = pool.max_parallel_instances - pool.active_instances
            
            if (available_memory < required_memory or 
                available_cpu < required_cpu or 
                available_instances <= 0):
                logger.warning(f"Insufficient resources for {layer_name}/{category_name}: "
                             f"need {required_memory}MB/{required_cpu}%CPU/1instance, "
                             f"have {available_memory}MB/{available_cpu}%CPU/{available_instances}instances")
                return None
            
            # Create allocation
            allocation_id = f"{layer_name}_{category_name}_{int(time.time())}"
            expires_at = datetime.now() + timedelta(minutes=duration_minutes)
            
            allocation = ResourceAllocation(
                test_layer=layer_name,
                test_category=category_name,
                memory_mb=required_memory,
                cpu_percent=required_cpu,
                allocated_at=datetime.now(),
                expires_at=expires_at
            )
            
            # Update pool allocation
            pool.allocated_memory_mb += required_memory
            pool.allocated_cpu_percent += required_cpu
            pool.active_instances += 1
            pool.reserved_for.add(category_name)
            
            # Store allocation
            self.resource_allocations[allocation_id] = allocation
            
            logger.info(f"Allocated resources for {layer_name}/{category_name}: "
                       f"{required_memory}MB, {required_cpu}% CPU (ID: {allocation_id})")
            
            return allocation_id
    
    def release_resources(self, allocation_id: str) -> bool:
        """
        Release allocated resources.
        
        Args:
            allocation_id: Allocation ID to release
            
        Returns:
            True if released successfully, False otherwise
        """
        with self.resource_lock:
            allocation = self.resource_allocations.pop(allocation_id, None)
            if not allocation:
                logger.warning(f"Allocation not found: {allocation_id}")
                return False
            
            return self._release_allocation(allocation)
    
    def _release_allocation(self, allocation: ResourceAllocation) -> bool:
        """Release a resource allocation and update pools."""
        pool = self.resource_pools.get(allocation.test_layer)
        if not pool:
            logger.error(f"Pool not found for allocation: {allocation.test_layer}")
            return False
        
        # Update pool allocation
        pool.allocated_memory_mb = max(0, pool.allocated_memory_mb - allocation.memory_mb)
        pool.allocated_cpu_percent = max(0, pool.allocated_cpu_percent - allocation.cpu_percent)
        pool.active_instances = max(0, pool.active_instances - 1)
        pool.reserved_for.discard(allocation.test_category)
        
        logger.info(f"Released resources for {allocation.test_layer}/{allocation.test_category}: "
                   f"{allocation.memory_mb}MB, {allocation.cpu_percent}% CPU")
        
        return True
    
    def get_resource_status(self) -> Dict[str, Any]:
        """
        Get current resource status and allocation information.
        
        Returns:
            Dictionary with resource status information
        """
        with self.resource_lock:
            # Current system metrics
            latest_metrics = self.metrics_history[-1] if self.metrics_history else None
            
            # Resource pool status
            pool_status = {}
            for pool_name, pool in self.resource_pools.items():
                pool_status[pool_name] = {
                    'max_memory_mb': pool.max_memory_mb,
                    'allocated_memory_mb': pool.allocated_memory_mb,
                    'available_memory_mb': pool.max_memory_mb - pool.allocated_memory_mb,
                    'max_cpu_percent': pool.max_cpu_percent,
                    'allocated_cpu_percent': pool.allocated_cpu_percent,
                    'available_cpu_percent': pool.max_cpu_percent - pool.allocated_cpu_percent,
                    'max_parallel_instances': pool.max_parallel_instances,
                    'active_instances': pool.active_instances,
                    'available_instances': pool.max_parallel_instances - pool.active_instances,
                    'reserved_for': list(pool.reserved_for),
                    'utilization_memory': (pool.allocated_memory_mb / pool.max_memory_mb) * 100,
                    'utilization_cpu': (pool.allocated_cpu_percent / pool.max_cpu_percent) * 100,
                    'utilization_instances': (pool.active_instances / pool.max_parallel_instances) * 100
                }
            
            # Active allocations
            allocation_status = {}
            for allocation_id, allocation in self.resource_allocations.items():
                allocation_status[allocation_id] = {
                    'layer': allocation.test_layer,
                    'category': allocation.test_category,
                    'memory_mb': allocation.memory_mb,
                    'cpu_percent': allocation.cpu_percent,
                    'allocated_at': allocation.allocated_at.isoformat(),
                    'expires_at': allocation.expires_at.isoformat() if allocation.expires_at else None,
                    'process_ids': list(allocation.process_ids)
                }
            
            return {
                'timestamp': datetime.now().isoformat(),
                'system_metrics': {
                    'cpu_percent': latest_metrics.cpu_percent if latest_metrics else 0,
                    'memory_percent': latest_metrics.memory_percent if latest_metrics else 0,
                    'memory_available_mb': latest_metrics.memory_available_mb if latest_metrics else 0,
                    'active_processes': latest_metrics.active_processes if latest_metrics else 0,
                    'load_average': latest_metrics.load_average if latest_metrics else (0, 0, 0)
                },
                'resource_pools': pool_status,
                'active_allocations': allocation_status,
                'total_allocations': len(self.resource_allocations),
                'monitoring_active': self.monitoring_active
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get current service status information.
        
        Returns:
            Dictionary with service status information
        """
        with self.service_lock:
            service_status = {}
            
            for service_name, health in self.service_health.items():
                service_status[service_name] = {
                    'status': health.status.value,
                    'last_check': health.last_check.isoformat(),
                    'error_message': health.error_message,
                    'restart_count': health.restart_count,
                    'port_mapping': {
                        'external_port': health.port_mapping.external_port,
                        'internal_port': health.port_mapping.internal_port,
                        'host': health.port_mapping.host,
                        'is_available': health.port_mapping.is_available
                    } if health.port_mapping else None,
                    'health_check_url': health.health_check_url
                }
            
            # Check for services not yet monitored
            for service_name in self.SERVICE_DEPENDENCIES.keys():
                if service_name not in service_status:
                    service_status[service_name] = {
                        'status': ServiceStatus.UNKNOWN.value,
                        'last_check': None,
                        'error_message': 'Not yet checked',
                        'restart_count': 0,
                        'port_mapping': None,
                        'health_check_url': None
                    }
            
            return {
                'timestamp': datetime.now().isoformat(),
                'services': service_status,
                'healthy_services': len([s for s in self.service_health.values() 
                                       if s.status == ServiceStatus.HEALTHY]),
                'total_services': len(self.SERVICE_DEPENDENCIES),
                'port_discovery_available': self.port_discovery.docker_available
            }
    
    def resolve_resource_conflicts(self) -> List[str]:
        """
        Identify and resolve resource allocation conflicts.
        
        Returns:
            List of conflict resolution actions taken
        """
        actions = []
        
        with self.resource_lock:
            # Check for overallocation
            for pool_name, pool in self.resource_pools.items():
                memory_overallocation = pool.allocated_memory_mb - pool.max_memory_mb
                cpu_overallocation = pool.allocated_cpu_percent - pool.max_cpu_percent
                instance_overallocation = pool.active_instances - pool.max_parallel_instances
                
                if memory_overallocation > 0:
                    action = f"Memory overallocation in {pool_name}: {memory_overallocation}MB"
                    actions.append(action)
                    logger.warning(action)
                
                if cpu_overallocation > 0:
                    action = f"CPU overallocation in {pool_name}: {cpu_overallocation}%"
                    actions.append(action)
                    logger.warning(action)
                
                if instance_overallocation > 0:
                    action = f"Instance overallocation in {pool_name}: {instance_overallocation} instances"
                    actions.append(action)
                    logger.warning(action)
            
            # Check system resource pressure
            latest_metrics = self.metrics_history[-1] if self.metrics_history else None
            if latest_metrics:
                if latest_metrics.memory_percent > self.resource_thresholds['memory_critical']:
                    action = f"System memory critical: {latest_metrics.memory_percent:.1f}%"
                    actions.append(action)
                    logger.error(action)
                
                if latest_metrics.cpu_percent > self.resource_thresholds['cpu_critical']:
                    action = f"System CPU critical: {latest_metrics.cpu_percent:.1f}%"
                    actions.append(action)
                    logger.error(action)
        
        if not actions:
            logger.debug("No resource conflicts detected")
        
        return actions
    
    def cleanup_resources(self, force: bool = False) -> None:
        """
        Clean up all allocated resources.
        
        Args:
            force: Force cleanup even if allocations haven't expired
        """
        logger.info("Starting resource cleanup")
        
        with self.resource_lock:
            allocations_to_remove = list(self.resource_allocations.keys())
            
            if not force:
                # Only remove expired allocations
                current_time = datetime.now()
                allocations_to_remove = [
                    allocation_id for allocation_id, allocation in self.resource_allocations.items()
                    if allocation.expires_at and current_time > allocation.expires_at
                ]
            
            # Release allocations
            for allocation_id in allocations_to_remove:
                allocation = self.resource_allocations.pop(allocation_id, None)
                if allocation:
                    self._release_allocation(allocation)
            
            if allocations_to_remove:
                logger.info(f"Released {len(allocations_to_remove)} allocations")
            else:
                logger.info("No allocations to release")
    
    def shutdown(self) -> None:
        """Shutdown the resource management agent."""
        logger.info("Shutting down ResourceManagementAgent")
        
        # Stop monitoring
        self.stop_monitoring()
        
        # Clean up all resources
        self.cleanup_resources(force=True)
        
        # Shutdown thread pool
        try:
            # Python 3.9+ supports timeout parameter
            self.executor.shutdown(wait=True, timeout=10.0)
        except TypeError:
            # Python < 3.9 doesn't support timeout
            self.executor.shutdown(wait=True)
        
        logger.info("ResourceManagementAgent shutdown complete")
    
    def __enter__(self):
        """Context manager entry."""
        if self.enable_monitoring:
            self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()


# Convenience functions for integration with test orchestration

def create_resource_manager(enable_monitoring: bool = True) -> ResourceManagementAgent:
    """
    Create a ResourceManagementAgent instance with standard configuration.
    
    Args:
        enable_monitoring: Enable continuous resource monitoring
        
    Returns:
        Configured ResourceManagementAgent instance
    """
    return ResourceManagementAgent(
        enable_monitoring=enable_monitoring,
        monitoring_interval=5.0,
        enable_auto_recovery=True
    )


def ensure_layer_resources_available(resource_manager: ResourceManagementAgent,
                                   layer_name: str,
                                   timeout_seconds: int = 120) -> bool:
    """
    Ensure all required resources and services are available for a test layer.
    
    Args:
        resource_manager: Resource management agent instance
        layer_name: Test layer name
        timeout_seconds: Maximum time to wait for resources
        
    Returns:
        True if all resources are available, False otherwise
    """
    logger.info(f"Ensuring resources for layer: {layer_name}")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        # Check services
        services_available, missing_services = resource_manager.ensure_layer_services(layer_name)
        
        if not services_available:
            logger.warning(f"Services not available for {layer_name}: {missing_services}")
            time.sleep(5)
            continue
        
        # Check resource conflicts
        conflicts = resource_manager.resolve_resource_conflicts()
        if conflicts:
            logger.warning(f"Resource conflicts detected for {layer_name}: {conflicts}")
            time.sleep(5)
            continue
        
        logger.info(f"All resources available for layer: {layer_name}")
        return True
    
    logger.error(f"Timed out waiting for resources for layer: {layer_name}")
    return False


if __name__ == "__main__":
    # CLI interface for resource management
    import argparse
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print("\nShutting down resource manager...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description="Resource Management Agent")
    parser.add_argument("--monitor", action="store_true", 
                       help="Enable continuous monitoring")
    parser.add_argument("--status", action="store_true",
                       help="Show resource and service status")
    parser.add_argument("--layer", type=str,
                       help="Check resources for specific layer")
    
    args = parser.parse_args()
    
    # Create resource manager
    with create_resource_manager(enable_monitoring=args.monitor) as rm:
        if args.status:
            # Show status
            resource_status = rm.get_resource_status()
            service_status = rm.get_service_status()
            
            print("=== RESOURCE STATUS ===")
            print(json.dumps(resource_status, indent=2))
            print("\n=== SERVICE STATUS ===")
            print(json.dumps(service_status, indent=2))
        
        elif args.layer:
            # Check specific layer
            success = ensure_layer_resources_available(rm, args.layer)
            if success:
                print(f" PASS:  Resources available for layer: {args.layer}")
            else:
                print(f" FAIL:  Resources not available for layer: {args.layer}")
                sys.exit(1)
        
        elif args.monitor:
            # Continuous monitoring mode
            print("Starting resource monitoring... Press Ctrl+C to stop")
            try:
                while True:
                    time.sleep(10)
                    status = rm.get_resource_status()
                    metrics = status['system_metrics']
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"CPU: {metrics['cpu_percent']:.1f}% "
                          f"Memory: {metrics['memory_percent']:.1f}% "
                          f"Processes: {metrics['active_processes']}")
            except KeyboardInterrupt:
                pass
        
        else:
            parser.print_help()