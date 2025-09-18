# Shim module for backward compatibility
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as ConnectionExecutor
WebSocketManager = ConnectionExecutor  # Backward compatibility alias


class ConnectionOperationBuilder:
    """
    Builder for connection operations - backward compatibility shim.
    
    This class provides compatibility with tests that expect a ConnectionOperationBuilder.
    In practice, operations should be performed directly with WebSocketManager.
    """
    
    def __init__(self, user_request: str = "default_request"):
        self.user_request = user_request
        self.manager = ConnectionExecutor()
    
    def build_state(self):
        """Build a basic state object for testing."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        import uuid
        return UserExecutionContext(
            user_id="test_user",
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            agent_context={
                'user_request': self.user_request,
                'test_compatibility_mode': True
            }
        )
