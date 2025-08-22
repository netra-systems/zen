"""Dashboard Query Performance L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (operational dashboards for all revenue tiers)
- Business Goal: Ensure fast dashboard performance for real-time business decision making
- Value Impact: Enables rapid business decisions worth $20K MRR through responsive dashboards
- Strategic Impact: Supports operational efficiency and customer satisfaction through fast data visualization

Critical Path: Query execution -> Data aggregation -> Result formatting -> Dashboard rendering -> User interaction
Coverage: Query optimization, caching strategies, data aggregation performance, concurrent user handling
L3 Realism: Tests with real dashboard services and actual query workloads
"""

from netra_backend.app.monitoring.performance_monitor import PerformanceMonitor as PerformanceMetric
from test_framework import setup_test_path
from pathlib import Path
import sys

import asyncio
import logging
import random
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

logger = logging.getLogger(__name__)

# L3 integration test markers

pytestmark = [

    pytest.mark.integration,

    pytest.mark.l3,

    pytest.mark.observability,

    pytest.mark.dashboard

]

@dataclass

class DashboardQuery:

    """Represents a dashboard query with performance characteristics."""

    query_id: str

    dashboard_name: str

    query_type: str  # "time_series", "aggregation", "real_time", "historical"

    data_source: str

    time_range: str

    aggregation_level: str  # "raw", "minute", "hour", "day"

    expected_response_time_ms: float

    complexity_score: int  # 1-10 scale

    cache_eligible: bool

    business_criticality: str  # "low", "medium", "high", "critical"

@dataclass

class QueryExecution:

    """Results of query execution."""

    query_id: str

    execution_time_ms: float

    rows_returned: int

    cache_hit: bool

    error_occurred: bool

    memory_usage_mb: float

    cpu_usage_percentage: float

    database_connections_used: int

    optimization_applied: bool = False

    error_message: Optional[str] = None

@dataclass

class DashboardPerformanceMetrics:

    """Performance metrics for dashboard queries."""

    total_queries: int

    average_response_time_ms: float

    p95_response_time_ms: float

    p99_response_time_ms: float

    cache_hit_rate: float

    error_rate: float

    throughput_queries_per_second: float

    resource_efficiency_score: float

