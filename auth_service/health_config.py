"""
Auth service health check configuration.
Sets up all health checks for the auth service using the unified health system.
"""

import os
from typing import Dict, Any

from netra_backend.app.services.unified_health_service import UnifiedHealthService
from netra_backend.app.services.health_registry import health_registry
from netra_backend.app.core.health_types import HealthCheckConfig, CheckType, HealthStatus


async def check_auth_postgres_health() -> Dict[str, Any]:
    """Check PostgreSQL database connectivity for auth service."""
    try:
        from auth_service.auth_core.database.connection import auth_db
        
        # Test database connection
        async with auth_db.get_session() as session:
            result = await session.execute("SELECT 1")
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
        # Check that OAuth providers are configured
        google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        github_client_id = os.getenv("GITHUB_CLIENT_ID")
        
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
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM", "HS256")
        
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


async def setup_auth_health_service() -> UnifiedHealthService:
    """Configure health checks for the auth service."""
    
    health_service = UnifiedHealthService("auth_service", "1.0.0")
    
    # Critical infrastructure checks
    await health_service.register_check(HealthCheckConfig(
        name="postgres",
        description="PostgreSQL database for auth",
        check_function=check_auth_postgres_health,
        timeout_seconds=10.0,
        check_type=CheckType.READINESS,
        critical=True,
        priority=1,  # Critical
        labels={"component": "database", "service": "auth"}
    ))
    
    # JWT configuration check
    await health_service.register_check(HealthCheckConfig(
        name="jwt_configuration",
        description="JWT token configuration",
        check_function=check_jwt_configuration,
        timeout_seconds=2.0,
        check_type=CheckType.READINESS,
        critical=True,
        priority=1,  # Critical for auth service
        labels={"component": "security", "service": "auth"}
    ))
    
    # OAuth provider checks
    await health_service.register_check(HealthCheckConfig(
        name="oauth_providers",
        description="OAuth provider connectivity",
        check_function=check_oauth_providers_health,
        timeout_seconds=5.0,
        check_type=CheckType.COMPONENT,
        critical=False,
        priority=2,  # Important but not critical
        labels={"component": "oauth", "service": "auth"}
    ))
    
    # Register with global registry
    health_registry.register_service("auth_service", health_service)
    
    return health_service