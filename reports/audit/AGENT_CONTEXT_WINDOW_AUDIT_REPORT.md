# Agent Context Window Isolation and Observability Audit Report

## Executive Summary

This audit examined the context window isolation, prompt management, and observability capabilities of the Netra agent system. Critical gaps were identified in context length validation, token counting, and observability reporting that could lead to:

1. **Context overflow errors** when prompts exceed model limits
2. **Cross-agent context leakage** due to insufficient isolation
3. **Lack of visibility** into token usage and context sizes
4. **Missing safeguards** for prompt truncation and batching

## Key Findings

### 1. Context Isolation Issues

**Current State:**
- Agents maintain a `context` dictionary but lack formal isolation mechanisms
- No validation of context window sizes before LLM calls
- Context can be shared inadvertently between agent instances

**Evidence:**
```python
# From BaseSubAgent
self.context = {}  # Protected context for this agent
```

**Impact:** HIGH - Risk of sensitive data leakage between agents

### 2. Missing Token Counting

**Current State:**
- No token counting implementation in base agents
- Methods like `_estimate_token_count()` do not exist
- Prompt size logging only tracks MB, not tokens

**Evidence:**
```python
# From ActionsToMeetGoalsSubAgent
def _log_prompt_size(self, prompt: str, run_id: str):
    size_mb = len(prompt) / (1024 * 1024)
    if size_mb > 1:
        logger.info(f"Large prompt ({size_mb:.2f}MB) for {run_id}")
```

**Impact:** HIGH - Cannot predict or prevent context overflow

### 3. No Context Window Validation

**Current State:**
- No validation before sending prompts to LLM
- No checks against model-specific context limits
- No handling for context overflow errors

**Test Results:**
- 16 tests failed due to missing implementations
- 5 tests marked as expected failures (xfail)

**Impact:** CRITICAL - Production failures when context exceeds limits

### 4. Limited Observability

**Current State:**
- Basic prompt size logging in MB only
- No metrics collection for token usage
- No alerting on context threshold violations
- No system-wide context usage tracking

**Impact:** MEDIUM - Cannot monitor or optimize token usage

## Test Coverage Analysis

### Failed Test Categories

1. **Context Isolation (5 failures)**
   - `test_context_isolation_between_agents` - FAILED
   - `test_parallel_agent_context_isolation` - FAILED
   - `test_supervisor_agent_context_distribution` - FAILED

2. **Context Size Management (6 failures)**
   - `test_context_window_size_limit` - FAILED
   - `test_prompt_truncation_on_overflow` - FAILED
   - `test_context_window_with_history` - FAILED

3. **Token Counting (3 failures)**
   - `test_token_counting_accuracy` - FAILED
   - `test_max_tokens_enforcement` - FAILED
   - `test_dynamic_token_allocation` - FAILED

4. **Observability (2 failures)**
   - `test_context_metrics_reporting` - FAILED
   - `test_context_overflow_alerting` - FAILED

### Root Cause: Abstract Class Issue

Many tests failed with:
```
TypeError: Can't instantiate abstract class BaseSubAgent without an implementation for abstract method 'execute'
```

This indicates the base agent class requires concrete implementations for testing.

## Specific Agent Analysis

### 1. Supervisor Agent
- **Max tokens:** 2000 (hardcoded)
- **No context validation**
- **No token counting**

### 2. Data Sub-Agent
- **No explicit token limits**
- **No context truncation**
- **No batch processing for large datasets**

### 3. Triage Sub-Agent
- **Config includes MAX_TOKENS** but not enforced
- **Has `_truncate_content()` but only for display**
- **No conversation history limits**

### 4. Actions Agent
- **Has `_log_prompt_size()` but only logs MB**
- **No token-based limits**
- **No context overflow handling**

## Recommendations

### Immediate Actions (P0)

1. **Implement Token Counting**
   ```python
   def _estimate_token_count(self, text: str) -> int:
       # Implement proper tokenization
       return len(str(text)) // 4  # Rough estimate
   ```

