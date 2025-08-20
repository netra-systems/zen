"""Fixtures Tests - Split from test_example_message_integration_final.py"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.routes.example_messages_enhanced import (
from app.handlers.example_message_handler_enhanced import (
from app.logging_config import central_logger
from app.handlers.example_message_handler_enhanced import ExampleMessageMetadata
from app.routes.example_messages_enhanced import example_message_websocket_enhanced

    def app(self):
        """Create FastAPI app with enhanced routes"""
        app = FastAPI()
        app.include_router(router)
        return app

    def app(self):
        """Create FastAPI app with enhanced routes"""
        app = FastAPI()
        app.include_router(router)
        return app

    def client(self, app):
        """Create test client"""
        return TestClient(app)

    def mock_dependencies(self):
        """Mock all external dependencies"""
        mocks = {}
        
        # Mock WebSocket manager
        mocks['ws_manager'] = Mock()
        mocks['ws_manager'].connect_user = AsyncMock(return_value={'connection_id': 'test'})
        mocks['ws_manager'].disconnect_user = AsyncMock()
        mocks['ws_manager'].send_message_to_user = AsyncMock()
        mocks['ws_manager'].handle_message = AsyncMock()
        
        # Mock database
        mocks['db_session'] = AsyncMock()
        mocks['db_session'].execute = AsyncMock()
        mocks['db_session'].__aenter__ = AsyncMock(return_value=mocks['db_session'])
        mocks['db_session'].__aexit__ = AsyncMock()
        
        # Mock LLM manager
        mocks['llm_manager'] = Mock()
        
        # Mock supervisor
        mocks['supervisor'] = Mock()
        mocks['supervisor'].process_message = AsyncMock(
            return_value=Mock(content="Test optimization response")
        )
        
        return mocks
