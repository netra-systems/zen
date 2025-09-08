---
description: "Action this issue command"
argument-hint: "[issue, or link to .md file]"
---

ACTION These ISSUEs following this PROCESS for each item:

$1


EXPECT THERE MAY BE MULTIPLE ITEMS AND REPEAT WHOLE PROCESS AS NEEDED.

PROCESS:
For EACH ITEM!!:

0) Five whys root root root cause analaysis.

1) PLAN TEST: Spawn a sub agent to PLAN ONLY the update, align, or creation of: the required unit, integration (non-docker), or e2e gcp staging tests, with desired level of failing or not, difficulty, etc.: suites focused
on reproducing the item in question (failing tests). following reports\testing\TEST_CREATION_GUIDE.md
and all of the latest testing best practices as per claude.md

2) EXECUTE THE TEST PLAN with new spawned sub agent. audit and review the test. And run the fake test checks. Fix issues if fixable or if entirely bad mark and report as such and go back to 0) with the new added info.

3) PLAN REMEDIATION ITEM SPECIFIC PLAN: Spawn a sub agent to PLAN ONLY THE REMEDIATION TO THE SYSTEM UNDER TEST.
to fix the original issue and pass the test too.

4) EXECUTE THE REMEDIATION ITEM SPECIFIC PLAN.  Spawn a sub agent team to complete this.

5) Spawn a sub agent PROVE THAT THE CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
otherwise go back and ensure that any code changes exclusively add value as one atomic package of commit and
do not introduce new problems.

6) Save work in progress to report log

7) git commit.

You must update and save your work

MUST Keep going and repeating the entire test creation PROCESS until ALL NEEDED items are complete. Expect this to take at least 8-20+ hours.

