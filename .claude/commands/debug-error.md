---
allowed-tools: ["Task", "Read", "Edit", "Bash", "TodoWrite", "Grep", "Glob"]
description: "CRITICAL Five Whys-driven error analysis with complete root cause investigation"
argument-hint: "<error-description> [initial-agents]"
---

# 🔬 CRITICAL: Five Whys Root Cause Analysis - The Foundation of ALL Debugging

**⚠️ MANDATORY: The FIVE WHYS methodology is the CORE PRINCIPLE that drives EVERY aspect of this debugging process.**

Deep, systematic error analysis where FIVE WHYS guides error analysis, solution development, testing strategy, and agent allocation.

## Configuration
- **Error Description:** $1
- **Initial Agent Count:** ${2:-3}
- **FIVE WHYS Depth:** MANDATORY 5 levels minimum (continue until true root found)
- **Dynamic Allocation:** Agents spawned ONLY after FIVE WHYS completion
- **Consensus Threshold:** 80% agreement on FIVE WHYS root cause
- **Mode:** FIVE WHYS-driven systematic investigation with cascade prevention
- **Core Principle:** NO action without complete FIVE WHYS analysis

## Phase 1: MANDATORY FIVE WHYS Deep Analysis (NO SHORTCUTS)

### 1. Capture Current Error State for FIVE WHYS Context
!echo "🔴 FIVE WHYS INVESTIGATION INITIATED:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
!echo "Error Under Investigation: $1"
!echo "Timestamp: $(date)"
!echo "MANDATORY: Complete FIVE WHYS before ANY action"
!echo ""

### 2. Comprehensive Evidence Collection for FIVE WHYS
!echo "📄 Gathering comprehensive evidence for FIVE WHYS analysis..."

# Collect ALL relevant context for deep analysis
!docker compose logs --tail 500 2>&1 | grep -iE "error|exception|failed|traceback|warning" > /tmp/five_whys_evidence.log
!git log --oneline -20 > /tmp/five_whys_commits.log
!git diff HEAD~5 > /tmp/five_whys_recent_changes.diff
!python -c "import sys; print(sys.path)" > /tmp/five_whys_python_env.log
!git status --short > /tmp/five_whys_initial_state.txt
!echo "FIVE WHYS evidence collection complete"

### 3. CRITICAL FIVE WHYS Analysis - The Core of Everything

**🚨 FIVE WHYS Master Analyst - COMPLETE INVESTIGATION REQUIRED**
@Task: Perform EXHAUSTIVE Five Whys analysis on error: $1
Five Whys Master Analyst:
⚠️ CRITICAL MANDATE: The FIVE WHYS is not optional. It is the FOUNDATION of all debugging.
You MUST complete ALL FIVE levels with deep analysis at each stage:

🔴 **WHY #1 - SURFACE SYMPTOM**: Why did this specific error occur?
   - READ the EXACT error message and stack trace
   - IDENTIFY the immediate trigger point (file:line)
   - EXAMINE the failing function/method
   - CHECK input parameters and state at failure
   - DOCUMENT: "Error occurred because: [SPECIFIC TECHNICAL REASON]"
   - SAVE to /tmp/five_whys_level_1.txt

🟠 **WHY #2 - IMMEDIATE CAUSE**: Why did [Level 1 answer] happen?
   - TRACE the call chain that led to failure
   - ANALYZE the preconditions that weren't met
   - REVIEW the data flow leading to this point
   - IDENTIFY any missing validations or checks
   - DOCUMENT: "Level 1 happened because: [DEEPER TECHNICAL CAUSE]"
   - SAVE to /tmp/five_whys_level_2.txt

🟡 **WHY #3 - SYSTEM FAILURE**: Why did [Level 2 answer] occur?
   - EXAMINE architectural decisions that allowed this
   - ANALYZE design patterns that contributed
   - REVIEW integration points and boundaries
   - CHECK for missing abstractions or poor coupling
   - DOCUMENT: "Level 2 occurred because: [ARCHITECTURAL/DESIGN ISSUE]"
   - SAVE to /tmp/five_whys_level_3.txt

