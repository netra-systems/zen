"""
Market Operations - Provider comparison, anomaly detection, and market reporting
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models_postgres import AISupplyItem
from netra_backend.app.supply_item_operations import SupplyItemOperations
from netra_backend.app.price_analysis_operations import PriceAnalysisOperations
from netra_backend.app.research_session_operations import ResearchSessionOperations
from app.logging_config import central_logger as logger


class MarketOperations:
    """Handles market analysis, provider comparison, and anomaly detection"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.supply_ops = SupplyItemOperations(db)
        self.price_ops = PriceAnalysisOperations(db) 
        self.research_ops = ResearchSessionOperations(db)
    
    def _get_provider_list(self) -> List[str]:
        """Get list of providers to compare"""
        return ["openai", "anthropic", "google", "mistral", "cohere"]
    
    def _build_flagship_data(self, flagship, items_count: int) -> Dict[str, Any]:
        """Build flagship model data for provider"""
        return {
            "flagship_model": flagship.model_name,
            "input_price": float(flagship.pricing_input) if flagship.pricing_input else None,
            "output_price": float(flagship.pricing_output) if flagship.pricing_output else None,
            "context_window": flagship.context_window,
            "last_updated": flagship.last_updated.isoformat() if flagship.last_updated else None,
            "model_count": items_count
        }
    
    def _build_provider_comparison_data(self) -> Dict[str, Any]:
        """Build comparison data for all providers"""
        providers = self._get_provider_list()
        comparison = {}
        for provider in providers:
            items = self.supply_ops.get_supply_items(provider=provider)
            if items:
                flagship = items[0]  # Get flagship model (usually the first/latest)
                comparison[provider] = self._build_flagship_data(flagship, len(items))
        return comparison
    
    def _get_valid_providers(self, comparison: Dict[str, Any]) -> List[str]:
        """Get providers with valid pricing data"""
        return [p for p, d in comparison.items() if d.get("input_price")]
    
    def _build_price_analysis(self, comparison: Dict[str, Any], valid_providers: List[str]) -> Dict[str, Any]:
        """Build price analysis for valid providers"""
        cheapest = min(valid_providers, key=lambda p: comparison[p]["input_price"])
        expensive = max(valid_providers, key=lambda p: comparison[p]["input_price"])
        return {
            "cheapest_input": {"provider": cheapest, "price": comparison[cheapest]["input_price"]},
            "most_expensive_input": {"provider": expensive, "price": comparison[expensive]["input_price"]},
            "price_spread": comparison[expensive]["input_price"] - comparison[cheapest]["input_price"]
        }
    
    def get_provider_comparison(self) -> Dict[str, Any]:
        """Get pricing comparison across providers"""
        comparison = self._build_provider_comparison_data()
        valid_providers = self._get_valid_providers(comparison)
        if valid_providers:
            analysis = self._build_price_analysis(comparison, valid_providers)
            return {"providers": comparison, "analysis": analysis}
        return {"providers": comparison, "analysis": {}}
    
    def _build_price_change_anomaly(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Build anomaly record for significant price change"""
        return {
            "type": "significant_price_change",
            "provider": change["provider"],
            "model": change["model"],
            "field": change["field"],
            "percent_change": change["percent_change"],
            "severity": "high" if abs(change["percent_change"]) > 50 else "medium",
            "detected_at": change["updated_at"]
        }
    
    def _detect_price_change_anomalies(self, threshold: float) -> List[Dict[str, Any]]:
        """Detect significant price change anomalies"""
        anomalies = []
        changes = self.price_ops.calculate_price_changes(days_back=30)
        for change in changes.get("all_changes", []):
            if abs(change["percent_change"]) > threshold * 100:
                anomalies.append(self._build_price_change_anomaly(change))
        return anomalies
    
    def _build_stale_data_anomaly(self, item) -> Dict[str, Any]:
        """Build anomaly record for stale data"""
        return {
            "type": "stale_data",
            "provider": item.provider,
            "model": item.model_name,
            "last_updated": item.last_updated.isoformat() if item.last_updated else None,
            "severity": "low"
        }
    
    def _detect_stale_data_anomalies(self) -> List[Dict[str, Any]]:
        """Detect stale data anomalies"""
        anomalies = []
        stale_cutoff = datetime.now(UTC) - timedelta(days=30)
        stale_items = self.db.query(AISupplyItem).filter(
            AISupplyItem.last_updated < stale_cutoff
        ).all()
        for item in stale_items:
            anomalies.append(self._build_stale_data_anomaly(item))
        return anomalies
    
    def detect_anomalies(self, threshold: float = 0.2) -> List[Dict[str, Any]]:
        """Detect pricing anomalies (significant deviations)"""
        price_anomalies = self._detect_price_change_anomalies(threshold)
        stale_anomalies = self._detect_stale_data_anomalies()
        return price_anomalies + stale_anomalies
    
    def _initialize_report_structure(self) -> Dict[str, Any]:
        """Initialize the base report structure."""
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "sections": {}
        }
    
    def _generate_price_changes_section(self) -> Dict[str, Any]:
        """Generate price changes section of the report."""
        return {
            "weekly": self.price_ops.calculate_price_changes(days_back=7),
            "monthly": self.price_ops.calculate_price_changes(days_back=30)
        }
    
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
        all_items = self.supply_ops.get_supply_items()
        return len(set(item.provider for item in all_items))
    
    def _generate_statistics_section(self) -> Dict[str, Any]:
        """Generate model statistics section."""
        model_counts = self._get_model_counts()
        providers_count = self._get_providers_count()
        return {**model_counts, "providers_tracked": providers_count}
    
    async def _populate_report_sections(self, report: Dict[str, Any]) -> None:
        """Populate all report sections."""
        report["sections"]["provider_comparison"] = self.get_provider_comparison()
        report["sections"]["price_changes"] = self._generate_price_changes_section()
        report["sections"]["anomalies"] = self.detect_anomalies()
        report["sections"]["statistics"] = self._generate_statistics_section()
        report["sections"]["recent_research"] = self.research_ops._generate_research_section()
    
    async def generate_market_report(self) -> Dict[str, Any]:
        """Generate comprehensive market report"""
        report = self._initialize_report_structure()
        await self._populate_report_sections(report)
        return report