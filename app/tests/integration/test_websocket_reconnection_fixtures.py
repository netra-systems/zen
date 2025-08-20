"""Fixtures Tests - Split from test_websocket_reconnection.py

        BVJ: Ensures users don't lose progress during network disruptions. Long-running
        AI optimizations (10-30 minutes) are critical revenue-generating workflows.
        Connection issues causing workflow loss = immediate customer frustration + support costs.
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
import json
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import websockets
from websockets.exceptions import ConnectionClosed
from app.ws_manager import WebSocketManager
from app.websocket.rate_limiter import RateLimiter
from app.schemas.registry import (
from app.services.state_persistence import StatePersistenceService
from starlette.websockets import WebSocket, WebSocketState
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
import tempfile

    def websocket_infrastructure(self):
        """Setup WebSocket infrastructure for testing"""
        return self._init_websocket_infrastructure()

    def long_running_workflow_state(self):
        """Setup state for long-running AI optimization workflow"""
        return self._create_workflow_state()
