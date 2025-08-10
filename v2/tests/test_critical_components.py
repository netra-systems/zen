"""Critical Components Test Suite - Tests for the 10 most important system components"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json
import uuid
from datetime import datetime

# Test 1: Basic API Health Check
def test_health_check():
    """Test that the health check endpoint returns expected response"""
    from app.main import app
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

# Test 2: Authentication System
def test_authentication_flow():
    """Test basic authentication flow"""
    from app.auth.auth import create_access_token, decode_access_token
    from app.config import settings
    
    # Create a test token
    test_user_id = str(uuid.uuid4())
    token = create_access_token(data={"sub": test_user_id})
    assert token is not None
    
    # Decode the token
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded.get("sub") == test_user_id

# Test 3: WebSocket Manager
def test_websocket_manager():
    """Test WebSocket connection manager functionality"""
    from app.ws_manager import WebSocketConnectionManager
    
    manager = WebSocketConnectionManager()
    assert manager is not None
    assert hasattr(manager, 'active_connections')
    assert hasattr(manager, 'connect')
    assert hasattr(manager, 'disconnect')

# Test 4: Configuration Loading
def test_config_loading():
    """Test configuration loading and validation"""
    from app.config import settings
    
    assert settings is not None
    assert hasattr(settings, 'environment')
    assert hasattr(settings, 'database_url')
    assert settings.environment in ['development', 'staging', 'production', 'testing']

# Test 5: Database Session Creation
@pytest.mark.asyncio
async def test_database_session():
    """Test database session creation"""
    from app.db.postgres import engine
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    assert engine is not None
    AsyncSessionLocal = sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        assert session is not None
        # Test simple query
        result = await session.execute("SELECT 1")
        assert result is not None

# Test 6: Agent Service Initialization
def test_agent_service_initialization():
    """Test that agent service can be initialized"""
    with patch('app.services.agent_service.LLMManager'):
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

# Test 7: Supervisor Agent Creation
def test_supervisor_agent_creation():
    """Test supervisor agent creation and registration"""
    with patch('app.agents.supervisor.LLMManager'):
        from app.agents.supervisor import Supervisor
        
        mock_llm_manager = Mock()
        supervisor = Supervisor(llm_manager=mock_llm_manager)
        
        assert supervisor is not None
        assert hasattr(supervisor, 'agents')
        assert hasattr(supervisor, 'process_message')

# Test 8: Thread Service Operations
@pytest.mark.asyncio
async def test_thread_service():
    """Test thread service basic operations"""
    from app.services.thread_service import ThreadService
    from app.schemas import ThreadCreate
    
    mock_repo = AsyncMock()
    mock_repo.create_thread.return_value = {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "name": "Test Thread",
        "created_at": datetime.utcnow()
    }
    
    service = ThreadService(thread_repository=mock_repo)
    
    thread_data = ThreadCreate(name="Test Thread")
    user_id = str(uuid.uuid4())
    
    result = await service.create_thread(thread_data, user_id)
    assert result is not None
    assert result["name"] == "Test Thread"

# Test 9: Message Processing Pipeline
@pytest.mark.asyncio
async def test_message_processing():
    """Test message processing through the system"""
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
    
    # Verify message can be serialized
    json_str = message.model_dump_json()
    assert json_str is not None
    
    # Verify it can be deserialized
    parsed = WebSocketMessage.model_validate_json(json_str)
    assert parsed.type == message.type

# Test 10: Error Handling Middleware
def test_error_handling():
    """Test error handling and exception catching"""
    from app.core.exceptions import NetraException
    from app.core.error_context import ErrorContext
    
    # Test custom exception
    error = NetraException(
        message="Test error",
        error_code="TEST_ERROR",
        status_code=400
    )
    
    assert error.message == "Test error"
    assert error.error_code == "TEST_ERROR"
    assert error.status_code == 400
    
    # Test error context
    context = ErrorContext()
    assert hasattr(context, 'trace_id')
    assert context.trace_id is not None

# Additional helper test for logging
def test_logging_configuration():
    """Test logging is properly configured"""
    from app.logging_config import central_logger
    
    assert central_logger is not None
    assert hasattr(central_logger, 'info')
    assert hasattr(central_logger, 'error')
    assert hasattr(central_logger, 'warning')

# Test for Redis connection
def test_redis_manager():
    """Test Redis manager initialization"""
    from app.redis_manager import RedisManager
    
    manager = RedisManager()
    assert manager is not None
    assert hasattr(manager, 'get_client')

# Test for Supply Catalog Service
@pytest.mark.asyncio
async def test_supply_catalog_service():
    """Test supply catalog service operations"""
    from app.services.supply_catalog_service import SupplyCatalogService
    
    mock_repo = AsyncMock()
    mock_repo.search_models.return_value = []
    
    service = SupplyCatalogService(supply_catalog_repository=mock_repo)
    
    results = await service.search_models(query="test")
    assert results is not None
    assert isinstance(results, list)

# Test for Key Manager
def test_key_manager():
    """Test key manager functionality"""
    from app.services.key_manager import KeyManager
    from app.config import settings
    
    key_manager = KeyManager.load_from_settings(settings)
    assert key_manager is not None
    assert hasattr(key_manager, 'fernet_key')

# Test for Schema Validation
def test_schema_validation():
    """Test Pydantic schema validation"""
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
    
    # Invalid email should raise validation error
    with pytest.raises(ValueError):
        invalid_data = {
            "email": "not-an-email",
            "full_name": "Test User",
            "password": "password"
        }
        UserCreate(**invalid_data)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])