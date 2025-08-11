# Real LLM Testing Configuration Requirements Report

## Overview
This report outlines the missing configuration items and setup requirements needed to fully enable real LLM testing in the Netra AI Platform test suite.

## Current Implementation Status

### ✅ Completed
1. **Testing Specification Updated** (`SPEC/testing.xml`)
   - Added comprehensive `<real_llm_testing>` section
   - Defined test environments, seed data management, execution patterns
   - Documented performance expectations and cost estimates
   - Added troubleshooting guide and best practices

2. **Test Runner Enhanced** (`test_runner.py`)
   - Added `--real-llm` flag to enable real LLM API calls
   - Added `--llm-model` option with support for multiple models
   - Added `--llm-timeout` option for configurable timeouts
   - Added `--parallel` option for controlling test parallelism
   - Environment variables passed to backend tests: `TEST_USE_REAL_LLM`, `TEST_LLM_MODEL`, `TEST_LLM_TIMEOUT`, `TEST_PARALLEL`

## Missing Configuration Items

### 1. Environment Variables
The following environment variables need to be configured for real LLM testing:

#### Test-Specific LLM API Keys
```bash
# Separate API keys for testing (lower rate limits, cost tracking)
TEST_ANTHROPIC_API_KEY=<your-test-anthropic-key>
TEST_GOOGLE_API_KEY=<your-test-google-key>
TEST_OPENAI_API_KEY=<your-test-openai-key>

# Test database connections
TEST_DATABASE_URL=postgresql://user:pass@localhost/netra_test
TEST_REDIS_URL=redis://localhost:6379/1
TEST_CLICKHOUSE_URL=clickhouse://localhost:9000/netra_test

# Staging environment (optional)
STAGING_DATABASE_URL=postgresql://user:pass@staging/netra_staging
```

### 2. Database Setup Scripts
The following scripts need to be created:

#### `scripts/setup_test_db.sql`
```sql
-- Create test database and schema
CREATE DATABASE IF NOT EXISTS netra_test;
-- Apply migrations
-- Create test users with appropriate permissions
-- Set up initial schema
```

#### `scripts/teardown_test_db.sql`
```sql
-- Clean up test data
-- Reset sequences
-- Clear caches
```

### 3. Seed Data Files
The following seed data files need to be created:

#### `test_data/seed/basic_optimization.json`
- 5 test users with different permission levels
- 10 conversation threads with varying complexity
- 1000 sample metrics over 7 days
- 3 different model configurations

#### `test_data/seed/complex_workflows.json`
- Pre-generated corpus entries
- AI supply chain configurations
- 50 KV cache instances
- Performance benchmark data

#### `test_data/seed/edge_cases.json`
- Intentionally malformed requests
- Rate limit simulation data
- Long-running query scenarios
- High memory usage patterns

### 4. Backend Test Runner Modifications
The backend test runner (`scripts/test_backend.py`) needs to be updated to:

1. **Read environment variables for real LLM configuration**
```python
import os

USE_REAL_LLM = os.environ.get("TEST_USE_REAL_LLM", "false") == "true"
LLM_MODEL = os.environ.get("TEST_LLM_MODEL", "gemini-1.5-flash")
LLM_TIMEOUT = int(os.environ.get("TEST_LLM_TIMEOUT", "30"))
PARALLEL = os.environ.get("TEST_PARALLEL", "auto")
```

2. **Configure pytest to use real LLM when requested**
```python
if USE_REAL_LLM:
    # Disable LLM mocking
    os.environ["DEV_MODE_DISABLE_LLM"] = "false"
    # Set the test LLM model
    os.environ["TEST_LLM_MODEL_OVERRIDE"] = LLM_MODEL
    # Configure timeout
    pytest_args.extend(["--timeout", str(LLM_TIMEOUT)])
```

3. **Add parallel execution control**
```python
if PARALLEL != "auto":
    if PARALLEL == "1":
        # Sequential execution
        pytest_args.append("-n0")
    else:
        # Specific number of workers
        pytest_args.extend(["-n", PARALLEL])
```

### 5. LLM Manager Updates
The LLM Manager (`app/llm/llm_manager.py`) needs modifications to:

1. **Support test-specific API keys**
```python
def get_api_key(provider: str) -> str:
    if os.environ.get("TEST_USE_REAL_LLM") == "true":
        # Use test-specific keys
        key_map = {
            "google": "TEST_GOOGLE_API_KEY",
            "openai": "TEST_OPENAI_API_KEY",
            "anthropic": "TEST_ANTHROPIC_API_KEY"
        }
        return os.environ.get(key_map.get(provider))
    # Regular key retrieval
```

