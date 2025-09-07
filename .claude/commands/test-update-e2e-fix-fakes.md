---
description: "Fix fake tests"
---

The goal is to FIX FAKE TESTS. By removing ALL CHEATING parts of the test.
The new tests must follow the latest testing best practices as per claude.md
Examples include removing cheating things like bad try/catch blocks
Or not actually raising on things it REALLY SHOULD RAISE for. fake comment excuses etc.

PROCESS:
1) Spawn a sub agent to find next e2e tests with cheating in it. 
2) Spawn a new sub agent to audit and make the test cheat free.
3) Run the test
4) If needed, fix the system under test based on the failure
5) Delete the legacy test
6) Save work in progress to report log. git commit. 

You must update and save your work

MUST Keep going and repeating the entire test creation PROCESS until ALL NEEDED tests are update. Expect this to take at least 8 hours.

