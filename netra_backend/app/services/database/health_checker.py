"""Database Connection Health Checker Module

Performs periodic health checks on database connections.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from netra_backend.app.logging_config import central_logger

# DatabaseManager import removed - using SSOT database module instead

logger = central_logger.get_logger(__name__)

class ConnectionHealthChecker:
    """Perform periodic health checks on database connections"""
    
    def __init__(self, metrics, database_manager=None) -> None:
        self.metrics = metrics
        self._database_manager = database_manager
        self._running = False
        self._check_interval = 60  # 1 minute
        self._monitoring_task = None
        
    async def start_monitoring(self) -> None:
        """Start periodic monitoring"""
        self._running = True
        logger.info("Starting database connection monitoring")
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        # Return immediately instead of awaiting the loop
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self._running:
            await self._perform_check_safely()
            await asyncio.sleep(self._check_interval)
    
    async def _perform_check_safely(self) -> None:
        """Perform health check with error handling"""
        try:
            await self.perform_health_check()
        except Exception as e:
            logger.error(f"Error in health check monitoring: {e}")
    
    def stop_monitoring(self) -> None:
        """Stop periodic monitoring"""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
        logger.info("Stopping database connection monitoring")
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check"""
        health_check = self._init_health_check()
        await self._run_health_checks(health_check)
        self._assess_health(health_check)
        return health_check
    
    def _init_health_check(self) -> Dict[str, Any]:
        """Initialize health check dictionary"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pool_status": None,
            "connectivity_test": None,
            "performance_test": None,
            "overall_health": "unknown"
        }
    
    async def _run_health_checks(self, health_check: Dict[str, Any]) -> None:
        """Run all health check components"""
        try:
            health_check["pool_status"] = self.metrics.get_pool_status()
            health_check["connectivity_test"] = await self._test_connectivity()
            health_check["performance_test"] = await self._test_performance()
        except Exception as e:
            self._handle_check_error(health_check, e)
    
    def _handle_check_error(self, health_check: Dict[str, Any], error: Exception) -> None:
        """Handle health check errors"""
        logger.error(f"Error performing health check: {error}")
        health_check["error"] = str(error)
        health_check["overall_health"] = "error"
    
    def _assess_health(self, health_check: Dict[str, Any]) -> None:
        """Assess overall health status"""
        if "error" not in health_check:
            health_check["overall_health"] = self._assess_overall_health(health_check)
    
    async def _test_connectivity(self) -> Dict[str, Any]:
        """Test basic database connectivity"""
        test_result = self._init_test_result()
        await self._run_connectivity_test(test_result)
        return test_result
    
    def _init_test_result(self) -> Dict[str, Any]:
        """Initialize test result dictionary"""
        return {
            "status": "unknown",
            "response_time_ms": None,
            "error": None
        }
    
    async def _run_connectivity_test(self, test_result: Dict[str, Any]) -> None:
        """Execute connectivity test"""
        try:
            start_time = time.time()
            await self._execute_test_query()
            self._record_success(test_result, start_time)
        except Exception as e:
            self._record_failure(test_result, e, "Connectivity")
    
    async def _execute_test_query(self) -> None:
        """Execute a simple test query"""
        try:
            # Get or create engine
            engine = await self._get_or_create_engine()
            try:
                # Add timeout to prevent hanging
                async with engine.begin() as conn:
                    result = await asyncio.wait_for(
                        conn.execute(text("SELECT 1")), 
                        timeout=10.0
                    )
                    result.fetchone()
            finally:
                # Always dispose of the engine to free resources
                await engine.dispose()
        except asyncio.TimeoutError:
            logger.error("Database health check query timed out after 10 seconds")
            raise
        except Exception as e:
            if "sslmode" in str(e):
                logger.error(f"CRITICAL: Health checker detected sslmode error - this indicates URL conversion was bypassed: {e}")
            raise
    
    def _record_success(self, test_result: Dict[str, Any], start_time: float) -> None:
        """Record successful test result"""
        end_time = time.time()
        test_result["response_time_ms"] = round((end_time - start_time) * 1000, 2)
        test_result["status"] = "healthy"
    
    def _record_failure(self, test_result: Dict[str, Any], error: Exception, 
                       test_type: str) -> None:
        """Record failed test result"""
        test_result["status"] = "failed"
        test_result["error"] = str(error)
        logger.error(f"{test_type} test failed: {error}")
    
    async def _test_performance(self) -> Dict[str, Any]:
        """Test database performance"""
        test_result = self._init_performance_result()
        await self._run_performance_test(test_result)
        return test_result
    
    def _init_performance_result(self) -> Dict[str, Any]:
        """Initialize performance test result"""
        return {
            "status": "unknown",
            "avg_response_time_ms": None,
            "max_response_time_ms": None,
            "error": None
        }
    
    async def _run_performance_test(self, test_result: Dict[str, Any]) -> None:
        """Execute performance test"""
        try:
            response_times = await self._execute_performance_queries()
            self._analyze_performance(test_result, response_times)
        except Exception as e:
            self._record_failure(test_result, e, "Performance")
    
    async def _execute_performance_queries(self) -> list:
        """Execute multiple test queries"""
        response_times = []
        test_queries = self._get_test_queries()
        
        # Get or create engine
        engine = await self._get_or_create_engine()
        try:
            for query in test_queries:
                response_time = await self._time_query_with_engine(query, engine)
                response_times.append(response_time)
        finally:
            # Always dispose of the engine to free resources
            await engine.dispose()
        
        return response_times
    
    def _get_test_queries(self) -> list:
        """Get list of test queries"""
        return [
            text("SELECT 1"),
            text("SELECT NOW()"),
            text("SELECT COUNT(*) FROM information_schema.tables")
        ]
    
    async def _get_or_create_engine(self) -> AsyncEngine:
        """Get or create database engine for health checks using SSOT database module"""
        # Use SSOT database module for engine access
        from netra_backend.app.database import get_engine
        return get_engine()
    
    async def _time_query(self, query) -> float:
        """Time a single query execution"""
        # Get or create engine
        engine = await self._get_or_create_engine()
        try:
            start_time = time.time()
            async with engine.begin() as conn:
                result = await conn.execute(query)
                result.fetchall()
            end_time = time.time()
            return (end_time - start_time) * 1000
        finally:
            await engine.dispose()
    
    async def _time_query_with_engine(self, query, engine) -> float:
        """Time a single query execution with provided engine"""
        start_time = time.time()
        async with engine.begin() as conn:
            result = await conn.execute(query)
            result.fetchall()
        end_time = time.time()
        return (end_time - start_time) * 1000
    
    def _analyze_performance(self, test_result: Dict[str, Any], 
                            response_times: list) -> None:
        """Analyze performance test results"""
        if not response_times:
            return
        
        self._calculate_performance_metrics(test_result, response_times)
        self._assess_performance_status(test_result)
    
    def _calculate_performance_metrics(self, test_result: Dict[str, Any], 
                                      response_times: list) -> None:
        """Calculate performance metrics"""
        test_result["avg_response_time_ms"] = round(sum(response_times) / len(response_times), 2)
        test_result["max_response_time_ms"] = round(max(response_times), 2)
    
    def _assess_performance_status(self, test_result: Dict[str, Any]) -> None:
        """Assess performance status based on metrics"""
        max_time = test_result.get("max_response_time_ms", 0)
        avg_time = test_result.get("avg_response_time_ms", 0)
        
        if max_time > 5000:  # 5 seconds
            test_result["status"] = "slow"
        elif avg_time > 1000:  # 1 second
            test_result["status"] = "degraded"
        else:
            test_result["status"] = "healthy"
    
    def _assess_overall_health(self, health_check: Dict[str, Any]) -> str:
        """Assess overall system health"""
        statuses = self._extract_health_statuses(health_check)
        return self._determine_overall_status(statuses)
    
    def _extract_health_statuses(self, health_check: Dict[str, Any]) -> Dict[str, str]:
        """Extract individual health statuses"""
        return {
            "pool": health_check.get("pool_status", {}).get("health", "unknown"),
            "connectivity": health_check.get("connectivity_test", {}).get("status", "unknown"),
            "performance": health_check.get("performance_test", {}).get("status", "unknown")
        }
    
    def _determine_overall_status(self, statuses: Dict[str, str]) -> str:
        """Determine overall status from individual statuses"""
        if self._has_critical_issues(statuses):
            return "critical"
        if self._has_warnings(statuses):
            return "warning"
        if self._all_healthy(statuses):
            return "healthy"
        return "unknown"
    
    def _has_critical_issues(self, statuses: Dict[str, str]) -> bool:
        """Check for critical issues"""
        return ("failed" in statuses.values() or 
                statuses["pool"] == "critical")
    
    def _has_warnings(self, statuses: Dict[str, str]) -> bool:
        """Check for warnings"""
        return ("slow" in statuses.values() or 
                "degraded" in statuses.values() or 
                statuses["pool"] == "warning")
    
    def _all_healthy(self, statuses: Dict[str, str]) -> bool:
        """Check if all components are healthy"""
        return all(status == "healthy" for status in statuses.values())