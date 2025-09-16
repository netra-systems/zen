"""
Multi-Service Authentication Test Helpers
Helper classes and utilities for multi-service authentication testing.
"""

import asyncio
import json
import subprocess
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.tests.integration.helpers.redis_l3_helpers import MockWebSocketForRedis

logger = central_logger.get_logger(__name__)

class PostgreSQLContainer:
    """Manages PostgreSQL container for auth service database."""
    
    def __init__(self, port: int = 5435):
        self.port = port
        self.container_name = f"netra-test-postgres-auth-{uuid.uuid4().hex[:8]}"
        self.container_id = None
        self.database_url = f"postgresql+asyncpg://auth_user:auth_pass@localhost:{port}/auth_test"
    
    async def start(self) -> str:
        """Start PostgreSQL container."""
        try:
            await self._cleanup_existing()
            
            cmd = [
                "docker", "run", "-d",
                "--name", self.container_name,
                "-p", f"{self.port}:5432",
                "-e", "POSTGRES_DB=auth_test",
                "-e", "POSTGRES_USER=auth_user",
                "-e", "POSTGRES_PASSWORD=auth_pass",
                "postgres:15-alpine"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise RuntimeError(f"Failed to start PostgreSQL: {result.stderr}")
            
            self.container_id = result.stdout.strip()
            await self._wait_for_ready()
            
            logger.info(f"PostgreSQL container started: {self.container_name}")
            return self.database_url
            
        except Exception as e:
            await self.stop()
            raise RuntimeError(f"PostgreSQL startup failed: {e}")
    
    async def stop(self) -> None:
        """Stop PostgreSQL container."""
        if self.container_id:
            try:
                subprocess.run(["docker", "stop", self.container_id], 
                             capture_output=True, timeout=10)
                subprocess.run(["docker", "rm", self.container_id], 
                             capture_output=True, timeout=10)
                logger.info(f"PostgreSQL container stopped: {self.container_name}")
            except Exception as e:
                logger.warning(f"Error stopping PostgreSQL: {e}")
            finally:
                self.container_id = None
    
    async def _cleanup_existing(self) -> None:
        """Clean up existing container."""
        try:
            subprocess.run(["docker", "stop", self.container_name], 
                         capture_output=True, timeout=5)
            subprocess.run(["docker", "rm", self.container_name], 
                         capture_output=True, timeout=5)
        except:
            pass
    
    async def _wait_for_ready(self, timeout: int = 60) -> None:
        """Wait for PostgreSQL to be ready."""
        from sqlalchemy import create_engine, text
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                sync_url = self.database_url.replace("+asyncpg", "")
                engine = create_engine(sync_url)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                engine.dispose()
                return
            except Exception:
                await asyncio.sleep(1)
        
        raise RuntimeError("PostgreSQL failed to become ready")

class AuthServiceSimulator:
    """Simulates auth service for testing token generation."""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.service_url = "http://localhost:8082"
        self.generated_tokens = {}
        self.auth_requests = []
    
    async def start(self) -> str:
        """Start auth service simulator."""
        logger.info("Auth service simulator started")
        return self.service_url
    
    async def stop(self) -> None:
        """Stop auth service simulator."""
        logger.info("Auth service simulator stopped")
    
    async def generate_token(self, user_id: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Generate JWT token and store in Redis."""
        try:
            token = f"jwt_token_{user_id}_{uuid.uuid4().hex[:8]}"
            
            token_data = {
                "user_id": user_id,
                "permissions": ["read", "write"],
                "tier": "free",
                "issued_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "issuer": "auth_service"
            }
            
            token_key = f"jwt_token:{token}"
            await self.redis_client.set(token_key, json.dumps(token_data), ex=3600)
            
            self.generated_tokens[user_id] = token
            self.auth_requests.append({
                "user_id": user_id,
                "action": "generate_token",
                "success": True,
                "token": token,
                "timestamp": time.time()
            })
            
            return {"success": True, "token": token, "user_id": user_id}
            
        except Exception as e:
            self.auth_requests.append({
                "user_id": user_id,
                "action": "generate_token",
                "success": False,
                "error": str(e),
                "timestamp": time.time()
            })
            return {"success": False, "error": f"Token generation failed: {str(e)}"}

class BackendServiceSimulator:
    """Simulates main backend service for token validation testing."""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.validated_tokens = []
        self.token_cache = {}
    
    async def validate_token_from_redis(self, token: str) -> Dict[str, Any]:
        """Simulate backend validating token from Redis."""
        try:
            token_key = f"jwt_token:{token}"
            token_data = await self.redis_client.get(token_key)
            
            if not token_data:
                return {"valid": False, "error": "Token not found in Redis"}
            
            token_dict = json.loads(token_data)
            
            required_fields = ["user_id", "permissions", "expires_at"]
            for field in required_fields:
                if field not in token_dict:
                    return {"valid": False, "error": f"Missing field: {field}"}
            
            expires_at = datetime.fromisoformat(token_dict["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                return {"valid": False, "error": "Token expired"}
            
            self.token_cache[token] = token_dict
            self.validated_tokens.append({
                "token": token,
                "user_id": token_dict["user_id"],
                "validated_at": time.time()
            })
            
            return {
                "valid": True,
                "user_id": token_dict["user_id"],
                "permissions": token_dict["permissions"],
                "expires_at": token_dict["expires_at"]
            }
            
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

class WebSocketServiceSimulator:
    """Simulates WebSocket service for real-time auth testing."""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.active_connections = {}
        self.auth_attempts = []
    
    async def authenticate_websocket(self, token: str) -> Dict[str, Any]:
        """Simulate WebSocket authentication with token."""
        auth_attempt = {
            "token": token,
            "timestamp": time.time(),
            "success": False,
            "user_id": None
        }
        
        try:
            token_key = f"jwt_token:{token}"
            token_data = await self.redis_client.get(token_key)
            
            if not token_data:
                auth_attempt["error"] = "Token not found"
                self.auth_attempts.append(auth_attempt)
                return {"authenticated": False, "error": "Invalid token"}
            
            token_dict = json.loads(token_data)
            user_id = token_dict["user_id"]
            
            expires_at = datetime.fromisoformat(token_dict["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                auth_attempt["error"] = "Token expired"
                self.auth_attempts.append(auth_attempt)
                return {"authenticated": False, "error": "Token expired"}
            
            connection_id = f"ws_{user_id}_{uuid.uuid4().hex[:8]}"
            websocket = MockWebSocketForRedis(user_id)
            
            self.active_connections[connection_id] = {
                "user_id": user_id,
                "websocket": websocket,
                "connected_at": time.time(),
                "token": token
            }
            
            auth_attempt["success"] = True
            auth_attempt["user_id"] = user_id
            auth_attempt["connection_id"] = connection_id
            self.auth_attempts.append(auth_attempt)
            
            return {
                "authenticated": True,
                "user_id": user_id,
                "connection_id": connection_id,
                "websocket": websocket
            }
            
        except Exception as e:
            auth_attempt["error"] = str(e)
            self.auth_attempts.append(auth_attempt)
            return {"authenticated": False, "error": f"Auth error: {str(e)}"}
    
    async def send_message_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send message to authenticated user."""
        for conn_id, conn_data in self.active_connections.items():
            if conn_data["user_id"] == user_id:
                websocket = conn_data["websocket"]
                await websocket.send_json(message)
                return True
        return False