# 🔴 CRITICAL: Auth Testing Requirements

## MANDATORY: All Auth Tests Must Be Integration Tests

### The Golden Rule
**NEVER mock auth_client or the auth service. Always test against a real auth service instance.**

## Test Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        TEST SUITE                            │
│                                                              │
│  1. Starts test auth service on port 8001                   │
│  2. Configures auth_client to use test service              │
│  3. Runs tests with REAL HTTP calls                         │
│  4. Validates full auth flow                                │
└──────────────────────────────────────────────────────────────┘
                         │
                         │ Real HTTP Calls
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  TEST AUTH SERVICE                           │
│              (Real instance on port 8001)                    │
└──────────────────────────────────────────────────────────────┘
```

## Test Patterns

### ✅ CORRECT: Integration Test Pattern
```python
import pytest
from app.clients.auth_client import auth_client
from tests.helpers.auth_service_helper import start_test_auth_service

@pytest.mark.integration
class TestAuthIntegration:
    @classmethod
    async def setup_class(cls):
        """Start real auth service for tests."""
        cls.auth_service = await start_test_auth_service(port=8001)
        auth_client.settings.base_url = "http://localhost:8001"
    
    @classmethod
    async def teardown_class(cls):
        """Stop auth service."""
        await cls.auth_service.stop()
    
    async def test_token_validation(self):
        """Test real token validation through auth service."""
        # Create real token via auth service
        login_result = await auth_client.login("test@example.com", "password")
        token = login_result["access_token"]
        
        # Validate through real service
        validation = await auth_client.validate_token(token)
        assert validation["valid"] is True
        assert validation["user_id"] is not None
```

### ❌ WRONG: Mocked Test Pattern
```python
# NEVER DO THIS!
from unittest.mock import patch, MagicMock

@patch('app.clients.auth_client.auth_client')
def test_auth_mocked(mock_client):
    # This bypasses the real auth service!
    mock_client.validate_token.return_value = {"valid": True}
    # This test has no value!
```

## Test Categories

### 1. Auth Service Tests (`test_auth_service_*.py`)
- Tests the auth service ITSELF (not integration)
- Located in `app/tests/auth/`
- Can mock OAuth providers (Google, etc.)
- Cannot mock core auth logic

### 2. Integration Tests (`test_*_integration.py`)
- Tests main backend integration with auth service
- Must use real auth service instance
- Tests full flow: Backend → Auth Service → Backend
- Located throughout test directories

### 3. End-to-End Tests (`test_*_e2e.py`)
- Tests complete user flows
- Frontend → Backend → Auth Service
- Uses real services throughout

## Test Helpers

### Auth Service Test Helper
Create `tests/helpers/auth_service_helper.py`:
```python
import asyncio
import subprocess
from typing import Optional

class TestAuthService:
    def __init__(self, port: int = 8001):
        self.port = port
        self.process: Optional[subprocess.Popen] = None
    
    async def start(self):
        """Start auth service for testing."""
        self.process = subprocess.Popen(
            ["python", "app/auth/auth_service.py"],
            env={
                **os.environ,
                "AUTH_SERVICE_PORT": str(self.port),
                "AUTH_SERVICE_ENV": "test",
                "GOOGLE_CLIENT_ID": "test-client-id",
                "GOOGLE_CLIENT_SECRET": "test-secret",
                "JWT_SECRET_KEY": "test-jwt-secret"
            }
        )
        # Wait for service to be ready
        await self._wait_for_service()
    
    async def _wait_for_service(self, timeout: int = 10):
        """Wait for auth service to be ready."""
        import httpx
        start = time.time()
        while time.time() - start < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"http://localhost:{self.port}/health")
                    if response.status_code == 200:
                        return
            except:
                await asyncio.sleep(0.5)
        raise TimeoutError("Auth service failed to start")
    
    async def stop(self):
        """Stop auth service."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)

async def start_test_auth_service(port: int = 8001) -> TestAuthService:
    """Start test auth service."""
    service = TestAuthService(port)
    await service.start()
    return service
```

## Environment Variables for Tests

```env
# Test environment
AUTH_SERVICE_URL=http://localhost:8001
AUTH_SERVICE_ENABLED=true
AUTH_SERVICE_TEST_MODE=true

# Test credentials
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=test-password
TEST_ADMIN_EMAIL=admin@example.com
TEST_ADMIN_PASSWORD=admin-password
```

## Common Test Scenarios

### 1. User Login Flow
```python
async def test_user_login_flow():
    """Test complete login flow."""
    # 1. Login via auth service
    result = await auth_client.login("user@example.com", "password")
    assert result["access_token"]
    
    # 2. Validate token
    validation = await auth_client.validate_token(result["access_token"])
    assert validation["valid"]
    
    # 3. Use token in main backend
    headers = {"Authorization": f"Bearer {result['access_token']}"}
    response = await client.get("/api/protected", headers=headers)
    assert response.status_code == 200
```

### 2. OAuth Flow
```python
async def test_oauth_flow():
    """Test OAuth integration."""
    # 1. Initiate OAuth
    response = await client.get("/auth/login?provider=google")
    assert response.status_code == 302
    assert "accounts.google.com" in response.headers["location"]
    
    # 2. Simulate callback (with test code)
    callback_response = await client.get(
        "/auth/callback?code=test-code&state=test-state"
    )
    assert callback_response.status_code == 200
```

### 3. Token Refresh
```python
async def test_token_refresh():
    """Test token refresh flow."""
    # 1. Get initial tokens
    login = await auth_client.login("user@example.com", "password")
    
    # 2. Refresh token
    refreshed = await auth_client.refresh_token(login["refresh_token"])
    assert refreshed["access_token"] != login["access_token"]
```

## Regression Prevention

### Before Writing Auth Tests, Verify:
- [ ] You are NOT mocking auth_client
- [ ] You are starting a real auth service instance
- [ ] You are making real HTTP calls
- [ ] You are testing the complete flow
- [ ] You have proper setup/teardown for the auth service

### Red Flags in Tests:
- `@patch('app.clients.auth_client')`
- `Mock()` or `MagicMock()` for auth objects
- Hardcoded tokens or user IDs
- No auth service startup code
- Tests that pass without auth service running

## Test Execution

### Run Auth Integration Tests
```bash
# Run all auth integration tests
pytest app/tests/ -m integration --auth-service

# Run specific auth test
pytest app/tests/auth/test_auth_integration.py -v

# Run with real auth service
AUTH_SERVICE_TEST_MODE=true pytest app/tests/
```

## Final Warning
**Mocking the auth service defeats the entire purpose of having a separate auth service.**
**Always test against real instances to ensure security and correctness.**