"""
Auth service health check configuration.
Uses SSOT AuthEnvironment for all configuration access.
"""

import os
from typing import Dict, Any
from enum import Enum
from sqlalchemy import text
from auth_service.auth_core.auth_environment import get_auth_env


class HealthStatus(Enum):
    """Health status values"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


async def check_auth_postgres_health() -> Dict[str, Any]:
    """Check PostgreSQL database connectivity for auth service."""
    try:
        from auth_service.auth_core.database.connection import auth_db
        
        # Test database connection
        async with auth_db.get_session() as session:
            result = await session.execute(text("SELECT 1"))
            _ = result.scalar()
            
        return {
            "status": HealthStatus.HEALTHY.value,
            "message": "Auth database connection successful"
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY.value,
            "message": f"Auth database connection failed: {str(e)}"
        }


async def check_oauth_providers_health() -> Dict[str, Any]:
    """Check OAuth provider connectivity and configuration."""
    try:
        # Use SSOT AuthEnvironment for all configuration access
        auth_env = get_auth_env()
        
        # Check OAuth configuration using SSOT
        google_client_id = auth_env.get_oauth_google_client_id()
        github_client_id = auth_env.get_oauth_github_client_id()
        
        configured_providers = []
        if google_client_id:
            configured_providers.append("google")
        if github_client_id:
            configured_providers.append("github")
        
        if not configured_providers:
            return {
                "status": HealthStatus.DEGRADED.value,
                "message": "No OAuth providers configured",
                "details": {"configured_providers": []}
            }
        
        return {
            "status": HealthStatus.HEALTHY.value,
            "message": f"OAuth providers configured: {', '.join(configured_providers)}",
            "details": {"configured_providers": configured_providers}
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY.value,
            "message": f"OAuth provider check failed: {str(e)}"
        }


async def check_jwt_configuration() -> Dict[str, Any]:
    """Check JWT configuration and secret key."""
    try:
        # Use SSOT AuthEnvironment for all JWT configuration
        auth_env = get_auth_env()
        
        secret_key = auth_env.get_jwt_secret_key()
        algorithm = auth_env.get_jwt_algorithm()
        
        if not secret_key:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": "JWT secret key not configured"
            }
        
        if len(secret_key) < 32:
            return {
                "status": HealthStatus.DEGRADED.value,
                "message": "JWT secret key is weak (less than 32 characters)"
            }
        
        return {
            "status": HealthStatus.HEALTHY.value,
            "message": f"JWT configured with {algorithm} algorithm",
            "details": {"algorithm": algorithm}
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY.value,
            "message": f"JWT configuration check failed: {str(e)}"
        }


# Simplified health check setup - auth service is independent
async def get_auth_health() -> Dict[str, Any]:
    """Get overall health status of auth service."""
    health_checks = {
        "database": await check_auth_postgres_health(),
        "jwt": await check_jwt_configuration(),
        "oauth": await check_oauth_providers_health()
    }
    
    # Determine overall status
    overall_status = HealthStatus.HEALTHY.value
    for check in health_checks.values():
        if check["status"] == HealthStatus.UNHEALTHY.value:
            overall_status = HealthStatus.UNHEALTHY.value
            break
        elif check["status"] == HealthStatus.DEGRADED.value and overall_status == HealthStatus.HEALTHY.value:
            overall_status = HealthStatus.DEGRADED.value
    
    return {
        "status": overall_status,
        "service": "auth_service",
        "version": "1.0.0",
        "checks": health_checks
    }