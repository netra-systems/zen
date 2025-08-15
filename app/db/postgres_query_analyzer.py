"""PostgreSQL query analysis for index optimization.

This module provides specialized PostgreSQL query analysis functionality
for generating index recommendations based on query patterns.
"""

from typing import List, Dict, Any, Tuple
from sqlalchemy import text

from app.logging_config import central_logger
from app.db.index_optimizer_core import (
    IndexRecommendation,
    QueryAnalyzer,
    PerformanceMetrics
)

logger = central_logger.get_logger(__name__)


class PostgreSQLSlowQueryAnalyzer:
    """Analyze slow PostgreSQL queries for index recommendations."""
    
    async def get_slow_queries(self, session) -> List[Tuple]:
        """Get slow queries from pg_stat_statements."""
        try:
            slow_queries_query = text("""
                SELECT query, calls, total_time, mean_time, rows
                FROM pg_stat_statements 
                WHERE mean_time > 100  -- queries slower than 100ms
                ORDER BY mean_time DESC
                LIMIT 20
            """)
            result = await session.execute(slow_queries_query)
            return result.fetchall()
        except Exception as e:
            logger.debug(f"pg_stat_statements not available: {e}")
            return []
    
    def analyze_single_query(self, query_data: Tuple) -> List[IndexRecommendation]:
        """Analyze single query and generate recommendations."""
        query, calls, total_time, mean_time, rows = query_data
        recommendations = []
        
        # Extract table and conditions
        table_name = QueryAnalyzer.extract_table_name(query)
        if not table_name:
            return recommendations
        
        # WHERE clause recommendations
        where_conditions = QueryAnalyzer.extract_where_conditions(query)
        if where_conditions:
            benefit = PerformanceMetrics.calculate_benefit_estimate(mean_time)
            priority = PerformanceMetrics.get_priority_from_benefit(benefit)
            
            rec = IndexRecommendation(
                table_name=table_name,
                columns=where_conditions[:3],  # Limit to 3 columns
                reason=f"WHERE clause equality: {', '.join(where_conditions)}",
                estimated_benefit=benefit,
                priority=priority
            )
            recommendations.append(rec)
        
        # ORDER BY recommendations
        order_columns = QueryAnalyzer.extract_order_by_columns(query)
        if order_columns:
            benefit = PerformanceMetrics.calculate_benefit_estimate(mean_time)
            priority = PerformanceMetrics.get_priority_from_benefit(benefit)
            
            rec = IndexRecommendation(
                table_name=table_name,
                columns=order_columns[:2],  # Limit to 2 columns for ORDER BY
                reason=f"ORDER BY optimization: {', '.join(order_columns)}",
                estimated_benefit=benefit,
                priority=priority
            )
            recommendations.append(rec)
        
        return recommendations
    
    def generate_recommendations_from_queries(self, slow_queries: List[Tuple]) -> List[IndexRecommendation]:
        """Generate recommendations from multiple slow queries."""
        all_recommendations = []
        
        for query_data in slow_queries:
            query_recommendations = self.analyze_single_query(query_data)
            all_recommendations.extend(query_recommendations)
        
        return all_recommendations


class PostgreSQLRecommendationProvider:
    """Provide general PostgreSQL index recommendations."""
    
    def get_general_recommendations(self) -> List[IndexRecommendation]:
        """Get general index recommendations for common patterns."""
        return [
            IndexRecommendation(
                table_name="userbase",
                columns=["email"], 
                reason="Frequent user lookups by email",
                priority=1
            ),
            IndexRecommendation(
                table_name="corpus_audit_logs",
                columns=["timestamp"],
                reason="Time-based audit queries", 
                priority=1
            ),
            IndexRecommendation(
                table_name="corpus_audit_logs",
                columns=["user_id", "action"],
                reason="User action filtering",
                priority=2
            ),
            IndexRecommendation(
                table_name="secret",
                columns=["user_id"],
                reason="User secret lookups",
                priority=2
            ),
            IndexRecommendation(
                table_name="agent_states",
                columns=["session_id"],
                reason="Session-based state lookups",
                priority=2
            )
        ]
    
    def get_composite_index_recommendations(self) -> List[IndexRecommendation]:
        """Get composite index recommendations for complex queries."""
        return [
            IndexRecommendation(
                table_name="userbase",
                columns=["plan_tier", "plan_expires_at", "is_active"],
                reason="Plan expiration queries",
                priority=2
            ),
            IndexRecommendation(
                table_name="corpus_audit_logs", 
                columns=["user_id", "action", "timestamp"],
                reason="User action timeline queries",
                priority=2
            ),
            IndexRecommendation(
                table_name="corpus_audit_logs",
                columns=["corpus_id", "timestamp", "status"], 
                reason="Corpus operation history queries",
                priority=3
            )
        ]
    
    def get_all_recommendations(self) -> List[IndexRecommendation]:
        """Get all general recommendations."""
        recommendations = []
        recommendations.extend(self.get_general_recommendations())
        recommendations.extend(self.get_composite_index_recommendations())
        return recommendations