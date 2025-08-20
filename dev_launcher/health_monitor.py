"""
Health monitoring for dev launcher processes.

This module provides health checks and automatic recovery
to ensure processes stay running.
"""

import time
import threading
import logging
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service state during startup and runtime."""
    STARTING = "starting"
    GRACE_PERIOD = "grace_period"
    READY = "ready"
    MONITORING = "monitoring"
    FAILED = "failed"


@dataclass
class HealthStatus:
    """Health status for a service."""
    is_healthy: bool
    last_check: datetime
    consecutive_failures: int
    error_message: Optional[str] = None
    state: ServiceState = ServiceState.STARTING
    startup_time: Optional[datetime] = None
    grace_period_seconds: int = 30
    ready_confirmed: bool = False


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
        Initialize the health monitor.
        
        Args:
            check_interval: Seconds between health checks (default 30 per SPEC)
        """
        self.check_interval = check_interval
        self.services: Dict[str, Dict] = {}
        self.running = False
        self.monitoring_enabled = False  # New: monitoring only starts after readiness
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.health_status: Dict[str, HealthStatus] = {}
        self.startup_complete = False  # Track when all services are ready
    
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
    
    def mark_service_ready(self, name: str) -> bool:
        """Mark a service as ready after successful readiness check.
        
        Args:
            name: Service name
            
        Returns:
            True if service was marked ready
        """
        with self._lock:
            if name in self.health_status:
                status = self.health_status[name]
                status.ready_confirmed = True
                status.state = ServiceState.READY
                logger.info(f"Service {name} marked as ready")
                return True
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
        """Determine if a service should be monitored based on its state and grace period.
        
        Per SPEC HEALTH-002: Health checks begin AFTER grace period AND readiness confirmation.
        """
        if not status.ready_confirmed:
            return False
        
        if status.startup_time is None:
            return True  # Fallback - monitor if no startup time
        
        # Check if grace period has elapsed
        elapsed = (datetime.now() - status.startup_time).total_seconds()
        grace_period_elapsed = elapsed >= status.grace_period_seconds
        
        return grace_period_elapsed and status.state in [ServiceState.READY, ServiceState.MONITORING]
    
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
        """Get health status for all services."""
        with self._lock:
            return dict(self.health_status)
    
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
        """Check if all services are healthy.
        
        During startup, considers services healthy until monitoring begins.
        """
        with self._lock:
            for status in self.health_status.values():
                # During startup/grace period, consider healthy
                if status.state in [ServiceState.STARTING, ServiceState.GRACE_PERIOD]:
                    continue
                # Once monitoring, check actual health
                if not status.is_healthy:
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