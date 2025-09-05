# UVS Execution Checklist - ReportingSubAgent Enhancement

## Master Requirements
**See [`../../UVS_REQUIREMENTS.md`](../../UVS_REQUIREMENTS.md) for complete specifications.**

## 🚨 Week 1: Critical Path (MUST COMPLETE)

### Day 1-2: ReportingSubAgent Enhancement
- [ ] **Modify ReportingSubAgent.execute()**
  - [ ] Add comprehensive try/catch wrapper
  - [ ] Implement determine_report_mode() method
  - [ ] Add FULL_REPORT path (existing logic)
  - [ ] Add PARTIAL_REPORT path
  - [ ] Add GUIDANCE_REPORT path
  - [ ] Add ultimate fallback in except block

- [ ] **Implement Helper Methods**
  - [ ] generate_next_steps() - ALWAYS returns actionable steps
  - [ ] generate_partial_report() - Works with incomplete data
  - [ ] generate_guidance_report() - Helps users start
  - [ ] has_sufficient_data() - Determines data availability

- [ ] **Ensure Backward Compatibility**
  - [ ] Test existing full data flow works unchanged
  - [ ] Verify WebSocket events still fire
  - [ ] Check existing response format maintained

### Day 3: Minimal Integration Updates
- [ ] **Update WorkflowOrchestrator (MINIMAL)**
  - [ ] Add try/catch around each agent.execute()
  - [ ] Log errors but continue execution
  - [ ] Let ReportingSubAgent handle failures
  - [ ] NO other changes to orchestration logic

### Day 4-5: Testing & Validation
- [ ] **Unit Tests**
  - [ ] Test no data scenario → guidance report
  - [ ] Test partial data → partial report
  - [ ] Test full data → normal report
  - [ ] Test exception handling → fallback report
  
- [ ] **Integration Tests**
  - [ ] Test with failed DataAgent
  - [ ] Test with failed OptimizationAgent
  - [ ] Test complete pipeline success
  - [ ] Verify WebSocket events in all scenarios

- [ ] **E2E Tests**
  - [ ] User with no data gets guidance
  - [ ] User with CSV gets analysis
  - [ ] System handles all error cases

## Week 2: Enhancements (NICE TO HAVE)

### Multi-Turn Support
- [ ] Add thread_id support to context
- [ ] Implement context loading from previous turns
- [ ] Save report state for continuity
- [ ] Test conversation flows

### Data Collection Guidance
- [ ] Enhance data collection suggestions
- [ ] Add specific instructions per optimization type
- [ ] Integrate with DataHelperAgent output

## Week 3: Polish (OPTIONAL)

### Performance & Monitoring
- [ ] Add comprehensive logging
- [ ] Implement performance metrics
- [ ] Create monitoring dashboards
- [ ] Document troubleshooting guide

## Validation Commands

```bash
# Week 1 - Must Pass
python tests/unit/test_reporting_fallbacks.py
python tests/e2e/test_reporting_no_data.py
python tests/e2e/test_agent_pipeline.py --real-services

# Week 2 - Nice to Have  
python tests/integration/test_multi_turn.py
python tests/e2e/test_data_collection_guidance.py

# Week 3 - Optional
python tests/performance/test_reporting_speed.py
python tests/load/test_concurrent_reports.py
```

## Success Indicators - Week 1

| Metric | Target | Actual |
|--------|--------|--------|
| ReportingSubAgent crashes | 0 | [ ] |
| Requests with response | 100% | [ ] |
| Responses with next_steps | 100% | [ ] |
| WebSocket events working | Yes | [ ] |
| Existing flow unchanged | Yes | [ ] |

## Common Blockers & Solutions

| Blocker | Solution |
|---------|----------|
| Don't know what to return with no data | Return guidance questions |
| next_steps is empty | Hard-code fallback suggestions |
| WebSocket events stopped | Don't modify event code |
| Other agents need changes | They don't - only ReportingSubAgent |
| Complex orchestration needed | It's not - keep it simple |

## Critical Reminders

✅ **DO:** Focus ONLY on ReportingSubAgent  
✅ **DO:** Always return something meaningful  
✅ **DO:** Include next_steps in every response  
✅ **DO:** Test with zero data scenarios  

❌ **DON'T:** Change other agents  
❌ **DON'T:** Modify orchestration flow  
❌ **DON'T:** Alter WebSocket infrastructure  
❌ **DON'T:** Over-engineer the solution  

## Definition of Done - Week 1

- [ ] ReportingSubAgent NEVER crashes (0 exceptions in 24hrs)
- [ ] 100% of chat requests get a response
- [ ] Every response includes actionable next_steps
- [ ] Works with: no data, partial data, full data
- [ ] All existing tests still pass
- [ ] Deployed to staging and tested
- [ ] No regression in existing functionality

## Remember

**CHAT VALUE IS KING** - Users must ALWAYS get value from the chat interface.

This is a surgical enhancement to ReportingSubAgent, not a system redesign. Keep it simple, make it bulletproof, ship it fast.