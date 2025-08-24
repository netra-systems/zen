# Shim module for backward compatibility
from netra_backend.app.websocket_core.handlers import BatchMessageHandler

# Simple configuration class for batch handling
class BatchConfig:
    def __init__(self, max_batch_size=10, batch_timeout=1.0):
        self.max_batch_size = max_batch_size
        self.batch_timeout = batch_timeout
