# ResourceManagementAgent

Comprehensive service dependencies and resource allocation management for the Netra Apex test orchestration system.

## Overview

The ResourceManagementAgent is a critical component that handles:

- **Service Dependencies**: PostgreSQL, Redis, ClickHouse, Backend, Auth, Frontend
- **Resource Allocation**: CPU, memory, network, disk resources across test layers
- **Conflict Management**: Prevents resource conflicts between test categories and layers
- **Service Availability**: Ensures service availability before test execution
- **Resource Cleanup**: Automatic resource cleanup and recovery mechanisms

## Key Features

### Service Management

```python
from test_framework.orchestration import ResourceManagementAgent, create_resource_manager

# Create resource manager
rm = create_resource_manager(enable_monitoring=True)

# Check service availability for a test layer
available, missing = rm.ensure_layer_services("core_integration")
if not available:
    print(f"Missing services: {missing}")
```

### Resource Allocation

```python
from test_framework.layer_system import ResourceRequirements

# Define resource requirements
requirements = ResourceRequirements(
    requires_postgresql=True,
    requires_redis=True,
    min_memory_mb=512,
    dedicated_resources=False
)

# Allocate resources
allocation_id = rm.allocate_resources(
    layer_name="service_integration",
    category_name="api_tests",
    requirements=requirements,
    duration_minutes=30
)

# Use resources for test execution
# ... run tests ...

# Release resources
success = rm.release_resources(allocation_id)
```

### Resource Monitoring

```python
# Get real-time resource status
resource_status = rm.get_resource_status()
print(f"Active allocations: {resource_status['total_allocations']}")

# Get service health status  
service_status = rm.get_service_status()
print(f"Healthy services: {service_status['healthy_services']}")

# Check for resource conflicts
conflicts = rm.resolve_resource_conflicts()
if conflicts:
    print(f"Resource conflicts detected: {conflicts}")
```

## Service Dependency Graph

The ResourceManagementAgent understands service startup dependencies:

```
Layer Dependencies:
fast_feedback: None (unit tests, minimal resources)
core_integration: PostgreSQL, Redis (database tests need DB)
service_integration: PostgreSQL, Redis, Backend, Auth (API tests need services)
e2e_background: PostgreSQL, Redis, Backend, Auth, Frontend (full stack)

Service Startup Order:
1. PostgreSQL, Redis, ClickHouse (no dependencies)
2. Auth Service (needs PostgreSQL, Redis)
3. Backend Service (needs PostgreSQL, Redis, Auth)
4. Frontend Service (needs Backend, Auth)
5. WebSocket Service (needs Backend, Redis)
```

## Resource Pools

Each test layer has dedicated resource pools:

| Layer | Memory | CPU | Parallel Instances |
|-------|--------|-----|-------------------|
| fast_feedback | 512MB | 50% | 8 |
| core_integration | 1024MB | 70% | 6 |
| service_integration | 2048MB | 80% | 4 |
| e2e_background | 4096MB | 90% | 2 |

## Usage Patterns

### Basic Usage

```python
# Context manager (recommended)
with create_resource_manager() as rm:
    # Check layer resources
    available, missing = rm.ensure_layer_services("core_integration")
    
    if available:
        # Allocate resources
        allocation_id = rm.allocate_resources(
            layer_name="core_integration",
            category_name="database_tests",
            requirements=ResourceRequirements(min_memory_mb=256),
            duration_minutes=15
        )
        
        # Run tests...
        
        # Resources automatically released on context exit
```

### Integration with Test Layers

```python
from test_framework.orchestration import ensure_layer_resources_available

# Ensure all resources are available before layer execution
success = ensure_layer_resources_available(rm, "service_integration", timeout_seconds=120)
if not success:
    raise RuntimeError("Layer resources not available")
```

### CLI Usage

```bash
# Check resource status
python test_framework/orchestration/resource_management_agent.py --status

# Check resources for specific layer
python test_framework/orchestration/resource_management_agent.py --layer fast_feedback

# Continuous monitoring
python test_framework/orchestration/resource_management_agent.py --monitor
```

## Resource Conflict Management

The agent prevents and resolves resource conflicts:

- **Memory Conflicts**: Prevents OOM with smart memory allocation
- **CPU Conflicts**: Balances CPU usage across parallel categories
- **Service Conflicts**: Ensures services don't interfere between layers
- **Instance Conflicts**: Manages parallel test execution limits

## Error Handling

Comprehensive error handling with actionable remediation:

```python
try:
    rm.ensure_layer_services("service_integration")
except ServiceUnavailableError as e:
    print(f"Service error: {e.service_name}")
    print(f"Details: {e.details}")
    for step in e.remediation_steps:
        print(f"- {step}")
```

## Integration Points

- **LayerExecutionAgent**: Coordinates resource requirements for layer execution
- **BackgroundE2EAgent**: Provides dedicated resource pools for background execution
- **ProgressStreamingAgent**: Reports resource metrics and service status
- **TestOrchestratorAgent**: Uses resource availability for execution planning

## Best Practices

1. **Always use context manager** for automatic cleanup
2. **Check service availability** before test execution
3. **Monitor resource utilization** during long-running tests
4. **Release resources promptly** after test completion
5. **Handle service failures gracefully** with fallback strategies
6. **Use appropriate resource pools** for different test types

## Configuration

Environment variables for service configuration:

```bash
# Database services
DATABASE_URL=postgresql://user:pass@localhost:5432/netra_dev
REDIS_URL=redis://localhost:6379

# Service endpoints
BACKEND_URL=http://localhost:8000
AUTH_SERVICE_URL=http://localhost:8081
FRONTEND_URL=http://localhost:3000

# Resource limits (optional)
MAX_MEMORY_ALLOCATION_MB=8192
MAX_CPU_ALLOCATION_PERCENT=90
MAX_PARALLEL_INSTANCES=10
```

## Monitoring and Observability

The ResourceManagementAgent provides comprehensive monitoring:

- **Real-time metrics**: CPU, memory, disk I/O, network I/O
- **Service health**: Continuous health checks for all services
- **Resource utilization**: Per-layer resource pool utilization
- **Allocation tracking**: Active resource allocations and expirations
- **Conflict detection**: Automatic detection and reporting of resource conflicts

## Architecture Integration

The ResourceManagementAgent integrates seamlessly with:

- **IsolatedEnvironment**: All environment access goes through unified environment management
- **ServiceAvailabilityChecker**: Real service connectivity testing
- **DockerPortDiscovery**: Dynamic Docker service discovery
- **LayerSystem**: Layer-specific resource requirements and limits
- **CategorySystem**: Category-specific resource allocation patterns

This ensures consistent, reliable resource management across the entire test orchestration system.