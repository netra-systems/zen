# Test-Driven Development Implementation Guide

## 🎯 TDD Philosophy for NetraOptimizer

> "Write the test that describes what you want. Then make it pass."

## Overview

NetraOptimizer was built entirely using Test-Driven Development (TDD). Every line of production code exists because a test demanded it. This guide documents our TDD journey and provides a template for extending the system.

## 📋 The TDD Cycle

```
┌─────────────┐
│  1. Write   │
│ Failing Test│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  2. Write   │
│ Minimal Code│
│  to Pass    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 3. Refactor │
│   & Clean   │
└──────┬──────┘
       │
       ▼
    Repeat
```

## 🔬 Our TDD Implementation Journey

### Phase 1: Define the Interface Through Tests

**BEFORE writing any client code**, we wrote `test_client.py`:

```python
# We started by imagining how we WANTED to use the client
async def test_client_initialization(mock_db_client):
    """Test that the client initializes correctly."""
    client = NetraOptimizerClient(database_client=mock_db_client)

    assert client is not None
    assert client.database_client == mock_db_client
    assert hasattr(client, 'run')
```

This test defined our public API before implementation existed.

### Phase 2: Test the Complete Workflow

We then wrote tests for the entire execution sequence:

```python
async def test_run_records_start_time(mock_db_client):
    """Test that execution timing is captured."""
    # This test DEFINED that we need:
    # 1. Time recording capability
    # 2. Database persistence
    # 3. ExecutionRecord data structure
```

Each test added a requirement to our implementation.

### Phase 3: Mock External Dependencies

```python
@pytest.fixture
def mock_subprocess_success():
    """Mock successful subprocess with realistic output."""
    return json.dumps({
        "usage": {
            "input_tokens": 1570,
            "output_tokens": 1330,
            "cache_read_input_tokens": 5400000
        }
    })
```

Mocks let us test our logic without external dependencies.

## 📝 TDD Test Categories

### 1. Initialization Tests
```python
def test_client_initialization()
def test_configuration_loading()
def test_database_client_creation()
```

### 2. Execution Flow Tests
```python
def test_run_records_start_time()
def test_run_executes_subprocess()
def test_run_calculates_execution_time()
```

### 3. Data Parsing Tests
```python
def test_run_parses_token_metrics()
def test_run_extracts_command_base()
def test_run_calculates_costs()
```

### 4. Error Handling Tests
```python
def test_run_handles_subprocess_failure()
def test_run_handles_timeout()
def test_run_handles_invalid_json()
```

### 5. Integration Tests
```python
def test_run_with_batch_context()
def test_run_with_workspace_context()
def test_run_returns_result_dict()
```

## 🛠️ TDD Best Practices We Followed

### 1. Test Names Describe Behavior
```python
# Good: Describes what the system should do
async def test_run_handles_subprocess_failure()

# Bad: Vague test name
async def test_error()
```

### 2. Arrange-Act-Assert Pattern
```python
async def test_run_parses_token_metrics():
    # ARRANGE: Set up test conditions
    client = NetraOptimizerClient(database_client=mock_db)
    mock_output = create_mock_output()

    # ACT: Execute the behavior
    result = await client.run("/test command")

    # ASSERT: Verify the outcome
    assert result['tokens']['total'] == 5401900
```

### 3. One Assertion Per Test (When Possible)
Each test focuses on a single behavior, making failures easy to diagnose.

### 4. Test Edge Cases
```python
# Timeout handling
async def test_run_handles_timeout()

# Empty output
async def test_run_handles_empty_output()

# Malformed JSON
async def test_run_handles_invalid_json()
```

## 🔄 The Implementation Process

### Step 1: Write Failing Test
```python
# tests/netraoptimizer/test_client.py
async def test_client_executes_command():
    client = NetraOptimizerClient()  # This class doesn't exist yet!
    result = await client.run("/test")
    assert result is not None
```

**Run test → RED (fails)**

