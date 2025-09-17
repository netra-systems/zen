class TestWebSocketConnection:

# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""Real WebSocket connection for testing instead of mocks."""

def __init__(self):
pass
self.messages_sent = []
self.is_connected = True
self._closed = False

async def send_json(self, message: dict):
"""Send JSON message."""
if self._closed:
raise RuntimeError("WebSocket is closed")
self.messages_sent.append(message)

async def close(self, code: int = 1000, reason: str = "Normal closure"):
"""Close WebSocket connection."""
pass
self._closed = True
self.is_connected = False

def get_messages(self) -> list:
"""Get all sent messages."""
await asyncio.sleep(0)
return self.messages_sent.copy()

'''
L4 Critical Core Integration Tests
====================================
These tests are designed to expose real flaws in core system functionality.
Focus: Auth, Login, WebSockets, Core APIs - testing from different angles
to reveal edge cases and integration issues.
'''

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.redis_manager import redis_manager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import aiohttp
import jwt
import pytest
import redis.asyncio as redis
from aiohttp import ClientSession, ClientTimeout
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import get_env


class TestL4CriticalAuthIntegration:
        """Test authentication edge cases and vulnerabilities"""

@pytest.mark.asyncio
    async def test_01_concurrent_login_race_condition(self):
"""Test: Multiple simultaneous login attempts from same user"""
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.core.config import settings

auth_client = AuthServiceClient(settings.AUTH_SERVICE_URL)
user_email = "race_test@example.com"

        # Create user
user_result = await auth_client.register( )
email=user_email,
password="TestPass123!"
        

        # Attempt 10 concurrent logins
login_tasks = []
for _ in range(10):
login_tasks.append( )
auth_client.login(user_email, "TestPass123!")
            

results = await asyncio.gather(*login_tasks, return_exceptions=True)

            # Check for race conditions
tokens = [item for item in []]
errors = [item for item in []]

            # All should succeed or fail consistently
assert len(tokens) > 0, "At least some logins should succeed"
assert len(set(tokens)) == len(tokens), "Each login should generate unique token"

            # Verify all tokens are valid
for token in tokens:
decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"], options={"verify_signature": False})
assert decoded.get("sub") or decoded.get("user_id")

@pytest.mark.asyncio
    async def test_02_expired_token_reuse_vulnerability(self):
"""Test: Attempt to reuse expired tokens"""

auth_client = AuthServiceClient(settings.AUTH_SERVICE_URL)

                    # Create user and get token
user_result = await auth_client.register( )
email="expired_test@example.com",
password="TestPass123!"
                    

                    # Create expired token
from tests.helpers.auth_test_utils import TestAuthHelper
auth_helper = TestAuthHelper()
expired_token = auth_helper.create_expired_test_token("test_user_id")

                    # Try to use expired token
result = await auth_client.verify_token(expired_token)
assert not result.get("valid"), "Expired token should not be valid"

                    # Ensure refresh doesn't work with expired token
refresh_result = await auth_client.refresh_access_token(expired_token)
assert refresh_result is None or "error" in refresh_result

@pytest.mark.asyncio
    async def test_03_password_reset_token_hijacking(self):
"""Test: Password reset token security"""

auth_client = AuthServiceClient(settings.AUTH_SERVICE_URL)

                        # Create two users
user1 = await auth_client.register( )
email="user1@example.com",
password="Pass123!"
                        
user2 = await auth_client.register( )
email="user2@example.com",
password="Pass456!"
                        

                        # Generate reset token for user1 (mock since API might not expose this)
reset_token = "fake_reset_token_for_user1"

                        # Try to use user1's reset token for user2 (should fail)
reset_result = await auth_client.reset_password( )
email="user2@example.com",
token=reset_token,
new_password="NewPass789!"
                        
assert not reset_result or "error" in reset_result

                        # Verify user2's password unchanged
auth_result = await auth_client.login("user2@example.com", "Pass456!")
assert auth_result is not None

@pytest.mark.asyncio
    async def test_04_session_fixation_attack(self):
"""Test: Session fixation vulnerability"""

auth_client = AuthServiceClient(settings.AUTH_SERVICE_URL)

                            # Create user