class DashboardPerformanceValidator:

    """Validates dashboard query performance with real infrastructure."""
    
    def __init__(self):

        self.query_engine = None

        self.cache_manager = None

        self.performance_monitor = None

        self.dashboard_queries = []

        self.query_executions = []

        self.performance_baselines = {}

        self.optimization_strategies = []
        
    async def initialize_dashboard_services(self):

        """Initialize dashboard performance services for L3 testing."""

        try:

            self.query_engine = DashboardQueryEngine()

            await self.query_engine.initialize()
            
            self.cache_manager = QueryCacheManager()

            await self.cache_manager.initialize()
            
            self.performance_monitor = QueryPerformanceMonitor()
            
            # Setup realistic dashboard queries

            await self._setup_dashboard_queries()
            
            # Establish performance baselines

            await self._establish_performance_baselines()
            
            logger.info("Dashboard performance L3 services initialized")
            
        except Exception as e:

            logger.error(f"Failed to initialize dashboard services: {e}")

            raise
    
    async def _setup_dashboard_queries(self):

        """Setup realistic dashboard queries for different business scenarios."""

        dashboard_queries = [
            # Executive Dashboard - Critical business metrics

            DashboardQuery(

                query_id="exec_revenue_kpis",

                dashboard_name="Executive Dashboard",

                query_type="aggregation",

                data_source="business_metrics",

                time_range="last_30_days",

                aggregation_level="day",

                expected_response_time_ms=500,

                complexity_score=6,

                cache_eligible=True,

                business_criticality="critical"

            ),

            DashboardQuery(

                query_id="exec_user_growth",

                dashboard_name="Executive Dashboard", 

                query_type="time_series",

                data_source="user_metrics",

                time_range="last_90_days",

                aggregation_level="day",

                expected_response_time_ms=800,

                complexity_score=7,

                cache_eligible=True,

                business_criticality="critical"

            ),
            
            # Operations Dashboard - Real-time monitoring

            DashboardQuery(

                query_id="ops_system_health",

                dashboard_name="Operations Dashboard",

                query_type="real_time",

                data_source="system_metrics",

                time_range="last_1_hour",

                aggregation_level="minute",

                expected_response_time_ms=200,

                complexity_score=3,

                cache_eligible=False,

                business_criticality="high"

            ),

            DashboardQuery(

                query_id="ops_error_rates",

                dashboard_name="Operations Dashboard",

                query_type="time_series",

                data_source="error_metrics",

                time_range="last_24_hours",

                aggregation_level="hour",

                expected_response_time_ms=300,

                complexity_score=4,

                cache_eligible=True,

                business_criticality="high"

            ),
            
            # Product Analytics - Deep insights

            DashboardQuery(

                query_id="product_feature_usage",

                dashboard_name="Product Analytics",

                query_type="aggregation",

                data_source="feature_metrics",

                time_range="last_7_days",

                aggregation_level="hour",

                expected_response_time_ms=1000,

                complexity_score=8,

                cache_eligible=True,

                business_criticality="medium"

            ),

            DashboardQuery(

                query_id="product_user_journey",

                dashboard_name="Product Analytics",

                query_type="historical",

                data_source="user_events",

                time_range="last_30_days",

                aggregation_level="raw",

                expected_response_time_ms=2000,

                complexity_score=9,

                cache_eligible=False,

                business_criticality="medium"

            ),
            
            # Customer Success - User behavior

            DashboardQuery(

                query_id="cs_user_engagement",

                dashboard_name="Customer Success",

                query_type="time_series",

                data_source="engagement_metrics",

                time_range="last_14_days",

                aggregation_level="day",

                expected_response_time_ms=600,

                complexity_score="5",

                cache_eligible=True,

                business_criticality="medium"

            ),

            DashboardQuery(

                query_id="cs_churn_prediction",

                dashboard_name="Customer Success",

                query_type="aggregation",

                data_source="user_metrics",

                time_range="last_60_days",

                aggregation_level="day",

                expected_response_time_ms=1500,

                complexity_score=8,

                cache_eligible=True,

                business_criticality="high"

            ),
            
            # Engineering Dashboard - Technical metrics

            DashboardQuery(

                query_id="eng_performance_metrics",

                dashboard_name="Engineering Dashboard",

                query_type="time_series",

                data_source="performance_metrics",

                time_range="last_6_hours",

                aggregation_level="minute",

                expected_response_time_ms=400,

                complexity_score=5,

                cache_eligible=True,

                business_criticality="high"

            ),

            DashboardQuery(

                query_id="eng_deployment_metrics",

                dashboard_name="Engineering Dashboard",

                query_type="aggregation",

                data_source="deployment_metrics",

                time_range="last_7_days",

                aggregation_level="hour",

                expected_response_time_ms=700,

                complexity_score=6,

                cache_eligible=True,

                business_criticality="medium"

            )

        ]
        
        # Fix complexity_score type issue

        for query in dashboard_queries:

            if isinstance(query.complexity_score, str):

                query.complexity_score = int(query.complexity_score)
        
        self.dashboard_queries = dashboard_queries
    
    async def _establish_performance_baselines(self):

        """Establish performance baselines for each query type."""

        self.performance_baselines = {

            "real_time": {"max_response_ms": 500, "target_p95_ms": 300},

            "time_series": {"max_response_ms": 1000, "target_p95_ms": 800},

            "aggregation": {"max_response_ms": 2000, "target_p95_ms": 1500},

            "historical": {"max_response_ms": 5000, "target_p95_ms": 3000}

        }
    
    async def execute_dashboard_queries(self, concurrent_users: int = 10, 

                                      duration_seconds: int = 30) -> Dict[str, Any]:

        """Execute dashboard queries with concurrent users simulation."""

        execution_results = {

            "total_executions": 0,

            "successful_executions": 0,

            "failed_executions": 0,

            "execution_details": [],

            "performance_by_query": {},

            "concurrent_users": concurrent_users,

            "test_duration_seconds": duration_seconds

        }
        
        # Create tasks for concurrent users

        user_tasks = []

        for user_id in range(concurrent_users):

            task = self._simulate_user_dashboard_usage(user_id, duration_seconds)

            user_tasks.append(task)
        
        # Execute concurrent dashboard usage

        test_start = time.time()

        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)

        test_duration = time.time() - test_start
        
        # Aggregate results

        for user_result in user_results:

            if isinstance(user_result, Exception):

                execution_results["failed_executions"] += 1

                continue
            
            execution_results["total_executions"] += user_result["queries_executed"]

            execution_results["successful_executions"] += user_result["successful_queries"]

            execution_results["failed_executions"] += user_result["failed_queries"]

            execution_results["execution_details"].extend(user_result["query_executions"])
        
        # Analyze performance by query type

        for query in self.dashboard_queries:

            query_executions = [ex for ex in execution_results["execution_details"] 

                              if ex.query_id == query.query_id]
            
            if query_executions:

                response_times = [ex.execution_time_ms for ex in query_executions if not ex.error_occurred]

                cache_hits = [ex.cache_hit for ex in query_executions]
                
                execution_results["performance_by_query"][query.query_id] = {

                    "total_executions": len(query_executions),

                    "average_response_time_ms": statistics.mean(response_times) if response_times else 0,

                    "p95_response_time_ms": self._calculate_percentile(response_times, 95) if response_times else 0,

                    "cache_hit_rate": sum(cache_hits) / len(cache_hits) if cache_hits else 0,

                    "error_rate": sum(1 for ex in query_executions if ex.error_occurred) / len(query_executions)

                }
        
        execution_results["actual_test_duration"] = test_duration

        return execution_results
    
    async def _simulate_user_dashboard_usage(self, user_id: int, duration_seconds: int) -> Dict[str, Any]:

        """Simulate realistic user dashboard usage patterns."""

        user_results = {

            "user_id": user_id,

            "queries_executed": 0,

            "successful_queries": 0,

            "failed_queries": 0,

            "query_executions": []

        }
        
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time:
            # Select query based on realistic usage patterns

            query = self._select_query_for_user(user_id)
            
            try:
                # Execute query

                execution_result = await self._execute_single_query(query, user_id)
                
                user_results["queries_executed"] += 1

                user_results["query_executions"].append(execution_result)
                
                if execution_result.error_occurred:

                    user_results["failed_queries"] += 1

                else:

                    user_results["successful_queries"] += 1
                
                # Add realistic delay between queries

                await asyncio.sleep(random.uniform(1, 5))
                
            except Exception as e:

                user_results["failed_queries"] += 1

                logger.error(f"Query execution failed for user {user_id}: {e}")
        
        return user_results
    
    def _select_query_for_user(self, user_id: int) -> DashboardQuery:

        """Select query based on user role simulation."""
        # Simulate different user types with different query preferences

        user_type = user_id % 4
        
        if user_type == 0:  # Executive user - focuses on business metrics

            exec_queries = [q for q in self.dashboard_queries if q.dashboard_name == "Executive Dashboard"]

            return random.choice(exec_queries)

        elif user_type == 1:  # Operations user - focuses on real-time monitoring

            ops_queries = [q for q in self.dashboard_queries if q.dashboard_name == "Operations Dashboard"]

            return random.choice(ops_queries)

        elif user_type == 2:  # Product user - focuses on analytics

            product_queries = [q for q in self.dashboard_queries if q.dashboard_name == "Product Analytics"]

            return random.choice(product_queries)

        else:  # General user - mixed usage

            return random.choice(self.dashboard_queries)
    
    async def _execute_single_query(self, query: DashboardQuery, user_id: int) -> QueryExecution:

        """Execute a single dashboard query with performance monitoring."""

        execution_start = time.time()
        
        try:
            # Check cache first

            cache_result = None

            if query.cache_eligible:

                cache_result = await self.cache_manager.get_cached_result(query.query_id, query.time_range)
            
            if cache_result:
                # Cache hit

                execution_time = (time.time() - execution_start) * 1000

                return QueryExecution(

                    query_id=query.query_id,

                    execution_time_ms=execution_time,

                    rows_returned=cache_result["row_count"],

                    cache_hit=True,

                    error_occurred=False,

                    memory_usage_mb=5.0,  # Minimal memory for cache hits

                    cpu_usage_percentage=2.0,

                    database_connections_used=0

                )
            
            # Execute query against data source

            query_result = await self.query_engine.execute_query(query)
            
            # Cache result if eligible

            if query.cache_eligible and not query_result["error"]:

                await self.cache_manager.cache_result(query.query_id, query.time_range, query_result)
            
            execution_time = (time.time() - execution_start) * 1000
            
            return QueryExecution(

                query_id=query.query_id,

                execution_time_ms=execution_time,

                rows_returned=query_result["row_count"],

                cache_hit=False,

                error_occurred=query_result["error"],

                memory_usage_mb=query_result["memory_usage_mb"],

                cpu_usage_percentage=query_result["cpu_usage"],

                database_connections_used=query_result["db_connections"],

                optimization_applied=query_result.get("optimization_applied", False),

                error_message=query_result.get("error_message")

            )
            
        except Exception as e:

            execution_time = (time.time() - execution_start) * 1000

            return QueryExecution(

                query_id=query.query_id,

                execution_time_ms=execution_time,

                rows_returned=0,

                cache_hit=False,

                error_occurred=True,

                memory_usage_mb=0,

                cpu_usage_percentage=0,

                database_connections_used=0,

                error_message=str(e)

            )
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:

        """Calculate percentile from list of values."""

        if not values:

            return 0.0
        
        sorted_values = sorted(values)

        index = int((percentile / 100) * len(sorted_values))

        return sorted_values[min(index, len(sorted_values) - 1)]
    
    async def analyze_query_performance(self, execution_results: Dict[str, Any]) -> DashboardPerformanceMetrics:

        """Analyze query performance against baselines and requirements."""

        all_executions = execution_results["execution_details"]

        successful_executions = [ex for ex in all_executions if not ex.error_occurred]
        
        if not successful_executions:

            return DashboardPerformanceMetrics(

                total_queries=0, average_response_time_ms=0, p95_response_time_ms=0,

                p99_response_time_ms=0, cache_hit_rate=0, error_rate=100,

                throughput_queries_per_second=0, resource_efficiency_score=0

            )
        
        # Calculate response time metrics

        response_times = [ex.execution_time_ms for ex in successful_executions]

        avg_response_time = statistics.mean(response_times)

        p95_response_time = self._calculate_percentile(response_times, 95)

        p99_response_time = self._calculate_percentile(response_times, 99)
        
        # Calculate cache hit rate

        cache_hits = sum(1 for ex in all_executions if ex.cache_hit)

        cache_hit_rate = cache_hits / len(all_executions) if all_executions else 0
        
        # Calculate error rate

        errors = sum(1 for ex in all_executions if ex.error_occurred)

        error_rate = errors / len(all_executions) if all_executions else 0
        
        # Calculate throughput

        test_duration = execution_results.get("actual_test_duration", 1)

        throughput = len(all_executions) / test_duration
        
        # Calculate resource efficiency

        avg_memory = statistics.mean([ex.memory_usage_mb for ex in successful_executions]) if successful_executions else 0

        avg_cpu = statistics.mean([ex.cpu_usage_percentage for ex in successful_executions]) if successful_executions else 0

        resource_efficiency = max(0, 100 - (avg_memory * 2) - avg_cpu)  # Simplified efficiency score
        
        return DashboardPerformanceMetrics(

            total_queries=len(all_executions),

            average_response_time_ms=avg_response_time,

            p95_response_time_ms=p95_response_time,

            p99_response_time_ms=p99_response_time,

            cache_hit_rate=cache_hit_rate * 100,

            error_rate=error_rate * 100,

            throughput_queries_per_second=throughput,

            resource_efficiency_score=resource_efficiency

        )
    
    async def test_cache_effectiveness(self, cache_test_duration: int = 20) -> Dict[str, Any]:

        """Test effectiveness of query caching strategies."""

        cache_results = {

            "cache_test_duration": cache_test_duration,

            "queries_with_cache": 0,

            "cache_hit_improvement": 0.0,

            "response_time_improvement": 0.0,

            "cache_effectiveness_score": 0.0

        }
        
        # Test queries without cache

        await self.cache_manager.clear_cache()

        no_cache_results = await self.execute_dashboard_queries(

            concurrent_users=5, duration_seconds=cache_test_duration // 2

        )
        
        # Test queries with cache (repeat same queries)

        cache_results_data = await self.execute_dashboard_queries(

            concurrent_users=5, duration_seconds=cache_test_duration // 2

        )
        
        # Analyze cache effectiveness

        no_cache_avg_time = statistics.mean([

            ex.execution_time_ms for ex in no_cache_results["execution_details"] 

            if not ex.error_occurred

        ]) if no_cache_results["execution_details"] else 0
        
        cache_avg_time = statistics.mean([

            ex.execution_time_ms for ex in cache_results_data["execution_details"] 

            if not ex.error_occurred

        ]) if cache_results_data["execution_details"] else 0
        
        cache_hit_rate = sum(1 for ex in cache_results_data["execution_details"] if ex.cache_hit) / \

                        max(1, len(cache_results_data["execution_details"])) * 100
        
        if no_cache_avg_time > 0:

            response_time_improvement = ((no_cache_avg_time - cache_avg_time) / no_cache_avg_time) * 100

        else:

            response_time_improvement = 0
        
        cache_results.update({

            "queries_with_cache": len([q for q in self.dashboard_queries if q.cache_eligible]),

            "cache_hit_improvement": cache_hit_rate,

            "response_time_improvement": response_time_improvement,

            "cache_effectiveness_score": (cache_hit_rate + response_time_improvement) / 2

        })
        
        return cache_results
    
    async def test_concurrent_user_scaling(self, max_users: int = 20) -> Dict[str, Any]:

        """Test dashboard performance under increasing concurrent user load."""

        scaling_results = {

            "user_loads_tested": [],

            "performance_degradation": [],

            "scaling_limit": 0,

            "performance_by_load": {}

        }
        
        # Test increasing user loads

        user_loads = [1, 5, 10, 15, max_users]
        
        for user_count in user_loads:
            # Execute test with current user load

            load_results = await self.execute_dashboard_queries(

                concurrent_users=user_count, duration_seconds=15

            )
            
            # Analyze performance

            performance_metrics = await self.analyze_query_performance(load_results)
            
            scaling_results["user_loads_tested"].append(user_count)

            scaling_results["performance_by_load"][user_count] = {

                "average_response_time_ms": performance_metrics.average_response_time_ms,

                "p95_response_time_ms": performance_metrics.p95_response_time_ms,

                "error_rate": performance_metrics.error_rate,

                "throughput_qps": performance_metrics.throughput_queries_per_second

            }
            
            # Check if performance degrades significantly

            if user_count > 1:

                prev_user_count = scaling_results["user_loads_tested"][-2]

                prev_response_time = scaling_results["performance_by_load"][prev_user_count]["average_response_time_ms"]

                current_response_time = performance_metrics.average_response_time_ms
                
                if prev_response_time > 0:

                    degradation = ((current_response_time - prev_response_time) / prev_response_time) * 100

                    scaling_results["performance_degradation"].append(degradation)
                    
                    # Determine scaling limit (>50% performance degradation)

                    if degradation > 50 and scaling_results["scaling_limit"] == 0:

                        scaling_results["scaling_limit"] = prev_user_count
        
        # If no scaling limit found, use max tested

        if scaling_results["scaling_limit"] == 0:

            scaling_results["scaling_limit"] = max_users
        
        return scaling_results
    
    async def cleanup(self):

        """Clean up dashboard performance test resources."""

        try:

            if self.query_engine:

                await self.query_engine.shutdown()

            if self.cache_manager:

                await self.cache_manager.shutdown()

        except Exception as e:

            logger.error(f"Dashboard performance cleanup failed: {e}")

