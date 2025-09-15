---
description: "Git Issue Planner"
argument-hint: "[focus area, defaults to latest]"
---

Have sub agents use built in github tools or direct `git` or `gh` if needed.

By default, ignore issues with the tag "actively-being-worked-on"

ISSUE: ${1 : one recent open issue}

SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
ALL Github content must follow @GITHUB_STYLE_GUIDE.md

**CRITICAL BRANCH SAFETY POLICY:**
- ALWAYS stay on Branch = develop-long-lived
- **All work performed on**: develop-long-lived
- **PR target**: develop-long-lived (current working branch) - NEVER main
 
PROCESS INSTRUCTIONS START:

AGENT_SESSEION_ID = agent-session-{datetime}

Deeply think and plan out what to do based on the content of the issue.
First create the outline of the plan and save it as a comment on the isue
Then Spawn SNST as needed to action individual items.
Cross link work output from individual SNST agents as needed.

END PROCESS INSTRUCTIONS
