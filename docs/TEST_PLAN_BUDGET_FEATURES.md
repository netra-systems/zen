# Comprehensive Test Plan: Token and Cost Budget Features

## Executive Summary

This test plan focuses on Zen's most valuable features for cost-conscious users: **token and cost budget management**. These features enable users to control their spending and prevent unexpected costs when using Claude models. The plan covers both the `TokenBudgetManager` in `token_budget/budget_manager.py` and the `ClaudePricingEngine` in `token_transparency/claude_pricing_engine.py`.

**Target Users:** Organizations and developers who need to manage and control their Claude API costs effectively.

**High-Value Features Tested:**
1. Budget enforcement (warn/block modes)
2. Cost calculation accuracy
3. Token-to-cost and cost-to-token conversions
4. Multi-model pricing support
5. Overall and per-command budget limits

---

## 1. Test Coverage Areas

### 1.1 Token Budget Manager (`token_budget/budget_manager.py`)

#### Priority 1: Budget Enforcement Modes (Critical)
**Why Critical:** This is the primary mechanism users rely on to prevent overspending.

**Test Cases:**

| Test ID | Test Case | Expected Behavior | Enforcement Mode | File Reference |
|---------|-----------|-------------------|------------------|----------------|
| TB-001 | Warn mode with overall budget exceeded | Warning message displayed, execution continues | `warn` | `budget_manager.py:20` |
| TB-002 | Block mode with overall budget exceeded | Execution blocked, error message shown | `block` | `budget_manager.py:20` |
| TB-003 | Warn mode with command budget exceeded | Warning for specific command, execution continues | `warn` | `budget_manager.py:67-76` |
| TB-004 | Block mode with command budget exceeded | Command execution blocked | `block` | `budget_manager.py:67-76` |
| TB-005 | Multiple commands under combined budget limit | All commands execute successfully | Both | `budget_manager.py:143-154` |
| TB-006 | Overall budget takes precedence over command budget | Overall budget enforced first | Both | `budget_manager.py:143-145` |

**Implementation Notes:**
- Test both token-based and cost-based budgets
- Verify error messages are clear and actionable
- Test edge case: exactly at budget limit

#### Priority 1: Budget Calculation and Tracking (Critical)
**Why Critical:** Inaccurate tracking leads to budget overruns or unnecessary blocking.

**Test Cases:**

| Test ID | Test Case | Expected Behavior | Budget Type | File Reference |
|---------|-----------|-------------------|-------------|----------------|
| TB-101 | Token budget initialization | Budget correctly set and tracked | Tokens | `budget_manager.py:19-45` |
| TB-102 | Cost budget initialization | Budget correctly set and tracked | Cost | `budget_manager.py:22,34-35` |
| TB-103 | Mixed budget initialization | Both types supported simultaneously | Mixed | `budget_manager.py:21,39-41` |
| TB-104 | Record token usage | Total and command usage updated accurately | Tokens | `budget_manager.py:89-99` |
| TB-105 | Record cost usage | Total and command cost updated accurately | Cost | `budget_manager.py:101-105` |
| TB-106 | Check remaining budget | Correct remaining amount calculated | Both | `models.py:30-32` |
| TB-107 | Budget percentage calculation | Accurate percentage of budget used | Both | `models.py:34-37` |

**Implementation Notes:**
- Test with various budget sizes (small: $1, medium: $10, large: $100)
- Verify floating-point precision for cost calculations
- Test cumulative usage across multiple commands

#### Priority 2: Budget Type Conversions (High Value)
**Why Important:** Enables users to think in either tokens or dollars based on preference.

**Test Cases:**

| Test ID | Test Case | Expected Behavior | File Reference |
|---------|-----------|-------------------|----------------|
| TB-201 | Convert tokens to cost (Claude 3.5 Sonnet) | Accurate cost calculation with 60/40 input/output split | `budget_manager.py:156-173` |
| TB-202 | Convert tokens to cost (Claude Haiku) | Different pricing rate applied correctly | `budget_manager.py:156-173` |
| TB-203 | Convert tokens to cost (Claude Opus) | Premium pricing rate applied correctly | `budget_manager.py:156-173` |
| TB-204 | Convert cost to tokens (average pricing) | Approximate token count returned | `budget_manager.py:175-189` |
| TB-205 | Round-trip conversion accuracy | Cost → tokens → cost within 20% tolerance | `test_dollar_budget_enhancement.py:161-165` |
| TB-206 | Conversion with zero tokens/cost | Handles edge case gracefully | `budget_manager.py:156-189` |