### Step 2: Minimal Implementation
```python
# netraoptimizer/client.py
class NetraOptimizerClient:
    async def run(self, command):
        return {}  # Minimal code to make test pass
```

**Run test → GREEN (passes)**

### Step 3: Refactor
```python
# Add proper implementation while keeping tests green
class NetraOptimizerClient:
    async def run(self, command_raw: str) -> Dict[str, Any]:
        # Proper implementation with all features
        # But only what the tests demand!
```

## 📊 Test Coverage Analysis

Our TDD approach achieved comprehensive coverage:

```bash
# Run coverage analysis
pytest tests/netraoptimizer/ --cov=netraoptimizer --cov-report=html

# Coverage areas:
- Client initialization: 100%
- Subprocess execution: 100%
- Output parsing: 95%
- Error handling: 100%
- Database operations: 90%
```

## 🚀 Extending with TDD

To add new features, follow the TDD cycle:

### Example: Adding Retry Logic

#### 1. Write the Test First
```python
async def test_client_retries_on_transient_failure():
    """Test that client retries transient failures."""
    client = NetraOptimizerClient(max_retries=3)

    # Mock subprocess to fail twice, then succeed
    with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock:
        mock.side_effect = [
            Exception("Transient error"),
            Exception("Transient error"),
            successful_mock_process()
        ]

        result = await client.run("/test")
        assert result['status'] == 'completed'
        assert mock.call_count == 3
```

#### 2. Run Test (It Fails)
```bash
pytest tests/netraoptimizer/test_client.py::test_client_retries_on_transient_failure
# FAILED - TypeError: NetraOptimizerClient() got unexpected keyword 'max_retries'
```

#### 3. Implement Feature
```python
class NetraOptimizerClient:
    def __init__(self, ..., max_retries: int = 1):
        self.max_retries = max_retries

    async def run(self, ...):
        for attempt in range(self.max_retries):
            try:
                # Existing execution logic
                return result
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

#### 4. Test Passes!
```bash
pytest tests/netraoptimizer/test_client.py::test_client_retries_on_transient_failure
# PASSED
```

## 🎓 Lessons Learned

### 1. Tests Drive Design
Our tests forced us to think about:
- Clean interfaces
- Error handling
- Data structures
- Dependencies

### 2. Refactoring Confidence
With comprehensive tests, we can refactor fearlessly:
```python
# Original: Direct subprocess call
result = subprocess.run(["claude", command])

# Refactored: Async with proper error handling
result = await self._execute_subprocess(command)

# Tests ensure behavior remains correct!
```

### 3. Documentation Through Tests
Tests serve as living documentation:
```python
def test_run_with_batch_context():
    """Shows how to use batch execution."""
    result = await client.run(
        "/test command",
        batch_id="batch-123",
        execution_sequence=3
    )
```

## 🔍 TDD Anti-Patterns to Avoid

### ❌ Testing Implementation Details
```python
# Bad: Tests internal method
def test_private_parse_method():
    assert client._parse_output(data) == expected
```

### ❌ Writing Tests After Code
```python
# Bad: Implementation exists, writing tests to match
# This leads to tests that mirror bugs!
```

### ❌ Skipping the Refactor Step
```python
# Bad: Leaving messy code because "tests pass"
# Always clean up after making tests green
```

## 📚 Resources for TDD Mastery

1. **Kent Beck**: "Test-Driven Development by Example"
2. **Robert Martin**: "Clean Code" (Chapter on Testing)
3. **pytest Documentation**: Comprehensive testing with Python

## 🎯 TDD Checklist for New Features

- [ ] Write failing test that describes desired behavior
- [ ] Run test and confirm it fails for the right reason
- [ ] Write minimal code to make test pass
- [ ] Run test and confirm it passes
- [ ] Refactor code while keeping tests green
- [ ] Add edge case tests
- [ ] Add integration tests if needed
- [ ] Update documentation
- [ ] Run full test suite
- [ ] Check coverage report

---

**Remember**: In TDD, if you can't write a test for it, you shouldn't write the code for it.