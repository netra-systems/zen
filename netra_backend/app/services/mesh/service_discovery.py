"""Service Discovery implementation"""

import asyncio
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set


class ServiceDiscovery:
    """Service discovery for finding and managing services"""
    
    def __init__(self):
        self.registry: Dict[str, Dict[str, Any]] = {}
        self.tags: Dict[str, Set[str]] = {}
        self.watchers: Dict[str, List] = {}
    
    async def register(self, service_id: str, service_name: str, address: str, port: int, tags: Optional[List[str]] = None) -> bool:
        """Register a service instance"""
        service_info = {
            "id": service_id,
            "name": service_name,
            "address": address,
            "port": port,
            "tags": tags or [],
            "registered_at": datetime.now(UTC).isoformat(),
            "last_heartbeat": datetime.now(UTC).isoformat(),
            "status": "active"
        }
        
        self.registry[service_id] = service_info
        
        # Update tag index
        for tag in tags or []:
            if tag not in self.tags:
                self.tags[tag] = set()
            self.tags[tag].add(service_id)
        
        await self._notify_watchers(service_name, "registered", service_info)
        return True
    
    async def deregister(self, service_id: str) -> bool:
        """Deregister a service instance"""
        if service_id not in self.registry:
            return False
        
        service_info = self.registry[service_id]
        service_name = service_info["name"]
        
        # Remove from tag index
        for tag in service_info.get("tags", []):
            if tag in self.tags:
                self.tags[tag].discard(service_id)
                if not self.tags[tag]:
                    del self.tags[tag]
        
        del self.registry[service_id]
        await self._notify_watchers(service_name, "deregistered", service_info)
        return True
    
    async def find_service(self, service_name: str) -> List[Dict[str, Any]]:
        """Find all instances of a service"""
        instances = []
        for service_info in self.registry.values():
            if service_info["name"] == service_name and service_info["status"] == "active":
                instances.append(service_info)
        return instances
    
    async def find_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Find services by tag"""
        if tag not in self.tags:
            return []
        
        instances = []
        for service_id in self.tags[tag]:
            if service_id in self.registry:
                service_info = self.registry[service_id]
                if service_info["status"] == "active":
                    instances.append(service_info)
        return instances
    
    async def heartbeat(self, service_id: str) -> bool:
        """Update service heartbeat"""
        if service_id not in self.registry:
            return False
        
        self.registry[service_id]["last_heartbeat"] = datetime.now(UTC).isoformat()
        self.registry[service_id]["status"] = "active"
        return True
    
    async def health_check(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get health information for a service"""
        if service_id not in self.registry:
            return None
        
        service_info = self.registry[service_id]
        last_heartbeat = datetime.fromisoformat(service_info["last_heartbeat"])
        now = datetime.now(UTC)
        
        # Consider service unhealthy if no heartbeat for 30 seconds
        is_healthy = (now - last_heartbeat).total_seconds() < 30
        
        return {
            "service_id": service_id,
            "healthy": is_healthy,
            "last_heartbeat": service_info["last_heartbeat"],
            "status": service_info["status"]
        }
    
    async def list_services(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all services grouped by name"""
        services = {}
        for service_info in self.registry.values():
            service_name = service_info["name"]
            if service_name not in services:
                services[service_name] = []
            services[service_name].append(service_info)
        return services
    
    async def watch_service(self, service_name: str, callback) -> None:
        """Watch for changes to a service"""
        if service_name not in self.watchers:
            self.watchers[service_name] = []
        self.watchers[service_name].append(callback)
    
    async def _notify_watchers(self, service_name: str, event: str, service_info: Dict[str, Any]) -> None:
        """Notify watchers of service changes"""
        if service_name in self.watchers:
            for callback in self.watchers[service_name]:
                try:
                    await callback(event, service_info)
                except Exception:
                    # Ignore callback errors
                    pass
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get discovery statistics"""
        service_counts = {}
        for service_info in self.registry.values():
            service_name = service_info["name"]
            service_counts[service_name] = service_counts.get(service_name, 0) + 1
        
        return {
            "total_instances": len(self.registry),
            "unique_services": len(set(info["name"] for info in self.registry.values())),
            "service_counts": service_counts,
            "total_tags": len(self.tags)
        }