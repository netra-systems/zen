# Netra Agent System Architecture Documentation

## 🔗 Critical Architecture References

> **⚠️ IMPORTANT**: Before working with the agent system, review the **[User Context Architecture](../USER_CONTEXT_ARCHITECTURE.md)** which describes the Factory-based isolation patterns that ensure complete user separation and eliminate shared state issues.

## Table of Contents
1. [Overview](#overview)
2. [User Isolation & Execution Context](#user-isolation--execution-context)
3. [LLM Infrastructure](#llm-infrastructure)
4. [Agent Architecture](#agent-architecture)
5. [Structured Output System](#structured-output-system)
6. [Implementation Details](#implementation-details)
7. [Testing & Validation](#testing--validation)

## Overview

The Netra platform uses a sophisticated multi-agent AI system built on LangChain and various LLM providers. The system emphasizes type safety, structured outputs, provider flexibility, and **complete user isolation through Factory patterns**.

### Key Architecture Documents
- **[User Context Architecture](../USER_CONTEXT_ARCHITECTURE.md)** - Factory patterns, execution engines, and user isolation
- [WebSocket Modernization](../WEBSOCKET_MODERNIZATION_REPORT.md) - WebSocket event isolation
- [Tool Dispatcher Migration](../TOOL_DISPATCHER_MIGRATION_GUIDE.md) - Request-scoped tool execution

## User Isolation & Execution Context (Issue #1116 Complete - 2025-09-14)

The agent system implements complete user isolation through the Factory pattern architecture described in the **[User Context Architecture](../USER_CONTEXT_ARCHITECTURE.md)** with **Issue #1116 Agent Factory SSOT migration complete**:

### 🏆 Agent Factory SSOT Implementation (Issue #1116 Complete):
- **AgentInstanceFactory**: SSOT for all agent instantiation with guaranteed user isolation
- **ExecutionEngineFactory**: Creates per-request execution engines
- **UserExecutionContext**: Maintains isolated state for each user request
- **IsolatedExecutionEngine**: Executes agents with no shared state
- **UserWebSocketEmitter**: Delivers events to specific users only

### Enterprise Security Guarantees:
- **Zero Singleton Patterns**: All 48+ singleton violations eliminated
- **Complete User Isolation**: Factory patterns prevent cross-user contamination
- **Enterprise Compliance**: HIPAA, SOC2, SEC requirements met
- **0% Cross-User Contamination**: Validated through comprehensive testing

This ensures that concurrent users never share state or receive cross-user notifications, with enterprise-grade security validation.

## LLM Infrastructure

### Package Dependencies

The system uses the following critical package combinations for structured output support:

```
google-genai>=1.32.0
langchain-google-genai>=2.1.10
langchain-core>=0.3.75
langchain-community>=0.3.28
openai>=1.101.0
anthropic>=0.64.0
```

### Provider Management Architecture

```
LLMProviderManager (netra_backend/app/llm/llm_provider_manager.py)
├── LLMConfigManager (Configuration)
├── Provider Handlers (Provider-specific initialization)
│   ├── Google/Gemini (ChatGoogleGenerativeAI)
│   ├── OpenAI (ChatOpenAI)
│   ├── Anthropic (ChatAnthropic)
│   ├── Cohere (ChatCohere)
│   └── Mistral (ChatMistralAI)
└── Caching Layer (Instance reuse)
```

### Key Components

#### 1. LLM Provider Manager (`llm_provider_manager.py`)
- **Purpose**: Centralized LLM instance management
- **Features**:
  - Provider abstraction
  - Instance caching
  - Configuration merging
  - API key validation
  - Fallback response handling

#### 2. Provider Handlers (`llm_provider_handlers.py`)
- **Purpose**: Provider-specific LLM initialization
- **Implementation**:
  ```python
  def create_google_llm(model_name: str, api_key: str, 
                       generation_config: Dict[str, Any]) -> Any:
      from langchain_google_genai import ChatGoogleGenerativeAI
      return ChatGoogleGenerativeAI(
          model=model_name,
          api_key=api_key,
          **generation_config
      )
  ```

#### 3. Structured Operations (`llm_structured_operations.py`)
- **Purpose**: Type-safe structured output generation
- **Method**: Uses `llm.with_structured_output(schema)` pattern
- **Features**:
  - Pydantic model validation
  - Response caching
  - Fallback to JSON parsing
  - Retry logic

## Agent Architecture

### Multi-Layered Approach

```
Supervisor Agent (Orchestration)
├── Triage Agent (Request Classification)
├── Data Agent (Data Analysis)
├── Optimization Agent (Performance Tuning)
├── Reporting Agent (Report Generation)
└── Corpus Admin Agent (Knowledge Management)
```

### Base Agent Pattern (`base_agent.py`)

All agents inherit from a common base that provides:
- LLM manager integration
- Structured output support
- Error handling
- Logging and metrics
- Context management

## Structured Output System

### Current Implementation

The system uses a comprehensive approach to structured data generation:

1. **Primary Method**: `with_structured_output()`
   - Native support in langchain-google-genai>=2.1.10
   - Ensures type-safe responses
   - Validates against Pydantic schemas

2. **Validation Pipeline**:
   ```python
   # Example from triage agent
   llm = self.llm_manager.get_llm("triage")
   structured_llm = llm.with_structured_output(TriageResult)
   response = await structured_llm.ainvoke(prompt)
   # response is now a validated TriageResult instance
   ```

3. **Fallback Chain**:
   - Structured call with schema
   - Retry on ValidationError
   - Text generation with JSON instruction
   - Basic fallback structure if all fails

### Success Metrics

Based on the LLM Structured Data Generation Audit:
- **Without Outlines**: ~17.7% initial success rate (industry average)
- **With retries**: Higher success but increased latency
- **Token waste**: ~82% of structured calls may fail initially

### Recommended Improvements

The audit recommends adopting the Outlines library for:
- **99.9% structure guarantee**
- **5x faster generation**
- **60-80% token savings**
- **Simplified error handling**

## Implementation Details

### Environment Management

All environment access goes through `IsolatedEnvironment` as defined in `SPEC/unified_environment_management.xml`.

### Database Connectivity

Uses architecture defined in `SPEC/database_connectivity_architecture.xml` for all database connections.

### Circuit Breaker Pattern

Each provider has circuit breakers to prevent cascade failures:
- Tracks failure rates per provider
- Automatic failover to alternate providers
- Exponential backoff for retries
- Failure classification (transient vs permanent)

### Logging & Observability

```python
# Current logging structure
- Input/Output logging via log_agent_input/output
- Correlation IDs for request tracking
- Heartbeat system for long-running LLM calls
- Performance metrics in metadata
```

#### Missing Observability (To Be Implemented)
- Structured output success rate tracking
- Validation failure rate monitoring
- Schema compliance metrics
- Fallback usage frequency

## Testing & Validation

### Test Infrastructure

```
test_framework/
├── llm_config_manager.py (Test configuration)
├── conftest_base.py (Base fixtures)
├── llm_mock_clients.py (Mock LLM clients)
└── fixtures/
    └── llm_fixtures_core.py (LLM test fixtures)
```

### Mock Support

The system includes comprehensive mocking for testing:

```python
class MockLLM:
    def with_structured_output(self, schema: Type[BaseModel], **kwargs):
        """Return a mock structured LLM for dev mode."""
        return MockStructuredLLM(self.model_name, schema)
```

### Validation Process

1. **Package Compatibility Check**:
   - Verify langchain-google-genai>=2.1.10
   - Confirm google-genai>=1.32.0
   - Test with_structured_output availability

2. **Functional Testing**:
   - Unit tests for each agent
   - Integration tests with real LLMs
   - E2E tests for full workflows
   - Performance benchmarks

## Configuration

### LLM Configuration Structure

```python
# Example configuration
llm_configs = {
    "triage": {
        "provider": "google",
        "model_name": "gemini-1.5-flash",
        "api_key": os.getenv("GEMINI_API_KEY"),
        "generation_config": {
            "temperature": 0.5,
            "max_tokens": 1000
        }
    }
}
```

### Provider Support Matrix

| Provider | Model Support | Structured Output | Status |
|----------|--------------|-------------------|---------|
| Google/Gemini | gemini-1.5-flash/pro | ✅ Native | Production |
| OpenAI | GPT-4/GPT-3.5 | ✅ Native | Production |
| Anthropic | Claude 3 | ✅ Native | Production |
| Cohere | Command | ✅ Via LangChain | Beta |
| Mistral | Mistral models | ✅ Via LangChain | Beta |

## Best Practices

### 1. Always Use Structured Output
```python
# Good
structured_llm = llm.with_structured_output(ResponseSchema)
response = await structured_llm.ainvoke(prompt)

# Bad
response = await llm.ainvoke(prompt)
parsed = json.loads(response.content)  # Prone to errors
```

### 2. Define Clear Schemas
```python
class AgentResponse(BaseModel):
    """Well-documented response schema"""
    status: str = Field(description="Success or failure")
    data: Dict = Field(description="Response data")
    confidence: float = Field(ge=0, le=1, description="Confidence score")
```

### 3. Implement Proper Error Handling
```python
try:
    response = await structured_llm.ainvoke(prompt)
except ValidationError as e:
    # Handle schema validation errors
    logger.error(f"Schema validation failed: {e}")
    # Fall back to alternative approach
```

### 4. Monitor Performance
- Track structured output success rates
- Monitor token usage
- Measure response latencies
- Alert on degradation

## Future Roadmap

### Phase 1: Metrics & Monitoring (Weeks 1-2)
- Implement structured generation metrics
- Create monitoring dashboard
- Establish baseline success rates

### Phase 2: Outlines Integration (Weeks 3-4)
- Pilot Outlines library with TriageAgent
- A/B test against current implementation
- Measure token savings and latency improvements

### Phase 3: Full Migration (Weeks 5-6)
- Gradual rollout with feature flags
- Update all agents to use constrained generation
- Document new patterns

### Phase 4: Optimization (Weeks 7-8)
- Implement grammar-based generation
- Add multiple-choice constraints
- Optimize caching strategies

## Compliance & Standards

The agent system adheres to:
- **SPEC/type_safety.xml**: Type safety requirements
- **SPEC/conventions.xml**: Coding standards
- **SPEC/import_management_architecture.xml**: Import rules
- **SPEC/git_commit_atomic_units.xml**: Version control standards

## Conclusion

The Netra agent system provides a robust, type-safe, multi-provider LLM infrastructure with structured output support. The combination of langchain-google-genai>=2.1.10 and google-genai>=1.32.0 ensures reliable structured generation for Google's Gemini models, with similar support across all major providers.

Key strengths:
- Provider-agnostic architecture
- Type-safe structured outputs
- Comprehensive fallback system
- Extensive testing infrastructure

Areas for improvement:
- Implement Outlines for guaranteed structure
- Add comprehensive metrics tracking
- Reduce token waste from retries
- Enhance observability

---

*Last Updated: 2025-08-30*
*Version: 1.0.0*