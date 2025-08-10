"""Fixed Critical Components Test Suite - Robust tests for core system components"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
import uuid
from datetime import datetime
import sys
import os

# Add app to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Test 1: Configuration Loading (PASSING)
def test_config_loading():
    """Test configuration loading and validation"""
    from app.config import settings
    
    assert settings is not None
    assert hasattr(settings, 'environment')
    assert hasattr(settings, 'database_url')
    assert settings.environment in ['development', 'staging', 'production', 'testing']

# Test 2: Authentication Token Creation
def test_authentication_token_creation():
    """Test JWT token creation and validation"""
    from app.auth.auth import create_access_token, decode_access_token
    
    # Create a test token
    test_user_id = str(uuid.uuid4())
    token = create_access_token(data={"sub": test_user_id})
    assert token is not None
    assert isinstance(token, str)
    
    # Decode the token
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded.get("sub") == test_user_id

# Test 3: WebSocket Manager Structure
def test_websocket_manager_structure():
    """Test WebSocket manager has required methods"""
    from app.ws_manager import WebSocketConnectionManager
    
    manager = WebSocketConnectionManager()
    assert manager is not None
    assert hasattr(manager, 'active_connections')
    assert hasattr(manager, 'connect')
    assert hasattr(manager, 'disconnect')
    assert hasattr(manager, 'send_message')

# Test 4: Database Engine Configuration
def test_database_engine():
    """Test database engine is properly configured"""
    from app.db.postgres import engine
    
    assert engine is not None
    assert hasattr(engine, 'url')
    assert hasattr(engine, 'dialect')

# Test 5: Schema Validation - User Creation
def test_user_schema_validation():
    """Test Pydantic schema validation for user creation"""
    from app.schemas import UserCreate
    
    # Valid user data
    valid_data = {
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "SecurePassword123!"
    }
    
    user = UserCreate(**valid_data)
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.password == "SecurePassword123!"

# Test 6: WebSocket Message Schema
def test_websocket_message_schema():
    """Test WebSocket message schema validation"""
    from app.schemas.WebSocket import WebSocketMessage
    
    message = WebSocketMessage(
        type="user_message",
        data={
            "content": "Test message",
            "thread_id": str(uuid.uuid4())
        }
    )
    
    assert message.type == "user_message"
    assert message.data["content"] == "Test message"
    
    # Verify serialization
    json_str = message.model_dump_json()
    assert json_str is not None
    
    # Verify deserialization
    parsed = WebSocketMessage.model_validate_json(json_str)
    assert parsed.type == message.type
    assert parsed.data["content"] == message.data["content"]

# Test 7: Error Exception Classes
def test_error_exception_classes():
    """Test custom exception classes"""
    from app.core.exceptions import NetraException
    
    error = NetraException(
        message="Test error",
        error_code="TEST_ERROR",
        status_code=400
    )
    
    assert error.message == "Test error"
    assert error.error_code == "TEST_ERROR"
    assert error.status_code == 400

# Test 8: Logging Configuration
def test_logging_configuration():
    """Test logging is properly configured"""
    from app.logging_config import central_logger
    
    assert central_logger is not None
    assert hasattr(central_logger, 'info')
    assert hasattr(central_logger, 'error')
    assert hasattr(central_logger, 'warning')
    assert hasattr(central_logger, 'debug')

# Test 9: Redis Manager Structure
def test_redis_manager_structure():
    """Test Redis manager initialization"""
    from app.redis_manager import RedisManager
    
    manager = RedisManager()
    assert manager is not None
    assert hasattr(manager, 'get_client')
    assert hasattr(manager, 'url')

# Test 10: Key Manager with Mocked Settings
def test_key_manager():
    """Test key manager functionality"""
    from app.services.key_manager import KeyManager
    
    # Create a mock settings object
    mock_settings = Mock()
    mock_settings.secret_key = "test-secret-key-1234567890"
    mock_settings.encryption_key = None
    
    key_manager = KeyManager.load_from_settings(mock_settings)
    assert key_manager is not None
    assert hasattr(key_manager, 'fernet_key')
    assert key_manager.fernet_key is not None

# Test 11: Thread Schema Validation
def test_thread_schema():
    """Test thread creation schema"""
    from app.schemas import ThreadCreate
    
    thread_data = ThreadCreate(name="Test Thread")
    assert thread_data.name == "Test Thread"
    
    # Test JSON serialization
    json_data = thread_data.model_dump_json()
    assert json_data is not None
    assert "Test Thread" in json_data

# Test 12: Agent Service Structure
@patch('app.services.agent_service.LLMManager')
def test_agent_service_structure(mock_llm):
    """Test agent service has required methods"""
    from app.services.agent_service import AgentService
    
    mock_supervisor = Mock()
    mock_thread_service = Mock()
    mock_reference_service = Mock()
    mock_llm_manager = Mock()
    
    service = AgentService(
        supervisor=mock_supervisor,
        thread_service=mock_thread_service,
        reference_service=mock_reference_service,
        llm_manager=mock_llm_manager
    )
    
    assert service is not None
    assert service.supervisor == mock_supervisor
    assert hasattr(service, 'process_message')

# Test 13: Supply Catalog Service Structure
def test_supply_catalog_service_structure():
    """Test supply catalog service structure"""
    from app.services.supply_catalog_service import SupplyCatalogService
    
    mock_repo = Mock()
    service = SupplyCatalogService(supply_catalog_repository=mock_repo)
    
    assert service is not None
    assert hasattr(service, 'search_models')
    assert hasattr(service, 'get_model_by_id')

# Test 14: Message Handler Types
def test_message_handler_types():
    """Test message type constants"""
    from app.services.websocket.message_handler import MessageType
    
    assert hasattr(MessageType, 'USER_MESSAGE')
    assert hasattr(MessageType, 'SYSTEM_MESSAGE')
    assert hasattr(MessageType, 'ERROR')
    assert hasattr(MessageType, 'AGENT_RESPONSE')

# Test 15: Health Check Response Schema
def test_health_response_schema():
    """Test health check response schema"""
    from app.schemas.common import HealthResponse
    from datetime import datetime
    
    health = HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )
    
    assert health.status == "healthy"
    assert health.version == "1.0.0"
    assert isinstance(health.timestamp, datetime)

if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short"])