🟢 **WHY #4 - PROCESS GAP**: Why did [Level 3 answer] exist?
   - INVESTIGATE development process failures
   - EXAMINE testing gaps that missed this
   - REVIEW code review and QA processes
   - ANALYZE technical debt accumulation
   - DOCUMENT: "Level 3 existed because: [PROCESS/PRACTICE FAILURE]"
   - SAVE to /tmp/five_whys_level_4.txt

🔵 **WHY #5 - ROOT CAUSE**: Why did [Level 4 answer] persist?
   - IDENTIFY the fundamental systemic issue
   - FIND the core organizational/technical principle violation
   - DISCOVER the missing safeguard or control
   - UNDERSTAND the knowledge/skill/resource gap
   - DOCUMENT: "TRUE ROOT CAUSE: [FUNDAMENTAL SYSTEMIC ISSUE]"
   - SAVE to /tmp/five_whys_root_cause.txt

⚠️ **MANDATORY FIVE WHYS OUTPUT**:
1. Complete causal chain from symptom to root
2. Evidence supporting each WHY level
3. Identification of ALL contributing factors
4. Clear articulation of the TRUE root cause
5. Systemic improvements needed to prevent recurrence

🎯 **FIVE WHYS-DRIVEN Agent Allocation**:
Based on the COMPLETE Five Whys analysis, determine specialist agents:
- If database-related: Request DatabaseSpecialist agent
- If async/context manager: Request AsyncPythonExpert agent
- If WebSocket-related: Request WebSocketSpecialist agent
- If Docker/deployment: Request DevOpsSpecialist agent
- If dependency/import: Request DependencyAnalyst agent
- If performance: Request PerformanceEngineer agent
- If security: Request SecurityAuditor agent
- If frontend integration: Request FrontendSpecialist agent

**FIVE WHYS DELIVERABLES** (ALL MANDATORY):
1. ✅ Complete Five Whys causal chain (5 levels minimum)
2. ✅ TRUE root cause with evidence trail
3. ✅ Specialist agents needed based on root cause (not symptoms)
4. ✅ Solution hypothesis targeting root cause
5. ✅ Test strategy addressing each WHY level
6. ✅ Prevention measures for systemic improvement

## Phase 2: FIVE WHYS-Driven Dynamic Agent Allocation

### 4. Agent Selection Based on FIVE WHYS Root Cause Analysis

**🎯 FIVE WHYS-Guided Agent Spawner**
@Task: Spawn specialist agents ONLY based on FIVE WHYS root cause findings
Agent Orchestrator:
⚠️ CRITICAL: Agents are selected based on the ROOT CAUSE from FIVE WHYS, not surface symptoms!

Review the FIVE WHYS analysis and spawn agents that address the TRUE root cause:

# The actual agents spawned will be determined by the Five Whys analysis
# Examples of specialist agents that might be spawned:

IF error contains "async_generator" or "context manager":
  **AsyncPythonExpert Agent**
  @Task: Analyze async/await and context manager patterns
  - Review asynccontextmanager decorators
  - Check async generator usage
  - Verify FastAPI dependency injection
  - Analyze yield vs return patterns
  - Document async flow issues

IF error contains "500" or "Internal Server Error":
  **HTTPErrorSpecialist Agent**
  @Task: Analyze HTTP 500 error patterns
  - Check API endpoint handlers
  - Review middleware stack
  - Analyze request/response cycle
  - Check error handling and logging
  - Identify cascade failures

IF error contains "database" or "session" or "connection":
  **DatabaseSpecialist Agent**
  @Task: Analyze database and session issues
  - Check connection pooling
  - Review transaction boundaries
  - Analyze session lifecycle
  - Verify isolation levels
  - Check for connection leaks

IF error contains "WebSocket" or "real-time":
  **WebSocketSpecialist Agent**
  @Task: Analyze WebSocket communication
  - Check WebSocket handlers
  - Review event routing
  - Analyze connection management
  - Verify message serialization
  - Check for race conditions

IF error contains "import" or "module" or "circular":
  **DependencyAnalyst Agent**
  @Task: Analyze import and dependency issues
  - Map import graph
  - Detect circular dependencies
  - Check package versions
  - Analyze module loading order
  - Review lazy imports

