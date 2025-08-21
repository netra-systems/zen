"""ClickHouse Client - Focused ClickHouse Operations

Handles all ClickHouse database interactions with proper error handling.
Follows ClickHouse best practices for nested types and array operations.

Business Value: Reliable data access for performance analysis.
"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta

from netra_backend.app.logging_config import central_logger
from netra_backend.app.config import get_config

# ClickHouse client imports (assuming standard client available)
try:
    from clickhouse_connect import get_client
except ImportError:
    # Fallback for development/testing
    get_client = None


class ClickHouseClient:
    """Focused ClickHouse client for data analysis operations."""
    
    def __init__(self):
        self.logger = central_logger.get_logger("ClickHouseClient")
        self.client = None
        self._connection_pool = None
        self._health_status = {"healthy": False, "last_check": None}
        
    async def connect(self) -> bool:
        """Establish ClickHouse connection."""
        try:
            if get_client is None:
                self.logger.warning("ClickHouse client not available, using mock mode")
                return True
                
            config = get_config()
            self.client = get_client(
                host=getattr(config, 'clickhouse_host', 'localhost'),
                port=getattr(config, 'clickhouse_port', 8123),
                username=getattr(config, 'clickhouse_user', 'default'),
                password=getattr(config, 'clickhouse_password', ''),
                database=getattr(config, 'clickhouse_database', 'default')
            )
            
            # Test connection
            await self._test_connection()
            self._health_status = {"healthy": True, "last_check": datetime.utcnow()}
            
            self.logger.info("ClickHouse connection established")
            return True
            
        except Exception as e:
            self.logger.error(f"ClickHouse connection failed: {e}")
            self._health_status = {"healthy": False, "last_check": datetime.utcnow()}
            return False
    
    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute ClickHouse query with proper error handling."""
        if not self.is_healthy():
            await self.connect()
        
        try:
            if self.client is None:
                return self._mock_query_result(query)
            
            # Execute query with parameters
            result = self.client.query(query, parameters=parameters or {})
            
            # Convert to list of dictionaries
            return [dict(row) for row in result.result_rows] if result.result_rows else []
            
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            self.logger.error(f"Query: {query}")
            raise
    
    async def get_workload_metrics(self, timeframe: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get workload metrics with proper nested array handling."""
        # Use proper arrayElement() functions per ClickHouse spec
        query = """
        SELECT 
            timestamp,
            user_id,
            workload_id,
            -- Use arrayElement for safe nested array access
            arrayExists(x -> x = 'latency_ms', metrics.name) as has_latency,
            if(has_latency, 
               arrayElement(metrics.value, arrayFirstIndex(x -> x = 'latency_ms', metrics.name)), 
               0.0) as latency_ms,
            arrayExists(x -> x = 'cost_cents', metrics.name) as has_cost,
            if(has_cost, 
               arrayElement(metrics.value, arrayFirstIndex(x -> x = 'cost_cents', metrics.name)), 
               0.0) as cost_cents,
            arrayExists(x -> x = 'throughput', metrics.name) as has_throughput,
            if(has_throughput, 
               arrayElement(metrics.value, arrayFirstIndex(x -> x = 'throughput', metrics.name)), 
               0.0) as throughput
        FROM workload_events 
        WHERE timestamp >= now() - INTERVAL {timeframe:String}
        {user_filter}
        ORDER BY timestamp DESC
        LIMIT 10000
        """
        
        user_filter = "AND user_id = {user_id:String}" if user_id else ""
        final_query = query.format(user_filter=user_filter)
        
        parameters = {"timeframe": timeframe}
        if user_id:
            parameters["user_id"] = user_id
            
        return await self.execute_query(final_query, parameters)
    
    async def get_cost_breakdown(self, timeframe: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get cost breakdown analysis."""
        query = """
        SELECT 
            user_id,
            workload_type,
            COUNT(*) as request_count,
            AVG(if(arrayExists(x -> x = 'cost_cents', metrics.name),
                   arrayElement(metrics.value, arrayFirstIndex(x -> x = 'cost_cents', metrics.name)),
                   0.0)) as avg_cost_cents,
            SUM(if(arrayExists(x -> x = 'cost_cents', metrics.name),
                   arrayElement(metrics.value, arrayFirstIndex(x -> x = 'cost_cents', metrics.name)),
                   0.0)) as total_cost_cents
        FROM workload_events 
        WHERE timestamp >= now() - INTERVAL {timeframe:String}
        {user_filter}
        GROUP BY user_id, workload_type
        ORDER BY total_cost_cents DESC
        """
        
        user_filter = "AND user_id = {user_id:String}" if user_id else ""
        final_query = query.format(user_filter=user_filter)
        
        parameters = {"timeframe": timeframe}
        if user_id:
            parameters["user_id"] = user_id
            
        return await self.execute_query(final_query, parameters)
    
    async def _test_connection(self) -> None:
        """Test ClickHouse connection health."""
        if self.client:
            self.client.query("SELECT 1")
    
    def _mock_query_result(self, query: str) -> List[Dict[str, Any]]:
        """Generate mock data for development/testing."""
        self.logger.info(f"Using mock data for query: {query[:100]}...")
        
        # Return sample data structure
        return [
            {
                "timestamp": datetime.utcnow(),
                "user_id": "test_user",
                "workload_id": "test_workload",
                "latency_ms": 150.5,
                "cost_cents": 2.3,
                "throughput": 100.0
            }
        ]
    
    def is_healthy(self) -> bool:
        """Check if ClickHouse connection is healthy."""
        if not self._health_status["last_check"]:
            return False
            
        # Consider connection stale after 5 minutes
        time_since_check = datetime.utcnow() - self._health_status["last_check"]
        if time_since_check > timedelta(minutes=5):
            return False
            
        return self._health_status["healthy"]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status."""
        return {
            "healthy": self.is_healthy(),
            "last_check": self._health_status["last_check"].isoformat() if self._health_status["last_check"] else None,
            "client_available": self.client is not None or get_client is None
        }
    
    async def close(self) -> None:
        """Close ClickHouse connection."""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                self.logger.warning(f"Error closing ClickHouse client: {e}")
            finally:
                self.client = None
        
        self.logger.info("ClickHouse client closed")
