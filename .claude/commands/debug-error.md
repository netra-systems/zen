---
allowed-tools: ["Task", "Read", "Edit", "Bash", "TodoWrite"]
description: "Intelligent error debugging with N agents consensus and cascade prevention"
argument-hint: "<error-description> [num-agents]"
---

# 🔬 Intelligent Error Debugging with Consensus

Spawn N agents to analyze errors, debug only with consensus, prevent cascades, and revert if needed.

## Configuration
- **Error Description:** $1
- **Number of Debug Agents:** ${2:-5}
- **Consensus Threshold:** (n-1)/n agents must agree
- **Mode:** Safe debugging with cascade prevention

## Phase 1: Error Discovery & Analysis

### 1. Capture Current Error State
!echo "🔴 CURRENT ERROR STATE:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
!echo "Error: $1"
!echo ""

### 2. Collect Error Context
!echo "📄 Collecting error evidence..."

# Check Docker logs for errors
!docker compose logs --tail 100 2>&1 | grep -iE "error|exception|failed" | tail -20

# Check test failures
!python tests/unified_test_runner.py --category smoke --fast-fail 2>&1 | grep -E "FAILED|ERROR" | head -10 || echo "Tests not run yet"

# Save initial state
!git status --short > /tmp/debug_initial_state.txt
!echo "Initial state saved to /tmp/debug_initial_state.txt"

## Phase 2: Multi-Agent Root Cause Analysis

### 3. Spawn Diagnostic Agents (${2:-5} agents)

**Agent 1 - Code Analysis**
@Task: Analyze code for error: $1
Diagnostic Agent 1:
- Examine the error message and stack trace
- Identify the exact file and line causing the error
- Analyze the code logic around the error
- Determine root cause from code perspective
- Document findings in structured format
- DO NOT make any changes yet

**Agent 2 - Dependency Analysis**
@Task: Analyze dependencies for error: $1
Diagnostic Agent 2:
- Check import statements and module dependencies
- Verify all required packages are installed
- Check for version conflicts
- Analyze circular dependencies
- Document dependency-related causes
- DO NOT make any changes yet

**Agent 3 - Configuration Analysis**
@Task: Analyze configuration for error: $1
Diagnostic Agent 3:
- Check environment variables
- Verify configuration files
- Analyze service connections (DB, Redis, etc.)
- Check for missing or incorrect settings
- Document configuration issues
- DO NOT make any changes yet

**Agent 4 - Historical Analysis**
@Task: Analyze git history for error: $1
Diagnostic Agent 4:
- Review recent commits that might have introduced the error
- Check if similar errors occurred before
- Analyze what changed recently
- Look for patterns in past fixes
- Document historical context
- DO NOT make any changes yet

**Agent 5 - System Analysis**
@Task: Analyze system state for error: $1
Diagnostic Agent 5:
- Check system resources (memory, CPU, disk)
- Verify Docker container states
- Analyze network connectivity
- Check file permissions
- Document system-level issues
- DO NOT make any changes yet

### 4. Consensus Evaluation
@Task: Evaluate consensus from ${2:-5} diagnostic agents
Consensus Evaluator:
- Collect all ${2:-5} agent reports
- Identify the root cause that (${2:-5}-1)/${2:-5} agents agree on
- If consensus reached: Document agreed root cause
- If no consensus: List all proposed causes with agent votes
- Create decision matrix

## Phase 3: Solution Implementation (Only with Consensus)

### 5. Implement Fix (If Consensus Achieved)
@Task: Implement fix for agreed root cause
IF (${2:-5}-1)/${2:-5} agents agree on root cause:
- Create detailed fix plan
- Make MINIMAL changes required
- Add extensive logging around changes
- Document every modification
- Save rollback information
ELSE:
- DO NOT implement any fix
- Request human intervention
- Document disagreement for review

### 6. Test Fix Locally
!echo "\n🧪 Testing implemented fix..."
!python tests/unified_test_runner.py --real-services --category smoke --fast-fail

## Phase 4: Cascade Prevention

### 7. Spawn Validation Agents (${2:-5} new agents)

**Validation Squad**
@Task: Verify fix doesn't cause new issues - Agent Squad of ${2:-5}
Spawn ${2:-5} NEW validation agents to check:
- Agent 1: Verify core functionality still works
- Agent 2: Check for new errors in logs
- Agent 3: Validate all API endpoints
- Agent 4: Test WebSocket events
- Agent 5: Verify database operations

Each agent should:
- Run specific tests for their area
- Check for any new errors or warnings
- Verify no regression occurred
- Report any cascade issues found

### 8. Cascade Detection
@Task: Analyze validation results for cascading failures
Cascade Analyzer:
- Review all validation agent reports
- Identify any new issues introduced
- Check for unexpected side effects
- Determine if rollback is needed
- Document cascade risks

## Phase 5: Commit or Revert Decision

### 9. Final Decision Logic
!echo "\n🎯 FINAL DECISION:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

@Task: Make final commit or revert decision
Decision Maker:
IF all conditions met:
  1. (${2:-5}-1)/${2:-5} diagnostic agents agreed on root cause
  2. Fix was implemented successfully
  3. Local tests pass
  4. No cascade issues detected by validation agents
  5. Execution is now flawless
THEN:
  - Commit the fix with detailed message
  - Document the solution
ELSE:
  - REVERT all changes
  - Restore original state
  - Document why fix was reverted
  - Provide detailed report for human review

### 10. Execute Decision

**If Committing:**
!echo "✅ All checks passed. Committing fix..."
!git add -A
!git commit -m "fix: $1 - Validated by ${2:-5} agents with consensus"

**If Reverting:**
!echo "❌ Issues detected. Reverting changes..."
!git checkout -- .
!git clean -fd
!echo "Reverted to original state"

### 11. Final Report
@TodoWrite: Create final debugging report
- Error: $1
- Root cause: [Consensus finding]
- Solution: [Implemented fix or revert reason]
- Validation: [Test results]
- Decision: [Commit or Revert]
- Next steps: [Recommendations]

## Usage Examples
- `/debug-error "IndentationError in agent_websocket_bridge.py" 5`
- `/debug-error "Connection refused to PostgreSQL" 7`
- `/debug-error "WebSocket events not firing" 3`
- `/debug-error "Import cycle detected" 10`

## Safety Features
1. **No Unilateral Changes:** Requires (n-1)/n consensus
2. **Cascade Prevention:** Validation agents check for new issues
3. **Automatic Revert:** Reverts if any validation fails
4. **No Commits Without Perfection:** Only commits if execution is flawless
5. **Human Fallback:** Requests human help if no consensus

## Debug Workflow Summary
1. 🔍 Analyze error with N agents
2. 🤝 Require (N-1)/N consensus on root cause
3. 🔧 Implement minimal fix
4. 🧪 Test thoroughly
5. 🔎 Validate with N new agents
6. ✅ Commit only if perfect
7. ❌ Revert if any issues found

## Notes
- Agents work sequentially to avoid system overload
- Every change is documented and reversible
- Consensus prevents wrong fixes
- Validation prevents cascade failures
- Conservative approach: When in doubt, revert