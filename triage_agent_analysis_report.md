# Triage Agent Issue Analysis Report

## Issue Summary
The triage agent is not stuck but consistently failing to parse LLM responses and falling back to error results. The flow completes, but always returns an error category instead of proper triage categorization.

## Root Cause Analysis

### 1. Circuit Breaker Cascade Failure
- **Location**: `netra_backend/app/llm/fallback_handler.py`
- **Issue**: After initial failures, the circuit breaker opens and blocks all subsequent LLM calls
- **Impact**: All triage attempts immediately fail with "Error" category

### 2. Structured LLM Call Implementation
- **Current Implementation**: Properly uses `ask_structured_llm` with Pydantic schema
- **Schema**: `TriageResult` model in `netra_backend/app/agents/triage_sub_agent/models.py`
- **Issue**: Circuit breaker prevents actual LLM calls from executing

### 3. Fallback Chain
1. First attempt: `ask_structured_llm` with `TriageResult` schema
2. On failure: Retry with exponential backoff (max 2 attempts)
3. Circuit breaker opens after 3 failures
4. All subsequent calls return `None` from circuit breaker check
5. Fallback creates error result with `category: "Error"`

## Technical Details

### Execution Flow
```
/run_agent endpoint → SupervisorAgent → TriageSubAgent
    ↓
TriageSubAgent.execute()
    ↓
llm_processor.execute_triage_with_llm()
    ↓
llm_fallback_handler.execute_structured_with_fallback()
    ↓
Circuit Breaker Check (OPEN = immediate return None)
    ↓
_validate_or_create_fallback() → Creates Error result
```

### Key Files
- `netra_backend/app/agents/triage_sub_agent/agent.py` - Main agent
- `netra_backend/app/agents/triage_sub_agent/llm_processor.py` - LLM orchestration
- `netra_backend/app/llm/fallback_handler.py` - Circuit breaker & fallback logic
- `netra_backend/app/agents/triage_sub_agent/execution_helpers.py` - Error result creation

## Gemini 2.0 Flash Compatibility

### Current Support
- Configuration exists in `netra_backend/app/schemas/config.py` with `gemini_api_key` field
- LLM provider enum supports Gemini models
- Structured output supported via `with_structured_output()` method

### Implementation Status
✅ Gemini API key configuration
✅ Provider selection logic
✅ Structured output support
⚠️ Circuit breaker thresholds may need tuning for Gemini latency

## Recommendations

### Immediate Fixes

1. **Reset Circuit Breakers on Test Start**
```python
# In test setup
agent.llm_fallback_handler.reset_circuit_breakers()
```

2. **Tune Circuit Breaker Settings**
```python
# netra_backend/app/llm/client_config.py
FAST_LLM_CONFIG = CircuitBreakerConfig(
    failure_threshold=10,  # Increase from 5
    recovery_timeout=10.0,  # Decrease from 20
    timeout_seconds=15,     # Increase from 10
)
```

3. **Fix Mock LLM Manager**
```python
# Return valid structured response on first call
async def mock_ask_structured_llm(prompt, llm_config_name, schema, **kwargs):
    return schema(**EXPECTED_TRIAGE_RESPONSE)  # Direct success
```

### Long-term Improvements

1. **Implement Circuit Breaker Reset Logic**
   - Add periodic reset for development/testing
   - Implement health check endpoint to reset circuits

2. **Improve Error Categorization**
   - Replace generic "Error" category with specific failure types
   - Add "SystemUnavailable", "ValidationFailed", "TimeoutError" categories

3. **Add Observability**
   - Log circuit breaker state changes
   - Track fallback usage metrics
   - Monitor structured vs unstructured LLM call ratios

## Test Results

### Current Behavior
- All 6 test prompts return `category: "Error"`
- Circuit breaker opens after first 2 failures
- Subsequent calls blocked by open circuit
- Fallback always returns error result

### Expected Behavior
- Prompts should categorize as "Cost Optimization", "Performance", etc.
- Circuit breaker should allow retries after recovery timeout
- Fallback should provide meaningful default categorization

## Business Value Justification (BVJ)
- **Segment**: Free, Early, Mid
- **Business Goal**: Conversion through accurate triage
- **Value Impact**: Poor triage blocks optimization value demonstration
- **Strategic Impact**: 80% of users abandon after failed triage (estimated)

## Next Steps

1. Implement circuit breaker reset in test setup
2. Tune circuit breaker thresholds for development
3. Add proper Gemini 2.0 Flash model configuration
4. Test with real LLM endpoints
5. Monitor production circuit breaker metrics