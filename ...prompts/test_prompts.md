
## Example prompts for running tests with Claude Code

- USING UNIFIED TEST RUNNER: One at a time, step through each cypress test. spawn a new sub agent. upgrade the test to refect current SUT.
- USING UNIFIED TEST RUNNER: One at a time, step through each e2e test. spawn a new sub agent. Update test to reflect current claude.md standards and the SUT. Run the test. Fix the SUT. 
- USING UNIFIED TEST RUNNER: One at a time, step through each e2e test. spawn a new sub agent. Run the test. Fix the SUT.  MOST LIKELY TO FAIL first. 
- USING UNIFIED TEST RUNNER: One at a time, step through each integration test. spawn a new sub agent. Update test to reflect current claude.md standards and the SUT. Run the test. Fix the SUT. 
- USING UNIFIED TEST RUNNER: One at a time, step through each integration test, audit if the test is legacy or useful for active real system under test. Update it as needed or if it's of negative value add delete it.
- USING UNIFIED TEST RUNNER: One at a time, run all tests related to agents. spawn a new sub agent. Run the test. Fix the SUT. 
- USING UNIFIED TEST RUNNER: Run integration tests related to agents. spawn a new sub agent. Run the test. Fix the system under test for failures. focus on tests MOST LIKELY TO FAIL first. 
- USING UNIFIED TEST RUNNER: One at a time, step through each e2e real llm agent tests. spawn a new sub agent. Run the test. Fix the SUT.  MOST LIKELY TO FAIL first. 
- USING UNIFIED TEST RUNNER: One at a time, step through each cypress real llm agent tests. spawn a new sub agent. Run the test. Fix the SUT.  MOST LIKELY TO FAIL first. 


- USING UNIFIED TEST RUNNER: One at a time, step through each e2e REAL llm agent tests. spawn a new sub agent. Run the test. Fix the SUT.  MOST LIKELY TO FAIL first. 
 Fix all errors

- USING UNIFIED TEST RUNNER: One at a time, for each step: spawn a new sub agent. run frontend tests -fast-fail (and think MOST LIKELY TO FAIL first). Fix the SUT.  
REPEAT each step at least 100 times or still all tests pass.

- USING UNIFIED TEST RUNNER: One at a time, for each step: spawn a new sub agent. run dev-env dev auto login and auth tests -fast-fail (and think MOST LIKELY TO FAIL first). Fix the SUT.  
REPEAT each step at least 100 times or still all tests pass.

 - USING UNIFIED TEST RUNNER: Run tests most likely to fail and fail the fastest first.  One at a time, step through each failure. spawn a new sub agent. Run the test. Fix the SUT. 
 - USING UNIFIED TEST RUNNER: Run AUTH tests most likely to fail and fail the fastest first.  One at a time, step through each failure. spawn a new sub agent. Run the test. Fix the SUT. 


 CRITICAL: Action and remediate each item in E2E_REAL_LLM_AUDIT_REPORT.md
for each item, one at a time, spawn a new sub agent team
do not bulk edit files, do one file at a time, run the tests , fix system under test

#1 USING UNIFIED TEST RUNNER: TODO List track all tests in e2e\frontend\FRONTEND_TEST_COVERAGE_REPORT.md  STEP: One at a time: spawn a new sub agent: run the test and fix the system under test
REPEAT each STEP at least 100 times or untill all tests pass.

# 2
USING UNIFIED TEST RUNNER:  STEP: Run tests most likely to fail and fail the fastest first.  One at a time, step  through each failure. spawn a new sub agent. Run the test. Fix the SUT.
  REPEAT each STEP at least 100 times or untill all tests pass.


  USING UNIFIED TEST RUNNER: Run REGRESSION tests most likely to fail and fail the fastest first.  One at a time, step through each failure. spawn a new sub agent. Run the test. Fix the SUT. 

    USING UNIFIED TEST RUNNER: Run unit and integration tests most likely to fail and fail the fastest first.  One at a time, step through each failure. spawn a new sub agent. Run the test. Fix the SUT. 

    
    USING UNIFIED TEST RUNNER: Run most likely to fail and fail the fastest first AND be the most useful. Use test discovery. One at a time, step through each failure. spawn a new sub agent. Run the test. Fix the SUT. 

    AUDIT e2e tests most badly using mocks One at a time, step through each failure. spawn a new sub agent. Make the test more realistic and much tougher. Focus on the BASICS, the most expected critical paths. Run it. Fix the system under test.


    
## PLAN: The 5 Most Important Missing Tests for "Chat is King" Concept

**Business Context:** Chat delivers 90% of user value. Beta users must experience responsive, useful, and strong chat functionality. Tests must validate real system behavior with minimal dependency overhead.

### **TEST 1: Real-Time Chat Responsiveness Under Load** 
**Priority: CRITICAL** | **Business Impact: $500K+ ARR** | **User Experience: Core**

**Objective:** Validate that chat remains responsive during peak usage scenarios that beta users will experience.

