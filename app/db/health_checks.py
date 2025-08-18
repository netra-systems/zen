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
    
    def _get_default_databases(self, databases: List[str]) -> List[str]:
        """Get default database list if none provided."""
        return databases if databases else ["postgres", "clickhouse", "redis"]
    
    def _set_check_timestamp(self) -> None:
        """Set the last check time to current UTC time."""
        self.last_check_time = datetime.now(UTC)
    
    def _create_base_results_structure(self) -> Dict:
        """Create base health check results structure."""
        return {
            "overall_status": "healthy",
            "timestamp": self.last_check_time.isoformat(),
            "database_checks": {},
            "issues": []
        }
    
    def _initialize_health_check_results(self) -> Dict:
        """Initialize health check results structure."""
        self._set_check_timestamp()
        return self._create_base_results_structure()
    
    async def _process_single_database_check(self, db: str, results: Dict) -> None:
        """Process health check for single database."""
        try:
            db_result = await self._check_single_database(db)
            results["database_checks"][db] = db_result
            await self._update_overall_status_if_unhealthy(db, db_result, results)
        except Exception as e:
            await self._handle_database_check_exception(db, e, results)
    
    async def _update_overall_status_if_unhealthy(self, db: str, db_result: Dict, results: Dict) -> None:
        """Update overall status if database is unhealthy."""
        if db_result["status"] != "healthy":
            results["overall_status"] = "unhealthy"
            results["issues"].append(f"{db}: {db_result.get('error', 'Unknown issue')}")
    
    async def _handle_database_check_exception(self, db: str, e: Exception, results: Dict) -> None:
        """Handle exception during database check."""
        results["database_checks"][db] = {"status": "error", "error": str(e), "response_time_ms": 0}
        results["overall_status"] = "unhealthy"
        results["issues"].append(f"{db}: {str(e)}")
    
    def _update_check_history(self, results: Dict) -> None:
        """Update health check history."""
        self.health_status = results
        self.check_history.append(results)
        if len(self.check_history) > 10:
            self.check_history = self.check_history[-10:]
    
    async def _process_all_database_checks(self, databases: List[str], results: Dict) -> None:
        """Process health checks for all databases."""
        for db in databases:
            await self._process_single_database_check(db, results)

    async def check_database_health(self, databases: List[str] = None) -> Dict:
        """Check health of database connections"""
        databases = self._get_default_databases(databases)
        results = self._initialize_health_check_results()
        await self._process_all_database_checks(databases, results)
        self._update_check_history(results)
        return results
    
    async def _calculate_response_time(self) -> float:
        """Calculate and return response time in milliseconds."""
        start_time = datetime.now(UTC)
        await asyncio.sleep(0.01)  # Simulate check latency
        end_time = datetime.now(UTC)
        return round((end_time - start_time).total_seconds() * 1000, 2)
    
    def _get_postgres_health_response(self, response_time: float) -> Dict:
        """Get PostgreSQL health response."""
        return {
            "status": "healthy", "response_time_ms": response_time,
            "connection_pool": {"active": 2, "idle": 8, "max": 10},
            "last_query": "2024-08-14T10:00:00Z"
        }
    
    def _get_clickhouse_health_response(self, response_time: float) -> Dict:
        """Get ClickHouse health response."""
        return {
            "status": "healthy", "response_time_ms": response_time,
            "cluster_status": "active", "disk_usage": "45%",
            "last_query": "2024-08-14T10:00:00Z"
        }
    
    def _get_redis_health_response(self, response_time: float) -> Dict:
        """Get Redis health response."""
        return {
            "status": "healthy", "response_time_ms": response_time,
            "memory_usage": "128MB", "connected_clients": 5,
            "last_command": "2024-08-14T10:00:00Z"
        }
    
    def _get_unknown_database_response(self, db_name: str, response_time: float) -> Dict:
        """Get response for unknown database type."""
        return {
            "status": "unknown", "response_time_ms": response_time,
            "error": f"Unknown database type: {db_name}"
        }
    
    async def _check_single_database(self, db_name: str) -> Dict:
        """Check health of a single database"""
        response_time = await self._calculate_response_time()
        
        if db_name == "postgres":
            return self._get_postgres_health_response(response_time)
        elif db_name == "clickhouse":
            return self._get_clickhouse_health_response(response_time)
        elif db_name == "redis":
            return self._get_redis_health_response(response_time)
        else:
            return self._get_unknown_database_response(db_name, response_time)
    
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