**Implementation Notes:**
- Use official Claude pricing rates from documentation
- Document the 60/40 input/output split assumption
- Test with various models

---

### 1.2 Claude Pricing Engine (`token_transparency/claude_pricing_engine.py`)

#### Priority 1: Cost Calculation Accuracy (Critical)
**Why Critical:** Financial accuracy is paramount; errors directly impact user costs.

**Test Cases:**

| Test ID | Test Case | Expected Behavior | File Reference |
|---------|-----------|-------------------|----------------|
| CP-001 | Calculate cost for Claude 3.5 Sonnet | $3/M input, $15/M output pricing | `claude_pricing_engine.py:29-36,206-207` |
| CP-002 | Calculate cost for Claude Haiku 3.5 | $0.8/M input, $4/M output pricing | `claude_pricing_engine.py:29-36,206-207` |
| CP-003 | Calculate cost for Claude Opus 4 | $15/M input, $75/M output pricing | `claude_pricing_engine.py:29-36,206-207` |
| CP-004 | Calculate cost with cache reads (10% of base) | Correct cache read multiplier applied | `claude_pricing_engine.py:39,210-211` |
| CP-005 | Calculate cost with 5min cache writes (1.25x) | 25% premium for cache creation | `claude_pricing_engine.py:40,214-219` |
| CP-006 | Calculate cost with 1hour cache writes (2.0x) | 100% premium for cache creation | `claude_pricing_engine.py:41,214-219` |
| CP-007 | Calculate cost with tool usage | Tool tokens charged at input rate | `claude_pricing_engine.py:222-226` |
| CP-008 | Zero token usage | Returns $0.00 cost | `test_pricing_engine.py:284-293` |
| CP-009 | Authoritative cost override | SDK cost takes precedence | `claude_pricing_engine.py:190-197` |

**Implementation Notes:**
- Verify against official Claude pricing documentation
- Test cost breakdown includes all components
- Precision: 6 decimal places for USD amounts

#### Priority 1: Model Detection (Critical)
**Why Critical:** Wrong model detection leads to incorrect pricing.

**Test Cases:**

| Test ID | Test Case | Expected Behavior | File Reference |
|---------|-----------|-------------------|----------------|
| CP-101 | Detect model from 'model' field | Model correctly identified | `claude_pricing_engine.py:107-108` |
| CP-102 | Detect model from 'model_name' field | Model correctly identified | `claude_pricing_engine.py:109` |
| CP-103 | Detect model from nested 'usage.model' | Model correctly identified | `claude_pricing_engine.py:110` |
| CP-104 | Detect model from 'message.model' | Model correctly identified | `claude_pricing_engine.py:111` |
| CP-105 | Detect model from 'metadata.model' | Model correctly identified | `claude_pricing_engine.py:112` |
| CP-106 | Handle missing model field | Defaults to Claude 3.5 Sonnet | `claude_pricing_engine.py:123-124` |
| CP-107 | Normalize model name variations | Various formats correctly normalized | `claude_pricing_engine.py:126-147` |
| CP-108 | Detect cache type (5min vs 1hour) | Correct cache type identified | `claude_pricing_engine.py:149-174` |

**Implementation Notes:**
- Test with real API response formats
- Document default fallback behavior
- Handle case-insensitive model names

#### Priority 2: Response Parsing (High Value)
**Why Important:** Accurate parsing ensures correct cost tracking from API responses.

**Test Cases:**

| Test ID | Test Case | Expected Behavior | File Reference |
|---------|-----------|-------------------|----------------|
| CP-201 | Parse valid JSON response with usage data | TokenUsageData correctly populated | `claude_pricing_engine.py:238-280` |
| CP-202 | Parse nested usage data (message.usage) | TokenUsageData extracted correctly | `claude_pricing_engine.py:263-264` |
| CP-203 | Parse response with cache tokens | Cache tokens correctly extracted | `claude_pricing_engine.py:270-271` |
| CP-204 | Handle malformed JSON | Returns None gracefully | `claude_pricing_engine.py:277-279` |
| CP-205 | Handle non-JSON text | Returns None gracefully | `test_pricing_engine.py:218-231` |
| CP-206 | Handle missing usage field | Returns None gracefully | `claude_pricing_engine.py:277-279` |

**Implementation Notes:**
- Test with various API response formats
- Verify error handling doesn't crash
- Log parsing failures for debugging

#### Priority 2: Transparency Reporting (High Value)
**Why Important:** Users need visibility into where their money is going.

