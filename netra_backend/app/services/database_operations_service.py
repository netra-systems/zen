"""
Database Operations Service
Provides service layer abstractions for direct database operations used in routes
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select as future_select

from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.db.models_content import Reference
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DatabaseOperationsService:
    """Service layer for database operations abstraction."""
    
    # PostgreSQL operations
    async def execute_postgres_health_check(self, db: AsyncSession) -> bool:
        """Execute PostgreSQL health check query."""
        try:
            result = await db.execute(text("SELECT 1"))
            result.scalar_one_or_none()
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False
    
    # ClickHouse operations  
    async def execute_clickhouse_health_check(self) -> bool:
        """Execute ClickHouse health check."""
        try:
            async with get_clickhouse_client() as client:
                await client.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {e}")
            return False
    
    async def list_clickhouse_tables(self) -> List[str]:
        """List all ClickHouse tables."""
        try:
            async with get_clickhouse_client() as client:
                result = await client.execute_query("SHOW TABLES")
                if result:
                    return [row[0] for row in result]
                return []
        except Exception as e:
            logger.error(f"Failed to list ClickHouse tables: {e}")
            raise
    
    # Reference model operations
    async def get_references_count(self, db: AsyncSession) -> int:
        """Get total count of references."""
        count_result = await db.execute(select(func.count(Reference.id)))
        return count_result.scalar()
    
    async def get_paginated_references(self, db: AsyncSession, offset: int, limit: int) -> List[Reference]:
        """Get paginated references."""
        query = select(Reference).offset(offset).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def search_references(self, db: AsyncSession, query: Optional[str]) -> List[Reference]:
        """Search references by name or description."""
        base_query = select(Reference)
        if query:
            search_filter = or_(
                Reference.name.ilike(f"%{query}%"), 
                Reference.description.ilike(f"%{query}%")
            )
            base_query = base_query.filter(search_filter)
        
        result = await db.execute(base_query)
        return result.scalars().all()
    
    async def get_reference_by_id(self, db: AsyncSession, reference_id: str) -> Optional[Reference]:
        """Get reference by ID."""
        result = await db.execute(select(Reference).filter(Reference.id == reference_id))
        return result.scalars().first()
    
    async def create_reference(self, db: AsyncSession, reference_data: Dict[str, Any]) -> Reference:
        """Create reference in database."""
        db_reference = Reference(**reference_data)
        db.add(db_reference)
        await db.commit()
        await db.refresh(db_reference)
        return db_reference
    
    async def update_reference(self, db: AsyncSession, db_reference: Reference, update_data: Dict[str, Any]) -> Reference:
        """Update reference in database."""
        for key, value in update_data.items():
            setattr(db_reference, key, value)
        await db.commit()
        await db.refresh(db_reference)
        return db_reference
    
    async def delete_reference(self, db: AsyncSession, db_reference: Reference) -> Dict[str, str]:
        """Delete reference from database."""
        await db.delete(db_reference)
        await db.commit()
        return {"status": "deleted"}


# Singleton instance
database_operations_service = DatabaseOperationsService()