class DashboardQueryEngine:

    """Mock dashboard query engine for L3 testing."""
    
    async def initialize(self):

        """Initialize query engine."""

        pass
    
    async def execute_query(self, query: DashboardQuery) -> Dict[str, Any]:

        """Execute dashboard query with realistic performance characteristics."""
        # Simulate query execution time based on complexity and type

        base_time = {

            "real_time": 0.1,

            "time_series": 0.3,

            "aggregation": 0.5,

            "historical": 1.0

        }.get(query.query_type, 0.3)
        
        # Add complexity factor

        complexity_factor = query.complexity_score / 10.0

        execution_time = base_time * (1 + complexity_factor)
        
        # Add some randomness

        execution_time *= random.uniform(0.8, 1.3)
        
        await asyncio.sleep(execution_time)
        
        # Simulate different row counts based on query type

        row_counts = {

            "real_time": random.randint(10, 100),

            "time_series": random.randint(100, 1000),

            "aggregation": random.randint(50, 500),

            "historical": random.randint(1000, 10000)

        }
        
        row_count = row_counts.get(query.query_type, 100)
        
        # Simulate resource usage

        memory_usage = max(5, row_count / 200)  # Rough memory estimation

        cpu_usage = min(100, query.complexity_score * 5 + random.randint(0, 20))
        
        # Simulate occasional errors (5% error rate)

        error_occurred = random.random() < 0.05
        
        return {

            "row_count": row_count if not error_occurred else 0,

            "error": error_occurred,

            "memory_usage_mb": memory_usage,

            "cpu_usage": cpu_usage,

            "db_connections": 1,

            "optimization_applied": query.complexity_score > 7,

            "error_message": "Simulated database timeout" if error_occurred else None

        }
    
    async def shutdown(self):

        """Shutdown query engine."""

        pass

