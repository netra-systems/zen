# Multi-Agent Team Prompt: UVS Action Plan Enhancement v3

## 📚 CRITICAL: Required Reading Before Starting

### Primary Source of Truth
**MUST READ FIRST**: [`../../UVS_REQUIREMENTS.md`](../../UVS_REQUIREMENTS.md) - This is the authoritative specification for UVS implementation.

### Coordination with Other Teams
**If any confusion or conflicts arise**, read the other agent team prompts in this directory:
- `02_reporting_resilience_prompt.md` - ReportingSubAgent enhancements
- `03_supervisor_orchestration_prompt.md` - Supervisor simplification

These prompts work together - understanding all three ensures consistent implementation.

## Team Mission
Enhance the ActionPlanBuilder to integrate with the Unified User Value System (UVS), ensuring action plans always deliver value to users, even with incomplete data or agent failures.

## Team Composition & Roles

### 1. Principal Engineer (Coordinator)
- **Role**: Overall strategy, architecture decisions, and synthesis
- **Responsibilities**: 
  - Analyze UVS requirements and existing ActionPlanBuilder implementation
  - Design integration approach that maintains SSOT compliance
  - Coordinate between specialized agents
  - Final integration and validation

### 2. Product Manager Agent
- **Role**: Define business value and user outcomes
- **Responsibilities**:
  - Define BVJ (Business Value Justification) for UVS integration
  - Ensure "CHAT IS KING" principle is maintained
  - Validate that all scenarios deliver user value
  - Create success criteria metrics

### 3. Implementation Agent  
- **Role**: Execute code changes with SSOT compliance
- **Responsibilities**:
  - Enhance ActionPlanBuilder with UVS fallback mechanisms
  - Implement three-tier response system (full/partial/guidance)
  - Ensure proper error handling and resilience
  - Maintain existing test compatibility

### 4. QA/Security Agent
- **Role**: Comprehensive testing and validation
- **Responsibilities**:
  - Test all failure scenarios (no data, partial data, exceptions)
  - Verify WebSocket event continuity
  - Validate user isolation and context handling
  - Security audit for data leakage

## Context & Requirements

### Core UVS Principles
```python
# From UVS_REQUIREMENTS.md
ONLY_2_AGENTS_REQUIRED = ["triage", "reporting"]  # Everything else is optional
ALWAYS_DELIVER_VALUE = True  # Never return empty/error responses
DYNAMIC_WORKFLOW = True  # Adapt based on available data
```

### Current ActionPlanBuilder State
```python
class ActionPlanBuilder:
    """Already SSOT compliant with:
    - User context isolation
    - Unified JSON handling  
    - Retry mechanisms
    - Cache integration
    """
    
    def __init__(self, user_context, cache_manager=None):
        # Existing implementation is good
        pass
```

### Required Enhancements

#### 1. Dynamic Plan Generation Based on Data Availability
```python
async def generate_adaptive_plan(self, context: UserExecutionContext) -> ActionPlanResult:
    """Generate plan that adapts to available data"""
    
    data_state = self._assess_data_availability(context)
    
    if data_state == DataState.SUFFICIENT:
        # Full optimization plan
        return await self._generate_full_plan(context)
    elif data_state == DataState.PARTIAL:
        # Partial analysis + data collection steps
        return await self._generate_hybrid_plan(context)
    else:
        # Pure guidance plan
        return await self._generate_guidance_plan(context)
```

#### 2. Fallback Plan Templates
```python
FALLBACK_PLAN_TEMPLATES = {
    'no_data': {
        'plan_steps': [
            PlanStep(
                step_number=1,
                action="Understand your AI usage patterns",
                details="Let's explore your current AI infrastructure",
                expected_outcome="Clear understanding of optimization needs"
            ),
            PlanStep(
                step_number=2,
                action="Collect usage data",
                details="I'll guide you through data collection",
                expected_outcome="Baseline metrics for analysis"
            )
        ],
        'summary': "Let's start by understanding your AI usage",
        'next_steps': ["Share any usage data", "Describe your use cases"]
    },
    'partial_data': {
        # Similar structure for partial data scenario
    }
}
```

#### 3. Integration with ReportingSubAgent
```python
# ActionPlanBuilder must provide plans that ReportingSubAgent can use
def ensure_reporting_compatibility(self, plan: ActionPlanResult) -> ActionPlanResult:
    """Ensure plan has all fields needed by ReportingSubAgent"""
    
    # Always include next_steps
    if not plan.next_steps:
        plan.next_steps = self._generate_next_steps(plan)
    
    # Always include user_guidance
    if not plan.user_guidance:
        plan.user_guidance = self._generate_user_guidance(plan)
    
    return plan
```

