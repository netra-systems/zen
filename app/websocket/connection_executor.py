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
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.reliability_manager import ReliabilityManager
from app.websocket.connection_info import ConnectionInfo, ConnectionMetrics
from app.websocket.connection_reliability import ConnectionReliabilityManager

logger = central_logger.get_logger(__name__)


class ConnectionExecutor(BaseExecutionInterface):
    """Modern WebSocket connection executor with standardized patterns."""
    
    def __init__(self, websocket_manager=None):
        super().__init__("websocket_connection", websocket_manager)
        self.connection_metrics = ConnectionMetrics()
        self.reliability_manager = ConnectionReliabilityManager()
        self.monitor = ExecutionMonitor()
        self.execution_engine = BaseExecutionEngine(
            reliability_manager=None,  # Using our custom reliability manager
            monitor=self.monitor
        )
        
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute connection operation core logic."""
        operation_type = context.metadata.get("operation_type")
        operation_data = context.metadata.get("operation_data", {})
        
        if operation_type == "establish_connection":
            return await self._execute_establish_connection(operation_data)
        elif operation_type == "close_connection":
            return await self._execute_close_connection(operation_data)
        elif operation_type == "cleanup_dead_connections":
            return await self._execute_cleanup_dead_connections(operation_data)
        elif operation_type == "get_connection_stats":
            return await self._execute_get_connection_stats(operation_data)
        else:
            raise ValueError(f"Unknown operation type: {operation_type}")
            
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate connection operation preconditions."""
        operation_type = context.metadata.get("operation_type")
        operation_data = context.metadata.get("operation_data", {})
        
        if operation_type == "establish_connection":
            return self._validate_establish_connection(operation_data)
        elif operation_type == "close_connection":
            return self._validate_close_connection(operation_data)
        elif operation_type in ["cleanup_dead_connections", "get_connection_stats"]:
            return True  # These operations don't require specific validation
        else:
            return False
            
    async def _execute_establish_connection(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute connection establishment."""
        user_id = data["user_id"]
        websocket = data["websocket"]
        max_connections = data.get("max_connections", 5)
        
        from app.websocket.connection_reliability import ConnectionEstablishmentReliability
        reliability_handler = ConnectionEstablishmentReliability(self.reliability_manager)
        
        conn_info = await reliability_handler.establish_connection_safely(
            user_id, websocket, max_connections
        )
        
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
        
        from app.websocket.connection_reliability import ConnectionCloseReliability
        reliability_handler = ConnectionCloseReliability(self.reliability_manager)
        
        success = await reliability_handler.close_connection_safely(conn_info, code, reason)
        
        if success:
            self.reliability_manager.cleanup_connection(conn_info.connection_id)
            
        return {"success": success, "connection_id": conn_info.connection_id}
        
    async def _execute_cleanup_dead_connections(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute cleanup of dead connections."""
        connections_to_check = data.get("connections", [])
        cleaned_count = 0
        
        for conn_info in connections_to_check:
            if not self._is_connection_alive(conn_info):
                await self._cleanup_single_connection(conn_info)
                cleaned_count += 1
                
        return {"cleaned_connections": cleaned_count, "total_checked": len(connections_to_check)}
        
    async def _execute_get_connection_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute connection statistics retrieval."""
        basic_stats = self.connection_metrics.get_stats()
        reliability_health = self.reliability_manager.get_overall_health()
        monitor_health = self.monitor.get_health_status()
        
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
        if not self._operation_type or not self._run_id:
            raise ValueError("Operation type and run ID required")
            
        from app.agents.state import DeepAgentState
        
        state = DeepAgentState()
        return ExecutionContext(
            run_id=self._run_id,
            agent_name="websocket_connection",
            state=state,
            metadata={
                "operation_type": self._operation_type,
                "operation_data": self._operation_data
            }
        )


class ConnectionExecutionOrchestrator:
    """Orchestrates connection execution with modern patterns."""
    
    def __init__(self):
        self.executor = ConnectionExecutor()
        self.operation_builder = ConnectionOperationBuilder()
        
    async def establish_connection(self, user_id: str, websocket, 
                                 max_connections: int = 5) -> ExecutionResult:
        """Establish connection using modern execution patterns."""
        context = self._build_operation_context("establish_connection", {
            "user_id": user_id,
            "websocket": websocket,
            "max_connections": max_connections
        })
        
        return await self.executor.execution_engine.execute(self.executor, context)
        
    async def close_connection(self, conn_info: ConnectionInfo,
                             code: int = 1000, reason: str = "Normal closure") -> ExecutionResult:
        """Close connection using modern execution patterns."""
        context = self._build_operation_context("close_connection", {
            "connection_info": conn_info,
            "code": code,
            "reason": reason
        })
        
        return await self.executor.execution_engine.execute(self.executor, context)
        
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
        import time
        run_id = f"conn_{operation_type}_{int(time.time() * 1000)}"
        
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