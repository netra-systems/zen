---
description: "Refresh Gardener"
argument-hint: "[focus area, defaults to latest]"
---

Your goal is to refresh and update docs.

1. Have sub agents use built in github tools or direct `git` or `gh` if needed.
2. SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
3. ALL Github content must follow @GITHUB_STYLE_GUIDE.md
4. BRANCH SAFETY POLICY:
- ALWAYS stay on Branch = develop-long-lived
- **All work performed on**: develop-long-lived
- **PR target**: develop-long-lived (current working branch) - NEVER main

DEFAULT_FOCUS = [Docs]

FOCUS_AREA = ${ 1 : DEFAULT_FOCUS}

for each TASK in FOCUS_AREA:

    PROCESS INSTRUCTIONS START:

    AGENT_SESSION_ID = agent-session-{datetime}

    0) BRANCH SAFETY CHECK : SNST: 
        Verify current branch is develop-long-lived: `git branch --show-current`
        If not on develop-long-lived, STOP and switch: `git checkout develop-long-lived`
        Record branch state for safety monitoring throughout process.
        pull latest, and handle merge conflicts

    1) DOCS:
        1.1 Refresh primary readme
        1.2 Refresh Work in progress index
        1.3 Refresh other important indexes
        1.4 Refresh string literals
        1.5 Refresh test coverage docs
        1.6 Refresh golden path docs
        including GOLDEN_PATH_USER_FLOW_COMPLETE.md
            
        1.7 Refresh SSOT docs
        1.8 Refresh other important docs

    2) pull latest, and handle merge conflicts, commit and push work to origin.

    END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS until all DEFAULT_FOCUS tasks are complete.
EVERY NEW PROCESS ENTRY MUST SPAWN NEW SNST