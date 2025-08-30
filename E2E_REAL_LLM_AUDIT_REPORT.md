# E2E Real LLM Test Audit Report

## Executive Summary

**CRITICAL FINDING**: The e2e tests marked with `@pytest.mark.real_llm` are **NOT using real LLMs** by default. They rely on environment variables that are not set, causing tests to either skip or fall back to mocks. This violates the CLAUDE.md principle: "MOCKS are FORBIDDEN in dev, staging or production."

## Key Findings

### 1. Real LLM Tests Are Not Real ❌

**Evidence:**
- Environment variables `TEST_USE_REAL_LLM`, `USE_REAL_LLM`, `ENABLE_REAL_LLM_TESTING` are **not set** by default
- `GEMINI_API_KEY` is **not configured** in the environment
- Tests check these variables and **skip execution** when not set
- Many tests marked `@pytest.mark.real_llm` actually use **mocks internally**

**Example from `test_real_llm_core.py`:**
```python
def should_use_real_llm(self) -> bool:
    env_enabled = (
        os.getenv("TEST_USE_REAL_LLM", "false").lower() == "true" or
        os.getenv("USE_REAL_LLM", "false").lower() == "true"
    )
    if not env_enabled:
        return False  # Tests skip here!
```

### 2. Widespread Mock Usage in E2E Tests ❌

**Violation Count: 50+ files using mocks**

Key offenders:
- `test_supervisor_real_llm_integration.py`: Uses `AsyncMock()` for dependencies despite "real_llm" name
- `journeys/test_agent_conversation_flow.py`: Patches LLM manager with mocks
- `ai_supply_chain_helpers.py`: Contains `MockLLMProvider` class
- `config.py`: Sets mock API keys when real LLM testing is disabled

### 3. Test Coverage Gaps 🟨

**Found 14 test files** marked with `@pytest.mark.real_llm`, but coverage is limited:

**What's Tested:**
- Basic LLM API calls (Google AI/Gemini)
- Cost management validation
- Performance SLA checks (<2s response)
- Concurrent LLM calls
- Agent-LLM integration

**What's Missing:**
- Error recovery and retry logic with real APIs
- Rate limiting behavior
- Token exhaustion scenarios
- API key rotation
- Multi-provider failover
- Real streaming responses
- Long-running conversations
- Context window limits
- Real cost tracking validation
- Production data processing

### 4. Configuration Issues ❌

**Problems:**
1. **No API keys configured**: Tests can't run without `GEMINI_API_KEY`
2. **Confusing variable names**: Three different env vars for same purpose
3. **Mock fallback by default**: `config.py` sets mock keys when real LLM disabled
4. **No clear documentation**: How to enable real LLM testing not documented

### 5. Test Infrastructure Problems

**Unified Test Runner Issues:**
- `--real-llm` flag exists but not well integrated
- Frontend tests set `USE_REAL_LLM=false` by default
- No clear separation between mock and real test suites

## Impact Assessment

### Business Risk
- **$347K+ MRR at risk**: Enterprise customers rely on LLM integration
- **20-50% cost reduction claims unvalidated**: Without real LLM tests, optimization claims are unverified
- **Production failures likely**: Mocked tests don't catch real API issues

### Technical Debt
- Tests provide false confidence
- Real integration issues go undetected
- Performance characteristics unknown
- Cost management untested

## Recommendations

### Immediate Actions Required

1. **Enable Real LLM Testing**
   ```bash
   export TEST_USE_REAL_LLM=true
   export GEMINI_API_KEY=<actual_key>
   ```

2. **Remove All Mocks from E2E Tests**
   - Replace `AsyncMock()` with real service instances
   - Remove all `patch()` decorators for LLM services
   - Use real database, Redis, and API connections

3. **Fix test_real_llm_core.py**
   - Remove skip conditions
   - Fail tests explicitly if API key missing
   - Add proper error messages

### Short-term Improvements

1. **Create Dedicated Real LLM Test Suite**
   ```bash
   tests/e2e/real_llm/
   ├── test_api_integration.py
   ├── test_cost_tracking.py
   ├── test_error_handling.py
   ├── test_performance.py
   └── test_streaming.py
   ```

2. **Add Missing Test Scenarios**
   - Rate limiting and backoff
   - Token limit handling
   - Multi-provider failover
   - Real-time streaming
   - Long conversation contexts

3. **Improve Configuration**
   - Single env var: `NETRA_REAL_LLM_ENABLED`
   - Clear documentation in README
   - CI/CD integration with secure key storage

### Long-term Strategy

1. **Separate Test Environments**
   - Mock suite for fast CI/CD
   - Real LLM suite for nightly/release testing
   - Cost-controlled test quotas

2. **Monitoring and Reporting**
   - Track real LLM test costs
   - Performance baselines
   - API reliability metrics

3. **Compliance Enforcement**
   - Pre-commit hooks to prevent mock usage in e2e/
   - Automated detection of mock patterns
   - Regular audit reports

## Conclusion

The current "real LLM" tests are **not real** and violate core architectural principles. This creates significant business risk and technical debt. Immediate action is required to:

1. Enable actual LLM API calls in tests
2. Remove all mocks from e2e test suite
3. Expand test coverage for critical scenarios
4. Establish proper test infrastructure

**Recommendation**: Stop all feature development until real LLM testing is properly implemented. The risk to $347K+ MRR is too high to continue with mock-based testing.

## Compliance Score

- **Current State**: 2/10 ❌
- **After Immediate Actions**: 5/10 🟨
- **After Full Implementation**: 9/10 ✅

---

*Generated: 2025-08-30*
*Auditor: Principal Engineer*
*Business Impact: CRITICAL - $347K+ MRR at risk*