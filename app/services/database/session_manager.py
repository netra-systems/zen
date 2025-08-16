"""Session Management Module

Handles database session validation and management for repositories.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import DatabaseError


class SessionManager:
    """Handles database session validation and management"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
    
    def validate_session(self, db: Optional[AsyncSession], session: Optional[AsyncSession] = None) -> AsyncSession:
        """Validate and return database session."""
        validated_session = db or session
        if not validated_session:
            raise DatabaseError(
                message="No database session available",
                context={"repository": self.model_name}
            )
        return validated_session
    
    def validate_session_with_id(self, db: Optional[AsyncSession], entity_id: str, session: Optional[AsyncSession] = None) -> AsyncSession:
        """Validate session for operations requiring entity ID."""
        validated_session = db or session
        if not validated_session:
            raise DatabaseError(
                message="No database session available",
                context={"repository": self.model_name, "entity_id": entity_id}
            )
        return validated_session