IF error contains "Docker" or "container" or "deployment":
  **DevOpsSpecialist Agent**
  @Task: Analyze deployment and container issues
  - Check Docker configurations
  - Review environment variables
  - Analyze build process
  - Verify service dependencies
  - Check resource limits

IF error contains "memory" or "CPU" or "performance":
  **PerformanceEngineer Agent**
  @Task: Analyze performance issues
  - Profile resource usage
  - Check for memory leaks
  - Analyze query performance
  - Review caching strategies
  - Identify bottlenecks

IF error contains "auth" or "security" or "permission":
  **SecurityAuditor Agent**
  @Task: Analyze security and authentication issues
  - Check authentication flow
  - Review authorization logic
  - Analyze token validation
  - Verify security headers
  - Check for vulnerabilities

IF error pattern is unclear:
  **GeneralistDebugger Agent**
  @Task: Perform broad spectrum analysis
  - General code review
  - Check recent changes
  - Review system logs
  - Analyze test failures
  - Document observations

### 5. FIVE WHYS Consensus Validation

@Task: Validate all agents agree with FIVE WHYS root cause analysis
FIVE WHYS Consensus Validator:
⚠️ CRITICAL: All agents MUST validate against the FIVE WHYS findings!
- Collect all specialist agent analyses
- Verify each agent's findings align with FIVE WHYS root cause
- Calculate consensus on FIVE WHYS causal chain (must exceed 80%)
- If disagreement exists, RE-RUN FIVE WHYS with new evidence
- Document how each agent's findings support/refute FIVE WHYS
- Create FIVE WHYS-aligned action matrix

## Phase 3: FIVE WHYS-Driven Solution Development

### 6. Develop Solution Addressing EACH Level of FIVE WHYS

@Task: Create comprehensive fix addressing ALL FIVE WHYS levels, not just symptoms
FIVE WHYS Solution Architect:
⚠️ MANDATORY: Your solution MUST address findings from ALL FIVE WHY levels!

IF FIVE WHYS consensus >= 80%:
  **Layered Solution Development**:
  
  📍 **For WHY #1 (Symptom)**: 
    - Add immediate error handling
    - Improve error messages and logging
    
  📍 **For WHY #2 (Immediate Cause)**:
    - Fix the direct technical issue
    - Add input validation/guards
    
  📍 **For WHY #3 (System Failure)**:
    - Refactor architecture/design flaw
    - Improve module boundaries
    
  📍 **For WHY #4 (Process Gap)**:
    - Add missing tests/checks
    - Update development workflows
    
  📍 **For WHY #5 (Root Cause)**:
    - Implement systemic solution
    - Add permanent safeguards
    - Update documentation/training
    
  - Document how solution addresses EACH WHY level
  - Create rollback plan for each layer
  - Save solution mapping to /tmp/five_whys_solution_map.txt
  
ELSE:
  - RERUN FIVE WHYS with additional evidence
  - Document conflicting analyses
  - Escalate with complete FIVE WHYS report
  - DO NOT proceed without root cause clarity

### 7. FIVE WHYS-Based Test Strategy Development

!echo "\n🧪 FIVE WHYS-driven test strategy..."

@Task: Create tests that validate EACH level of the FIVE WHYS
FIVE WHYS Test Strategist:
Design tests that verify fixes at ALL FIVE WHY levels:

1. **Test for WHY #1**: Verify symptom is handled
2. **Test for WHY #2**: Validate immediate cause is fixed
3. **Test for WHY #3**: Confirm system issue is resolved
4. **Test for WHY #4**: Check process improvements work
5. **Test for WHY #5**: Ensure root cause cannot recur

!python -m pytest tests/ -k "five_whys_validation" --tb=short || true

## Phase 4: FIVE WHYS-Validated Implementation

### 8. Implement Multi-Layer Fix Based on FIVE WHYS

@Task: Apply fixes addressing ALL FIVE WHYS levels systematically
FIVE WHYS Implementation Specialist:
⚠️ CRITICAL: Implementation MUST follow FIVE WHYS findings!

