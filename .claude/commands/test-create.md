---
description: "Test Creation"
argument-hint: "[tests to be created]"
---

Create the following tests following reports\testing\TEST_CREATION_GUIDE.md
and all of the latest testing best practices as per claude.md

For each test, the creation the process is:
1) Spawn a sub agent to create the test
2) Spawn a new sub agent to audit and edit the test
3) Run the test
4) If needed, fix the system under test based on the failure
5) Save work in progress to report log

Keep going and repeating the entire test creation process until all tests are created 

Tests to create:
$1