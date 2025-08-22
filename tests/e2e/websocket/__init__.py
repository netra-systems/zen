import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent
while not (PROJECT_ROOT / 'netra_backend').exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

"""WebSocket Core Functionality Tests

WebSocket testing package focusing on CORE BASIC FUNCTIONALITY:
- Connection state synchronization (Test #10)
- Message ordering and delivery 
- Heartbeat and keep-alive mechanisms
- Error handling and recovery

Follows implementation plan from websocket_test_implementation_plan.md
"""