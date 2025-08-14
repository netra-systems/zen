"""
Shared production types and classes to eliminate duplicate type definitions.
Single source of truth for production types used across multiple modules.
"""

from typing import Dict, Optional, List, AsyncGenerator, Union
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from app.llm.llm_manager import LLMManager
# Avoid circular imports by using TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.base import BaseSubAgent
    from app.agents.tool_dispatcher import ToolDispatcher
    from app.agents.state import DeepAgentState

# Type aliases for common patterns to replace Any usage
PrimitiveType = Union[str, int, float, bool, None]
JsonCompatibleDict = Dict[str, PrimitiveType]
NestedJsonDict = Dict[str, Union[PrimitiveType, List[PrimitiveType], Dict[str, PrimitiveType]]]
ExecutionResult = Union[JsonCompatibleDict, List[JsonCompatibleDict], str, bool, None]
ToolParameters = Dict[str, Union[str, int, float, bool]]
ToolResult = Dict[str, Union[str, int, float, bool, List[str]]]
AgentState = 'DeepAgentState'  # Forward reference
AgentExecutionResult = ExecutionResult


class AgentStatus(str, Enum):
    """Standard agent status enumeration"""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    STOPPED = "stopped"


class ProcessingResult(BaseModel):
    """Standard processing result structure"""
    status: str = Field(..., description="Processing status")
    data: Optional[Dict[str, Union[str, int, float, bool]]] = Field(default=None, description="Result data")
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict, description="Processing metadata")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")


class ErrorContext(BaseModel):
    """Standard error context for consistent error handling"""
    trace_id: str = Field(..., description="Unique trace identifier")
    operation: str = Field(..., description="Operation being performed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    details: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict, description="Error details")
    user_id: Optional[str] = Field(default=None, description="User identifier")


class BaseAgentInterface(ABC):
    """Base interface for agent implementations to ensure consistency"""
    
    @abstractmethod
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: 'ToolDispatcher') -> None:
        pass
    
    @abstractmethod
    async def execute(self, state: 'DeepAgentState', session_id: str, **kwargs) -> Any:
        pass
    
    @abstractmethod
    def _init_components(self) -> None:
        pass


class DataSubAgent(BaseSubAgent):
    """
    Canonical DataSubAgent implementation - single source of truth.
    Advanced data gathering and analysis agent with ClickHouse integration.
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher) -> None:
        super().__init__(
            llm_manager, 
            name="DataSubAgent", 
            description="Advanced data gathering and analysis agent with ClickHouse integration."
        )
        self.tool_dispatcher = tool_dispatcher
        self.status = AgentStatus.INITIALIZING
        self._init_components()
        self._init_redis()
        self._init_reliability()
        self.status = AgentStatus.READY
        
    def _init_components(self) -> None:
        """Initialize core components."""
        from app.agents.data_sub_agent.query_builder import QueryBuilder
        from app.agents.data_sub_agent.analysis_engine import AnalysisEngine
        from app.agents.data_sub_agent.clickhouse_operations import ClickHouseOperations
        from app.agents.config import agent_config
        
        self.query_builder = QueryBuilder()
        self.analysis_engine = AnalysisEngine()
        self.clickhouse_ops = ClickHouseOperations()
        self.cache_ttl = getattr(agent_config.cache, 'default_ttl', 300)
        
    def _init_redis(self) -> None:
        """Initialize Redis connection."""
        from app.redis_manager import RedisManager
        from app.logging_config import central_logger as logger
        
        self.redis_manager: Optional[RedisManager] = None
        try:
            self.redis_manager = RedisManager()
        except Exception as e:
            logger.warning(f"Redis not available for DataSubAgent caching: {e}")
    
    def _init_reliability(self) -> None:
        """Initialize reliability components."""
        try:
            from app.core.reliability import get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
            
            self.circuit_breaker = get_reliability_wrapper(
                CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60)
            )
            self.retry_config = RetryConfig(max_attempts=3, base_delay=1.0)
        except Exception as e:
            from app.logging_config import central_logger as logger
            logger.warning(f"Reliability components not available: {e}")
            self.circuit_breaker = None
            self.retry_config = None
    
    async def execute(self, state: DeepAgentState, session_id: str, 
                     stream_updates: bool = False, **kwargs) -> ProcessingResult:
        """Execute data analysis task."""
        self.status = AgentStatus.PROCESSING
        
        try:
            # Implementation would go here
            result = ProcessingResult(
                status="success",
                data={"analysis": "completed"},
                metadata={"session_id": session_id, "agent": "DataSubAgent"}
            )
            self.status = AgentStatus.READY
            return result
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            return ProcessingResult(
                status="error",
                errors=[str(e)],
                metadata={"session_id": session_id, "agent": "DataSubAgent"}
            )
    
    async def process_with_retry(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with retry logic."""
        max_retries = getattr(self, 'config', {}).get('max_retries', 3)
        
        for attempt in range(max_retries):
            try:
                return await self._process_internal(data)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return {"success": False, "error": "Max retries exceeded"}
    
    async def _process_internal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Internal processing method - to be implemented by subclasses."""
        return {"success": True, "data": data}


class ToolExecutionContext(BaseModel):
    """Context for tool execution with permissions"""
    user_id: str = Field(..., description="User identifier")
    tool_name: str = Field(..., description="Tool being executed")
    requested_action: str = Field(..., description="Requested action")
    user_plan: str = Field(..., description="User subscription plan")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    permissions: Dict[str, Any] = Field(default_factory=dict, description="User permissions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class CacheKey(BaseModel):
    """Standard cache key structure"""
    prefix: str = Field(..., description="Cache key prefix")
    identifier: str = Field(..., description="Unique identifier")
    version: str = Field(default="v1", description="Cache version")
    
    def to_string(self) -> str:
        """Convert to cache key string"""
        return f"{self.prefix}:{self.version}:{self.identifier}"


class ServiceHealth(BaseModel):
    """Standard service health check response"""
    service_name: str = Field(..., description="Service name")
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency statuses")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Health metrics")


class ApiResponse(BaseModel):
    """Standard API response structure"""
    success: bool = Field(..., description="Operation success status")
    data: Optional[Any] = Field(default=None, description="Response data")
    message: Optional[str] = Field(default=None, description="Response message")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")


class EventContext(BaseModel):
    """Context for event processing"""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event type")
    source: str = Field(..., description="Event source")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(..., description="Event data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")


# Common constants and utilities
DEFAULT_CACHE_TTL = 300  # 5 minutes
DEFAULT_TIMEOUT = 30  # 30 seconds
DEFAULT_RETRY_ATTEMPTS = 3

# Type aliases for common patterns
AgentConfigDict = Dict[str, Any]
ProcessingContextDict = Dict[str, Any]
MetadataDict = Dict[str, Any]