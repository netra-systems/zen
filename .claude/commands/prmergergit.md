---
description: "PR Merger - Safe PR merging to working branch with remote branch management"
argument-hint: "[PR Number, defaults to all]"
---

Your goals are to:
1. Safely merge all PRs (PR = Pull Request) to the WORKING BRANCH
Maintain current working branch context during operations

PRs_To_MERGE = ${1 : all}

Context:
    1. You must keep going until all work is fully completed.
    2. Have sub agents use built in github tools or direct `git` or `gh` if needed. ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
    3. Branch policy:
        3.1. ALWAYS merge PRs to the WORKING BRANCH (develop-long-lived) - NEVER to main
        3.2. When creating branches for PRs: Create REMOTE branches WITHOUT changing current working branch
        3.3 Curent working branch**: develop-long-lived (as per CLAUDE.md)
    4. SNST = SPAWN NEW SUBAGENT TASK
    5. ALL Github output (issues, comments, prs etc.) MUST follow @GITHUB_STYLE_GUIDE.md
    6. FIRST DO NO HARM. Your mandate is to SAFELY merge the PR.
    7. PR-WORKLOG = PR-WORKLOG-{PRs_To_MERGE}-{date-time}.md
    8. PR-WORKLOG-UPDATE = Update PR-WORKLOG.
    9. PR-WORKLOG-UPDATE-PUSH = 1:PR-WORKLOG-UPDATE 2: Git commit and push safely (stop if not safe)
    10. UPDATE-PR-COMMENT = UPDATE a comment on the PR with the human readable noise-free updates (per @GITHUB_STYLE_GUIDE.md)
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

For each PR in PRs_To_MERGE:

    PROCESS INSTRUCTIONS START:

    0) BRANCH STATUS CHECK :
        Check current branch status and ensure we're on develop-long-lived working branch.
        Record current branch state for safety.
        Safely git push and pull
        Create PR-WORKLOG
        Do PR-WORKLOG-UPDATE

    1) READ PR : SNST: Use gh to read the PR and PR comments in question.
        Identify:
        - PR source branch
        - Verify PR target branch == develop-long-lived OR set = develop-long-lived
        - PR conflicts status
        - PR approval status
        Do PR-WORKLOG-UPDATE
        - DECISION: If there are no merge conflicts, merge the branch directly and close the PR, then Do PR-WORKLOG-UPDATE and go to next loop (next PR) skip remaining steps.

    2) Start merge and RESOLVE MERGE CONFLICTS:
        - Use `git fetch origin` to get latest changes
        - Start merging the source branch into develop-long-lived.
        - If conflicts exist, resolve conflicts safely.
        Do PR-WORKLOG-UPDATE

    3) SAFE PR Merge and close PR : SNST:
        Using GitHub CLI to merge and close the PR to develop-long-lived:
        - Verify PR status: `gh pr status [PR#]`
        - Confirm target is develop-long-lived: `gh pr view [PR#] --json baseRefName`
        - Execute merge: `gh pr merge [PR#] --merge --delete-branch`
        - Verify merge success on develop-long-lived
        - UPDATE-PR-COMMENT with merge confirmation
        Do PR-WORKLOG-UPDATE-PUSH

    4) POST-MERGE VERIFICATION:
        - Confirm current branch is still develop-long-lived
        - Verify merged changes appear in develop-long-lived
        - Run basic health check: `git log --oneline -5`
        - Document successful merge in PR-WORKLOG
        Do PR-WORKLOG-UPDATE-PUSH

    END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS until all PRs_To_MERGE are complete.