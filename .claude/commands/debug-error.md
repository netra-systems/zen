---
allowed-tools: ["Task", "Read", "Edit", "Bash", "TodoWrite", "Grep", "Glob"]
description: "Five Whys error analysis with dynamically allocated specialist agents"
argument-hint: "<error-description> [initial-agents]"
---

# 🔬 Five Whys Root Cause Analysis with Dynamic Agent Allocation

Deep error analysis using the Five Whys methodology and dynamically allocated specialist agents based on error patterns.

## Configuration
- **Error Description:** $1
- **Initial Agent Count:** ${2:-3}
- **Dynamic Allocation:** Agents spawned based on error type
- **Consensus Threshold:** 80% agreement required
- **Mode:** Five Whys iterative analysis with cascade prevention

## Phase 1: Initial Error Assessment & Five Whys

### 1. Capture Current Error State
!echo "🔴 CURRENT ERROR STATE:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
!echo "Error: $1"
!echo "Timestamp: $(date)"
!echo ""

### 2. Collect Error Evidence
!echo "📄 Collecting error evidence..."

# Check Docker logs for errors
!docker compose logs --tail 200 2>&1 | grep -iE "error|exception|failed|traceback" | tail -30 > /tmp/error_context.log

# Check recent changes
!git log --oneline -10 > /tmp/recent_commits.log

# Save initial state
!git status --short > /tmp/debug_initial_state.txt
!echo "Initial state saved to /tmp/debug_initial_state.txt"

### 3. Five Whys Analysis with Dynamic Agent Spawning

**Root Cause Analyzer - Five Whys Methodology**
@Task: Perform Five Whys analysis on error: $1
Five Whys Analyst:
CRITICAL: Apply the Five Whys methodology systematically:

1. **WHY #1**: Why did the error occur?
   - Analyze the immediate error message
   - Identify the direct trigger
   - Document: "The error occurred because..."

2. **WHY #2**: Why did [answer from Why #1] happen?
   - Dig deeper into the underlying cause
   - Look for system/code issues
   - Document: "This happened because..."

3. **WHY #3**: Why did [answer from Why #2] happen?
   - Examine design/architecture decisions
   - Check for process failures
   - Document: "This was caused by..."

4. **WHY #4**: Why did [answer from Why #3] happen?
   - Investigate organizational/structural issues
   - Review development practices
   - Document: "This resulted from..."

5. **WHY #5**: Why did [answer from Why #4] happen?
   - Identify the root systemic cause
   - Find the fundamental issue
   - Document: "The root cause is..."

After Five Whys, determine which specialist agents are needed:
- If database-related: Request DatabaseSpecialist agent
- If async/context manager: Request AsyncPythonExpert agent
- If WebSocket-related: Request WebSocketSpecialist agent
- If Docker/deployment: Request DevOpsSpecialist agent
- If dependency/import: Request DependencyAnalyst agent
- If performance: Request PerformanceEngineer agent
- If security: Request SecurityAuditor agent
- If frontend integration: Request FrontendSpecialist agent

Return:
1. Complete Five Whys chain
2. Identified root cause
3. List of required specialist agents
4. Initial remediation hypothesis

## Phase 2: Dynamic Agent Allocation

### 4. Spawn Specialist Agents Based on Error Type

**Dynamic Agent Spawner**
@Task: Based on Five Whys analysis, spawn appropriate specialist agents
Agent Orchestrator:
Based on the Five Whys findings, dynamically spawn the following agents:

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

### 5. Consensus Building from Dynamic Agents

@Task: Build consensus from all spawned specialist agents
Consensus Builder:
- Collect all specialist agent reports
- Weight opinions based on agent expertise relevance
- Calculate consensus score (must exceed 80%)
- Identify primary root cause
- Document dissenting opinions
- Create action priority matrix

## Phase 3: Solution Development (With Consensus)

### 6. Develop Targeted Fix

@Task: Create fix based on Five Whys root cause and specialist consensus
IF consensus >= 80%:
  Solution Architect:
  - Design minimal fix addressing root cause
  - Consider Five Whys chain for comprehensive solution
  - Add defensive coding where needed
  - Include detailed comments explaining the fix
  - Create rollback plan
ELSE:
  - Document lack of consensus
  - Present all hypotheses with evidence
  - Request human intervention
  - Suggest additional investigation paths

### 7. Pre-Implementation Testing

!echo "\n🧪 Pre-implementation verification..."

# Run specific tests related to the error area
!python -m pytest tests/ -k "relevant_test_pattern" --tb=short || true

## Phase 4: Implementation & Validation

### 8. Implement Fix with Safeguards

@Task: Apply the consensus-approved fix with safety checks
Implementation Specialist:
- Apply fix incrementally
- Add comprehensive logging
- Include error recovery mechanisms
- Update relevant documentation
- Create unit tests for the fix