**Test Cases:**

| Test ID | Test Case | Expected Behavior | File Reference |
|---------|-----------|-------------------|----------------|
| CP-301 | Generate transparency report | All required fields present | `claude_pricing_engine.py:282-327` |
| CP-302 | Report includes cost breakdown | Input, output, cache costs separate | `claude_pricing_engine.py:307-314` |
| CP-303 | Report includes token breakdown | All token types detailed | `claude_pricing_engine.py:299-306` |
| CP-304 | Report includes pricing rates | Current rates documented | `claude_pricing_engine.py:315-321` |
| CP-305 | Report includes compliance info | Source documentation linked | `claude_pricing_engine.py:322-327` |
| CP-306 | Cost values rounded to 6 decimals | Consistent precision | `claude_pricing_engine.py:308-313` |

**Implementation Notes:**
- Verify report format is user-friendly
- Test with tool usage included
- Ensure compliance URL is current

---

## 2. Integration Test Scenarios

### Scenario 1: User Sets Overall Cost Budget with Block Mode
**Objective:** Prevent execution when projected cost would exceed budget.

**Steps:**
1. Initialize `TokenBudgetManager` with `overall_cost_budget=5.0`, `enforcement_mode='block'`
2. Attempt command estimated at $3.00
3. Record actual usage of $2.95
4. Attempt second command estimated at $2.50
5. Verify second command is blocked (total would be $5.45 > $5.00)
6. Check error message is clear and actionable

**Expected Results:**
- First command: Executes successfully
- Second command: Blocked before execution
- Error message: "Overall cost budget exceeded: $5.45/$5.00"
- Total usage remains at $2.95

**Files Involved:**
- `budget_manager.py:126-129`
- `budget_manager.py:20` (enforcement_mode)

---

### Scenario 2: User Sets Per-Command Cost Budgets
**Objective:** Different commands have different cost limits.

**Steps:**
1. Initialize `TokenBudgetManager` with `overall_cost_budget=10.0`
2. Set command budget: `/analyze` → $3.00
3. Set command budget: `/summarize` → $1.50
4. Execute `/analyze` using $2.80
5. Execute `/summarize` using $1.45
6. Attempt `/summarize` again with estimated $0.20
7. Verify `/summarize` is blocked (would be $1.65 > $1.50)

**Expected Results:**
- `/analyze`: Executes, uses $2.80, has $0.20 remaining
- `/summarize`: First execution succeeds ($1.45 used)
- `/summarize`: Second execution blocked
- Error message: "Command '/summarize' cost budget exceeded: $1.65/$1.50"
- Overall budget: $4.25/$10.00 used

**Files Involved:**
- `budget_manager.py:78-87` (set_command_cost_budget)
- `budget_manager.py:120-138` (check_cost_budget)

---

### Scenario 3: Warn Mode Allows Execution but Alerts User
**Objective:** User gets visibility into budget overruns without blocking work.

**Steps:**
1. Initialize `TokenBudgetManager` with `overall_cost_budget=2.0`, `enforcement_mode='warn'`
2. Execute command estimated at $1.50, actual cost $1.45
3. Execute command estimated at $1.00, actual cost $0.95
4. Verify both commands execute
5. Check warning message displayed for second command

**Expected Results:**
- Both commands execute successfully
- Total usage: $2.40 (exceeds $2.00 budget)
- Warning message shown: "Overall cost budget exceeded: $2.40/$2.00"
- Execution NOT blocked

**Files Involved:**
- `budget_manager.py:20` (enforcement_mode='warn')
- Integration with orchestrator to display warnings

---

### Scenario 4: Multi-Model Cost Calculation
**Objective:** Verify correct pricing for different Claude models.

**Steps:**
1. Calculate cost for 10,000 input + 5,000 output tokens on Sonnet 3.5
2. Calculate same usage on Haiku 3.5
3. Calculate same usage on Opus 4
4. Verify cost differences match pricing tiers

**Expected Results:**
- **Sonnet 3.5**: Input: $0.03, Output: $0.075, Total: $0.105
- **Haiku 3.5**: Input: $0.008, Output: $0.020, Total: $0.028
- **Opus 4**: Input: $0.15, Output: $0.375, Total: $0.525
- Cost ratios: Opus ≈ 5x Sonnet, Sonnet ≈ 3.75x Haiku

**Files Involved:**
- `claude_pricing_engine.py:29-36` (MODEL_PRICING)
- `claude_pricing_engine.py:176-236` (calculate_cost)