2. **Add Context Validation**
   ```python
   def _validate_context_window(self, prompt: str) -> None:
       tokens = self._estimate_token_count(prompt)
       if tokens > self.context_limit:
           raise ContextWindowExceeded(tokens, self.context_limit)
   ```

3. **Implement Context Truncation**
   ```python
   def _truncate_context(self, context: Dict, max_tokens: int) -> Dict:
       # Smart truncation preserving recent/important data
   ```

### Short-term Actions (P1)

1. **Add Observability Mixin**
   - Import and use `ContextObservabilityMixin` in all agents
   - Report metrics to monitoring system
   - Set up alerting thresholds

2. **Implement Batch Processing**
   - For corpus admin and data agents handling large datasets
   - Process in chunks to avoid context overflow

3. **Add Context Isolation Tests**
   - Ensure contexts are truly isolated between agents
   - Test parallel execution scenarios

### Long-term Actions (P2)

1. **Dynamic Context Management**
   - Automatically adjust context based on model limits
   - Implement sliding window for conversation history
   - Smart context compression techniques

2. **Token Budget System**
   - Track token usage per user/session
   - Implement cost tracking and limits
   - Optimize token usage across agent calls

3. **Advanced Observability**
   - Real-time token usage dashboard
   - Predictive alerts for context overflow
   - Historical analysis and optimization recommendations

## Implementation Guide

### Step 1: Add Context Observability Mixin

```python
# In base_agent.py
from netra_backend.app.agents.context_observability import ContextObservabilityMixin

class BaseSubAgent(
    AgentLifecycleMixin,
    AgentCommunicationMixin,
    AgentStateMixin,
    AgentObservabilityMixin,
    ContextObservabilityMixin,  # Add this
    ABC
):
    ...
```

### Step 2: Use Token Validation

```python
# Before any LLM call
async def process(self, query: str, context: Dict) -> Any:
    prompt = self._build_prompt(query, context)
    self._validate_context_window_size(prompt)  # Add validation
    self._report_context_metrics()  # Add metrics
    
    result = await self.llm_manager.generate(
        prompt,
        max_tokens=self._calculate_output_tokens(context)
    )
    ...
```

### Step 3: Implement Graceful Degradation

```python
# Handle context overflow
try:
    result = await self._execute_with_context(prompt, context)
except ContextWindowExceeded:
    truncated = self._truncate_context_if_needed(context)
    result = await self._execute_with_context(prompt, truncated)
```

## Metrics to Track

1. **Per Agent:**
   - Average context size (bytes/tokens)
   - Peak context usage
   - Context overflow frequency
   - Token usage per call

2. **System-wide:**
   - Total token consumption
   - Context overflow rate
   - Average response truncation
   - Cost per agent type

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Context overflow in production | HIGH | CRITICAL | Implement validation and truncation |
| Token cost overruns | MEDIUM | HIGH | Add token budgeting and monitoring |
| Cross-agent data leakage | LOW | CRITICAL | Ensure proper context isolation |
| Performance degradation | MEDIUM | MEDIUM | Implement efficient token counting |

## Conclusion

The current agent system lacks critical context window management capabilities. The implementation of the `ContextObservabilityMixin` provides a foundation, but it must be integrated into all agents along with proper testing and monitoring.

**Priority:** CRITICAL - These issues will cause production failures with large contexts.

**Estimated Effort:** 
- Immediate fixes: 2-3 days
- Full implementation: 1-2 weeks
- Complete observability: 3-4 weeks

## Appendix: Test Commands

```bash
# Run context isolation tests
python -m pytest netra_backend/tests/agents/test_context_window_isolation.py -v

# Run context validation tests  
python -m pytest netra_backend/tests/agents/test_context_length_validation.py -v

# Run with coverage
python -m pytest netra_backend/tests/agents/test_context*.py --cov=netra_backend.app.agents --cov-report=html
```

---

*Report Generated: 2024-12-29*
*Audit Performed By: Principal Engineer*
*Next Review Date: 2025-01-15*