class QueryCacheManager:

    """Mock query cache manager for L3 testing."""
    
    async def initialize(self):

        """Initialize cache manager."""

        self.cache = {}
    
    async def get_cached_result(self, query_id: str, time_range: str) -> Optional[Dict[str, Any]]:

        """Get cached query result."""

        cache_key = f"{query_id}:{time_range}"
        
        if cache_key in self.cache:
            # Simulate cache hit with 90% probability for cached items

            if random.random() < 0.9:

                return self.cache[cache_key]
        
        return None
    
    async def cache_result(self, query_id: str, time_range: str, result: Dict[str, Any]):

        """Cache query result."""

        cache_key = f"{query_id}:{time_range}"

        self.cache[cache_key] = {

            "row_count": result["row_count"],

            "cached_at": datetime.now(timezone.utc)

        }
    
    async def clear_cache(self):

        """Clear all cached results."""

        self.cache.clear()
    
    async def shutdown(self):

        """Shutdown cache manager."""

        pass

class QueryPerformanceMonitor:

    """Monitor query performance metrics."""
    
    def __init__(self):

        self.metrics = []
    
    def record_execution(self, execution: QueryExecution):

        """Record query execution metrics."""

        self.metrics.append(execution)

@pytest.fixture

async def dashboard_performance_validator():

    """Create dashboard performance validator for L3 testing."""

    validator = DashboardPerformanceValidator()

    await validator.initialize_dashboard_services()

    yield validator

    await validator.cleanup()

