"""
Health Check Validator - Service-specific health validation logic.

Provides comprehensive health checks for each service type with real
connection validation, operational testing, and integration with existing
health check systems. Maintains SSOT compliance by extending existing
health check patterns.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.shared_health_types import HealthStatus
from .models import (
    EnvironmentType,
    HealthCheckResult,
    ServiceConfiguration,
    ServiceType,
)


class HealthCheckValidator:
    """
    Comprehensive service health validation system.
    
    Provides service-specific health checks that go beyond basic connectivity
    to validate operational readiness, schema availability, and business
    functionality requirements.
    """
    
    def __init__(self, environment: EnvironmentType = EnvironmentType.DEVELOPMENT):
        """Initialize health check validator."""
        self.logger = central_logger.get_logger(__name__)
        self.environment = environment
        
        # Service configuration cache
        self._service_configs: Dict[ServiceType, ServiceConfiguration] = {}
        self._initialize_service_configs()
    
    def _initialize_service_configs(self) -> None:
        """Initialize service configurations for current environment."""
        for service_type in ServiceType:
            self._service_configs[service_type] = ServiceConfiguration.for_environment(
                service_type, self.environment
            )
    
    async def validate_service_health(
        self,
        app: Any,
        service_type: ServiceType
    ) -> HealthCheckResult:
        """
        Validate health for a specific service type.
        
        Args:
            app: FastAPI application instance
            service_type: Type of service to validate
            
        Returns:
            Comprehensive health check result
        """
        start_time = time.time()
        service_config = self._service_configs[service_type]
        
        self.logger.debug(f"Health check starting for {service_type.value}")
        
        try:
            # Dispatch to service-specific health check
            if service_type == ServiceType.DATABASE_POSTGRES:
                result = await self.validate_postgresql_health(app, service_config)
            elif service_type == ServiceType.DATABASE_REDIS:
                result = await self.validate_redis_health(app, service_config)
            elif service_type == ServiceType.AUTH_SERVICE:
                result = await self.validate_auth_service_health(app, service_config)
            elif service_type == ServiceType.BACKEND_SERVICE:
                result = await self.validate_backend_service_health(app, service_config)
            elif service_type == ServiceType.WEBSOCKET_SERVICE:
                result = await self.validate_websocket_service_health(app, service_config)
            elif service_type == ServiceType.LLM_SERVICE:
                result = await self.validate_llm_service_health(app, service_config)
            elif service_type == ServiceType.FRONTEND_SERVICE:
                result = await self.validate_frontend_service_health(app, service_config)
            elif service_type == ServiceType.ANALYTICS_SERVICE:
                result = await self.validate_analytics_service_health(app, service_config)
            else:
                # Unknown service type
                result = self._create_error_result(
                    service_type,
                    start_time,
                    f"Unknown service type: {service_type.value}"
                )
            
            # Add timing information
            result.response_time_ms = (time.time() - start_time) * 1000
            
            return result
            
        except asyncio.TimeoutError:
            return self._create_timeout_result(service_type, start_time, service_config.timeout_seconds)
        except Exception as e:
            return self._create_error_result(service_type, start_time, str(e))
    
    async def validate_postgresql_health(
        self,
        app: Any,
        config: ServiceConfiguration
    ) -> HealthCheckResult:
        """Validate PostgreSQL database health with operational checks."""
        service_type = ServiceType.DATABASE_POSTGRES
        
        try:
            # Check if database session factory exists
            if not hasattr(app.state, 'db_session_factory') or app.state.db_session_factory is None:
                return self._create_unhealthy_result(
                    service_type,
                    "Database session factory not initialized"
                )
            
            # Test database connection and basic query
            async with asyncio.timeout(config.timeout_seconds):
                async with app.state.db_session_factory() as session:
                    # Basic connectivity test
                    result = await session.execute("SELECT 1 as test_value")
                    test_value = result.scalar()
                    
                    if test_value != 1:
                        return self._create_unhealthy_result(
                            service_type,
                            f"Database query returned unexpected result: {test_value}"
                        )
                    
                    # Schema readiness check - count tables
                    table_result = await session.execute("""
                        SELECT COUNT(*) as table_count 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """)
                    table_count = table_result.scalar()
                    
                    details = {
                        "table_count": table_count,
                        "connection_pool_size": getattr(app.state.db_session_factory, 'size', 0),
                        "schema_ready": table_count > 0
                    }
                    
                    # Determine health status based on table count
                    if table_count == 0:
                        health_status = HealthStatus.DEGRADED
                        details["warning"] = "No tables found - database may not be initialized"
                    else:
                        health_status = HealthStatus.HEALTHY
            
            return HealthCheckResult(
                service_type=service_type,
                service_name="PostgreSQL Database",
                success=True,
                health_status=health_status,
                response_time_ms=0.0,  # Will be set by caller
                details=details
            )
            
        except asyncio.TimeoutError:
            return self._create_unhealthy_result(
                service_type,
                f"Database health check timed out after {config.timeout_seconds}s"
            )
        except Exception as e:
            return self._create_unhealthy_result(
                service_type,
                f"Database connection failed: {str(e)}"
            )
    
    async def validate_redis_health(
        self,
        app: Any,
        config: ServiceConfiguration
    ) -> HealthCheckResult:
        """Validate Redis health with operational checks."""
        service_type = ServiceType.DATABASE_REDIS
        
        try:
            # Check if Redis manager exists
            if not hasattr(app.state, 'redis_manager') or app.state.redis_manager is None:
                return self._create_unhealthy_result(
                    service_type,
                    "Redis manager not initialized"
                )
            
            redis_manager = app.state.redis_manager
            
            # Test Redis connection with set/get operations
            async with asyncio.timeout(config.timeout_seconds):
                test_key = f"health_check_{int(time.time())}"
                test_value = "health_check_value"
                
                # Test SET operation
                await redis_manager.set(test_key, test_value, expire_seconds=60)
                
                # Test GET operation
                retrieved_value = await redis_manager.get(test_key)
                
                if retrieved_value != test_value:
                    return self._create_unhealthy_result(
                        service_type,
                        f"Redis SET/GET test failed - expected '{test_value}', got '{retrieved_value}'"
                    )
                
                # Clean up test key
                await redis_manager.delete(test_key)
                
                # Get Redis info for additional details
                details = {
                    "set_get_test": "passed",
                    "cleanup_test": "passed"
                }
                
                # Try to get Redis info if available
                if hasattr(redis_manager, 'get_info'):
                    try:
                        redis_info = await redis_manager.get_info()
                        details.update({
                            "memory_usage": redis_info.get("used_memory_human", "unknown"),
                            "connected_clients": redis_info.get("connected_clients", "unknown"),
                            "redis_version": redis_info.get("redis_version", "unknown")
                        })
                    except Exception:
                        details["info_available"] = False
            
            return HealthCheckResult(
                service_type=service_type,
                service_name="Redis Cache",
                success=True,
                health_status=HealthStatus.HEALTHY,
                response_time_ms=0.0,  # Will be set by caller
                details=details
            )
            
        except asyncio.TimeoutError:
            return self._create_unhealthy_result(
                service_type,
                f"Redis health check timed out after {config.timeout_seconds}s"
            )
        except Exception as e:
            return self._create_unhealthy_result(
                service_type,
                f"Redis connection failed: {str(e)}"
            )
    
    async def validate_auth_service_health(
        self,
        app: Any,
        config: ServiceConfiguration
    ) -> HealthCheckResult:
        """Validate Auth Service health with JWT and user operations."""
        service_type = ServiceType.AUTH_SERVICE
        
        try:
            # Check if auth components exist
            auth_components = []
            
            if hasattr(app.state, 'key_manager') and app.state.key_manager:
                auth_components.append("key_manager")
            if hasattr(app.state, 'security_service') and app.state.security_service:
                auth_components.append("security_service")
            
            if not auth_components:
                return self._create_unhealthy_result(
                    service_type,
                    "No auth service components found (key_manager, security_service)"
                )
            
            # Test JWT validation capabilities if key manager exists
            async with asyncio.timeout(config.timeout_seconds):
                details = {
                    "components_found": auth_components,
                    "jwt_test": "not_performed",
                    "user_creation_ready": False
                }
                
                # Test JWT token validation if key manager is available
                if hasattr(app.state, 'key_manager') and app.state.key_manager:
                    try:
                        key_manager = app.state.key_manager
                        # Check if key manager has required methods
                        has_jwt_methods = (
                            hasattr(key_manager, 'create_access_token') and
                            hasattr(key_manager, 'verify_token')
                        )
                        
                        if has_jwt_methods:
                            details["jwt_test"] = "methods_available"
                        else:
                            details["jwt_test"] = "methods_missing"
                            
                    except Exception as jwt_e:
                        details["jwt_test"] = f"error: {str(jwt_e)}"
                
                # Check if user service is ready for user creation
                if hasattr(app.state, 'user_service') and app.state.user_service:
                    details["user_creation_ready"] = True
                
                # Determine health status
                if "key_manager" in auth_components and details["jwt_test"] in ["methods_available"]:
                    health_status = HealthStatus.HEALTHY
                elif auth_components:
                    health_status = HealthStatus.DEGRADED
                else:
                    health_status = HealthStatus.UNHEALTHY
            
            return HealthCheckResult(
                service_type=service_type,
                service_name="Auth Service",
                success=health_status != HealthStatus.UNHEALTHY,
                health_status=health_status,
                response_time_ms=0.0,  # Will be set by caller
                details=details
            )
            
        except asyncio.TimeoutError:
            return self._create_unhealthy_result(
                service_type,
                f"Auth service health check timed out after {config.timeout_seconds}s"
            )
        except Exception as e:
            return self._create_unhealthy_result(
                service_type,
                f"Auth service validation failed: {str(e)}"
            )
    
    async def validate_backend_service_health(
        self,
        app: Any,
        config: ServiceConfiguration
    ) -> HealthCheckResult:
        """Validate Backend Service health with agent execution readiness."""
        service_type = ServiceType.BACKEND_SERVICE
        
        try:
            # Check core backend components
            async with asyncio.timeout(config.timeout_seconds):
                details = {
                    "agent_supervisor": False,
                    "execution_engine": False,
                    "tool_system": False,
                    "llm_manager": False,
                    "thread_service": False
                }
                
                # Check agent supervisor
                if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
                    details["agent_supervisor"] = True
                
                # Check execution engine (can be in supervisor or separate)
                if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
                    supervisor = app.state.agent_supervisor
                    if hasattr(supervisor, 'engine') or hasattr(supervisor, 'execution_engine'):
                        details["execution_engine"] = True
                
                # Check tool system readiness
                if (hasattr(app.state, 'tool_classes') and app.state.tool_classes) or \
                   (hasattr(app.state, 'tool_dispatcher') and app.state.tool_dispatcher):
                    details["tool_system"] = True
                
                # Check LLM manager
                if hasattr(app.state, 'llm_manager') and app.state.llm_manager:
                    details["llm_manager"] = True
                
                # Check thread service
                if hasattr(app.state, 'thread_service') and app.state.thread_service:
                    details["thread_service"] = True
                
                # Calculate readiness score
                components_ready = sum(1 for ready in details.values() if ready)
                total_components = len(details)
                readiness_score = components_ready / total_components
                
                details["readiness_score"] = readiness_score
                details["components_ready"] = components_ready
                details["total_components"] = total_components
                
                # Determine health status
                if readiness_score >= 0.8:  # 4/5 components ready
                    health_status = HealthStatus.HEALTHY
                elif readiness_score >= 0.6:  # 3/5 components ready
                    health_status = HealthStatus.DEGRADED
                else:
                    health_status = HealthStatus.UNHEALTHY
            
            return HealthCheckResult(
                service_type=service_type,
                service_name="Backend Service",
                success=health_status != HealthStatus.UNHEALTHY,
                health_status=health_status,
                response_time_ms=0.0,  # Will be set by caller
                details=details
            )
            
        except asyncio.TimeoutError:
            return self._create_unhealthy_result(
                service_type,
                f"Backend service health check timed out after {config.timeout_seconds}s"
            )
        except Exception as e:
            return self._create_unhealthy_result(
                service_type,
                f"Backend service validation failed: {str(e)}"
            )
    
    async def validate_websocket_service_health(
        self,
        app: Any,
        config: ServiceConfiguration
    ) -> HealthCheckResult:
        """Validate WebSocket Service health with real-time communication readiness."""
        service_type = ServiceType.WEBSOCKET_SERVICE
        
        try:
            # Check WebSocket components
            async with asyncio.timeout(config.timeout_seconds):
                details = {
                    "websocket_manager": False,
                    "websocket_bridge": False,
                    "message_router": False,
                    "agent_events_ready": False
                }
                
                # Check WebSocket manager
                if hasattr(app.state, 'websocket_manager') and app.state.websocket_manager:
                    details["websocket_manager"] = True
                elif hasattr(app.state, 'websocket_bridge_factory'):
                    details["websocket_manager"] = "factory_pattern"
                
                # Check agent WebSocket bridge
                if hasattr(app.state, 'agent_websocket_bridge') and app.state.agent_websocket_bridge:
                    details["websocket_bridge"] = True
                
                # Check message router
                try:
                    from netra_backend.app.websocket_core import get_message_router
                    message_router = get_message_router()
                    if message_router:
                        details["message_router"] = True
                except ImportError:
                    details["message_router"] = "import_error"
                
                # Check if agent events can be sent (critical for chat)
                if details["websocket_bridge"] and details["message_router"]:
                    details["agent_events_ready"] = True
                
                # Calculate readiness
                ready_components = sum(1 for v in details.values() if v is True)
                total_components = len(details)
                
                # Special scoring for factory pattern
                if details["websocket_manager"] == "factory_pattern":
                    ready_components += 0.5  # Factory pattern is partial readiness
                
                readiness_score = ready_components / total_components
                details["readiness_score"] = readiness_score
                
                # Determine health status - WebSocket events are critical for chat
                if details["agent_events_ready"]:
                    health_status = HealthStatus.HEALTHY
                elif readiness_score >= 0.6:
                    health_status = HealthStatus.DEGRADED
                else:
                    health_status = HealthStatus.UNHEALTHY
            
            return HealthCheckResult(
                service_type=service_type,
                service_name="WebSocket Service",
                success=health_status != HealthStatus.UNHEALTHY,
                health_status=health_status,
                response_time_ms=0.0,  # Will be set by caller
                details=details
            )
            
        except asyncio.TimeoutError:
            return self._create_unhealthy_result(
                service_type,
                f"WebSocket service health check timed out after {config.timeout_seconds}s"
            )
        except Exception as e:
            return self._create_unhealthy_result(
                service_type,
                f"WebSocket service validation failed: {str(e)}"
            )
    
    async def validate_llm_service_health(
        self,
        app: Any,
        config: ServiceConfiguration
    ) -> HealthCheckResult:
        """Validate LLM Service health."""
        service_type = ServiceType.LLM_SERVICE
        
        try:
            # Check LLM manager
            async with asyncio.timeout(config.timeout_seconds):
                if not hasattr(app.state, 'llm_manager') or app.state.llm_manager is None:
                    return self._create_unhealthy_result(
                        service_type,
                        "LLM manager not initialized"
                    )
                
                details = {
                    "llm_manager_ready": True,
                    "provider_count": 0
                }
                
                # Try to get LLM provider information if available
                llm_manager = app.state.llm_manager
                if hasattr(llm_manager, 'get_available_providers'):
                    try:
                        providers = await llm_manager.get_available_providers()
                        details["provider_count"] = len(providers) if providers else 0
                        details["providers"] = providers
                    except Exception:
                        details["provider_info_available"] = False
            
            return HealthCheckResult(
                service_type=service_type,
                service_name="LLM Service",
                success=True,
                health_status=HealthStatus.HEALTHY,
                response_time_ms=0.0,  # Will be set by caller
                details=details
            )
            
        except asyncio.TimeoutError:
            return self._create_unhealthy_result(
                service_type,
                f"LLM service health check timed out after {config.timeout_seconds}s"
            )
        except Exception as e:
            return self._create_unhealthy_result(
                service_type,
                f"LLM service validation failed: {str(e)}"
            )
    
    async def validate_frontend_service_health(
        self,
        app: Any,
        config: ServiceConfiguration
    ) -> HealthCheckResult:
        """Validate Frontend Service health (placeholder implementation)."""
        service_type = ServiceType.FRONTEND_SERVICE
        
        # Frontend service validation is typically done via HTTP endpoints
        # For now, return healthy if we reach this point
        return HealthCheckResult(
            service_type=service_type,
            service_name="Frontend Service",
            success=True,
            health_status=HealthStatus.HEALTHY,
            response_time_ms=0.0,  # Will be set by caller
            details={"status": "assumed_healthy"}
        )
    
    async def validate_analytics_service_health(
        self,
        app: Any,
        config: ServiceConfiguration
    ) -> HealthCheckResult:
        """Validate Analytics Service health (placeholder implementation)."""
        service_type = ServiceType.ANALYTICS_SERVICE
        
        # Analytics service is optional for core functionality
        return HealthCheckResult(
            service_type=service_type,
            service_name="Analytics Service",
            success=True,
            health_status=HealthStatus.HEALTHY,
            response_time_ms=0.0,  # Will be set by caller
            details={"status": "optional_service"}
        )
    
    def _create_unhealthy_result(
        self,
        service_type: ServiceType,
        error_message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> HealthCheckResult:
        """Create an unhealthy health check result."""
        return HealthCheckResult(
            service_type=service_type,
            service_name=service_type.value,
            success=False,
            health_status=HealthStatus.UNHEALTHY,
            response_time_ms=0.0,  # Will be set by caller
            error_message=error_message,
            details=details or {}
        )
    
    def _create_timeout_result(
        self,
        service_type: ServiceType,
        start_time: float,
        timeout_seconds: float
    ) -> HealthCheckResult:
        """Create a timeout health check result."""
        response_time_ms = (time.time() - start_time) * 1000
        return HealthCheckResult(
            service_type=service_type,
            service_name=service_type.value,
            success=False,
            health_status=HealthStatus.UNHEALTHY,
            response_time_ms=response_time_ms,
            error_message=f"Health check timed out after {timeout_seconds}s",
            details={"timeout_seconds": timeout_seconds}
        )
    
    def _create_error_result(
        self,
        service_type: ServiceType,
        start_time: float,
        error_message: str
    ) -> HealthCheckResult:
        """Create an error health check result."""
        response_time_ms = (time.time() - start_time) * 1000
        return HealthCheckResult(
            service_type=service_type,
            service_name=service_type.value,
            success=False,
            health_status=HealthStatus.UNHEALTHY,
            response_time_ms=response_time_ms,
            error_message=error_message,
            details={"error_type": "validation_exception"}
        )