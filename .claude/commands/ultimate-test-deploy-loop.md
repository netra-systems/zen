---
description: "Real e2e test fix deploy loop (backend focused by default)"
argument-hint: "[focus area]"
---

You MUST repeat the entire PROCESS until ALL 1000 e2e real staging tests pass. WAIT AS LONG AS IT TAKES KEEP GOING ALL NIGHT. At least 8-20+ hours.

PROCESS INSTRUCTIONS START:

0) Deploy the backend service if it hasn't been deployed last few minutes. 
WAIT for service revision success

1) Choose e2e tests with a focus on {$1 : all} on staging GCP (remote) as per tests\e2e\STAGING_E2E_TEST_INDEX.md
Read recent logs in e2e/test_results/ for tests with ongoing issues or recently passed tests to do last.

Save the choice of tests a fresh LOG = e2e testing log. in e2e/test_results/ folder (or create it)
Literally output the named of the LOG.

2) Spawn a new sub agent to run real e2e staging tests with fail fast.
Validate the test actually ran and is real e.g. real time running, real output that makes sense. If needed fix the test itself.
Update the LOG with literal test output.
This is aving the ACTUAL TEST OUTPUT prove it passes or fails in reports at each step. 
Report failures back up to you


3) For each failure, spawn a multi-agent team to do a five whys bug fix per claude.md (Read the GCP staging logs for errors too). MUST BE SSOT. MUST solve the REAL ROOT ROOT ROOT ISSUE.
Update LOG with status.

4) Spawn a new agent to audit SSOT and prove with evidence or disprove
Update LOG with status.
IF the situation is bad, revert back to step 3) and repeat until 4) passes.

5) Spawn a new agent 
PROVE THAT PRIOR AGENTS CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
otherwise go back and ensure that any code changes exclusively add value as one atomic package of commit and
do not introduce new problems.
Update LOG with status.
IF the change is false go back to step 3

6) Git commit

END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS until ALL 1000 e2e real staging tests pass. WAIT AS LONG AS IT TAKES KEEP GOING ALL NIGHT. At least 8-20+ hours.