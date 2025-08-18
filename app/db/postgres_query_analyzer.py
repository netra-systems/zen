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
    
    def _build_slow_queries_sql(self) -> text:
        """Build SQL query for slow query analysis."""
        return text("""
            SELECT query, calls, total_time, mean_time, rows
            FROM pg_stat_statements 
            WHERE mean_time > 100  -- queries slower than 100ms
            ORDER BY mean_time DESC
            LIMIT 20
        """)
    
    async def get_slow_queries(self, session) -> List[Tuple]:
        """Get slow queries from pg_stat_statements."""
        try:
            slow_queries_query = self._build_slow_queries_sql()
            result = await session.execute(slow_queries_query)
            return result.fetchall()
        except Exception as e:
            logger.debug(f"pg_stat_statements not available: {e}")
            return []
    
    def _extract_query_info(self, query_data: Tuple) -> Tuple[str, str, float]:
        """Extract basic query information."""
        query, calls, total_time, mean_time, rows = query_data
        table_name = QueryAnalyzer.extract_table_name(query)
        return query, table_name, mean_time
    
    def _extract_where_conditions_data(self, query: str, mean_time: float):
        """Extract WHERE conditions and performance data."""
        where_conditions = QueryAnalyzer.extract_where_conditions(query)
        benefit = PerformanceMetrics.calculate_benefit_estimate(mean_time)
        priority = PerformanceMetrics.get_priority_from_benefit(benefit)
        return where_conditions, benefit, priority
    
    def _build_where_recommendation(self, table_name: str, where_conditions: List, 
                                   benefit: float, priority: int) -> IndexRecommendation:
        """Build WHERE clause recommendation."""
        return IndexRecommendation(
            table_name=table_name,
            columns=where_conditions[:3],
            reason=f"WHERE clause equality: {', '.join(where_conditions)}",
            estimated_benefit=benefit,
            priority=priority
        )
    
    def _generate_where_recommendation(self, query: str, table_name: str, mean_time: float) -> IndexRecommendation:
        """Generate WHERE clause index recommendation."""
        where_conditions, benefit, priority = self._extract_where_conditions_data(query, mean_time)
        return self._build_where_recommendation(table_name, where_conditions, benefit, priority)
    
    def _extract_order_columns_data(self, query: str, mean_time: float):
        """Extract ORDER BY columns and performance data."""
        order_columns = QueryAnalyzer.extract_order_by_columns(query)
        benefit = PerformanceMetrics.calculate_benefit_estimate(mean_time)
        priority = PerformanceMetrics.get_priority_from_benefit(benefit)
        return order_columns, benefit, priority
    
    def _build_order_recommendation(self, table_name: str, order_columns: List,
                                   benefit: float, priority: int) -> IndexRecommendation:
        """Build ORDER BY recommendation."""
        return IndexRecommendation(
            table_name=table_name,
            columns=order_columns[:2],
            reason=f"ORDER BY optimization: {', '.join(order_columns)}",
            estimated_benefit=benefit,
            priority=priority
        )
    
    def _generate_order_recommendation(self, query: str, table_name: str, mean_time: float) -> IndexRecommendation:
        """Generate ORDER BY index recommendation."""
        order_columns, benefit, priority = self._extract_order_columns_data(query, mean_time)
        return self._build_order_recommendation(table_name, order_columns, benefit, priority)
    
    def _add_where_recommendations(self, recommendations: List, query: str, 
                                  table_name: str, mean_time: float):
        """Add WHERE clause recommendations if applicable."""
        where_conditions = QueryAnalyzer.extract_where_conditions(query)
        if where_conditions:
            recommendations.append(self._generate_where_recommendation(query, table_name, mean_time))
    
    def _add_order_recommendations(self, recommendations: List, query: str,
                                  table_name: str, mean_time: float):
        """Add ORDER BY recommendations if applicable."""
        order_columns = QueryAnalyzer.extract_order_by_columns(query)
        if order_columns:
            recommendations.append(self._generate_order_recommendation(query, table_name, mean_time))
    
    def analyze_single_query(self, query_data: Tuple) -> List[IndexRecommendation]:
        """Analyze single query and generate recommendations."""
        recommendations = []
        query, table_name, mean_time = self._extract_query_info(query_data)
        if not table_name:
            return recommendations
        self._add_where_recommendations(recommendations, query, table_name, mean_time)
        self._add_order_recommendations(recommendations, query, table_name, mean_time)
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
    
    def _get_user_table_recommendations(self) -> List[IndexRecommendation]:
        """Get user-related table recommendations."""
        return [
            IndexRecommendation(
                table_name="userbase",
                columns=["email"], 
                reason="Frequent user lookups by email",
                priority=1
            )
        ]
    
    def _get_audit_table_recommendations(self) -> List[IndexRecommendation]:
        """Get audit log table recommendations."""
        return [
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
            )
        ]
    
    def _get_other_table_recommendations(self) -> List[IndexRecommendation]:
        """Get other table recommendations."""
        return [
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
    
    def get_general_recommendations(self) -> List[IndexRecommendation]:
        """Get general index recommendations for common patterns."""
        recommendations = []
        recommendations.extend(self._get_user_table_recommendations())
        recommendations.extend(self._get_audit_table_recommendations())
        recommendations.extend(self._get_other_table_recommendations())
        return recommendations
    
    def _get_user_composite_recommendations(self) -> List[IndexRecommendation]:
        """Get composite recommendations for user tables."""
        return [
            IndexRecommendation(
                table_name="userbase",
                columns=["plan_tier", "plan_expires_at", "is_active"],
                reason="Plan expiration queries",
                priority=2
            )
        ]
    
    def _get_audit_composite_recommendations(self) -> List[IndexRecommendation]:
        """Get composite recommendations for audit tables."""
        return [
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
    
    def get_composite_index_recommendations(self) -> List[IndexRecommendation]:
        """Get composite index recommendations for complex queries."""
        recommendations = []
        recommendations.extend(self._get_user_composite_recommendations())
        recommendations.extend(self._get_audit_composite_recommendations())
        return recommendations
    
    def get_all_recommendations(self) -> List[IndexRecommendation]:
        """Get all general recommendations."""
        recommendations = []
        recommendations.extend(self.get_general_recommendations())
        recommendations.extend(self.get_composite_index_recommendations())
        return recommendations