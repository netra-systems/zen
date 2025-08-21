"""Unified database index management.

This module provides centralized management for database index optimization
across PostgreSQL and ClickHouse databases with proper error handling.
"""

from datetime import datetime
from typing import Any, Dict, List

from netra_backend.app.db.clickhouse_index_optimizer import ClickHouseIndexOptimizer
from netra_backend.app.db.postgres_index_optimizer import PostgreSQLIndexOptimizer
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DatabaseOptimizationRunner:
    """Run optimization operations across databases."""
    
    def __init__(self, postgres_optimizer: PostgreSQLIndexOptimizer, 
                 clickhouse_optimizer: ClickHouseIndexOptimizer):
        self.postgres_optimizer = postgres_optimizer
        self.clickhouse_optimizer = clickhouse_optimizer
    
    async def _run_postgres_optimizations(self) -> Dict[str, Any]:
        """Run PostgreSQL optimizations with error handling."""
        try:
            postgres_indexes = await self.postgres_optimizer.create_performance_indexes()
            postgres_recommendations = await self.postgres_optimizer.analyze_query_performance()
            postgres_stats = await self.postgres_optimizer.get_index_usage_stats()
            
            return {
                "indexes_created": postgres_indexes,
                "recommendations": [rec.__dict__ for rec in postgres_recommendations],
                "usage_stats": postgres_stats
            }
        except Exception as e:
            logger.error(f"PostgreSQL optimization error: {e}")
            return {"error": str(e)}
    
    async def _run_clickhouse_optimizations(self) -> Dict[str, Any]:
        """Run ClickHouse optimizations with error handling."""
        try:
            clickhouse_tables = await self.clickhouse_optimizer.optimize_table_engines()
            clickhouse_views = await self.clickhouse_optimizer.create_materialized_views()
            
            return {
                "table_optimizations": clickhouse_tables,
                "materialized_views": clickhouse_views
            }
        except Exception as e:
            logger.error(f"ClickHouse optimization error: {e}")
            return {"error": str(e)}
    
    async def run_all_optimizations(self) -> Dict[str, Any]:
        """Run optimization on all databases."""
        results = {
            "postgres": {},
            "clickhouse": {},
            "recommendations": []
        }
        
        # Run PostgreSQL optimizations
        postgres_results = await self._run_postgres_optimizations()
        results["postgres"] = postgres_results
        
        # Run ClickHouse optimizations  
        clickhouse_results = await self._run_clickhouse_optimizations()
        results["clickhouse"] = clickhouse_results
        
        return results


class DatabaseReportGenerator:
    """Generate comprehensive database optimization reports."""
    
    def __init__(self, postgres_optimizer: PostgreSQLIndexOptimizer):
        self.postgres_optimizer = postgres_optimizer
    
    async def _get_postgres_statistics(self) -> Dict[str, Any]:
        """Get PostgreSQL statistics for report."""
        try:
            return await self.postgres_optimizer.get_index_usage_stats()
        except Exception as e:
            logger.error(f"Error getting PostgreSQL stats: {e}")
            return {"error": str(e)}
    
    async def _get_postgres_recommendations(self) -> List[Dict[str, Any]]:
        """Get PostgreSQL recommendations for report."""
        try:
            recommendations = await self.postgres_optimizer.analyze_query_performance()
            return [rec.__dict__ for rec in recommendations]
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []
    
    async def generate_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "postgres_stats": {},
            "clickhouse_stats": {},
            "recommendations": []
        }
        
        # Get PostgreSQL stats and recommendations
        postgres_stats = await self._get_postgres_statistics()
        postgres_recommendations = await self._get_postgres_recommendations()
        
        report["postgres_stats"] = postgres_stats
        report["recommendations"] = postgres_recommendations
        
        return report


class DatabaseIndexManager:
    """Unified database index management."""
    
    def __init__(self):
        self.postgres_optimizer = PostgreSQLIndexOptimizer()
        self.clickhouse_optimizer = ClickHouseIndexOptimizer()
        self.optimization_runner = DatabaseOptimizationRunner(
            self.postgres_optimizer, self.clickhouse_optimizer
        )
        self.report_generator = DatabaseReportGenerator(self.postgres_optimizer)
    
    async def optimize_all_databases(self) -> Dict[str, Any]:
        """Run optimization on all databases."""
        logger.info("Starting database optimization across all databases")
        
        results = await self.optimization_runner.run_all_optimizations()
        
        # Log summary
        postgres_success = "error" not in results.get("postgres", {})
        clickhouse_success = "error" not in results.get("clickhouse", {})
        
        logger.info(f"Database optimization completed - PostgreSQL: {postgres_success}, ClickHouse: {clickhouse_success}")
        
        return results
    
    async def get_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        logger.info("Generating database optimization report")
        return await self.report_generator.generate_optimization_report()
    
    async def create_postgres_indexes_only(self) -> Dict[str, bool]:
        """Create PostgreSQL indexes only."""
        logger.info("Creating PostgreSQL performance indexes only")
        return await self.postgres_optimizer.create_performance_indexes()
    
    async def optimize_clickhouse_only(self) -> Dict[str, Any]:
        """Optimize ClickHouse only."""
        logger.info("Running ClickHouse optimizations only")
        return await self.clickhouse_optimizer.get_optimization_summary()


# Global instance for backward compatibility
index_manager = DatabaseIndexManager()