"""
Supply Database Manager

Manages database operations for supply research results.
Maintains 25-line function limit and focused database logic.
"""

from typing import Dict, Any, List
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.db.models_postgres import AISupplyItem, SupplyUpdateLog
from netra_backend.app.logging_config import central_logger as logger


class SupplyDatabaseManager:
    """Manages database operations for supply research"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def update_database(
        self,
        supply_items: List[Dict[str, Any]],
        research_session_id: str
    ) -> Dict[str, Any]:
        """Update database with new supply information"""
        updates_made = self._process_supply_items(supply_items, research_session_id)
        return self._finalize_updates(updates_made)
    
    def _process_supply_items(
        self, 
        supply_items: List[Dict[str, Any]], 
        research_session_id: str
    ) -> List[Dict[str, Any]]:
        """Process all supply items for database updates"""
        updates_made = []
        for item_data in supply_items:
            update = self._process_single_item(item_data, research_session_id)
            if update:
                updates_made.append(update)
        return updates_made
    
    def _process_single_item(
        self, 
        item_data: Dict[str, Any], 
        research_session_id: str
    ) -> Dict[str, Any] | None:
        """Process single supply item with error handling"""
        try:
            existing = self._find_existing_item(item_data)
            return self._handle_item_update(existing, item_data, research_session_id)
        except Exception as e:
            logger.error(f"Failed to update supply item: {e}")
            return None
    
    def _handle_item_update(
        self, 
        existing: AISupplyItem | None, 
        item_data: Dict[str, Any], 
        research_session_id: str
    ) -> Dict[str, Any]:
        """Handle update or creation of supply item"""
        if existing:
            return self._update_existing_item(existing, item_data, research_session_id)
        return self._create_new_item(item_data)
    
    def _finalize_updates(self, updates_made: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Finalize database updates and return summary"""
        if updates_made:
            self.db.commit()
        return {
            "updates_count": len(updates_made),
            "updates": updates_made
        }
    
    def _find_existing_item(self, item_data: Dict[str, Any]) -> AISupplyItem:
        """Find existing supply item in database"""
        return self.db.query(AISupplyItem).filter(
            AISupplyItem.provider == item_data["provider"],
            AISupplyItem.model_name == item_data["model_name"]
        ).first()
    
    def _update_existing_item(
        self,
        existing: AISupplyItem,
        item_data: Dict[str, Any],
        research_session_id: str
    ) -> Dict[str, Any] | None:
        """Update existing supply item"""
        changes = self._detect_changes(existing, item_data)
        return self._apply_changes_if_needed(existing, item_data, changes, research_session_id)
    
    def _apply_changes_if_needed(
        self,
        existing: AISupplyItem,
        item_data: Dict[str, Any],
        changes: List[Dict[str, Any]],
        research_session_id: str
    ) -> Dict[str, Any] | None:
        """Apply changes if any detected"""
        if not changes:
            return None
        self._apply_changes(existing, item_data)
        self._create_update_logs(existing, changes, research_session_id)
        return self._build_update_result(existing, changes)
    
    def _create_new_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new supply item"""
        new_item = AISupplyItem(**item_data)
        self.db.add(new_item)
        
        return {
            "action": "created",
            "model": f"{item_data['provider']} {item_data['model_name']}"
        }
    
    def _detect_changes(
        self,
        existing: AISupplyItem,
        item_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect changes between existing and new data"""
        changes = []
        self._check_pricing_input_change(changes, existing, item_data)
        self._check_pricing_output_change(changes, existing, item_data)
        return changes
    
    def _check_pricing_input_change(
        self, 
        changes: List[Dict[str, Any]], 
        existing: AISupplyItem, 
        item_data: Dict[str, Any]
    ) -> None:
        """Check and record pricing input changes"""
        if self._pricing_input_changed(existing, item_data):
            change_record = self._create_change_record(
                "pricing_input", existing.pricing_input, item_data["pricing_input"]
            )
            changes.append(change_record)
    
    def _check_pricing_output_change(
        self, 
        changes: List[Dict[str, Any]], 
        existing: AISupplyItem, 
        item_data: Dict[str, Any]
    ) -> None:
        """Check and record pricing output changes"""
        if self._pricing_output_changed(existing, item_data):
            change_record = self._create_change_record(
                "pricing_output", existing.pricing_output, item_data["pricing_output"]
            )
            changes.append(change_record)
    
    def _create_change_record(self, field: str, old_value: Any, new_value: Any) -> Dict[str, Any]:
        """Create a change record dictionary"""
        return {
            "field": field,
            "old": str(old_value),
            "new": str(new_value)
        }
    
    def _build_update_result(
        self, 
        existing: AISupplyItem, 
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build update result dictionary"""
        return {
            "action": "updated",
            "model": f"{existing.provider} {existing.model_name}",
            "changes": changes
        }
    
    def _apply_changes(self, existing: AISupplyItem, item_data: Dict[str, Any]) -> None:
        """Apply changes to existing item"""
        self._update_pricing_fields(existing, item_data)
        self._update_metadata_fields(existing, item_data)
    
    def _update_pricing_fields(self, existing: AISupplyItem, item_data: Dict[str, Any]) -> None:
        """Update pricing fields if provided"""
        if item_data.get("pricing_input"):
            existing.pricing_input = item_data["pricing_input"]
        if item_data.get("pricing_output"):
            existing.pricing_output = item_data["pricing_output"]
    
    def _update_metadata_fields(self, existing: AISupplyItem, item_data: Dict[str, Any]) -> None:
        """Update metadata fields"""
        existing.last_updated = datetime.now(UTC)
        existing.research_source = item_data["research_source"]
        existing.confidence_score = item_data["confidence_score"]
    
    def _create_update_logs(
        self,
        existing: AISupplyItem,
        changes: List[Dict[str, Any]],
        research_session_id: str
    ) -> None:
        """Create update logs for changes"""
        for change in changes:
            log = self._build_update_log(existing, change, research_session_id)
            self.db.add(log)
    
    def _build_update_log(
        self, 
        existing: AISupplyItem, 
        change: Dict[str, Any], 
        research_session_id: str
    ) -> SupplyUpdateLog:
        """Build a single update log entry"""
        log_data = self._get_log_base_data(existing, research_session_id)
        log_data.update(self._get_change_data(change))
        return SupplyUpdateLog(**log_data)
    
    def _get_log_base_data(self, existing: AISupplyItem, research_session_id: str) -> Dict[str, Any]:
        """Get base data for update log"""
        return {
            "supply_item_id": existing.id,
            "research_session_id": research_session_id,
            "update_reason": "Research update",
            "updated_by": "SupplyResearcherAgent",
            "updated_at": datetime.now(UTC)
        }
    
    def _get_change_data(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Get change-specific data for update log"""
        return {
            "field_updated": change["field"],
            "old_value": change["old"],
            "new_value": change["new"]
        }
    
    def _pricing_input_changed(
        self,
        existing: AISupplyItem,
        item_data: Dict[str, Any]
    ) -> bool:
        """Check if pricing input changed"""
        return (item_data.get("pricing_input") and 
                existing.pricing_input != item_data["pricing_input"])
    
    def _pricing_output_changed(
        self,
        existing: AISupplyItem,
        item_data: Dict[str, Any]
    ) -> bool:
        """Check if pricing output changed"""
        return (item_data.get("pricing_output") and 
                existing.pricing_output != item_data["pricing_output"])