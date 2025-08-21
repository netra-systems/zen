"""Service Discovery Service for service mesh"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, UTC


class ServiceDiscoveryService:
    """Advanced service discovery with health monitoring and graceful degradation"""
    
    def __init__(self, graceful_mode: bool = True, default_healthy: bool = True):
        self.services: Dict[str, Dict[str, Any]] = {}
        self.health_status: Dict[str, bool] = {}
        self.discovery_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.cache_ttl = 30  # seconds
        self.graceful_mode = graceful_mode  # Pragmatic rigor: default to graceful
        self.default_healthy = default_healthy  # Default to resilience
        self.fallback_services: Dict[str, List[Dict[str, Any]]] = {}  # Fallback registry
    
    async def register_service(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Register a service with discovery (graceful configuration handling)"""
        try:
            # Graceful handling of missing or malformed config
            service_config = {
                "id": service_id,
                "name": self._safe_get(config, "name", service_id),
                "endpoint": self._safe_get(config, "endpoint", "localhost"),
                "port": self._safe_get_int(config, "port", 8080),
                "version": self._safe_get(config, "version", "1.0.0"),
                "metadata": self._safe_get(config, "metadata", {}),
                "registered_at": datetime.now(UTC).isoformat(),
                "last_seen": datetime.now(UTC).isoformat(),
                "optional": self._safe_get_bool(config, "optional", True)  # Services are optional by default
            }
            
            self.services[service_id] = service_config
            self.health_status[service_id] = self.default_healthy
            self._invalidate_cache()
            return True
        except Exception as e:
            if not self.graceful_mode:
                raise
            # In graceful mode, log warning but don't fail registration
            print(f"Warning: Service registration had issues but proceeding: {e}")
            return False
    
    async def unregister_service(self, service_id: str) -> bool:
        """Unregister a service"""
        if service_id in self.services:
            del self.services[service_id]
            if service_id in self.health_status:
                del self.health_status[service_id]
            self._invalidate_cache()
            return True
        return False
    
    async def discover_services(self, service_name: str, include_unhealthy: bool = False) -> List[Dict[str, Any]]:
        """Discover available instances of a service (graceful degradation)"""
        # Check cache first
        cache_key = f"discover_{service_name}_{include_unhealthy}"
        if cache_key in self.discovery_cache:
            return self.discovery_cache[cache_key]
        
        # Find matching services with flexible criteria
        matching_services = []
        for service_id, service_config in self.services.items():
            service_matches = self._service_name_matches(service_config.get("name", ""), service_name)
            is_healthy = self.health_status.get(service_id, self.default_healthy)
            
            if service_matches and (is_healthy or include_unhealthy):
                matching_services.append(service_config)
        
        # If no healthy services found, try fallbacks in graceful mode
        if not matching_services and self.graceful_mode:
            matching_services = self._get_fallback_services(service_name)
        
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
        """Update health status of a service (graceful handling of unknown services)"""
        if service_id not in self.services:
            if self.graceful_mode:
                # In graceful mode, auto-register unknown services with basic config
                await self.register_service(service_id, {
                    "name": service_id,
                    "endpoint": "unknown",
                    "optional": True
                })
            else:
                return False
        
        self.health_status[service_id] = is_healthy
        if service_id in self.services:
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
    
    async def get_services_by_version(self, service_name: str, version: str, 
                                    allow_compatible: bool = True) -> List[Dict[str, Any]]:
        """Get services by name and version (flexible version matching)"""
        matching_services = []
        for service_id, service_config in self.services.items():
            name_matches = self._service_name_matches(service_config.get("name", ""), service_name)
            version_matches = self._version_matches(service_config.get("version", ""), version, allow_compatible)
            is_healthy = self.health_status.get(service_id, self.default_healthy)
            
            if name_matches and version_matches and is_healthy:
                matching_services.append(service_config)
        return matching_services
    
    def _version_matches(self, service_version: str, target_version: str, allow_compatible: bool) -> bool:
        """Check if service version matches target (flexible version matching)."""
        if not service_version or not target_version:
            return True  # If version is unknown, assume compatible
        
        # Exact match
        if service_version == target_version:
            return True
        
        if not allow_compatible:
            return False
        
        # Compatible version matching (simplified semver logic)
        try:
            service_parts = [int(x) for x in service_version.split('.')][:3]
            target_parts = [int(x) for x in target_version.split('.')][:3]
            
            # Pad with zeros if needed
            while len(service_parts) < 3:
                service_parts.append(0)
            while len(target_parts) < 3:
                target_parts.append(0)
            
            # Major version must match, minor can be >= target
            return (service_parts[0] == target_parts[0] and 
                   service_parts[1] >= target_parts[1])
        except (ValueError, IndexError):
            # If version parsing fails, assume compatible in graceful mode
            return self.graceful_mode
    
    def _invalidate_cache(self) -> None:
        """Clear discovery cache"""
        self.discovery_cache.clear()
    
    async def _cleanup_cache_entry(self, cache_key: str) -> None:
        """Clean up specific cache entry after TTL"""
        await asyncio.sleep(self.cache_ttl)
        if cache_key in self.discovery_cache:
            del self.discovery_cache[cache_key]
    
    def _safe_get(self, config: Dict[str, Any], key: str, default: str) -> str:
        """Safely get string value from config."""
        try:
            value = config.get(key, default)
            return str(value) if value is not None else default
        except:
            return default
    
    def _safe_get_int(self, config: Dict[str, Any], key: str, default: int) -> int:
        """Safely get int value from config."""
        try:
            value = config.get(key, default)
            return int(value) if value is not None else default
        except:
            return default
    
    def _safe_get_bool(self, config: Dict[str, Any], key: str, default: bool) -> bool:
        """Safely get bool value from config."""
        try:
            value = config.get(key, default)
            if isinstance(value, bool):
                return value
            return str(value).lower() in ('true', '1', 'yes', 'on') if value is not None else default
        except:
            return default
    
    def _service_name_matches(self, service_name: str, target_name: str) -> bool:
        """Check if service name matches target (flexible matching)."""
        if not service_name or not target_name:
            return False
        # Exact match
        if service_name == target_name:
            return True
        # Case-insensitive match
        if service_name.lower() == target_name.lower():
            return True
        # Partial match for flexibility
        if self.graceful_mode:
            return target_name.lower() in service_name.lower() or service_name.lower() in target_name.lower()
        return False
    
    def _get_fallback_services(self, service_name: str) -> List[Dict[str, Any]]:
        """Get fallback services when primary discovery fails."""
        return self.fallback_services.get(service_name, [])
    
    async def register_fallback_service(self, service_name: str, fallback_config: Dict[str, Any]) -> None:
        """Register a fallback service for when primary services are unavailable."""
        if service_name not in self.fallback_services:
            self.fallback_services[service_name] = []
        self.fallback_services[service_name].append({
            **fallback_config,
            "fallback": True,
            "registered_at": datetime.now(UTC).isoformat()
        })
    
    async def is_service_critical(self, service_id: str) -> bool:
        """Check if a service is critical (non-optional)."""
        if service_id not in self.services:
            return False
        return not self.services[service_id].get("optional", True)
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get discovery service statistics"""
        healthy_count = sum(1 for health in self.health_status.values() if health)
        service_names = set(service["name"] for service in self.services.values())
        optional_count = sum(1 for service in self.services.values() 
                           if service.get("optional", True))
        
        return {
            "total_services": len(self.services),
            "healthy_services": healthy_count,
            "unhealthy_services": len(self.services) - healthy_count,
            "optional_services": optional_count,
            "critical_services": len(self.services) - optional_count,
            "unique_service_names": len(service_names),
            "cache_entries": len(self.discovery_cache),
            "graceful_mode": self.graceful_mode,
            "fallback_services": len(self.fallback_services)
        }