---
description: "PR Merger - Safe PR merging to working branch with remote branch management"
argument-hint: "[PR Number, defaults to all]"
---

WORKING_BRANCH = develop-long-lived

Your goals are to:
1. Safely merge all PRs (PR = Pull Request) to the WORKING_BRANCH.
Maintain current working branch context during operations

PRs_To_MERGE = ${1 : all}

Context:
    1. You must keep going until all work is fully completed.
    2. Have sub agents use built in github tools or direct `git` or `gh` if needed. ALWAYS think about overall repo safety and stop or skip operations if anything might damage overall health of repo.
    3. Branch policy:
        3.1. ALWAYS merge PRs to the WORKING_BRANCH - NEVER to main
        3.2. Merge directly into the WORKING_BRANCH
    4. SNST = SPAWN NEW SUBAGENT TASK
    5. ALL Github output (issues, comments, prs etc.) MUST follow @GITHUB_STYLE_GUIDE.md
    6. FIRST DO NO HARM. Your mandate is to SAFELY merge the PR.
    7. PR-WORKLOG = PR-WORKLOG-{PRs_To_MERGE}-{date-time}.md
    8. PR-WORKLOG-UPDATE = Update PR-WORKLOG.
    9. PR-WORKLOG-UPDATE-PUSH = 1:PR-WORKLOG-UPDATE 2: Git commit and push safely (stop if not safe)
    10. UPDATE-PR-COMMENT = UPDATE a comment on the PR with the human readable noise-free updates.
    11. -
    12. LIMIT SCOPE. Only do the MINIMUM number of changes per issue required to safely do one "atomic" unit
    that improve SSOT coverage while keeping system state.
    13. TARGET BRANCH Always target develop-long-lived for merges (working branch)
    14. **CRITICAL SAFETY RULES:**
        - NEVER checkout main branch
        - NEVER merge to main branch  
        - NEVER change from develop-long-lived during operations
        - ALWAYS verify branch target before merging
        - SKIP and do something different if any operation attempts to modify main

For each PR in PRs_To_MERGE (SNST):

    PROCESS INSTRUCTIONS START:

    0) BRANCH STATUS CHECK :
        Check current branch status and ensure we're on develop-long-lived working branch.
            Record current branch state for safety.
        Safely git pull and push, clean working state.
        If needed solve merge conflicts with local WORKING_BRANCH and origin WORKING_BRANCH
        Create PR-WORKLOG
        Do PR-WORKLOG-UPDATE

    1) READ PR: Use gh to read the PR and PR comments in question.
        - Verify PR target branch == WORKING_BRANCH
            OR set = WORKING_BRANCH
        - PR conflicts status
        Do PR-WORKLOG-UPDATE
        - DECISION: 
            If there are no merge conflicts,
                merge the branch directly and close the PR, 
                then Do PR-WORKLOG-UPDATE 
                and go to next loop (next PR) skip remaining steps.

    2) Start merge and RESOLVE MERGE CONFLICTS:
        - Use `git fetch origin` to get latest changes
        - Start merging the source branch into develop-long-lived.
        - If conflicts exist, resolve conflicts safely.
        - Do PR-WORKLOG-UPDATE

    3) SAFE PR Merge and close PR:
        Merge and close the PR to WORKING_BRANCH:
        - Verify PR status: `gh pr status [PR#]``
        - Execute merge
        - Verify merge success on develop-long-lived
        - UPDATE-PR-COMMENT with merge confirmation
        - Do PR-WORKLOG-UPDATE-PUSH

    4) POST-MERGE VERIFICATION:
        - Confirm current branch is still develop-long-lived
        - Verify merged changes appear in develop-long-lived
        - Run basic health check: `git log --oneline -5`
        - Document successful merge in PR-WORKLOG
        Safely git pull and push, clean working state.
        If needed solve merge conflicts with local WORKING_BRANCH and origin WORKING_BRANCH
        Do PR-WORKLOG-UPDATE-PUSH

    END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS until all PRs_To_MERGE are complete.