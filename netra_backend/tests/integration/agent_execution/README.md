# Agent Execution Integration Tests

This directory contains comprehensive integration tests for agent execution patterns, tool dispatch integration, and WebSocket event delivery focused on validating real business value delivery without external dependencies.

## 🎯 Business Value Focus

These tests ensure that the core agent execution patterns deliver measurable business value through:

- **Real Agent Orchestration**: Tests actual SupervisorAgent routing and coordination logic
- **Tool Dispatcher Integration**: Validates tools execute and deliver business outcomes  
- **Agent Communication**: Ensures proper handoffs and context sharing between agents
- **WebSocket Events**: Confirms all 5 critical events are delivered for user experience
- **Performance & Reliability**: Validates system operates under load with consistent quality

## 🏗️ Test Architecture

### Core Principles

1. **NO MOCKS for Internal Logic**: Tests use real agent execution patterns, not mocks
2. **Real UserExecutionContext**: All tests use authentic user context isolation
3. **Business Value Validation**: Every test validates actual business outcomes
4. **External Dependencies Only**: Only external APIs/services are mocked (LLM, WebSocket infrastructure)
5. **Performance Focused**: Tests measure real execution timing and resource usage

### Test Categories

```
agent_execution/
├── base_agent_execution_test.py        # Base test framework with WebSocket validation
├── test_supervisor_orchestration_patterns.py    # SupervisorAgent orchestration (5 tests)
├── test_tool_dispatcher_integration.py          # Tool execution & business scenarios (5 tests)  
├── test_agent_communication_handoffs.py         # Agent handoffs & coordination (5 tests)
├── test_websocket_agent_events.py              # WebSocket event delivery (5 tests)
├── test_agent_performance_reliability.py        # Performance & load testing (5 tests)
├── test_runner_validation.py                    # Test authenticity validation
└── README.md                                     # This documentation
```

## 🚀 Running the Tests

### Individual Test Categories

```bash
# SupervisorAgent orchestration patterns
python -m pytest netra_backend/tests/integration/agent_execution/test_supervisor_orchestration_patterns.py -v

# Tool dispatcher integration
python -m pytest netra_backend/tests/integration/agent_execution/test_tool_dispatcher_integration.py -v

# Agent communication and handoffs
python -m pytest netra_backend/tests/integration/agent_execution/test_agent_communication_handoffs.py -v

# WebSocket event delivery (all 5 critical events)
python -m pytest netra_backend/tests/integration/agent_execution/test_websocket_agent_events.py -v

# Performance and reliability under load
python -m pytest netra_backend/tests/integration/agent_execution/test_agent_performance_reliability.py -v
```

### Full Test Suite

```bash
# Run all agent execution integration tests
python -m pytest netra_backend/tests/integration/agent_execution/ -v

# Run with coverage and performance metrics  
python -m pytest netra_backend/tests/integration/agent_execution/ -v --durations=10

# Run validation to ensure tests use real patterns
python netra_backend/tests/integration/agent_execution/test_runner_validation.py
```

### Integration with Unified Test Runner

```bash
# Run through unified test runner (recommended)
python tests/unified_test_runner.py --category integration --pattern agent_execution
```

## 📊 Test Coverage Matrix

| Category | Tests | Focus Areas | Business Value |
|----------|-------|-------------|----------------|
| **SupervisorAgent Orchestration** | 5 | Agent routing, sub-agent coordination, error handling | Ensures comprehensive AI workflow orchestration |
| **Tool Dispatcher Integration** | 5 | Tool execution, business scenarios, performance | Validates tools deliver measurable business outcomes |
| **Agent Communication** | 5 | Handoffs, context sharing, multi-agent workflows | Ensures seamless agent-to-agent collaboration |  
| **WebSocket Events** | 5 | All 5 critical events, timing, isolation, recovery | Enables real-time user experience and transparency |
| **Performance & Reliability** | 5 | Load testing, memory management, failure recovery | Ensures production-ready scalability and reliability |

## 🎯 Critical Event Validation

The WebSocket event tests specifically validate the **5 critical events** required for business value delivery:

1. **`agent_started`** - User sees agent began processing their request
2. **`agent_thinking`** - Real-time visibility into AI reasoning process  
3. **`tool_executing`** - Transparency into tool usage and business analysis
4. **`tool_completed`** - Display of tool results and business insights
5. **`agent_completed`** - User knows when comprehensive response is ready

## 🔧 Key Test Components

### BaseAgentExecutionTest

Provides shared utilities for all agent execution tests:

- **WebSocket Event Validation**: Captures and validates event delivery
- **UserExecutionContext Creation**: Factory methods for test contexts
- **Business Value Validation**: Ensures tests focus on business outcomes
- **Performance Metrics**: Tracks execution timing and resource usage
- **Mock Infrastructure**: Only for external dependencies (LLM, WebSocket manager)

### Mock Components (External Only)

