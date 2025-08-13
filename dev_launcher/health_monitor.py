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

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status for a service."""
    is_healthy: bool
    last_check: datetime
    consecutive_failures: int
    error_message: Optional[str] = None


class HealthMonitor:
    """
    Monitors the health of running processes.
    
    This class performs periodic health checks and can trigger
    recovery actions when processes fail.
    """
    
    def __init__(self, check_interval: int = 10):
        """
        Initialize the health monitor.
        
        Args:
            check_interval: Seconds between health checks
        """
        self.check_interval = check_interval
        self.services: Dict[str, Dict] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.health_status: Dict[str, HealthStatus] = {}
    
    def register_service(
        self,
        name: str,
        health_check: Callable[[], bool],
        recovery_action: Optional[Callable[[], None]] = None,
        max_failures: int = 3
    ):
        """
        Register a service for health monitoring.
        
        Args:
            name: Service name
            health_check: Function that returns True if healthy
            recovery_action: Function to call for recovery
            max_failures: Consecutive failures before recovery
        """
        with self._lock:
            self.services[name] = {
                'health_check': health_check,
                'recovery_action': recovery_action,
                'max_failures': max_failures
            }
            self.health_status[name] = HealthStatus(
                is_healthy=True,
                last_check=datetime.now(),
                consecutive_failures=0
            )
            logger.info(f"Registered health monitoring for {name}")
    
    def unregister_service(self, name: str):
        """Remove a service from monitoring."""
        with self._lock:
            if name in self.services:
                del self.services[name]
                del self.health_status[name]
                logger.info(f"Unregistered health monitoring for {name}")
    
    def start(self):
        """Start the health monitoring thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Health monitor started")
    
    def stop(self):
        """Stop the health monitoring thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Health monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                self._check_all_services()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                time.sleep(self.check_interval)
    
    def _check_all_services(self):
        """Check health of all registered services."""
        with self._lock:
            services = dict(self.services)
        
        for name, config in services.items():
            try:
                # Perform health check
                is_healthy = config['health_check']()
                
                with self._lock:
                    status = self.health_status[name]
                    status.last_check = datetime.now()
                    
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
                        
                        # Trigger recovery if needed
                        if status.consecutive_failures >= config['max_failures']:
                            self._trigger_recovery(name, config)
                            status.consecutive_failures = 0
            
            except Exception as e:
                logger.error(f"Error checking health of {name}: {e}")
                with self._lock:
                    status = self.health_status[name]
                    status.is_healthy = False
                    status.consecutive_failures += 1
                    status.error_message = str(e)
    
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
            True if healthy
        """
        status = self.get_status(name)
        return status.is_healthy if status else False
    
    def all_healthy(self) -> bool:
        """Check if all services are healthy."""
        with self._lock:
            return all(s.is_healthy for s in self.health_status.values())


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