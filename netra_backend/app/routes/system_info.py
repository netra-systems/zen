"""
System information and introspection endpoints for monitoring and debugging.

Provides detailed system, configuration, and dependency status information.
"""

import os
import sys
import platform
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from netra_backend.app.auth_integration import get_current_user_optional
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
router = APIRouter()


class SystemInfo(BaseModel):
    """System information response."""
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment name")
    python_version: str = Field(..., description="Python version")
    platform: str = Field(..., description="Operating system platform")
    hostname: str = Field(..., description="Hostname")
    started_at: str = Field(..., description="Service start time")
    git_commit: Optional[str] = Field(None, description="Git commit hash")
    build_time: Optional[str] = Field(None, description="Build timestamp")


class ConfigValidation(BaseModel):
    """Configuration validation response."""
    valid: bool = Field(..., description="Whether configuration is valid")
    errors: List[str] = Field(..., description="List of validation errors")
    warnings: List[str] = Field(..., description="List of validation warnings")
    config_sources: Dict[str, str] = Field(..., description="Configuration sources")
    effective_config: Dict[str, Any] = Field(..., description="Effective configuration (sanitized)")


class DependencyStatus(BaseModel):
    """Dependency status response."""
    name: str = Field(..., description="Dependency name")
    type: str = Field(..., description="Dependency type (database, api, queue, etc)")
    status: str = Field(..., description="Status (healthy, degraded, unhealthy)")
    latency_ms: Optional[float] = Field(None, description="Connection latency")
    version: Optional[str] = Field(None, description="Dependency version")
    error: Optional[str] = Field(None, description="Error message if unhealthy")


class DependenciesReport(BaseModel):
    """Dependencies status report."""
    overall_status: str = Field(..., description="Overall dependencies status")
    dependencies: List[DependencyStatus] = Field(..., description="Individual dependency statuses")
    timestamp: str = Field(..., description="Check timestamp")


class RouteInfo(BaseModel):
    """Route information."""
    path: str = Field(..., description="Route path")
    methods: List[str] = Field(..., description="HTTP methods")
    name: Optional[str] = Field(None, description="Route name")
    tags: List[str] = Field(default_factory=list, description="Route tags")


