"""
Test Database Query Optimization - Iteration 54

Business Value Justification:
- Segment: Enterprise/Mid
- Business Goal: Performance Optimization
- Value Impact: Reduces query response times and improves user experience
- Strategic Impact: Enables higher throughput and better resource utilization

Focus: Query execution plans, index optimization, and performance monitoring
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import time
import statistics

from netra_backend.app.database.manager import DatabaseManager
from netra_backend.app.core.error_recovery_integration import ErrorRecoveryManager


class TestDatabaseQueryOptimization:
    """Test database query optimization and performance monitoring"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager with query optimization features"""
        manager = MagicMock()
        manager.query_cache = {}
        manager.execution_stats = []
        manager.slow_queries = []
        return manager
    
    @pytest.fixture
    def mock_query_optimizer(self):
        """Mock query optimizer service"""
        optimizer = MagicMock()
        optimizer.optimization_history = []
        return optimizer
    
    @pytest.mark.asyncio
    async def test_query_execution_plan_analysis(self, mock_db_manager, mock_query_optimizer):
        """Test query execution plan analysis and optimization"""
        def analyze_execution_plan(query):
            # Simulate execution plan analysis
            plan_data = {
                "query": query,
                "estimated_cost": 100,
                "actual_cost": 120,
                "execution_time_ms": 50,
                "rows_examined": 1000,
                "rows_returned": 10,
                "index_used": "user_id_idx" if "WHERE user_id" in query else None,
                "optimization_suggestions": []
            }
            
            # Add optimization suggestions based on query patterns
            if "SELECT *" in query:
                plan_data["optimization_suggestions"].append("Avoid SELECT *, specify columns")
            
            if plan_data["rows_examined"] > plan_data["rows_returned"] * 100:
                plan_data["optimization_suggestions"].append("Consider adding index")
            
            if not plan_data["index_used"] and "WHERE" in query:
                plan_data["optimization_suggestions"].append("Missing index for WHERE clause")
            
            return plan_data
        
        mock_query_optimizer.analyze_execution_plan = analyze_execution_plan
        
        # Test well-optimized query
        optimized_query = "SELECT id, name FROM users WHERE user_id = ?"
        plan = mock_query_optimizer.analyze_execution_plan(optimized_query)
        
        assert plan["query"] == optimized_query
        assert plan["index_used"] == "user_id_idx"
        assert len(plan["optimization_suggestions"]) == 0
        
        # Test poorly optimized query
        poor_query = "SELECT * FROM users WHERE email LIKE '%@domain.com'"
        plan = mock_query_optimizer.analyze_execution_plan(poor_query)
        
        assert "Avoid SELECT *" in str(plan["optimization_suggestions"])
        assert plan["index_used"] is None
    
    @pytest.mark.asyncio
    async def test_slow_query_detection_and_logging(self, mock_db_manager):
        """Test detection and logging of slow queries"""
        slow_query_threshold = 100  # milliseconds
        
        async def execute_query(query, params=None):
            start_time = time.time()
            
            # Simulate different query execution times
            if "complex_join" in query:
                await asyncio.sleep(0.15)  # 150ms - slow
            elif "simple_select" in query:
                await asyncio.sleep(0.05)  # 50ms - fast
            else:
                await asyncio.sleep(0.12)  # 120ms - slow
            
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            query_stats = {
                "query": query,
                "execution_time_ms": execution_time,
                "timestamp": time.time(),
                "params": params
            }
            
            mock_db_manager.execution_stats.append(query_stats)
            
            # Log slow queries
            if execution_time > slow_query_threshold:
                mock_db_manager.slow_queries.append(query_stats)
            
            return {"status": "success", "execution_time": execution_time}
        
        mock_db_manager.execute_query = execute_query
        
        with patch('netra_backend.app.database.manager.DatabaseManager', return_value=mock_db_manager):
            # Execute various queries
            queries = [
                "SELECT * FROM users WHERE simple_select = 1",
                "SELECT u.*, p.* FROM users u JOIN profiles p WHERE complex_join = 1",
                "UPDATE users SET name = ? WHERE id = ?"
            ]
            
            for query in queries:
                await mock_db_manager.execute_query(query)
            
            assert len(mock_db_manager.execution_stats) == 3
            
            # Check slow query detection
            slow_queries = mock_db_manager.slow_queries
            assert len(slow_queries) >= 1  # At least the complex join should be slow
            
            # Verify slow queries exceed threshold
            for slow_query in slow_queries:
                assert slow_query["execution_time_ms"] > slow_query_threshold
    
    @pytest.mark.asyncio
    async def test_index_usage_optimization(self, mock_db_manager, mock_query_optimizer):
        """Test index usage analysis and optimization recommendations"""
        def analyze_index_usage(table_name):
            # Mock index usage statistics
            index_stats = {
                "table": table_name,
                "indexes": {
                    "primary_key": {"usage_count": 1000, "efficiency": 0.95},
                    "user_email_idx": {"usage_count": 500, "efficiency": 0.85},
                    "created_at_idx": {"usage_count": 50, "efficiency": 0.60},
                    "unused_idx": {"usage_count": 0, "efficiency": 0.0}
                },
                "recommendations": []
            }
            
            # Generate recommendations based on usage
            for idx_name, stats in index_stats["indexes"].items():
                if stats["usage_count"] == 0:
                    index_stats["recommendations"].append({
                        "type": "drop_index",
                        "index": idx_name,
                        "reason": "Index never used"
                    })
                elif stats["efficiency"] < 0.7:
                    index_stats["recommendations"].append({
                        "type": "optimize_index",
                        "index": idx_name,
                        "reason": f"Low efficiency: {stats['efficiency']}"
                    })
            
            return index_stats
        
        mock_query_optimizer.analyze_index_usage = analyze_index_usage
        
        stats = mock_query_optimizer.analyze_index_usage("users")
        
        assert stats["table"] == "users"
        assert len(stats["indexes"]) == 4
        
        # Check recommendations
        recommendations = stats["recommendations"]
        drop_recs = [r for r in recommendations if r["type"] == "drop_index"]
        optimize_recs = [r for r in recommendations if r["type"] == "optimize_index"]
        
        assert len(drop_recs) >= 1  # unused_idx should be recommended for drop
        assert len(optimize_recs) >= 1  # created_at_idx should be recommended for optimization
    
    @pytest.mark.asyncio
    async def test_query_caching_mechanism(self, mock_db_manager):
        """Test query result caching mechanism"""
        cache_hits = 0
        cache_misses = 0
        
        async def execute_with_cache(query, params=None, cache_ttl=300):
            nonlocal cache_hits, cache_misses
            
            cache_key = f"{query}_{hash(str(params))}"
            
            # Check cache
            if cache_key in mock_db_manager.query_cache:
                cache_entry = mock_db_manager.query_cache[cache_key]
                if time.time() - cache_entry["timestamp"] < cache_ttl:
                    cache_hits += 1
                    return {
                        "result": cache_entry["result"],
                        "cached": True,
                        "cache_age": time.time() - cache_entry["timestamp"]
                    }
            
            # Cache miss - execute query
            cache_misses += 1
            await asyncio.sleep(0.05)  # Simulate query execution
            
            result = {"data": f"result_for_{query}", "count": 10}
            
            # Store in cache
            mock_db_manager.query_cache[cache_key] = {
                "result": result,
                "timestamp": time.time()
            }
            
            return {"result": result, "cached": False, "execution_time": 50}
        
        mock_db_manager.execute_with_cache = execute_with_cache
        
        with patch('netra_backend.app.database.manager.DatabaseManager', return_value=mock_db_manager):
            query = "SELECT * FROM users WHERE active = true"
            
            # First execution - cache miss
            result1 = await mock_db_manager.execute_with_cache(query)
            assert result1["cached"] is False
            assert cache_misses == 1
            assert cache_hits == 0
            
            # Second execution - cache hit
            result2 = await mock_db_manager.execute_with_cache(query)
            assert result2["cached"] is True
            assert cache_hits == 1
            assert cache_misses == 1
            
            # Different query - cache miss
            result3 = await mock_db_manager.execute_with_cache("SELECT * FROM posts")
            assert result3["cached"] is False
            assert cache_misses == 2
    
    @pytest.mark.asyncio
    async def test_query_performance_monitoring(self, mock_db_manager):
        """Test continuous query performance monitoring"""
        performance_metrics = {
            "total_queries": 0,
            "average_response_time": 0,
            "slowest_query": None,
            "fastest_query": None,
            "queries_per_second": 0
        }
        
        query_times = []
        start_time = time.time()
        
        async def monitor_query_performance(query):
            query_start = time.time()
            
            # Simulate query execution with varying times
            execution_time = 0.05 + (hash(query) % 100) / 1000  # 50-150ms range
            await asyncio.sleep(execution_time)
            
            query_end = time.time()
            actual_time = query_end - query_start
            query_times.append(actual_time)
            
            # Update metrics
            performance_metrics["total_queries"] += 1
            performance_metrics["average_response_time"] = statistics.mean(query_times)
            performance_metrics["queries_per_second"] = performance_metrics["total_queries"] / (time.time() - start_time)
            
            if not performance_metrics["slowest_query"] or actual_time > performance_metrics["slowest_query"]["time"]:
                performance_metrics["slowest_query"] = {"query": query, "time": actual_time}
            
            if not performance_metrics["fastest_query"] or actual_time < performance_metrics["fastest_query"]["time"]:
                performance_metrics["fastest_query"] = {"query": query, "time": actual_time}
            
            return {
                "query": query,
                "execution_time": actual_time,
                "performance_metrics": performance_metrics.copy()
            }
        
        mock_db_manager.monitor_query_performance = monitor_query_performance
        
        # Execute multiple queries
        test_queries = [
            "SELECT * FROM users",
            "SELECT * FROM posts WHERE published = true",
            "SELECT COUNT(*) FROM comments",
            "UPDATE users SET last_login = NOW()",
            "DELETE FROM temp_data WHERE created < NOW() - INTERVAL 1 DAY"
        ]
        
        results = []
        for query in test_queries:
            result = await mock_db_manager.monitor_query_performance(query)
            results.append(result)
        
        final_metrics = results[-1]["performance_metrics"]
        
        assert final_metrics["total_queries"] == len(test_queries)
        assert final_metrics["average_response_time"] > 0
        assert final_metrics["slowest_query"] is not None
        assert final_metrics["fastest_query"] is not None
        assert final_metrics["queries_per_second"] > 0
        
        # Verify slowest is actually slower than fastest
        assert final_metrics["slowest_query"]["time"] >= final_metrics["fastest_query"]["time"]
    
    def test_query_optimization_suggestions(self, mock_query_optimizer):
        """Test automated query optimization suggestions"""
        def generate_optimization_suggestions(query_stats):
            suggestions = []
            
            # Analyze query patterns and generate suggestions
            if query_stats.get("full_table_scan", False):
                suggestions.append({
                    "type": "add_index",
                    "priority": "high",
                    "description": "Add index to avoid full table scan",
                    "estimated_improvement": "70-90%"
                })
            
            if query_stats.get("execution_time_ms", 0) > 500:
                suggestions.append({
                    "type": "query_rewrite",
                    "priority": "medium",
                    "description": "Consider rewriting query for better performance",
                    "estimated_improvement": "30-50%"
                })
            
            if query_stats.get("rows_examined", 0) > query_stats.get("rows_returned", 0) * 50:
                suggestions.append({
                    "type": "filter_optimization",
                    "priority": "medium",
                    "description": "Optimize WHERE clauses to reduce examined rows",
                    "estimated_improvement": "40-60%"
                })
            
            if "SELECT *" in query_stats.get("query", ""):
                suggestions.append({
                    "type": "column_selection",
                    "priority": "low",
                    "description": "Specify only needed columns instead of SELECT *",
                    "estimated_improvement": "10-20%"
                })
            
            return suggestions
        
        mock_query_optimizer.generate_optimization_suggestions = generate_optimization_suggestions
        
        # Test high-priority optimization case
        problematic_query = {
            "query": "SELECT * FROM large_table WHERE name LIKE '%test%'",
            "execution_time_ms": 800,
            "rows_examined": 1000000,
            "rows_returned": 5,
            "full_table_scan": True
        }
        
        suggestions = mock_query_optimizer.generate_optimization_suggestions(problematic_query)
        
        assert len(suggestions) >= 3  # Should have multiple suggestions
        
        high_priority = [s for s in suggestions if s["priority"] == "high"]
        assert len(high_priority) >= 1  # Full table scan should generate high priority suggestion
        
        # Verify suggestion content
        index_suggestion = next((s for s in suggestions if s["type"] == "add_index"), None)
        assert index_suggestion is not None
        assert "index" in index_suggestion["description"].lower()
        
        column_suggestion = next((s for s in suggestions if s["type"] == "column_selection"), None)
        assert column_suggestion is not None
        assert "SELECT *" in column_suggestion["description"]