

AUDIT all e2e real LLM tests are they real? is their coverage good? are they missing things?

Identify the 100 most important files in the system. one at a time spawn a sub agent to review them for claude.md violations. Remediate and align. CAREFUL if a file needs to update other files etc. to make changes complete.

Identify the 100 most important tests in the system. one at a time spawn a sub agent to review the test and rate   │
│   it on a critera of 1) usefulness 2) difficulty to pass 3) {you decide}  


AUDIT Top 10 CHAT IS KING business value concepts with the technical side of DEFINITION_OF_DONE_CHECKLIST.md
For each important business value concept, audit and remediate (across all system layers) plan, then action plan.
Use fresh sub agents and todo list



CREATE AN AUDIT SPEC AND RUN IT FOR: 

## all major parts of system that are **defined but never called!!!**

 e.g. like      │
│   this isue After a comprehensive multi-agent audit of the WebSocket communication chain, I identified several       │
│   critical                                                                                                           │
│     missing pieces:                                                                                                  │
│                                                                                                                      │
│     1. Missing WebSocket Events: The backend had all the WebSocket notification methods defined but they were NOT    │
│     being called during agent execution                                                                              │
│     2. Events Not Sent:                                                                                              │
│       - agent_thinking - Real-time agent reasoning updates                                                           │
│       - partial_result - Incremental result streaming                                                                │
│       - tool_executing - Tool execution notifications                                                                │
│       - tool_completed - Tool completion status                                                                      │
│       - final_report - Comprehensive completion reports                                                              │
│     3. Frontend Ready but Not Receiving: The frontend has comprehensive handlers for all these events but wasn't     │
│     receiving them because the backend wasn't sending them