---

### Scenario 5: Cache-Aware Cost Calculation
**Objective:** Verify cache pricing reduces costs appropriately.

**Steps:**
1. Calculate cost without cache: 10,000 input, 5,000 output (Sonnet)
2. Calculate cost with 5min cache: 5,000 input, 5,000 cache read, 5,000 output
3. Calculate cost with 1hour cache: 5,000 input, 5,000 cache creation, 5,000 output
4. Compare costs

**Expected Results:**
- **No cache**: $0.105 (as per Scenario 4)
- **5min cache read**: Input $0.015, Cache read $0.0015, Output $0.075 = **$0.0915** (13% savings)
- **1hour cache write**: Input $0.015, Cache write $0.030, Output $0.075 = **$0.120** (14% premium)

**Files Involved:**
- `claude_pricing_engine.py:39-41` (cache multipliers)
- `claude_pricing_engine.py:210-219` (cache cost calculation)

---

## 3. Edge Cases and Error Handling

### 3.1 Budget Edge Cases

| Test ID | Edge Case | Expected Behavior | Severity |
|---------|-----------|-------------------|----------|
| EC-001 | Exactly at budget limit | Allow execution | Medium |
| EC-002 | Budget set to $0.00 | Block all execution | High |
| EC-003 | Negative budget value | Reject with error | High |
| EC-004 | Extremely large budget (>$1M) | Handle gracefully | Low |
| EC-005 | Budget in different currency | Not supported, document | Low |
| EC-006 | Budget updated mid-execution | New limit takes effect | Medium |
| EC-007 | Command removed from budget list | No limits applied | Low |

### 3.2 Calculation Edge Cases

| Test ID | Edge Case | Expected Behavior | Severity |
|---------|-----------|-------------------|----------|
| EC-101 | Zero tokens | Return $0.00 | High |
| EC-102 | Single token | Minimal cost calculated | Medium |
| EC-103 | Billion tokens | Handle large numbers | Low |
| EC-104 | Unknown model | Default to Sonnet 3.5 | Medium |
| EC-105 | Future model not in config | Graceful degradation | Medium |
| EC-106 | Floating-point precision errors | Round to 6 decimals | High |
| EC-107 | Malformed API response | Return None, log error | High |

### 3.3 Concurrency Edge Cases

| Test ID | Edge Case | Expected Behavior | Severity |
|---------|-----------|-------------------|----------|
| EC-201 | Multiple commands check budget simultaneously | Serialized access, correct totals | High |
| EC-202 | Budget updated during command execution | Consistent view per command | Medium |
| EC-203 | Usage recorded out of order | Totals still accurate | Medium |

---

## 4. Test Implementation Guide

### 4.1 Unit Tests Structure

```python
# tests/test_budget_manager_comprehensive.py

class TestBudgetEnforcement(unittest.TestCase):
    """Test warn and block enforcement modes"""

    def test_block_mode_overall_budget(self):
        """Test TB-002: Block mode prevents budget overrun"""
        manager = TokenBudgetManager(
            overall_cost_budget=5.0,
            enforcement_mode='block'
        )

        # Record usage approaching limit
        manager.record_cost_usage('/cmd1', 4.5)

        # Try to exceed budget
        can_run, reason = manager.check_cost_budget('/cmd2', 1.0)

        self.assertFalse(can_run)
        self.assertIn('Overall cost budget exceeded', reason)
        self.assertIn('$5.50/$5.00', reason)

    def test_warn_mode_allows_execution(self):
        """Test TB-001: Warn mode allows execution over budget"""
        manager = TokenBudgetManager(
            overall_cost_budget=2.0,
            enforcement_mode='warn'
        )

        # Record usage
        manager.record_cost_usage('/cmd1', 1.5)

        # This would exceed budget but should still "pass" check in warn mode
        # Note: actual warning display is handled by orchestrator
        can_run, reason = manager.check_cost_budget('/cmd2', 1.0)

        # In warn mode, we still report the issue but don't block
        # Implementation detail: may need orchestrator integration
        # to properly test warning vs blocking

class TestBudgetCalculations(unittest.TestCase):
    """Test budget calculation accuracy"""

    def test_cost_budget_tracking(self):
        """Test TB-105: Cost usage tracking accuracy"""
        manager = TokenBudgetManager(overall_cost_budget=10.0)
        manager.set_command_cost_budget('/analyze', 3.0)

        # Record usage
        manager.record_cost_usage('/analyze', 1.25)
        manager.record_cost_usage('/analyze', 0.50)

        # Verify totals
        self.assertEqual(manager.total_usage, 1.75)
        self.assertEqual(
            manager.command_budgets['/analyze'].used,
            1.75
        )
        self.assertEqual(
            manager.command_budgets['/analyze'].remaining,
            1.25
        )

class TestBudgetConversions(unittest.TestCase):
    """Test token-cost conversions"""

    def test_tokens_to_cost_sonnet(self):
        """Test TB-201: Token to cost conversion for Sonnet"""
        manager = TokenBudgetManager(overall_cost_budget=10.0)

        cost = manager.convert_tokens_to_cost(
            tokens=1000,
            model='claude-3-5-sonnet'
        )

        # 1000 tokens with 60/40 split
        # Input: 600 * $3/1M = $0.0018
        # Output: 400 * $15/1M = $0.0060
        # Total: $0.0078
        expected_cost = 0.0078

        self.assertAlmostEqual(cost, expected_cost, places=6)
```

