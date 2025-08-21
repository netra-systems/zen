"""
Search and query operations for corpus management
Handles content retrieval, statistics, and analytical queries
"""

import json
from typing import Dict, List, Optional

from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.corpus.base import (
    ClickHouseOperationError,
    CorpusNotAvailableError,
)


class SearchOperations:
    """Handles search and analytical operations on corpus content"""
    
    async def get_corpus_statistics(self, db_corpus) -> Optional[Dict]:
        """Get corpus statistics from ClickHouse"""
        self._validate_corpus_availability(db_corpus)
        try:
            async with get_clickhouse_client() as client:
                return await self._gather_corpus_statistics(client, db_corpus.table_name)
        except Exception as e:
            central_logger.error(f"Failed to get statistics for corpus {db_corpus.id}: {str(e)}")
            raise ClickHouseOperationError(f"Failed to retrieve statistics: {str(e)}")
    
    async def _gather_corpus_statistics(self, client, table_name: str) -> Dict:
        """Gather all corpus statistics from ClickHouse."""
        basic_stats = await self._get_basic_statistics(client, table_name)
        workload_dist = await self._get_workload_distribution(client, table_name)
        return self._combine_statistics(basic_stats, workload_dist)
    
    async def _get_basic_statistics(self, client, table_name: str) -> Dict:
        """Get basic corpus statistics."""
        stats_query = self._build_basic_stats_query(table_name)
        result = await client.execute(stats_query)
        return self._format_basic_stats(result)
    
    def _build_basic_stats_query(self, table_name: str) -> str:
        """Build query for basic statistics."""
        return f"""
            SELECT COUNT(*) as total_records, COUNT(DISTINCT workload_type) as unique_workload_types,
                   AVG(LENGTH(prompt)) as avg_prompt_length, AVG(LENGTH(response)) as avg_response_length,
                   MIN(created_at) as first_record, MAX(created_at) as last_record
            FROM {table_name}
        """
    
    def _format_basic_stats(self, result) -> Dict:
        """Format basic statistics from query result."""
        if not result:
            return {}
        row = result[0]
        return self._build_stats_dict(row)
    
    def _build_stats_dict(self, row) -> Dict:
        """Build statistics dictionary from result row."""
        return {
            "total_records": row[0], "unique_workload_types": row[1],
            "avg_prompt_length": float(row[2]) if row[2] else 0.0,
            "avg_response_length": float(row[3]) if row[3] else 0.0,
            "first_record": row[4].isoformat() if row[4] else None,
            "last_record": row[5].isoformat() if row[5] else None
        }
    
    async def _get_workload_distribution(self, client, table_name: str) -> Dict:
        """Get workload type distribution."""
        dist_query = f"SELECT workload_type, COUNT(*) as count FROM {table_name} GROUP BY workload_type"
        result = await client.execute(dist_query)
        return {row[0]: row[1] for row in result}
    
    def _combine_statistics(self, basic_stats: Dict, workload_dist: Dict) -> Dict:
        """Combine basic statistics and workload distribution."""
        basic_stats["workload_distribution"] = workload_dist
        return basic_stats
    
    def _validate_corpus_availability(self, db_corpus) -> None:
        """Validate that corpus is available for searching"""
        if db_corpus.status != "available":
            raise CorpusNotAvailableError(
                f"Corpus {db_corpus.id} is not available"
            )
    
    def _build_base_query(self, table_name: str) -> str:
        """Build the base SELECT query"""
        return f"""
            SELECT record_id, workload_type, prompt, response, metadata, created_at
            FROM {table_name}
        """
    
    def _add_workload_type_filter(
        self, conditions: List[str], search_params: Dict
    ) -> None:
        """Add workload type filter to conditions list"""
        if search_params.get("workload_type"):
            conditions.append(
                f"workload_type = '{search_params['workload_type']}'"
            )
    
    def _add_date_range_filters(
        self, conditions: List[str], search_params: Dict
    ) -> None:
        """Add date range filters to conditions list"""
        if search_params.get("start_date"):
            conditions.append(f"created_at >= '{search_params['start_date']}'")
        if search_params.get("end_date"):
            conditions.append(f"created_at <= '{search_params['end_date']}'")
    
    def _escape_text_search(self, text: str) -> str:
        """Escape text search string for SQL safety"""
        return text.replace("'", "''")
    
    def _add_text_search_filter(
        self, conditions: List[str], search_params: Dict
    ) -> None:
        """Add text search filter to conditions list"""
        if search_params.get("text_search"):
            escaped_text = self._escape_text_search(search_params["text_search"])
            filter_clause = f"(prompt LIKE '%{escaped_text}%' OR response LIKE '%{escaped_text}%')"
            conditions.append(filter_clause)
    
    def _add_domain_filter(
        self, conditions: List[str], search_params: Dict
    ) -> None:
        """Add domain filter to conditions list"""
        if search_params.get("domain"):
            conditions.append(f"domain = '{search_params['domain']}'")
    
    def _build_where_conditions(self, search_params: Dict) -> List[str]:
        """Build all WHERE conditions from search parameters"""
        conditions = []
        self._add_workload_type_filter(conditions, search_params)
        self._add_date_range_filters(conditions, search_params)
        self._add_text_search_filter(conditions, search_params)
        self._add_domain_filter(conditions, search_params)
        return conditions
    
    def _build_order_clause(self, search_params: Dict) -> str:
        """Build ORDER BY clause from search parameters"""
        order_by = search_params.get("order_by", "created_at")
        order_dir = search_params.get("order_direction", "DESC")
        return f" ORDER BY {order_by} {order_dir}"
    
    def _build_pagination_clause(self, search_params: Dict) -> str:
        """Build LIMIT and OFFSET clause from search parameters"""
        limit = min(search_params.get("limit", 100), 1000)  # Cap at 1000
        offset = search_params.get("offset", 0)
        return f" LIMIT {limit} OFFSET {offset}"
    
    def _parse_metadata(self, metadata_raw) -> Dict:
        """Parse metadata JSON or return empty dict"""
        return json.loads(metadata_raw) if metadata_raw else {}
    
    def _format_timestamp(self, timestamp) -> Optional[str]:
        """Format timestamp to ISO string or None"""
        return timestamp.isoformat() if timestamp else None
    
    def _build_result_dict(self, row) -> Dict:
        """Build result dictionary from row data"""
        return {
            "record_id": str(row[0]),
            "workload_type": row[1],
            "prompt": row[2],
            "response": row[3]
        }
    
    def _format_result_row(self, row) -> Dict:
        """Format a single result row to dictionary"""
        result = self._build_result_dict(row)
        result["metadata"] = self._parse_metadata(row[4])
        result["created_at"] = self._format_timestamp(row[5])
        return result
    
    def _process_search_results(self, result) -> List[Dict]:
        """Convert ClickHouse result rows to list of dictionaries"""
        return [self._format_result_row(row) for row in result]
    
    async def _execute_search_query(
        self, query: str, db_corpus
    ) -> List[Dict]:
        """Execute the complete search query and return processed results"""
        async with get_clickhouse_client() as client:
            result = await client.execute(query)
            return self._process_search_results(result)
    
    def _build_complete_search_query(self, db_corpus, search_params: Dict) -> str:
        """Build complete search query with all conditions"""
        query = self._build_base_query(db_corpus.table_name)
        conditions = self._build_where_conditions(search_params)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += self._build_order_clause(search_params)
        query += self._build_pagination_clause(search_params)
        return query

    def _handle_search_error(self, db_corpus, error: Exception) -> None:
        """Handle search operation errors"""
        central_logger.error(f"Failed to search corpus {db_corpus.id}: {str(error)}")
        raise ClickHouseOperationError(f"Search failed: {str(error)}")

    async def _execute_search_operation(self, db_corpus, search_params: Dict) -> List[Dict]:
        """Execute the complete search operation"""
        query = self._build_complete_search_query(db_corpus, search_params)
        return await self._execute_search_query(query, db_corpus)

    async def search_corpus_content(
        self, db_corpus, search_params: Dict
    ) -> Optional[List[Dict]]:
        """Search corpus content with advanced filtering"""
        self._validate_corpus_availability(db_corpus)
        try:
            return await self._execute_search_operation(db_corpus, search_params)
        except Exception as e:
            self._handle_search_error(db_corpus, e)
    
    async def get_corpus_sample(
        self, db_corpus, sample_size: int = 10, workload_type: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """Get a random sample of corpus content"""
        self._validate_corpus_availability(db_corpus)
        try:
            async with get_clickhouse_client() as client:
                return await self._execute_sample_query(client, db_corpus.table_name, sample_size, workload_type)
        except Exception as e:
            central_logger.error(f"Failed to sample corpus {db_corpus.id}: {str(e)}")
            raise ClickHouseOperationError(f"Sampling failed: {str(e)}")
    
    async def _execute_sample_query(
        self, client, table_name: str, sample_size: int, workload_type: Optional[str]
    ) -> List[Dict]:
        """Execute sampling query and return formatted results."""
        query = self._build_sample_query(table_name, sample_size, workload_type)
        result = await client.execute(query)
        return self._format_sample_results(result)
    
    def _build_sample_query(self, table_name: str, sample_size: int, workload_type: Optional[str]) -> str:
        """Build random sampling query."""
        base_query = f"SELECT record_id, workload_type, prompt, response, metadata FROM {table_name}"
        where_clause = f" WHERE workload_type = '{workload_type}'" if workload_type else ""
        limit_clause = f" ORDER BY rand() LIMIT {min(sample_size, 100)}"
        return base_query + where_clause + limit_clause
    
    def _format_sample_results(self, result) -> List[Dict]:
        """Format sampling results into list of dictionaries."""
        return [self._format_sample_row(row) for row in result]
    
    def _format_sample_row(self, row) -> Dict:
        """Format a single sample row."""
        return {
            "record_id": str(row[0]), "workload_type": row[1], "prompt": row[2],
            "response": row[3], "metadata": self._parse_metadata(row[4])
        }
    
    async def get_workload_type_analytics(
        self,
        db_corpus
    ) -> Optional[Dict]:
        """Get detailed analytics by workload type"""
        self._validate_corpus_availability(db_corpus)
        try:
            async with get_clickhouse_client() as client:
                return await self._execute_workload_analytics_query(client, db_corpus.table_name)
        except Exception as e:
            central_logger.error(f"Failed to get workload analytics for corpus {db_corpus.id}: {str(e)}")
            raise ClickHouseOperationError(f"Analytics query failed: {str(e)}")
    
    async def _execute_workload_analytics_query(
        self, client, table_name: str
    ) -> Dict:
        """Execute workload analytics query and format results."""
        query = self._build_workload_analytics_query(table_name)
        result = await client.execute(query)
        return self._format_workload_analytics_results(result)
    
    def _build_workload_analytics_query(self, table_name: str) -> str:
        """Build analytics query for workload type data."""
        return f"""
            SELECT workload_type, COUNT(*) as count,
                   AVG(LENGTH(prompt)) as avg_prompt_length, AVG(LENGTH(response)) as avg_response_length,
                   MIN(LENGTH(prompt)) as min_prompt_length, MAX(LENGTH(prompt)) as max_prompt_length,
                   MIN(LENGTH(response)) as min_response_length, MAX(LENGTH(response)) as max_response_length,
                   MIN(created_at) as earliest_record, MAX(created_at) as latest_record
            FROM {table_name} GROUP BY workload_type ORDER BY count DESC
        """
    
    def _format_workload_analytics_results(self, result) -> Dict:
        """Format workload analytics results into dictionary."""
        analytics = {}
        for row in result:
            analytics[row[0]] = self._build_workload_analytics_row(row)
        return analytics
    
    def _build_workload_analytics_row(self, row) -> Dict:
        """Build analytics data dictionary for a single workload type row."""
        base_data = self._extract_workload_row_metrics(row)
        timestamps = self._format_workload_timestamps(row[8], row[9])
        return {**base_data, **timestamps}
    
    def _extract_workload_row_metrics(self, row) -> Dict:
        """Extract numeric metrics from workload analytics row."""
        return {
            "count": row[1], "avg_prompt_length": float(row[2]) if row[2] else 0.0,
            "avg_response_length": float(row[3]) if row[3] else 0.0, "min_prompt_length": row[4],
            "max_prompt_length": row[5], "min_response_length": row[6], "max_response_length": row[7]
        }
    
    def _format_workload_timestamps(self, earliest, latest) -> Dict:
        """Format earliest and latest timestamps for workload analytics."""
        return {
            "earliest_record": earliest.isoformat() if earliest else None,
            "latest_record": latest.isoformat() if latest else None
        }