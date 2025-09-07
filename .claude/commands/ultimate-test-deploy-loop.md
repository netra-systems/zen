---
description: "Real e2e test fix deploy loop"
argument-hint: "[focus area]"
---

You MUST repeat ALL steps until ALL 466 e2e real staging tests pass. WAIT AS LONG AS IT TAKES KEEP GOING ALL NIGHT

Steps:
1 Run real e2e staging tests with a focus on $1 on staging GCP (remote) as per tests\e2e\STAGING_E2E_TEST_INDEX.md
2 Document the ACTUAL TEST OUTPUT and save and prove it passes or fails in reports at each step.
3 For each failure, spawn a multi-agent team to do a five whys bug fix per claude.md (access the GCP logs for errors)
4 MAKE A GIT COMMIT FOR THIS.
5 Re-Deploy the service
6 WAIT then go back to 1