### 4.2 Integration Tests Structure

```python
# tests/test_budget_integration.py

class TestBudgetIntegrationScenarios(unittest.TestCase):
    """End-to-end budget management scenarios"""

    def test_scenario_1_overall_budget_block(self):
        """Scenario 1: Overall budget with block mode"""
        manager = TokenBudgetManager(
            overall_cost_budget=5.0,
            enforcement_mode='block'
        )

        # Step 1: First command
        can_run, _ = manager.check_cost_budget('/cmd1', 3.0)
        self.assertTrue(can_run)
        manager.record_cost_usage('/cmd1', 2.95)

        # Step 2: Second command exceeds budget
        can_run, reason = manager.check_cost_budget('/cmd2', 2.50)
        self.assertFalse(can_run)
        self.assertIn('$5.45/$5.00', reason)

        # Step 3: Total usage unchanged (blocked)
        self.assertEqual(manager.total_usage, 2.95)
```

### 4.3 Pricing Engine Tests Structure

```python
# tests/test_pricing_engine_comprehensive.py

class TestCostCalculationAccuracy(unittest.TestCase):
    """Test cost calculation for all models"""

    def test_multi_model_pricing(self):
        """Scenario 4: Different models have different costs"""
        engine = ClaudePricingEngine()

        # Same usage across models
        base_usage = TokenUsageData(
            input_tokens=10000,
            output_tokens=5000
        )

        # Test each model
        models_and_costs = [
            ('claude-3-5-sonnet', 0.105),
            ('claude-haiku-3.5', 0.028),
            ('claude-opus-4', 0.525)
        ]

        for model, expected_cost in models_and_costs:
            usage = TokenUsageData(
                input_tokens=10000,
                output_tokens=5000,
                model=model
            )
            cost = engine.calculate_cost(usage)

            self.assertAlmostEqual(
                cost.total_cost,
                expected_cost,
                places=6,
                msg=f"Cost mismatch for {model}"
            )

class TestCacheCostCalculation(unittest.TestCase):
    """Test cache-aware cost calculations"""

    def test_cache_cost_reduction(self):
        """Scenario 5: Cache reduces costs"""
        engine = ClaudePricingEngine()

        # No cache
        no_cache = TokenUsageData(
            input_tokens=10000,
            output_tokens=5000,
            model='claude-3-5-sonnet'
        )
        cost_no_cache = engine.calculate_cost(no_cache)

        # With cache read (5min)
        with_cache = TokenUsageData(
            input_tokens=5000,
            output_tokens=5000,
            cache_read_tokens=5000,
            cache_type='5min',
            model='claude-3-5-sonnet'
        )
        cost_with_cache = engine.calculate_cost(with_cache)

        # Cache should reduce cost
        self.assertLess(
            cost_with_cache.total_cost,
            cost_no_cache.total_cost
        )

        # Verify specific savings
        savings_pct = (
            (cost_no_cache.total_cost - cost_with_cache.total_cost)
            / cost_no_cache.total_cost * 100
        )
        self.assertAlmostEqual(savings_pct, 13.0, delta=1.0)
```

---

## 5. Test Execution Plan

### 5.1 Phases

**Phase 1: Unit Tests (Week 1)**
- Implement all Priority 1 test cases
- Run tests against current codebase
- Document any failures
- Target: 100% pass rate

**Phase 2: Integration Tests (Week 2)**
- Implement all 5 integration scenarios
- Test with real API responses (mocked)
- Verify end-to-end workflows
- Target: All scenarios pass

