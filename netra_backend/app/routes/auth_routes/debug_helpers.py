"""
Auth debug helpers for diagnosing login failures in staging.
Provides comprehensive logging and error analysis for auth service communication.
"""

from shared.logging.unified_logging_ssot import get_logger
from typing import Dict, Any, Optional
import httpx
from fastapi import HTTPException
from shared.isolated_environment import get_env

logger = get_logger(__name__)


class AuthServiceDebugger:
    """Debug helper for auth service communication issues."""
    
    def __init__(self):
        self.env = get_env()
    
    def get_auth_service_url(self) -> str:
        """Get auth service URL from environment with fallback logic."""
        auth_url = self.env.get("AUTH_SERVICE_URL", "")
        
        if not auth_url:
            # Try common environment variables
            if self.env.get("ENVIRONMENT", "").lower() == "staging":
                auth_url = "https://auth.staging.netrasystems.ai"
            elif self.env.get("ENVIRONMENT", "").lower() == "production":
                auth_url = "https://auth.netrasystems.ai"
            else:
                auth_url = "http://localhost:8081"
        
        return auth_url
    
    def get_service_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Get service credentials with debugging."""
        service_id = self.env.get("SERVICE_ID")
        service_secret = self.env.get("SERVICE_SECRET")
        
        # Clean up whitespace which is a common issue
        if service_id:
            service_id = service_id.strip()
        if service_secret:
            service_secret = service_secret.strip()
        
        return service_id, service_secret
    
    def log_environment_debug_info(self) -> Dict[str, Any]:
        """Log comprehensive environment debug information."""
        auth_url = self.get_auth_service_url()
        service_id, service_secret = self.get_service_credentials()
        
        debug_info = {
            "environment": self.env.get("ENVIRONMENT", "unknown"),
            "auth_service_url": auth_url,
            "service_id_configured": bool(service_id),
            "service_id_value": service_id or "NOT_SET",
            "service_secret_configured": bool(service_secret),
            "auth_service_enabled": self.env.get("AUTH_SERVICE_ENABLED", "unknown"),
            "testing_flag": self.env.get("TESTING", "unknown"),
            "netra_env": self.env.get("NETRA_ENV", "unknown"),
        }
        
        logger.info("AUTH SERVICE DEBUG INFO:")
        for key, value in debug_info.items():
            if "secret" in key.lower():
                # Don't log actual secret values
                logger.info(f"  {key}: {'SET' if value else 'NOT_SET'}")
            else:
                logger.info(f"  {key}: {value}")
        
        return debug_info
    
    async def test_auth_service_connectivity(self) -> Dict[str, Any]:
        """Test basic connectivity to auth service."""
        auth_url = self.get_auth_service_url()
        service_id, service_secret = self.get_service_credentials()
        
        result = {
            "auth_service_url": auth_url,
            "connectivity_test": "failed",
            "error": None,
            "status_code": None,
            "response_time_ms": None,
            "service_auth_supported": False,
        }
        
        try:
            import time
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try a simple health check endpoint
                try:
                    response = await client.get(f"{auth_url}/health")
                    result["connectivity_test"] = "success" if response.status_code == 200 else "partial"
                    result["status_code"] = response.status_code
                    result["response_time_ms"] = int((time.time() - start_time) * 1000)
                    
                    if response.status_code == 200:
                        logger.info(f"Auth service health check: OK ({result['response_time_ms']}ms)")
                    else:
                        logger.warning(f"Auth service health check: {response.status_code} ({result['response_time_ms']}ms)")
                        
                except httpx.RequestError:
                    # Health endpoint failed, try root endpoint
                    response = await client.get(auth_url)
                    result["connectivity_test"] = "success" if response.status_code == 200 else "partial"
                    result["status_code"] = response.status_code
                    result["response_time_ms"] = int((time.time() - start_time) * 1000)
                    
                    logger.info(f"Auth service root endpoint: {response.status_code} ({result['response_time_ms']}ms)")
                
                # Test service-to-service authentication if credentials are available
                if service_id and service_secret:
                    try:
                        headers = {
                            "X-Service-ID": service_id,
                            "X-Service-Secret": service_secret
                        }
                        auth_response = await client.post(
                            f"{auth_url}/auth/service-token",
                            json={"service_id": service_id, "service_secret": service_secret},
                            headers=headers
                        )
                        result["service_auth_supported"] = auth_response.status_code == 200
                        logger.info(f"Service auth test: {auth_response.status_code}")
                    except Exception as e:
                        logger.warning(f"Service auth test failed: {e}")
                        
        except Exception as e:
            result["error"] = str(e)
            result["connectivity_test"] = "failed"
            logger.error(f"Auth service connectivity test failed: {e}")
        
        return result
    
    async def debug_login_attempt(self, email: str, password: str) -> Dict[str, Any]:
        """Debug a login attempt with comprehensive logging."""
        debug_info = self.log_environment_debug_info()
        connectivity = await self.test_auth_service_connectivity()
        
        result = {
            "debug_info": debug_info,
            "connectivity": connectivity,
            "login_attempt": "failed",
            "error_details": None,
            "recommended_actions": []
        }
        
        # Determine recommended actions based on findings
        if connectivity["connectivity_test"] == "failed":
            result["recommended_actions"].append("Check AUTH_SERVICE_URL configuration")
            result["recommended_actions"].append("Verify auth service is running")
            result["recommended_actions"].append("Check network connectivity")
        
        if not debug_info["service_id_configured"] or not debug_info["service_secret_configured"]:
            result["recommended_actions"].append("Configure SERVICE_ID and SERVICE_SECRET environment variables")
        
        if not connectivity["service_auth_supported"]:
            result["recommended_actions"].append("Verify service credentials are valid")
            result["recommended_actions"].append("Check if backend service is registered with auth service")
        
        logger.error("LOGIN ATTEMPT DEBUG SUMMARY:")
        logger.error(f"Environment: {debug_info['environment']}")
        logger.error(f"Auth Service URL: {debug_info['auth_service_url']}")
        logger.error(f"Connectivity: {connectivity['connectivity_test']}")
        logger.error(f"Service Auth: {connectivity['service_auth_supported']}")
        logger.error(f"Recommended Actions: {result['recommended_actions']}")
        
        return result


def create_enhanced_auth_error_response(
    original_error: Exception,
    debug_info: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Create enhanced error response with debug information for staging."""
    
    env = get_env()
    environment = env.get("ENVIRONMENT", "").lower()
    
    # In staging, provide more detailed error information
    if environment == "staging":
        error_detail = {
            "error": "Authentication service communication failed",
            "original_error": str(original_error),
            "debug_info": debug_info or {},
            "suggestions": [
                "Check AUTH_SERVICE_URL configuration",
                "Verify SERVICE_ID and SERVICE_SECRET are set",
                "Confirm auth service is running and accessible",
                "Check network connectivity between services"
            ]
        }
        return HTTPException(
            status_code=500,
            detail=error_detail
        )
    else:
        # In production, provide generic error
        return HTTPException(
            status_code=500,
            detail="Authentication service temporarily unavailable"
        )


async def enhanced_auth_service_call(
    func,
    *args,
    operation_name: str = "auth_operation",
    **kwargs
) -> Any:
    """Enhanced wrapper for auth service calls with comprehensive error handling."""
    
    debugger = AuthServiceDebugger()
    
    try:
        # Log the operation attempt
        logger.info(f"Attempting {operation_name}")
        
        # Execute the function
        result = await func(*args, **kwargs)
        
        if result:
            logger.info(f"{operation_name} completed successfully")
            return result
        else:
            logger.warning(f"{operation_name} returned empty result")
            
            # Debug the failure
            debug_info = await debugger.test_auth_service_connectivity()
            logger.error(f"{operation_name} debug info: {debug_info}")
            
            raise HTTPException(
                status_code=401,
                detail=f"{operation_name.replace('_', ' ').title()} failed"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"{operation_name} failed with exception: {e}")
        
        # Get debug information
        debug_info = await debugger.test_auth_service_connectivity()
        
        # Create enhanced error response
        raise create_enhanced_auth_error_response(e, debug_info)