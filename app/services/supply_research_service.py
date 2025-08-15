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
    
    def get_supply_items(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        availability_status: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[AISupplyItem]:
        """Get supply items with optional filters"""
        query = self.db.query(AISupplyItem)
        
        if provider:
            query = query.filter(AISupplyItem.provider == provider)
        if model_name:
            query = query.filter(AISupplyItem.model_name.ilike(f"%{model_name}%"))
        if availability_status:
            query = query.filter(AISupplyItem.availability_status == availability_status)
        if min_confidence:
            query = query.filter(AISupplyItem.confidence_score >= min_confidence)
        
        return query.order_by(desc(AISupplyItem.last_updated)).all()
    
    def get_supply_item_by_id(self, item_id: str) -> Optional[AISupplyItem]:
        """Get a specific supply item by ID"""
        return self.db.query(AISupplyItem).filter(AISupplyItem.id == item_id).first()
    
    def create_or_update_supply_item(
        self,
        provider: str,
        model_name: str,
        data: Dict[str, Any],
        research_session_id: Optional[str] = None,
        updated_by: str = "system"
    ) -> AISupplyItem:
        """Create or update a supply item"""
        # Check for existing item
        existing = self.db.query(AISupplyItem).filter(
            and_(
                AISupplyItem.provider == provider,
                AISupplyItem.model_name == model_name
            )
        ).first()
        
        if existing:
            # Track changes for update log
            changes = []
            
            # Update fields if provided
            for field in ['pricing_input', 'pricing_output', 'context_window', 
                         'max_output_tokens', 'capabilities', 'availability_status',
                         'api_endpoints', 'performance_metrics']:
                if field in data and getattr(existing, field) != data[field]:
                    old_value = getattr(existing, field)
                    new_value = data[field]
                    setattr(existing, field, new_value)
                    
                    # Create update log
                    log = SupplyUpdateLog(
                        supply_item_id=existing.id,
                        field_updated=field,
                        old_value=json.dumps(old_value, default=str),
                        new_value=json.dumps(new_value, default=str),
                        research_session_id=research_session_id,
                        update_reason="Supply data update",
                        updated_by=updated_by,
                        updated_at=datetime.now(UTC)
                    )
                    self.db.add(log)
                    changes.append(field)
            
            if changes:
                existing.last_updated = datetime.now(UTC)
                if 'confidence_score' in data:
                    existing.confidence_score = data['confidence_score']
                if 'research_source' in data:
                    existing.research_source = data['research_source']
            
            self.db.commit()
            return existing
        else:
            # Create new item
            new_item = AISupplyItem(
                provider=provider,
                model_name=model_name,
                **data,
                last_updated=datetime.now(UTC)
            )
            self.db.add(new_item)
            self.db.commit()
            
            # Create creation log
            log = SupplyUpdateLog(
                supply_item_id=new_item.id,
                field_updated="*",
                old_value=None,
                new_value=json.dumps({"action": "created"}, default=str),
                research_session_id=research_session_id,
                update_reason="New supply item created",
                updated_by=updated_by,
                updated_at=datetime.now(UTC)
            )
            self.db.add(log)
            self.db.commit()
            
            return new_item
    
    def get_research_sessions(
        self,
        status: Optional[str] = None,
        initiated_by: Optional[str] = None,
        limit: int = 100
    ) -> List[ResearchSession]:
        """Get research sessions with optional filters"""
        query = self.db.query(ResearchSession)
        
        if status:
            query = query.filter(ResearchSession.status == status)
        if initiated_by:
            query = query.filter(ResearchSession.initiated_by == initiated_by)
        
        return query.order_by(desc(ResearchSession.created_at)).limit(limit).all()
    
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
    
    def calculate_price_changes(
        self,
        provider: Optional[str] = None,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """Calculate price changes over a period"""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_back)
        
        # Get price change logs
        query = self.db.query(SupplyUpdateLog).filter(
            and_(
                SupplyUpdateLog.updated_at >= cutoff_date,
                or_(
                    SupplyUpdateLog.field_updated == "pricing_input",
                    SupplyUpdateLog.field_updated == "pricing_output"
                )
            )
        )
        
        if provider:
            # Join with supply items to filter by provider
            query = query.join(AISupplyItem).filter(AISupplyItem.provider == provider)
        
        logs = query.all()
        
        # Analyze changes
        changes = []
        for log in logs:
            try:
                old_val = Decimal(json.loads(log.old_value)) if log.old_value else Decimal(0)
                new_val = Decimal(json.loads(log.new_value)) if log.new_value else Decimal(0)
                
                if old_val > 0:
                    percent_change = ((new_val - old_val) / old_val) * 100
                    
                    supply_item = self.db.query(AISupplyItem).filter(
                        AISupplyItem.id == log.supply_item_id
                    ).first()
                    
                    changes.append({
                        "provider": supply_item.provider if supply_item else "unknown",
                        "model": supply_item.model_name if supply_item else "unknown",
                        "field": log.field_updated,
                        "old_value": float(old_val),
                        "new_value": float(new_val),
                        "percent_change": float(percent_change),
                        "direction": "increase" if percent_change > 0 else "decrease",
                        "updated_at": log.updated_at.isoformat()
                    })
            except Exception as e:
                logger.error(f"Error processing price change log: {e}")
        
        # Sort by percent change magnitude
        changes.sort(key=lambda x: abs(x["percent_change"]), reverse=True)
        
        # Calculate summary statistics
        if changes:
            total_changes = len(changes)
            increases = [c for c in changes if c["direction"] == "increase"]
            decreases = [c for c in changes if c["direction"] == "decrease"]
            
            avg_increase = sum(c["percent_change"] for c in increases) / len(increases) if increases else 0
            avg_decrease = sum(c["percent_change"] for c in decreases) / len(decreases) if decreases else 0
            
            return {
                "period": f"Last {days_back} days",
                "total_changes": total_changes,
                "increases": len(increases),
                "decreases": len(decreases),
                "average_increase_percent": avg_increase,
                "average_decrease_percent": avg_decrease,
                "largest_changes": changes[:10],  # Top 10 changes
                "all_changes": changes
            }
        
        return {
            "period": f"Last {days_back} days",
            "total_changes": 0,
            "message": "No price changes detected"
        }
    
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
        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "sections": {}
        }
        
        # Provider comparison
        report["sections"]["provider_comparison"] = self.get_provider_comparison()
        
        # Recent price changes
        report["sections"]["price_changes"] = {
            "weekly": self.calculate_price_changes(days_back=7),
            "monthly": self.calculate_price_changes(days_back=30)
        }
        
        # Anomalies
        report["sections"]["anomalies"] = self.detect_anomalies()
        
        # Model statistics
        total_models = self.db.query(AISupplyItem).count()
        available_models = self.db.query(AISupplyItem).filter(
            AISupplyItem.availability_status == "available"
        ).count()
        deprecated_models = self.db.query(AISupplyItem).filter(
            AISupplyItem.availability_status == "deprecated"
        ).count()
        
        report["sections"]["statistics"] = {
            "total_models": total_models,
            "available_models": available_models,
            "deprecated_models": deprecated_models,
            "providers_tracked": len(set(item.provider for item in self.get_supply_items()))
        }
        
        # Recent research sessions
        recent_sessions = self.get_research_sessions(limit=10)
        report["sections"]["recent_research"] = [
            {
                "id": str(session.id),
                "query": session.query[:100] + "..." if len(session.query) > 100 else session.query,
                "status": session.status,
                "created_at": session.created_at.isoformat() if session.created_at else None
            }
            for session in recent_sessions
        ]
        
        return report
    
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