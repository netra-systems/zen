"""
Netra Factory Layer - User Context Isolation Patterns

This module implements Factory patterns for data access isolation following
the USER_CONTEXT_ARCHITECTURE.md patterns. Each factory creates user-scoped
contexts that eliminate shared state and ensure proper isolation.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Complete user isolation for multi-tenant data security
- Value Impact: Prevents data leakage between users, enables enterprise deployment
- Revenue Impact: Critical for Enterprise segments requiring strict data isolation

Key Factories:
- DataAccessFactory: Base factory pattern for data layer isolation
- ClickHouseAccessFactory: User-scoped ClickHouse contexts  
- RedisAccessFactory: User-scoped Redis contexts
- ClickHouseFactory: User-isolated ClickHouse instances with connection pooling
- RedisFactory: User-isolated Redis instances with connection management
- ToolDispatcherFactory: SSOT factory for tool dispatcher creation (Phase 2 consolidation)
"""

from netra_backend.app.factories.data_access_factory import (
    DataAccessFactory,
    get_clickhouse_factory,
    get_redis_factory
)
from netra_backend.app.factories.clickhouse_factory import (
    ClickHouseFactory,
    UserClickHouseClient
)
from netra_backend.app.factories.redis_factory import (
    RedisFactory,
    UserRedisClient
)
from netra_backend.app.factories.tool_dispatcher_factory import (
    ToolDispatcherFactory,
    get_tool_dispatcher_factory,
    set_tool_dispatcher_factory_websocket_manager,
    create_tool_dispatcher,
    tool_dispatcher_scope,
    # Backward compatibility (DEPRECATED)
    create_isolated_tool_dispatcher,
    isolated_tool_dispatcher_scope,
)
from netra_backend.app.factories.websocket_bridge_factory import (
    WebSocketBridgeProtocol,
    StandardWebSocketBridge,
    create_standard_websocket_bridge,
    create_agent_bridge_adapter,
    create_emitter_bridge_adapter,
    create_manager_bridge_adapter,
    # Backward compatibility (DEPRECATED)
    WebSocketBridgeAdapter,
)

__all__ = [
    "DataAccessFactory",
    "ClickHouseFactory",
    "UserClickHouseClient",
    "get_clickhouse_factory",
    "RedisFactory",
    "UserRedisClient",
    "get_redis_factory",
    # SSOT Tool Dispatcher Factory
    "ToolDispatcherFactory",
    "get_tool_dispatcher_factory",
    "set_tool_dispatcher_factory_websocket_manager",
    "create_tool_dispatcher",
    "tool_dispatcher_scope",
    # SSOT WebSocket Bridge Factory
    "WebSocketBridgeProtocol",
    "StandardWebSocketBridge",
    "create_standard_websocket_bridge",
    "create_agent_bridge_adapter",
    "create_emitter_bridge_adapter",
    "create_manager_bridge_adapter",
    # Backward Compatibility (DEPRECATED)
    "create_isolated_tool_dispatcher",
    "isolated_tool_dispatcher_scope",
    "WebSocketBridgeAdapter",
]