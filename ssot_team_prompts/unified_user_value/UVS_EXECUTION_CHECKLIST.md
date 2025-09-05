# UVS Execution Checklist - Parallel Team Coordination

## Phase 1: Foundation (Day 1)
**3 Claude instances running in parallel**

### Terminal 1 - Product Manager
- [ ] Open new Claude instance
- [ ] Copy entire contents of `PROMPT_1_UVS_PM_REQUIREMENTS.md`
- [ ] Let agent complete all deliverables:
  - [ ] User journey maps created
  - [ ] Loop transition matrix defined
  - [ ] Value metrics established
  - [ ] Integration requirements documented
- [ ] Save all outputs to `deliverables/phase1/pm/`
- [ ] Mark complete in team coordination channel

### Terminal 2 - System Architect  
- [ ] Open new Claude instance
- [ ] Copy entire contents of `PROMPT_2_UVS_ARCHITECTURE_DESIGN.md`
- [ ] Let agent complete all deliverables:
  - [ ] System architecture diagram created
  - [ ] Loop state machine defined
  - [ ] API specifications written
  - [ ] Integration diagrams completed
  - [ ] Data flow diagrams created
  - [ ] Error recovery flows documented
  - [ ] Performance specifications defined
- [ ] Save all outputs to `deliverables/phase1/architecture/`
- [ ] Mark complete in team coordination channel

### Terminal 3 - QA Engineer
- [ ] Open new Claude instance
- [ ] Copy entire contents of `PROMPT_3_UVS_QA_TESTING.md`
- [ ] Let agent complete all deliverables:
  - [ ] Test strategy document created
  - [ ] Loop test scenarios written
  - [ ] Value level test cases defined
  - [ ] Checkpoint test suite created
  - [ ] Integration test plan completed
  - [ ] Regression prevention tests added
  - [ ] Performance benchmarks established
- [ ] Save all outputs to `deliverables/phase1/qa/`
- [ ] Mark complete in team coordination channel

## Phase 1 Validation Gate
**Before proceeding to Phase 2:**
- [ ] All Phase 1 teams completed
- [ ] Outputs reviewed for consistency
- [ ] Any conflicts resolved
- [ ] Integration points verified
- [ ] Proceed/No-Go decision made

## Phase 2: Implementation (Day 2)
**3 Claude instances running in parallel**

### Terminal 1 - Core Implementation
- [ ] Open new Claude instance
- [ ] Copy entire contents of `PROMPT_4_UVS_CORE_IMPLEMENTATION.md`
- [ ] Provide Phase 1 outputs as context if needed
- [ ] Let agent complete implementation:
  - [ ] ReportingSubAgent enhanced
  - [ ] LoopPatternDetector implemented
  - [ ] ProgressiveValueCalculator created
  - [ ] ValueLevel enum defined
  - [ ] Error recovery implemented
  - [ ] Unit tests written
  - [ ] Integration verified
- [ ] Verify no SSOT violations
- [ ] Run unit tests
- [ ] Mark complete in team coordination channel

### Terminal 2 - Checkpoint & DataHelper
- [ ] Open new Claude instance
- [ ] Copy entire contents of `PROMPT_5_UVS_CHECKPOINT_DATAHELPER.md`
- [ ] Provide Phase 1 outputs as context if needed
- [ ] Let agent complete implementation:
  - [ ] UVSCheckpointManager created
  - [ ] ContextPreserver implemented
  - [ ] DataHelperCoordinator created
  - [ ] Redis integration completed
  - [ ] Multi-session logic tested
  - [ ] Data request generation working
  - [ ] Integration tests passing
- [ ] Verify checkpoint persistence
- [ ] Test multi-session continuity
- [ ] Mark complete in team coordination channel

### Terminal 3 - Workflow Integration
- [ ] Open new Claude instance
- [ ] Copy entire contents of `PROMPT_6_UVS_WORKFLOW_INTEGRATION.md`
- [ ] Provide Phase 1 outputs as context if needed
- [ ] Let agent complete integration:
  - [ ] WorkflowOrchestrator updated
  - [ ] Dynamic step injection added
  - [ ] Fallback routing implemented
  - [ ] Legacy code identified
  - [ ] Migration executed
  - [ ] All references updated
  - [ ] WebSocket events verified
- [ ] Run integration tests
- [ ] Verify WebSocket events
- [ ] Mark complete in team coordination channel

