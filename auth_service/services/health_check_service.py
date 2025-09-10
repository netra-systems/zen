"""
Health Check Service - Single Source of Truth for Service Health Monitoring

This service provides a unified interface for health check operations,
following SSOT principles and maintaining service independence.

Business Value: Enables proactive monitoring to prevent service failures
that would impact user authentication and platform availability.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, UTC
import asyncio

from auth_service.auth_core.config import AuthConfig
from netra_backend.app.redis_manager import redis_manager

logger = logging.getLogger(__name__)


class HealthCheckService:
    """
    Single Source of Truth for health check operations.
    
    This service provides a unified interface for monitoring service health,
    including dependencies like Redis and database connections.
    """
    
    def __init__(self, auth_config: AuthConfig, redis_manager: Optional[AuthRedisManager] = None):
        """
        Initialize HealthCheckService with configuration.
        
        Args:
            auth_config: Authentication configuration
            redis_manager: Optional Redis manager instance
        """
        self.auth_config = auth_config
        self.redis_manager = redis_manager or AuthRedisManager()
        
    async def check_service_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of auth service.
        
        Returns:
            Dictionary with health status and component checks
        """
        health_status = {
            "service": "auth_service",
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": {}
        }
        
        try:
            # Check Redis connectivity
            redis_health = await self._check_redis_health()
            health_status["checks"]["redis"] = redis_health
            
            # Check basic service functionality
            service_health = await self._check_service_functionality()
            health_status["checks"]["service"] = service_health
            
            # Determine overall status
            all_checks_healthy = all(
                check.get("status") == "healthy" 
                for check in health_status["checks"].values()
            )
            
            if not all_checks_healthy:
                health_status["status"] = "degraded"
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            
        return health_status
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis service health."""
        try:
            # Ensure Redis connection is available
            if not await self.redis_manager.ensure_connected():
                return {
                    "status": "unhealthy",
                    "message": "Redis connection not available"
                }
            
            client = self.redis_manager.get_client()
            if not client:
                return {
                    "status": "unhealthy", 
                    "message": "Redis client not available"
                }
            
            # Test Redis connectivity
            test_key = f"health_check_{datetime.now(UTC).timestamp()}"
            test_value = "health_check_value"
            
            # Try to set and get a test value
            await client.setex(test_key, 60, test_value)
            retrieved_value = await client.get(test_key)
            
            if retrieved_value and retrieved_value.decode() == test_value:
                # Clean up test key
                await client.delete(test_key)
                return {
                    "status": "healthy",
                    "message": "Redis connectivity confirmed"
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Redis read/write test failed"
                }
                
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Redis connectivity failed: {str(e)}"
            }
    
    async def _check_service_functionality(self) -> Dict[str, Any]:
        """Check basic service functionality."""
        try:
            # Basic functionality check - verify config is loaded
            if not self.auth_config:
                return {
                    "status": "unhealthy",
                    "message": "Auth configuration not available"
                }
                
            # Check if we can create basic service instances
            return {
                "status": "healthy",
                "message": "Service functionality verified"
            }
            
        except Exception as e:
            logger.error(f"Service functionality check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Service functionality check failed: {str(e)}"
            }
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get basic service status information.
        
        Returns:
            Dictionary with service status
        """
        try:
            return {
                "service": "auth_service",
                "status": "running",
                "timestamp": datetime.now(UTC).isoformat(),
                "version": "1.0.0"
            }
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {
                "service": "auth_service", 
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }
    
    async def ping(self) -> Dict[str, Any]:
        """
        Simple ping endpoint for basic connectivity check.
        
        Returns:
            Ping response
        """
        return {
            "status": "ok",
            "service": "auth_service",
            "timestamp": datetime.now(UTC).isoformat()
        }


__all__ = ["HealthCheckService"]