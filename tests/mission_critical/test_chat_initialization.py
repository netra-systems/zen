import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
import jwt
import pytest
import os
import sys
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import environment management
from shared.isolated_environment import get_env

# Import factory patterns from architecture
from netra_backend.app.services.websocket_bridge_factory import ()
    WebSocketBridgeFactory,
    UserWebSocketEmitter,
    UserWebSocketContext,
    WebSocketEvent
)


# Import test framework components
from test_framework.test_context import TestContext, create_test_context, TestUserContext
from test_framework.backend_client import BackendClient

# Set up isolated test environment
env = get_env()
env.set('SKIP_REAL_SERVICES', 'false', "test)  # We want to test real chat initialization"
env.set('USE_REAL_SERVICES', 'true', test)
env.set('RUN_E2E_TESTS', 'true', "test)"

# Disable service dependency checks for controlled testing
pytestmark = [ ]
pytest.mark.filterwarnings(ignore"),"
pytest.mark.asyncio