"""
Health monitoring for dev launcher processes.

This module provides health checks and automatic recovery with enhanced grace period
implementation per SPEC/dev_launcher.xml requirements:

CRITICAL REQUIREMENTS:
- HEALTH-001: Health monitoring MUST NOT start immediately after service launch
- HEALTH-002: Grace period implementation (Backend: 30s, Frontend: 90s) 
- HEALTH-003: Health checks begin AFTER grace period AND readiness confirmation

Windows Enhancements:
- Process verification using tasklist
- Port monitoring integration
- Enhanced error reporting with Windows-specific troubleshooting

This module ensures processes stay running while respecting startup timing requirements.
"""

import asyncio
import logging
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set

# Import coordination components for integration
try:
    from dev_launcher.readiness_checker import ReadinessManager
    from dev_launcher.service_registry import get_global_service_registry, ServiceStatus
    COORDINATION_AVAILABLE = True
except ImportError:
    COORDINATION_AVAILABLE = False

logger = logging.getLogger(__name__)

if not COORDINATION_AVAILABLE:
    logger.warning("Coordination components not available, running in legacy mode")


class ServiceState(Enum):
    """Service state during startup and runtime."""
    STARTING = "starting"
    GRACE_PERIOD = "grace_period"
    READY = "ready"
    MONITORING = "monitoring"
    FAILED = "failed"


@dataclass
class HealthStatus:
    """Health status for a service with enhanced grace period tracking."""
    is_healthy: bool
    last_check: datetime
    consecutive_failures: int
    error_message: Optional[str] = None
    state: ServiceState = ServiceState.STARTING
    startup_time: Optional[datetime] = None
    grace_period_seconds: int = 30
    ready_confirmed: bool = False
    
    # Enhanced tracking
    readiness_check_attempts: int = 0
    last_successful_check: Optional[datetime] = None
    grace_period_end: Optional[datetime] = None
    process_verified: bool = False
    ports_verified: Set[int] = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.ports_verified is None:
            self.ports_verified = set()
        
        # Calculate grace period end time
        if self.startup_time and self.grace_period_end is None:
            self.grace_period_end = self.startup_time + timedelta(seconds=self.grace_period_seconds)
    
    def update_cross_service_status(self, cors_enabled: bool = False, service_discovery_active: bool = False) -> None:
        """Update cross-service integration status."""
        if not hasattr(self, 'cross_service_status'):
            self.cross_service_status = {}
        
        self.cross_service_status.update({
            'cors_enabled': cors_enabled,
            'service_discovery_active': service_discovery_active,
            'last_updated': datetime.now().isoformat()
        })
    
    def is_grace_period_over(self) -> bool:
        """Check if grace period has ended."""
        if not self.grace_period_end:
            return True  # No grace period set
        return datetime.now() >= self.grace_period_end
    
    def time_remaining_in_grace_period(self) -> float:
        """Get remaining time in grace period (in seconds)."""
        if not self.grace_period_end:
            return 0.0
        
        remaining = (self.grace_period_end - datetime.now()).total_seconds()
        return max(0.0, remaining)
    
    def should_start_monitoring(self) -> bool:
        """Determine if health monitoring should start based on SPEC requirements."""
        # Per SPEC HEALTH-001: Must wait for readiness confirmation
        if not self.ready_confirmed:
            return False
        
        # Per SPEC HEALTH-002: Must wait for grace period to end
        if not self.is_grace_period_over():
            return False
        
        return True