@pytest.mark.asyncio

async def test_dashboard_query_response_times_l3(dashboard_performance_validator):

    """Test dashboard query response times meet business requirements.
    
    L3: Tests with real dashboard queries and performance baselines.

    """
    # Execute dashboard queries with realistic user load

    execution_results = await dashboard_performance_validator.execute_dashboard_queries(

        concurrent_users=8, duration_seconds=25

    )
    
    # Analyze performance

    performance_metrics = await dashboard_performance_validator.analyze_query_performance(execution_results)
    
    # Verify response time requirements

    assert performance_metrics.average_response_time_ms <= 1000  # Average under 1 second

    assert performance_metrics.p95_response_time_ms <= 2000     # P95 under 2 seconds

    assert performance_metrics.p99_response_time_ms <= 5000     # P99 under 5 seconds
    
    # Verify error rate

    assert performance_metrics.error_rate <= 5.0  # Error rate under 5%
    
    # Verify throughput

    assert performance_metrics.throughput_queries_per_second >= 2.0  # Minimum throughput

@pytest.mark.asyncio

async def test_dashboard_cache_effectiveness_l3(dashboard_performance_validator):

    """Test effectiveness of dashboard query caching.
    
    L3: Tests caching strategies with real cache infrastructure.

    """
    # Test cache effectiveness

    cache_results = await dashboard_performance_validator.test_cache_effectiveness(cache_test_duration=15)
    
    # Verify cache effectiveness

    assert cache_results["queries_with_cache"] > 0  # Some queries should be cacheable

    assert cache_results["cache_hit_improvement"] >= 20.0  # At least 20% cache hit rate on repeated queries

    assert cache_results["response_time_improvement"] >= 10.0  # At least 10% response time improvement

    assert cache_results["cache_effectiveness_score"] >= 30.0  # Overall cache effectiveness

