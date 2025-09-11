---
description: "Failing tests Gardener. ONLY creates issues does not attempt to remediate them. Use the github issue progressor for that."
argument-hint: "[test focus area]"
---

Your goals are to:
    1. Collect test issues and errors not yet in github issues

    TEST-FOCUS = ${1 : ALL_TESTS}

Context:
    1. You must keep going until all work is fully completed.
    2. Have sub agents use built in github tools or direct `git` or `gh` if needed. ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
    3. ALL_TESTS = all unit, integration (non-docker), e2e staging tests
    4. SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
    5. ALL Github output (issues, comments, prs etc.) MUST follow @GITHUB_STYLE_GUIDE.md
    Use label: "claude-code-generated-issue"
    6. FIRST DO NO HARM.
    7. FAILING-TEST-GARDENER-WORKLOG = FAILING-TEST-GARDENER-WORKLOG-{TEST-FOCUS}-{date-time}.md
    8. FAILING-TEST-GARDENER-WORKLOG-UPDATE = Update FAILING-TEST-GARDENER-WORKLOG.
    9. FAILING-TEST-GARDENER-WORKLOG-UPDATE-PUSH = 1:FAILING-TEST-GARDENER-WORKLOG-UPDATE 2: Git commit and pull / push safely (skip if not safe)
    10. UPDATE-COMMENT = UPDATE a comment on one of (Issue, PR) with the human readable noise-free updates.
    11. -
    12. LIMIT SCOPE. Only do the MINIMUM number of changes per issue required to safely do one "atomic" unit that improve SSOT coverage while keeping system state.


MASTER AGENT:
    1. Run TEST-FOCUS tests.
    2. Save the discovered issues to a fresh FAILING-TEST-GARDENER-WORKLOG in FAILING-TEST/gardener/ folder (or create it)
    3. for each issue start a new PROCESS with SNST:

        PROCESS INSTRUCTIONS START (SNST):

        0) Search if there is an existing issue similar to this.
        If there is an open issue, then make an update comment with most recent logs and context. If relevant, update the title and issue tags.

        Else: make a new issue with this format:
        {choose one - failing | uncollectable | {other} }-test-{choose one - regression | new | active-dev, or other category descriptor}-{severity level}-{human skimable name}
        
        PRIORITY TAG ASSIGNMENT (MANDATORY):
        Always assign a priority tag based on severity:
        - P0: Critical/blocking - system down, data loss, security vulnerability
        - P1: High - major feature broken, significant user impact
        - P2: Medium - minor feature issues, moderate user impact  
        - P3: Low - cosmetic issues, nice-to-have improvements

        1) Linking
        1.1 If other related (open or closed) issues are discovered that are relevant, link them to the issue.
        1.2 Link other relevant items, such as other related issues, other PRs, other related docs.
        1.3 FAILING-TEST-GARDENER-WORKLOG-UPDATE-PUSH

        END PROCESS INSTRUCTIONS


Repeat until all TEST-FOCUS have gone through the PROCESS.