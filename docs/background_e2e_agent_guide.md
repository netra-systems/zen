# Background E2E Agent - Non-blocking E2E Test Execution

The BackgroundE2EAgent is a comprehensive solution for executing long-running End-to-End tests without blocking development workflows. It provides queue management, background process execution, result persistence, and real-time monitoring for E2E test categories.

## 🎯 Core Purpose

**Problem Solved**: E2E tests (Cypress, performance, full user journeys) can take 20-45 minutes to complete, blocking fast feedback loops and development velocity.

**Solution**: Execute these resource-intensive tests in background processes with intelligent queue management, allowing developers to continue working while tests run asynchronously.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    BACKGROUND E2E AGENT                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │   Task Queue    │  │ Process Manager  │  │ Results Manager │ │
│  │   • Priority    │  │ • Lifecycle      │  │ • Persistence   │ │
│  │   • FIFO        │  │ • Monitoring     │  │ • Retrieval     │ │
│  │   • Scheduling  │  │ • Resource Limits│  │ • History       │ │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘ │
│           │                      │                      │       │
│           └──────────────────────┼──────────────────────┘       │
│                                  │                              │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              BACKGROUND PROCESSES                           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │ │
│  │  │   Cypress   │  │     E2E     │  │ Performance │  ...  │ │
│  │  │ (20+ min)   │  │ (30+ min)   │  │ (30+ min)   │       │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                 CLI INTEGRATION                             │ │
│  │    unified_test_runner.py --background-e2e                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 E2E Test Categories

The BackgroundE2EAgent handles four categories of E2E tests:

| Category | Duration | Description | Priority |
|----------|----------|-------------|----------|
| **cypress** | 20+ min | Cypress E2E tests with full service integration | Medium |
| **e2e** | 30+ min | Full end-to-end user journey tests | Medium |  
| **performance** | 30+ min | Load and performance tests | Low |
| **e2e_critical** | 5 min | Critical E2E tests (can also run in foreground) | High |

## 🚀 Quick Start

### 1. Basic Usage via CLI

```bash
# Queue E2E tests for background execution
python unified_test_runner.py --background-e2e --background-category cypress

# Check queue status
python unified_test_runner.py --background-status

# View recent results
python unified_test_runner.py --background-results 5

# Cancel a specific task
python unified_test_runner.py --kill-background TASK_ID
```

### 2. Programmatic Usage

```python
from test_framework.orchestration.background_e2e_agent import (
    BackgroundE2EAgent, E2ETestCategory, BackgroundTaskConfig
)

# Initialize agent
agent = BackgroundE2EAgent(project_root=Path("/path/to/project"))
agent.start()

try:
    # Queue a Cypress test
    task_id = agent.queue_e2e_test(E2ETestCategory.CYPRESS)
    print(f"Queued Cypress test: {task_id}")
    
    # Check status
    status = agent.get_task_status(task_id)
    print(f"Task status: {status['status']}")
    
    # Get queue overview
    queue_status = agent.get_queue_status()
    print(f"Queued: {queue_status['queued_tasks']}")
    
finally:
    agent.stop()
```

### 3. Context Manager Usage

```python
with BackgroundE2EAgent(project_root) as agent:
    task_id = agent.queue_e2e_test(E2ETestCategory.E2E)
    # Agent automatically starts and stops
```

## ⚙️ Advanced Configuration

### Custom Task Configuration

```python
config = BackgroundTaskConfig(
    category=E2ETestCategory.PERFORMANCE,
    environment="staging",
    timeout_minutes=45,
    max_retries=2,
    priority=1,  # Higher priority (lower number = higher priority)
    
    # Resource limits
    cpu_limit_percent=50,
    memory_limit_gb=4,
    
    # Service dependencies
    services_required={"postgres", "redis", "clickhouse", "backend"},
    
    # Additional execution options
    additional_args=["--stress-test", "--verbose"],
    env_vars={
        "PERF_MODE": "staging",
        "MAX_CONNECTIONS": "100"
    }
)

task_id = agent.queue_e2e_test(E2ETestCategory.PERFORMANCE, config)
```

### Environment-Specific Configuration

```python
# Development environment
dev_config = BackgroundTaskConfig(
    environment="development",
    use_real_services=False,  # Use Docker services
    use_real_llm=True,
    timeout_minutes=15
)

# Staging environment  
staging_config = BackgroundTaskConfig(
    environment="staging",
    use_real_services=True,   # Use deployed services
    use_real_llm=True,
    timeout_minutes=30,
    max_retries=3
)
```

## 📊 Monitoring and Status

### Queue Status

