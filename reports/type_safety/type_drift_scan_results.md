
TYPE DRIFT MIGRATION ANALYSIS REPORT
=====================================

SUMMARY:
- Files Scanned: 1049
- Total Issues Found: 2917
- Critical Issues: 2319
- High Priority Issues: 375
- Files Affected: 287

CRITICAL ISSUES BREAKDOWN:

CRITICAL ISSUES (Immediate Action Required):
  netra_backend/app/services/agent_service_core.py:173 - Function parameter uses string type for ID
    Fix: Replace 'run_id: str' with 'run_id: RunID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:180 - Function parameter uses string type for ID
    Fix: Replace 'run_id: str' with 'run_id: RunID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:184 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:219 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:280 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:291 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:305 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:319 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:326 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:352 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:373 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:390 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:408 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:412 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:510 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:595 - Function parameter uses string type for ID
    Fix: Replace 'user_id: str' with 'user_id: UserID' and import from shared.types

  netra_backend/app/services/agent_service_core.py:173 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str

  netra_backend/app/services/agent_service_core.py:180 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str

  netra_backend/app/services/agent_service_core.py:184 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str

  netra_backend/app/services/agent_service_core.py:219 - Class attribute uses string type for ID
    Fix: Use NewType identifier from shared.types instead of str


HIGH PRIORITY ISSUES:
  netra_backend/app/services/agent_service_core.py:177 - Hardcoded test/placeholder ID - should use typed constants
    Fix: Use strongly-typed alternative from shared.types

  netra_backend/app/services/agent_service_core.py:477 - Hardcoded test/placeholder ID - should use typed constants
    Fix: Use strongly-typed alternative from shared.types

  netra_backend/app/services/agent_service_core.py:515 - Hardcoded test/placeholder ID - should use typed constants
    Fix: Use strongly-typed alternative from shared.types

  netra_backend/app/services/agent_service_streaming.py:37 - Hardcoded test/placeholder ID - should use typed constants
    Fix: Use strongly-typed alternative from shared.types

  netra_backend/app/services/agent_websocket_bridge.py:950 - String literal WebSocket event type - should use enum
    Fix: Use WebSocketEventType enum from shared.types instead of string literal

  netra_backend/app/services/agent_websocket_bridge.py:959 - String literal WebSocket event type - should use enum
    Fix: Use WebSocketEventType enum from shared.types instead of string literal

  netra_backend/app/services/agent_websocket_bridge.py:1027 - String literal WebSocket event type - should use enum
    Fix: Use WebSocketEventType enum from shared.types instead of string literal

  netra_backend/app/services/agent_websocket_bridge.py:1093 - String literal WebSocket event type - should use enum
    Fix: Use WebSocketEventType enum from shared.types instead of string literal

  netra_backend/app/services/agent_websocket_bridge.py:1221 - String literal WebSocket event type - should use enum
    Fix: Use WebSocketEventType enum from shared.types instead of string literal

  netra_backend/app/services/factory_adapter.py:209 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/factory_adapter.py:210 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/factory_adapter.py:211 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/factory_adapter.py:360 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/factory_adapter.py:361 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos

  netra_backend/app/services/factory_adapter.py:400 - Dictionary access to ID field - prone to typos
    Fix: Consider using Pydantic model instead of dict access to prevent typos


TOP AFFECTED FILES:
  netra_backend/app/services/websocket\message_handler.py: 86 issues
  netra_backend/app/websocket_core/handlers.py: 59 issues
  netra_backend/app/agents/supervisor\websocket_notifier.py: 53 issues
  netra_backend/app/websocket_core/unified_manager.py: 53 issues
  netra_backend/app/services/agent_websocket_bridge.py: 44 issues
  netra_backend/app/services/state_persistence.py: 44 issues
  netra_backend/app/services/thread_service.py: 44 issues
  netra_backend/app/services/message_handlers.py: 43 issues
  netra_backend/app/clients/auth_client_core.py: 43 issues
  netra_backend/app/agents/agent_lifecycle.py: 40 issues