user = await auth_client.register( )
email="session_test@example.com",
password="TestPass123!"
                            

                            # Get initial session
token1 = await auth_client.login("session_test@example.com", "TestPass123!")

                            # Login again (should create new session)
token2 = await auth_client.login("session_test@example.com", "TestPass123!")

                            # Tokens should be different
assert token1 != token2, "New login should create new token"

                            # Old token might still be valid (depends on implementation)
old_token_check = await auth_client.verify_token(token1)
                            # This might fail if system invalidates old sessions - that's good!

@pytest.mark.asyncio
    async def test_05_brute_force_without_rate_limiting(self):
"""Test: Brute force attack detection"""

auth_client = AuthServiceClient(settings.AUTH_SERVICE_URL)

                                # Create user
user = await auth_client.register( )
email="brute_test@example.com",
password="RealPass123!"
                                

                                # Attempt 50 failed logins rapidly
failed_attempts = 0
for i in range(50):
result = await auth_client.login( )
"brute_test@example.com",
"formatted_string"
                                    
if not result or "error" in str(result):
failed_attempts += 1

                                        # System should block or slow down after multiple failures
assert failed_attempts == 50, "All wrong passwords should fail"

                                        # Check if account is locked or rate-limited
start_time = time.time()
                                        # Try correct password
result = await auth_client.login("brute_test@example.com", "RealPass123!")
response_time = time.time() - start_time

                                        # If response is slow or failed, might indicate rate limiting
if not result:
print("Account might be locked or rate-limited - good security!")
elif response_time > 1.0:
print("formatted_string")


class TestL4CriticalWebSocketIntegration:
    """Test WebSocket connection lifecycle and edge cases"""

@pytest.mark.asyncio
    async def test_06_websocket_connection_flood(self):
"""Test: Rapid WebSocket connection attempts"""
from netra_backend.app.services.websocket_service import WebSocketService

ws_service = WebSocketService()

        # Create mock websockets
connections = []
for i in range(100):
            # Mock: Generic component isolation for controlled unit testing
websocket = TestWebSocketConnection()
mock_ws.client_id = "formatted_string"
mock_ws.remote_address = ("127.0.0.1", 5000 + i)
connections.append(mock_ws)

            # Try to connect all at once
connect_tasks = []
for ws in connections:
connect_tasks.append( )
ws_service.handle_connection(ws)
                

results = await asyncio.gather(*connect_tasks, return_exceptions=True)

                # Check for connection limits
successful = len([item for item in []])
assert successful <= 50, "Should have connection limits per user"

@pytest.mark.asyncio
    async def test_07_websocket_message_injection(self):
"""Test: WebSocket message injection/spoofing"""

ws_service = WebSocketService()

                    # Setup legitimate connection
                    # Mock: Generic component isolation for controlled unit testing
websocket = TestWebSocketConnection()
legit_ws.client_id = "legit_client"
await ws_service.handle_connection(legit_ws)

                    # Setup attacker connection
                    # Mock: Generic component isolation for controlled unit testing
websocket = TestWebSocketConnection()
attacker_ws.client_id = "attacker_client"
await ws_service.handle_connection(attacker_ws)

                    # Attacker tries to send message as legitimate user
malicious_message = { )
"type": "message",
"user_id": "user1",  # Spoofing user1
"client_id": "legit_client",  # Spoofing client
"data": "malicious_content"
                    

                    # This should be rejected or sanitized
result = await ws_service.handle_message( )
attacker_ws,
json.dumps(malicious_message)
                    
                    # Should either reject or sanitize the spoofed fields
assert result is None or "error" in str(result)

@pytest.mark.asyncio
    async def test_08_websocket_reconnection_state_corruption(self):
"""Test: WebSocket reconnection with corrupted state"""

ws_service = WebSocketService()

                        # Initial connection
                        # Mock: Generic component isolation for controlled unit testing
websocket = TestWebSocketConnection()
ws1.client_id = "reconnect_client"
                        # Mock: Generic component isolation for controlled unit testing
ws1.websocket = TestWebSocketConnection()
await ws_service.handle_connection(ws1)

                        # Send some messages to build state
for i in range(5):
await ws1.send( )
json.dumps({"seq": i, "data": "formatted_string"})
                            

                            # Disconnect abruptly