- **MockWebSocketManager**: Simulates WebSocket infrastructure without external network
- **MockLLMManager**: Provides LLM responses without API calls
- **MockBusinessTool**: Simulates tool execution with realistic business logic
- **CommunicatingMockAgent**: Enables agent communication testing

## 📈 Performance Benchmarks

### Expected Performance Standards

| Metric | Requirement | Validation |
|--------|-------------|------------|
| **Agent Execution Time** | < 2.0s per agent | All supervisor orchestration tests |
| **WebSocket Event Latency** | < 0.05s per event | WebSocket event timing tests |
| **Concurrent User Isolation** | 100% isolation | Communication handoff tests |
| **Memory Growth** | < 1000 objects per execution | Performance reliability tests |
| **Tool Execution Throughput** | > 5 tools/second | Tool dispatcher integration tests |

### Load Testing Scenarios

- **Concurrent Users**: Up to 6 simultaneous agent executions
- **Sustained Load**: 20+ consecutive executions with degradation monitoring
- **Memory Pressure**: High-memory workloads with garbage collection validation
- **Failure Recovery**: Multiple failure scenarios with business continuity validation

## 🛡️ Test Authenticity Validation

The `test_runner_validation.py` script ensures all tests maintain authenticity:

### Anti-Patterns Detected

- ❌ Mocking internal agent execution logic
- ❌ Bypassing UserExecutionContext patterns  
- ❌ Missing business value validation
- ❌ Inadequate WebSocket event coverage
- ❌ Poor agent isolation testing

### Quality Standards Enforced

- ✅ Real UserExecutionContext usage in all tests
- ✅ Business outcome validation required
- ✅ WebSocket event delivery verification
- ✅ Performance and timing measurement
- ✅ User isolation and context integrity

## 🔍 Business Value Indicators

Every test validates specific business value indicators:

### Supervisor Orchestration
- Agent routing decisions based on business context
- Comprehensive workflow execution with UVS (Universal Value System)
- Error handling maintains business continuity
- Resource optimization across agent execution

### Tool Integration  
- Tools deliver measurable business outcomes (cost savings, performance improvements)
- Business scenarios (optimization, analysis, reporting) complete successfully
- Tool coordination enables comprehensive business analysis
- Performance meets business requirements for real-time usage

### Communication & Handoffs
- Context preservation maintains business continuity across agents
- Agent coordination delivers comprehensive business results
- Multi-agent workflows provide additive business value
- State synchronization prevents business data loss

### WebSocket Events
- Real-time visibility enables business decision making
- Event delivery supports user experience requirements
- Performance under load maintains business service quality
- Event content provides actionable business information

### Performance & Reliability
- System scales to support business growth requirements
- Memory management enables sustained business operations  
- Failure recovery maintains business availability
- Performance monitoring detects business impact early

## 📋 Running Validation

```bash
# Validate all tests use real patterns (no internal mocking)
python netra_backend/tests/integration/agent_execution/test_runner_validation.py

# Expected output for passing validation:
# ✅ ALL TESTS PASS VALIDATION - Agent execution tests use real patterns!
```

## 🚨 Critical Success Criteria

These tests are considered successful when:

1. **All 25+ tests pass** with real agent execution patterns
2. **Business value indicators** are present in every test result  
3. **WebSocket events** are delivered for all 5 critical event types
4. **Performance benchmarks** are met for execution timing and resource usage
5. **User isolation** is maintained across all concurrent execution scenarios
6. **Error recovery** maintains business continuity in failure scenarios

## 🔗 Integration Points

These tests validate integration with:

- **SupervisorAgent**: Core orchestration and routing logic
- **UserExecutionContext**: Request isolation and state management
- **Tool Dispatcher**: Business tool execution and coordination
- **WebSocket Bridge**: Real-time event delivery to users
- **Agent Instance Factory**: Proper agent creation and isolation
- **LLM Manager**: AI reasoning and decision making (mocked interface only)

## 💡 Usage Examples

### Testing Custom Agent Integration

```python
# Example: Test custom agent with supervisor orchestration
context = self.create_user_execution_context(
    user_request="Custom business analysis request",
    additional_metadata={"business_priority": "high"}
)

supervisor = self.create_supervisor_agent()
result = await supervisor.execute(context, stream_updates=True)

# Validate business outcomes
assert result["orchestration_successful"] is True
assert "business_output" in result["results"]["reporting"]
```

### Validating WebSocket Events

```python
# Execute agent and validate all critical events
result = await self.execute_agent_with_validation(
    agent=agent,
    context=context,
    expected_events=['agent_started', 'agent_thinking', 'tool_executing', 
                    'tool_completed', 'agent_completed'],
    business_value_indicators=['optimization', 'insights', 'recommendations']
)
```

---

This test suite ensures that Netra's agent execution patterns deliver real business value through comprehensive, authentic integration testing that validates actual system behavior under realistic conditions.