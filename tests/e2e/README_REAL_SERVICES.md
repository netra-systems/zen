# Real Services Manager

The Real Services Manager provides infrastructure for E2E testing with actual running services (no mocks).

## Features

- **Real Service Startup**: Starts Auth (port 8001), Backend (port 8000), and Frontend (port 3000)
- **Health Validation**: Waits for all services to be healthy before proceeding
- **Cross-Platform**: Handles Windows/Unix compatibility 
- **Clean Shutdown**: Proper cleanup on test completion
- **Health Monitoring**: Continuous monitoring of service health during tests

## Quick Usage

### Basic Usage
```python
from tests.real_services_manager import create_real_services_manager

# Create manager
manager = create_real_services_manager()

# Start all services
await manager.start_all_services()

# Check if ready
if manager.is_all_ready():
    print("All services running!")
    
# Get service URLs
urls = manager.get_service_urls()
print(f"Services: {urls}")

# Stop services
await manager.stop_all_services()
```

### Context Manager (Recommended)
```python
from tests.real_services_health import RealServicesContext

async with RealServicesContext() as manager:
    # Services are automatically started and monitored
    assert manager.is_all_ready()
    
    # Your E2E tests here
    urls = manager.get_service_urls()
    # Services automatically stopped when context exits
```

### Advanced Monitoring
```python
from tests.real_services_health import ServiceHealthMonitor

manager = create_real_services_manager()
monitor = ServiceHealthMonitor(manager)

await manager.start_all_services()
await monitor.start_monitoring()  # Continuous health checks

# Your tests...

await monitor.stop_monitoring()
await manager.stop_all_services()
```

## Service Configuration

| Service  | Port | Health Endpoint | Purpose |
|----------|------|----------------|---------|
| Auth     | 8001 | `/health`      | Authentication service |
| Backend  | 8000 | `/health`      | Main API backend |
| Frontend | 3000 | `/`            | Next.js frontend |

## Architecture Compliance

- **450-line limit**: Split into `real_services_manager.py` (291 lines) and `real_services_health.py` (87 lines)
- **25-line functions**: All functions ≤8 lines (MANDATORY compliance)
- **Modular design**: Separated concerns between core manager and health monitoring
- **Type safety**: Full type annotations with runtime safety

## Error Handling

- Port conflict detection
- Service startup timeouts (30s default)
- Graceful process termination (5s timeout before kill)
- Health check failures with retry logic
- Cross-platform subprocess handling

## Test Integration

```python
@pytest.mark.asyncio
@pytest.mark.slow  # Mark as slow test
async def test_full_e2e_flow():
    """Full E2E test with real services."""
    async with RealServicesContext() as manager:
        # All services are running and healthy
        
        # Test auth flow
        auth_url = f"{manager.get_service_urls()['auth']}/login"
        
        # Test backend API
        backend_url = f"{manager.get_service_urls()['backend']}/api/health"
        
        # Test frontend
        frontend_url = manager.get_service_urls()['frontend']
        
        # Your E2E test logic here
```

## Business Value Justification (BVJ)

**Segment**: Growth & Enterprise  
**Business Goal**: Reduce customer deployment failures and support tickets  
**Value Impact**: E2E testing with real services catches integration issues before production  
**Revenue Impact**: Reduces support costs and improves customer satisfaction, leading to higher retention