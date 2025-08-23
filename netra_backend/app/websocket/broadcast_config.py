"""WebSocket Broadcast Configuration and Statistics

**CONSOLIDATED INTO UNIFIED CONFIGURATION SYSTEM**

Handles configuration creation and statistics management for broadcast operations.
Separates configuration concerns from main agent implementation.
Now uses unified configuration system for enterprise-grade consistency.

Business Value: Centralized configuration management for maintainable broadcast system.
Prevents $12K MRR loss from configuration inconsistencies.
"""

import time
from typing import Any, Dict, Optional

from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.schemas.shared_types import RetryConfig
from netra_backend.app.websocket import broadcast_utils as utils
from netra_backend.app.websocket.broadcast_context import BroadcastContext


class BroadcastConfigManager:
    """Manages broadcast configuration creation and validation."""
    
    @staticmethod
    def create_circuit_breaker_config(config: Optional[Dict[str, Any]] = None) -> CircuitBreakerConfig:
        """Create circuit breaker configuration for WebSocket operations.
        
        **CONSOLIDATED**: Now uses unified configuration system for enterprise reliability.
        """
        unified_config = get_unified_config()
        merged_config = BroadcastConfigManager._merge_circuit_breaker_config(config, unified_config)
        return BroadcastConfigManager._build_circuit_breaker_config(merged_config)
    
    @staticmethod
    def _merge_circuit_breaker_config(config: Optional[Dict[str, Any]], 
                                     unified_config) -> Dict[str, Any]:
        """Merge configuration from unified config system and user overrides."""
        # Get configuration from unified config with enterprise defaults
        websocket_config = getattr(unified_config, 'ws_config', None)
        circuit_breaker_config = getattr(websocket_config, 'circuit_breaker', {}) if websocket_config else {}
        
        # Enterprise defaults for WebSocket broadcast circuit breaker
        default_config = {
            "failure_threshold": getattr(circuit_breaker_config, 'failure_threshold', 5),
            "recovery_timeout": getattr(circuit_breaker_config, 'recovery_timeout', 30)
        }
        
        # Allow local overrides for testing
        user_config = config.get("circuit_breaker", {}) if config else {}
        return {**default_config, **user_config}
    
    @staticmethod
    def _build_circuit_breaker_config(merged_config: Dict[str, Any]) -> CircuitBreakerConfig:
        """Build circuit breaker configuration object."""
        return CircuitBreakerConfig(
            name="websocket_broadcast",
            failure_threshold=merged_config["failure_threshold"],
            recovery_timeout=merged_config["recovery_timeout"]
        )
    
    @staticmethod
    def create_retry_config(config: Optional[Dict[str, Any]] = None) -> RetryConfig:
        """Create retry configuration for WebSocket operations.
        
        **CONSOLIDATED**: Now uses unified configuration system for enterprise reliability.
        """
        unified_config = get_unified_config()
        merged_config = BroadcastConfigManager._merge_retry_config(config, unified_config)
        return BroadcastConfigManager._build_retry_config(merged_config)
    
    @staticmethod
    def _merge_retry_config(config: Optional[Dict[str, Any]], 
                           unified_config) -> Dict[str, Any]:
        """Merge retry configuration from unified config system and user overrides."""
        # Get configuration from unified config with enterprise defaults
        websocket_config = getattr(unified_config, 'ws_config', None)
        retry_config = getattr(websocket_config, 'retry', {}) if websocket_config else {}
        
        # Enterprise defaults for WebSocket broadcast retry
        default_config = {
            "max_retries": getattr(retry_config, 'max_retries', 3),
            "base_delay": getattr(retry_config, 'base_delay', 1.0),
            "max_delay": getattr(retry_config, 'max_delay', 10.0)
        }
        
        # Allow local overrides for testing
        user_config = config.get("retry", {}) if config else {}
        return {**default_config, **user_config}
    
    @staticmethod
    def _build_retry_config(merged_config: Dict[str, Any]) -> RetryConfig:
        """Build retry configuration object."""
        return RetryConfig(
            max_retries=merged_config["max_retries"],
            base_delay=merged_config["base_delay"],
            max_delay=merged_config["max_delay"],
            exponential_backoff=True
        )


