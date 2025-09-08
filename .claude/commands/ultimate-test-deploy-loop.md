---
description: "Real e2e test fix deploy loop"
argument-hint: "[focus area]"
---

You MUST repeat ALL steps until ALL 1000 e2e real staging tests pass. WAIT AS LONG AS IT TAKES KEEP GOING ALL NIGHT

Steps:
0 Deploy the service if it hasn't been deployed last few minutes. WAIT for service revision success
1 Run real e2e staging tests with a focus on $1 on staging GCP (remote) as per tests\e2e\STAGING_E2E_TEST_INDEX.md
2 Document the ACTUAL TEST OUTPUT and save and prove it passes or fails in reports at each step. Validate the test actually ran and is real e.g. real time running, real output that makes sense. If needed fix the test itself.
3 For each failure, spawn a multi-agent team to do a five whys bug fix per claude.md (Read the GCP staging logs for errors too). MUST BE SSOT. MUST solve the REAL ROOT ROOT ROOT ISSUE.
4 Spawn a new agent to audit SSOT and prove with evidence or disprove
5 PROVE THAT YOUR CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
otherwise go back and ensure that any code changes exclusively add value as one atomic package of commit and
do not introduce new problems.
6 IF the change is false go back to step 3
7 Git commit
8 Go back to 1