---
description: "Test Gardener"
argument-hint: "[focus area, defaults to latest]"
---


Context
1. You must keep going until all work is fully completed.
2. Use github tools or direct `git` or `gh` if needed. ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
You MUST follow @GITHUB_STYLE_GUIDE.md
3. TEST UPDATES: ${1 : all}. This is your focus area.
4. SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
5. -
6. FIRST DO NO HARM. Your mandate is to SAFELY progress issues.
ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
7. ALL_TESTS = all unit, integration (non-docker), e2e gcp staging tests

After reading instructions output the issue to console.

PROCESS INSTRUCTIONS START:

Discover ALL_TESTS tests that won't collect or have import issues

For each conceptual set of issues Spawn a new agent (SNST) 
to remediate it.

END PROCESS INSTRUCTIONS
