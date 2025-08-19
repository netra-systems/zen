# Unified E2E Test Harness

## Business Value
**$500K+ MRR Protection** - Comprehensive E2E validation ensuring service integration reliability and preventing revenue-impacting failures.

## Overview
The Unified E2E Test Harness provides complete service orchestration for end-to-end testing of Auth, Backend, and Frontend services with real database integration and WebSocket connectivity.

## Architecture
- **300-line module limit** - Each component is focused and maintainable
- **Service isolation** - Database isolation and port management
- **Resource cleanup** - Automatic cleanup of services, connections, and test data
- **Health monitoring** - Comprehensive service health validation

## Components

### 1. UnifiedE2ETestHarness (Main Interface)
```python
from tests.unified.e2e import create_e2e_harness

async with create_e2e_harness().test_environment() as harness:
    user = await harness.create_test_user()
    result = await harness.simulate_user_journey(user)
```

### 2. E2EServiceOrchestrator 
- Manages service lifecycle (Auth, Backend, Frontend)
- Health check validation
- Port management and service URLs
- Database setup and migrations

### 3. UserJourneyExecutor
- Test user creation and authentication
- WebSocket connection management  
- User journey simulation
- Concurrent user testing

## Usage Examples

### Basic E2E Test
```python
import asyncio
from tests.unified.e2e import create_e2e_harness

async def test_user_flow():
    async with create_e2e_harness().test_environment() as harness:
        # Create test user
        user = await harness.create_test_user()
        
        # Test WebSocket connection
        ws = await harness.create_websocket_connection(user)
        
        # Simulate user journey
        result = await harness.simulate_user_journey(user)
        
        assert len(result['steps_completed']) > 0
        assert not result['errors']
```

### Concurrent User Testing
```python
async def test_concurrent_users():
    async with create_e2e_harness().test_environment() as harness:
        results = await harness.run_concurrent_user_test(user_count=5)
        successful = [r for r in results if not r.get('errors')]
        assert len(successful) == 5
```

### Service Health Monitoring
```python
async def test_service_health():
    harness = create_e2e_harness()
    await harness.start_test_environment()
    
    status = await harness.get_environment_status()
    assert harness.is_environment_ready()
    assert all(svc['ready'] for svc in status['services'].values())
    
    await harness.cleanup_test_environment()
```

## Service Configuration
- **Auth Service**: Port 8001, `/health` endpoint
- **Backend Service**: Port 8000, `/health` endpoint  
- **Frontend Service**: Port 3000, `/` endpoint
- **Test Database**: Isolated per test session
- **WebSocket**: `ws://localhost:8000/ws` with auth headers

## Resource Management
- **Automatic cleanup** on context manager exit
- **Database isolation** with unique test database names
- **Port availability** checking before service startup
- **Process termination** with graceful shutdown and timeout handling
- **Custom cleanup tasks** via `add_cleanup_task()`

## Demo
Run the demo to see the harness in action:
```bash
cd tests/unified/e2e
python demo_e2e_test.py
```

## Error Handling
- Service startup failures raise `RuntimeError`
- Health check timeouts with configurable limits
- WebSocket connection errors captured in journey results
- Resource cleanup continues even if individual steps fail

## Integration with Test Framework
The harness integrates with the existing test infrastructure:
- Uses `RealServicesManager` for service orchestration
- Leverages `DatabaseTestManager` for database operations
- Utilizes `RealWebSocketClient` for WebSocket testing
- Compatible with pytest and unittest frameworks