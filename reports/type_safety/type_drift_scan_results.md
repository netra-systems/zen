
TYPE DRIFT MIGRATION ANALYSIS REPORT
=====================================

SUMMARY:
- Files Scanned: 1272
- Total Issues Found: 3774
- Critical Issues: 2837
- High Priority Issues: 618
- Files Affected: 374

CRITICAL ISSUES BREAKDOWN:

CRITICAL ISSUES (Immediate Action Required):
  netra_backend/app/services/key_manager.py:333 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/key_manager.py:402 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/key_manager.py:335 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str

  netra_backend/app/services/key_manager.py:404 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str

  netra_backend/app/services/mcp_service.py:299 - Function parameter uses string type for ID
    Fix: Use strongly-typed alternative from shared.types

  netra_backend/app/services/mcp_service.py:310 - Function parameter uses string type for ID
    Fix: Use strongly-typed alternative from shared.types

  netra_backend/app/services/mcp_service.py:315 - Function parameter uses string type for ID
    Fix: Use strongly-typed alternative from shared.types

  netra_backend/app/services/mcp_service.py:331 - Function parameter uses string type for ID
    Fix: Use strongly-typed alternative from shared.types

  netra_backend/app/services/mcp_service.py:335 - Function parameter uses string type for ID
    Fix: Use strongly-typed alternative from shared.types

  netra_backend/app/services/mcp_service.py:341 - Function parameter uses string type for ID
    Fix: Use strongly-typed alternative from shared.types

  netra_backend/app/services/mcp_service.py:485 - Function parameter uses string type for ID
    Fix: Use strongly-typed alternative from shared.types

  netra_backend/app/services/mcp_service.py:299 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str

  netra_backend/app/services/mcp_service.py:310 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str

  netra_backend/app/services/mcp_service.py:315 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str

  netra_backend/app/services/mcp_service.py:331 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str

  netra_backend/app/services/mcp_service.py:335 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str

  netra_backend/app/services/mcp_service.py:341 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str

  netra_backend/app/services/mcp_service.py:485 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str

  netra_backend/app/services/compensation_handlers_core.py:50 - Function parameter uses string type for ID
    Fix: Use strongly-typed alternative from shared.types

  netra_backend/app/services/compensation_handlers_core.py:60 - Function parameter uses string type for ID
    Fix: Use strongly-typed alternative from shared.types


HIGH PRIORITY ISSUES:
  netra_backend/app/services/file_storage_service.py:380 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/key_manager.py:390 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/unified_authentication_service.py:241 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/unified_authentication_service.py:354 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/mcp_service.py:481 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/query_builder.py:94 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/websocket_event_router.py:414 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/event_delivery_tracker.py:216 - String literal WebSocket event type - should use enum
    Fix: Use WebSocketEventType enum from shared.types instead of string literal

  netra_backend/app/services/message_handlers.py:128 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/message_handlers.py:419 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/message_handlers.py:465 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/message_handlers.py:561 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/tool_registry.py:143 - Untyped auth result dictionary
    Fix: Use AuthValidationResult from shared.types instead of dict

  netra_backend/app/services/user_execution_context.py:1273 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/user_execution_context.py:203 - Hardcoded test/placeholder ID - should use typed constants
    Fix: Use strongly-typed alternative from shared.types


TOP AFFECTED FILES:
  netra_backend/app/websocket_core/handlers.py: 121 issues
  netra_backend/app/services/websocket/message_handler.py: 90 issues
  netra_backend/app/services/agent_websocket_bridge.py: 87 issues
  netra_backend/app/services/user_execution_context.py: 75 issues
  netra_backend/app/websocket_core/unified_manager.py: 72 issues
  netra_backend/app/services/state_persistence.py: 56 issues
  netra_backend/app/clients/auth_client_core.py: 54 issues
  netra_backend/app/agents/agent_lifecycle.py: 52 issues
  netra_backend/app/websocket_core/event_validator.py: 52 issues
  netra_backend/app/agents/supervisor/agent_registry.py: 50 issues
