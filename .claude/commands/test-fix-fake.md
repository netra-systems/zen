---
description: "Fix fake tests"
---

The goal is to create new tests based on spirit of tests with 'REMOVED_SYNTAX_ERROR' markings.
The new tests must follow the latest testing best practices as per claude.md

PROCESS:
1) Spawn a sub agent to find next test with REMOVED_SYNTAX_ERROR in it. create new tests based on spirit of tests. The new tests must follow the latest testing best practices as per claude.md
2) Spawn a new sub agent to audit and review the test. Fix issues.
3) Run the test
4) If needed, fix the system under test based on the failure
5) Delete the legacy test
6) Save work in progress to report log. git commit. 


You must update and save your work

MUST Keep going and repeating the entire test creation PROCESS until ALL NEEDED tests are created. Expect this to take at least 8 hours.

