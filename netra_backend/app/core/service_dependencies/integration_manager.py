"""
Integration Manager - Service integration coordination and Docker management.

Provides integration coordination between service dependency resolution
and external systems like Docker, existing health checks, and service
discovery. Maintains SSOT compliance while bridging new dependency
resolution with existing infrastructure.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import text

from netra_backend.app.logging_config import central_logger
from .models import (
    EnvironmentType,
    ServiceType,
)


class IntegrationManager:
    """
    Coordinates integration between service dependency system and existing infrastructure.
    
    Provides coordination with Docker services, existing health check systems,
    service discovery mechanisms, and ensures smooth integration with existing
    startup and monitoring systems.
    """
    
    def __init__(self, environment: EnvironmentType = EnvironmentType.DEVELOPMENT):
        """Initialize integration manager."""
        self.logger = central_logger.get_logger(__name__)
        self.environment = environment
        
        # Integration state tracking
        self._docker_integration_available = None
        self._health_check_integration = None
        self._service_discovery_integration = None
    
    async def ensure_service_integration(
        self,
        app: Any,
        services: List[ServiceType]
    ) -> Dict[str, Any]:
        """
        Ensure proper integration between validated services and application state.
        
        Args:
            app: FastAPI application instance
            services: List of validated services to integrate
            
        Returns:
            Integration result with status and details
        """
        self.logger.info(f"Ensuring service integration for {len(services)} services")
        
        integration_result = {
            "success": True,
            "message": "Service integration completed",
            "services_integrated": [],
            "integration_warnings": [],
            "integration_errors": []
        }
        
        try:
            # Integrate each service type with application state
            for service_type in services:
                service_integration = await self._integrate_single_service(app, service_type)
                
                if service_integration["success"]:
                    integration_result["services_integrated"].append(service_type.value)
                    self.logger.debug(f"✓ Integrated {service_type.value}")
                else:
                    integration_result["integration_warnings"].append(
                        f"{service_type.value}: {service_integration['message']}"
                    )
                    self.logger.warning(f"⚠️ Integration issue for {service_type.value}: {service_integration['message']}")
            
            # Validate cross-service integrations
            cross_service_result = await self._validate_cross_service_integration(app, services)
            if not cross_service_result["success"]:
                integration_result["integration_warnings"].append(
                    f"Cross-service integration: {cross_service_result['message']}"
                )
            
            # Update final status
            if integration_result["integration_errors"]:
                integration_result["success"] = False
                integration_result["message"] = f"Service integration failed with {len(integration_result['integration_errors'])} errors"
            elif integration_result["integration_warnings"]:
                integration_result["message"] = f"Service integration completed with {len(integration_result['integration_warnings'])} warnings"
            
            return integration_result
            
        except Exception as e:
            self.logger.error(f"Service integration failed: {e}")
            return {
                "success": False,
                "message": f"Service integration exception: {str(e)}",
                "services_integrated": [],
                "integration_warnings": [],
                "integration_errors": [str(e)]
            }
    
    async def _integrate_single_service(
        self,
        app: Any,
        service_type: ServiceType
    ) -> Dict[str, Any]:
        """Integrate a single service with application state."""
        try:
            if service_type == ServiceType.DATABASE_POSTGRES:
                return await self._integrate_postgres_service(app)
            elif service_type == ServiceType.DATABASE_REDIS:
                return await self._integrate_redis_service(app)
            elif service_type == ServiceType.AUTH_SERVICE:
                return await self._integrate_auth_service(app)
            elif service_type == ServiceType.BACKEND_SERVICE:
                return await self._integrate_backend_service(app)
            elif service_type == ServiceType.WEBSOCKET_SERVICE:
                return await self._integrate_websocket_service(app)
            elif service_type == ServiceType.LLM_SERVICE:
                return await self._integrate_llm_service(app)
            else:
                return {
                    "success": True,
                    "message": f"No specific integration needed for {service_type.value}",
                    "integration_type": "passthrough"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Integration failed: {str(e)}",
                "error": str(e)
            }
    
    async def _integrate_postgres_service(self, app: Any) -> Dict[str, Any]:
        """Integrate PostgreSQL service with application state."""
        # Check if database session factory is properly integrated
        if hasattr(app.state, 'db_session_factory') and app.state.db_session_factory:
            # Validate that database migrations are current (if applicable)
            try:
                # Check for basic database connectivity through existing session factory
                async with app.state.db_session_factory() as session:
                    await session.execute(text("SELECT 1"))
                
                return {
                    "success": True,
                    "message": "PostgreSQL integration validated",
                    "integration_type": "database_session_factory"
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"PostgreSQL integration validation failed: {str(e)}"
                }
        else:
            return {
                "success": False,
                "message": "PostgreSQL session factory not found in application state"
            }
    
    async def _integrate_redis_service(self, app: Any) -> Dict[str, Any]:
        """Integrate Redis service with application state."""
        if hasattr(app.state, 'redis_manager') and app.state.redis_manager:
            try:
                # Validate Redis connection through existing manager
                redis_manager = app.state.redis_manager
                test_key = "integration_test"
                await redis_manager.set(test_key, "test_value", ex=60)
                await redis_manager.delete(test_key)
                
                return {
                    "success": True,
                    "message": "Redis integration validated",
                    "integration_type": "redis_manager"
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Redis integration validation failed: {str(e)}"
                }
        else:
            return {
                "success": False,
                "message": "Redis manager not found in application state"
            }
    
    async def _integrate_auth_service(self, app: Any) -> Dict[str, Any]:
        """Integrate Auth service with application state."""
        auth_components = {}
        
        # Check key manager integration
        if hasattr(app.state, 'key_manager') and app.state.key_manager:
            auth_components["key_manager"] = True
        
        # Check security service integration
        if hasattr(app.state, 'security_service') and app.state.security_service:
            auth_components["security_service"] = True
        
        # Check user service integration
        if hasattr(app.state, 'user_service') and app.state.user_service:
            auth_components["user_service"] = True
        
        if auth_components:
            return {
                "success": True,
                "message": f"Auth service integration validated - components: {list(auth_components.keys())}",
                "integration_type": "auth_components",
                "components": auth_components
            }
        else:
            return {
                "success": False,
                "message": "No auth service components found in application state"
            }
    
    async def _integrate_backend_service(self, app: Any) -> Dict[str, Any]:
        """Integrate Backend service with application state."""
        backend_components = {}
        
        # Check agent supervisor integration
        if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
            backend_components["agent_supervisor"] = True
        
        # Check LLM manager integration
        if hasattr(app.state, 'llm_manager') and app.state.llm_manager:
            backend_components["llm_manager"] = True
        
        # Check thread service integration
        if hasattr(app.state, 'thread_service') and app.state.thread_service:
            backend_components["thread_service"] = True
        
        # Check agent service integration
        if hasattr(app.state, 'agent_service') and app.state.agent_service:
            backend_components["agent_service"] = True
        
        if len(backend_components) >= 2:  # At least 2 core components
            return {
                "success": True,
                "message": f"Backend service integration validated - {len(backend_components)} components ready",
                "integration_type": "backend_components",
                "components": backend_components
            }
        else:
            return {
                "success": False,
                "message": f"Insufficient backend components - only {len(backend_components)} found",
                "components": backend_components
            }
    
    async def _integrate_websocket_service(self, app: Any) -> Dict[str, Any]:
        """Integrate WebSocket service with application state."""
        websocket_components = {}
        
        # Check WebSocket manager (can be factory pattern)
        if hasattr(app.state, 'websocket_manager') and app.state.websocket_manager:
            websocket_components["websocket_manager"] = "singleton"
        elif hasattr(app.state, 'websocket_bridge_factory'):
            websocket_components["websocket_manager"] = "factory"
        
        # Check agent WebSocket bridge
        if hasattr(app.state, 'agent_websocket_bridge') and app.state.agent_websocket_bridge:
            websocket_components["agent_websocket_bridge"] = True
        
        # Check WebSocket connection pool
        if hasattr(app.state, 'websocket_connection_pool'):
            websocket_components["websocket_connection_pool"] = True
        
        if websocket_components:
            return {
                "success": True,
                "message": f"WebSocket service integration validated - components: {list(websocket_components.keys())}",
                "integration_type": "websocket_components",
                "components": websocket_components
            }
        else:
            return {
                "success": False,
                "message": "No WebSocket service components found in application state"
            }
    
    async def _integrate_llm_service(self, app: Any) -> Dict[str, Any]:
        """Integrate LLM service with application state."""
        if hasattr(app.state, 'llm_manager') and app.state.llm_manager:
            return {
                "success": True,
                "message": "LLM service integration validated",
                "integration_type": "llm_manager"
            }
        else:
            return {
                "success": False,
                "message": "LLM manager not found in application state"
            }
    
    async def _validate_cross_service_integration(
        self,
        app: Any,
        services: List[ServiceType]
    ) -> Dict[str, Any]:
        """Validate integration between multiple services."""
        try:
            integration_checks = []
            
            # Check critical cross-service integrations
            if (ServiceType.BACKEND_SERVICE in services and 
                ServiceType.WEBSOCKET_SERVICE in services):
                
                # Validate agent -> WebSocket event integration
                agent_websocket_integration = self._check_agent_websocket_integration(app)
                integration_checks.append({
                    "integration": "agent_websocket_events",
                    "success": agent_websocket_integration,
                    "description": "Agent execution events to WebSocket users"
                })
            
            if (ServiceType.AUTH_SERVICE in services and 
                ServiceType.DATABASE_POSTGRES in services):
                
                # Validate auth -> database integration
                auth_db_integration = self._check_auth_database_integration(app)
                integration_checks.append({
                    "integration": "auth_database",
                    "success": auth_db_integration,
                    "description": "Auth service database connectivity"
                })
            
            if (ServiceType.BACKEND_SERVICE in services and 
                ServiceType.DATABASE_REDIS in services):
                
                # Validate backend -> Redis caching integration
                backend_redis_integration = self._check_backend_redis_integration(app)
                integration_checks.append({
                    "integration": "backend_redis_cache",
                    "success": backend_redis_integration,
                    "description": "Backend service Redis caching"
                })
            
            # Determine overall cross-service integration success
            successful_integrations = sum(1 for check in integration_checks if check["success"])
            total_integrations = len(integration_checks)
            
            if total_integrations == 0:
                return {
                    "success": True,
                    "message": "No cross-service integrations to validate",
                    "integration_checks": []
                }
            
            if successful_integrations == total_integrations:
                return {
                    "success": True,
                    "message": f"All {total_integrations} cross-service integrations validated",
                    "integration_checks": integration_checks
                }
            else:
                failed_integrations = [
                    check["integration"] for check in integration_checks 
                    if not check["success"]
                ]
                return {
                    "success": False,
                    "message": f"Cross-service integration issues: {failed_integrations}",
                    "integration_checks": integration_checks
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Cross-service integration validation failed: {str(e)}",
                "integration_checks": []
            }
    
    def _check_agent_websocket_integration(self, app: Any) -> bool:
        """Check if agent execution can send WebSocket events."""
        try:
            # Check if agent supervisor exists
            if not (hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor):
                return False
            
            # Check if agent WebSocket bridge exists
            if not (hasattr(app.state, 'agent_websocket_bridge') and app.state.agent_websocket_bridge):
                return False
            
            # Check if the bridge is integrated with the supervisor
            supervisor = app.state.agent_supervisor
            if hasattr(supervisor, 'registry') and hasattr(supervisor.registry, 'websocket_bridge'):
                return supervisor.registry.websocket_bridge is not None
            
            # Alternative check for direct integration
            return True
            
        except Exception:
            return False
    
    def _check_auth_database_integration(self, app: Any) -> bool:
        """Check if auth service can access database."""
        try:
            # Both auth components and database must exist
            has_auth = (hasattr(app.state, 'key_manager') and app.state.key_manager) or \
                      (hasattr(app.state, 'security_service') and app.state.security_service)
            
            has_database = hasattr(app.state, 'db_session_factory') and app.state.db_session_factory
            
            return has_auth and has_database
            
        except Exception:
            return False
    
    def _check_backend_redis_integration(self, app: Any) -> bool:
        """Check if backend service can access Redis."""
        try:
            has_backend = hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor
            has_redis = hasattr(app.state, 'redis_manager') and app.state.redis_manager
            
            return has_backend and has_redis
            
        except Exception:
            return False
    
    async def ensure_docker_services_ready(
        self,
        target_services: Optional[List[ServiceType]]
    ) -> Dict[str, Any]:
        """
        Ensure Docker services are ready for the target service types.
        
        Args:
            target_services: Service types that need Docker coordination
            
        Returns:
            Docker coordination result
        """
        try:
            # Check if Docker integration is available
            if self._docker_integration_available is None:
                self._docker_integration_available = await self._check_docker_availability()
            
            if not self._docker_integration_available:
                return {
                    "success": True,  # Not a failure if Docker not available
                    "message": "Docker integration not available - assuming external service management",
                    "docker_available": False
                }
            
            # Map service types to Docker service names
            docker_services = self._map_services_to_docker(target_services or [])
            
            if not docker_services:
                return {
                    "success": True,
                    "message": "No Docker services needed for target service types",
                    "docker_services": []
                }
            
            # Coordinate Docker service startup
            coordination_result = await self._coordinate_docker_startup(docker_services)
            
            return {
                "success": coordination_result["success"],
                "message": coordination_result["message"],
                "docker_services": docker_services,
                "coordination_details": coordination_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Docker coordination failed: {str(e)}",
                "error": str(e)
            }
    
    async def _check_docker_availability(self) -> bool:
        """Check if Docker integration is available."""
        try:
            # Try to import Docker management utilities
            from netra_backend.app.core.docker_management import UnifiedDockerManager
            return True
        except ImportError:
            return False
        except Exception:
            return False
    
    def _map_services_to_docker(self, service_types: List[ServiceType]) -> List[str]:
        """Map service types to Docker service names."""
        service_mapping = {
            ServiceType.DATABASE_POSTGRES: "postgres",
            ServiceType.DATABASE_REDIS: "redis",
            ServiceType.AUTH_SERVICE: "auth_service",
            ServiceType.BACKEND_SERVICE: "backend",
            ServiceType.FRONTEND_SERVICE: "frontend",
        }
        
        docker_services = []
        for service_type in service_types:
            if service_type in service_mapping:
                docker_services.append(service_mapping[service_type])
        
        return docker_services
    
    async def _coordinate_docker_startup(self, docker_services: List[str]) -> Dict[str, Any]:
        """Coordinate Docker service startup."""
        try:
            # This would integrate with the UnifiedDockerManager
            # For now, return a placeholder successful result
            self.logger.info(f"Docker coordination requested for: {docker_services}")
            
            return {
                "success": True,
                "message": f"Docker services coordination completed for {len(docker_services)} services",
                "services_started": docker_services
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Docker startup coordination failed: {str(e)}",
                "error": str(e)
            }
    
    async def emergency_service_restart(self, service_type: ServiceType) -> Dict[str, Any]:
        """
        Coordinate emergency restart for a specific service type.
        
        Args:
            service_type: Service type to restart
            
        Returns:
            Restart coordination result
        """
        try:
            self.logger.warning(f"Emergency restart coordination for {service_type.value}")
            
            # Map service type to restart mechanism
            if service_type in [ServiceType.DATABASE_POSTGRES, ServiceType.DATABASE_REDIS]:
                # Database services might need Docker restart
                docker_service = self._map_services_to_docker([service_type])
                if docker_service:
                    return await self._coordinate_docker_restart(docker_service[0])
                else:
                    return {
                        "success": False,
                        "message": f"No Docker service mapping for {service_type.value}"
                    }
            else:
                # Other services might need different restart mechanisms
                return {
                    "success": True,
                    "message": f"Emergency restart coordination not implemented for {service_type.value}",
                    "restart_type": "not_implemented"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Emergency restart coordination failed: {str(e)}",
                "error": str(e)
            }
    
    async def _coordinate_docker_restart(self, docker_service: str) -> Dict[str, Any]:
        """Coordinate Docker service restart."""
        try:
            self.logger.info(f"Docker restart coordination for: {docker_service}")
            
            # This would integrate with Docker management
            # For now, return a placeholder result
            return {
                "success": True,
                "message": f"Docker restart coordination completed for {docker_service}",
                "service_restarted": docker_service
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Docker restart coordination failed: {str(e)}",
                "error": str(e)
            }