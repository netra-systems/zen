"""Extended health check endpoints with detailed monitoring."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgres import get_pool_status, async_engine
from app.dependencies import get_db_dependency
from app.logging_config import central_logger
from typing import Dict, Any
import psutil
import asyncio
from datetime import datetime

logger = central_logger.get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])

@router.get("/database")
async def health_database(db: AsyncSession = Depends(get_db_dependency)) -> Dict[str, Any]:
    """Check database health and connection pool status."""
    try:
        # Test database connectivity
        result = await db.execute("SELECT 1")
        db_connected = result.scalar() == 1
        
        # Get pool status
        pool_status = get_pool_status()
        
        # Get database statistics if available
        stats = {}
        if async_engine:
            try:
                result = await db.execute("""
                    SELECT 
                        count(*) as active_connections,
                        max(state_change) as last_activity
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """)
                row = result.first()
                if row:
                    stats = {
                        "active_connections": row.active_connections,
                        "last_activity": row.last_activity.isoformat() if row.last_activity else None
                    }
            except Exception as e:
                logger.warning(f"Could not fetch database statistics: {e}")
        
        return {
            "status": "healthy" if db_connected else "unhealthy",
            "connected": db_connected,
            "pool_status": pool_status,
            "database_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")

@router.get("/system")
async def health_system() -> Dict[str, Any]:
    """Check system resource usage."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get process-specific metrics
        process = psutil.Process()
        process_memory = process.memory_info()
        
        return {
            "status": "healthy",
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "free": disk.free,
                    "percent": disk.percent
                }
            },
            "process": {
                "memory_rss": process_memory.rss,
                "memory_vms": process_memory.vms,
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads(),
                "connections": len(process.connections(kind='inet'))
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/pool-metrics")
async def pool_metrics() -> Dict[str, Any]:
    """Get detailed connection pool metrics for monitoring."""
    metrics = {
        "pool_configuration": {
            "pool_size": 20,
            "max_overflow": 30,
            "pool_timeout": 30,
            "pool_recycle": 1800,
            "max_connections": 100
        },
        "current_status": get_pool_status(),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Calculate pool utilization
    if metrics["current_status"]["async"]:
        async_pool = metrics["current_status"]["async"]
        if async_pool.get("size") is not None and async_pool.get("checked_in") is not None:
            active = async_pool["size"] - async_pool["checked_in"]
            metrics["utilization"] = {
                "active_connections": active,
                "utilization_percent": (active / (async_pool["size"] + async_pool.get("overflow", 0))) * 100 if async_pool["size"] else 0
            }
    
    return metrics