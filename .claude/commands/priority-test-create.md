---
description: "Create tests based on priority script"
---

Create the following tests following reports\testing\TEST_CREATION_GUIDE.md
and all of the latest testing best practices as per claude.md
YOU MUST create at least 100 real high quality tests in total.
Expect this work to take 20 hours.

For each test, the creation the process is:
1) Get testing priorities: python scripts/claude_coverage_command.py priorities
save results to a .md file
2) Spawn a sub agent to plan then create: unit, integration (non-docker!), and all real staging e2e tests.
For integration: These must be as realistic as possible!! NO MOCKS!!! Yet not require services to be actually running.
Be careful here this must fill gap between unit and e2e tests.
2) Spawn a new sub agent to audit and edit the test
3) Run the test
4) If needed, fix the system under test based on the failure
5) Save work in progress to report log

Keep going and repeating the entire test creation process until all tests are created 
YOU MUST create at least 100 real high quality tests in total.
Expect this work to take 20 hours.