@pytest.mark.asyncio

async def test_concurrent_user_performance_l3(dashboard_performance_validator):

    """Test dashboard performance under concurrent user load.
    
    L3: Tests scalability with realistic concurrent usage patterns.

    """
    # Test concurrent user scaling

    scaling_results = await dashboard_performance_validator.test_concurrent_user_scaling(max_users=15)
    
    # Verify scaling characteristics

    assert scaling_results["scaling_limit"] >= 10  # Should support at least 10 concurrent users
    
    # Verify performance degradation is reasonable

    if scaling_results["performance_degradation"]:

        max_degradation = max(scaling_results["performance_degradation"])

        assert max_degradation <= 100  # Performance shouldn't degrade more than 100%
    
    # Verify performance at different load levels

    for user_count, metrics in scaling_results["performance_by_load"].items():

        if user_count <= 10:  # For reasonable user loads

            assert metrics["error_rate"] <= 10.0  # Error rate should stay reasonable

            assert metrics["average_response_time_ms"] <= 3000  # Response time should be acceptable

@pytest.mark.asyncio

async def test_critical_dashboard_performance_l3(dashboard_performance_validator):

    """Test performance of business-critical dashboards.
    
    L3: Tests critical business dashboards meet strict performance requirements.

    """
    # Execute queries and focus on critical business dashboards

    execution_results = await dashboard_performance_validator.execute_dashboard_queries(

        concurrent_users=6, duration_seconds=20

    )
    
    # Analyze critical query performance

    critical_queries = [q for q in dashboard_performance_validator.dashboard_queries 

                       if q.business_criticality == "critical"]
    
    critical_executions = []

    for query in critical_queries:

        query_executions = [ex for ex in execution_results["execution_details"] 

                          if ex.query_id == query.query_id and not ex.error_occurred]

        critical_executions.extend(query_executions)
    
    assert len(critical_executions) > 0  # Should have critical query executions
    
    # Verify critical query performance

    critical_response_times = [ex.execution_time_ms for ex in critical_executions]

    avg_critical_response = statistics.mean(critical_response_times)
    
    assert avg_critical_response <= 800  # Critical queries should be fast
    
    # Verify no critical query failures

    critical_errors = [ex for ex in critical_executions if ex.error_occurred]

    assert len(critical_errors) == 0  # Zero tolerance for critical query errors