**Phase 3: Edge Cases (Week 3)**
- Implement all edge case tests
- Stress test with extreme values
- Verify error handling
- Target: Graceful degradation

**Phase 4: Regression Testing (Ongoing)**
- Add to CI/CD pipeline
- Run on every commit
- Monitor for regressions

### 5.2 Success Criteria

✅ **All Priority 1 tests pass (100%)**
✅ **Integration scenarios work end-to-end**
✅ **Cost calculations accurate to 6 decimal places**
✅ **Budget enforcement prevents overruns in block mode**
✅ **Budget warnings display in warn mode**
✅ **Edge cases handled gracefully**
✅ **No crashes or unhandled exceptions**

### 5.3 Test Data

```python
# Test data constants
SAMPLE_BUDGETS = {
    'small': 1.0,      # $1 for small tasks
    'medium': 10.0,    # $10 for standard workflows
    'large': 100.0,    # $100 for extensive analysis
}

SAMPLE_MODELS = [
    'claude-3-5-sonnet',
    'claude-haiku-3.5',
    'claude-opus-4',
]

SAMPLE_COMMANDS = {
    '/analyze': 5.0,       # Moderate cost
    '/summarize': 1.50,    # Low cost
    '/research': 15.0,     # High cost
}
```

---

## 6. Reporting and Metrics

### 6.1 Test Coverage Metrics

Track coverage for:
- **Line coverage**: Target >95% for budget_manager.py and claude_pricing_engine.py
- **Branch coverage**: Target >90% for conditional logic
- **Function coverage**: Target 100% for public methods

### 6.2 Test Execution Reports

For each test run, report:
1. Total tests executed
2. Pass/fail/skip counts
3. Execution time
4. Coverage percentages
5. Any regressions detected

### 6.3 Quality Gates

**Cannot merge code unless:**
- All Priority 1 tests pass
- Coverage remains above thresholds
- No new edge cases introduced without tests
- Integration scenarios all pass

---

## 7. Appendix

### 7.1 Pricing Reference (As of 2024-2025)

| Model | Input ($/M tokens) | Output ($/M tokens) |
|-------|-------------------|---------------------|
| Claude Opus 4 | $15.00 | $75.00 |
| Claude Sonnet 4 | $3.00 | $15.00 |
| Claude 3.5 Sonnet | $3.00 | $15.00 |
| Claude Haiku 3.5 | $0.80 | $4.00 |

**Cache Multipliers:**
- Cache read: 0.1x (10% of input price)
- 5-min cache write: 1.25x (25% premium)
- 1-hour cache write: 2.0x (100% premium)

**Source:** https://docs.claude.com/en/docs/about-claude/pricing

### 7.2 File Reference Map

| Component | File Path | Key Classes/Functions |
|-----------|-----------|----------------------|
| Budget Manager | `token_budget/budget_manager.py` | `TokenBudgetManager` |
| Budget Models | `token_budget/models.py` | `BudgetType`, `CommandBudgetInfo` |
| Pricing Engine | `token_transparency/claude_pricing_engine.py` | `ClaudePricingEngine` |
| Pricing Config | `token_transparency/claude_pricing_engine.py` | `ClaudePricingConfig` |
| Usage Data | `token_transparency/claude_pricing_engine.py` | `TokenUsageData` |
| Cost Breakdown | `token_transparency/claude_pricing_engine.py` | `CostBreakdown` |
| Existing Tests | `tests/test_pricing_engine.py` | Pricing tests |
| Existing Tests | `tests/test_dollar_budget_enhancement.py` | Budget tests |

### 7.3 Test Execution Commands

```bash
# Run all budget and pricing tests
python -m pytest tests/test_budget_manager_comprehensive.py -v
python -m pytest tests/test_pricing_engine_comprehensive.py -v
python -m pytest tests/test_budget_integration.py -v

# Run with coverage
python -m pytest tests/test_budget_*.py --cov=token_budget --cov=token_transparency --cov-report=html

# Run specific test category
python -m pytest tests/test_budget_*.py -k "enforcement" -v
python -m pytest tests/test_pricing_*.py -k "cost_calculation" -v

# Run integration scenarios only
python -m pytest tests/test_budget_integration.py::TestBudgetIntegrationScenarios -v
```

---

## Document Control

**Version:** 1.0
**Created:** 2025-10-10
**Author:** Claude Code
**Status:** Draft for Review
**Next Review:** After test implementation

**Change Log:**
- 2025-10-10: Initial version created with comprehensive test plan