```python
status = agent.get_queue_status()
# Returns:
{
    "agent_running": True,
    "queued_tasks": 3,
    "active_tasks": 1,
    "queued_by_category": {
        "cypress": 2,
        "e2e": 1
    },
    "active_task_ids": ["task_123"]
}
```

### Task Status

```python
task_status = agent.get_task_status(task_id)
# Returns:
{
    "task_id": "task_123",
    "category": "cypress", 
    "status": "running",
    "created_at": "2024-01-15T10:30:00",
    "process_info": {
        "pid": 12345,
        "running": True,
        "duration_seconds": 120.5,
        "resource_usage": {
            "cpu_percent": 25.3,
            "memory_mb": 512.1
        }
    }
}
```

### Recent Results

```python
results = agent.get_recent_results(limit=10)
# Returns list of:
{
    "task_id": "task_123",
    "category": "cypress",
    "status": "completed",
    "exit_code": 0,
    "duration_seconds": 1205.7,
    "test_counts": {
        "total": 25,
        "passed": 23,
        "failed": 2,
        "skipped": 0
    },
    "error_message": None
}
```

## 🔧 Integration Points

### Unified Test Runner Integration

The BackgroundE2EAgent integrates seamlessly with `unified_test_runner.py`:

```bash
# All these commands now support background execution
python unified_test_runner.py --background-e2e --background-category cypress
python unified_test_runner.py --background-e2e --background-category e2e --background-timeout 45
python unified_test_runner.py --background-e2e --background-category performance --env staging
```

### Orchestrator Integration

When used with the TestOrchestratorAgent:

```python
# Agent communication protocol support
agent.enable_communication(communication_protocol)

# Handle messages from orchestrator
await agent.handle_message(message)
```

### Service Coordination

Automatic service availability checking:

```python
# Agent ensures required services are available before execution
config = BackgroundTaskConfig(
    services_required={"postgres", "redis", "backend", "frontend"}
)
# Agent will check each service before starting the test
```

## 🏃‍♂️ Execution Flow

### 1. Task Queuing
```
Developer/CI → Queue E2E Test → Priority Queue → Background Execution
```

### 2. Background Processing
```
Worker Thread → Dequeue Task → Check Services → Start Process → Monitor
```

### 3. Result Handling
```
Process Complete → Parse Results → Store Persistently → Notify → Cleanup
```

## 📁 File Structure

```
test_framework/orchestration/
├── background_e2e_agent.py          # Main agent implementation
├── test_background_e2e_agent.py     # Comprehensive test suite
└── __init__.py

test_reports/background_e2e/          # Persistent result storage
├── task_123.json
├── task_456.json
└── ...

examples/
└── background_e2e_demo.py           # Interactive demonstration

docs/
└── background_e2e_agent_guide.md    # This documentation
```

## 🎮 CLI Commands Reference

### Queue Management
```bash
# Queue specific E2E category
python unified_test_runner.py --background-e2e --background-category cypress
python unified_test_runner.py --background-e2e --background-category e2e  
python unified_test_runner.py --background-e2e --background-category performance
python unified_test_runner.py --background-e2e --background-category e2e_critical

# Set custom timeout
python unified_test_runner.py --background-e2e --background-timeout 45
```

### Status and Monitoring
```bash
# Show queue status
python unified_test_runner.py --background-status

# Show recent results
python unified_test_runner.py --background-results 10

# Show results for specific time period
python unified_test_runner.py --background-results 20
```

### Task Management
```bash
# Cancel specific task
python unified_test_runner.py --kill-background abc123def456

# Cancel all background tasks (stop agent)
# This is handled automatically when the agent shuts down
```

## 🔄 Task Lifecycle

### Task States
- **QUEUED**: Task waiting in queue for execution
- **STARTING**: Task being prepared for execution
- **RUNNING**: Task actively executing in background process
- **COMPLETED**: Task finished successfully
- **FAILED**: Task failed during execution
- **CANCELLED**: Task was manually cancelled
- **TIMEOUT**: Task exceeded timeout limit

### State Transitions
```
QUEUED → STARTING → RUNNING → {COMPLETED, FAILED, TIMEOUT}
   ↓
CANCELLED (can happen from QUEUED or RUNNING)
```

## 🛡️ Error Handling and Recovery

### Graceful Failure Recovery
- **Service Unavailable**: Task fails early with clear error message
- **Timeout**: Process is terminated cleanly, resources freed
- **Crash**: Process cleanup, error logged, queue continues
- **System Shutdown**: All processes terminated gracefully

### Resource Management
```python
# Automatic resource limits
config = BackgroundTaskConfig(
    cpu_limit_percent=50,    # Limit to 50% CPU
    memory_limit_gb=4        # Limit to 4GB RAM
)

# Process isolation prevents interference with development
```

