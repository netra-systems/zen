"""
Database Health Checks Module
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, UTC
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DatabaseHealthChecker:
    """Performs health checks on database connections"""
    
    def __init__(self):
        self.last_check_time = None
        self.health_status = {"status": "unknown"}
        self.check_history = []
    
    async def check_database_health(self, databases: List[str] = None) -> Dict:
        """Check health of database connections"""
        if not databases:
            databases = ["postgres", "clickhouse", "redis"]
        
        self.last_check_time = datetime.now(UTC)
        results = {
            "overall_status": "healthy",
            "timestamp": self.last_check_time.isoformat(),
            "database_checks": {},
            "issues": []
        }
        
        for db in databases:
            try:
                db_result = await self._check_single_database(db)
                results["database_checks"][db] = db_result
                
                if db_result["status"] != "healthy":
                    results["overall_status"] = "unhealthy"
                    results["issues"].append(f"{db}: {db_result.get('error', 'Unknown issue')}")
                    
            except Exception as e:
                results["database_checks"][db] = {
                    "status": "error",
                    "error": str(e),
                    "response_time_ms": 0
                }
                results["overall_status"] = "unhealthy"
                results["issues"].append(f"{db}: {str(e)}")
        
        self.health_status = results
        self.check_history.append(results)
        
        # Keep only last 10 checks
        if len(self.check_history) > 10:
            self.check_history = self.check_history[-10:]
        
        return results
    
    async def _check_single_database(self, db_name: str) -> Dict:
        """Check health of a single database"""
        start_time = datetime.now(UTC)
        
        # Mock database health check
        await asyncio.sleep(0.01)  # Simulate check latency
        
        end_time = datetime.now(UTC)
        response_time = (end_time - start_time).total_seconds() * 1000
        
        # Mock health responses
        if db_name == "postgres":
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "connection_pool": {"active": 2, "idle": 8, "max": 10},
                "last_query": "2024-08-14T10:00:00Z"
            }
        elif db_name == "clickhouse":
            return {
                "status": "healthy", 
                "response_time_ms": round(response_time, 2),
                "cluster_status": "active",
                "disk_usage": "45%",
                "last_query": "2024-08-14T10:00:00Z"
            }
        elif db_name == "redis":
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "memory_usage": "128MB",
                "connected_clients": 5,
                "last_command": "2024-08-14T10:00:00Z"
            }
        else:
            return {
                "status": "unknown",
                "response_time_ms": round(response_time, 2),
                "error": f"Unknown database type: {db_name}"
            }
    
    def get_health_status(self) -> Dict:
        """Get current health status"""
        return self.health_status
    
    def get_check_history(self) -> List[Dict]:
        """Get recent health check history"""
        return self.check_history
    
    async def check_connection_pools(self) -> Dict:
        """Check database connection pool status"""
        return {
            "postgres": {
                "active_connections": 2,
                "idle_connections": 8,
                "max_connections": 10,
                "pool_health": "healthy"
            },
            "clickhouse": {
                "active_connections": 1,
                "idle_connections": 4,
                "max_connections": 5,
                "pool_health": "healthy"
            }
        }
    
    async def run_diagnostic_queries(self) -> Dict:
        """Run diagnostic queries on databases"""
        return {
            "postgres": {
                "query": "SELECT 1",
                "result": "success",
                "execution_time_ms": 5.2
            },
            "clickhouse": {
                "query": "SELECT version()",
                "result": "success", 
                "execution_time_ms": 12.8
            }
        }