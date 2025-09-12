"""
Corpus Audit Repository
Repository layer for corpus audit operations with async patterns.
Focused on database interactions only.  <= 300 lines,  <= 8 lines per function.
"""

from typing import Any, Dict, List

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.core.exceptions_database import DatabaseError
from netra_backend.app.db.models_postgres import CorpusAuditLog
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.registry import CorpusAuditSearchFilter
from netra_backend.app.services.database.base_repository import BaseRepository

logger = central_logger.get_logger(__name__)


class CorpusAuditRepository(BaseRepository[CorpusAuditLog]):
    """Repository for corpus audit operations with async patterns."""

    def __init__(self):
        super().__init__(CorpusAuditLog)

    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[CorpusAuditLog]:
        """Find audit records by user ID."""
        try:
            return await self._execute_user_query(db, user_id)
        except Exception as e:
            return self._handle_user_query_error(e, user_id)
    
    async def _execute_user_query(self, db: AsyncSession, user_id: str) -> List[CorpusAuditLog]:
        """Execute user query and return results."""
        result = await db.execute(
            select(CorpusAuditLog).where(CorpusAuditLog.user_id == user_id)
        )
        return list(result.scalars().all())
    
    def _handle_user_query_error(self, error: Exception, user_id: str) -> None:
        """Handle user query errors."""
        logger.error(f"Error finding audit records by user {user_id}: {error}")
        raise DatabaseError(f"Failed to find audit records", context={"user_id": user_id})

    async def search_records(self, db: AsyncSession, filters: CorpusAuditSearchFilter) -> List[CorpusAuditLog]:
        """Search audit records with comprehensive filtering."""
        try:
            return await self._execute_search_query(db, filters)
        except Exception as e:
            self._handle_search_error(e, filters)

    async def _execute_search_query(self, db: AsyncSession, filters: CorpusAuditSearchFilter) -> List[CorpusAuditLog]:
        """Execute search query with pagination."""
        query = self._build_search_query(filters)
        result = await db.execute(query.limit(filters.limit).offset(filters.offset))
        return list(result.scalars().all())
    
    def _handle_search_error(self, error: Exception, filters: CorpusAuditSearchFilter) -> None:
        """Handle search query errors."""
        logger.error(f"Error searching audit records: {error}")
        raise DatabaseError("Failed to search audit records", context={"filters": filters.model_dump()})

    def _build_search_query(self, filters: CorpusAuditSearchFilter):
        """Build search query with all filters applied."""
        query = select(CorpusAuditLog).order_by(desc(CorpusAuditLog.timestamp))
        query = self._apply_basic_filters(query, filters)
        return self._apply_additional_filters(query, filters)
    
    def _apply_basic_filters(self, query, filters: CorpusAuditSearchFilter):
        """Apply basic filters to query."""
        query = self._apply_user_filter(query, filters)
        query = self._apply_action_status_filters(query, filters)
        return query

    def _apply_user_filter(self, query, filters: CorpusAuditSearchFilter):
        """Apply user ID filter to query."""
        if filters.user_id:
            query = query.where(CorpusAuditLog.user_id == filters.user_id)
        return query

    def _apply_action_status_filters(self, query, filters: CorpusAuditSearchFilter):
        """Apply action and status filters to query."""
        if filters.action:
            query = query.where(CorpusAuditLog.action == filters.action.value)
        if filters.status:
            query = query.where(CorpusAuditLog.status == filters.status.value)
        return query

    def _apply_additional_filters(self, query, filters: CorpusAuditSearchFilter):
        """Apply additional search filters to query."""
        query = self._apply_resource_filters(query, filters)
        query = self._apply_date_filters(query, filters)
        return query
    
    def _apply_resource_filters(self, query, filters: CorpusAuditSearchFilter):
        """Apply resource-related filters to query."""
        if filters.corpus_id:
            query = query.where(CorpusAuditLog.corpus_id == filters.corpus_id)
        if filters.resource_type:
            query = query.where(CorpusAuditLog.resource_type == filters.resource_type)
        return query
    
    def _apply_date_filters(self, query, filters: CorpusAuditSearchFilter):
        """Apply date-related filters to query."""
        if filters.start_date:
            query = query.where(CorpusAuditLog.timestamp >= filters.start_date)
        if filters.end_date:
            query = query.where(CorpusAuditLog.timestamp <= filters.end_date)
        return query

    async def count_records(self, db: AsyncSession, filters: CorpusAuditSearchFilter) -> int:
        """Count total records matching search filters."""
        try:
            return await self._execute_count_query(db, filters)
        except Exception as e:
            self._handle_count_error(e, filters)

    async def _execute_count_query(self, db: AsyncSession, filters: CorpusAuditSearchFilter) -> int:
        """Execute count query and return result."""
        query = self._build_count_query(filters)
        result = await db.execute(query)
        return result.scalar() or 0
    
    def _handle_count_error(self, error: Exception, filters: CorpusAuditSearchFilter) -> None:
        """Handle count query errors."""
        logger.error(f"Error counting audit records: {error}")
        raise DatabaseError("Failed to count audit records", context={"filters": filters.model_dump()})

    def _build_count_query(self, filters: CorpusAuditSearchFilter):
        """Build count query with filters applied."""
        query = select(func.count()).select_from(CorpusAuditLog)
        conditions = self._build_count_conditions(filters)
        return self._apply_count_conditions(query, conditions, filters)
    
    def _build_count_conditions(self, filters: CorpusAuditSearchFilter) -> List:
        """Build conditions list for count query."""
        conditions = []
        if filters.user_id:
            conditions.append(CorpusAuditLog.user_id == filters.user_id)
        return self._add_action_status_conditions(conditions, filters)
    
    def _add_action_status_conditions(self, conditions: List, filters: CorpusAuditSearchFilter) -> List:
        """Add action and status conditions to list."""
        if filters.action:
            conditions.append(CorpusAuditLog.action == filters.action.value)
        if filters.status:
            conditions.append(CorpusAuditLog.status == filters.status.value)
        return conditions

    def _apply_count_conditions(self, query, conditions: List, filters: CorpusAuditSearchFilter):
        """Apply remaining conditions to count query."""
        conditions = self._add_remaining_conditions(conditions, filters)
        return query.where(and_(*conditions)) if conditions else query
    
    def _add_remaining_conditions(self, conditions: List, filters: CorpusAuditSearchFilter) -> List:
        """Add remaining filter conditions to list."""
        conditions = self._add_corpus_resource_conditions(conditions, filters)
        conditions = self._add_timestamp_conditions(conditions, filters)
        return conditions
    
    def _add_corpus_resource_conditions(self, conditions: List, filters: CorpusAuditSearchFilter) -> List:
        """Add corpus and resource conditions."""
        if filters.corpus_id:
            conditions.append(CorpusAuditLog.corpus_id == filters.corpus_id)
        if filters.resource_type:
            conditions.append(CorpusAuditLog.resource_type == filters.resource_type)
        return conditions
    
    def _add_timestamp_conditions(self, conditions: List, filters: CorpusAuditSearchFilter) -> List:
        """Add timestamp conditions to list."""
        if filters.start_date:
            conditions.append(CorpusAuditLog.timestamp >= filters.start_date)
        if filters.end_date:
            conditions.append(CorpusAuditLog.timestamp <= filters.end_date)
        return conditions

    async def get_summary_stats(self, db: AsyncSession, filters: CorpusAuditSearchFilter) -> Dict[str, int]:
        """Get summary statistics for audit records."""
        try:
            return await self._execute_summary_query(db)
        except Exception as e:
            return self._handle_summary_error(e)
    
    async def _execute_summary_query(self, db: AsyncSession) -> Dict[str, int]:
        """Execute summary statistics query."""
        query = self._build_summary_query()
        result = await db.execute(query)
        return self._process_summary_results(result.fetchall())
    
    def _build_summary_query(self):
        """Build summary statistics query."""
        return select(
            CorpusAuditLog.action,
            CorpusAuditLog.status,
            func.count().label('count')
        ).group_by(CorpusAuditLog.action, CorpusAuditLog.status)
    
    def _handle_summary_error(self, error: Exception) -> None:
        """Handle summary statistics errors."""
        logger.error(f"Error getting summary stats: {error}")
        raise DatabaseError("Failed to get summary statistics")

    def _process_summary_results(self, results: List) -> Dict[str, int]:
        """Process summary query results into organized stats."""
        stats = {}
        for action, status, count in results:
            key = f"{action}_{status}"
            stats[key] = count
        return stats
    
