"""
Supply Item Operations - CRUD operations for AI supply items
"""

import json
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import AISupplyItem, SupplyUpdateLog
from netra_backend.app.logging_config import central_logger as logger


class SupplyItemOperations:
    """Handles CRUD operations for AI supply items"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _build_supply_items_base_query(self):
        """Build base query for supply items"""
        return self.db.query(AISupplyItem)
    
    def _apply_provider_filter_to_query(self, query, provider: Optional[str]):
        """Apply provider filter to query"""
        if provider:
            return query.filter(AISupplyItem.provider == provider)
        return query
    
    def _apply_model_name_filter(self, query, model_name: Optional[str]):
        """Apply model name filter to query"""
        if model_name:
            return query.filter(AISupplyItem.model_name.ilike(f"%{model_name}%"))
        return query
    
    def _apply_availability_filter(self, query, availability_status: Optional[str]):
        """Apply availability status filter to query"""
        if availability_status:
            return query.filter(AISupplyItem.availability_status == availability_status)
        return query
    
    def _apply_confidence_filter(self, query, min_confidence: Optional[float]):
        """Apply confidence score filter to query"""
        if min_confidence:
            return query.filter(AISupplyItem.confidence_score >= min_confidence)
        return query
    
    def _execute_supply_items_query(self, query):
        """Execute and order supply items query"""
        return query.order_by(desc(AISupplyItem.last_updated)).all()
    
    def _apply_all_filters(self, query, provider: Optional[str], model_name: Optional[str], availability_status: Optional[str], min_confidence: Optional[float]):
        """Apply all filters to the query"""
        query = self._apply_provider_filter_to_query(query, provider)
        query = self._apply_model_name_filter(query, model_name)
        query = self._apply_availability_filter(query, availability_status)
        query = self._apply_confidence_filter(query, min_confidence)
        return query
    
    def get_supply_items(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        availability_status: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[AISupplyItem]:
        """Get supply items with optional filters"""
        query = self._build_supply_items_base_query()
        filtered_query = self._apply_all_filters(query, provider, model_name, availability_status, min_confidence)
        return self._execute_supply_items_query(filtered_query)
    
    def get_supply_item_by_id(self, item_id: str) -> Optional[AISupplyItem]:
        """Get a specific supply item by ID"""
        return self.db.query(AISupplyItem).filter(AISupplyItem.id == item_id).first()
    
    def _find_existing_supply_item(self, provider: str, model_name: str) -> Optional[AISupplyItem]:
        """Find existing supply item by provider and model name"""
        return self.db.query(AISupplyItem).filter(
            and_(
                AISupplyItem.provider == provider,
                AISupplyItem.model_name == model_name
            )
        ).first()
    
    def _get_updatable_fields(self) -> List[str]:
        """Get list of updatable fields for supply items"""
        return [
            'pricing_input', 'pricing_output', 'context_window',
            'max_output_tokens', 'capabilities', 'availability_status',
            'api_endpoints', 'performance_metrics'
        ]
    
    def _prepare_log_values(self, old_value: Any, new_value: Any) -> Tuple[str, str]:
        """Prepare old and new values for logging"""
        old_json = json.dumps(old_value, default=str)
        new_json = json.dumps(new_value, default=str)
        return old_json, new_json
    
    def _create_field_update_log(self, item_id: str, field: str, old_value: Any, new_value: Any, research_session_id: Optional[str], updated_by: str) -> SupplyUpdateLog:
        """Create update log for a field change"""
        old_json, new_json = self._prepare_log_values(old_value, new_value)
        return SupplyUpdateLog(supply_item_id=item_id, field_updated=field, old_value=old_json, new_value=new_json,
                              research_session_id=research_session_id, update_reason="Supply data update",
                              updated_by=updated_by, updated_at=datetime.now(UTC))
    
    def _apply_field_change(self, item: AISupplyItem, field: str, new_value: Any) -> Any:
        """Apply field change and return old value"""
        old_value = getattr(item, field)
        setattr(item, field, new_value)
        return old_value
    
    def _process_field_update(self, item: AISupplyItem, field: str, new_value: Any, research_session_id: Optional[str], updated_by: str) -> bool:
        """Process update for a single field"""
        old_value = getattr(item, field)
        if old_value == new_value:
            return False
        self._apply_field_change(item, field, new_value)
        self.db.add(self._create_field_update_log(item.id, field, old_value, new_value, research_session_id, updated_by))
        return True
    
    def _check_and_update_field(self, item: AISupplyItem, field: str, data: Dict[str, Any], research_session_id: Optional[str], updated_by: str) -> bool:
        """Check if field needs update and apply it"""
        if field in data:
            return self._process_field_update(item, field, data[field], research_session_id, updated_by)
        return False
    
    def _process_all_field_updates(self, item: AISupplyItem, data: Dict[str, Any], research_session_id: Optional[str], updated_by: str) -> List[str]:
        """Process all field updates"""
        changes = []
        for field in self._get_updatable_fields():
            if self._check_and_update_field(item, field, data, research_session_id, updated_by):
                changes.append(field)
        return changes
    
    def _update_metadata_fields(self, existing_item: AISupplyItem, data: Dict[str, Any]) -> None:
        """Update metadata fields if changes were made"""
        existing_item.last_updated = datetime.now(UTC)
        if 'confidence_score' in data:
            existing_item.confidence_score = data['confidence_score']
        if 'research_source' in data:
            existing_item.research_source = data['research_source']
    
    def _update_existing_supply_item(self, item: AISupplyItem, data: Dict[str, Any], research_session_id: Optional[str], updated_by: str) -> AISupplyItem:
        """Update existing supply item"""
        changes = self._process_all_field_updates(item, data, research_session_id, updated_by)
        if changes:
            self._update_metadata_fields(item, data)
        self.db.commit()
        return item
    
    def _build_new_item(self, provider: str, model_name: str, data: Dict[str, Any]) -> AISupplyItem:
        """Build new supply item instance"""
        return AISupplyItem(
            provider=provider, model_name=model_name,
            **data, last_updated=datetime.now(UTC)
        )
    
    def _create_new_supply_item(self, provider: str, model_name: str, data: Dict[str, Any]) -> AISupplyItem:
        """Create new supply item"""
        new_item = self._build_new_item(provider, model_name, data)
        self.db.add(new_item)
        self.db.commit()
        return new_item
    
    def _build_creation_log(self, item_id: str, research_session_id: Optional[str], updated_by: str) -> SupplyUpdateLog:
        """Build creation log entry"""
        return SupplyUpdateLog(supply_item_id=item_id, field_updated="*", old_value=None,
                              new_value=json.dumps({"action": "created"}, default=str),
                              research_session_id=research_session_id, update_reason="New supply item created",
                              updated_by=updated_by, updated_at=datetime.now(UTC))
    
    def _create_item_creation_log(self, item_id: str, research_session_id: Optional[str], updated_by: str) -> None:
        """Create log entry for new item creation"""
        log = self._build_creation_log(item_id, research_session_id, updated_by)
        self.db.add(log)
        self.db.commit()
    
    def create_or_update_supply_item(self, provider: str, model_name: str, data: Dict[str, Any], research_session_id: Optional[str] = None, updated_by: str = "system") -> AISupplyItem:
        """Create or update a supply item"""
        existing = self._find_existing_supply_item(provider, model_name)
        if existing:
            return self._update_existing_supply_item(existing, data, research_session_id, updated_by)
        new_item = self._create_new_supply_item(provider, model_name, data)
        self._create_item_creation_log(new_item.id, research_session_id, updated_by)
        return new_item