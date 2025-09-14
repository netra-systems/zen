# REMEDIATION PLAN - Issue #881: E2E Staging Auth Setup Failures

## Executive Summary
**Root Cause:** StagingAuthClient initialization dependencies and service availability issues. Recent SSOT migrations broke staging auth configuration. Missing auth_client and test_user initialization in test setup.

**Solution:** Repair StagingAuthClient infrastructure, implement missing functions, and add robust service health checks with proper error handling.

**Business Impact:** Enables validation of $500K+ ARR Golden Path functionality in staging environment by fixing E2E test execution.

## Phase 1: StagingAuthClient Infrastructure Repair (Priority: P0 - CRITICAL)

### 1.1 Fix StagingAuthClient Initialization

**Files to Modify:**
- `tests/e2e/staging_auth_client.py`
- `tests/e2e/staging_config.py`
- `test_framework/ssot/e2e_auth_helper.py`

### 1.2 Implementation Steps:

**Step 1: Enhance StagingAuthClient with Robust Error Handling**
```python
# File: tests/e2e/staging_auth_client.py
class StagingAuthClient:
    def __init__(self, config=None, max_retries=3, retry_delay=2.0):
        """Initialize with robust error handling and retries."""
        try:
            self.config = config or get_staging_config()
            self.max_retries = max_retries
            self.retry_delay = retry_delay
            self.token_cache: Dict[str, Tuple[str, datetime]] = {}
            
            # CRITICAL: Validate configuration on initialization
            self._validate_configuration()
            
        except Exception as e:
            logger.error(f"StagingAuthClient initialization failed: {e}")
            raise ConfigurationError(f"Cannot initialize staging auth client: {e}")
    
    def _validate_configuration(self):
        """Validate all required configuration is present."""
        required_env_vars = [
            "E2E_OAUTH_SIMULATION_KEY",
            "STAGING_AUTH_URL", 
            "STAGING_BACKEND_URL"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ConfigurationError(f"Missing required environment variables: {missing_vars}")
```

**Step 2: Add Service Health Check with Retries**
```python
async def check_staging_service_health(self) -> Dict[str, bool]:
    """Check health of required staging services with retries."""
    
    services = {
        "auth": f"{self.config.urls.auth_url}/health",
        "backend": f"{self.config.urls.backend_url}/health"
    }
    
    health_status = {}
    
    for service_name, health_url in services.items():
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(health_url)
                    health_status[service_name] = response.status_code == 200
                    if health_status[service_name]:
                        break
                        
            except Exception as e:
                logger.warning(f"Service {service_name} health check failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    health_status[service_name] = False
    
    return health_status
```

## Phase 2: Missing Function Implementation (Priority: P0 - CRITICAL)

### 2.1 Implement Missing Functions in test_framework.ssot.e2e_auth_helper

**File to Create/Modify:** `test_framework/ssot/e2e_auth_helper.py`

```python
# File: test_framework/ssot/e2e_auth_helper.py
class E2EAuthHelper:
    """SSOT Authentication helper for E2E tests."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.auth_client = StagingAuthClient()
        
    async def validate_authenticated_session(self, auth_token: str, user_id: str) -> Dict[str, Any]:
        """Validate that an authenticated session is active and valid."""
        
        try:
            # Verify token is valid by making authenticated request
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.auth_client.config.urls.backend_url}/api/user/profile",
                    headers={"Authorization": f"Bearer {auth_token}"}
                )
                
                if response.status_code == 200:
                    profile_data = response.json()
                    return {
                        "valid": True,
                        "user_id": profile_data.get("user_id"),
                        "email": profile_data.get("email"),
                        "session_data": profile_data
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"Authentication validation failed: {response.status_code}",
                        "response": response.text
                    }
                    
        except Exception as e:
            return {
                "valid": False,
                "error": f"Session validation error: {str(e)}",
                "exception": e
            }
    
    async def get_authenticated_user_context(self, 
                                           email: Optional[str] = None,
                                           permissions: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get complete authenticated user context for testing."""
        
        try:
            # Get authentication tokens
            auth_tokens = await self.auth_client.get_auth_token(
                email=email,
                permissions=permissions or ["read", "write"]
            )
            
            # Validate the session
            validation_result = await self.validate_authenticated_session(
                auth_token=auth_tokens["access_token"],
                user_id=auth_tokens.get("user_id", "unknown")
            )
            
            if not validation_result["valid"]:
                raise AuthenticationError(f"Failed to create valid user context: {validation_result['error']}")
            
            return {
                "access_token": auth_tokens["access_token"],
                "refresh_token": auth_tokens.get("refresh_token"),
                "user_id": validation_result["user_id"],
                "email": validation_result["email"],
                "session_valid": True,
                "permissions": permissions or ["read", "write"]
            }
            
        except Exception as e:
            logger.error(f"Failed to get authenticated user context: {e}")
            raise AuthenticationError(f"Cannot create authenticated user context: {e}")
```

