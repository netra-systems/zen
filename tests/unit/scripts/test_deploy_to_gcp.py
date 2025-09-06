from shared.isolated_environment import IsolatedEnvironment
import asyncio


class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
        async def send_json(self, message: dict):
            """Send JSON message."""
            if self._closed:
                raise RuntimeError("WebSocket is closed")
                self.messages_sent.append(message)
        
                async def close(self, code: int = 1000, reason: str = "Normal closure"):
                    """Close WebSocket connection."""
                    pass
                    self._closed = True
                    self.is_connected = False
        
                    def get_messages(self) -> list:
                        """Get all sent messages."""
                        # FIXED: await outside async - using pass
                        pass
                        return self.messages_sent.copy()
