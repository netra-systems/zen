"""Data Sub Agent Helpers

Helper components for delegation and backward compatibility.
Manages cache operations, data processing, and legacy interface support.

Business Value: Ensures seamless backward compatibility during modernization.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from app.logging_config import central_logger as logger
from app.agents.state import DeepAgentState
from app.schemas.strict_types import TypedAgentResult

# Import existing modular components for delegation
from .agent_cache import CacheManager
from .agent_execution import ExecutionManager
from .agent_data_processing import DataProcessor
from .agent_corpus_operations import CorpusOperations
from .agent_anomaly_processing import AnomalyProcessor
from .modern_execution_interface import DataSubAgentModernExecution
from .delegation_helper import DataSubAgentDelegationHelper
from .configuration_manager import DataSubAgentConfigurationManager


class DataSubAgentHelpers:
    """Helper components for backward compatibility and delegation.
    
    Manages all auxiliary operations and legacy interface support.
    """
    
    def __init__(self, agent) -> None:
        self.agent = agent
        self._init_component_managers()
        self._init_helper_managers()
        self._init_configuration_managers()
        
    def _init_component_managers(self) -> None:
        """Initialize core component managers."""
        self.cache_manager = CacheManager(self.agent)
        self.execution_manager = ExecutionManager(self.agent)
        self.data_processor = DataProcessor(self.agent)
        self.corpus_operations = CorpusOperations(self.agent)
        
    def _init_helper_managers(self) -> None:
        """Initialize helper managers."""
        self.anomaly_processor = AnomalyProcessor(self.agent)
        self.modern_execution = DataSubAgentModernExecution(self.agent)
        self.delegation_helper = DataSubAgentDelegationHelper()
        
    def _init_configuration_managers(self) -> None:
        """Initialize configuration managers."""
        self.config_manager = DataSubAgentConfigurationManager()
    
    # Backward compatibility execution methods
    async def execute_legacy_analysis(self, state: DeepAgentState, run_id: str, 
                                    stream_updates: bool = False) -> TypedAgentResult:
        """Execute analysis using legacy execution manager."""
        return await self.execution_manager.execute(state, run_id, stream_updates)
    
    # Cache management delegation
    async def get_cached_schema(self, table_name: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get cached schema with TTL and cache invalidation."""
        return await self.cache_manager.get_cached_schema(table_name, force_refresh)
        
    def clear_cache(self) -> None:
        """Clear schema cache for test compatibility."""
        self.cache_manager.cache_clear()
        
    async def invalidate_schema_cache(self, table_name: Optional[str] = None) -> None:
        """Invalidate schema cache for specific table or all tables."""
        await self.cache_manager.invalidate_schema_cache(table_name)
    
    # Data operations delegation
    async def fetch_clickhouse_data(self, query: str, cache_key: Optional[str] = None):
        """Execute ClickHouse query with caching support."""
        return await self.agent.core.clickhouse_ops.fetch_data(
            query, cache_key, self.agent.core.redis_manager, self.agent.core.cache_ttl
        )
    
    # Data processing delegation
    async def process_and_stream(self, data: Dict[str, Any], websocket) -> None:
        """Process data and stream results via WebSocket."""
        await self.data_processor.process_and_stream(data, websocket)
        
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate data has required fields."""
        return self.data_processor._validate_data(data)
        
    async def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data and preserve type."""
        return await self.data_processor._transform_data(data)
        
    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual data item."""
        return await self.data_processor.process_data(data)
        
    async def process_batch(self, batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process batch of data items."""
        return await self.data_processor.process_batch(batch_data)
    
    # Corpus operations delegation  
    async def analyze_corpus_data(self, corpus_id: str):
        """Analyze data related to a specific corpus."""
        return await self.corpus_operations.analyze_corpus_data(corpus_id)
        
    async def get_corpus_usage_patterns(self, corpus_id: str):
        """Retrieve usage patterns for a specific corpus."""
        return await self.corpus_operations.get_corpus_usage_patterns(corpus_id)
        
    async def detect_corpus_anomalies(self, corpus_id: str):
        """Detect anomalies in corpus usage and performance."""
        return await self.corpus_operations.detect_corpus_anomalies(corpus_id)
        
    async def generate_corpus_insights(self, corpus_id: str) -> Dict[str, Any]:
        """Generate comprehensive insights for a corpus."""
        return await self.corpus_operations.generate_corpus_insights(corpus_id)
    
    # Anomaly processing delegation
    def ensure_data_result(self, result):
        """Ensure result is a proper data analysis result object."""
        return self.execution_manager._ensure_data_result(result)
    
    # WebSocket communication
    async def send_websocket_update(self, run_id: str, update: Dict[str, Any]) -> None:
        """Send real-time update via WebSocket."""
        try:
            if hasattr(self.agent, 'websocket_manager') and self.agent.websocket_manager:
                await self.agent.websocket_manager.send_agent_update(
                    run_id, "DataSubAgent", update
                )
        except Exception as e:
            logger.debug(f"Failed to send WebSocket update: {e}")
    
    # Extended operations delegation
    def get_delegation_methods(self) -> List[str]:
        """Get available delegation methods."""
        return self.delegation_helper.get_delegation_methods()
        
    def resolve_delegation_method(self, name: str, delegation_target: Any):
        """Resolve delegation method to target."""
        return self.delegation_helper.resolve_delegation_method(name, delegation_target)
    
    # Health and status
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of helper components."""
        return {
            "cache_manager": "healthy" if self.cache_manager else "unavailable",
            "execution_manager": "healthy" if self.execution_manager else "unavailable",
            "data_processor": "healthy" if self.data_processor else "unavailable",
            "corpus_operations": "healthy" if self.corpus_operations else "unavailable",
            "anomaly_processor": "healthy" if self.anomaly_processor else "unavailable"
        }
    
    # Cleanup operations
    async def cleanup_resources(self, current_time: float) -> None:
        """Cleanup resources and old cache entries."""
        await self.cache_manager.cleanup_old_cache_entries(current_time)
        await self.modern_execution.cleanup_modern_components(
            self.agent, "cleanup"  # Simplified parameters for cleanup
        )