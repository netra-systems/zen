"""Test WebSocket message validation for sub_agent_update."""

from app.schemas.websocket_unified import WebSocketMessageType

# Test if sub_agent_update is in the enum
try:
    msg_type = WebSocketMessageType("sub_agent_update")
    print(f"[OK] 'sub_agent_update' is valid: {msg_type}")
    print(f"  Enum name: {msg_type.name}")
    print(f"  Enum value: {msg_type.value}")
except ValueError as e:
    print(f"[ERROR] Error: {e}")

# Check all available message types
print("\nAll available message types:")
for msg_type in WebSocketMessageType:
    print(f"  {msg_type.name} = '{msg_type.value}'")
    
# Test validation with actual message
from app.websocket.validation import MessageValidator

validator = MessageValidator()
test_message = {
    "type": "sub_agent_update",
    "payload": {
        "sub_agent_name": "test_agent",
        "state": "running"
    }
}

result = validator.validate_message(test_message)
if result is True:
    print(f"\n[OK] Message validation passed")
else:
    print(f"\n[ERROR] Message validation failed: {result.message if hasattr(result, 'message') else result}")