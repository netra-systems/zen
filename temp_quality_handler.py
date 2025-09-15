# Temporary file to add QualityRouterHandler to MessageRouter
import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Read the handlers file
handlers_file = "netra_backend/app/websocket_core/handlers.py"

with open(handlers_file, 'r') as f:
    content = f.read()

# Create the QualityRouterHandler class
quality_handler_class = '''

class QualityRouterHandler(BaseMessageHandler):
    """Handler for quality-related messages - ensures quality handlers are discoverable by tests."""

    def __init__(self):
        super().__init__([MessageType.USER_MESSAGE])

    async def handle_message(self, user_id: str, websocket: WebSocket, message) -> bool:
        """Handle quality-related messages by delegating to the router's quality system."""
        try:
            # Get the router instance from the websocket if available
            if hasattr(websocket, '_router'):
                router = websocket._router
                # Extract raw message for quality routing
                raw_message = {
                    "type": message.payload.get("type") if hasattr(message, 'payload') else "unknown",
                    "payload": message.payload if hasattr(message, 'payload') else {},
                    "thread_id": getattr(message, 'thread_id', None)
                }

                # Check if this is a quality message
                if hasattr(router, '_is_quality_message_type') and router._is_quality_message_type(raw_message["type"]):
                    # Delegate to the router's quality handler
                    return await router.handle_quality_message(user_id, raw_message)

            return False  # Not handled
        except Exception as e:
            logger.error(f"Error in QualityRouterHandler: {e}")
            return False

'''

# Find the insertion point (before MessageRouter class)
insertion_point = content.find('class MessageRouter:')
if insertion_point == -1:
    print("Could not find MessageRouter class")
    exit(1)

# Insert the QualityRouterHandler class
new_content = content[:insertion_point] + quality_handler_class + content[insertion_point:]

# Now update the builtin_handlers list to include QualityRouterHandler
old_handlers_list = '''        self.builtin_handlers: List[MessageHandler] = [
            ConnectionHandler(),
            TypingHandler(),
            HeartbeatHandler(),
            AgentHandler(),  # Handle agent status messages
            # CRITICAL FIX: Add AgentRequestHandler as fallback for execute_agent/START_AGENT messages
            # This ensures there's always a handler available for agent execution requests,
            # even when AgentMessageHandler can't be registered due to missing services
            AgentRequestHandler(),  # Fallback handler for START_AGENT messages
            UserMessageHandler(),
            JsonRpcHandler(),
            ErrorHandler(),
            BatchMessageHandler()  # Add batch processing capability
        ]'''

new_handlers_list = '''        self.builtin_handlers: List[MessageHandler] = [
            ConnectionHandler(),
            TypingHandler(),
            HeartbeatHandler(),
            AgentHandler(),  # Handle agent status messages
            # CRITICAL FIX: Add AgentRequestHandler as fallback for execute_agent/START_AGENT messages
            # This ensures there's always a handler available for agent execution requests,
            # even when AgentMessageHandler can't be registered due to missing services
            AgentRequestHandler(),  # Fallback handler for START_AGENT messages
            UserMessageHandler(),
            JsonRpcHandler(),
            ErrorHandler(),
            BatchMessageHandler(),  # Add batch processing capability
            QualityRouterHandler()  # Add quality router handler for SSOT integration
        ]'''

new_content = new_content.replace(old_handlers_list, new_handlers_list)

# Write the updated content back
with open(handlers_file, 'w') as f:
    f.write(new_content)

print("Successfully added QualityRouterHandler to MessageRouter")