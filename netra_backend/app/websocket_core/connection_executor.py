# Shim module for backward compatibility
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as ConnectionExecutor
from shared.id_generation.unified_id_generator import UnifiedIdGenerator  # SSOT Import for Phase 2 UUID violation remediation
WebSocketManager = ConnectionExecutor  # Backward compatibility alias


class ConnectionOperationBuilder:
    """
    Builder for connection operations - backward compatibility shim.
    
    This class provides compatibility with tests that expect a ConnectionOperationBuilder.
    In practice, operations should be performed directly with WebSocketManager.
    """
    
    def __init__(self, user_request: str = "default_request"):
        self.user_request = user_request
        # Delay manager creation to avoid factory pattern issues during import
        self.manager = None
    
    def build_state(self):
        """Build a basic state object for testing."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        import uuid

        # Generate SSOT-compliant IDs for test compatibility
        thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids("test_user", "test")

        return UserExecutionContext(
            user_id="test_user",
            thread_id=thread_id,
            run_id=run_id,
            agent_context={
                'user_request': self.user_request,
                'test_compatibility_mode': True
            }
        )
