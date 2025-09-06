"""Supply Database Manager - Database operations for supply research agent.

This module provides specialized database operations for the supply researcher agent,
working with supply items and research sessions.
"""

import json
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_

from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.db.models_postgres import (
    AISupplyItem,
    ResearchSession,
    SupplyUpdateLog
)


class SupplyDatabaseManager:
    """Manages database operations for supply research data."""
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session.
        
        Args:
            db: AsyncSession for database operations
        """
        self.db = db
    
    async def update_database(
        self, 
        supply_items: List[Dict[str, Any]], 
        research_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update database with supply research results.
        
        Args:
            supply_items: List of supply item data dictionaries
            research_session_id: Optional research session ID for tracking
            
        Returns:
            Dictionary with update counts and details
        """
        update_result = {
            "updates_count": 0,
            "updates": [],
            "created_count": 0,
            "created": [],
            "errors": []
        }
        
        for item in supply_items:
            try:
                result = await self._process_supply_item(item, research_session_id)
                if result["action"] == "created":
                    update_result["created_count"] += 1
                    update_result["created"].append(result)
                elif result["action"] == "updated":
                    update_result["updates_count"] += 1
                    update_result["updates"].append(result)
            except Exception as e:
                logger.error(f"Error processing supply item {item.get('model_name', 'unknown')}: {e}")
                update_result["errors"].append({
                    "item": item.get("model_name", "unknown"),
                    "error": str(e)
                })
        
        # Commit all changes
        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error committing supply updates: {e}")
            await self.db.rollback()
            raise
        
        return update_result
    
    async def _process_supply_item(
        self, 
        item_data: Dict[str, Any],
        research_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a single supply item update.
        
        Args:
            item_data: Supply item data dictionary
            research_session_id: Optional research session ID
            
        Returns:
            Dictionary with action taken and details
        """
        provider = item_data.get("provider", "unknown")
        model_name = item_data.get("model_name", "unknown")
        
        # Check if item exists
        existing_item = await self._find_existing_supply_item(provider, model_name)
        
        if existing_item:
            # Update existing item
            return await self._update_existing_item(existing_item, item_data, research_session_id)
        else:
            # Create new item
            return await self._create_new_item(item_data, research_session_id)
    
    async def _find_existing_supply_item(
        self, 
        provider: str, 
        model_name: str
    ) -> Optional[AISupplyItem]:
        """Find existing supply item by provider and model name.
        
        Args:
            provider: Provider name
            model_name: Model name
            
        Returns:
            Existing AISupplyItem or None
        """
        from sqlalchemy import select
        
        stmt = select(AISupplyItem).where(
            and_(
                AISupplyItem.provider == provider,
                AISupplyItem.model_name == model_name
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _update_existing_item(
        self,
        existing_item: AISupplyItem,
        item_data: Dict[str, Any],
        research_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing supply item.
        
        Args:
            existing_item: Existing AISupplyItem instance
            item_data: New data for the item
            research_session_id: Optional research session ID
            
        Returns:
            Dictionary with update details
        """
        updates_made = []
        
        # Track changes for each field
        updatable_fields = [
            'pricing_input', 'pricing_output', 'context_window',
            'max_output_tokens', 'capabilities', 'availability_status',
            'api_endpoints', 'performance_metrics', 'confidence_score'
        ]
        
        for field in updatable_fields:
            if field in item_data:
                old_value = getattr(existing_item, field, None)
                new_value = item_data[field]
                
                if old_value != new_value:
                    setattr(existing_item, field, new_value)
                    updates_made.append({
                        "field": field,
                        "old_value": old_value,
                        "new_value": new_value
                    })
                    
                    # Create update log
                    await self._create_update_log(
                        existing_item.id,
                        field,
                        old_value,
                        new_value,
                        research_session_id
                    )
        
        # Update timestamps and research source
        existing_item.last_updated = datetime.now(UTC)
        if research_session_id:
            existing_item.research_source = research_session_id
        
        return {
            "action": "updated",
            "item_id": existing_item.id,
            "provider": existing_item.provider,
            "model_name": existing_item.model_name,
            "updates": updates_made
        }
    
    async def _create_new_item(
        self,
        item_data: Dict[str, Any],
        research_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new supply item.
        
        Args:
            item_data: Supply item data
            research_session_id: Optional research session ID
            
        Returns:
            Dictionary with creation details
        """
        import uuid
        
        new_item = AISupplyItem(
            id=str(uuid.uuid4()),
            provider=item_data.get("provider", "unknown"),
            model_name=item_data.get("model_name", "unknown"),
            model_version=item_data.get("model_version"),
            pricing_input=item_data.get("pricing_input"),
            pricing_output=item_data.get("pricing_output"),
            pricing_currency=item_data.get("pricing_currency", "USD"),
            context_window=item_data.get("context_window"),
            max_output_tokens=item_data.get("max_output_tokens"),
            capabilities=item_data.get("capabilities", {}),
            availability_status=item_data.get("availability_status", "available"),
            api_endpoints=item_data.get("api_endpoints", {}),
            performance_metrics=item_data.get("performance_metrics", {}),
            confidence_score=item_data.get("confidence_score", 0.5),
            research_source=research_session_id,  # Store session ID as research source
            last_updated=datetime.now(UTC),
            created_at=datetime.now(UTC)
        )
        
        self.db.add(new_item)
        
        # Create initial log entry
        await self._create_update_log(
            new_item.id,
            "created",
            None,
            "Initial creation",
            research_session_id
        )
        
        return {
            "action": "created",
            "item_id": new_item.id,
            "provider": new_item.provider,
            "model_name": new_item.model_name
        }
    
    async def _create_update_log(
        self,
        supply_item_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        research_session_id: Optional[str] = None
    ) -> None:
        """Create a supply update log entry.
        
        Args:
            supply_item_id: ID of the supply item
            field_name: Name of the field being updated
            old_value: Previous value
            new_value: New value
            research_session_id: Optional research session ID
        """
        import uuid
        
        log_entry = SupplyUpdateLog(
            id=str(uuid.uuid4()),
            supply_item_id=supply_item_id,
            field_name=field_name,
            old_value=json.dumps(old_value, default=str) if old_value is not None else None,
            new_value=json.dumps(new_value, default=str) if new_value is not None else None,
            research_session_id=research_session_id,
            updated_by="supply_researcher_agent",
            updated_at=datetime.now(UTC)
        )
        
        self.db.add(log_entry)
        
    async def get_supply_statistics(self) -> Dict[str, Any]:
        """Get statistics about supply items in the database.
        
        Returns:
            Dictionary with supply statistics
        """
        from sqlalchemy import select, func
        
        # Count total items
        total_stmt = select(func.count(AISupplyItem.id))
        total_result = await self.db.execute(total_stmt)
        total_count = total_result.scalar()
        
        # Count by provider
        provider_stmt = select(
            AISupplyItem.provider,
            func.count(AISupplyItem.id)
        ).group_by(AISupplyItem.provider)
        provider_result = await self.db.execute(provider_stmt)
        provider_counts = dict(provider_result.all())
        
        # Count by availability status
        status_stmt = select(
            AISupplyItem.availability_status,
            func.count(AISupplyItem.id)
        ).group_by(AISupplyItem.availability_status)
        status_result = await self.db.execute(status_stmt)
        status_counts = dict(status_result.all())
        
        return {
            "total_items": total_count,
            "by_provider": provider_counts,
            "by_availability": status_counts
        }