**Test Strategy:**
- **Real System Testing:** Uses actual WebSocket connections, real agent execution, and live message routing
- **Minimal Dependencies:** Embedded LLM responses (no external LLM calls), local database, mock external APIs only
- **Beta User Simulation:** 3-10 concurrent users with realistic message patterns

**Key Test Scenarios:**
1. **Concurrent User Load Test:**
   - 5 simultaneous users sending messages
   - Each user receives real-time updates within 2 seconds
   - WebSocket events flow correctly (agent_started, agent_thinking, tool_executing, agent_completed)
   - No message loss or connection drops

2. **Agent Processing Backlog Test:**
   - Queue 10 requests rapidly 
   - Verify each user sees proper "processing" indicators
   - Ensure messages are processed in order
   - No user is left without feedback

3. **WebSocket Connection Recovery:**
   - Simulate brief network disruption during active chat
   - Verify automatic reconnection and message replay
   - User sees seamless continuation

**Implementation Approach:**
- Spawn dedicated agent team: Test Infrastructure Agent + Load Testing Agent
- Build on existing `WebSocketManager` and `SupervisorAgent` 
- Extend `StressTestClient` from mission_critical test suite
- Use real `ExecutionEngine` with mocked tool responses

**Acceptance Criteria:**
- ✅ 5 concurrent users get responses within 2s
- ✅ All WebSocket events fire correctly under load  
- ✅ Zero message loss during normal operation
- ✅ Connection recovery works within 5s

---

### **TEST 2: End-to-End Agent Orchestration Flow**
**Priority: CRITICAL** | **Business Impact: User Retention** | **User Experience: Core**

**Objective:** Validate complete user journey from chat message to final response using real agent orchestration.

**Test Strategy:** 
- **Real System Testing:** Full SupervisorAgent → SubAgent → Tool execution chain
- **Minimal Dependencies:** Real agent registry, real tool dispatcher, mocked external services
- **Beta User Journey:** Authentic multi-agent workflows that users will encounter

**Key Test Scenarios:**
1. **Complete Agent Workflow:**
   - User sends: "What's my account status and recent usage?"
   - SupervisorAgent routes to DataSubAgent and AnalyticsAgent  
   - Tools execute with real parameters
   - Final response synthesizes all agent results
   - User sees step-by-step progress via WebSocket

2. **Agent Handoff and Context Preservation:**
   - Multi-turn conversation requiring context
   - State transfers correctly between agents
   - User context maintained throughout flow
   - Previous conversation history impacts agent decisions

3. **Error Recovery During Agent Execution:**
   - One sub-agent fails mid-execution
   - SupervisorAgent routes to fallback agent
   - User sees transparent error handling
   - Final response acknowledges limitation but provides value

**Implementation Approach:**
- Spawn dedicated agent team: Agent Orchestration Specialist + Integration Testing Agent
- Use real `AgentRegistry`, `ExecutionEngine`, and `PipelineExecutor`
- Mock external API responses but use real internal routing
- Build comprehensive flow validator that tracks agent handoffs

**Acceptance Criteria:**
- ✅ Complete user request fulfilled via multi-agent orchestration
- ✅ All agent transitions logged and visible to user
- ✅ Context preserved across agent handoffs
- ✅ Error scenarios result in useful fallback responses

---

### **TEST 3: WebSocket Event Reliability and User Feedback**
**Priority: HIGH** | **Business Impact: User Trust** | **User Experience: Transparency**

**Objective:** Ensure users always know what's happening - no "black box" periods where agents are working silently.

**Test Strategy:**
- **Real System Testing:** Actual WebSocket events using production event flow
- **Minimal Dependencies:** Real WebSocketManager, real event emission, mocked slow operations
- **Beta User Experience:** Focus on "user never wonders what's happening"

**Key Test Scenarios:**
1. **Event Completeness Validation:**
   - Every agent execution phase sends appropriate WebSocket event
   - Events include contextually useful information (not just "processing...")
   - User sees specific tool names and progress indicators
   - Final events include success/error state clearly

2. **Event Ordering and Timing:**
   - Events arrive in logical sequence
   - No events arrive out of order or after completion
   - Timing feels natural (not too fast to read, not too slow to frustrate)
   - Long-running operations send periodic updates

3. **Edge Case Event Handling:**
   - Agent crashes mid-execution → user gets clear error event
   - Network hiccup → events resume without duplication
   - Malformed requests → user gets helpful error guidance
   - System overload → user gets "please wait" rather than silence

**Implementation Approach:**
- Spawn dedicated agent team: WebSocket Specialist + UX Validation Agent  
- Build enhanced `MissionCriticalEventValidator` with timing analysis
- Use real event emission pipeline with controllable delays
- Create "beta user simulator" that validates event usefulness

**Acceptance Criteria:**
- ✅ Every user action results in immediate event (within 500ms)
- ✅ No silent periods longer than 5 seconds during processing
- ✅ Error events provide actionable guidance to user
- ✅ Event content is contextually useful, not generic

