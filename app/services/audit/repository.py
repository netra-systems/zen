"""
Corpus Audit Repository
Repository layer for corpus audit operations with async patterns.
Focused on database interactions only. ≤300 lines, ≤8 lines per function.
"""

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from app.schemas.registry import CorpusAuditSearchFilter
from app.db.models_postgres import CorpusAuditLog
from app.services.database.base_repository import BaseRepository
from app.logging_config import central_logger
from app.core.exceptions_database import DatabaseError

logger = central_logger.get_logger(__name__)


class CorpusAuditRepository(BaseRepository[CorpusAuditLog]):
    """Repository for corpus audit operations with async patterns."""

    def __init__(self):
        super().__init__(CorpusAuditLog)

    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[CorpusAuditLog]:
        """Find audit records by user ID."""
        try:
            result = await db.execute(
                select(CorpusAuditLog).where(CorpusAuditLog.user_id == user_id)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error finding audit records by user {user_id}: {e}")
            raise DatabaseError(f"Failed to find audit records", context={"user_id": user_id})

    async def search_records(self, db: AsyncSession, filters: CorpusAuditSearchFilter) -> List[CorpusAuditLog]:
        """Search audit records with comprehensive filtering."""
        try:
            query = self._build_search_query(filters)
            result = await db.execute(query.limit(filters.limit).offset(filters.offset))
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error searching audit records: {e}")
            raise DatabaseError("Failed to search audit records", context={"filters": filters.model_dump()})

    def _build_search_query(self, filters: CorpusAuditSearchFilter):
        """Build search query with all filters applied."""
        query = select(CorpusAuditLog).order_by(desc(CorpusAuditLog.timestamp))
        
        if filters.user_id:
            query = query.where(CorpusAuditLog.user_id == filters.user_id)
        if filters.action:
            query = query.where(CorpusAuditLog.action == filters.action.value)
        if filters.status:
            query = query.where(CorpusAuditLog.status == filters.status.value)
        
        return self._apply_additional_filters(query, filters)

    def _apply_additional_filters(self, query, filters: CorpusAuditSearchFilter):
        """Apply additional search filters to query."""
        if filters.corpus_id:
            query = query.where(CorpusAuditLog.corpus_id == filters.corpus_id)
        if filters.resource_type:
            query = query.where(CorpusAuditLog.resource_type == filters.resource_type)
        if filters.start_date:
            query = query.where(CorpusAuditLog.timestamp >= filters.start_date)
        if filters.end_date:
            query = query.where(CorpusAuditLog.timestamp <= filters.end_date)
        
        return query

    async def count_records(self, db: AsyncSession, filters: CorpusAuditSearchFilter) -> int:
        """Count total records matching search filters."""
        try:
            query = self._build_count_query(filters)
            result = await db.execute(query)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting audit records: {e}")
            raise DatabaseError("Failed to count audit records", context={"filters": filters.model_dump()})

    def _build_count_query(self, filters: CorpusAuditSearchFilter):
        """Build count query with filters applied."""
        query = select(func.count()).select_from(CorpusAuditLog)
        
        conditions = []
        if filters.user_id:
            conditions.append(CorpusAuditLog.user_id == filters.user_id)
        if filters.action:
            conditions.append(CorpusAuditLog.action == filters.action.value)
        if filters.status:
            conditions.append(CorpusAuditLog.status == filters.status.value)
        
        return self._apply_count_conditions(query, conditions, filters)

    def _apply_count_conditions(self, query, conditions: List, filters: CorpusAuditSearchFilter):
        """Apply remaining conditions to count query."""
        if filters.corpus_id:
            conditions.append(CorpusAuditLog.corpus_id == filters.corpus_id)
        if filters.resource_type:
            conditions.append(CorpusAuditLog.resource_type == filters.resource_type)
        if filters.start_date:
            conditions.append(CorpusAuditLog.timestamp >= filters.start_date)
        if filters.end_date:
            conditions.append(CorpusAuditLog.timestamp <= filters.end_date)
        
        return query.where(and_(*conditions)) if conditions else query

    async def get_summary_stats(self, db: AsyncSession, filters: CorpusAuditSearchFilter) -> Dict[str, int]:
        """Get summary statistics for audit records."""
        try:
            query = select(
                CorpusAuditLog.action,
                CorpusAuditLog.status,
                func.count().label('count')
            ).group_by(CorpusAuditLog.action, CorpusAuditLog.status)
            
            result = await db.execute(query)
            return self._process_summary_results(result.fetchall())
        except Exception as e:
            logger.error(f"Error getting summary stats: {e}")
            raise DatabaseError("Failed to get summary statistics")

    def _process_summary_results(self, results: List) -> Dict[str, int]:
        """Process summary query results into organized stats."""
        stats = {}
        for action, status, count in results:
            key = f"{action}_{status}"
            stats[key] = count
        return stats