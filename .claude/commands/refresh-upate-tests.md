---
description: "Refresh tests for existing area command"
argument-hint: "[focus area]"
---

Update, align, refresh, and if needed create new tests
for the following focus area:

$1

following reports\testing\TEST_CREATION_GUIDE.md
and all of the latest testing best practices as per claude.md

PROCESS:
For each test suite, the creation the process is:
0) PLAN: Spawn a sub agent to PLAN ONLY the update, align, or creation of: the required unit, integration (non-docker), or e2e gcp staging tests, with desired level of failing or not, difficulty, etc.: suites focused on: $1
1) EXECUTE THE PLAN with new spawned sub agent
2) Spawn a new sub agent to audit and review the test. And run the fake test checks. Fix issues if fixable or 
if entirely bad mark and report as such and go back to 0) with the new added info.
3) Run the tests and log results with evidence of output and pass fail, timing etc.
4) Spawn a sub agent If needed, fix the system under test based on the failure
5) Spawn a sub agent PROVE THAT THE CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
otherwise go back and ensure that any code changes exclusively add value as one atomic package of commit and
do not introduce new problems.
6) Save work in progress to report log
7) git commit.

You must update and save your work

MUST Keep going and repeating the entire test creation PROCESS until ALL NEEDED tests are created. Expect this to take at least 8 hours.

