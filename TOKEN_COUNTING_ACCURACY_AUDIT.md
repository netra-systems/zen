# Token Counting Accuracy Audit - Claude Instance Orchestrator

**File Audited**: `scripts\claude-instance-orchestrator.py`
**Date**: 2025-09-16
**Issue**: Token counting inaccuracies relative to Claude Code SDK best practices

## Executive Summary

The Claude Instance Orchestrator contains several critical token counting inaccuracies that violate SDK billing principles and could lead to significant cost miscalculations. The primary issues involve double-counting tokens from messages with identical IDs and improper aggregation of usage data.

## Critical Issues Identified

### 1. **Double-Counting from Same Message ID** (Critical)
**Location**: Lines 803-826, 832-854
**Issue**: The code accumulates token usage using `+=` even when processing messages with the same ID.
**SDK Rule Violated**: "All messages with the same `id` field report identical usage" - should only charge once per unique message ID.

```python
# WRONG - Double counting
status.input_tokens += int(usage['input_tokens'])    # Line 805
status.output_tokens += int(usage['output_tokens'])  # Line 806
```

**Impact**: Users could be charged multiple times for the same Claude API call.

### 2. **No Message ID Deduplication**
**Location**: `_try_parse_json_token_usage()` method
**Issue**: The method doesn't check if it already processed a message ID.
**SDK Rule Violated**: "You should only charge users once per step" and "Same ID = Same Usage"

**Current Implementation**:
```python
def _try_parse_json_token_usage(self, line: str, status: InstanceStatus) -> bool:
    # Missing: message ID deduplication check
    if 'usage' in json_data:
        status.input_tokens += int(usage['input_tokens'])  # Always accumulates
```

### 3. **Cache Token Aggregation Error**
**Location**: Lines 809-811, 837-839
**Issue**: Combines `cache_read_input_tokens` and `cache_creation_input_tokens` into single `cached_tokens` field.
**SDK Rule Violated**: These represent different billing categories with different pricing.

```python
# WRONG - Loses pricing distinction
if 'cache_read_input_tokens' in usage:
    status.cached_tokens += int(usage['cache_read_input_tokens'])
if 'cache_creation_input_tokens' in usage:
    status.cached_tokens += int(usage['cache_creation_input_tokens'])  # Same field!
```

### 4. **Total Token Miscalculation**
**Location**: Lines 823-825, 851-853
**Issue**: Calculates total by summing already-accumulated values instead of using authoritative values.
**SDK Rule Violated**: Should use the highest/final reported total, not accumulate components.

```python
# WRONG - Calculating from already-accumulated values
calculated_total = input_tokens + output_tokens + cache_creation + cache_read
if calculated_total > status.total_tokens:
    status.total_tokens = calculated_total
```

### 5. **Missing "Same ID" Detection for Tool Calls**
**Location**: Lines 858-867
**Issue**: Tool calls are incremented without checking message ID deduplication.

```python
# WRONG - No ID deduplication
if json_data['type'] in ['tool_use', 'tool_call', 'tool_execution']:
    status.tool_calls += 1  # Always increments
```

### 6. **Cost Calculation Issues**
**Location**: Lines 432-437 (`_calculate_cost` method)
**Issues**:
- Uses incorrect pricing: $3/$15 per million (outdated)
- Treats all cached tokens with single $0.30 rate
- Should differentiate cache read vs creation costs

```python
# WRONG - Outdated pricing and oversimplified cache cost
def _calculate_cost(self, status: InstanceStatus) -> float:
    input_cost = (status.input_tokens / 1_000_000) * 3.00   # Outdated rate
    output_cost = (status.output_tokens / 1_000_000) * 15.00 # Outdated rate
    cache_cost = (status.cached_tokens / 1_000_000) * 0.30   # Wrong approach
```

## SDK-Compliant Solution

### Required Changes to `InstanceStatus` Class

```python
@dataclass
class InstanceStatus:
    """Status of a Claude Code instance"""
    name: str
    pid: Optional[int] = None
    status: str = "pending"
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    output: str = ""
    error: str = ""

    # Token tracking with SDK compliance
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0      # NEW: Separate cache read
    cache_creation_tokens: int = 0  # NEW: Separate cache creation
    tool_calls: int = 0

    # NEW: Message ID deduplication
    processed_message_ids: Set[str] = field(default_factory=set)

    # NEW: Authoritative cost from SDK
    total_cost_usd: Optional[float] = None
```

### Fixed Token Processing Method