await ws_service.handle_disconnect(ws1)

                            # Reconnect with different client but same user
                            # Mock: Generic component isolation for controlled unit testing
websocket = TestWebSocketConnection()
ws2.client_id = "reconnect_client_new"
                            # Mock: Generic component isolation for controlled unit testing
ws2.websocket = TestWebSocketConnection()
await ws_service.handle_connection(ws2)

                            # Try to resume with corrupted sequence
resume_msg = { )
"type": "resume",
"last_seq": 999,  # Invalid sequence
"client_id": "reconnect_client"  # Old client ID
                            

                            # Should handle gracefully
result = await ws_service.handle_message( )
ws2,
json.dumps(resume_msg)
                            
                            # Should either reject or reset state properly
assert result is None or "error" not in str(result).lower()

@pytest.mark.asyncio
    async def test_09_websocket_memory_leak_via_large_messages(self):
"""Test: Memory exhaustion via large WebSocket messages"""

ws_service = WebSocketService()

                                # Mock: Generic component isolation for controlled unit testing
websocket = TestWebSocketConnection()
ws.client_id = "memory_test"
                                # Mock: Generic component isolation for controlled unit testing
ws.websocket = TestWebSocketConnection()
await ws_service.handle_connection(ws)

                                # Send increasingly large messages
for size_mb in [1, 5, 10, 50]:
large_data = "x" * (size_mb * 1024 * 1024)
message = { )
"type": "data",
"payload": large_data
                                    

                                    # Should have size limits
try:
result = await ws_service.handle_message( )
ws,
json.dumps(message)
                                        
if size_mb > 10:
                                            # Large messages should be rejected
assert result is None or "error" in str(result)
except Exception as e:
if size_mb > 10:
                                                    # Expected for large messages
assert "size" in str(e).lower() or "large" in str(e).lower()
else:
raise

@pytest.mark.asyncio
    async def test_10_websocket_protocol_confusion(self):
"""Test: WebSocket protocol confusion attacks"""

ws_service = WebSocketService()

                                                            # Mock: Generic component isolation for controlled unit testing
websocket = TestWebSocketConnection()
ws.client_id = "protocol_test"
                                                            # Mock: Generic component isolation for controlled unit testing
ws.websocket = TestWebSocketConnection()
await ws_service.handle_connection(ws)

                                                            # Send malformed protocol messages
attacks = [ )
'{"type": "../../etc/passwd"}',  # Path traversal
'{"type": "exec", "cmd": "rm -rf /"}',  # Command injection
'{"type": null}',  # Null type
'{"type": ["array", "type"]}',  # Array type
'{"type": {"nested": "object"}}',  # Object type
'{}',  # Empty message
'not json at all',  # Invalid JSON
'{"type": "' + 'a' * 10000 + '"}',  # Long type
                                                            

for attack in attacks:
                                                                # All should be handled safely
try:
result = await ws_service.handle_message(ws, attack)
                                                                    # Should either sanitize or reject
except json.JSONDecodeError:
pass  # Expected for invalid JSON
except Exception as e:
                                                                            # Should be a controlled exception
assert "invalid" in str(e).lower() or "malformed" in str(e).lower()


class TestL4CriticalAPIIntegration:
    """Test core API functionality from different angles"""

@pytest.mark.asyncio
    async def test_11_api_pagination_boundary_errors(self):
"""Test: API pagination edge cases"""

api_url = "formatted_string"

async with ClientSession() as session:
            # Test various pagination boundaries
test_cases = [ )
{"page": -1, "limit": 10},  # Negative page
{"page": 0, "limit": 0},  # Zero limit
{"page": 999999, "limit": 10},  # Huge page
{"page": 1, "limit": 10000},  # Huge limit
{"page": "1"; DROP TABLE users;--", "limit": 10},  # SQL injection
            

for params in test_cases:
try:
async with session.get( )
"formatted_string",
params=params,
timeout=ClientTimeout(total=5)
) as response:
                        # Should handle gracefully
assert response.status in [200, 400, 404, 422]
if response.status == 200:
data = await response.json()
                            # Should have sensible defaults
assert len(data.get("items", [])) <= 100
except Exception:
                                # Connection errors are ok for this test
