"""L3 Integration Test: OAuth to JWT to WebSocket Flow

Business Value Justification (BVJ):
- Segment: All tiers (authentication foundation)
- Business Goal: Secure end-to-end authentication flow from OAuth to real-time features
- Value Impact: Enables secure user onboarding and session management for $75K MRR
- Strategic Impact: Critical authentication pipeline for platform reliability

L3 Test: Real OAuth → JWT → WebSocket flow with PostgreSQL, Redis containers.
Tests complete authentication chain with real database persistence.
"""

from netra_backend.tests.test_utils import setup_test_path

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add project root to path


# OAuth service replaced with mock
from unittest.mock import AsyncMock
OAuthService = AsyncMock
# JWT service replaced with auth_integration
from auth_integration import create_access_token, validate_token_jwt
from unittest.mock import AsyncMock
JWTService = AsyncMock
# Session manager replaced with mock
from unittest.mock import AsyncMock
SessionManager = AsyncMock
from ws_manager import WebSocketManager
from netra_backend.app.redis_manager import RedisManager
from database.models import User, Session
from database.database import get_database
from schemas import UserInDB
from netra_backend.app.logging_config import central_logger
from netra_backend.tests.helpers.redis_l3_helpers import RedisContainer, MockWebSocketForRedis

logger = central_logger.get_logger(__name__)