```python
def _try_parse_json_token_usage(self, line: str, status: InstanceStatus) -> bool:
    """SDK-compliant token usage parsing with message ID deduplication"""
    line = line.strip()
    if not line.startswith('{'):
        return False

    try:
        json_data = json.loads(line)

        # Extract message ID for deduplication
        message_id = (
            json_data.get('id') or
            json_data.get('message', {}).get('id')
        )

        if message_id:
            # SDK Rule: Skip if already processed this message ID
            if message_id in status.processed_message_ids:
                logger.debug(f"Skipping duplicate message ID: {message_id}")
                return True

            # Mark as processed
            status.processed_message_ids.add(message_id)

        # Process usage data (only once per message ID)
        usage_data = None
        if 'usage' in json_data:
            usage_data = json_data['usage']
        elif 'message' in json_data and 'usage' in json_data['message']:
            usage_data = json_data['message']['usage']

        if usage_data and isinstance(usage_data, dict):
            # Use assignment (=) not accumulation (+=) for same-ID messages
            if 'input_tokens' in usage_data:
                status.input_tokens = max(status.input_tokens, int(usage_data['input_tokens']))
            if 'output_tokens' in usage_data:
                status.output_tokens = max(status.output_tokens, int(usage_data['output_tokens']))

            # Separate cache types for accurate billing
            if 'cache_read_input_tokens' in usage_data:
                status.cache_read_tokens = max(status.cache_read_tokens, int(usage_data['cache_read_input_tokens']))
            if 'cache_creation_input_tokens' in usage_data:
                status.cache_creation_tokens = max(status.cache_creation_tokens, int(usage_data['cache_creation_input_tokens']))

            # Use authoritative total when available
            if 'total_tokens' in usage_data:
                total = int(usage_data['total_tokens'])
                status.total_tokens = max(status.total_tokens, total)

            # Store authoritative cost if available
            if 'total_cost_usd' in usage_data:
                status.total_cost_usd = float(usage_data['total_cost_usd'])

            return True

        # Handle tool calls with same ID deduplication
        if message_id and 'type' in json_data:
            if json_data['type'] in ['tool_use', 'tool_call', 'tool_execution']:
                # Only count tools once per message ID
                status.tool_calls += 1
                return True

        return False

    except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
        logger.debug(f"JSON parsing failed for line: {e}")
        return False
```

### Updated Cost Calculation

```python
def _calculate_cost(self, status: InstanceStatus) -> float:
    """Calculate cost with current Claude 3.5 Sonnet pricing and proper cache handling"""

    # Use authoritative cost if available (preferred)
    if status.total_cost_usd is not None:
        return status.total_cost_usd

    # Fallback calculation with current pricing
    # Claude 3.5 Sonnet current rates (verify these)
    input_cost = (status.input_tokens / 1_000_000) * 3.00    # $3 per M input
    output_cost = (status.output_tokens / 1_000_000) * 15.00  # $15 per M output

    # Cache costs (differentiated by type)
    cache_read_cost = (status.cache_read_tokens / 1_000_000) * 0.30      # $0.30 per M cache read
    cache_creation_cost = (status.cache_creation_tokens / 1_000_000) * 3.75  # $3.75 per M cache creation (25% of input rate)

    return input_cost + output_cost + cache_read_cost + cache_creation_cost
```

## Implementation Priority

1. **CRITICAL**: Add message ID deduplication to prevent double-charging
2. **HIGH**: Separate cache read vs creation tokens for accurate billing
3. **HIGH**: Use authoritative `total_cost_usd` when available from final result
4. **MEDIUM**: Update to current Claude pricing rates
5. **MEDIUM**: Apply max() instead of += for same-ID message processing

## Testing Strategy

1. **Unit Tests**: Create test cases with duplicate message IDs to verify deduplication
2. **Integration Tests**: Compare calculated costs against SDK's authoritative `total_cost_usd`
3. **Billing Validation**: Test against known conversation costs to verify accuracy

## Business Impact

- **Risk**: Current implementation may overcharge customers due to double-counting
- **Compliance**: Violates Claude SDK billing best practices
- **Trust**: Inaccurate billing could damage customer relationships
- **Financial**: Could result in revenue disputes or refunds

## Related Documentation

- [Claude Code SDK: Tracking Costs and Usage](https://docs.anthropic.com/en/docs/claude-code/sdk/tracking-costs-and-usage)
- [Claude Code TypeScript SDK Reference](https://docs.anthropic.com/en/docs/claude-code/typescript-sdk-reference)

---

**Next Steps**: Implement the recommended changes and validate against SDK examples before deploying to production.