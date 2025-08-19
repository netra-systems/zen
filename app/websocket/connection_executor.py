"""WebSocket Connection Executor

Modern execution interface for WebSocket connection operations.
Implements BaseExecutionInterface for standardized connection management.

Business Value: Standardizes connection operations with monitoring and reliability.
"""

import asyncio
from typing import Dict, Any, List, Optional

from app.logging_config import central_logger
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult, ExecutionStatus
)
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.reliability_manager import ReliabilityManager
from app.websocket.connection_info import ConnectionInfo, ConnectionMetrics
from app.websocket.connection_reliability import ConnectionReliabilityManager

logger = central_logger.get_logger(__name__)


class ConnectionExecutor(BaseExecutionInterface):
    """Modern WebSocket connection executor with standardized patterns."""
    
    def __init__(self, websocket_manager=None):
        super().__init__("websocket_connection", websocket_manager)
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize connection executor components."""
        self._initialize_metrics_and_managers()
        self._initialize_execution_engine()
        
    def _initialize_metrics_and_managers(self):
        """Initialize metrics and manager components."""
        self.connection_metrics = ConnectionMetrics()
        self.reliability_manager = ConnectionReliabilityManager()
        self.monitor = ExecutionMonitor()
        
    def _initialize_execution_engine(self):
        """Initialize execution engine."""
        # Removed BaseExecutionEngine import to fix circular dependency
        # Connection executor uses its own execution pattern
        self.execution_engine = None  # Not needed for connection management
        
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute connection operation core logic."""
        operation_type = context.metadata.get("operation_type")
        operation_data = context.metadata.get("operation_data", {})
        return await self._route_operation(operation_type, operation_data)
        
    async def _route_operation(self, operation_type: str, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route operation to appropriate handler."""
        operation_map = self._get_operation_map()
        if operation_type in operation_map:
            return await operation_map[operation_type](operation_data)
        else:
            raise ValueError(f"Unknown operation type: {operation_type}")
            
    def _get_operation_map(self) -> Dict[str, Any]:
        """Get operation mapping dictionary."""
        return {
            "establish_connection": self._execute_establish_connection,
            "close_connection": self._execute_close_connection,
            "cleanup_dead_connections": self._execute_cleanup_dead_connections,
            "get_connection_stats": self._execute_get_connection_stats
        }
            
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate connection operation preconditions."""
        operation_type = context.metadata.get("operation_type")
        operation_data = context.metadata.get("operation_data", {})
        return self._validate_operation_preconditions(operation_type, operation_data)
        
    def _validate_operation_preconditions(self, operation_type: str, operation_data: Dict[str, Any]) -> bool:
        """Validate specific operation preconditions."""
        validation_map = self._get_validation_map()
        return validation_map.get(operation_type, lambda _: False)(operation_data)
        
    def _get_validation_map(self) -> Dict[str, Any]:
        """Get validation mapping dictionary."""
        return {
            "establish_connection": self._validate_establish_connection,
            "close_connection": self._validate_close_connection,
            "cleanup_dead_connections": lambda _: True,
            "get_connection_stats": lambda _: True
        }
            
    async def _execute_establish_connection(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute connection establishment."""
        connection_params = self._extract_connection_params(data)
        reliability_handler = self._create_establishment_reliability_handler()
        conn_info = await self._establish_connection_with_handler(
            reliability_handler, connection_params
        )
        return self._handle_establishment_result(conn_info)
        
    def _extract_connection_params(self, data: Dict[str, Any]) -> tuple:
        """Extract connection parameters from data."""
        user_id = data["user_id"]
        websocket = data["websocket"]
        max_connections = data.get("max_connections", 5)
        return user_id, websocket, max_connections
        
    async def _establish_connection_with_handler(self, reliability_handler, params: tuple):
        """Establish connection with reliability handler."""
        user_id, websocket, max_connections = params
        return await reliability_handler.establish_connection_safely(
            user_id, websocket, max_connections
        )
        
    def _create_establishment_reliability_handler(self):
        """Create connection establishment reliability handler."""
        from app.websocket.connection_reliability import ConnectionEstablishmentReliability
        return ConnectionEstablishmentReliability(self.reliability_manager)
        
    def _handle_establishment_result(self, conn_info) -> Dict[str, Any]:
        """Handle connection establishment result."""
        if conn_info:
            self.connection_metrics.record_connection_success()
            return {"connection_info": conn_info, "success": True}
        else:
            self.connection_metrics.record_connection_failure()
            return {"success": False, "error": "Failed to establish connection"}
            
    async def _execute_close_connection(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute connection closure."""
        conn_info = data["connection_info"]
        code = data.get("code", 1000)
        reason = data.get("reason", "Normal closure")
        reliability_handler = self._create_close_reliability_handler()
        success = await reliability_handler.close_connection_safely(conn_info, code, reason)
        return self._handle_close_result(success, conn_info)
        
    def _create_close_reliability_handler(self):
        """Create connection close reliability handler."""
        from app.websocket.connection_reliability import ConnectionCloseReliability
        return ConnectionCloseReliability(self.reliability_manager)
        
    def _handle_close_result(self, success: bool, conn_info) -> Dict[str, Any]:
        """Handle connection close result."""
        if success:
            self.reliability_manager.cleanup_connection(conn_info.connection_id)
        return {"success": success, "connection_id": conn_info.connection_id}
        
    async def _execute_cleanup_dead_connections(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute cleanup of dead connections."""
        connections_to_check = data.get("connections", [])
        cleaned_count = await self._cleanup_dead_connections_batch(connections_to_check)
        return {"cleaned_connections": cleaned_count, "total_checked": len(connections_to_check)}
        
    async def _cleanup_dead_connections_batch(self, connections_to_check: List) -> int:
        """Clean up batch of dead connections."""
        cleaned_count = 0
        for conn_info in connections_to_check:
            if not self._is_connection_alive(conn_info):
                await self._cleanup_single_connection(conn_info)
                cleaned_count += 1
        return cleaned_count
        
    async def _execute_get_connection_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute connection statistics retrieval."""
        basic_stats = self.connection_metrics.get_stats()
        reliability_health = self.reliability_manager.get_overall_health()
        monitor_health = self.monitor.get_health_status()
        return self._build_stats_response(basic_stats, reliability_health, monitor_health)
        
    def _build_stats_response(self, basic_stats, reliability_health, monitor_health) -> Dict[str, Any]:
        """Build connection statistics response."""
        return {
            "connection_stats": basic_stats,
            "reliability_health": reliability_health,
            "monitor_health": monitor_health,
            "timestamp": self._get_current_timestamp()
        }
        
    def _validate_establish_connection(self, data: Dict[str, Any]) -> bool:
        """Validate establish connection parameters."""
        required_fields = ["user_id", "websocket"]
        return all(field in data and data[field] is not None for field in required_fields)
        
    def _validate_close_connection(self, data: Dict[str, Any]) -> bool:
        """Validate close connection parameters."""
        return "connection_info" in data and data["connection_info"] is not None
        
    def _is_connection_alive(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection is alive."""
        from app.websocket.connection_info import ConnectionValidator
        return ConnectionValidator.is_websocket_connected(conn_info.websocket)
        
    async def _cleanup_single_connection(self, conn_info: ConnectionInfo) -> None:
        """Clean up a single dead connection."""
        try:
            await conn_info.websocket.close(code=1001, reason="Connection lost")
        except Exception as e:
            logger.debug(f"Error closing dead connection {conn_info.connection_id}: {e}")
            
        self.reliability_manager.cleanup_connection(conn_info.connection_id)
        
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for stats."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        return {
            "executor_health": "healthy",
            "connection_metrics": self.connection_metrics.get_stats(),
            "reliability_health": self.reliability_manager.get_overall_health(),
            "monitor_health": self.monitor.get_health_status()
        }


class ConnectionOperationBuilder:
    """Builder for creating connection operation contexts."""
    
    def __init__(self):
        self._operation_type = None
        self._operation_data = {}
        self._run_id = None
        
    def with_operation_type(self, operation_type: str) -> 'ConnectionOperationBuilder':
        """Set operation type."""
        self._operation_type = operation_type
        return self
        
    def with_operation_data(self, operation_data: Dict[str, Any]) -> 'ConnectionOperationBuilder':
        """Set operation data."""
        self._operation_data = operation_data
        return self
        
    def with_run_id(self, run_id: str) -> 'ConnectionOperationBuilder':
        """Set run ID."""
        self._run_id = run_id
        return self
        
    def build(self) -> ExecutionContext:
        """Build execution context."""
        self._validate_build_requirements()
        state = self._create_agent_state()
        return self._create_execution_context(state)
        
    def _validate_build_requirements(self) -> None:
        """Validate build requirements."""
        if not self._operation_type or not self._run_id:
            raise ValueError("Operation type and run ID required")
            
    def _create_agent_state(self):
        """Create agent state."""
        from app.agents.state import DeepAgentState
        return DeepAgentState(user_request="websocket_operation_context")
        
    def _create_execution_context(self, state) -> ExecutionContext:
        """Create execution context."""
        metadata = self._build_context_metadata()
        return self._build_execution_context_with_params(state, metadata)
        
    def _build_execution_context_with_params(self, state, metadata) -> ExecutionContext:
        """Build execution context with parameters."""
        return ExecutionContext(
            run_id=self._run_id,
            agent_name="websocket_connection",
            state=state,
            metadata=metadata
        )
        
    def _build_context_metadata(self) -> Dict[str, Any]:
        """Build context metadata."""
        return {
            "operation_type": self._operation_type,
            "operation_data": self._operation_data
        }


class ConnectionExecutionOrchestrator:
    """Orchestrates connection execution with modern patterns."""
    
    def __init__(self):
        self.executor = ConnectionExecutor()
        self.operation_builder = ConnectionOperationBuilder()
        
    async def establish_connection(self, user_id: str, websocket, 
                                 max_connections: int = 5) -> ExecutionResult:
        """Establish connection using modern execution patterns."""
        operation_data = self._build_establish_operation_data(
            user_id, websocket, max_connections
        )
        context = self._build_operation_context("establish_connection", operation_data)
        return await self.executor.execution_engine.execute(self.executor, context)
        
    def _build_establish_operation_data(self, user_id: str, websocket, max_connections: int) -> Dict[str, Any]:
        """Build establish connection operation data."""
        return {
            "user_id": user_id,
            "websocket": websocket,
            "max_connections": max_connections
        }
        
    async def close_connection(self, conn_info: ConnectionInfo,
                             code: int = 1000, reason: str = "Normal closure") -> ExecutionResult:
        """Close connection using modern execution patterns."""
        operation_data = self._build_close_operation_data(conn_info, code, reason)
        context = self._build_operation_context("close_connection", operation_data)
        return await self.executor.execution_engine.execute(self.executor, context)
        
    def _build_close_operation_data(self, conn_info: ConnectionInfo, code: int, reason: str) -> Dict[str, Any]:
        """Build close connection operation data."""
        return {
            "connection_info": conn_info,
            "code": code,
            "reason": reason
        }
        
    async def cleanup_dead_connections(self, connections: List[ConnectionInfo]) -> ExecutionResult:
        """Clean up dead connections using modern execution patterns."""
        context = self._build_operation_context("cleanup_dead_connections", {
            "connections": connections
        })
        
        return await self.executor.execution_engine.execute(self.executor, context)
        
    async def get_connection_stats(self) -> ExecutionResult:
        """Get connection statistics using modern execution patterns."""
        context = self._build_operation_context("get_connection_stats", {})
        return await self.executor.execution_engine.execute(self.executor, context)
        
    def _build_operation_context(self, operation_type: str, 
                               operation_data: Dict[str, Any]) -> ExecutionContext:
        """Build operation context."""
        run_id = self._generate_run_id(operation_type)
        return self._create_operation_context(operation_type, operation_data, run_id)
        
    def _generate_run_id(self, operation_type: str) -> str:
        """Generate unique run ID."""
        import time
        return f"conn_{operation_type}_{int(time.time() * 1000)}"
        
    def _create_operation_context(self, operation_type: str, operation_data: Dict[str, Any], run_id: str) -> ExecutionContext:
        """Create operation context."""
        return (self.operation_builder
                .with_operation_type(operation_type)
                .with_operation_data(operation_data)
                .with_run_id(run_id)
                .build())
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get orchestrator health status."""
        return {
            "orchestrator_status": "healthy",
            "executor_health": self.executor.get_health_status()
        }