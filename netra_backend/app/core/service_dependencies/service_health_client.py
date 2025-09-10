"""
Service Health Client - HTTP-based service communication for Golden Path validation.

This client replaces direct database access with HTTP calls to service health endpoints,
respecting microservice boundaries and enabling proper service isolation.
"""

import asyncio
import aiohttp
from datetime import UTC, datetime
from typing import Any, Dict, Optional
from urllib.parse import urljoin

from netra_backend.app.logging_config import central_logger
from .models import ServiceType, EnvironmentType


class ServiceHealthClient:
    """
    HTTP client for service health validation.
    
    Enables Golden Path validation through service HTTP endpoints instead of
    direct database access, maintaining microservice independence.
    """
    
    def __init__(self, environment: EnvironmentType = EnvironmentType.DEVELOPMENT):
        """Initialize service health client."""
        self.logger = central_logger.get_logger(__name__)
        self.environment = environment
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Service base URLs by environment
        self.service_urls = self._get_service_urls(environment)
        
        # HTTP timeouts for health checks
        self.timeout = aiohttp.ClientTimeout(total=10.0, connect=3.0)
    
    def _get_service_urls(self, environment: EnvironmentType) -> Dict[ServiceType, str]:
        """Get service base URLs for the given environment."""
        if environment == EnvironmentType.TESTING:
            return {
                ServiceType.AUTH_SERVICE: "http://localhost:8081",
                ServiceType.BACKEND_SERVICE: "http://localhost:8000"
            }
        elif environment == EnvironmentType.DEVELOPMENT:
            return {
                ServiceType.AUTH_SERVICE: "http://localhost:8081", 
                ServiceType.BACKEND_SERVICE: "http://localhost:8000"
            }
        elif environment == EnvironmentType.STAGING:
            return {
                ServiceType.AUTH_SERVICE: "https://auth.staging.netrasystems.ai",
                ServiceType.BACKEND_SERVICE: "https://api.staging.netrasystems.ai"
            }
        elif environment == EnvironmentType.PRODUCTION:
            return {
                ServiceType.AUTH_SERVICE: "https://auth.netrasystems.ai",
                ServiceType.BACKEND_SERVICE: "https://api.netrasystems.ai"
            }
        else:
            # Default to development URLs
            return {
                ServiceType.AUTH_SERVICE: "http://localhost:8081",
                ServiceType.BACKEND_SERVICE: "http://localhost:8000"
            }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def validate_auth_service_health(self) -> Dict[str, Any]:
        """
        Validate Auth Service health through HTTP endpoint.
        
        Returns:
            Dict containing validation result with success status and details
        """
        try:
            base_url = self.service_urls.get(ServiceType.AUTH_SERVICE)
            if not base_url:
                return {
                    "requirement": "jwt_validation_ready",
                    "success": False,
                    "message": f"Auth service URL not configured for {self.environment.value}",
                    "details": {"environment": self.environment.value}
                }
            
            health_url = urljoin(base_url, "/health/auth")
            
            if not self.session:
                self.session = aiohttp.ClientSession(timeout=self.timeout)
            
            async with self.session.get(health_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "requirement": "jwt_validation_ready",
                        "success": True,
                        "message": "Auth service health validated via HTTP",
                        "details": {
                            "status_code": response.status,
                            "response_data": data,
                            "service_url": base_url
                        }
                    }
                else:
                    error_text = await response.text()
                    return {
                        "requirement": "jwt_validation_ready",
                        "success": False,
                        "message": f"Auth service health check failed - HTTP {response.status}",
                        "details": {
                            "status_code": response.status,
                            "error_response": error_text,
                            "service_url": base_url
                        }
                    }
                    
        except aiohttp.ClientTimeout:
            return {
                "requirement": "jwt_validation_ready",
                "success": False,
                "message": "Auth service health check timed out",
                "details": {
                    "timeout": f"{self.timeout.total}s",
                    "service_url": self.service_urls.get(ServiceType.AUTH_SERVICE),
                    "error_type": "timeout"
                }
            }
        except aiohttp.ClientError as e:
            return {
                "requirement": "jwt_validation_ready",
                "success": False,
                "message": f"Auth service health check network error: {str(e)}",
                "details": {
                    "service_url": self.service_urls.get(ServiceType.AUTH_SERVICE),
                    "error_type": "network_error",
                    "error": str(e)
                }
            }
        except Exception as e:
            return {
                "requirement": "jwt_validation_ready",
                "success": False,
                "message": f"Auth service health check failed: {str(e)}",
                "details": {
                    "service_url": self.service_urls.get(ServiceType.AUTH_SERVICE),
                    "error_type": "unknown_error",
                    "error": str(e)
                }
            }
    
    async def validate_backend_service_health(self) -> Dict[str, Any]:
        """
        Validate Backend Service health through HTTP endpoint.
        
        Returns:
            Dict containing validation result with success status and details
        """
        try:
            base_url = self.service_urls.get(ServiceType.BACKEND_SERVICE)
            if not base_url:
                return {
                    "requirement": "agent_execution_ready",
                    "success": False,
                    "message": f"Backend service URL not configured for {self.environment.value}",
                    "details": {"environment": self.environment.value}
                }
            
            health_url = urljoin(base_url, "/health/backend")
            
            if not self.session:
                self.session = aiohttp.ClientSession(timeout=self.timeout)
            
            async with self.session.get(health_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "requirement": "agent_execution_ready",
                        "success": True,
                        "message": "Backend service health validated via HTTP",
                        "details": {
                            "status_code": response.status,
                            "response_data": data,
                            "service_url": base_url
                        }
                    }
                else:
                    error_text = await response.text()
                    return {
                        "requirement": "agent_execution_ready", 
                        "success": False,
                        "message": f"Backend service health check failed - HTTP {response.status}",
                        "details": {
                            "status_code": response.status,
                            "error_response": error_text,
                            "service_url": base_url
                        }
                    }
                    
        except aiohttp.ClientTimeout:
            return {
                "requirement": "agent_execution_ready",
                "success": False,
                "message": "Backend service health check timed out",
                "details": {
                    "timeout": f"{self.timeout.total}s",
                    "service_url": self.service_urls.get(ServiceType.BACKEND_SERVICE),
                    "error_type": "timeout"
                }
            }
        except aiohttp.ClientError as e:
            return {
                "requirement": "agent_execution_ready",
                "success": False,
                "message": f"Backend service health check network error: {str(e)}",
                "details": {
                    "service_url": self.service_urls.get(ServiceType.BACKEND_SERVICE),
                    "error_type": "network_error",
                    "error": str(e)
                }
            }
        except Exception as e:
            return {
                "requirement": "agent_execution_ready",
                "success": False,
                "message": f"Backend service health check failed: {str(e)}",
                "details": {
                    "service_url": self.service_urls.get(ServiceType.BACKEND_SERVICE),
                    "error_type": "unknown_error",
                    "error": str(e)
                }
            }
    
    async def close(self):
        """Close the HTTP client session."""
        if self.session:
            await self.session.close()
            self.session = None