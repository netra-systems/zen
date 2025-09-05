# ActionPlanBuilder UVS Integration Guide

## Overview
This guide documents the Unified User Value System (UVS) enhancements to the ActionPlanBuilder, ensuring action plans ALWAYS deliver value to users, even with incomplete data or agent failures.

## Key Features

### 1. Three-Tier Response System
The ActionPlanBuilder now adapts to available data with three response tiers:

- **Full Optimization Plans** (Sufficient Data)
  - Complete analysis with specific recommendations
  - Detailed implementation steps
  - Cost/benefit analysis
  
- **Hybrid Plans** (Partial Data) 
  - Analysis of available data
  - Identification of data gaps
  - Guided collection for missing information
  
- **Guidance Plans** (No Data)
  - Educational content about optimization
  - Step-by-step data collection guidance
  - Next steps for getting started

### 2. Guaranteed Value Delivery
- **Never returns empty plans** - Always provides actionable content
- **Graceful degradation** - Adapts to available resources
- **Error recovery** - Fallback templates for any failure scenario

### 3. ReportingSubAgent Compatibility
All plans include required fields for downstream processing:
- `next_steps` - Always populated with actionable items
- `user_guidance` - Context-appropriate help
- `metadata.uvs_enabled` - UVS tracking

## Implementation

### Using the UVS-Enhanced ActionPlanBuilder

```python
from netra_backend.app.agents.actions_goals_plan_builder_uvs import (
    ActionPlanBuilderUVS,
    create_uvs_action_plan_builder
)

# Create UVS-enhanced builder
builder = create_uvs_action_plan_builder(
    user_context={'user_id': 'test_user'},
    cache_manager=cache_manager  # Optional
)

# Generate adaptive plan based on available data
result = await builder.generate_adaptive_plan(context)

# Result is GUARANTEED to have:
# - result.plan_steps (never empty)
# - result.action_plan_summary
# - result.metadata.custom_fields['next_steps']
# - result.metadata.custom_fields['uvs_mode'] 
# - result.metadata.custom_fields['data_state']
```

### Data State Assessment

The builder automatically assesses data availability:

```python
from netra_backend.app.agents.actions_goals_plan_builder_uvs import DataState

# DataState enum values:
# - SUFFICIENT: All required data available
# - PARTIAL: Some data available
# - INSUFFICIENT: No or minimal data
# - ERROR: Error accessing data
```

## Integration with ActionsToMeetGoalsSubAgent

To integrate UVS into the existing agent:

```python
# In ActionsToMeetGoalsSubAgent.__init__
from netra_backend.app.agents.actions_goals_plan_builder_uvs import ActionPlanBuilderUVS

self.action_plan_builder = ActionPlanBuilderUVS()  # Instead of ActionPlanBuilder

# In execute_core_logic or _generate_action_plan
action_plan_result = await self.action_plan_builder.generate_adaptive_plan(context)
```

## Fallback Templates

The system includes comprehensive fallback templates for:

### No Data Scenario
```python
{
    'plan_steps': [
        'Understand your AI usage patterns',
        'Collect baseline usage data', 
        'Identify quick optimization wins'
    ],
    'next_steps': [
        'Share any usage data',
        'Describe your use cases',
        'Tell me your optimization goals'
    ]
}
```

### Partial Data Scenario
```python
{
    'plan_steps': [
        'Analyze available data',
        'Identify and fill data gaps',
        'Generate optimization recommendations'
    ],
    'next_steps': [
        'Provide additional data identified',
        'Review initial insights',
        'Prepare to implement quick wins'
    ]
}
```

### Error Recovery Scenario
```python
{
    'plan_steps': [
        'Diagnose the issue',
        'Manual optimization assessment'
    ],
    'next_steps': [
        'Try refreshing and resubmitting',
        'Describe optimization goals',
        'Share specific concerns'
    ]
}
```

## Testing

### Key Test Scenarios

1. **Empty Context Test**
```python
async def test_empty_context():
    context = UserExecutionContext(
        user_id="test",
        thread_id="test", 
        run_id="test",
        metadata={}  # Empty!
    )
    result = await builder.generate_adaptive_plan(context)
    assert result is not None
    assert result.plan_steps  # Never empty
```

2. **Failure Recovery Test**
```python
async def test_llm_failure():
    with patch.object(builder, '_get_llm_response_safe', side_effect=Exception):
        result = await builder.generate_adaptive_plan(context)
        assert result is not None  # Still returns value
```

3. **Data State Validation**
```python
def test_data_assessment():
    context.metadata = {'data_result': {}}
    uvs_context = builder._assess_data_availability(context)
    assert uvs_context.data_state == DataState.PARTIAL
```

## Migration Checklist

- [ ] Replace `ActionPlanBuilder` imports with `ActionPlanBuilderUVS`
- [ ] Update instantiation to use `create_uvs_action_plan_builder()`
- [ ] Change `process_llm_response()` calls to `generate_adaptive_plan()`
- [ ] Access `next_steps` from `metadata.custom_fields['next_steps']`
- [ ] Test with empty/partial data scenarios
- [ ] Verify ReportingSubAgent receives required fields
- [ ] Update monitoring to track UVS mode distribution

## Performance Considerations

- **No performance degradation** - Fallback templates are lightweight
- **Cache-friendly** - Supports existing cache infrastructure
- **Concurrent-safe** - Maintains user isolation patterns

## Monitoring & Metrics

Track these metrics to measure UVS effectiveness:

```python
# Distribution of data states
metrics.increment('action_plan.data_state', tags={'state': uvs_context.data_state.value})

# Fallback usage
metrics.increment('action_plan.uvs_mode', tags={'mode': result.metadata.custom_fields['uvs_mode']})

# Recovery from errors
metrics.increment('action_plan.error_recovery', tags={'recovered': True})
```

## Backward Compatibility

The UVS enhancement maintains full backward compatibility:

1. **Original `process_llm_response()` still works** - Now with UVS fallbacks
2. **Static methods preserved** - For legacy code
3. **All existing tests pass** - No breaking changes

## Support & Documentation

- Implementation: `netra_backend/app/agents/actions_goals_plan_builder_uvs.py`
- Tests: `netra_backend/tests/unit/test_action_plan_uvs.py`  
- UVS Requirements: `UVS_REQUIREMENTS.md`
- Agent Team Prompts: `agent_team_prompts/01_action_plan_enhancement_prompt.md`

## Success Criteria

The UVS integration is successful when:

✅ ActionPlanBuilder never returns empty plans  
✅ Three-tier response system works correctly  
✅ All failure scenarios produce valuable output  
✅ Existing tests continue to pass  
✅ ReportingSubAgent receives all required fields  
✅ User isolation is maintained  
✅ WebSocket events fire correctly  

## Next Steps

1. Deploy to staging environment
2. Monitor data_state distribution
3. Collect user feedback on guidance quality
4. Iterate on fallback templates based on usage
5. Consider A/B testing different template variations