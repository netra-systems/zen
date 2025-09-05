# Team A: PM Agent - Unified User Value System (UVS) Requirements

## COPY THIS ENTIRE PROMPT:

You are a Product Manager defining requirements for enhancing the EXISTING ReportingSubAgent class to be the core of the Unified User Value System (UVS) - ensuring it's resilient, crash-proof, and always delivers user value.

CRITICAL: We are NOT creating a new class. We are enhancing the EXISTING `ReportingSubAgent` class located at `netra_backend/app/agents/reporting_sub_agent.py` to be the SINGLE SOURCE OF TRUTH for all user value delivery in the UVS.

## MANDATORY FIRST ACTIONS:

1. READ `reporting_crash_audit_and_plan.md` - Complete crash analysis
2. READ `netra_backend/app/agents/reporting_sub_agent.py` - Current implementation
3. READ `CLAUDE.md` Section 2.1 - SSOT principles
4. READ `DEFINITION_OF_DONE_CHECKLIST.md` - Reporting section
5. ANALYZE current crash points and failure modes

## YOUR PRODUCT REQUIREMENTS TASK:

Define comprehensive requirements for making ReportingSubAgent the foundation of UVS:

### 1. Core Requirements Definition

**MUST MAINTAIN:**
- Class name: `ReportingSubAgent` (NO CHANGES)
- Location: `netra_backend/app/agents/reporting_sub_agent.py`
- Base class: Inherits from `BaseAgent`
- All existing WebSocket events
- Factory pattern compatibility

**MUST ADD:**
- Progressive report generation (FULL → STANDARD → BASIC → MINIMAL)
- Checkpoint system for partial progress
- Automatic data_helper fallback triggering
- Graceful degradation on missing data
- Retry logic with exponential backoff
- Circuit breakers for error cascade prevention

### 2. User Stories to Define

```markdown
AS A user
WHEN the reporting agent encounters missing data
THEN I should receive a partial report with available information
AND the system should automatically request missing data via data_helper

AS A user  
WHEN the reporting agent experiences a transient failure
THEN the system should automatically retry with backoff
AND provide me with progress updates during recovery

AS A user
WHEN some analysis results are unavailable
THEN I should receive the best possible report from available data
AND see clear indication of what information is missing
```

### 3. Acceptance Criteria

**Report Generation Levels:**
- FULL: All 4 results present (action_plan, optimizations, data, triage)
- STANDARD: 3 results present (missing action_plan is OK)
- BASIC: 2 results present (data + triage minimum)
- MINIMAL: 1 result present (triage only)
- FALLBACK: No results (user request echo only)

**Checkpoint Requirements:**
- Save progress after each section generation
- Resume from last checkpoint on failure
- TTL of 1 hour for checkpoint data
- Atomic checkpoint operations

**Fallback Behavior:**
- Detect missing required data within 100ms
- Trigger data_helper within 500ms of detection
- Generate data request report as output
- Preserve partial results for future use

### 4. Technical Constraints

**SSOT Compliance:**
- Single ReportingSubAgent class only
- No duplicate reporting logic anywhere
- All reporting MUST go through this class
- Factory pattern for instance creation

**Performance Requirements:**
- Checkpoint overhead < 100ms
- Recovery time < 5 seconds
- Memory usage < 100MB per report
- Support 10+ concurrent reports

### 5. Migration Requirements

**Code Updates Required:**
- Update ALL references to reporting across codebase
- Remove ANY alternative reporting implementations
- Update imports in all consuming modules
- Migrate tests to use enhanced ReportingSubAgent

**Legacy Code Removal:**
- Delete any duplicate reporting logic
- Remove old fallback mechanisms
- Clean up unused reporting utilities
- Archive deprecated report formats

### 6. Business Metrics

Define success metrics:
- Crash rate: Current 10-15% → Target <1%
- Output success: Current 85% → Target 99.9%
- Recovery time: Current N/A → Target <5 sec
- User satisfaction: Current 70% → Target 95%

### 7. Risk Assessment

Identify and mitigate risks:
- **Risk**: Breaking existing workflows
  **Mitigation**: Feature flags for new behavior
  
- **Risk**: Performance degradation
  **Mitigation**: Async checkpoint operations
  
- **Risk**: Memory leaks from checkpoints
  **Mitigation**: TTL and size limits

### 8. Documentation Requirements

- Update API documentation
- Create runbook for failure scenarios
- Document checkpoint format
- Provide migration guide for consumers

## DELIVERABLES:

1. **requirements.json** with structured requirements
2. **user_stories.md** with complete scenarios
3. **acceptance_tests.py** with test definitions
4. **migration_plan.md** with step-by-step process

## VALIDATION CHECKLIST:

- [ ] Requirements maintain SSOT (single ReportingSubAgent class)
- [ ] All crash scenarios addressed
- [ ] Data_helper integration defined
- [ ] Performance targets specified
- [ ] Migration path clear
- [ ] Legacy code removal planned
- [ ] Business value quantified
- [ ] Risks identified and mitigated

## OUTPUT FORMAT:

```json
{
  "requirements": {
    "core": [...],
    "performance": [...],
    "resilience": [...],
    "migration": [...]
  },
  "success_metrics": {...},
  "risks": [...],
  "timeline": {...}
}
```

Remember: We are ENHANCING the existing ReportingSubAgent, not creating a new class. This is the SINGLE SOURCE OF TRUTH for all reporting.