---
description: "PR Merger"
argument-hint: "[PR Number]"
---

# 🚨 ULTRA THINK DEEPLY ALWAYS. COMPLETE FEATURE FREEZE.

Your goals are to:
1. Safely merge a PR (PR = Pull Request)

Context:
1. You must keep going until all work is fully completed.
2. Have sub agents use built in github tools or direct `git` or `gh` if needed. ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
3. Focus areas (output this to console) of SSOT: ${1 : latest}
4. SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
5. ALL Github output (issues, comments, prs etc.) MUST follow @GITHUB_STYLE_GUIDE.md
6. FIRST DO NO HARM. Your mandate is to SAFELY see IF the PR can be merged.
7. PR-WORKLOG = PR-WORKLOG-${1 : latest}-{date-time}.md
8. PR-WORKLOG-UPDATE = Update PR-WORKLOG.
9. PR-WORKLOG-UPDATE-PUSH = 1:PR-WORKLOG-UPDATE 2: Git commit and push safely (stop if not safe)
10. UPDATE-PR-COMMENT = UPDATE a comment on the PR with the human readable noise-free updates (per @GITHUB_STYLE_GUIDE.md)
11. -
12. LIMIT SCOPE. Only do the MINIMUM number of changes per issue required to safely do one "atomic" unit
that improve SSOT coverage while keeping system state.
13. -
14. PR = Pull Request

PROCESS INSTRUCTIONS START:


0) READ PR : SNST: Use gh to read the PR ${1 : latest open PR} in question.
Create PR-WORKLOG
Do PR-WORKLOG-UPDATE

1) Resolve Merge Conflicts : SNST:
Safely attempt to resolve merge conflicts
Stop if cannot.
Do PR-WORKLOG-UPDATE


END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS until success.
EVERY NEW PROCESS ENTRY MUST SPAWN NEW SNST FOR EACH ITEM.
STOP AFTER 3 PROCESS CYCLES