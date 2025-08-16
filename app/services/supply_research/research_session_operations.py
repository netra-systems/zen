"""
Research Session Operations - Management of research sessions and update logs
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.models_postgres import ResearchSession, SupplyUpdateLog
from app.logging_config import central_logger as logger


class ResearchSessionOperations:
    """Handles research session management and update logging"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _build_research_sessions_base_query(self):
        """Build base query for research sessions"""
        return self.db.query(ResearchSession)
    
    def _apply_status_filter_to_sessions(self, query, status: Optional[str]):
        """Apply status filter to research sessions query"""
        if status:
            return query.filter(ResearchSession.status == status)
        return query
    
    def _apply_initiator_filter_to_sessions(self, query, initiated_by: Optional[str]):
        """Apply initiator filter to research sessions query"""
        if initiated_by:
            return query.filter(ResearchSession.initiated_by == initiated_by)
        return query
    
    def _execute_research_sessions_query(self, query, limit: int):
        """Execute research sessions query with ordering and limit"""
        return query.order_by(desc(ResearchSession.created_at)).limit(limit).all()
    
    def _apply_session_filters(self, query, status: Optional[str], initiated_by: Optional[str]):
        """Apply filters to research sessions query"""
        query = self._apply_status_filter_to_sessions(query, status)
        query = self._apply_initiator_filter_to_sessions(query, initiated_by)
        return query
    
    def get_research_sessions(
        self,
        status: Optional[str] = None,
        initiated_by: Optional[str] = None,
        limit: int = 100
    ) -> List[ResearchSession]:
        """Get research sessions with optional filters"""
        query = self._build_research_sessions_base_query()
        filtered_query = self._apply_session_filters(query, status, initiated_by)
        return self._execute_research_sessions_query(filtered_query, limit)
    
    def get_research_session_by_id(self, session_id: str) -> Optional[ResearchSession]:
        """Get a specific research session"""
        return self.db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    
    def _apply_log_item_filter(self, query, supply_item_id: Optional[str]):
        """Apply supply item ID filter to logs query"""
        if supply_item_id:
            return query.filter(SupplyUpdateLog.supply_item_id == supply_item_id)
        return query
    
    def _apply_log_user_filter(self, query, updated_by: Optional[str]):
        """Apply updated by user filter to logs query"""
        if updated_by:
            return query.filter(SupplyUpdateLog.updated_by == updated_by)
        return query
    
    def _apply_log_date_filters(self, query, start_date: Optional[datetime], end_date: Optional[datetime]):
        """Apply date range filters to logs query"""
        if start_date:
            query = query.filter(SupplyUpdateLog.updated_at >= start_date)
        if end_date:
            query = query.filter(SupplyUpdateLog.updated_at <= end_date)
        return query
    
    def _apply_all_log_filters(self, query, supply_item_id: Optional[str], updated_by: Optional[str], start_date: Optional[datetime], end_date: Optional[datetime]):
        """Apply all filters to update logs query"""
        query = self._apply_log_item_filter(query, supply_item_id)
        query = self._apply_log_user_filter(query, updated_by)
        query = self._apply_log_date_filters(query, start_date, end_date)
        return query
    
    def get_update_logs(
        self,
        supply_item_id: Optional[str] = None,
        updated_by: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SupplyUpdateLog]:
        """Get supply update logs with filters"""
        query = self.db.query(SupplyUpdateLog)
        filtered_query = self._apply_all_log_filters(query, supply_item_id, updated_by, start_date, end_date)
        return filtered_query.order_by(desc(SupplyUpdateLog.updated_at)).limit(limit).all()
    
    def _generate_research_section(self) -> List[Dict[str, str]]:
        """Generate recent research sessions section."""
        recent_sessions = self.get_research_sessions(limit=10)
        return [self._format_session_summary(session) for session in recent_sessions]
    
    def _format_session_summary(self, session) -> Dict[str, str]:
        """Format a single research session for the report."""
        query_summary = session.query[:100] + "..." if len(session.query) > 100 else session.query
        return {
            "id": str(session.id), "query": query_summary, "status": session.status,
            "created_at": session.created_at.isoformat() if session.created_at else None
        }