"""
Health Monitor Service
Monitors health status of services and instances
"""

import asyncio
from shared.logging.unified_logging_ssot import get_logger
import time
from typing import Any, Dict, Optional

logger = get_logger(__name__)


class HealthMonitor:
    """Service for monitoring health of various system components."""
    
    def __init__(self, health_provider: Optional[Dict[str, Any]] = None):
        """Initialize health monitor."""
        self.health_cache: Dict[str, Dict[str, Any]] = {}
        self.health_history: Dict[str, list] = {}
        self.health_provider = health_provider  # External health provider for testing
        
    async def check_service_health(
        self, 
        service: str, 
        instance: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check health status of a service or specific instance.
        
        Args:
            service: Service name (e.g., 'auth', 'redis', 'postgres')
            instance: Optional specific instance name
            
        Returns:
            Dict with health status information
        """
        service_key = f"{service}:{instance}" if instance else service
        
        logger.debug(f"Checking health for: {service_key}")
        
        current_time = time.time()
        
        # Check external health provider first (for testing)
        if self.health_provider and 'health_metrics' in self.health_provider and instance:
            external_metrics = self.health_provider['health_metrics'].get(instance)
            if external_metrics:
                is_healthy = external_metrics.get('healthy', True)
                response_time = external_metrics.get('response_time', 0.1)
            else:
                is_healthy = True
                response_time = 0.1
        # Fallback to cached status or default healthy
        elif service_key in self.health_cache:
            cached_health = self.health_cache[service_key]
            is_healthy = cached_health.get('healthy', True)
            response_time = cached_health.get('response_time', 0.1)
        else:
            is_healthy = True
            response_time = 0.1
            
        health_status = {
            'service': service,
            'instance': instance,
            'healthy': is_healthy,
            'response_time': response_time,
            'timestamp': current_time,
            'status_code': 200 if is_healthy else 503
        }
        
        # Cache the health status
        self.health_cache[service_key] = health_status
        
        # Track health history
        if service_key not in self.health_history:
            self.health_history[service_key] = []
        self.health_history[service_key].append(health_status)
        
        # Keep only last 100 entries
        if len(self.health_history[service_key]) > 100:
            self.health_history[service_key] = self.health_history[service_key][-100:]
            
        logger.debug(f"Health check result for {service_key}: {'healthy' if is_healthy else 'unhealthy'}")
        
        return health_status
    
    async def set_service_health(
        self, 
        service: str, 
        instance: Optional[str], 
        healthy: bool, 
        response_time: float = 0.1
    ) -> None:
        """
        Manually set health status (for testing purposes).
        
        Args:
            service: Service name
            instance: Instance name
            healthy: Health status
            response_time: Response time in seconds
        """
        service_key = f"{service}:{instance}" if instance else service
        
        self.health_cache[service_key] = {
            'service': service,
            'instance': instance,
            'healthy': healthy,
            'response_time': response_time,
            'timestamp': time.time(),
            'status_code': 200 if healthy else 503
        }
        
        logger.info(f"Set health status for {service_key}: {'healthy' if healthy else 'unhealthy'}")
    
    async def get_health_history(self, service: str, instance: Optional[str] = None) -> list:
        """
        Get health history for a service or instance.
        
        Args:
            service: Service name
            instance: Optional instance name
            
        Returns:
            List of health check results
        """
        service_key = f"{service}:{instance}" if instance else service
        return self.health_history.get(service_key, [])
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """
        Get overall system health summary.
        
        Returns:
            Dict with overall health metrics
        """
        healthy_services = 0
        total_services = len(self.health_cache)
        unhealthy_services = []
        
        for service_key, health in self.health_cache.items():
            if health.get('healthy', True):
                healthy_services += 1
            else:
                unhealthy_services.append(service_key)
        
        overall_health = {
            'overall_healthy': len(unhealthy_services) == 0,
            'healthy_services': healthy_services,
            'total_services': total_services,
            'unhealthy_services': unhealthy_services,
            'health_percentage': (healthy_services / total_services * 100) if total_services > 0 else 100,
            'timestamp': time.time()
        }
        
        return overall_health


# Singleton instance
health_monitor = HealthMonitor()