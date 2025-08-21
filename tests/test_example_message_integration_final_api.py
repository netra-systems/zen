"""Api Tests - Split from test_example_message_integration_final.py"""

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
from app.logging_config import central_logger
from app.handlers.example_message_handler_enhanced import ExampleMessageMetadata
from app.routes.example_messages_enhanced import example_message_websocket_enhanced


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def client(self, app):
        """Create test client"""
        return TestClient(app)

    def test_enhanced_api_endpoints(self, client, mock_dependencies):
        """Test all enhanced API endpoints"""
        
        with patch('app.routes.example_messages_enhanced.get_example_message_handler') as mock_handler_getter:
            mock_handler = Mock()
            mock_handler.get_session_stats.return_value = {
                'active_sessions': 5,
                'processing_sessions': 2,
                'avg_processing_time': 15.5
            }
            mock_handler.get_active_sessions.return_value = {
                'session_1': {'status': 'processing', 'metadata': {'category': 'cost-optimization'}},
                'session_2': {'status': 'completed', 'metadata': {'category': 'latency-optimization'}}
            }
            mock_handler_getter.return_value = mock_handler
            
            with patch('app.routes.example_messages_enhanced.get_async_db', return_value=mock_dependencies['db_session']):
                
                # Test enhanced stats endpoint
                response = client.get("/api/v1/example-messages/stats")
                assert response.status_code == 200
                
                data = response.json()
                assert data['status'] == 'success'
                assert 'circuit_breaker_stats' in data
                assert 'message_sequencing_stats' in data
                assert 'connection_stats' in data
                
                # Test enhanced health endpoint
                response = client.get("/api/v1/example-messages/health")
                assert response.status_code in [200, 503]  # Could be degraded
                
                health_data = response.json()
                assert 'handler_active' in health_data
                assert 'database_healthy' in health_data
                assert 'circuit_breaker_healthy' in health_data
                assert 'system_metrics' in health_data
                
                # Test circuit breaker reset endpoint
                response = client.get("/api/v1/example-messages/circuit-breaker/reset")
                assert response.status_code == 200
                
                # Test pending messages endpoint
                response = client.get("/api/v1/example-messages/pending-messages/test_user")
                assert response.status_code == 200
                
                pending_data = response.json()
                assert 'pending_count' in pending_data
                assert 'pending_messages' in pending_data
# )  # Orphaned closing parenthesis