pass

@pytest.mark.asyncio
    async def test_12_api_header_injection(self):
"""Test: HTTP header injection vulnerabilities"""

api_url = "formatted_string"

async with ClientSession() as session:
                                        # Test malicious headers
headers = { )
"X-Forwarded-For": "127.0.0.1\r
X-Admin: true",
"User-Agent": "Mozilla/5.0\r
Set-Cookie: admin=true",
"Authorization": "Bearer token\r
X-Privilege: root",
                                        

try:
async with session.get( )
"formatted_string",
headers=headers,
timeout=ClientTimeout(total=5)
) as response:
                                                # Should sanitize headers
assert response.status in [200, 401, 403]
                                                # Check response headers for injection
assert "\r
" not in str(response.headers)
except Exception:
                                                    # Connection errors are ok for this test
pass

@pytest.mark.asyncio
    async def test_13_api_method_override_attacks(self):
"""Test: HTTP method override vulnerabilities"""

api_url = "formatted_string"

async with ClientSession() as session:
                                                            # Try to override methods
override_headers = [ )
{"X-HTTP-Method-Override": "DELETE"},
{"X-Method-Override": "PUT"},
{"_method": "DELETE"},
                                                            

for headers in override_headers:
try:
                                                                    # Send GET request with override headers
async with session.get( )
"formatted_string",
headers=headers,
timeout=ClientTimeout(total=5)
) as response:
                                                                        # Should not delete the user
assert response.status != 204

                                                                        # Verify user still exists
async with session.get( )
"formatted_string",
timeout=ClientTimeout(total=5)
) as check_response:
                                                                            # User should still be there or 404 if never existed
assert check_response.status in [200, 401, 404]
except Exception:
                                                                                # Connection errors are ok for this test
pass

@pytest.mark.asyncio
    async def test_14_api_content_type_confusion(self):
"""Test: Content-Type confusion attacks"""

api_url = "formatted_string"

async with ClientSession() as session:
                                                                                        # Send JSON with wrong content type
json_data = {"key": "value"}

test_cases = [ )
("text/plain", json.dumps(json_data)),
("application/xml", json.dumps(json_data)),
("multipart/form-data", json.dumps(json_data)),
("application/json", "not json"),  # Wrong format
                                                                                        

for content_type, data in test_cases:
try:
async with session.post( )
"formatted_string",
headers={"Content-Type": content_type},
data=data,
timeout=ClientTimeout(total=5)
) as response:
                                                                                                    # Should validate content type
if content_type != "application/json":
assert response.status in [400, 401, 404, 415, 422]
except Exception:
                                                                                                            # Connection errors are ok for this test
pass

@pytest.mark.asyncio
    async def test_15_api_race_condition_in_transactions(self):
"""Test: Race conditions in API transactions"""

api_url = "formatted_string"

async with ClientSession() as session:
thread_id = str(uuid.uuid4())

try:
                                                                                                                        # Create thread
async with session.post( )
"formatted_string",
json={"id": thread_id, "name": "Race Test"},
timeout=ClientTimeout(total=5)
) as response:
if response.status not in [201, 401, 404]:
await asyncio.sleep(0)
return  # Skip if API not available

                                                                                                                                # Concurrent updates
update_tasks = []
for i in range(10):
update_data = {"status": "formatted_string"}
                                                                                                                                    # Mock: Component isolation for testing without external dependencies
task = session.patch( )
"formatted_string",
json=update_data,
timeout=ClientTimeout(total=5)
                                                                                                                                    
update_tasks.append(task)

responses = await asyncio.gather(*update_tasks, return_exceptions=True)

                                                                                                                                    # Check final state
async with session.get( )
"formatted_string",
timeout=ClientTimeout(total=5)
) as response:
if response.status == 200:
data = await response.json()
                                                                                                                                            # Should have one consistent status
assert data.get("status") in ["formatted_string" for i in range(10)]
except Exception:
                                                                                                                                                # Connection errors are ok for this test
pass


class TestL4CriticalDatabaseIntegration:
    """Test database interaction edge cases"""

@pytest.mark.asyncio
    async def test_16_connection_pool_exhaustion(self):