## Implementation Approach

### Phase 1: Analysis (Principal + PM)
1. Review existing ActionPlanBuilder implementation
2. Map all failure points where UVS must intervene
3. Define success metrics for each scenario
4. Create BVJ for the enhancement

### Phase 2: Design (Principal + Implementation)
1. Design fallback hierarchy for plan generation
2. Create template system for guidance plans
3. Define data assessment logic
4. Plan WebSocket event integration

### Phase 3: Implementation (Implementation Agent)
1. Add `DataState` enum and assessment logic
2. Implement three-tier plan generation
3. Add fallback templates
4. Enhance error handling with UVS patterns

### Phase 4: Testing (QA Agent)
1. Test no-data scenario
2. Test partial-data scenario  
3. Test exception handling
4. Verify WebSocket events still fire
5. Load test with concurrent users

## Success Criteria

### Must Have (Week 1)
✅ ActionPlanBuilder never returns empty plans  
✅ Three-tier response system works  
✅ Fallback templates provide value  
✅ Existing tests still pass  
✅ WebSocket events unchanged  
✅ User isolation maintained  

### Nice to Have (Week 2+)
- Sophisticated data collection guidance
- Industry-specific plan templates
- Multi-turn context for plan refinement
- A/B testing of plan effectiveness

## Testing Scenarios

### Scenario 1: No Data Available
```python
async def test_no_data_generates_guidance_plan():
    context = UserExecutionContext()  # Empty context
    builder = ActionPlanBuilder(context.to_dict())
    plan = await builder.generate_adaptive_plan(context)
    
    assert plan is not None
    assert plan.plan_steps
    assert plan.next_steps
    assert "collect" in plan.summary.lower() or "guide" in plan.summary.lower()
```

### Scenario 2: LLM Failure
```python
async def test_llm_failure_uses_template():
    builder = ActionPlanBuilder()
    # Simulate LLM failure
    with patch('llm_call', side_effect=Exception("LLM Error")):
        plan = await builder.process_llm_response("", "test_run")
    
    assert plan is not None
    assert plan.plan_steps  # Should use fallback template
```

### Scenario 3: Partial Data
```python
async def test_partial_data_hybrid_plan():
    context = UserExecutionContext()
    context.metadata['data_result'] = {'partial': True}
    
    builder = ActionPlanBuilder(context.to_dict())
    plan = await builder.generate_adaptive_plan(context)
    
    assert "analyze" in str(plan.plan_steps)
    assert "collect" in str(plan.plan_steps)  # Both analysis and collection
```

## Code Locations & Files

### Primary Files to Modify
- `netra_backend/app/agents/actions_goals_plan_builder.py` - Main enhancement target
- `netra_backend/app/agents/state.py` - May need new fields for UVS

### Integration Points
- `netra_backend/app/agents/supervisor.py` - Uses ActionPlanBuilder
- `netra_backend/app/agents/triage/unified_triage_agent.py` - Provides data assessment
- `netra_backend/app/agents/reporting/reporting_subagent.py` - Consumes plans

### Test Files
- `netra_backend/tests/mission_critical/test_action_plan_builder_ssot.py` - Existing tests
- Create: `netra_backend/tests/unit/test_action_plan_uvs.py` - New UVS tests

## CRITICAL Constraints

### DO NOT Change
- WebSocket event architecture
- User isolation patterns  
- SSOT compliance structures
- Existing public APIs
- Tool architecture

### MUST Maintain
- All existing tests passing
- Performance (no degradation)
- Memory usage (no leaks)
- Concurrent user support
- Error resilience

## Deliverables Checklist

- [ ] Enhanced ActionPlanBuilder with UVS integration
- [ ] Fallback plan templates
- [ ] Data assessment logic
- [ ] Unit tests for all scenarios
- [ ] Integration tests with ReportingSubAgent
- [ ] Performance validation
- [ ] Documentation updates
- [ ] Migration guide (if needed)

## Team Coordination Protocol

1. **Principal** reads all UVS docs and existing code
2. **PM** creates BVJ and defines success metrics
3. **Principal** designs integration approach
4. **Implementation** executes changes in atomic commits
5. **QA** validates all scenarios
6. **Principal** performs final integration
7. **Team** reviews and documents learnings

## Remember: SIMPLICITY IS KEY

The goal is NOT to rebuild the system but to enhance ActionPlanBuilder so it:
1. Never fails to provide a plan
2. Adapts to available data
3. Always delivers user value
4. Maintains all existing functionality

This is about making the action planning bulletproof while keeping the implementation simple and maintainable.