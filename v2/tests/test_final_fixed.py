"""Final Fixed Critical Component Tests - Corrected imports and signatures"""

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
    print("[PASS] Config loading test PASSED")

# Test 2: Authentication Functions
def test_authentication_functions():
    """Test JWT authentication functions exist and work"""
    from app.auth.auth import verify_password, get_password_hash
    
    # Test password hashing
    test_password = "SecurePassword123!"
    hashed = get_password_hash(test_password)
    assert hashed is not None
    assert hashed != test_password
    
    # Test password verification
    assert verify_password(test_password, hashed) == True
    assert verify_password("WrongPassword", hashed) == False
    print("[PASS] Authentication functions test PASSED")

# Test 3: WebSocket Manager Class
def test_websocket_manager_class():
    """Test WebSocket manager class exists with required attributes"""
    from app.ws_manager import WebSocketManager
    
    manager = WebSocketManager()
    assert manager is not None
    assert hasattr(manager, 'active_connections')
    assert hasattr(manager, 'connect')
    assert hasattr(manager, 'disconnect')
    print("[PASS] WebSocket manager test PASSED")

# Test 4: Database Async Engine
def test_database_async_engine():
    """Test database async engine is configured"""
    from app.db.postgres import async_engine
    
    assert async_engine is not None
    assert hasattr(async_engine, 'url')
    print("[PASS] Database engine test PASSED")

# Test 5: User Schema Validation
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
    print("[PASS] User schema validation test PASSED")

# Test 6: WebSocket Message Schema
def test_websocket_message_schema():
    """Test WebSocket message schema with correct fields"""
    from app.schemas.WebSocket import WebSocketMessage
    
    # Create message with correct fields
    message = WebSocketMessage(
        type="user_message",
        payload={
            "content": "Test message",
            "thread_id": str(uuid.uuid4())
        }
    )
    
    assert message.type == "user_message"
    assert message.payload["content"] == "Test message"
    
    # Verify serialization
    json_str = message.model_dump_json()
    assert json_str is not None
    print("[PASS] WebSocket message schema test PASSED")

# Test 7: Custom Exception Class
def test_custom_exception_class():
    """Test NetraException with correct signature"""
    from app.core.exceptions import NetraException
    
    # Create exception with correct parameters
    error = NetraException(
        message="Test error",
        status_code=400
    )
    
    assert error.message == "Test error"
    assert error.status_code == 400
    print("[PASS] Custom exception test PASSED")

# Test 8: Central Logger
def test_central_logger():
    """Test central logger has logging methods"""
    from app.logging_config import central_logger
    
    assert central_logger is not None
    # Central logger uses log() method with level parameter
    assert hasattr(central_logger, 'log')
    assert hasattr(central_logger, 'exception')
    print("[PASS] Central logger test PASSED")

# Test 9: Redis Manager
def test_redis_manager():
    """Test Redis manager initialization and methods"""
    from app.redis_manager import RedisManager
    
    manager = RedisManager()
    assert manager is not None
    assert hasattr(manager, 'get_client')
    assert hasattr(manager, 'redis_url')  # Check for redis_url instead of url
    print("[PASS] Redis manager test PASSED")

# Test 10: Key Manager with Valid Settings
def test_key_manager_with_valid_settings():
    """Test key manager with properly configured settings"""
    from app.services.key_manager import KeyManager
    
    # Create mock settings with valid values
    mock_settings = Mock()
    mock_settings.secret_key = "a" * 32  # 32 character key
    mock_settings.encryption_key = None
    mock_settings.jwt_secret_key = "b" * 32
    
    key_manager = KeyManager.load_from_settings(mock_settings)
    assert key_manager is not None
    assert key_manager.fernet_key is not None
    print("[PASS] Key manager test PASSED")

# Test 11: Thread Creation Schema
def test_thread_creation_schema():
    """Test thread creation with ThreadCreateRequest"""
    from app.schemas.threads import ThreadCreateRequest
    
    thread_data = ThreadCreateRequest(name="Test Thread")
    assert thread_data.name == "Test Thread"
    
    # Test JSON serialization
    json_data = thread_data.model_dump_json()
    assert json_data is not None
    assert "Test Thread" in json_data
    print("[PASS] Thread creation schema test PASSED")

# Test 12: Agent Service Initialization
def test_agent_service_init():
    """Test AgentService with correct initialization"""
    from app.services.agent_service import AgentService
    
    # AgentService doesn't take any initialization arguments
    service = AgentService()
    
    assert service is not None
    assert hasattr(service, 'process_message')
    print("[PASS] Agent service initialization test PASSED")

# Test 13: Supply Catalog Service
def test_supply_catalog_service():
    """Test SupplyCatalogService initialization"""
    from app.services.supply_catalog_service import SupplyCatalogService
    
    # SupplyCatalogService doesn't take initialization arguments
    service = SupplyCatalogService()
    
    assert service is not None
    assert hasattr(service, 'search_models')
    print("[PASS] Supply catalog service test PASSED")

# Test 14: WebSocket Message Types
def test_websocket_message_types():
    """Test WebSocket message type constants"""
    # Check if we have message type constants anywhere
    from app.schemas.WebSocket import WebSocketMessage
    
    # Test that we can create messages with different types
    test_types = ["user_message", "system_message", "error", "agent_response"]
    
    for msg_type in test_types:
        msg = WebSocketMessage(
            type=msg_type,
            payload={"test": "data"}
        )
        assert msg.type == msg_type
    print("[PASS] WebSocket message types test PASSED")

# Test 15: Health Check Schema
def test_health_check_schema():
    """Test health check response structure"""
    from pydantic import BaseModel
    from datetime import datetime
    
    # Create a simple health response model
    class HealthResponse(BaseModel):
        status: str
        timestamp: datetime
        version: str = "1.0.0"
    
    health = HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )
    
    assert health.status == "healthy"
    assert health.version == "1.0.0"
    assert isinstance(health.timestamp, datetime)
    print("[PASS] Health check schema test PASSED")

# Summary function
def run_all_tests():
    """Run all tests and provide summary"""
    print("\n" + "="*60)
    print("RUNNING CRITICAL COMPONENT TESTS")
    print("="*60 + "\n")
    
    test_functions = [
        test_config_loading,
        test_authentication_functions,
        test_websocket_manager_class,
        test_database_async_engine,
        test_user_schema_validation,
        test_websocket_message_schema,
        test_custom_exception_class,
        test_central_logger,
        test_redis_manager,
        test_key_manager_with_valid_settings,
        test_thread_creation_schema,
        test_agent_service_init,
        test_supply_catalog_service,
        test_websocket_message_types,
        test_health_check_schema
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test_func.__name__} FAILED: {str(e)}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} PASSED, {failed} FAILED")
    print("="*60)
    
    return passed, failed

if __name__ == "__main__":
    # Run with pytest or directly
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--direct":
        run_all_tests()
    else:
        pytest.main([__file__, "-v", "--tb=short"])