- Start with WHY #5 (root cause) fixes
- Work backwards to WHY #1 (symptom) fixes  
- Each fix must reference its FIVE WHYS level
- Add logging that traces FIVE WHYS causal chain
- Include FIVE WHYS documentation in code comments
- Create tests for each WHY level

### 9. FIVE WHYS Validation Agent Deployment

@Task: Deploy validation agents for EACH FIVE WHYS level
FIVE WHYS Validation Orchestrator:
Spawn validation agents to verify fixes at each WHY level:

- If database fix: DatabaseValidation agent
- If async fix: AsyncFlowValidation agent  
- If API fix: APIEndpointValidation agent
- If WebSocket fix: RealtimeValidation agent
- If configuration fix: ConfigValidation agent

**FIVE WHYS Level Validators**:
1. **WHY #1 Validator**: Symptom properly handled?
2. **WHY #2 Validator**: Immediate cause resolved?
3. **WHY #3 Validator**: System issue fixed?
4. **WHY #4 Validator**: Process gap closed?
5. **WHY #5 Validator**: Root cause eliminated?

Each validator MUST:
- Test their specific FIVE WHYS level
- Verify no regression at their level
- Confirm fix prevents recurrence
- Validate against FIVE WHYS documentation
- Report success/failure with evidence

### 10. FIVE WHYS Cascade Prevention Analysis

@Task: Use FIVE WHYS to predict and prevent cascade failures
FIVE WHYS Cascade Analyst:
⚠️ Apply FIVE WHYS thinking to cascade prevention:
- For each change, ask "Why might this cascade?"
- Trace potential failure paths using FIVE WHYS
- Test each level of potential cascade
- Document cascade prevention measures
- Verify fixes don't create new FIVE WHYS chains

## Phase 5: FIVE WHYS-Based Decision & Documentation

### 11. FIVE WHYS Decision Matrix

!echo "\n🎯 FIVE WHYS FINAL DECISION MATRIX:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

@Task: Make commit/revert decision based on FIVE WHYS analysis completeness
FIVE WHYS Decision Engine:
⚠️ CRITICAL: Decision MUST be based on FIVE WHYS completion!

Evaluate FIVE WHYS criteria:
1. **FIVE WHYS Completion**: All 5 levels analyzed? [YES/NO]
2. **Root Cause Identified**: TRUE root cause found? [YES/NO]
3. **Causal Chain Clear**: Complete chain documented? [YES/NO]
4. **Solution Coverage**: All WHY levels addressed? [% covered]
5. **Test Coverage**: Each WHY level tested? [% tested]
6. **Consensus on Root**: Agreement on root cause? [% consensus]
7. **Prevention Measures**: Systemic fixes in place? [YES/NO]

**FIVE WHYS Success Criteria**:
- ✅ ALL criteria must be YES or >80% to proceed
- ❌ ANY missing FIVE WHYS level = STOP and re-analyze
- ⚠️ Root cause MUST be systemic, not symptomatic

IF FIVE WHYS criteria satisfied:
  - Commit with complete FIVE WHYS documentation
  - Update knowledge base with FIVE WHYS learnings
  - Create monitoring for each WHY level
  - Implement systemic prevention measures
ELSE:
  - DO NOT PROCEED without complete FIVE WHYS
  - Re-run FIVE WHYS with more evidence
  - Escalate with partial FIVE WHYS findings
  - Request additional investigation resources

### 12. Execute FIVE WHYS-Based Decision

**If FIVE WHYS Complete & Validated:**
!echo "✅ FIVE WHYS analysis complete. Committing comprehensive fix..."
!git add -A
!git commit -m "fix: $1

FIVE WHYS Root Cause Analysis:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHY #1: $(cat /tmp/five_whys_level_1.txt)
WHY #2: $(cat /tmp/five_whys_level_2.txt)
WHY #3: $(cat /tmp/five_whys_level_3.txt)
WHY #4: $(cat /tmp/five_whys_level_4.txt)
WHY #5 (ROOT): $(cat /tmp/five_whys_root_cause.txt)

