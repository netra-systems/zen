"""
Supply Research Service - Business logic for AI supply research operations
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.core.exceptions_base import NetraException
from app.redis_manager import RedisManager
from app.db.models_postgres import AISupplyItem, ResearchSession, SupplyUpdateLog, User
from app.services.permission_service import PermissionService
from app.logging_config import central_logger as logger



class SupplyResearchService:
    """Service for managing AI supply research operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.redis_manager = None
        self.cache_ttl = 3600  # 1 hour cache
        
        try:
            self.redis_manager = RedisManager()
        except Exception as e:
            logger.warning(f"Redis not available for caching: {e}")
    
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
    
    def get_supply_items(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        availability_status: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[AISupplyItem]:
        """Get supply items with optional filters"""
        query = self._build_supply_items_base_query()
        query = self._apply_provider_filter_to_query(query, provider)
        query = self._apply_model_name_filter(query, model_name)
        query = self._apply_availability_filter(query, availability_status)
        query = self._apply_confidence_filter(query, min_confidence)
        return self._execute_supply_items_query(query)
    
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
    
    def get_research_sessions(
        self,
        status: Optional[str] = None,
        initiated_by: Optional[str] = None,
        limit: int = 100
    ) -> List[ResearchSession]:
        """Get research sessions with optional filters"""
        query = self._build_research_sessions_base_query()
        query = self._apply_status_filter_to_sessions(query, status)
        query = self._apply_initiator_filter_to_sessions(query, initiated_by)
        return self._execute_research_sessions_query(query, limit)
    
    def get_research_session_by_id(self, session_id: str) -> Optional[ResearchSession]:
        """Get a specific research session"""
        return self.db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    
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
        
        if supply_item_id:
            query = query.filter(SupplyUpdateLog.supply_item_id == supply_item_id)
        if updated_by:
            query = query.filter(SupplyUpdateLog.updated_by == updated_by)
        if start_date:
            query = query.filter(SupplyUpdateLog.updated_at >= start_date)
        if end_date:
            query = query.filter(SupplyUpdateLog.updated_at <= end_date)
        
        return query.order_by(desc(SupplyUpdateLog.updated_at)).limit(limit).all()
    
    def _calculate_cutoff_date(self, days_back: int) -> datetime:
        """Calculate cutoff date for price change analysis"""
        return datetime.now(UTC) - timedelta(days=days_back)
    
    def _build_date_filter(self, cutoff_date: datetime):
        """Build date filter for price logs"""
        return SupplyUpdateLog.updated_at >= cutoff_date
    
    def _build_field_filter(self):
        """Build field filter for pricing fields"""
        return or_(
            SupplyUpdateLog.field_updated == "pricing_input",
            SupplyUpdateLog.field_updated == "pricing_output"
        )
    
    def _build_base_price_query(self, cutoff_date: datetime):
        """Build base query for price change logs"""
        date_filter = self._build_date_filter(cutoff_date)
        field_filter = self._build_field_filter()
        return self.db.query(SupplyUpdateLog).filter(and_(date_filter, field_filter))
    
    def _apply_provider_filter(self, query, provider: Optional[str]):
        """Apply provider filter to query if specified"""
        if provider:
            return query.join(AISupplyItem).filter(AISupplyItem.provider == provider)
        return query
    
    def _build_price_change_query(self, cutoff_date: datetime, provider: Optional[str]):
        """Build query for price change logs"""
        base_query = self._build_base_price_query(cutoff_date)
        filtered_query = self._apply_provider_filter(base_query, provider)
        return filtered_query.all()
    
    def _parse_price_values(self, log) -> Tuple[Decimal, Decimal]:
        """Parse old and new price values from log"""
        old_val = Decimal(json.loads(log.old_value)) if log.old_value else Decimal(0)
        new_val = Decimal(json.loads(log.new_value)) if log.new_value else Decimal(0)
        return old_val, new_val
    
    def _calculate_percent_change(self, old_val: Decimal, new_val: Decimal) -> float:
        """Calculate percentage change between old and new values"""
        if old_val <= 0:
            return 0.0
        return float(((new_val - old_val) / old_val) * 100)
    
    def _get_supply_item_info(self, supply_item_id: str) -> Tuple[str, str]:
        """Get provider and model name for supply item"""
        supply_item = self.db.query(AISupplyItem).filter(
            AISupplyItem.id == supply_item_id
        ).first()
        provider = supply_item.provider if supply_item else "unknown"
        model = supply_item.model_name if supply_item else "unknown"
        return provider, model
    
    def _get_direction(self, percent_change: float) -> str:
        """Get direction of price change"""
        return "increase" if percent_change > 0 else "decrease"
    
    def _build_value_data(self, old_val: Decimal, new_val: Decimal, percent_change: float) -> Dict[str, Any]:
        """Build value-related data"""
        return {
            "old_value": float(old_val),
            "new_value": float(new_val),
            "percent_change": percent_change,
            "direction": self._get_direction(percent_change)
        }
    
    def _build_change_record_data(self, log, old_val: Decimal, new_val: Decimal, percent_change: float) -> Dict[str, Any]:
        """Build change record data structure"""
        base_data = {
            "field": log.field_updated,
            "updated_at": log.updated_at.isoformat()
        }
        value_data = self._build_value_data(old_val, new_val, percent_change)
        base_data.update(value_data)
        return base_data
    
    def _create_change_record(self, log, old_val: Decimal, new_val: Decimal, percent_change: float) -> Dict[str, Any]:
        """Create change record from log data"""
        provider, model = self._get_supply_item_info(log.supply_item_id)
        record_data = self._build_change_record_data(log, old_val, new_val, percent_change)
        record_data.update({"provider": provider, "model": model})
        return record_data
    
    def _extract_change_data(self, log) -> Tuple[Decimal, Decimal, float]:
        """Extract change data from log"""
        old_val, new_val = self._parse_price_values(log)
        percent_change = self._calculate_percent_change(old_val, new_val)
        return old_val, new_val, percent_change
    
    def _process_price_change_log(self, log) -> Optional[Dict[str, Any]]:
        """Process individual price change log entry"""
        try:
            old_val, new_val, percent_change = self._extract_change_data(log)
            if percent_change != 0.0:
                return self._create_change_record(log, old_val, new_val, percent_change)
        except Exception as e:
            logger.error(f"Error processing price change log: {e}")
        return None
    
    def _sort_changes_by_magnitude(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort changes by percent change magnitude (highest first)"""
        return sorted(changes, key=lambda x: abs(x["percent_change"]), reverse=True)
    
    def _categorize_changes(self, changes: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Categorize changes into increases and decreases"""
        increases = [c for c in changes if c["direction"] == "increase"]
        decreases = [c for c in changes if c["direction"] == "decrease"]
        return increases, decreases
    
    def _calculate_averages(self, increases: List[Dict[str, Any]], decreases: List[Dict[str, Any]]) -> Tuple[float, float]:
        """Calculate average percentage changes"""
        avg_increase = sum(c["percent_change"] for c in increases) / len(increases) if increases else 0
        avg_decrease = sum(c["percent_change"] for c in decreases) / len(decreases) if decreases else 0
        return avg_increase, avg_decrease
    
    def _build_basic_stats(self, changes: List[Dict[str, Any]], increases: List[Dict[str, Any]], decreases: List[Dict[str, Any]], days_back: int) -> Dict[str, Any]:
        """Build basic statistics structure"""
        return {
            "period": f"Last {days_back} days",
            "total_changes": len(changes),
            "increases": len(increases),
            "decreases": len(decreases)
        }
    
    def _add_averages_and_changes(self, base_stats: Dict[str, Any], avg_increase: float, avg_decrease: float, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add averages and change data to statistics"""
        base_stats.update({
            "average_increase_percent": avg_increase,
            "average_decrease_percent": avg_decrease,
            "largest_changes": changes[:10],
            "all_changes": changes
        })
        return base_stats
    
    def _build_statistics_result(self, changes: List[Dict[str, Any]], increases: List[Dict[str, Any]], 
                                decreases: List[Dict[str, Any]], avg_increase: float, avg_decrease: float, days_back: int) -> Dict[str, Any]:
        """Build statistics result structure"""
        base_stats = self._build_basic_stats(changes, increases, decreases, days_back)
        return self._add_averages_and_changes(base_stats, avg_increase, avg_decrease, changes)
    
    def _calculate_change_statistics(self, changes: List[Dict[str, Any]], days_back: int) -> Dict[str, Any]:
        """Calculate summary statistics for price changes"""
        if not changes:
            return self._create_empty_result(days_back)
        increases, decreases = self._categorize_changes(changes)
        avg_increase, avg_decrease = self._calculate_averages(increases, decreases)
        return self._build_statistics_result(changes, increases, decreases, avg_increase, avg_decrease, days_back)
    
    def _create_empty_result(self, days_back: int) -> Dict[str, Any]:
        """Create empty result when no price changes found"""
        return {
            "period": f"Last {days_back} days",
            "total_changes": 0,
            "message": "No price changes detected"
        }
    
    def _process_logs_to_changes(self, logs) -> List[Dict[str, Any]]:
        """Process logs into change records"""
        return [change for log in logs if (change := self._process_price_change_log(log)) is not None]
    
    def calculate_price_changes(self, provider: Optional[str] = None, days_back: int = 7) -> Dict[str, Any]:
        """Calculate price changes over a period"""
        cutoff_date = self._calculate_cutoff_date(days_back)
        logs = self._build_price_change_query(cutoff_date, provider)
        changes = self._process_logs_to_changes(logs)
        sorted_changes = self._sort_changes_by_magnitude(changes)
        return self._calculate_change_statistics(sorted_changes, days_back)
    
    def get_provider_comparison(self) -> Dict[str, Any]:
        """Get pricing comparison across providers"""
        providers = ["openai", "anthropic", "google", "mistral", "cohere"]
        comparison = {}
        
        for provider in providers:
            items = self.get_supply_items(provider=provider)
            if items:
                # Get flagship model (usually the first/latest)
                flagship = items[0]
                comparison[provider] = {
                    "flagship_model": flagship.model_name,
                    "input_price": float(flagship.pricing_input) if flagship.pricing_input else None,
                    "output_price": float(flagship.pricing_output) if flagship.pricing_output else None,
                    "context_window": flagship.context_window,
                    "last_updated": flagship.last_updated.isoformat() if flagship.last_updated else None,
                    "model_count": len(items)
                }
        
        # Find cheapest and most expensive
        valid_providers = [p for p, d in comparison.items() if d.get("input_price")]
        if valid_providers:
            cheapest_input = min(valid_providers, key=lambda p: comparison[p]["input_price"])
            expensive_input = max(valid_providers, key=lambda p: comparison[p]["input_price"])
            
            return {
                "providers": comparison,
                "analysis": {
                    "cheapest_input": {
                        "provider": cheapest_input,
                        "price": comparison[cheapest_input]["input_price"]
                    },
                    "most_expensive_input": {
                        "provider": expensive_input,
                        "price": comparison[expensive_input]["input_price"]
                    },
                    "price_spread": comparison[expensive_input]["input_price"] - comparison[cheapest_input]["input_price"]
                }
            }
        
        return {"providers": comparison, "analysis": {}}
    
    def detect_anomalies(self, threshold: float = 0.2) -> List[Dict[str, Any]]:
        """Detect pricing anomalies (significant deviations)"""
        anomalies = []
        
        # Get recent price changes
        changes = self.calculate_price_changes(days_back=30)
        
        for change in changes.get("all_changes", []):
            if abs(change["percent_change"]) > threshold * 100:  # threshold is in decimal
                anomalies.append({
                    "type": "significant_price_change",
                    "provider": change["provider"],
                    "model": change["model"],
                    "field": change["field"],
                    "percent_change": change["percent_change"],
                    "severity": "high" if abs(change["percent_change"]) > 50 else "medium",
                    "detected_at": change["updated_at"]
                })
        
        # Check for missing updates (models not updated in a while)
        stale_cutoff = datetime.now(UTC) - timedelta(days=30)
        stale_items = self.db.query(AISupplyItem).filter(
            AISupplyItem.last_updated < stale_cutoff
        ).all()
        
        for item in stale_items:
            anomalies.append({
                "type": "stale_data",
                "provider": item.provider,
                "model": item.model_name,
                "last_updated": item.last_updated.isoformat() if item.last_updated else None,
                "severity": "low"
            })
        
        return anomalies
    
    async def generate_market_report(self) -> Dict[str, Any]:
        """Generate comprehensive market report"""
        report = self._initialize_report_structure()
        await self._populate_report_sections(report)
        return report
    
    def _initialize_report_structure(self) -> Dict[str, Any]:
        """Initialize the base report structure."""
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "sections": {}
        }
    
    async def _populate_report_sections(self, report: Dict[str, Any]) -> None:
        """Populate all report sections."""
        report["sections"]["provider_comparison"] = self.get_provider_comparison()
        report["sections"]["price_changes"] = self._generate_price_changes_section()
        report["sections"]["anomalies"] = self.detect_anomalies()
        report["sections"]["statistics"] = self._generate_statistics_section()
        report["sections"]["recent_research"] = self._generate_research_section()
    
    def _generate_price_changes_section(self) -> Dict[str, Any]:
        """Generate price changes section of the report."""
        return {
            "weekly": self.calculate_price_changes(days_back=7),
            "monthly": self.calculate_price_changes(days_back=30)
        }
    
    def _generate_statistics_section(self) -> Dict[str, Any]:
        """Generate model statistics section."""
        model_counts = self._get_model_counts()
        providers_count = self._get_providers_count()
        return {**model_counts, "providers_tracked": providers_count}
    
    def _get_model_counts(self) -> Dict[str, int]:
        """Get various model counts for statistics."""
        total_models = self.db.query(AISupplyItem).count()
        available_models = self.db.query(AISupplyItem).filter(
            AISupplyItem.availability_status == "available").count()
        deprecated_models = self.db.query(AISupplyItem).filter(
            AISupplyItem.availability_status == "deprecated").count()
        return {"total_models": total_models, "available_models": available_models, "deprecated_models": deprecated_models}
    
    def _get_providers_count(self) -> int:
        """Get count of unique providers tracked."""
        all_items = self.get_supply_items()
        return len(set(item.provider for item in all_items))
    
    def _generate_research_section(self) -> List[Dict[str, Any]]:
        """Generate recent research sessions section."""
        recent_sessions = self.get_research_sessions(limit=10)
        return [self._format_session_summary(session) for session in recent_sessions]
    
    def _format_session_summary(self, session) -> Dict[str, Any]:
        """Format a single research session for the report."""
        query_summary = session.query[:100] + "..." if len(session.query) > 100 else session.query
        return {
            "id": str(session.id), "query": query_summary, "status": session.status,
            "created_at": session.created_at.isoformat() if session.created_at else None
        }
    
    def validate_supply_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate supply data before storage"""
        errors = []
        
        # Required fields
        required = ["provider", "model_name"]
        for field in required:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate pricing (if provided)
        if "pricing_input" in data:
            try:
                val = Decimal(str(data["pricing_input"]))
                if val < 0:
                    errors.append("Input pricing cannot be negative")
                if val > 10000:  # Sanity check - $10,000 per 1M tokens seems unrealistic
                    errors.append("Input pricing seems unrealistically high")
            except:
                errors.append("Invalid input pricing format")
        
        if "pricing_output" in data:
            try:
                val = Decimal(str(data["pricing_output"]))
                if val < 0:
                    errors.append("Output pricing cannot be negative")
                if val > 10000:
                    errors.append("Output pricing seems unrealistically high")
            except:
                errors.append("Invalid output pricing format")
        
        # Validate context window
        if "context_window" in data:
            try:
                val = int(data["context_window"])
                if val < 0:
                    errors.append("Context window cannot be negative")
                if val > 10000000:  # 10M tokens seems like a reasonable upper limit
                    errors.append("Context window seems unrealistically large")
            except:
                errors.append("Invalid context window format")
        
        # Validate confidence score
        if "confidence_score" in data:
            try:
                val = float(data["confidence_score"])
                if val < 0 or val > 1:
                    errors.append("Confidence score must be between 0 and 1")
            except:
                errors.append("Invalid confidence score format")
        
        # Validate availability status
        if "availability_status" in data:
            valid_statuses = ["available", "deprecated", "preview", "waitlist"]
            if data["availability_status"] not in valid_statuses:
                errors.append(f"Invalid availability status. Must be one of: {valid_statuses}")
        
        return len(errors) == 0, errors