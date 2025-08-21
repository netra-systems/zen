# Real LLM Testing Configuration Improvements

## Summary
Updated the real LLM testing configuration to provide better defaults, parallel execution control, and realistic timeouts for production-quality testing.

## Key Improvements

### 1. Enhanced Test Levels
- **Added `real_e2e` level**: Complete end-to-end tests with real services (20-30 min)
- **Updated `real_services` level**: Better timeouts and parallelism controls (40 min timeout)
- **Smart defaults**: Each level has appropriate LLM timeout defaults

### 2. Intelligent Parallel Execution
- **Rate limit protection**: Automatically limits parallel LLM calls to 2-3 to avoid rate limits
- **Smart delays**: Adds 1s delay between calls when parallelism > 2
- **Level-specific limits**: Each test level defines its own `max_parallel_llm_calls`

### 3. Realistic Timeouts
- **Default LLM timeout**: 30s (can be overridden)
- **Level-specific defaults**:
  - `real_services`: 60s per LLM call
  - `real_e2e`: 90s per LLM call
  - `agent-startup`: 60s per LLM call
- **Test suite timeouts**: Automatically tripled when using real LLM

### 4. Pytest Marker Fix
- Added `real_e2e` marker to pytest.ini to fix marker configuration error

## Usage Examples

### Basic Real LLM Testing
```bash
# Run integration tests with real LLM (smart defaults)
python test_runner.py --level integration --real-llm

# Run E2E tests with real services
python test_runner.py --level real_e2e --real-llm

# Run with specific model and timeout
python test_runner.py --level real_services --real-llm --llm-model gpt-4 --llm-timeout 120
```

### Parallel Execution Control
```bash
# Auto parallel (limits to 2-3 for LLM tests)
python test_runner.py --level real_services --real-llm --parallel auto

# Serial execution (safest for rate limits)
python test_runner.py --level real_e2e --real-llm --parallel 1

# Maximum parallelism (use with caution)
python test_runner.py --level integration --real-llm --parallel max
```

### Agent Testing
```bash
# Agent tests with real LLM (MANDATORY for agent changes)
python test_runner.py --level agents --real-llm

# Agent startup E2E tests
python test_runner.py --level agent-startup --real-llm
```

## Configuration Details

### Test Level Configurations
| Level | Default LLM Timeout | Max Parallel | Suite Timeout | Business Critical |
|-------|-------------------|--------------|---------------|-------------------|
| real_e2e | 90s | 2 | 30 min | Yes |
| real_services | 60s | 2 | 40 min | No |
| agent-startup | 60s | 2 | 5 min | Yes |
| integration | 30s | 3 | 5 min | No |
| agents | 30s | 3 | 3 min | No |

### Environment Variables Set
- `TEST_USE_REAL_LLM=true`
- `ENABLE_REAL_LLM_TESTING=true`
- `TEST_LLM_TIMEOUT={timeout}`
- `TEST_LLM_MODEL={model}`
- `TEST_PARALLEL={workers}`
- `TEST_LLM_RATE_LIMIT_DELAY={delay}` (when needed)

## Best Practices

1. **Start with serial execution** (`--parallel 1`) when testing with production API keys
2. **Use cost-efficient models** (gemini-2.5-flash) for regular testing
3. **Reserve premium models** (gpt-4, gemini-2.5-pro) for critical validation
4. **Monitor API costs** - Real LLM tests cost ~$0.50-5.00 per run depending on model
5. **Use appropriate timeouts** - 60-120s for complex agent interactions
6. **Run real LLM tests selectively** - Not every commit needs them

## Performance Expectations

### With Mocks (Default)
- Integration: 3-5 minutes
- Comprehensive: 10-15 minutes

### With Real LLM
- Integration: 10-15 minutes
- Real Services: 20-30 minutes
- Real E2E: 20-30 minutes
- Comprehensive: 30-45 minutes

## Troubleshooting

### Rate Limit Errors
- Reduce parallelism: `--parallel 1`
- Add delays between tests
- Use test-specific API keys with higher limits

### Timeout Errors
- Increase timeout: `--llm-timeout 120`
- Check network connectivity
- Verify API key validity

### Inconsistent Results
- Use deterministic models (temperature=0)
- Ensure consistent seed data
- Run tests serially for debugging