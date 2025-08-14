"""
Supply Database Manager

Manages database operations for supply research results.
Maintains 8-line function limit and focused database logic.
"""

from typing import Dict, Any, List
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from app.db.models_postgres import AISupplyItem, SupplyUpdateLog
from app.logging_config import central_logger as logger


class SupplyDatabaseManager:
    """Manages database operations for supply research"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def update_database(
        self,
        supply_items: List[Dict[str, Any]],
        research_session_id: str
    ) -> Dict[str, Any]:
        """Update database with new supply information"""
        updates_made = []
        
        for item_data in supply_items:
            try:
                existing = self._find_existing_item(item_data)
                
                if existing:
                    updates = self._update_existing_item(existing, item_data, research_session_id)
                    if updates:
                        updates_made.append(updates)
                else:
                    updates_made.append(self._create_new_item(item_data))
            
            except Exception as e:
                logger.error(f"Failed to update supply item: {e}")
        
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
    ) -> Dict[str, Any]:
        """Update existing supply item"""
        changes = self._detect_changes(existing, item_data)
        
        if changes:
            self._apply_changes(existing, item_data)
            self._create_update_logs(existing, changes, research_session_id)
            
            return {
                "action": "updated",
                "model": f"{existing.provider} {existing.model_name}",
                "changes": changes
            }
        
        return None
    
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
        
        if self._pricing_input_changed(existing, item_data):
            changes.append({
                "field": "pricing_input",
                "old": str(existing.pricing_input),
                "new": str(item_data["pricing_input"])
            })
        
        if self._pricing_output_changed(existing, item_data):
            changes.append({
                "field": "pricing_output",
                "old": str(existing.pricing_output),
                "new": str(item_data["pricing_output"])
            })
        
        return changes
    
    def _apply_changes(self, existing: AISupplyItem, item_data: Dict[str, Any]) -> None:
        """Apply changes to existing item"""
        if item_data.get("pricing_input"):
            existing.pricing_input = item_data["pricing_input"]
        if item_data.get("pricing_output"):
            existing.pricing_output = item_data["pricing_output"]
        
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
            log = SupplyUpdateLog(
                supply_item_id=existing.id,
                field_updated=change["field"],
                old_value=change["old"],
                new_value=change["new"],
                research_session_id=research_session_id,
                update_reason="Research update",
                updated_by="SupplyResearcherAgent",
                updated_at=datetime.now(UTC)
            )
            self.db.add(log)
    
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