"""
Price Analysis Operations - Price change analysis and market reporting
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, desc

from netra_backend.app.db.models_postgres import AISupplyItem, SupplyUpdateLog
from netra_backend.app.logging_config import central_logger as logger


class PriceAnalysisOperations:
    """Handles price analysis, market reports, and anomaly detection"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
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