---
description: "Git Issue progressor"
argument-hint: "[focus area, defaults to latest]"
---

You MUST keep going until issue is closed.
AS LONG AS IT TAKES KEEP GOING ALL NIGHT. At ONE FULL DAY OF WORK.

Have sub agents use built in github tools or direct `git` or `gh` if needed.
ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.

Focus areas (output this to console) is ISSUE: ${1 : latest}
 
SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
ALL Github output MUST follow @GITHUB_STYLE_GUIDE.md

PROCESS INSTRUCTIONS START:

0) READ ISSUE : SNST: Use gh to read the ISSUE ${1 : latest open issue} in question.

1) STATUS UPDATE : SNST : AUDIT the current codebase and linked PRs (closed and open) with FIVE WHYS approach and assess the current state of the issue.
1.1) Make or UPDATE a comment on the ISSUE with your learnings following @GITHUB_STYLE_GUIDE.md .
OUTPUT the comment ID here:

2) STATUS DECISION : SNST : (Pass context from 1): 
IF the issue appears to already be resolved close the issue and repeat PROCESS loop, otherwise continue to the next step.
2.1) UPDATE the existing comment on the ISSUE with your learnings following @GITHUB_STYLE_GUIDE.md  .

OPTIONAL STEPS IF ISSUE IS OPEN:

3) PLAN TEST : SNST : (Pass context from 1 and 2):
PLAN ONLY the update, align, or creation of: the required unit, integration (non-docker), or e2e gcp staging tests, with desired level of failing or not, difficulty, etc.: suites focused
on reproducing the item in question (failing tests). following reports\testing\TEST_CREATION_GUIDE.md
and all of the latest testing best practices as per claude.md
ONLY RUN tests that don't require docker, such as unit, integration (no docker), or e2e on staging gcp remote.
3.1) UPDATE a comment on the ISSUE with the TEST PLAN following @GITHUB_STYLE_GUIDE.md.

4) EXECUTE THE TEST PLAN : SNST : with new spawned sub agent. audit and review the test. And run the fake test checks. 
ONLY RUN tests that don't require docker, such as unit, integration (no docker), or e2e on staging gcp remote.

Decision (one of): Fix the TEST if fixable OR
if very bad mark and report as such and go back to 3) with the new added info.
4.1) UPDATE a comment on the ISSUE with the test results and decision.

5) PLAN REMEDIATION ITEM SPECIFIC PLAN : SNST : 
PLAN ONLY THE REMEDIATION TO THE SYSTEM UNDER TEST.
to fix the original issue and pass the test too.
5.1) Make or UPDATE a comment on the ISSUE with the results.

6) EXECUTE THE REMEDIATION ITEM SPECIFIC PLAN: SNST :
6.1) Make or UPDATE a comment on the ISSUE with the results.
6.2) Git commit work in conceptual batches. 

7) PROOF: SNST : Spawn a sub agent PROVE THAT THE CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
otherwise go back and ensure that any code changes exclusively add value as one atomic package of commit and
do not introduce new problems.
7.1) Make or UPDATE a comment on the ISSUE with PROOF.

8) PR AND CLOSURE: SNST:
8.1) Git commit remaining related work in conceptual batches. 
8.2) Make a NEW PR (Pull Request).
8.3) Cross link the prior generated issue so it will close on PR merge.

END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS until success ALL NIGHT. At least 8-20+ hours.
EVERY NEW PROCESS ENTRY MUST SPAWN NEW SNST FOR EACH ITEM.
STOP AFTER 3 PROCESS CYCLES OR IF THE ISSUE IS CLOSED.