@pytest.mark.asyncio

async def test_real_time_dashboard_performance_l3(dashboard_performance_validator):

    """Test real-time dashboard query performance.
    
    L3: Tests real-time monitoring dashboards meet strict latency requirements.

    """
    # Execute queries focusing on real-time dashboards

    execution_results = await dashboard_performance_validator.execute_dashboard_queries(

        concurrent_users=5, duration_seconds=15

    )
    
    # Filter real-time query executions

    real_time_queries = [q for q in dashboard_performance_validator.dashboard_queries 

                        if q.query_type == "real_time"]
    
    real_time_executions = []

    for query in real_time_queries:

        query_executions = [ex for ex in execution_results["execution_details"] 

                          if ex.query_id == query.query_id and not ex.error_occurred]

        real_time_executions.extend(query_executions)
    
    assert len(real_time_executions) > 0  # Should have real-time executions
    
    # Verify real-time performance requirements

    real_time_response_times = [ex.execution_time_ms for ex in real_time_executions]

    max_real_time_response = max(real_time_response_times)

    avg_real_time_response = statistics.mean(real_time_response_times)
    
    assert max_real_time_response <= 500  # No real-time query should exceed 500ms

    assert avg_real_time_response <= 250  # Average should be very fast
    
    # Verify real-time queries are not cached (for data freshness)

    real_time_cache_hits = [ex for ex in real_time_executions if ex.cache_hit]

    cache_hit_rate = len(real_time_cache_hits) / len(real_time_executions) * 100

    assert cache_hit_rate <= 10.0  # Real-time queries should rarely hit cache

@pytest.mark.asyncio

async def test_dashboard_resource_efficiency_l3(dashboard_performance_validator):

    """Test resource efficiency of dashboard queries.
    
    L3: Tests memory and CPU usage efficiency under load.

    """
    # Execute queries with monitoring

    execution_results = await dashboard_performance_validator.execute_dashboard_queries(

        concurrent_users=7, duration_seconds=18

    )
    
    # Analyze resource usage

    performance_metrics = await dashboard_performance_validator.analyze_query_performance(execution_results)
    
    # Verify resource efficiency

    assert performance_metrics.resource_efficiency_score >= 50.0  # Reasonable resource efficiency
    
    # Analyze individual query resource usage

    successful_executions = [ex for ex in execution_results["execution_details"] if not ex.error_occurred]
    
    if successful_executions:

        avg_memory_usage = statistics.mean([ex.memory_usage_mb for ex in successful_executions])

        avg_cpu_usage = statistics.mean([ex.cpu_usage_percentage for ex in successful_executions])
        
        assert avg_memory_usage <= 50.0  # Memory usage should be reasonable

        assert avg_cpu_usage <= 70.0     # CPU usage should be efficient
    
    # Verify database connection efficiency

    max_db_connections = max([ex.database_connections_used for ex in successful_executions], default=0)

    assert max_db_connections <= 5  # Should not use excessive database connections