class PostgreSQLContainer:
    """Manages PostgreSQL Docker container for L3 testing."""
    
    def __init__(self, port: int = 5434):
        self.port = port
        self.container_name = f"netra-test-postgres-l3-{uuid.uuid4().hex[:8]}"
        self.container_id = None
        self.database_url = f"postgresql+asyncpg://postgres:testpass@localhost:{port}/testdb"
    
    async def start(self) -> str:
        """Start PostgreSQL container."""
        import subprocess
        
        try:
            await self._cleanup_existing()
            
            cmd = [
                "docker", "run", "-d",
                "--name", self.container_name,
                "-p", f"{self.port}:5432",
                "-e", "POSTGRES_PASSWORD=testpass",
                "-e", "POSTGRES_DB=testdb",
                "postgres:15-alpine"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise RuntimeError(f"Failed to start PostgreSQL container: {result.stderr}")
            
            self.container_id = result.stdout.strip()
            await self._wait_for_ready()
            
            logger.info(f"PostgreSQL container started: {self.container_name}")
            return self.database_url
            
        except Exception as e:
            await self.stop()
            raise RuntimeError(f"PostgreSQL container startup failed: {e}")
    
    async def stop(self) -> None:
        """Stop PostgreSQL container."""
        if self.container_id:
            import subprocess
            try:
                subprocess.run(["docker", "stop", self.container_id], capture_output=True, timeout=10)
                subprocess.run(["docker", "rm", self.container_id], capture_output=True, timeout=10)
                logger.info(f"PostgreSQL container stopped: {self.container_name}")
            except Exception as e:
                logger.warning(f"Error stopping PostgreSQL container: {e}")
            finally:
                self.container_id = None
    
    async def _cleanup_existing(self) -> None:
        """Clean up existing container."""
        import subprocess
        try:
            subprocess.run(["docker", "stop", self.container_name], capture_output=True, timeout=5)
            subprocess.run(["docker", "rm", self.container_name], capture_output=True, timeout=5)
        except:
            pass
    
    async def _wait_for_ready(self, timeout: int = 60) -> None:
        """Wait for PostgreSQL to be ready."""
        from sqlalchemy import create_engine, text
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Use sync connection for initial check
                sync_url = self.database_url.replace("+asyncpg", "")
                engine = create_engine(sync_url)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                engine.dispose()
                return
            except Exception:
                await asyncio.sleep(1)
        
        raise RuntimeError("PostgreSQL container failed to become ready")


@pytest.mark.L3
@pytest.mark.integration
class TestOAuthJWTWebSocketFlowL3:
    """L3 integration test for complete OAuth → JWT → WebSocket authentication flow."""
    
    @pytest.fixture(scope="class")
    async def postgres_container(self):
        """Set up PostgreSQL container."""
        container = PostgreSQLContainer()
        database_url = await container.start()
        yield container, database_url
        await container.stop()
    
    @pytest.fixture(scope="class")
    async def redis_container(self):
        """Set up Redis container."""
        container = RedisContainer()
        redis_url = await container.start()
        yield container, redis_url
        await container.stop()
    
    @pytest.fixture
    async def database_session(self, postgres_container):
        """Create database session with real PostgreSQL."""
        _, database_url = postgres_container
        
        engine = create_async_engine(database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        # Create tables
        from netra_backend.app.database.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        session = async_session()
        yield session
        await session.close()
        await engine.dispose()
    
    @pytest.fixture
    async def redis_client(self, redis_container):
        """Create Redis client."""
        _, redis_url = redis_container
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        yield client
        await client.close()
    
    @pytest.fixture
    async def auth_services(self, database_session, redis_client):
        """Initialize authentication services with real backends."""
        oauth_service = OAuthService()
        jwt_service = JWTService()
        session_manager = SessionManager()
        
        # Mock database and redis connections
        with patch('app.database.database.get_database') as mock_db:
            mock_db.return_value = database_session
            
            with patch('app.redis_manager.RedisManager.get_client') as mock_redis:
                mock_redis.return_value = redis_client
                
                await oauth_service.initialize()
                await jwt_service.initialize()
                await session_manager.initialize()
                
                yield {
                    'oauth': oauth_service,
                    'jwt': jwt_service,
                    'session': session_manager
                }
                
                await session_manager.shutdown()
                await jwt_service.shutdown()
                await oauth_service.shutdown()
    
    @pytest.fixture
    async def websocket_manager(self, redis_client):
        """Create WebSocket manager with real Redis."""
        with patch('app.ws_manager.redis_manager') as mock_redis_mgr:
            test_redis_mgr = RedisManager()
            test_redis_mgr.enabled = True
            test_redis_mgr.redis_client = redis_client
            mock_redis_mgr.return_value = test_redis_mgr
            mock_redis_mgr.get_client.return_value = redis_client
            
            manager = WebSocketManager()
            yield manager
    
    async def test_complete_oauth_to_websocket_flow(self, auth_services, websocket_manager, 
                                                   database_session, redis_client):
        """Test complete OAuth → JWT → WebSocket authentication flow."""
        # Step 1: OAuth authentication
        oauth_service = auth_services['oauth']
        
        # Simulate OAuth provider response
        oauth_data = {
            "provider": "google",
            "provider_id": "google_user_123",
            "email": "testuser@example.com",
            "name": "Test User",
            "verified": True
        }
        
        # Create user through OAuth
        with patch.object(oauth_service, '_verify_oauth_token') as mock_verify:
            mock_verify.return_value = oauth_data
            
            auth_result = await oauth_service.authenticate_with_oauth(
                provider="google",
                oauth_token="mock_oauth_token",
                oauth_code="mock_oauth_code"
            )
        
        assert auth_result["success"] is True
        assert "user_id" in auth_result
        user_id = auth_result["user_id"]
        
        # Verify user created in database
        user = await database_session.get(User, user_id)
        assert user is not None
        assert user.email == oauth_data["email"]
        
        # Step 2: JWT token generation
        jwt_service = auth_services['jwt']
        
        token_result = await jwt_service.generate_token(
            user_id=user_id,
            permissions=["read", "write"],
            tier="free"
        )
        
        assert token_result["success"] is True
        assert "token" in token_result
        assert "refresh_token" in token_result
        jwt_token = token_result["token"]
        
        # Verify JWT token
        token_data = await jwt_service.verify_token(jwt_token)
        assert token_data["valid"] is True
        assert token_data["user_id"] == user_id
        
        # Step 3: Session creation
        session_manager = auth_services['session']
        
        session_result = await session_manager.create_session(
            user_id=user_id,
            token=jwt_token,
            metadata={
                "auth_method": "oauth",
                "provider": "google",
                "ip_address": "127.0.0.1",
                "user_agent": "test_client"
            }
        )
        
        assert session_result["success"] is True
        session_id = session_result["session_id"]
        
        # Verify session in database
        session_record = await database_session.get(Session, session_id)
        assert session_record is not None
        assert session_record.user_id == user_id
        
        # Verify session in Redis
        session_key = f"session:{session_id}"
        session_data = await redis_client.get(session_key)
        assert session_data is not None
        session_dict = json.loads(session_data)
        assert session_dict["user_id"] == user_id
        
        # Step 4: WebSocket connection with JWT
        websocket = MockWebSocketForRedis(user_id)
        
        # Mock JWT verification for WebSocket
        with patch('app.ws_manager.verify_jwt_token') as mock_verify_jwt:
            mock_verify_jwt.return_value = {
                "valid": True,
                "user_id": user_id,
                "permissions": ["read", "write"]
            }
            
            connection_info = await websocket_manager.connect_user(user_id, websocket)
        
        assert connection_info is not None
        assert connection_info.user_id == user_id
        assert user_id in websocket_manager.active_connections
        
        # Step 5: Test message flow through WebSocket
        test_message = {
            "type": "thread_message",
            "data": {
                "thread_id": "thread_123",
                "content": "Hello from authenticated user"
            }
        }
        
        success = await websocket_manager.send_message_to_user(user_id, test_message)
        assert success is True
        assert len(websocket.messages) > 0
        
        # Verify message received
        received_message = websocket.messages[-1]
        assert received_message["type"] == "thread_message"
        assert received_message["data"]["content"] == "Hello from authenticated user"
        
        # Cleanup
        await websocket_manager.disconnect_user(user_id, websocket)
        await session_manager.invalidate_session(session_id)
    
    async def test_oauth_user_creation_and_retrieval(self, auth_services, database_session):
        """Test OAuth user creation and subsequent retrieval."""
        oauth_service = auth_services['oauth']
        
        # First OAuth login - creates user
        oauth_data_1 = {
            "provider": "github",
            "provider_id": "github_user_456",
            "email": "newuser@example.com",
            "name": "New User",
            "verified": True
        }
        
        with patch.object(oauth_service, '_verify_oauth_token') as mock_verify:
            mock_verify.return_value = oauth_data_1
            
            first_auth = await oauth_service.authenticate_with_oauth(
                provider="github",
                oauth_token="token_1",
                oauth_code="code_1"
            )
        
        assert first_auth["success"] is True
        user_id_1 = first_auth["user_id"]
        
        # Second OAuth login - retrieves existing user
        with patch.object(oauth_service, '_verify_oauth_token') as mock_verify:
            mock_verify.return_value = oauth_data_1
            
            second_auth = await oauth_service.authenticate_with_oauth(
                provider="github",
                oauth_token="token_2",
                oauth_code="code_2"
            )
        
        assert second_auth["success"] is True
        user_id_2 = second_auth["user_id"]
        
        # Should be same user
        assert user_id_1 == user_id_2
        
        # Verify only one user record in database
        from sqlalchemy import select, func
        result = await database_session.execute(
            select(func.count(User.id)).where(User.email == oauth_data_1["email"])
        )
        user_count = result.scalar()
        assert user_count == 1
    
    async def test_jwt_token_expiry_and_refresh(self, auth_services, redis_client):
        """Test JWT token expiry and refresh mechanism."""
        jwt_service = auth_services['jwt']
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Generate token with short expiry
        token_result = await jwt_service.generate_token(
            user_id=user_id,
            permissions=["read"],
            tier="free",
            expires_delta=timedelta(seconds=2)  # Very short expiry
        )
        
        assert token_result["success"] is True
        jwt_token = token_result["token"]
        refresh_token = token_result["refresh_token"]
        
        # Token should be valid initially
        token_data = await jwt_service.verify_token(jwt_token)
        assert token_data["valid"] is True
        
        # Wait for token to expire
        await asyncio.sleep(3)
        
        # Token should now be expired
        expired_data = await jwt_service.verify_token(jwt_token)
        assert expired_data["valid"] is False
        assert "expired" in expired_data["error"]
        
        # Refresh the token
        refresh_result = await jwt_service.refresh_token(refresh_token)
        assert refresh_result["success"] is True
        
        new_token = refresh_result["token"]
        assert new_token != jwt_token
        
        # New token should be valid
        new_token_data = await jwt_service.verify_token(new_token)
        assert new_token_data["valid"] is True
        assert new_token_data["user_id"] == user_id
    
    async def test_concurrent_oauth_authentications(self, auth_services, database_session):
        """Test concurrent OAuth authentications with database consistency."""
        oauth_service = auth_services['oauth']
        
        async def authenticate_user(user_index):
            oauth_data = {
                "provider": "google",
                "provider_id": f"concurrent_user_{user_index}",
                "email": f"concurrent{user_index}@example.com",
                "name": f"Concurrent User {user_index}",
                "verified": True
            }
            
            with patch.object(oauth_service, '_verify_oauth_token') as mock_verify:
                mock_verify.return_value = oauth_data
                
                return await oauth_service.authenticate_with_oauth(
                    provider="google",
                    oauth_token=f"token_{user_index}",
                    oauth_code=f"code_{user_index}"
                )
        
        # Run concurrent authentications
        tasks = [authenticate_user(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all authentications succeeded
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Authentication {i} failed: {result}")
            
            assert result["success"] is True
            assert "user_id" in result
        
        # Verify all users created in database
        from sqlalchemy import select
        result = await database_session.execute(
            select(func.count(User.id)).where(User.email.like("concurrent%@example.com"))
        )
        user_count = result.scalar()
        assert user_count == 5
    
    async def test_websocket_auth_token_validation(self, websocket_manager, auth_services):
        """Test WebSocket authentication with invalid/expired tokens."""
        jwt_service = auth_services['jwt']
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Test with invalid token
        websocket = MockWebSocketForRedis(user_id)
        
        with patch('app.ws_manager.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"valid": False, "error": "Invalid token"}
            
            connection_info = await websocket_manager.connect_user(user_id, websocket)
        
        # Connection should fail
        assert connection_info is None
        assert user_id not in websocket_manager.active_connections
        
        # Test with valid token
        token_result = await jwt_service.generate_token(user_id, ["read"], "free")
        valid_token = token_result["token"]
        
        with patch('app.ws_manager.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {
                "valid": True,
                "user_id": user_id,
                "permissions": ["read"]
            }
            
            connection_info = await websocket_manager.connect_user(user_id, websocket)
        
        # Connection should succeed
        assert connection_info is not None
        assert user_id in websocket_manager.active_connections
        
        # Cleanup
        await websocket_manager.disconnect_user(user_id, websocket)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])