---

### **TEST 4: Chat Session Persistence and State Management** 
**Priority: HIGH** | **Business Impact: User Productivity** | **User Experience: Continuity**

**Objective:** Beta users can have meaningful multi-session conversations without losing context or having to repeat themselves.

**Test Strategy:**
- **Real System Testing:** Real database persistence, real state serialization/deserialization  
- **Minimal Dependencies:** Local PostgreSQL, real state management, mocked external context
- **Beta User Workflow:** Multi-day conversation continuation and context recall

**Key Test Scenarios:**
1. **Cross-Session Context Preservation:**
   - User starts conversation about project X  
   - Returns next day and continues discussion
   - Agent remembers previous context and decisions
   - User doesn't need to re-explain background

2. **Conversation Thread Management:**
   - Multiple parallel conversation threads
   - Agent maintains separate context per thread
   - User can switch between threads without confusion
   - Thread history is preserved and searchable

3. **State Recovery After Interruption:**
   - Agent execution interrupted mid-process
   - User reconnects and continues from last meaningful state
   - No duplicate processing of completed steps
   - User sees clear indication of where they left off

**Implementation Approach:**
- Spawn dedicated agent team: State Management Specialist + Database Integration Agent
- Use real `StateManager` and `state_persistence_service`
- Test with actual `DeepAgentState` serialization/deserialization
- Create conversation continuity validator

**Acceptance Criteria:**  
- ✅ Context preserved across browser close/reopen
- ✅ Multi-thread conversations maintain separate context
- ✅ Interrupted sessions resume cleanly
- ✅ State transitions are atomic (no partial states)

---

### **TEST 5: Beta User Onboarding and First-Chat Experience**
**Priority: HIGH** | **Business Impact: User Conversion** | **User Experience: First Impression**

**Objective:** New beta users have a smooth, confidence-building first chat experience that demonstrates the platform's value immediately.

**Test Strategy:**
- **Real System Testing:** Complete onboarding flow using real authentication and chat initialization
- **Minimal Dependencies:** Real auth flow, real WebSocket setup, simplified demo agents  
- **Beta User Journey:** Authentic first-user experience from signup to first valuable response

**Key Test Scenarios:**
1. **Smooth Onboarding to First Chat:**
   - New user signs up and gets immediate access to chat
   - First message shows agent capabilities clearly
   - System provides helpful suggestions for initial questions
   - User gets valuable response within first 30 seconds

2. **Progressive Feature Discovery:**
   - Initial chat demonstrates basic agent functionality
   - Follow-up interactions reveal more advanced capabilities
   - User naturally discovers multi-agent orchestration
   - Error handling is educational, not frustrating

3. **Value Demonstration Sequence:**
   - First 3 messages demonstrate clear platform value
   - Each response builds user confidence in system
   - User understands how to get value from subsequent chats
   - System sets appropriate expectations for response quality/time

**Implementation Approach:**
- Spawn dedicated agent team: Onboarding Specialist + User Experience Agent
- Create "first-time user simulator" with realistic usage patterns
- Use real authentication system with test user provisioning
- Build "value demonstration validator" that measures user success metrics

**Acceptance Criteria:**
- ✅ New user gets first response within 30 seconds
- ✅ First 3 interactions each demonstrate distinct value
- ✅ Error scenarios provide educational guidance  
- ✅ User can successfully complete 5 different request types

---

## **Implementation Strategy**

### **Phase 1: Infrastructure Setup (Week 1)**
1. Create shared test infrastructure supporting all 5 test suites
2. Establish baseline metrics and success criteria
3. Set up continuous integration pipeline for these critical tests

### **Phase 2: Sequential Implementation (Weeks 2-6)**
- **Week 2:** Test 1 (Load/Responsiveness) - Foundation for all other tests
- **Week 3:** Test 2 (Agent Orchestration) - Core business logic validation
- **Week 4:** Test 3 (WebSocket Events) - User experience validation
- **Week 5:** Test 4 (State Management) - Multi-session user value
- **Week 6:** Test 5 (Onboarding) - New user conversion

### **Phase 3: Integration and Hardening (Week 7)**
1. Run all 5 test suites together to identify interactions
2. Optimize test execution time while maintaining real system coverage
3. Create test maintenance documentation and ownership

### **Test Execution Protocol**
Each test suite will be implemented by a dedicated multi-agent team:
1. **Test Infrastructure Agent:** Sets up test environment and tooling
2. **Domain Specialist Agent:** Implements core test logic for the specific area
3. **Integration Agent:** Ensures test works with real system components
4. **Validation Agent:** Creates comprehensive acceptance criteria validation

### **Success Metrics**
- **Technical:** All tests pass in <5 minutes, catch regressions before production
- **Business:** Beta user satisfaction >90%, chat response time <3 seconds average
- **Quality:** Zero critical chat bugs reach beta users, 99.9% WebSocket reliability

This plan prioritizes the most critical user experience gaps while maintaining practical implementation constraints for a beta user rollout.