Solution addresses all 5 levels
Validated by FIVE WHYS consensus (${CONSENSUS_SCORE}%)
Prevention measures implemented for systemic improvement"

**If FIVE WHYS Incomplete:**
!echo "❌ FIVE WHYS incomplete. Cannot proceed without root cause..."
!echo "Missing FIVE WHYS levels - investigation continues"
!git stash
!echo "Changes stashed pending complete FIVE WHYS analysis"

### 13. FIVE WHYS Knowledge Capture

@TodoWrite: Capture FIVE WHYS learnings permanently
- **Error Symptom**: $1
- **FIVE WHYS Complete Chain**:
  - WHY #1: [Surface symptom analysis]
  - WHY #2: [Immediate cause finding]
  - WHY #3: [System failure identified]
  - WHY #4: [Process gap discovered]
  - WHY #5: [ROOT CAUSE determined]
- **Agents Allocated Based on Root**: [List of FIVE WHYS-driven agents]
- **Multi-Layer Solution**: [Fixes for each WHY level]
- **Validation at Each Level**: [Test results per WHY]
- **Systemic Improvements**: [Long-term prevention measures]
- **FIVE WHYS Success Metrics**: [Completion %, consensus %, prevention effectiveness]

## Usage Examples (FIVE WHYS will be applied to each)
- `/debug-error "AsyncGeneratorContextManager error in WebSocket handler"`
- `/debug-error "500 Internal Server Error on /api/threads endpoint"`
- `/debug-error "Database connection pool exhausted" 5`
- `/debug-error "Circular import in agent modules"`

## 🚨 CRITICAL: FIVE WHYS Enforcement Rules

### FIVE WHYS is MANDATORY for:
1. **Every Error Investigation** - No exceptions
2. **Agent Allocation** - Only after root cause identified
3. **Solution Design** - Must address all 5 levels
4. **Testing Strategy** - Tests for each WHY level
5. **Decision Making** - Cannot proceed without complete FIVE WHYS

### FIVE WHYS-Selected Agent Types (Based on ROOT CAUSE, not symptoms)
1. **AsyncPythonExpert** - When root is async/await design flaw
2. **DatabaseSpecialist** - When root is data architecture issue
3. **WebSocketSpecialist** - When root is real-time design problem
4. **HTTPErrorSpecialist** - When root is API contract violation
5. **DevOpsSpecialist** - When root is deployment/config management
6. **DependencyAnalyst** - When root is module architecture flaw
7. **PerformanceEngineer** - When root is algorithmic/resource issue
8. **SecurityAuditor** - When root is security model weakness
9. **FrontendSpecialist** - When root is UI/UX integration design
10. **GeneralistDebugger** - When FIVE WHYS reveals complex multi-system root

### FIVE WHYS Safety Mechanisms
1. **Complete FIVE WHYS Required** - Cannot skip levels
2. **Root Cause Validation** - Must be systemic, not symptomatic
3. **Multi-Layer Solutions** - Address each WHY level
4. **Level-Specific Testing** - Validate each layer
5. **Consensus on Root** - 80% agreement on true cause
6. **Prevention Focus** - Systemic improvements mandatory

## FIVE WHYS Workflow (STRICTLY ENFORCED)
1. 🔴 **WHY #1** - Identify surface symptom
2. 🟠 **WHY #2** - Find immediate cause
3. 🟡 **WHY #3** - Discover system failure
4. 🟢 **WHY #4** - Uncover process gap
5. 🔵 **WHY #5** - Determine ROOT CAUSE
6. 🎯 Allocate agents based on ROOT
7. 🔧 Implement fixes for ALL levels
8. 🧪 Test each WHY level
9. ✅ Commit only if FIVE WHYS complete
10. 📚 Document complete FIVE WHYS chain

## ⚠️ FINAL WARNING
**FIVE WHYS is not a suggestion - it is THE CORE METHODOLOGY**
- Incomplete FIVE WHYS = Investigation failure
- Treating symptoms without root cause = Guaranteed recurrence
- Every debugging session MUST produce a complete FIVE WHYS chain
- Success is measured by ROOT CAUSE elimination, not symptom suppression