



class TestWebSocketConnection:

    """Real WebSocket connection for testing instead of mocks."""

    

    def __init__(self):

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

        self._closed = True

        self.is_connected = False

        

    def get_messages(self) -> list:

        """Get all sent messages."""

        return self.messages_sent.copy()

