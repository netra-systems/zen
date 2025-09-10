---
description: "SSOT Gardener"
argument-hint: "[focus area, defaults to latest]"
---

# 🚨 ULTRA THINK DEEPLY ALWAYS. COMPLETE FEATURE FREEZE.

**CRITICAL MISSION:** Get Golden Path working - users login and get AI responses back.
Your goals are to:
1. Discover and remediate SSOT (Single Source of Truth) violations blocking golden path
2. Discover and remediate SSOT issues creating infinite or bad debugging loops.
3. Discover and remediate legacy issues, especially incomplete migrations to SSOT.

Context
1. You must keep going for at least 10 hours.
2. Have sub agents use built in github tools or direct `git` or `gh` if needed. ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
3. Focus areas (output this to console) is SSOT ISSUE: ${1 : latest}
4. SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
5. ALL Github output (issues, comments, prs etc.) MUST follow @GITHUB_STYLE_GUIDE.md
6. FIRST DO NO HARM. Your mandate is to SAFELY refresh to SSOT methods.
This means ensuring that SSOT updates pass tests (updating tests themselves when needed).
7. IND = {issue name}.md 
8. GCIFS = Git commit and push the IND updates if safe to do so.
9. IND; GCIFS = Save to IND and then Action GCIFS

PROCESS INSTRUCTIONS START:

0) Discover Next SSOT Issue (SSOT AUDIT) : SNST: 
0.1) Starting with the ${1 : latest} SSOT Critical index, most to least important, 
use tools to search through codebase and find the most important SSOT violations.
0.2) Make or update github ISSUE.
Minimize noise, focus on just a few readable lines of most critical context. Link to other docs for remaining context.
Issue name style: SSOT-{context (one of: regression, incomplete-migration, recent-change, {custom})}-{brief human description}}
Create a local md file (IND = {issue name}.md) with the same name ending in .md to record your work in progress
OUTPUT the issue name, .md progress tracker name {issue name}.md, and github link.
Action: IND; GCIFS

1) DISCOVER AND PLAN TEST : SNST : (Pass context from 0):

1.1) DISCOVER EXISTING: find collection of existing tests
tests protecting against breaking changes made by SSOT refactor or similar
After refactors: these tests must continue to pass, or now pass if failing prior, or updated as a test and pass.
IND; GCIFS

1.2) PLAN ONLY Plan for update, align, or creation of: the required unit,
integration (non-docker), or e2e gcp staging tests, with desired level of failing or not, difficulty, etc.: suites focused
on ideal code state AFTER SSOT refactor, gaps in current test coverage, and
to reproducing the SSOT violation in question (failing tests!). following reports\testing\TEST_CREATION_GUIDE.md
and all of the latest testing best practices as per claude.md
Save to IND

1.2.notes)
ONLY RUN tests that don't require docker, such as unit, integration (no docker), or e2e on staging gcp remote.
~20% of work is validating SSOT fixes, 60% existing tests (with updates if needed), ~20% new tests

1.3) UPDATE a comment on the ISSUE with the human readable noise-free IND updates


4) EXECUTE THE TEST PLAN : SNST : with new spawned sub agent. audit and review the test. And run the fake test checks. 
ONLY RUN tests that don't require docker, such as unit, integration (no docker), or e2e on staging gcp remote.

Decision (one of): Fix the TEST if fixable OR
if very bad mark and report as such and go back to 3) with the new added info.
4.1) UPDATE the comment on the ISSUE with the test results and decision following @GITHUB_STYLE_GUIDE.md  .

5) PLAN REMEDIATION ITEM SPECIFIC PLAN : SNST : 
PLAN ONLY THE REMEDIATION TO THE SYSTEM UNDER TEST.
to fix the original issue and pass the test too.
5.1) UPDATE the comment on the ISSUE with the results following @GITHUB_STYLE_GUIDE.md  .

6) EXECUTE THE REMEDIATION ITEM SPECIFIC PLAN: SNST :
6.1) UPDATE the comment on the ISSUE with the results following @GITHUB_STYLE_GUIDE.md  .
6.2) Git commit work in conceptual batches. 

7) PROOF: SNST : Spawn a sub agent PROVE THAT THE CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
otherwise go back and ensure that any code changes exclusively add value as one atomic package of commit and
do not introduce new problems.
7.1) UPDATE a comment on the ISSUE with PROOF  following @GITHUB_STYLE_GUIDE.md  .

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
9.2) Make a NEW PR (Pull Request).
9.3) Cross link the prior generated issue so it will close on PR merge.
9.4) Do a final update for this loop  following @GITHUB_STYLE_GUIDE.md  .

END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS until success ALL NIGHT. At least 8-20+ hours.
EVERY NEW PROCESS ENTRY MUST SPAWN NEW SNST FOR EACH ITEM.
STOP AFTER 3 PROCESS CYCLES OR IF THE ISSUE IS CLOSED.