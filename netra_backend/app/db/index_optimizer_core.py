"""Database index optimization core types and interfaces.

This module provides common types and interfaces for database index optimization
across PostgreSQL and ClickHouse databases.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class IndexRecommendation:
    """Database index recommendation."""
    table_name: str
    columns: List[str]
    index_type: str = "btree"  # btree, hash, gin, gist for PostgreSQL
    reason: str = ""
    estimated_benefit: float = 0.0
    priority: int = 1  # 1=high, 2=medium, 3=low


@dataclass
class IndexCreationResult:
    """Result of index creation operation."""
    index_name: str
    success: bool
    error_message: str = ""
    already_exists: bool = False


class DatabaseValidation:
    """Database connection and engine validation utilities."""
    
    @staticmethod
    def validate_async_engine(async_engine) -> bool:
        """Validate async engine is available."""
        return async_engine is not None
    
    @staticmethod
    def validate_raw_connection_method(async_engine) -> bool:
        """Validate raw connection method exists."""
        return hasattr(async_engine, 'raw_connection')
    
    @staticmethod
    def log_engine_unavailable(operation: str) -> None:
        """Log engine unavailable error."""
        logger.warning(f"Async engine not available, skipping {operation}")


class IndexNameGenerator:
    """Generate standardized index names."""
    
    @staticmethod
    def generate_index_name(table_name: str, columns: List[str]) -> str:
        """Generate standard index name."""
        return f"idx_{table_name}_{'_'.join(columns)}"
    
    @staticmethod
    def validate_index_name(index_name: str) -> bool:
        """Validate index name format."""
        return index_name.startswith("idx_") and len(index_name) <= 63


class QueryAnalyzer:
    """SQL query analysis utilities."""
    
    @staticmethod
    def _extract_where_clause(query_lower: str) -> Optional[str]:
        """Extract WHERE clause from lowercased query."""
        import re
        where_match = re.search(
            r'where\s+(.+?)(?:\s+order\s+by|\s+group\s+by|\s+limit|$)', 
            query_lower
        )
        return where_match.group(1) if where_match else None
    
    @staticmethod
    def _find_equality_columns(where_clause: str) -> List[str]:
        """Find columns with equality conditions in WHERE clause."""
        import re
        return re.findall(r'(\w+)\s*=\s*', where_clause)
    
    @staticmethod
    def extract_where_conditions(query: str) -> List[str]:
        """Extract WHERE clause equality conditions."""
        query_lower = query.lower()
        where_clause = QueryAnalyzer._extract_where_clause(query_lower)
        if where_clause:
            return QueryAnalyzer._find_equality_columns(where_clause)
        return []
    
    @staticmethod
    def extract_table_name(query: str) -> Optional[str]:
        """Extract table name from FROM clause."""
        import re
        from_match = re.search(r'from\s+(\w+)', query.lower())
        return from_match.group(1) if from_match else None
    
    @staticmethod
    def extract_order_by_columns(query: str) -> List[str]:
        """Extract ORDER BY columns."""
        import re
        order_match = re.search(r'order\s+by\s+([\w\s,]+)', query.lower())
        if order_match:
            return [col.strip() for col in order_match.group(1).split(',')]
        return []


class IndexExistenceChecker:
    """Check if indexes already exist."""
    
    def __init__(self):
        self.existing_indexes: Set[str] = set()
    
    def add_existing_index(self, index_name: str) -> None:
        """Add index to existing set."""
        self.existing_indexes.add(index_name)
    
    def index_exists(self, index_name: str) -> bool:
        """Check if index already exists."""
        return index_name in self.existing_indexes
    
    def get_existing_count(self) -> int:
        """Get count of existing indexes."""
        return len(self.existing_indexes)


class PerformanceMetrics:
    """Performance metrics calculation."""
    
    @staticmethod
    def calculate_benefit_estimate(mean_time: float) -> float:
        """Calculate estimated benefit from mean query time."""
        return min(mean_time / 100.0, 5.0)  # Cap at 5x benefit
    
    @staticmethod
    def get_priority_from_benefit(benefit: float) -> int:
        """Get priority level from benefit estimate."""
        if benefit >= 3.0:
            return 1  # high
        elif benefit >= 1.5:
            return 2  # medium
        return 3  # low


class DatabaseErrorHandler:
    """Handle database errors consistently."""
    
    @staticmethod
    def is_already_exists_error(error: Exception) -> bool:
        """Check if error indicates index already exists."""
        return "already exists" in str(error).lower()
    
    @staticmethod
    def log_index_creation_error(index_name: str, error: Exception) -> None:
        """Log index creation error."""
        logger.error(f"Error creating index {index_name}: {error}")
    
    @staticmethod
    def log_index_creation_success(index_name: str, table_name: str, 
                                 columns: List[str], reason: str) -> None:
        """Log successful index creation."""
        column_list = ', '.join(columns)
        logger.info(
            f"Created index {index_name} on {table_name}({column_list}) - {reason}"
        )