2. **Override model selection for testing**
```python
def get_model_for_context(context: str) -> str:
    if model_override := os.environ.get("TEST_LLM_MODEL_OVERRIDE"):
        return model_override
    # Regular model selection
```

### 6. Test Fixtures and Utilities
Create `app/tests/fixtures/llm_test_fixtures.py`:

```python
import pytest
import os
from typing import Generator

@pytest.fixture(scope="session")
def real_llm_enabled() -> bool:
    """Check if real LLM testing is enabled"""
    return os.environ.get("TEST_USE_REAL_LLM", "false") == "true"

@pytest.fixture(scope="function")
def llm_test_tracker() -> Generator:
    """Track LLM calls for cost estimation"""
    tracker = {
        "calls": 0,
        "tokens": 0,
        "cost": 0.0
    }
    yield tracker
    # Log final stats
    print(f"LLM Test Stats: {tracker['calls']} calls, {tracker['tokens']} tokens, ${tracker['cost']:.2f}")

@pytest.fixture(scope="session")
def seed_data_loader():
    """Load seed data for consistent testing"""
    import json
    from pathlib import Path
    
    def load_seed(name: str):
        path = Path(f"test_data/seed/{name}.json")
        if path.exists():
            return json.loads(path.read_text())
        return {}
    
    return load_seed
```

### 7. Quality Gate Integration
Update quality gate tests to work with real LLM responses:

```python
# app/tests/services/test_quality_gate_real.py
import pytest
from app.services.quality_gate_service import QualityGateService

@pytest.mark.skipif(
    not os.environ.get("TEST_USE_REAL_LLM") == "true",
    reason="Real LLM testing not enabled"
)
class TestQualityGateRealLLM:
    async def test_real_response_validation(self, real_llm_response):
        """Validate real LLM responses meet quality criteria"""
        service = QualityGateService()
        result = await service.validate(real_llm_response)
        
        assert result.specificity_score >= 0.6
        assert result.actionability_score >= 0.6
        assert not result.has_circular_reasoning
```

### 8. CI/CD Pipeline Configuration
Add GitHub Actions workflow (`.github/workflows/real-llm-tests.yml`):

```yaml
name: Real LLM Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  real-llm-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run Real LLM Tests
        env:
          TEST_GOOGLE_API_KEY: ${{ secrets.TEST_GOOGLE_API_KEY }}
          TEST_OPENAI_API_KEY: ${{ secrets.TEST_OPENAI_API_KEY }}
          TEST_DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
        run: |
          python test_runner.py --level critical --real-llm --parallel 1
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: real-llm-test-results
          path: test_reports/
```

## Implementation Priority

### High Priority (Required for Basic Functionality)
1. Backend test runner environment variable handling
2. LLM Manager test key support
3. Basic seed data files (at least one dataset)

### Medium Priority (Enhanced Testing)
1. Database setup/teardown scripts
2. Test fixtures and utilities
3. Quality gate integration

### Low Priority (Nice to Have)
1. CI/CD pipeline configuration
2. Cost tracking and reporting
3. Advanced seed data scenarios

## Estimated Implementation Time
- High Priority items: 2-3 hours
- Medium Priority items: 3-4 hours
- Low Priority items: 2-3 hours
- **Total: 7-10 hours**

## Next Steps
1. Create test-specific API keys with appropriate rate limits
2. Set up test database infrastructure
3. Modify backend test runner to handle environment variables
4. Create initial seed data files
5. Test with a simple real LLM test case
6. Gradually expand test coverage with real LLM calls

## Cost Considerations
Based on the specifications, expected costs for real LLM testing:
- Daily critical tests: ~$0.50-1.00
- Weekly integration tests: ~$2.00-5.00
- Monthly comprehensive tests: ~$10.00-20.00
- **Estimated monthly total: $30-50** (with daily critical, weekly integration)

## Recommendations
1. Start with gemini-1.5-flash for most tests (best cost/performance ratio)
2. Use sequential execution (--parallel 1) initially to avoid rate limits
3. Implement response caching to reduce redundant API calls
4. Set up budget alerts in cloud provider dashboards
5. Run real LLM tests selectively (not on every commit)
6. Use dedicated test API keys with lower rate limits
7. Monitor and log all LLM interactions for debugging

---
*Generated: 2025-08-11*
*Purpose: Configuration requirements for real LLM testing implementation*