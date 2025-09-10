---
description: "Test Gardener"
argument-hint: "[focus area, defaults to latest]"
---

 
Context
1. You must keep going until all work is fully completed.
2. Built in github tools or direct `git` or `gh` if needed. ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
You MUST follow @GITHUB_STYLE_GUIDE.md
3. TEST UPDATES: ${1 : all}. This is your focus area.
4. SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
5. ALL Github output (issues, titles, comments, prs etc.) MUST follow @GITHUB_STYLE_GUIDE.md
6. FIRST DO NO HARM. Your mandate is to SAFELY progress issues.
ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
7. ISSUE-WORKLOG = ISSUE-WORKLOG-${1 : latest}-{date-time}.md
8. ISSUE-WORKLOG-UPDATE = Update ISSUE-WORKLOG.
9. ISSUE-WORKLOG-UPDATE-PUSH = 1:ISSUE-WORKLOG-UPDATE 2: Git commit and push safely (stop if not safe)
10. UPDATE-ISSUE-COMMENT = UPDATE a comment on the ISSUE with the human readable noise-free updates (per @GITHUB_STYLE_GUIDE.md)


After reading instructions output the issue to console.

PROCESS INSTRUCTIONS START:

0) READ ISSUE: SNST: Use gh to read the ISSUE ${1 : latest open issue} in question.
Carefully read all issue comments.

1) Spawn a sub agent to PLAN ONLY the update, align, or creation of: the required unit, integration (non-docker), or e2e gcp staging tests, with desired level of failing or not, difficulty, etc.: suites focused on: $1

2) STATUS DECISION : SNST : (Pass context from 1): 
IF the issue appears to already be resolved close the issue and repeat PROCESS loop, otherwise continue to the next step.
ISSUE-WORKLOG-UPDATE; ISSUE-WORKLOG-UPDATE-PUSH

OPTIONAL STEPS IF ISSUE IS *OPEN*:

3) PLAN TEST : SNST : (Pass context from 1 and 2):
PLAN ONLY the update, align, or creation of: the required unit, integration (non-docker), or e2e gcp staging tests, with desired level of failing or not, difficulty, etc.: suites focused
on reproducing the item in question (failing tests). following reports\testing\TEST_CREATION_GUIDE.md
and all of the latest testing best practices as per claude.md
ONLY RUN tests that don't require docker, such as unit, integration (no docker), or e2e on staging gcp remote.
ISSUE-WORKLOG-UPDATE; ISSUE-WORKLOG-UPDATE-PUSH

4) EXECUTE THE TEST PLAN : SNST : with new spawned sub agent. audit and review the test. And run the fake test checks. 
ONLY RUN tests that don't require docker, such as unit, integration (no docker), or e2e on staging gcp remote.

Decision (one of): Fix the TEST if fixable OR
if very bad mark and report as such and go back to 3) with the new added info.
ISSUE-WORKLOG-UPDATE; ISSUE-WORKLOG-UPDATE-PUSH


5) PLAN REMEDIATION ITEM SPECIFIC PLAN : SNST : 
PLAN ONLY THE REMEDIATION TO THE SYSTEM UNDER TEST.
to fix the original issue and pass the test too.
ISSUE-WORKLOG-UPDATE; ISSUE-WORKLOG-UPDATE-PUSH

6) EXECUTE THE REMEDIATION ITEM SPECIFIC PLAN: SNST :
ISSUE-WORKLOG-UPDATE; ISSUE-WORKLOG-UPDATE-PUSH

7) PROOF: SNST : Spawn a sub agent PROVE THAT THE CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
otherwise go back and ensure that any code changes exclusively add value as one atomic package of commit and
do not introduce new problems.
ISSUE-WORKLOG-UPDATE; ISSUE-WORKLOG-UPDATE-PUSH

8) Staging Deploy SNST :  Spawn a sub agent PROVE THAT THE CHANGES WORK OR FAIL IN STAGING.
8.1) Deploy the service (only deploy the service(s) with the files edited/updated)
if it hasn't been deployed last 3 minutes.
8.2) WAIT for service revision success or failure.
8.3) Read service logs to audit no net new breaking changes
8.4) Run relevant tests on staging gcp (either newly created tests and relevant existing e2e tests related to this)
ISSUE-WORKLOG-UPDATE; ISSUE-WORKLOG-UPDATE-PUSH
8.6) IF new directly related and significant issues introduced log them and exit process, restart process from 1) (exit this agent and go back to main loop so it can spawn new agents)

9) PR AND CLOSURE: SNST:
9.1) Git commit remaining related work in conceptual batches. 
9.2) Make a NEW PR (Pull Request).
9.3) Cross link the prior generated issue so it will close on PR merge.
ISSUE-WORKLOG-UPDATE; ISSUE-WORKLOG-UPDATE-PUSH

END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS until success ALL NIGHT. At least 8-20+ hours.
EVERY NEW PROCESS ENTRY MUST SPAWN NEW SNST FOR EACH ITEM.
STOP AFTER 3 PROCESS CYCLES OR IF THE ISSUE IS CLOSED.