## Phase 2 Validation Gate
- [ ] All Phase 2 teams completed
- [ ] Code review conducted
- [ ] Integration points tested
- [ ] No merge conflicts
- [ ] All tests passing

## Phase 3: Integration Testing (Day 3)

### Combined Testing
- [ ] Merge all branches
- [ ] Resolve any conflicts
- [ ] Run full test suite:
  ```bash
  python tests/unified_test_runner.py --all --real-services
  ```
- [ ] Run WebSocket event tests:
  ```bash
  python tests/mission_critical/test_websocket_agent_events_suite.py
  ```
- [ ] Run UVS-specific tests:
  ```bash
  python tests/e2e/test_uvs_loops.py
  ```

### Loop Validation
- [ ] Test IMAGINATION loop with no data
- [ ] Test DATA_DISCOVERY loop with partial data
- [ ] Test REFINEMENT loop with follow-up
- [ ] Test CONTEXT loop with scope change
- [ ] Test COMPLETION with full data
- [ ] Test multi-session checkpoint recovery

### Value Level Validation
- [ ] Test FULL value delivery (90%+ data)
- [ ] Test STANDARD value delivery (70-90% data)
- [ ] Test BASIC value delivery (40-70% data)
- [ ] Test MINIMAL value delivery (10-40% data)
- [ ] Test FALLBACK value delivery (<10% data)

### Error Recovery Validation
- [ ] Test MissingDataError recovery
- [ ] Test ProcessingError recovery
- [ ] Test LLM failure recovery
- [ ] Test serialization error recovery
- [ ] Test complete failure fallback

## Phase 4: Staging Deployment (Day 4)

### Pre-Deployment
- [ ] All tests passing locally
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Migration plan reviewed
- [ ] Rollback plan prepared

### Deployment
- [ ] Deploy to staging environment:
  ```bash
  python scripts/deploy_to_gcp.py --project netra-staging --build-local
  ```
- [ ] Verify services healthy
- [ ] Run smoke tests
- [ ] Test user journeys
- [ ] Monitor for errors

### Post-Deployment
- [ ] Monitor error rates
- [ ] Check checkpoint persistence
- [ ] Verify multi-session continuity
- [ ] Test DataHelper triggering
- [ ] Validate WebSocket events

## Phase 5: Production Readiness (Day 5)

### Performance Validation
- [ ] Loop detection <2s
- [ ] Value calculation <1s
- [ ] Checkpoint save <500ms
- [ ] Report generation meets SLA
- [ ] Memory usage stable

### Documentation
- [ ] Update user documentation
- [ ] Create ops runbook
- [ ] Document monitoring queries
- [ ] Update API documentation
- [ ] Create troubleshooting guide

### Sign-offs
- [ ] Engineering approval
- [ ] QA approval
- [ ] Product approval
- [ ] Operations approval
- [ ] Security review

## Success Criteria

### Technical Success
- [ ] Zero reporting crashes in 24 hours
- [ ] 100% value delivery rate
- [ ] All tests passing
- [ ] WebSocket events working
- [ ] Checkpoints persisting

### Business Success
- [ ] Users receiving value with no data
- [ ] Multi-session journeys working
- [ ] Data collection guidance helpful
- [ ] Progressive insights delivered
- [ ] User satisfaction improved

## Rollback Plan

If issues arise:
1. [ ] Revert WorkflowOrchestrator changes
2. [ ] Restore original ReportingSubAgent
3. [ ] Clear checkpoint cache
4. [ ] Notify users of temporary reversion
5. [ ] Debug and fix issues
6. [ ] Re-attempt deployment

## Communication Plan

### Daily Standups
- Phase progress
- Blockers identified
- Help needed
- Next steps

### Coordination Channel
- Real-time updates
- Quick questions
- Blocker alerts
- Completion notifications

### Documentation
- All outputs saved
- Decisions documented
- Issues tracked
- Lessons learned captured

## Notes

- Each prompt is self-contained - no need to provide additional context
- Agents will create all necessary files and tests
- Let agents run to completion before intervening
- Save all outputs for reference
- Coordinate through shared channel to avoid conflicts

## Emergency Contacts

- Technical Lead: Review architecture decisions
- Product Owner: Clarify requirements
- DevOps: Deployment issues
- QA Lead: Test failures

Remember: The goal is iterative value delivery - users should ALWAYS get something useful, even with zero data!