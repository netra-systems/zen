# Model Column Guide - Technical Reference

## Overview

The Model column in Zen's status display provides real-time visibility into which Claude model is actually processing each request. This guide explains the technical implementation, detection logic, and business value of this feature.

## Model Detection Architecture

### Detection Strategy

Zen implements automatic model detection through systematic analysis of Claude API responses. The detection engine examines multiple locations in the response data to identify the actual model used:

```python
# Primary detection locations (in priority order)
1. response_data.get('model')
2. response_data.get('model_name')
3. response_data.get('usage', {}).get('model')
4. response_data.get('message', {}).get('model')
5. response_data.get('metadata', {}).get('model')
```

### Model Name Normalization

The system handles various Claude model naming conventions:

| API Response | Normalized Display | Cost Calculation |
|-------------|-------------------|------------------|
| `claude-opus-4` | `opus4` | claude-opus-4 rates |
| `claude-3-5-sonnet` | `35sonnet` | claude-3-5-sonnet rates |
| `opus-4.1` | `opus41` | claude-opus-4.1 rates |
| `haiku-3.5` | `haiku35` | claude-haiku-3.5 rates |

### Fallback Behavior

When model detection fails:
- **Display**: Shows "unknown" in the Model column
- **Cost Calculation**: Defaults to `claude-3-5-sonnet` pricing (conservative fallback)
- **Logging**: Logs detection failure for troubleshooting

## Real-World Model Behavior Examples

### Example 1: Configuration vs Reality

**Your Configuration**: Claude Opus (premium model)
**Simple Request**: "What's 2+2?"
**Actual Model Used**: Claude Sonnet (detected automatically)
**Why**: Claude may route simple requests to more efficient models

**Status Display**:
```
║  Status   Name          Model      Duration  Cost      Tokens
║  ✅        simple-math   35sonnet   0m12s     $0.0001   45
```

### Example 2: Complex Task Escalation

**Your Configuration**: Claude Sonnet (standard model)
**Complex Request**: "Analyze this 10,000-line codebase and create architecture diagrams"
**Actual Model Used**: Claude Opus (detected automatically)
**Why**: Claude may escalate complex tasks to more capable models

**Status Display**:
```
║  Status   Name          Model    Duration  Cost      Tokens
║  🏃        code-analysis opus4    15m30s    $0.2450   18,567
```

## Business Value & Cost Implications

### Accurate Cost Tracking

The Model column enables precise cost tracking because:

1. **Pricing Variations**: Different models have dramatically different costs
   - Opus: $15/$75 per million tokens (input/output)
   - Sonnet: $3/$15 per million tokens (input/output)
   - Haiku: $0.8/$4 per million tokens (input/output)

2. **Budget Accuracy**: Budget calculations use actual model costs, not assumed costs

3. **Spend Optimization**: Identify when you're paying premium rates vs. standard rates

### Real-Time Insights

**Detection Logging Example**:
```
🤖 MODEL DETECTED: claude-opus-4 (was claude-3-5-sonnet)
💰 COST IMPACT: $0.15 → $0.75 per million output tokens (5x increase)
📊 BUDGET UPDATE: 45% → 78% of command budget used
```

## Implementation Details

### Detection Code Location

Model detection is implemented in `zen_orchestrator.py`:

```python
def _try_parse_json_token_usage(self, line: str, status: InstanceStatus) -> bool:
    # Parse JSON response from Claude
    json_data = json.loads(line)

    # Extract model information
    detected_model = self._extract_model_from_response(json_data)

    # Update if model changed
    if detected_model != status.model_used:
        logger.debug(f"🤖 MODEL DETECTED: {detected_model} (was {status.model_used})")
        status.model_used = detected_model
```

### Status Display Implementation

The Model column shows abbreviated model names for compact display:

```python
# Format model name for display (line 961)
model_short = status.model_used.replace('claude-', '').replace('-', '') if status.model_used else "unknown"
```

## Troubleshooting Model Detection

### Common Issues

1. **"unknown" Model Display**
   - **Cause**: API response doesn't contain model information
   - **Impact**: Uses default pricing for cost calculation
   - **Solution**: Usually resolves automatically on subsequent requests

2. **Unexpected Model Changes**
   - **Cause**: Claude's intelligent routing based on request complexity
   - **Impact**: Cost calculations may be higher/lower than expected
   - **Solution**: Normal behavior - indicates Claude's optimization

3. **Model Detection Lag**
   - **Cause**: Streaming responses may not include model info immediately
   - **Impact**: Initial display shows "unknown", updates when detected
   - **Solution**: Wait for complete response processing

## Integration with Cost Allocation

The Model column data feeds directly into Zen's cost allocation system:

- **Per-Instance Costs**: Calculated using detected model rates
- **Tool Cost Attribution**: Tool tokens charged at detected model's input rate
- **Cache Cost Accuracy**: Cache pricing uses actual model being cached
- **Budget Enforcement**: Budget limits calculated against actual model costs

For detailed cost calculation formulas, see [Cost_allocation.md](Cost_allocation.md).

---

**Reference**: This guide covers the model detection implementation in `zen_orchestrator.py` and its integration with Zen's cost tracking and budget management systems.

**Related Documentation**:
- [Cost_allocation.md](Cost_allocation.md) - Detailed cost calculation formulas
- [README.md](../README.md) - User-facing overview of Model column

**Last Updated**: 2025-01-17
**Issue Reference**: GitHub Issue #1322