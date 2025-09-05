# Unified User Value System (UVS) - Quick Reference

## Master Requirements
**See [`../../UVS_REQUIREMENTS.md`](../../UVS_REQUIREMENTS.md) for complete specifications.**

## What UVS Actually Is

The **Unified User Value System (UVS)** enhances **ONLY the ReportingSubAgent** to guarantee value delivery even with incomplete data. This is NOT a system rewrite.

**Business Priority: CHAT VALUE IS KING** - Users must ALWAYS get meaningful responses.

## What Changes (Week 1)

### ReportingSubAgent Enhancement
```python
class ReportingSubAgent(BaseAgent):
    """Enhanced to NEVER crash"""
    
    async def execute(self, context):
        try:
            # Normal report if data available
            if self.has_sufficient_data(context):
                return await self.generate_normal_report(context)
            else:
                # Fallback guidance if no data
                return await self.generate_fallback_report(context)
        except Exception as e:
            # Ultimate fallback - ALWAYS return value
            return {
                'report_type': 'guidance',
                'message': 'Let me help you get started',
                'next_steps': ['Share your data', 'Describe your use case']
            }
```

## What Stays The Same

- **UnifiedTriageAgent** - NO CHANGES
- **UnifiedDataAgent** - NO CHANGES
- **OptimizationAgent** - NO CHANGES
- **WorkflowOrchestrator** - Minimal error handling only
- **WebSocket Events** - Continue unchanged
- **Tool Architecture** - No modifications

## Three Simple Report Modes

1. **FULL_REPORT** - Has data + optimizations (normal flow)
2. **PARTIAL_REPORT** - Has some data (provide partial analysis)
3. **GUIDANCE_REPORT** - No data (help user get started)

## Week 1 Success Criteria

✅ ReportingSubAgent NEVER crashes  
✅ ALWAYS returns meaningful response  
✅ Works with existing pipeline  
✅ Every response has next_steps  
✅ Handles: no data, partial data, full data

## Testing Commands

```bash
# Test ReportingSubAgent resilience
python tests/unit/test_reporting_fallbacks.py

# Test with no data scenario
python tests/e2e/test_reporting_no_data.py

# Test existing flow still works
python tests/e2e/test_agent_pipeline.py --real-services
```

## Future Direction (NOT Week 1)

- Tool-based iteration (like Claude Code) - FUTURE
- Multi-turn context - Week 2
- Sophisticated data guidance - Week 2
- New agent types - NOT PLANNED

## Remember

**This is about making ReportingSubAgent bulletproof, not rebuilding the system.**

The existing agent pipeline continues to work. We're just ensuring the final report ALWAYS delivers value, even when prior agents fail or return no data.