### Retry Logic
```python
config = BackgroundTaskConfig(
    max_retries=3,          # Retry failed tests up to 3 times
    timeout_minutes=30      # Per-attempt timeout
)
```

## 📈 Performance Benefits

### Development Velocity
- **Non-blocking Execution**: Continue development while E2E tests run
- **Fast Feedback**: Get unit/integration results immediately
- **Parallel Processing**: Multiple E2E tests can run concurrently

### Resource Efficiency
- **Queue Management**: Prevents resource overload
- **Priority Scheduling**: Critical tests run first
- **Resource Limits**: Prevents system slowdown

### Reliability
- **Persistent Results**: Test results survive system restarts
- **Automatic Retry**: Failed tests retry automatically
- **Clean Shutdown**: Graceful handling of interruptions

## 🧪 Testing

### Run Agent Tests
```bash
# Run comprehensive test suite
python -m pytest test_framework/orchestration/test_background_e2e_agent.py -v

# Run specific test categories
python -m pytest test_framework/orchestration/test_background_e2e_agent.py::TestBackgroundE2EAgent -v
python -m pytest test_framework/orchestration/test_background_e2e_agent.py::TestBackgroundE2ECLIIntegration -v
```

### Demo Script
```bash
# Interactive demonstration
python examples/background_e2e_demo.py
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Agent Won't Start
```bash
# Check if agent is already running
python unified_test_runner.py --background-status

# Kill any hanging processes
pkill -f "background_e2e"
```

#### 2. Services Not Available
```bash
# Start required services
docker-compose -f docker-compose.test.yml up -d postgres redis

# Check service status
python scripts/check_services.py
```

#### 3. Tasks Stuck in Queue
```bash
# Check queue status
python unified_test_runner.py --background-status

# Restart agent if needed
python unified_test_runner.py --kill-background ALL  # If implemented
```

#### 4. High Resource Usage
```python
# Use resource limits in config
config = BackgroundTaskConfig(
    cpu_limit_percent=25,     # Lower CPU limit
    memory_limit_gb=2         # Lower memory limit
)
```

### Debug Mode
```bash
# Enable debug logging
PYTHONPATH=. LOGLEVEL=DEBUG python unified_test_runner.py --background-e2e
```

## 🔗 Related Components

### Integration with Existing System
- **unified_test_runner.py**: Main CLI integration point
- **test_orchestrator_agent.py**: Higher-level orchestration
- **cypress_runner.py**: Cypress-specific execution
- **service_availability.py**: Service dependency management

### Configuration Files
- **test_framework/config/categories.yaml**: E2E category definitions
- **test_framework/config/test_layers.yaml**: Layer system integration

## 📚 Best Practices

### When to Use Background E2E
- **Long-running tests**: Tests taking >10 minutes
- **Resource-intensive tests**: Performance, load, stress tests
- **Non-blocking workflows**: When you need to continue development
- **CI/CD pipelines**: Parallel execution with other tasks

### Queue Management
- **Use priorities**: Critical tests get priority=1, others priority=2-5
- **Resource planning**: Don't queue too many resource-intensive tests
- **Monitor capacity**: Check active tasks before queuing more

### Development Workflow
```bash
# Typical development workflow
git commit -m "Feature implementation"
python unified_test_runner.py --category unit integration  # Fast feedback
python unified_test_runner.py --background-e2e --background-category cypress  # Queue E2E
# Continue development while E2E runs in background
python unified_test_runner.py --background-status  # Check progress
```

## 🎯 Business Value

### For Developers
- **Faster feedback loops**: Don't wait for E2E tests
- **Continuous development**: Work while tests run
- **Better focus**: Less context switching

### For Teams
- **Improved velocity**: Parallel development and testing
- **Resource efficiency**: Optimal use of compute resources
- **Quality assurance**: E2E tests still run, just non-blocking

### For CI/CD
- **Pipeline optimization**: Run E2E tests in parallel with other stages
- **Cost efficiency**: Better resource utilization
- **Faster deployments**: Reduced wait times

---

## 📋 Summary

The BackgroundE2EAgent transforms E2E testing from a blocking, sequential process into a non-blocking, parallel execution system. It provides:

✅ **Queue management** with priority scheduling  
✅ **Background process execution** with resource limits  
✅ **Persistent result storage** and retrieval  
✅ **Real-time status monitoring** and progress tracking  
✅ **CLI integration** with unified test runner  
✅ **Service coordination** and dependency management  
✅ **Graceful error handling** and automatic retry  
✅ **Resource management** to prevent system overload  

This enables developers to maintain fast feedback loops while ensuring comprehensive E2E test coverage executes in parallel, significantly improving development velocity and team productivity.