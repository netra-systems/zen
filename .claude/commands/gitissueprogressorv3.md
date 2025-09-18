---
description: "Git Issue progressor V3 SINGLE for use with orchestration"
argument-hint: "[focus area, defaults to latest]"
---

Have sub agents use built in github tools or direct `git` or `gh` if needed.

By default, ignore issues with the tag "actively-being-worked-on" and that have an "agent-session-{datetime}" within the last 20 minutes. Note: Expect multiple "agent-session-{datetime}" tags.

ISSUE: ${1 : one recent open issue}
 
If ISSUE is not a single literal number:
    Search git issues to determine most important issue to work on relative to ISSUE text.
    Be mindful of dependency tags
    Then set ISSUE = to that number

SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
ALL Github content must follow @GITHUB_STYLE_GUIDE.md

**CRITICAL BRANCH SAFETY POLICY:**
- ALWAYS stay on Branch = develop-long-lived
- **All work performed on**: develop-long-lived
- **PR target**: develop-long-lived (current working branch) - NEVER main

Issue Exclusion List (IEL): generally do not create issues for the following cases:
    1. merge conflicts
    2. local env specific issues

PROCESS INSTRUCTIONS START:

AGENT_SESSION_ID = agent-session-{datetime}

0) BRANCH SAFETY CHECK : SNST: 
    Verify current branch is develop-long-lived: `git branch --show-current`
    If not on develop-long-lived, STOP and switch: `git checkout develop-long-lived`
    Record branch state for safety monitoring throughout process.
    pull latest, and handle merge conflicts
    add a tags to the issue: actively-being-worked-on, AGENT_SESSION_ID

1) READ ISSUE : SNST: Use gh to read the ISSUE in question.

    STATUS UPDATE : 
    AUDIT the current codebase and linked PRs (closed and open) with FIVE WHYS approach and assess the current state of the issue.
    1.1) Make or UPDATE a comment on the ISSUE with your learnings following @GITHUB_STYLE_GUIDE.md .
    OUTPUT the comment ID here:

    2) STATUS DECISION :
    IF the issue appears to already be resolved:
        close the issue and repeat PROCESS loop, otherwise continue to the next step.
        If closing issue: remove label: actively-being-worked-on
        update the existing comment on the ISSUE with your learnings

OPTIONAL STEPS IF ISSUE IS OPEN:

3) PLAN TEST : SNST : (Pass context from 1 and 2):
    First pull latest, and handle merge conflicts

    PLAN ONLY the update, align, or creation of: the required unit, integration (non-docker), or e2e gcp staging tests, with desired level of failing or not, difficulty, etc.: suites focused
    on reproducing the item in question (failing tests). following reports\testing\TEST_CREATION_GUIDE.md
    and all of the latest testing best practices as per claude.md
    ONLY RUN tests that don't require docker, such as unit, integration (no docker), or e2e on staging gcp remote.
    3.1) UPDATE the comment on the ISSUE with the TEST PLAN following @GITHUB_STYLE_GUIDE.md.

4) EXECUTE THE TEST PLAN : SNST : with new spawned sub agent. audit and review the test. And run the fake test checks. 
ONLY RUN tests that don't require docker, such as unit, integration (no docker), or e2e on staging gcp remote.

Decision (one of): Fix the TEST if fixable OR
if very bad mark and report as such and go back to 3) with the new added info.
4.1) UPDATE the comment on the ISSUE with the test results and decision

5) PLAN REMEDIATION ITEM SPECIFIC PLAN : SNST : 
    PLAN ONLY THE REMEDIATION TO THE SYSTEM UNDER TEST.
    to fix the original issue and pass the test too.
    5.1) UPDATE the comment on the ISSUE with the results

6) EXECUTE THE REMEDIATION ITEM SPECIFIC PLAN: SNST :
    6.1) UPDATE the comment on the ISSUE with the results
    6.2) Run startup tests (non docker) fix import or other types of startup issues related to this change.
    6.3) Git commit work in conceptual batches. 
    6.4) Sync with origin: push/pull latest, and handle merge conflicts

7) PROOF: SNST : Spawn a sub agent PROVE THAT THE CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
otherwise go back and ensure that any code changes exclusively add value as one atomic package of commit and
do not introduce new problems.
7.1)  Run startup tests (non docker) fix import or other types of startup issues related to this change.
7.2) UPDATE a comment on the ISSUE with PROOF  following @GITHUB_STYLE_GUIDE.md  .

*Skip step 8 if recently deployed*
8) Staging Deploy SNST :  Spawn a sub agent PROVE THAT THE CHANGES WORK OR FAIL IN STAGING.
8.1) Deploy the service (only deploy the service(s) with the files edited/updated)
if it hasn't been deployed last 3 minutes.
8.2) WAIT for service revision success or failure.
8.3) Read service logs to audit no net new breaking changes
8.4) Run relevant tests on staging gcp (either newly created tests and relevant existing e2e tests related to this)
8.5) UPDATE a comment with Staging deploy information  following @GITHUB_STYLE_GUIDE.md  .
8.6) IF new directly related and significant issues introduced log them and exit process, restart process from 1) (exit this agent and go back to main loop so it can spawn new agents)

9) PR AND CLOSURE: SNST:
9.1) Git commit remaining related work in conceptual batches. 
9.2) **SAFE PR CREATION**: Create PR WITHOUT changing current branch:
    - Record current branch (should be develop-long-lived): `git branch --show-current`
    - pull latest, and handle merge conflicts
    - Create feature branch remotely: `git push origin HEAD:feature/issue-${ISSUE_NUMBER}-$(date +%s)`
    - Create PR from feature branch to current branch: `gh pr create --base develop-long-lived --head feature/issue-${ISSUE_NUMBER}-$(date +%s) --title "Fix: Issue #${ISSUE_NUMBER}" --body "Closes #${ISSUE_NUMBER}"`
    - VERIFY current branch unchanged: `git branch --show-current`
    - **CRITICAL**: Never checkout different branches - work stays on develop-long-lived
    - **PR MERGES TO**: Current working branch (develop-long-lived) - NEVER main
9.3) Cross link the prior generated issue so it will close on PR merge.
9.4) **PR TARGET VALIDATION**: Ensure PR merges back to current working branch (develop-long-lived)
9.5) Do a final update for this loop
    If closing issue: remove label: actively-being-worked-on

END PROCESS INSTRUCTIONS
