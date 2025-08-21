"""Service Discovery Service for service mesh"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, UTC


class ServiceDiscoveryService:
    """Advanced service discovery with health monitoring"""
    
    def __init__(self):
        self.services: Dict[str, Dict[str, Any]] = {}
        self.health_status: Dict[str, bool] = {}
        self.discovery_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.cache_ttl = 30  # seconds
    
    async def register_service(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Register a service with discovery"""
        service_config = {
            "id": service_id,
            "name": config.get("name", service_id),
            "endpoint": config.get("endpoint", ""),
            "port": config.get("port", 8080),
            "version": config.get("version", "1.0.0"),
            "metadata": config.get("metadata", {}),
            "registered_at": datetime.now(UTC).isoformat(),
            "last_seen": datetime.now(UTC).isoformat()
        }
        
        self.services[service_id] = service_config
        self.health_status[service_id] = True
        self._invalidate_cache()
        return True
    
    async def unregister_service(self, service_id: str) -> bool:
        """Unregister a service"""
        if service_id in self.services:
            del self.services[service_id]
            if service_id in self.health_status:
                del self.health_status[service_id]
            self._invalidate_cache()
            return True
        return False
    
    async def discover_services(self, service_name: str) -> List[Dict[str, Any]]:
        """Discover available instances of a service"""
        # Check cache first
        cache_key = f"discover_{service_name}"
        if cache_key in self.discovery_cache:
            return self.discovery_cache[cache_key]
        
        # Find matching services
        matching_services = []
        for service_id, service_config in self.services.items():
            if (service_config["name"] == service_name and 
                self.health_status.get(service_id, False)):
                matching_services.append(service_config)
        
        # Cache result
        self.discovery_cache[cache_key] = matching_services
        
        # Schedule cache cleanup
        asyncio.create_task(self._cleanup_cache_entry(cache_key))
        
        return matching_services
    
    async def get_service_health(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get health status of a service"""
        if service_id not in self.services:
            return None
        
        service = self.services[service_id]
        is_healthy = self.health_status.get(service_id, False)
        
        return {
            "service_id": service_id,
            "service_name": service["name"],
            "healthy": is_healthy,
            "last_seen": service["last_seen"],
            "endpoint": service["endpoint"]
        }
    
    async def update_service_health(self, service_id: str, is_healthy: bool) -> bool:
        """Update health status of a service"""
        if service_id not in self.services:
            return False
        
        self.health_status[service_id] = is_healthy
        self.services[service_id]["last_seen"] = datetime.now(UTC).isoformat()
        self._invalidate_cache()
        return True
    
    async def list_all_services(self) -> List[Dict[str, Any]]:
        """List all registered services"""
        return [
            {
                **service,
                "healthy": self.health_status.get(service_id, False)
            }
            for service_id, service in self.services.items()
        ]
    
    async def get_services_by_version(self, service_name: str, version: str) -> List[Dict[str, Any]]:
        """Get services by name and version"""
        matching_services = []
        for service_id, service_config in self.services.items():
            if (service_config["name"] == service_name and 
                service_config["version"] == version and
                self.health_status.get(service_id, False)):
                matching_services.append(service_config)
        return matching_services
    
    def _invalidate_cache(self) -> None:
        """Clear discovery cache"""
        self.discovery_cache.clear()
    
    async def _cleanup_cache_entry(self, cache_key: str) -> None:
        """Clean up specific cache entry after TTL"""
        await asyncio.sleep(self.cache_ttl)
        if cache_key in self.discovery_cache:
            del self.discovery_cache[cache_key]
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get discovery service statistics"""
        healthy_count = sum(1 for health in self.health_status.values() if health)
        service_names = set(service["name"] for service in self.services.values())
        
        return {
            "total_services": len(self.services),
            "healthy_services": healthy_count,
            "unhealthy_services": len(self.services) - healthy_count,
            "unique_service_names": len(service_names),
            "cache_entries": len(self.discovery_cache)
        }