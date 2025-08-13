"""
Search and query operations for corpus management
Handles content retrieval, statistics, and analytical queries
"""

import json
from typing import Dict, List, Optional

from ...db.clickhouse import get_clickhouse_client
from .base import ClickHouseOperationError, CorpusNotAvailableError
from app.logging_config import central_logger


class SearchOperations:
    """Handles search and analytical operations on corpus content"""
    
    async def get_corpus_statistics(
        self,
        db_corpus
    ) -> Optional[Dict]:
        """Get corpus statistics from ClickHouse"""
        if db_corpus.status != "available":
            raise CorpusNotAvailableError(f"Corpus {db_corpus.id} is not available")
        
        try:
            async with get_clickhouse_client() as client:
                # Get basic statistics
                stats_query = f"""
                    SELECT 
                        COUNT(*) as total_records,
                        COUNT(DISTINCT workload_type) as unique_workload_types,
                        AVG(LENGTH(prompt)) as avg_prompt_length,
                        AVG(LENGTH(response)) as avg_response_length,
                        MIN(created_at) as first_record,
                        MAX(created_at) as last_record
                    FROM {db_corpus.table_name}
                """
                
                stats_result = await client.execute(stats_query)
                
                # Get workload distribution
                dist_query = f"""
                    SELECT workload_type, COUNT(*) as count
                    FROM {db_corpus.table_name}
                    GROUP BY workload_type
                """
                
                dist_result = await client.execute(dist_query)
                
                # Format statistics
                stats = {}
                if stats_result:
                    row = stats_result[0]
                    stats = {
                        "total_records": row[0],
                        "unique_workload_types": row[1],
                        "avg_prompt_length": float(row[2]) if row[2] else 0.0,
                        "avg_response_length": float(row[3]) if row[3] else 0.0,
                        "first_record": row[4].isoformat() if row[4] else None,
                        "last_record": row[5].isoformat() if row[5] else None
                    }
                
                # Add workload distribution
                stats["workload_distribution"] = {
                    row[0]: row[1] for row in dist_result
                }
                
                return stats
                
        except Exception as e:
            central_logger.error(f"Failed to get statistics for corpus {db_corpus.id}: {str(e)}")
            raise ClickHouseOperationError(f"Failed to retrieve statistics: {str(e)}")
    
    async def search_corpus_content(
        self,
        db_corpus,
        search_params: Dict
    ) -> Optional[List[Dict]]:
        """
        Search corpus content with advanced filtering
        
        Args:
            db_corpus: Corpus database model
            search_params: Search parameters including filters, sorting, etc.
            
        Returns:
            List of matching records
        """
        if db_corpus.status != "available":
            raise CorpusNotAvailableError(f"Corpus {db_corpus.id} is not available")
        
        try:
            async with get_clickhouse_client() as client:
                # Build base query
                query = f"""
                    SELECT record_id, workload_type, prompt, response, metadata, created_at
                    FROM {db_corpus.table_name}
                """
                
                # Build WHERE clause
                where_conditions = []
                
                # Filter by workload type
                if search_params.get("workload_type"):
                    where_conditions.append(f"workload_type = '{search_params['workload_type']}'")
                
                # Filter by date range
                if search_params.get("start_date"):
                    where_conditions.append(f"created_at >= '{search_params['start_date']}'")
                if search_params.get("end_date"):
                    where_conditions.append(f"created_at <= '{search_params['end_date']}'")
                
                # Text search in prompt/response
                if search_params.get("text_search"):
                    text_search = search_params["text_search"].replace("'", "''")
                    where_conditions.append(
                        f"(prompt LIKE '%{text_search}%' OR response LIKE '%{text_search}%')"
                    )
                
                # Domain filter
                if search_params.get("domain"):
                    where_conditions.append(f"domain = '{search_params['domain']}'")
                
                # Add WHERE clause if conditions exist
                if where_conditions:
                    query += " WHERE " + " AND ".join(where_conditions)
                
                # Add ORDER BY
                order_by = search_params.get("order_by", "created_at")
                order_dir = search_params.get("order_direction", "DESC")
                query += f" ORDER BY {order_by} {order_dir}"
                
                # Add LIMIT and OFFSET
                limit = min(search_params.get("limit", 100), 1000)  # Cap at 1000
                offset = search_params.get("offset", 0)
                query += f" LIMIT {limit} OFFSET {offset}"
                
                result = await client.execute(query)
                
                # Convert to list of dicts
                content = []
                for row in result:
                    content.append({
                        "record_id": str(row[0]),
                        "workload_type": row[1],
                        "prompt": row[2],
                        "response": row[3],
                        "metadata": json.loads(row[4]) if row[4] else {},
                        "created_at": row[5].isoformat() if row[5] else None
                    })
                
                return content
                
        except Exception as e:
            central_logger.error(f"Failed to search corpus {db_corpus.id}: {str(e)}")
            raise ClickHouseOperationError(f"Search failed: {str(e)}")
    
    async def get_corpus_sample(
        self,
        db_corpus,
        sample_size: int = 10,
        workload_type: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """
        Get a random sample of corpus content
        
        Args:
            db_corpus: Corpus database model
            sample_size: Number of records to sample
            workload_type: Optional workload type filter
            
        Returns:
            Random sample of records
        """
        if db_corpus.status != "available":
            raise CorpusNotAvailableError(f"Corpus {db_corpus.id} is not available")
        
        try:
            async with get_clickhouse_client() as client:
                # Build query with random sampling
                query = f"""
                    SELECT record_id, workload_type, prompt, response, metadata
                    FROM {db_corpus.table_name}
                """
                
                if workload_type:
                    query += f" WHERE workload_type = '{workload_type}'"
                
                # Use SAMPLE for random sampling
                query += f" ORDER BY rand() LIMIT {min(sample_size, 100)}"
                
                result = await client.execute(query)
                
                # Convert to list of dicts
                sample = []
                for row in result:
                    sample.append({
                        "record_id": str(row[0]),
                        "workload_type": row[1],
                        "prompt": row[2],
                        "response": row[3],
                        "metadata": json.loads(row[4]) if row[4] else {}
                    })
                
                return sample
                
        except Exception as e:
            central_logger.error(f"Failed to sample corpus {db_corpus.id}: {str(e)}")
            raise ClickHouseOperationError(f"Sampling failed: {str(e)}")
    
    async def get_workload_type_analytics(
        self,
        db_corpus
    ) -> Optional[Dict]:
        """
        Get detailed analytics by workload type
        
        Args:
            db_corpus: Corpus database model
            
        Returns:
            Analytics data by workload type
        """
        if db_corpus.status != "available":
            raise CorpusNotAvailableError(f"Corpus {db_corpus.id} is not available")
        
        try:
            async with get_clickhouse_client() as client:
                # Get analytics by workload type
                analytics_query = f"""
                    SELECT 
                        workload_type,
                        COUNT(*) as count,
                        AVG(LENGTH(prompt)) as avg_prompt_length,
                        AVG(LENGTH(response)) as avg_response_length,
                        MIN(LENGTH(prompt)) as min_prompt_length,
                        MAX(LENGTH(prompt)) as max_prompt_length,
                        MIN(LENGTH(response)) as min_response_length,
                        MAX(LENGTH(response)) as max_response_length,
                        MIN(created_at) as earliest_record,
                        MAX(created_at) as latest_record
                    FROM {db_corpus.table_name}
                    GROUP BY workload_type
                    ORDER BY count DESC
                """
                
                result = await client.execute(analytics_query)
                
                # Format analytics
                analytics = {}
                for row in result:
                    analytics[row[0]] = {
                        "count": row[1],
                        "avg_prompt_length": float(row[2]) if row[2] else 0.0,
                        "avg_response_length": float(row[3]) if row[3] else 0.0,
                        "min_prompt_length": row[4],
                        "max_prompt_length": row[5],
                        "min_response_length": row[6],
                        "max_response_length": row[7],
                        "earliest_record": row[8].isoformat() if row[8] else None,
                        "latest_record": row[9].isoformat() if row[9] else None
                    }
                
                return analytics
                
        except Exception as e:
            central_logger.error(f"Failed to get workload analytics for corpus {db_corpus.id}: {str(e)}")
            raise ClickHouseOperationError(f"Analytics query failed: {str(e)}")