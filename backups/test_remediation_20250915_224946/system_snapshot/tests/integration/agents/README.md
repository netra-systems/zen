# AgentRegistry Integration Tests

## Overview

This directory contains comprehensive integration tests for the AgentRegistry SSOT class (1,729 lines, MEGA CLASS candidate), focusing on:

- **User Isolation and Factory Patterns** - Enterprise customer isolation ($15K+ MRR protection)
- **Agent Registration and Management** - Complete agent lifecycle testing  
- **WebSocket Bridge Integration** - Real-time communication validation
- **Enterprise Multi-User Validation** - Multi-tenant security testing
- **Golden Path Agent Orchestration** - Business value protection ($500K+ ARR)
- **Memory and Resource Management** - Leak prevention and cleanup

## Business Critical Scenarios

### Enterprise Customer Protection ($15K+ MRR per customer)
- Per-user agent registry isolation validation
- Factory pattern memory leak prevention under load
- Shared state contamination detection
- User context boundary enforcement

### Golden Path Protection ($500K+ ARR)
- Complete agent orchestration flow per user
- Agent coordination with supervisor integration  
- WebSocket event delivery isolation
- Business value delivery validation

## Test Categories

### 1. User Isolation and Factory Pattern Tests
- `test_per_user_agent_registry_isolation_validation()` - Enterprise data protection
- `test_factory_pattern_memory_leak_prevention_under_load()` - System stability
- `test_shared_state_contamination_detection()` - Data security
- `test_user_context_boundary_enforcement()` - Access control

### 2. Agent Registration and Management Tests
- `test_agent_registration_with_user_context_isolation()` - Registration isolation
- `test_agent_retrieval_by_user_and_thread_isolation()` - Thread safety
- `test_agent_lifecycle_management_per_user()` - Complete lifecycle
- `test_concurrent_agent_registration_safety()` - Concurrency validation

### 3. WebSocket Bridge Integration Tests  
- `test_websocket_manager_association_with_user_context()` - Context integration
- `test_bridge_communication_validation_per_user()` - Communication testing
- `test_event_delivery_isolation_between_users()` - Event isolation
- `test_websocket_connection_lifecycle_management()` - Connection lifecycle

### 4. Enterprise Multi-User Validation
- `test_concurrent_user_operations_isolation()` - High concurrency testing
- `test_enterprise_customer_data_protection()` - Enterprise data security
- `test_multi_tenant_agent_execution_boundaries()` - Multi-tenant isolation
- `test_user_session_cleanup_and_isolation()` - Cleanup validation

### 5. Golden Path Agent Orchestration
- `test_complete_agent_orchestration_flow_per_user()` - End-to-end orchestration
- `test_agent_coordination_with_supervisor_integration()` - Supervisor integration

### 6. Memory and Resource Management
- `test_memory_usage_validation_during_concurrent_operations()` - Memory patterns
- `test_resource_cleanup_after_user_session_termination()` - Resource cleanup
- `test_long_running_session_resource_management()` - Long-running sessions

## Running the Tests

### Prerequisites
- All tests use **real components** (NO MOCKS) except for WebSocket and LLM infrastructure
- Tests require the SSOT framework and verified import paths
- Memory monitoring requires `psutil` package

### Basic Test Execution
```bash
# Run all AgentRegistry integration tests
pytest tests/integration/agents/test_agent_registry_integration.py -v

# Run specific test category
pytest tests/integration/agents/test_agent_registry_integration.py -k "user_isolation" -v

# Run Enterprise critical tests only
pytest tests/integration/agents/test_agent_registry_integration.py -m "enterprise_critical" -v

# Run Golden Path tests only  
pytest tests/integration/agents/test_agent_registry_integration.py -m "golden_path" -v

# Run memory management tests
pytest tests/integration/agents/test_agent_registry_integration.py -m "memory_management" -v
```

### Advanced Test Options
```bash
# Run with detailed memory reporting
pytest tests/integration/agents/test_agent_registry_integration.py -v -s --tb=long

# Run specific test with maximum verbosity
pytest tests/integration/agents/test_agent_registry_integration.py::TestAgentRegistryUserIsolationIntegration::test_per_user_agent_registry_isolation_validation -v -s

# Run tests with coverage reporting
pytest tests/integration/agents/test_agent_registry_integration.py --cov=netra_backend.app.agents.supervisor.agent_registry --cov-report=html
```

### Test Markers
- `@pytest.mark.agent_registry_integration` - All tests in this module
- `@pytest.mark.user_isolation` - User isolation specific tests
- `@pytest.mark.enterprise_critical` - Enterprise customer protection tests
- `@pytest.mark.golden_path` - Golden Path business validation tests
- `@pytest.mark.memory_management` - Memory and resource management tests

## Expected Test Outcomes

### Success Criteria
- **User Isolation**: 100% prevention of cross-user data contamination
- **Memory Management**: <50MB memory growth per test, >80% garbage collection
- **Enterprise Security**: Complete data protection validation for $15K+ MRR customers
- **Golden Path**: End-to-end orchestration flow validation protecting $500K+ ARR
- **Concurrency**: >95% success rate under concurrent load (15+ users, 8+ operations each)

### Performance Benchmarks
- **Memory per operation**: <1MB per agent operation
- **Concurrent users**: Support 25+ concurrent enterprise users
- **Cleanup effectiveness**: >80% resource cleanup validation
- **Event isolation**: 100% event delivery isolation between users

## Troubleshooting

### Common Issues

**Import Errors**
- Ensure all SSOT imports are available from `SSOT_IMPORT_REGISTRY.md`
- Check that `netra_backend` module is in Python path

**Memory Test Failures**  
- Memory tests may be sensitive to other running processes
- Run tests in isolation for accurate memory measurements
- Ensure garbage collection with `gc.collect()` in test setup

**WebSocket Test Issues**
- Mock WebSocket managers are used to avoid infrastructure dependencies
- Real WebSocket tests require actual WebSocket infrastructure

**Agent Creation Failures**
- Check that LLM manager mock is properly configured
- Ensure tool dispatcher factory is available
- Validate user context creation parameters

### Test Environment Requirements
- Python 3.8+ with asyncio support
- `psutil` for memory monitoring
- `pytest` with async support
- Access to SSOT test framework components

## Integration with CI/CD

These tests are designed to be run as part of the integration test suite:

```bash
# Include in unified test runner
python tests/unified_test_runner.py --category integration --include-path tests/integration/agents

# Run as part of Golden Path validation
python tests/unified_test_runner.py --golden-path-validation
```

## Business Value Validation

These tests directly validate:
- **$15K+ MRR Enterprise customers**: Data isolation and security
- **$500K+ ARR Golden Path**: Complete agent orchestration flows
- **System Stability**: Memory leak prevention and resource management
- **Multi-tenant Security**: Enterprise compliance and access control

Failure of these tests indicates potential:
- Data security vulnerabilities affecting Enterprise customers
- Memory leaks causing system instability
- Cross-user contamination risking compliance violations  
- Golden Path disruption affecting primary revenue streams

## Test Metrics and Reporting

Each test captures comprehensive metrics:
- Memory usage patterns and cleanup effectiveness
- Concurrency performance under enterprise load
- User isolation validation results
- Event delivery and WebSocket communication metrics
- Resource management and cleanup success rates

These metrics help validate the business-critical nature of the AgentRegistry SSOT implementation.