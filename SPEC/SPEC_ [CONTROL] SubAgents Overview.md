## SPEC: \[CONTROL\] SubAgents Overview

1:0:0: PRIMARY GOAL: Dedicated SubAgent concepts: 

1:0:0:0 Intent: The point of SubAgents is to manage it’s own context and protect the primary context from getting cluttered.  
1:0:0:1: Follow best practices for SubAgents including having clear entry and exit conditions.  
1:0:0:2: The End to end flow from frontend to backend and back must work. Code must be PRODUCTION grade and include all concepts needed to the best of your ability.  
1:0:0:3: SubAgents use prompt templates to communicate with an LLM. They are LLM based always. Always include the complete prompt template and LLM usage.

1:0:1: Agents:  
1:0:1:0: Keep ALL existing Agents. Only Update Agents. Keep files where they are. Implement all updates as needed.  
1:0:1:1: SupervisorAgent.  
1:0:1:2: TriageSubAgent: The triage process is its own SubAgent.  
1:0:1:3: DataSubAgent: Data tools, enrichment type tools, etc. process.  
1:0:1:4: OptimizationsCoreSubAgent: Takes data from DataSubAgent and is the initial “Core” of everything between DataSubAgent and ActionsToMeetGoalsSubAgent.  
1:0:1:5: ActionsToMeetGoalsSubAgent: Takes all concepts from OptimizationsCoreSubAgent and formulates everything to do with tangible actions and changes and supply configs etc. to make it happen.  
1:0:1:6: ReportingAgent: Summarizes overall results and reports to users.

1:0:2: Modular concepts. Expect other subagents to be in the future.

1:0:3: Triple check all existing tools and functions are KEPT. This is only about ADDING and organizing subagent concepts. SubAgents may share many tools if needed.

1:0:4: Test the default flow: Input from user: SupervisorAgent: TriageSubAgent: SupervisorAgent: DataSubAgent: SupervisorAgent: OptimizationsCoreSubAgent: SupervisorAgent: ActionsToMeetGoalsSubAgent: SupervisorAgent: ReportingAgent: SupervisorAgent: Output back to user

1:0:5: WS connection validate WS is working correctly end to end. From user example message through WS back and forth through final message.

1:0:6: Update documentation in docs/subagents.md on 1:0:0-1:011 and related concepts.  
1:0:7: Check Lifecycle and shut down concepts  
1:0:8: Every SubAgent have all required fields to operate completed. E.g. its prompt definition etc. all completely filled out. 

Remember: 0:7.  Remember: 0:1 to 0:7 to 1 including all sub items 1:0:0 through 1:0:8.