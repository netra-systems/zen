"""Utilities Tests - Split from test_websocket_reconnection.py

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

    def _init_websocket_infrastructure(self):
        """Initialize WebSocket infrastructure components"""
        # Real WebSocket Manager
        ws_manager = WebSocketManager()
        
        # Mock state persistence service
        state_service = Mock(spec=StatePersistenceService)
        state_service.save_websocket_state = AsyncMock()
        state_service.load_websocket_state = AsyncMock()
        state_service.get_message_queue = AsyncMock(return_value=[])
        
        # Mock rate limiter
        rate_limiter = Mock(spec=RateLimiter)
        rate_limiter.check_rate_limit = AsyncMock(return_value=True)
        
        return {
            "ws_manager": ws_manager,
            "state_service": state_service,
            "rate_limiter": rate_limiter
        }

    def _create_workflow_state(self):
        """Create state for long-running optimization workflow"""
        return {
            "workflow_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "thread_id": str(uuid.uuid4()),
            "run_id": str(uuid.uuid4()),
            "workflow_stage": "data_collection",
            "progress_percentage": 45,
            "messages_sent": [
                {"type": "agent_started", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"type": "sub_agent_update", "progress": 25, "timestamp": datetime.now(timezone.utc).isoformat()},
                {"type": "sub_agent_update", "progress": 45, "timestamp": datetime.now(timezone.utc).isoformat()}
            ],
            "pending_messages": []
        }
