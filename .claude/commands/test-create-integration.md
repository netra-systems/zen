---
description: "Test Creation Integration"
argument-hint: "[Focus area]"
---

Create the following tests following reports\testing\TEST_CREATION_GUIDE.md
and all of the latest testing best practices as per claude.md
YOU MUST create at least 100 real high quality tests in total.
Expect this work to take 20 hours.

For each test, the creation the process is:
1) Spawn a sub agent to create a integration test (non-docker) with a focus on $1.
These must be as realistic as possible!! NO MOCKS!!! Yet not require services to be actually running.
Be careful here this must fill gap between unit and e2e tests.
2) Spawn a new sub agent to audit and edit the test
3) Run the test
4) If needed, fix the system under test based on the failure
5) PROVE THAT YOUR CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
otherwise go back and ensure that any code changes exclusively add value as one atomic package of commit and
do not introduce new problems.
6) Save work in progress to report log

Keep going and repeating the entire test creation process until all tests are created 
YOU MUST create at least 100 real high quality tests in total.
Expect this work to take 20 hours.