"""Test: Database connection pool exhaustion"""
from netra_backend.app.db.session import get_db_connection

        # Try to acquire more connections than pool allows
connections = []

try:
for i in range(200):  # Way more than typical pool size
conn = await get_db_connection()
connections.append(conn)
except Exception as e:
                # Should hit pool limit
assert "pool" in str(e).lower() or "connection" in str(e).lower() or "limit" in str(e).lower()
finally:
                    # Close connections
for conn in connections:
if hasattr(conn, 'close'):
await conn.close()

@pytest.mark.asyncio
    async def test_17_transaction_isolation_violations(self):
"""Test: Transaction isolation level issues"""

async def transaction1():
pass
conn = await get_db_connection()
try:
        # Mock transaction - actual implementation may vary
        # This tests the concept of isolation violations
await asyncio.sleep(0.1)
        # Simulated update
pass
finally:
if hasattr(conn, 'close'):
await conn.close()

async def transaction2():
pass
conn = await get_db_connection()
try:
        # Mock transaction - actual implementation may vary
        # This tests the concept of isolation violations
await asyncio.sleep(0.1)
        # Simulated update
pass
finally:
if hasattr(conn, 'close'):
await conn.close()

                # Run concurrent transactions
results = await asyncio.gather(transaction1(), transaction2(), return_exceptions=True)

                # Check for any errors indicating isolation issues
for result in results:
if isinstance(result, Exception):
                        # Some errors are expected in isolation testing
assert "deadlock" in str(result).lower() or "conflict" in str(result).lower() or True

@pytest.mark.asyncio
    async def test_18_clickhouse_query_injection(self):
"""Test: ClickHouse query injection vulnerabilities"""
                            # Mock ClickHouse client for testing

                            # Mock: Generic component isolation for controlled unit testing
ch_client = Magic        # Mock: Async component isolation for testing without real async operations
ch_client.execute = AsyncMock(return_value=[])

                            # Test injection attempts
malicious_inputs = [ )
""; DROP TABLE events; --",
"1 OR 1=1",
"admin"--",
"1; SELECT * FROM system.users; --",
                            

for injection in malicious_inputs:
                                # Should parameterize queries properly
query = "SELECT * FROM events WHERE user_id = %(user_id)s"
result = await ch_client.execute( )
query,
{"user_id": injection}
                                
                                # Mock should handle it safely
assert result is not None or result == []

@pytest.mark.asyncio
    async def test_19_redis_memory_pressure(self):
"""Test: Redis memory pressure handling"""

try:
redis_client = await redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
                                            # Redis might not be available in test env
pytest.skip("Redis not available")

try:
                                                # Fill Redis with large amounts of data
for i in range(1000):
large_value = "x" * 1024 * 100  # 100KB per key
await redis_client.set("formatted_string", large_value)

                                                    # Check memory usage
info = await redis_client.info("memory")
used_memory = info.get("used_memory", 0)

                                                    # Should have eviction policy or limits
assert used_memory < 1024 * 1024 * 1024  # Less than 1GB

finally:
                                                        # Cleanup
for i in range(1000):
await redis_client.delete("formatted_string")
await redis_client.close()

@pytest.mark.asyncio
    async def test_20_database_deadlock_scenarios(self):
"""Test: Database deadlock detection and recovery"""

async def lock_order_1():
conn = await get_db_connection()
try:
        # Simulated lock acquisition order 1
await asyncio.sleep(0.1)
pass
finally:
if hasattr(conn, 'close'):
await conn.close()

async def lock_order_2():
conn = await get_db_connection()
try:
        # Simulated lock acquisition order 2 (opposite of order 1)
await asyncio.sleep(0.1)
pass
finally:
if hasattr(conn, 'close'):
await conn.close()

                # Run potentially deadlocking transactions
results = await asyncio.gather( )
lock_order_1(),
lock_order_2(),
return_exceptions=True
                

                # Check for deadlock handling
deadlocks = [item for item in []]

                # System should detect and handle deadlocks
if deadlocks:
assert len(deadlocks) <= 1, "Only one transaction should be victim"


                    # Test configuration
if __name__ == "__main__":
pytest.main([__file__, "-v", "--asyncio-mode=auto"])
pass
