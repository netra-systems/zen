# Real Service Testing Implementation Plan

## Executive Summary
Transform our test infrastructure to use real services via dev_launcher, ensuring production-quality validation while maintaining fast development cycles.

## Phase 1: Core Infrastructure (Day 1-2)

### 1.1 Dev Launcher Pytest Integration
**File:** `tests/conftest.py`
```python
@pytest.fixture(scope="session")
async def dev_launcher():
    """Provides dev_launcher instance for real service testing."""
    launcher = DevLauncher(LauncherConfig(
        dynamic_ports=True,
        test_mode=True,
        startup_timeout=30
    ))
    yield launcher
    await launcher.shutdown()
```

### 1.2 Service Discovery Module
**File:** `dev_launcher/discovery.py`
```python
class ServiceDiscovery:
    def __init__(self, discovery_dir: Path = Path(".service_discovery")):
        self.discovery_dir = discovery_dir
    
    async def get_service_info(self, service: str) -> ServiceInfo:
        """Read service endpoint info from discovery files."""
        info_file = self.discovery_dir / f"{service}.json"
        data = json.loads(info_file.read_text())
        return ServiceInfo(
            port=data["port"],
            health_url=data["health_url"],
            base_url=f"http://localhost:{data['port']}"
        )
```

### 1.3 Test Client Factory
**File:** `tests/unified/clients/factory.py`
```python
class TestClientFactory:
    def __init__(self, discovery: ServiceDiscovery):
        self.discovery = discovery
        
    async def create_auth_client(self) -> AuthTestClient:
        info = await self.discovery.get_service_info("auth")
        return AuthTestClient(base_url=info.base_url)
    
    async def create_backend_client(self) -> BackendTestClient:
        info = await self.discovery.get_service_info("backend")
        return BackendTestClient(base_url=info.base_url)
    
    async def create_websocket_client(self, token: str) -> WebSocketTestClient:
        info = await self.discovery.get_service_info("backend")
        ws_url = f"ws://localhost:{info.port}/ws?token={token}"
        return WebSocketTestClient(url=ws_url)
```

## Phase 2: Refactor Existing Infrastructure (Day 3-4)

### 2.1 Update Real Services Manager
**File:** `tests/unified/real_services_manager.py`
```python
class RealServicesManager:
    def __init__(self, dev_launcher: DevLauncher):
        self.launcher = dev_launcher
        self.discovery = ServiceDiscovery()
        self.client_factory = TestClientFactory(self.discovery)
    
    async def start_all_services(self):
        # Use dev_launcher instead of manual subprocess
        success = await self.launcher.run()
        if not success:
            raise RuntimeError("Failed to start services via dev_launcher")
        
        # Wait for health checks
        await self.launcher.wait_for_healthy()
```

### 2.2 Update Test Fixtures
**File:** `tests/unified/conftest.py`
```python
@pytest.fixture(scope="session")
async def real_services(dev_launcher):
    """Provides real services with typed clients."""
    manager = RealServicesManager(dev_launcher)
    await manager.start_all_services()
    
    return RealServiceContext(
        auth_client=await manager.client_factory.create_auth_client(),
        backend_client=await manager.client_factory.create_backend_client(),
        websocket_factory=manager.client_factory.create_websocket_client
    )
```

## Phase 3: Migrate Critical Tests (Day 5-6)

### 3.1 WebSocket Integration Tests
```python
async def test_websocket_auth_flow(real_services):
    # Get auth token
    token = await real_services.auth_client.login("test@example.com", "password")
    
    # Connect WebSocket
    ws_client = await real_services.websocket_factory(token)
    await ws_client.connect()
    
    # Test real message flow
    await ws_client.send_chat("Hello")
    response = await ws_client.receive()
    assert response["type"] == "chat_response"
```

### 3.2 E2E User Journey Tests
```python
async def test_first_time_user_journey(real_services):
    # Register user
    user = await real_services.auth_client.register(
        email="new@example.com",
        password="secure123"
    )
    
    # Login and get token
    token = await real_services.auth_client.login(user.email, "secure123")
    
    # Connect WebSocket
    ws = await real_services.websocket_factory(token)
    await ws.connect()
    
    # Complete onboarding flow
    await ws.send({"type": "onboarding_start"})
    # ... continue journey
```

## Phase 4: Performance Optimization (Day 7)

### 4.1 Parallel Service Startup
```python
async def start_services_parallel(self):
    """Start all services concurrently for faster test startup."""
    tasks = [
        self._start_auth_service(),
        self._start_backend_service(),
        self._start_frontend_service()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check for failures
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            raise RuntimeError(f"Service {i} failed: {result}")
```

### 4.2 Service Caching
```python
class ServiceCache:
    """Cache running services between test sessions."""
    _instances: Dict[str, DevLauncher] = {}
    
    @classmethod
    async def get_or_create(cls, config: LauncherConfig) -> DevLauncher:
        key = config.cache_key()
        if key not in cls._instances:
            launcher = DevLauncher(config)
            await launcher.run()
            cls._instances[key] = launcher
        return cls._instances[key]
```

## Phase 5: CI/CD Integration (Day 8)

### 5.1 GitHub Actions Update
```yaml
- name: Run Real Service Tests
  env:
    USE_REAL_SERVICES: "true"
    DYNAMIC_PORTS: "true"
    TEST_ISOLATION: "1"
  run: |
    python test_runner.py --level integration --real-services
```

### 5.2 Test Report Generation
```python
class RealServiceTestReport:
    def generate(self):
        return {
            "services_started": self.services_started,
            "startup_time": self.startup_duration,
            "port_allocations": self.port_map,
            "health_check_results": self.health_checks,
            "test_results": self.results
        }
```

## Implementation Checklist

### Week 1 Tasks
- [ ] Create dev_launcher pytest fixture
- [ ] Build service discovery module
- [ ] Implement test client factory
- [ ] Refactor real_services_manager
- [ ] Update core test fixtures

### Week 2 Tasks
- [ ] Migrate WebSocket tests
- [ ] Migrate auth integration tests
- [ ] Migrate E2E user journeys
- [ ] Add performance optimizations
- [ ] Update CI/CD pipeline

### Success Metrics
- Test startup time < 10 seconds
- Zero flaky tests due to service issues
- 100% of integration tests using real services
- Parallel test execution enabled
- No hardcoded ports in test code

## Risk Mitigation

### Risk 1: Slow Test Startup
**Mitigation:** Implement parallel service startup and service caching

### Risk 2: Port Conflicts
**Mitigation:** Dynamic port allocation with fallback ranges

### Risk 3: Resource Leaks
**Mitigation:** Strict cleanup in fixtures with signal handling

### Risk 4: CI/CD Timeouts
**Mitigation:** Separate test levels with appropriate timeouts

## Rollback Plan
If issues arise:
1. Keep existing mock-based tests as fallback
2. Use feature flags to toggle real/mock services
3. Gradual migration with parallel test suites
4. Monitor test stability metrics before full cutover