### 9. Dynamic Validation Agent Allocation

@Task: Spawn validation agents based on fix type
Validation Orchestrator:
Based on the implemented fix, spawn appropriate validation agents:

- If database fix: DatabaseValidation agent
- If async fix: AsyncFlowValidation agent  
- If API fix: APIEndpointValidation agent
- If WebSocket fix: RealtimeValidation agent
- If configuration fix: ConfigValidation agent

Each validation agent should:
- Test specific area affected by fix
- Check for regressions
- Verify no new errors introduced
- Measure performance impact
- Report validation status

### 10. Cascade Prevention Analysis

@Task: Analyze for potential cascade failures
Cascade Analyst:
- Map all dependencies of changed code
- Test downstream components
- Check for breaking changes
- Verify backward compatibility
- Document any risks

## Phase 5: Decision & Documentation

### 11. Final Decision Matrix

!echo "\n🎯 FINAL DECISION MATRIX:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━"

@Task: Make commit/revert decision based on comprehensive analysis
Decision Engine:
Evaluate all factors:
1. Five Whys root cause clarity: [score/5]
2. Specialist consensus level: [percentage]
3. Fix implementation quality: [score/10]
4. Validation success rate: [percentage]
5. Cascade risk assessment: [low/medium/high]

IF all criteria meet thresholds:
  - Commit with detailed message including Five Whys
  - Document solution in knowledge base
  - Create monitoring alerts
ELSE:
  - Revert all changes
  - Document investigation findings
  - Escalate to senior engineers
  - Provide detailed failure analysis

### 12. Execute Decision

**If Committing:**
!echo "✅ All validations passed. Committing fix..."
!git add -A
!git commit -m "fix: $1

Root Cause (Five Whys):
$(cat /tmp/five_whys_analysis.txt 2>/dev/null || echo 'See investigation notes')

Validated by dynamic agent consensus (${CONSENSUS_SCORE}%)
Specialist agents involved: ${AGENT_LIST}"

**If Reverting:**
!echo "❌ Validation failed. Reverting changes..."
!git checkout -- .
!git clean -fd
!echo "Reverted to original state"

### 13. Knowledge Base Update

@TodoWrite: Update debugging knowledge base
- Error Pattern: $1
- Five Whys Chain: [Complete analysis]
- Root Cause: [Identified cause]
- Agents Used: [List of dynamically allocated agents]
- Solution: [Applied fix or investigation notes]
- Validation Results: [Test outcomes]
- Lessons Learned: [Key insights]
- Prevention Measures: [Future recommendations]

## Usage Examples
- `/debug-error "AsyncGeneratorContextManager error in WebSocket handler"`
- `/debug-error "500 Internal Server Error on /api/threads endpoint"`
- `/debug-error "Database connection pool exhausted" 5`
- `/debug-error "Circular import in agent modules"`

## Advanced Features

### Dynamic Agent Types (Automatically Selected)
1. **AsyncPythonExpert** - Async/await patterns, generators, context managers
2. **DatabaseSpecialist** - Connection pools, transactions, query optimization
3. **WebSocketSpecialist** - Real-time events, message routing, connection handling
4. **HTTPErrorSpecialist** - API errors, middleware, request/response cycle
5. **DevOpsSpecialist** - Docker, deployment, environment configuration
6. **DependencyAnalyst** - Import graphs, circular dependencies, package conflicts
7. **PerformanceEngineer** - Profiling, optimization, resource management
8. **SecurityAuditor** - Authentication, authorization, vulnerability assessment
9. **FrontendSpecialist** - UI/Backend integration, CORS, API contracts
10. **GeneralistDebugger** - Broad analysis when pattern is unclear

### Safety Mechanisms
1. **Five Whys Methodology** - Systematic root cause analysis
2. **Dynamic Agent Allocation** - Right expertise for each error type
3. **80% Consensus Required** - High confidence threshold
4. **Cascade Prevention** - Proactive regression testing
5. **Automatic Revert** - Rollback on validation failure
6. **Knowledge Capture** - Learn from every debugging session

## Workflow Summary
1. 🔍 Five Whys root cause analysis
2. 🤖 Dynamic specialist agent allocation
3. 🤝 Build consensus (80% threshold)
4. 🔧 Implement targeted fix
5. 🧪 Dynamic validation testing
6. 🛡️ Cascade prevention check
7. ✅ Commit if valid, ❌ Revert if not
8. 📚 Update knowledge base

## Notes
- Five Whys ensures deep understanding, not just symptom fixing
- Agents are allocated based on error characteristics, not predetermined
- Each debugging session improves the knowledge base
- Conservative approach: revert when uncertain
- All decisions are traceable and reversible