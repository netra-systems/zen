
IMPORTANT:
Two processes

Process A:
A: A:1 Continuously audit docker compose local dev logs for issues (logs that look wrong, repeating logs, errors, etc.)
A:2: Create a todo to track issues.
A:3: Active new agent for process B (with maximum concurrency of 3 at a time)
If at concurrency limit then wait to spawn new agent
A:4: Continue automatically, pausing for 50 seconds if zero new issues found
 
Process B:
B: for each issue: assign a sub agent team to work on it, fixing infra or system under test (SUT) as needed. Update a unified .md report for all issues with new information about each failure and solution.