@router.get("/info", response_model=SystemInfo)
async def get_system_info(
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> SystemInfo:
    """Get system information."""
    import socket
    
    # Try to get git commit from environment or file
    git_commit = get_env().get("GIT_COMMIT")
    if not git_commit and os.path.exists(".git/HEAD"):
        try:
            with open(".git/HEAD", "r") as f:
                ref = f.read().strip()
                if ref.startswith("ref: "):
                    ref_path = ref.replace("ref: ", "").strip()
                    commit_file = f".git/{ref_path}"
                    if os.path.exists(commit_file):
                        with open(commit_file, "r") as cf:
                            git_commit = cf.read().strip()[:8]
        except Exception:
            pass
    
    # Get start time
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        import psutil
        started_at = datetime.fromtimestamp(
            psutil.Process().create_time(),
            tz=timezone.utc
        ).isoformat()
    except ImportError:
        pass
    
    return SystemInfo(
        version=get_env().get("SERVICE_VERSION", "1.0.0"),
        environment=get_env().get("ENVIRONMENT", "development"),
        python_version=sys.version.split()[0],
        platform=f"{platform.system()} {platform.release()}",
        hostname=socket.gethostname(),
        started_at=started_at,
        git_commit=git_commit,
        build_time=get_env().get("BUILD_TIME")
    )


@router.get("/config/validate", response_model=ConfigValidation)
async def validate_configuration(
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> ConfigValidation:
    """Validate current configuration."""
    errors = []
    warnings = []
    config_sources = {}
    effective_config = {}
    
    try:
        from shared.isolated_environment import IsolatedEnvironment
        env = IsolatedEnvironment()
        
        # Check required environment variables - using component validation for database
        required_vars = [
            "JWT_SECRET_KEY",
            "OPENAI_API_KEY"
        ]
        
        # Validate database configuration using DatabaseURLBuilder SSOT
        database_config_vars = [
            "POSTGRES_HOST",
            "POSTGRES_USER", 
            "POSTGRES_DB"
        ]
        
        for var in required_vars:
            value = env.get(var)
            if not value:
                errors.append(f"Missing required environment variable: {var}")
            else:
                # Sanitize sensitive values
                if "SECRET" in var or "KEY" in var or "PASSWORD" in var:
                    effective_config[var] = "***REDACTED***"
                elif "URL" in var:
                    # Show only the scheme and host
                    if value.startswith(("http://", "https://", "postgresql://")):
                        parts = value.split("@")
                        if len(parts) > 1:
                            effective_config[var] = f"{parts[0].split('://')[0]}://***@{parts[-1].split('/')[0]}/***"
                        else:
                            effective_config[var] = f"{value.split('://')[0]}://***"
                else:
                    effective_config[var] = value
        
        # Check configuration sources
        if os.path.exists(".env"):
            config_sources[".env"] = "Found"
        if get_env().get("ENVIRONMENT"):
            config_sources["ENVIRONMENT"] = get_env().get("ENVIRONMENT")
        
        # Validate database configuration using DatabaseURLBuilder SSOT
        from shared.database_url_builder import DatabaseURLBuilder
        builder = DatabaseURLBuilder(env.get_all())
        
        # Validate database configuration
        is_valid, db_error = builder.validate()
        if not is_valid:
            errors.append(f"Database configuration invalid: {db_error}")
        
        # Get database URL for format validation
        db_url = builder.get_url_for_environment()
        if db_url:
            if not (db_url.startswith(("postgresql://", "postgres://")) or "memory" in db_url):
                errors.append("Database URL must be a PostgreSQL connection string or SQLite memory URL")
        
        # Check individual database configuration variables
        for var in database_config_vars:
            if not env.get(var):
                warnings.append(f"Database component {var} not configured - using defaults or environment detection")
        
        # Check for development mode warnings
        if env.get("ENVIRONMENT") == "development":
            if env.get("DEBUG") == "true":
                warnings.append("DEBUG mode is enabled")
            if not env.get("SSL_ENABLED"):
                warnings.append("SSL is not enabled")
        
        # Validate JWT configuration
        jwt_secret = env.get("JWT_SECRET_KEY")
        if jwt_secret and len(jwt_secret) < 32:
            warnings.append("JWT_SECRET_KEY should be at least 32 characters")
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        errors.append(f"Failed to validate configuration: {str(e)}")
    
    return ConfigValidation(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        config_sources=config_sources,
        effective_config=effective_config
    )


@router.get("/dependencies/status", response_model=DependenciesReport)
async def check_dependencies(
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> DependenciesReport:
    """Check status of all external dependencies."""
    dependencies = []
    overall_healthy = True
    
    # Check PostgreSQL
    try:
        import time
        from netra_backend.app.database import get_db_session
        
        start = time.time()
        async with get_db_session() as session:
            result = await session.execute("SELECT version()")
            version = result.scalar()
        latency = (time.time() - start) * 1000
        
        dependencies.append(DependencyStatus(
            name="PostgreSQL",
            type="database",
            status="healthy",
            latency_ms=latency,
            version=version.split()[1] if version else None
        ))
    except Exception as e:
        dependencies.append(DependencyStatus(
            name="PostgreSQL",
            type="database",
            status="unhealthy",
            error=str(e)
        ))
        overall_healthy = False
    
    # Check Redis (if configured)
    redis_url = get_env().get("REDIS_URL")
    if redis_url:
        try:
            import redis.asyncio as redis
            import time
            
            start = time.time()
            r = redis.from_url(redis_url)
            await r.ping()
            info = await r.info("server")
            await r.close()
            latency = (time.time() - start) * 1000
            
            dependencies.append(DependencyStatus(
                name="Redis",
                type="cache",
                status="healthy",
                latency_ms=latency,
                version=info.get("redis_version")
            ))
        except Exception as e:
            dependencies.append(DependencyStatus(
                name="Redis",
                type="cache",
                status="unhealthy",
                error=str(e)
            ))
            overall_healthy = False
    
    # Check OpenAI API
    try:
        import httpx
        import time
        
        start = time.time()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {get_env().get('OPENAI_API_KEY')}"},
                timeout=5.0
            )
        latency = (time.time() - start) * 1000
        
        if response.status_code == 200:
            dependencies.append(DependencyStatus(
                name="OpenAI API",
                type="api",
                status="healthy",
                latency_ms=latency
            ))
        else:
            dependencies.append(DependencyStatus(
                name="OpenAI API",
                type="api",
                status="degraded",
                latency_ms=latency,
                error=f"HTTP {response.status_code}"
            ))
            overall_healthy = False
    except Exception as e:
        dependencies.append(DependencyStatus(
            name="OpenAI API",
            type="api",
            status="unhealthy",
            error=str(e)
        ))
        overall_healthy = False
    
    # Check Auth Service (if separate)
    auth_service_url = get_env().get("AUTH_SERVICE_URL")
    if auth_service_url:
        try:
            import httpx
            import time
            
            start = time.time()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{auth_service_url}/health",
                    timeout=5.0
                )
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                dependencies.append(DependencyStatus(
                    name="Auth Service",
                    type="service",
                    status="healthy",
                    latency_ms=latency
                ))
            else:
                dependencies.append(DependencyStatus(
                    name="Auth Service",
                    type="service",
                    status="degraded",
                    latency_ms=latency,
                    error=f"HTTP {response.status_code}"
                ))
                overall_healthy = False
        except Exception as e:
            dependencies.append(DependencyStatus(
                name="Auth Service",
                type="service",
                status="unhealthy",
                error=str(e)
            ))
            overall_healthy = False
    
    return DependenciesReport(
        overall_status="healthy" if overall_healthy else "degraded",
        dependencies=dependencies,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get("/debug/routes", response_model=List[RouteInfo])
async def list_routes(
    request: Request,
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> List[RouteInfo]:
    """List all registered API routes."""
    routes = []
    
    for route in request.app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            route_info = RouteInfo(
                path=route.path,
                methods=list(route.methods) if route.methods else [],
                name=route.name,
                tags=getattr(route, "tags", [])
            )
            routes.append(route_info)
    
    # Sort by path for readability
    routes.sort(key=lambda r: r.path)
    
    return routes


@router.get("/debug/async_tasks")
async def get_async_tasks(
    user: Optional[Dict] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """Get information about running async tasks."""
    tasks = asyncio.all_tasks()
    
    task_info = {
        "total_tasks": len(tasks),
        "tasks": []
    }
    
    for task in tasks:
        info = {
            "name": task.get_name(),
            "done": task.done(),
            "cancelled": task.cancelled()
        }
        
        if task.done() and not task.cancelled():
            try:
                info["exception"] = str(task.exception())
            except Exception:
                info["exception"] = None
        
        task_info["tasks"].append(info)
    
    return task_info