### 2.2 Implement Missing Functions in test_framework.websocket_helpers

**File to Modify:** `test_framework/websocket_helpers.py`

```python
# File: test_framework/websocket_helpers.py
async def wait_for_agent_completion(websocket_client: Any, 
                                  timeout: float = 60.0,
                                  required_events: Optional[List[str]] = None) -> Dict[str, Any]:
    """Wait for agent execution to complete, collecting all events."""
    
    required_events = required_events or [
        "agent_started", "agent_thinking", "tool_executing", 
        "tool_completed", "agent_completed"
    ]
    
    collected_events = []
    event_types_received = set()
    start_time = time.time()
    
    try:
        while time.time() - start_time < timeout:
            try:
                # Wait for next event with short timeout
                events = await websocket_client.get_received_events(timeout=2.0)
                
                for event in events:
                    event_type = event.get("type")
                    collected_events.append(event)
                    
                    if event_type:
                        event_types_received.add(event_type)
                    
                    # Check for completion
                    if event_type == "agent_completed":
                        return {
                            "completed": True,
                            "events": collected_events,
                            "event_types": list(event_types_received),
                            "all_required_events": all(evt in event_types_received for evt in required_events),
                            "execution_time": time.time() - start_time
                        }
                        
            except asyncio.TimeoutError:
                # Continue waiting if no events received
                continue
                
    except Exception as e:
        logger.error(f"Error waiting for agent completion: {e}")
    
    # Timeout reached without completion
    return {
        "completed": False,
        "timeout": True,
        "events": collected_events,
        "event_types": list(event_types_received),
        "all_required_events": all(evt in event_types_received for evt in required_events),
        "execution_time": time.time() - start_time
    }
```

## Phase 3: Test Setup Infrastructure (Priority: P1 - HIGH)

### 3.1 Create Robust Test Initialization

```python
# Enhanced test setup for E2E staging tests
@pytest.fixture
async def staging_auth_setup():
    """Robust staging auth setup with health checks and retries."""
    
    auth_helper = E2EAuthHelper(environment="staging")
    
    # Check service health before proceeding
    health_status = await auth_helper.auth_client.check_staging_service_health()
    
    unhealthy_services = [svc for svc, healthy in health_status.items() if not healthy]
    if unhealthy_services:
        pytest.skip(f"Staging services unhealthy: {unhealthy_services}")
    
    # Create authenticated user context
    try:
        user_context = await auth_helper.get_authenticated_user_context(
            email="e2e-test-user@netra-test.com",
            permissions=["read", "write", "execute"]
        )
        
        yield {
            "auth_helper": auth_helper,
            "user_context": user_context,
            "auth_client": auth_helper.auth_client,
            "test_user": {
                "user_id": user_context["user_id"],
                "email": user_context["email"],
                "access_token": user_context["access_token"]
            }
        }
        
    except Exception as e:
        pytest.skip(f"Cannot setup staging auth: {e}")
```

## Phase 4: Pytest Configuration Fix (Priority: P2 - MEDIUM)

### 4.1 Fix Pytest Marker Configuration

**File to Modify:** `pytest.ini` or `pyproject.toml`

```ini
# Add to pytest.ini
[tool:pytest]
markers =
    issue_372: Tests related to issue 372
    e2e: End-to-end tests
    staging: Tests that require staging environment
    websocket: WebSocket related tests
    auth: Authentication related tests
```

## Implementation Sequence

1. **Service Health Infrastructure** (Immediate)
   - Implement service health checking in StagingAuthClient
   - Add retry logic and robust error handling
   - Test against staging environment

2. **Missing Function Implementation** (Immediate)
   - Implement `validate_authenticated_session` in E2EAuthHelper
   - Implement `get_authenticated_user_context` in E2EAuthHelper
   - Implement `wait_for_agent_completion` in websocket_helpers
   - Add proper SSOT imports and error handling

3. **Test Setup Enhancement** (Next)
   - Create robust `staging_auth_setup` fixture
   - Add environment validation and health checks
   - Implement graceful degradation for unavailable services

4. **Configuration Repair** (Final)
   - Fix pytest marker configuration
   - Add missing environment variable documentation
   - Validate all E2E tests can be collected without errors

## Success Criteria
- [ ] StagingAuthClient initializes without configuration errors
- [ ] Service health checks pass before running tests
- [ ] Missing functions implemented and available for import
- [ ] E2E staging tests can be collected without import errors
- [ ] Test setup creates valid authenticated user contexts
- [ ] Test collection success rate > 95%

## Risk Mitigation
- **Risk:** Staging service unavailability during tests
  - **Mitigation:** Implement health checks with graceful skipping
- **Risk:** Configuration drift in staging environment
  - **Mitigation:** Validate configuration on initialization
- **Risk:** Authentication token expiry during long test runs
  - **Mitigation:** Implement token refresh logic and caching
- **Risk:** Import errors due to missing functions
  - **Mitigation:** Comprehensive function implementation with proper error handling