class HealthMonitor:
    """
    Monitors the health of running processes.
    
    This class performs periodic health checks and can trigger
    recovery actions when processes fail.
    
    CRITICAL: Health monitoring MUST NOT start immediately after service launch.
    Per SPEC HEALTH-001: Must wait for startup checks to pass before beginning
    health monitoring.
    """
    
    def __init__(self, check_interval: int = 30):
        """
        Initialize the health monitor with enhanced grace period support.
        
        Args:
            check_interval: Seconds between health checks (default 30 per SPEC HEALTH-003)
        """
        self.check_interval = check_interval
        self.services: Dict[str, Dict] = {}
        self.running = False
        self.monitoring_enabled = False  # Monitoring only starts after readiness per SPEC HEALTH-001
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.health_status: Dict[str, HealthStatus] = {}
        self.startup_complete = False  # Track when all services are ready
        self.database_connector = None  # Will be set by launcher
        self.is_windows = sys.platform == "win32"
        self.port_manager = None  # Will be set by launcher for port verification
        
        logger.info(f"HealthMonitor initialized (check_interval: {check_interval}s)")
        if self.is_windows:
            logger.info("Windows process verification enabled")
    
    def register_service(
        self,
        name: str,
        health_check: Callable[[], bool],
        recovery_action: Optional[Callable[[], None]] = None,
        max_failures: int = 5,  # Increased to 5 per SPEC HEALTH-003
        grace_period_seconds: int = 30  # New: grace period support
    ):
        """
        Register a service for health monitoring.
        
        Args:
            name: Service name
            health_check: Function that returns True if healthy
            recovery_action: Function to call for recovery
            max_failures: Consecutive failures before recovery (default 5 per SPEC)
            grace_period_seconds: Grace period before health monitoring starts
        """
        # Set service-specific grace periods per SPEC HEALTH-002
        if name.lower() == "frontend":
            grace_period_seconds = 90  # Frontend: 90 second grace period
        elif name.lower() == "backend":
            grace_period_seconds = 30  # Backend: 30 second grace period
        
        with self._lock:
            self.services[name] = {
                'health_check': health_check,
                'recovery_action': recovery_action,
                'max_failures': max_failures
            }
            self.health_status[name] = HealthStatus(
                is_healthy=True,
                last_check=datetime.now(),
                consecutive_failures=0,
                state=ServiceState.STARTING,
                startup_time=datetime.now(),
                grace_period_seconds=grace_period_seconds,
                ready_confirmed=False
            )
            logger.info(f"Registered health monitoring for {name} (grace period: {grace_period_seconds}s)")
    
    def set_database_connector(self, database_connector):
        """Set database connector for database health monitoring."""
        self.database_connector = database_connector
        logger.info("Database connector linked to health monitor for cross-service health checks")
    
    def unregister_service(self, name: str):
        """Remove a service from monitoring."""
        with self._lock:
            if name in self.services:
                del self.services[name]
                del self.health_status[name]
                logger.info(f"Unregistered health monitoring for {name}")
    
    def start(self):
        """Start the health monitoring thread.
        
        NOTE: This starts the thread but monitoring is disabled until
        enable_monitoring() is called after startup verification.
        """
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Health monitor thread started (monitoring disabled until startup complete)")
    
    def enable_monitoring(self):
        """Enable health monitoring after startup verification is complete.
        
        Per SPEC HEALTH-001: Only AFTER startup verification should health monitoring begin.
        """
        with self._lock:
            self.monitoring_enabled = True
            self.startup_complete = True
            logger.info("Health monitoring enabled - all services confirmed ready")
    
    def mark_service_ready(self, name: str, process_pid: Optional[int] = None, 
                          ports: Optional[Set[int]] = None) -> bool:
        """
        Mark a service as ready after successful readiness check.
        
        Args:
            name: Service name
            process_pid: Process ID for verification
            ports: Set of ports used by the service
            
        Returns:
            True if service was marked ready
        """
        with self._lock:
            if name in self.health_status:
                status = self.health_status[name]
                status.ready_confirmed = True
                status.state = ServiceState.READY
                status.readiness_check_attempts += 1
                status.last_successful_check = datetime.now()
                
                # Store port information for monitoring
                if ports:
                    status.ports_verified = ports
                
                # Log detailed readiness info
                grace_remaining = status.time_remaining_in_grace_period()
                logger.info(f"Service {name} marked as ready")
                logger.info(f"   ->  Grace period remaining: {grace_remaining:.1f}s")
                if ports:
                    logger.info(f"   ->  Verified ports: {sorted(ports)}")
                if process_pid:
                    logger.info(f"   ->  Process PID: {process_pid}")
                    
                # Verify process on Windows
                if self.is_windows and process_pid:
                    status.process_verified = self._verify_windows_process(process_pid, name)
                
                return True
            return False
    
    def _verify_windows_process(self, pid: int, service_name: str) -> bool:
        """Verify that a Windows process is running using tasklist."""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Has header + data
                    process_info = lines[1].split(',')
                    if len(process_info) >= 2:
                        process_name = process_info[0].strip('"')
                        logger.debug(f"Verified {service_name} process: {process_name} (PID: {pid})")
                        return True
                        
            logger.warning(f"Could not verify {service_name} process (PID: {pid})")
            return False
            
        except Exception as e:
            logger.debug(f"Process verification failed for {service_name}: {e}")
            return False
    
    def stop(self):
        """Stop the health monitoring thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Health monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop.
        
        Per SPEC HEALTH-001: Health checks MUST NOT start immediately.
        Only checks services after grace period and readiness confirmation.
        """
        while self.running:
            try:
                # Only monitor if explicitly enabled and startup is complete
                if self.monitoring_enabled and self.startup_complete:
                    self._check_all_services()
                else:
                    # During startup, just update service states
                    self._update_startup_states()
                
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                time.sleep(self.check_interval)
    
    def _update_startup_states(self):
        """Update service states during startup without performing health checks."""
        with self._lock:
            current_time = datetime.now()
            
            for name, status in self.health_status.items():
                if status.state == ServiceState.STARTING and status.startup_time:
                    elapsed = (current_time - status.startup_time).total_seconds()
                    
                    # Move to grace period after startup
                    if elapsed > 5:  # Give 5 seconds for basic startup
                        status.state = ServiceState.GRACE_PERIOD
                        logger.debug(f"Service {name} entered grace period")
    
    def _check_all_services(self):
        """Check health of all registered services.
        
        Per SPEC HEALTH-003: Only check health AFTER service is confirmed ready.
        """
        with self._lock:
            services = dict(self.services)
        
        for name, config in services.items():
            status = self.health_status[name]
            
            # Skip health checks if service not ready or still in grace period
            if not self._should_monitor_service(name, status):
                continue
                
            try:
                # Perform health check only for ready services
                is_healthy = config['health_check']()
                
                with self._lock:
                    status.last_check = datetime.now()
                    status.state = ServiceState.MONITORING
                    
                    if is_healthy:
                        if not status.is_healthy:
                            logger.info(f"Service {name} recovered")
                        status.is_healthy = True
                        status.consecutive_failures = 0
                        status.error_message = None
                    else:
                        status.is_healthy = False
                        status.consecutive_failures += 1
                        status.error_message = "Health check failed"
                        
                        logger.warning(
                            f"Service {name} unhealthy "
                            f"(failure {status.consecutive_failures}/{config['max_failures']})"
                        )
                        
                        # Trigger recovery if needed (max 5 failures per SPEC)
                        if status.consecutive_failures >= config['max_failures']:
                            self._trigger_recovery(name, config)
                            status.consecutive_failures = 0
            
            except Exception as e:
                logger.error(f"Error checking health of {name}: {e}")
                with self._lock:
                    status.is_healthy = False
                    status.consecutive_failures += 1
                    status.error_message = str(e)
    
    def _should_monitor_service(self, name: str, status: HealthStatus) -> bool:
        """
        Determine if a service should be monitored based on SPEC requirements.
        
        Per SPEC HEALTH-001: Must wait for readiness confirmation
        Per SPEC HEALTH-002: Must wait for grace period AND readiness confirmation
        Per SPEC HEALTH-003: Only check health AFTER service is confirmed ready
        """
        # Use the enhanced method from HealthStatus
        should_monitor = status.should_start_monitoring()
        
        if not should_monitor:
            # Log why we're not monitoring yet
            if not status.ready_confirmed:
                logger.debug(f"Not monitoring {name}: waiting for readiness confirmation")
            elif not status.is_grace_period_over():
                remaining = status.time_remaining_in_grace_period()
                logger.debug(f"Not monitoring {name}: grace period remaining {remaining:.1f}s")
            return False
        
        # Additional state checks
        if status.state not in [ServiceState.READY, ServiceState.MONITORING]:
            logger.debug(f"Not monitoring {name}: state is {status.state}")
            return False
        
        return True
    
    def get_grace_period_status(self) -> Dict[str, Dict[str, any]]:
        """Get detailed grace period status for all services."""
        status_info = {}
        
        with self._lock:
            for name, status in self.health_status.items():
                remaining = status.time_remaining_in_grace_period()
                grace_over = status.is_grace_period_over()
                should_monitor = status.should_start_monitoring()
                
                status_info[name] = {
                    'state': status.state.value,
                    'ready_confirmed': status.ready_confirmed,
                    'grace_period_seconds': status.grace_period_seconds,
                    'grace_period_remaining': remaining,
                    'grace_period_over': grace_over,
                    'should_monitor': should_monitor,
                    'startup_time': status.startup_time.isoformat() if status.startup_time else None,
                    'process_verified': status.process_verified,
                    'ports_verified': sorted(status.ports_verified),
                    'consecutive_failures': status.consecutive_failures,
                    'last_check': status.last_check.isoformat() if status.last_check else None
                }
        
        return status_info
    
    def _trigger_recovery(self, name: str, config: Dict):
        """
        Trigger recovery action for a service.
        
        Args:
            name: Service name
            config: Service configuration
        """
        logger.warning(f"Triggering recovery for {name}")
        
        if config['recovery_action']:
            try:
                config['recovery_action']()
                logger.info(f"Recovery action completed for {name}")
            except Exception as e:
                logger.error(f"Recovery action failed for {name}: {e}")
        else:
            logger.warning(f"No recovery action configured for {name}")
    
    def get_status(self, name: str) -> Optional[HealthStatus]:
        """
        Get health status for a service.
        
        Args:
            name: Service name
            
        Returns:
            Health status or None if not found
        """
        with self._lock:
            return self.health_status.get(name)
    
    def get_all_status(self) -> Dict[str, HealthStatus]:
        """Get health status for all services including databases."""
        with self._lock:
            status = dict(self.health_status)
            
            # Add database status if available
            if self.database_connector:
                db_status = self.database_connector.get_connection_status()
                for db_name, db_info in db_status.items():
                    # Convert database status to HealthStatus format
                    status[f"database_{db_name}"] = HealthStatus(
                        is_healthy=(db_info["status"] == "connected"),
                        last_check=datetime.fromisoformat(db_info["last_check"]) if db_info["last_check"] else datetime.now(),
                        consecutive_failures=db_info["failure_count"],
                        error_message=db_info["last_error"],
                        state=ServiceState.MONITORING if db_info["status"] == "connected" else ServiceState.FAILED
                    )
            
            return status
    
    def is_healthy(self, name: str) -> bool:
        """
        Check if a service is healthy.
        
        Args:
            name: Service name
            
        Returns:
            True if healthy or still in startup/grace period
        """
        status = self.get_status(name)
        if not status:
            return False
            
        # During startup and grace period, consider service healthy
        # Only report unhealthy once monitoring has started
        if status.state in [ServiceState.STARTING, ServiceState.GRACE_PERIOD]:
            return True
            
        return status.is_healthy
    
    def all_healthy(self) -> bool:
        """Check if all services are healthy including databases.
        
        During startup, considers services healthy until monitoring begins.
        """
        with self._lock:
            # Check service health
            for status in self.health_status.values():
                # During startup/grace period, consider healthy
                if status.state in [ServiceState.STARTING, ServiceState.GRACE_PERIOD]:
                    continue
                # Once monitoring, check actual health
                if not status.is_healthy:
                    return False
            
            # Check database health if available
            if self.database_connector:
                if not self.database_connector.is_all_healthy():
                    return False
            
            return True
    
    def all_services_ready(self) -> bool:
        """Check if all services have completed startup and are ready.
        
        Returns:
            True if all services are past grace period and confirmed ready
        """
        with self._lock:
            if not self.health_status:
                return False
                
            for status in self.health_status.values():
                if not status.ready_confirmed:
                    return False
                if status.startup_time:
                    elapsed = (datetime.now() - status.startup_time).total_seconds()
                    if elapsed < status.grace_period_seconds:
                        return False
            return True

    def add_cors_metrics_monitoring(self, cors_middleware_getter: Callable = None) -> None:
        """Add CORS metrics monitoring to health checks."""
        if cors_middleware_getter:
            self._cors_middleware_getter = cors_middleware_getter
            logger.info("CORS metrics monitoring enabled")
    
    def get_cross_service_health_status(self) -> Dict[str, Any]:
        """Get comprehensive cross-service health status."""
        status_report = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'cross_service_integration': {
                'cors_enabled': False,
                'service_discovery_active': False,
                'auth_tokens_valid': False
            }
        }
        
        with self._lock:
            # Service health status
            for name, status in self.health_status.items():
                service_info = {
                    'healthy': status.is_healthy,
                    'state': status.state.value,
                    'ready_confirmed': status.ready_confirmed,
                    'consecutive_failures': status.consecutive_failures,
                    'last_check': status.last_check.isoformat() if status.last_check else None,
                    'startup_time': status.startup_time.isoformat() if status.startup_time else None,
                    'grace_period_remaining': status.time_remaining_in_grace_period()
                }
                
                # Add cross-service status if available
                if hasattr(status, 'cross_service_status'):
                    service_info['cross_service'] = status.cross_service_status
                
                status_report['services'][name] = service_info
            
            # Overall cross-service integration status
            if hasattr(self, '_cors_middleware_getter') and self._cors_middleware_getter:
                try:
                    cors_middleware = self._cors_middleware_getter()
                    if cors_middleware and hasattr(cors_middleware, 'get_cors_metrics'):
                        cors_metrics = cors_middleware.get_cors_metrics()
                        if cors_metrics:
                            status_report['cross_service_integration']['cors_enabled'] = True
                            status_report['cross_service_integration']['cors_metrics'] = cors_metrics
                except Exception as e:
                    logger.debug(f"Could not get CORS metrics: {e}")
            
            # Check service discovery status
            if hasattr(self, '_service_discovery'):
                try:
                    origins = self._service_discovery.get_all_service_origins()
                    status_report['cross_service_integration']['service_discovery_active'] = len(origins) > 0
                    status_report['cross_service_integration']['registered_service_origins'] = origins
                except Exception as e:
                    logger.debug(f"Could not get service discovery status: {e}")
        
        return status_report
    
    def set_service_discovery(self, service_discovery) -> None:
        """Set service discovery instance for health monitoring integration."""
        self._service_discovery = service_discovery
        logger.debug("Service discovery integration enabled in health monitor")
    
    def verify_cross_service_connectivity(self) -> bool:
        """Verify cross-service connectivity and authentication."""
        if not hasattr(self, '_service_discovery'):
            return True  # Skip if no service discovery
        
        try:
            # Check if cross-service auth token exists
            auth_token = self._service_discovery.get_cross_service_auth_token()
            if not auth_token:
                logger.warning("No cross-service auth token found")
                return False
            
            # Verify service origins are accessible
            origins = self._service_discovery.get_all_service_origins()
            accessible_count = 0
            
            for origin in origins:
                if self._check_service_origin_accessibility(origin):
                    accessible_count += 1
            
            success_rate = accessible_count / len(origins) if origins else 1.0
            logger.debug(f"Cross-service connectivity: {accessible_count}/{len(origins)} services accessible")
            
            return success_rate >= 0.7  # At least 70% of services must be accessible
        
        except Exception as e:
            logger.error(f"Cross-service connectivity check failed: {e}")
            return False
    
    def _check_service_origin_accessibility(self, origin: str) -> bool:
        """Check if a service origin is accessible."""
        try:
            import requests
            # Simple connectivity check - just check if we can reach the service
            response = requests.get(f"{origin}/health", timeout=2)
            return response.status_code in [200, 404]  # 404 is acceptable for some services
        except Exception:
            return False


def create_url_health_check(url: str, timeout: int = 5) -> Callable[[], bool]:
    """
    Create a health check function for a URL endpoint.
    
    Args:
        url: URL to check
        timeout: Request timeout in seconds
        
    Returns:
        Health check function
    """
    import requests
    
    def check():
        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code == 200
        except:
            return False
    
    return check


def create_process_health_check(process) -> Callable[[], bool]:
    """
    Create a health check function for a subprocess.
    
    Args:
        process: subprocess.Popen instance
        
    Returns:
        Health check function
    """
    def check():
        return process.poll() is None
    
    return check