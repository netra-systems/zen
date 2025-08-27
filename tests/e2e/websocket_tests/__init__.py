import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent

"""WebSocket Core Functionality Tests

WebSocket testing package focusing on CORE BASIC FUNCTIONALITY:
- Connection state synchronization (Test #10)
- Message ordering and delivery 
- Heartbeat and keep-alive mechanisms
- Error handling and recovery

Follows implementation plan from websocket_test_implementation_plan.md
"""