class BroadcastStatsManager:
    """Manages broadcast statistics collection and reporting."""
    
    @staticmethod
    def init_broadcast_stats() -> Dict[str, int]:
        """Initialize backward compatibility broadcast statistics."""
        return {
            "total_broadcasts": 0,
            "successful_sends": 0,
            "failed_sends": 0
        }
    
    @staticmethod
    def update_broadcast_stats(stats: Dict[str, int], successful_sends: int, failed_sends: int) -> None:
        """Update broadcast statistics for backward compatibility."""
        stats["total_broadcasts"] += 1
        stats["successful_sends"] += successful_sends
        stats["failed_sends"] += failed_sends
    
    @staticmethod
    def gather_stats_components(room_manager, stats_dict, reliability_manager, monitor) -> Dict[str, Any]:
        """Gather statistics from all components."""
        return {
            "room_stats": room_manager.get_stats(),
            "broadcast_stats": utils.get_broadcast_stats(stats_dict),
            "reliability_stats": reliability_manager.get_health_status(),
            "monitoring_stats": monitor.get_health_status()
        }
    
    @staticmethod
    def build_comprehensive_stats(stats_components: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
        """Build comprehensive statistics dictionary."""
        base_stats = {**stats_components["broadcast_stats"], **stats_components["room_stats"]}
        enhanced_stats = BroadcastStatsManager._add_enhanced_stats(stats_components, agent_name)
        return {**base_stats, **enhanced_stats}
    
    @staticmethod
    def _add_enhanced_stats(stats_components: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
        """Add enhanced statistics to base stats."""
        return {
            "reliability": stats_components["reliability_stats"],
            "monitoring": stats_components["monitoring_stats"],
            "agent_name": agent_name
        }


class BroadcastHealthManager:
    """Manages broadcast health status reporting."""
    
    @staticmethod
    def build_health_status_dict(reliability_manager, monitor) -> Dict[str, Any]:
        """Build health status dictionary from all components."""
        base_health = {"agent_health": "healthy"}
        component_health = BroadcastHealthManager._get_component_health_status(reliability_manager, monitor)
        return {**base_health, **component_health}
    
    @staticmethod
    def _get_component_health_status(reliability_manager, monitor) -> Dict[str, Any]:
        """Get health status from all components."""
        return {
            "reliability": reliability_manager.get_health_status(),
            "monitoring": monitor.get_health_status(),
            "executor_health": "healthy",
            "room_manager_health": "healthy"
        }


class BroadcastExecutionContextManager:
    """Manages execution context creation for broadcast operations."""
    
    @staticmethod
    def create_broadcast_execution_context(broadcast_ctx: BroadcastContext,
                                         run_id: str, agent_name: str, stream_updates: bool) -> ExecutionContext:
        """Create execution context for broadcast operation."""
        state_and_run_id = BroadcastExecutionContextManager._prepare_context_data(run_id)
        return BroadcastExecutionContextManager._build_execution_context(
            state_and_run_id["context_run_id"], agent_name, state_and_run_id["state"], 
            stream_updates, broadcast_ctx
        )
    
    @staticmethod
    def _prepare_context_data(run_id: str) -> Dict[str, Any]:
        """Prepare context data for execution context creation."""
        from netra_backend.app.agents.state import DeepAgentState
        return {
            "state": DeepAgentState(),
            "context_run_id": BroadcastExecutionContextManager._generate_run_id(run_id)
        }
    
    @staticmethod
    def _generate_run_id(run_id: str) -> str:
        """Generate run ID for execution context."""
        return run_id or f"broadcast_{int(time.time() * 1000)}"
    
    @staticmethod
    def _build_execution_context(run_id: str, agent_name: str, state, stream_updates: bool, 
                               broadcast_ctx: BroadcastContext) -> ExecutionContext:
        """Build execution context with parameters."""
        context_params = BroadcastExecutionContextManager._get_execution_context_params(
            run_id, agent_name, state, stream_updates
        )
        context_params["metadata"] = {"broadcast_context": broadcast_ctx}
        return ExecutionContext(**context_params)
    
    @staticmethod
    def _get_execution_context_params(run_id: str, agent_name: str, state, stream_updates: bool) -> Dict[str, Any]:
        """Get execution context parameters."""
        return {
            "run_id": run_id,
            "agent_name": agent_name,
            "state": state,
            "stream_updates": stream_updates
        }