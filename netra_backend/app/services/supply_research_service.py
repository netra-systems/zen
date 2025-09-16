"""
Supply Research Service - Business logic for AI supply research operations
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.db.models_postgres import (
    AISupplyItem,
    ResearchSession,
    SupplyUpdateLog,
    User,
)
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.permission_service import PermissionService
from netra_backend.app.services.supply_research.market_operations import (
    MarketOperations,
)
from netra_backend.app.services.supply_research.price_analysis_operations import (
    PriceAnalysisOperations,
)
from netra_backend.app.services.supply_research.research_session_operations import (
    ResearchSessionOperations,
)

# Import modular operations
from netra_backend.app.services.supply_research.supply_item_operations import (
    SupplyItemOperations,
)
from netra_backend.app.services.supply_research.supply_validation import (
    SupplyValidation,
)


class SupplyResearchService:
    """Service for managing AI supply research operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis_manager = None
        self.cache_ttl = 3600  # 1 hour cache
        
        # Initialize modular operations
        self.supply_ops = SupplyItemOperations(db)
        self.research_ops = ResearchSessionOperations(db)
        self.price_ops = PriceAnalysisOperations(db)
        self.market_ops = MarketOperations(db)
        self.validation = SupplyValidation()
        
        try:
            from netra_backend.app.redis_manager import redis_manager
            self.redis_manager = redis_manager
        except Exception as e:
            logger.warning(f"Redis not available for caching: {e}")
    
    # Supply Item Operations - Delegate to SupplyItemOperations
    def get_supply_items(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        availability_status: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[AISupplyItem]:
        """Get supply items with optional filters"""
        return self.supply_ops.get_supply_items(provider, model_name, availability_status, min_confidence)
    
    def get_supply_item_by_id(self, item_id: str) -> Optional[AISupplyItem]:
        """Get a specific supply item by ID"""
        return self.supply_ops.get_supply_item_by_id(item_id)
    
    def create_or_update_supply_item(self, provider: str, model_name: str, data: Dict[str, Any], research_session_id: Optional[str] = None, updated_by: str = "system") -> AISupplyItem:
        """Create or update a supply item"""
        return self.supply_ops.create_or_update_supply_item(provider, model_name, data, research_session_id, updated_by)
    
    # Research Session Operations - Delegate to ResearchSessionOperations
    def get_research_sessions(
        self,
        status: Optional[str] = None,
        initiated_by: Optional[str] = None,
        limit: int = 100
    ) -> List[ResearchSession]:
        """Get research sessions with optional filters"""
        return self.research_ops.get_research_sessions(status, initiated_by, limit)
    
    def get_research_session_by_id(self, session_id: str) -> Optional[ResearchSession]:
        """Get a specific research session"""
        return self.research_ops.get_research_session_by_id(session_id)
    
    def get_update_logs(
        self,
        supply_item_id: Optional[str] = None,
        updated_by: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[SupplyUpdateLog]:
        """Get supply update logs with filters"""
        return self.research_ops.get_update_logs(supply_item_id, updated_by, start_date, end_date, limit)
    
    # Price Analysis Operations - Delegate to PriceAnalysisOperations
    def calculate_price_changes(self, provider: Optional[str] = None, days_back: int = 7) -> Dict[str, Any]:
        """Calculate price changes over a period"""
        return self.price_ops.calculate_price_changes(provider, days_back)
    
    # Market Operations - Delegate to MarketOperations
    def get_provider_comparison(self) -> Dict[str, Any]:
        """Get pricing comparison across providers"""
        return self.market_ops.get_provider_comparison()
    
    def detect_anomalies(self, threshold: float = 0.2) -> List[Dict[str, Any]]:
        """Detect pricing anomalies (significant deviations)"""
        return self.market_ops.detect_anomalies(threshold)
    
    async def generate_market_report(self) -> Dict[str, Any]:
        """Generate comprehensive market report"""
        return await self.market_ops.generate_market_report()
    
    # Validation Operations - Delegate to SupplyValidation
    def validate_supply_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate supply data before storage"""
        return self.validation.validate_supply_data(data)