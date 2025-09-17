# Tool Token Usage Enhancement

## Summary

Enhanced the zen orchestrator to track token usage per tool and include tool costs in total cost calculations, providing complete transparency into AI agent tool usage patterns and costs.

## Key Enhancements

### 1. **Per-Tool Token Tracking**
- **Token Capture**: Extracts token usage from tool execution responses
- **Tool Mapping**: Tracks token usage by specific tool name
- **Cumulative Tracking**: Accumulates tokens across multiple tool uses
- **Integration**: Works with both individual tool calls and batch tool executions

### 2. **Tool Cost Calculation**
- **Pricing Integration**: Tool tokens charged at model input token rate
- **Cost Breakdown**: Separate tool cost component in total cost calculation
- **Model-Aware**: Uses detected model pricing (Sonnet, Haiku, Opus)
- **Fallback Support**: Includes tool costs in legacy calculation methods

### 3. **Enhanced Tool Usage Table**
Now displays comprehensive tool usage details:

```
╔═══ TOOL USAGE DETAILS ═══╗
║ Tool Name            Uses     Tokens     Cost ($)   Used By
║ ────────────────────────────────────────────────────────────────────────
║ web_search           5        2,450      0.0074     instance1(3 uses, 1,200 tok), instance2(2 uses, 1,250 tok)
║ file_edit            8        1,890      0.0057     instance1(4 uses, 920 tok), instance3(4 uses, 970 tok)
║ bash_execute         3        890        0.0027     instance2(3 uses, 890 tok)
║ ────────────────────────────────────────────────────────────────────────
║ TOTAL                16       5,230      0.0158
╚══════════════════════════════════════════════════════════════════════════╝
```

### 4. **Comprehensive Cost Integration**
- **Total Cost**: Includes tool costs in all cost calculations
- **Status Reports**: Real-time cost tracking includes tool usage
- **Final Summary**: Complete cost breakdown with tool component
- **Pricing Engine**: Enhanced with tool cost calculation support

## Implementation Details

### **Data Structure Enhancements**

```python
@dataclass
class InstanceStatus:
    # Existing fields...
    tool_details: Dict[str, int] = None   # Tool name -> usage count
    tool_tokens: Dict[str, int] = None    # Tool name -> token usage
```

### **Token Parsing Enhancement**

```python
# Extract tool token usage from JSON responses
if 'usage' in json_data and isinstance(json_data['usage'], dict):
    tool_usage = json_data['usage']
    tool_tokens = tool_usage.get('total_tokens',
                tool_usage.get('input_tokens', 0) + tool_usage.get('output_tokens', 0))
```

### **Cost Calculation Integration**

```python
# Include tool tokens in pricing engine
cost_breakdown = self.pricing_engine.calculate_cost(
    usage_data,
    status.total_cost_usd,
    status.tool_tokens  # Include tool token costs
)
```

### **Pricing Engine Enhancement**

```python
def calculate_cost(self, usage_data: TokenUsageData,
                  authoritative_cost: Optional[float] = None,
                  tool_tokens: Optional[Dict[str, int]] = None) -> CostBreakdown:
    # Calculate tool costs based on token usage
    tool_cost = 0.0
    if tool_tokens:
        for tool_name, tokens in tool_tokens.items():
            # Tool tokens are charged at the same rate as input tokens for the model
            tool_cost += (tokens / 1_000_000) * model_pricing["input"]
```

## Enhanced Status Report Example

```
╔═══ STATUS REPORT [14:30:15] ═══╗
║ Total: 3 instances
║ Running: 1, Completed: 2, Failed: 0, Pending: 0
║ Tokens: 25.4K total, 3.2K cached | Median: 8.0K | Tools: 16
║ 💰 Cost: $0.0891 total, $0.0297 avg/instance | Pricing: Claude compliant
║
║ TOKEN BUDGET STATUS
║ Overall: ████████░░ 25.4K/50K tokens
║
║  Status   Name                     Model      Duration   Tokens   vs Med   Cache   Tools
║  ✅       data-processor           35sonnet   45.2s      12.8K    +60%     1.5K    8
║  ✅       code-analyzer            35sonnet   32.1s      8.4K     +5%      1.2K    5
║  🏃       report-generator         35sonnet   12.1s      4.2K     -48%     0.5K    3
╚══════════════════════════════════════════════════════════════════════════════════════╝

╔═══ TOOL USAGE DETAILS ═══╗
║ Tool Name            Uses     Tokens     Cost ($)   Used By
║ ────────────────────────────────────────────────────────────────────────
║ web_search           5        2,450      0.0074     data-processor(3 uses, 1,200 tok), code-analyzer(2 uses, 1,250 tok)
║ file_read            8        1,890      0.0057     data-processor(4 uses, 920 tok), code-analyzer(4 uses, 970 tok)
║ bash_execute         3        890        0.0027     report-generator(3 uses, 890 tok)
║ ────────────────────────────────────────────────────────────────────────
║ TOTAL                16       5,230      0.0158
╚══════════════════════════════════════════════════════════════════════════════════════╝
```

## Benefits

### **1. Complete Cost Transparency**
- **Full Picture**: Total cost now includes all tool usage
- **Tool ROI**: Understand which tools provide value vs cost
- **Budget Planning**: More accurate cost predictions including tool usage
- **Optimization**: Identify expensive tool patterns for optimization

### **2. Tool Usage Analytics**
- **Usage Patterns**: Track which tools are used most frequently
- **Token Efficiency**: Understand token cost per tool operation
- **Instance Analysis**: See which instances are tool-heavy vs lightweight
- **Cost Attribution**: Attribute total costs to specific tool usage

### **3. Enhanced Monitoring**
- **Real-time Tracking**: Live updates of tool costs during execution
- **Historical Analysis**: Track tool usage trends over time
- **Performance Metrics**: Tool efficiency and success rate tracking
- **Resource Planning**: Better understanding of tool resource requirements

### **4. Pricing Compliance**
- **Accurate Billing**: Tool tokens charged at correct model rates
- **Model-Aware**: Different tool costs for different Claude models
- **Documentation**: Full traceability of tool cost calculations
- **Audit Trail**: Complete record of tool usage and associated costs

## Future Enhancements

### **Potential Additions**
1. **Tool Success Rates**: Track tool execution success/failure rates
2. **Tool Performance**: Measure tool execution time and efficiency
3. **Tool Recommendations**: Suggest optimal tool usage patterns
4. **Cost Optimization**: Automated recommendations for cost reduction
5. **Tool Budgets**: Per-tool budget limits and warnings
6. **Historical Trends**: Tool usage pattern analysis over time

## Conclusion

The zen orchestrator now provides comprehensive tool token tracking and cost calculation, ensuring complete transparency into AI agent tool usage patterns and their associated costs. This enhancement makes zen ready for enterprise use where understanding and controlling tool costs is critical for budget management and ROI analysis.

Total cost calculations now include:
- Input tokens (model-specific rates)
- Output tokens (model-specific rates)
- Cache read tokens (10% of input rate)
- Cache creation tokens (25% or 100% premium)
- **Tool tokens (charged at input token rate)**

This provides a complete picture of AI agent operational costs for informed decision-making and optimization.