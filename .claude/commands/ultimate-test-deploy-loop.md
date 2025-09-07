---
description: "Real e2e test fix deploy loop"
---

Run real e2e staging tests on staging GCP (remote) as per tests\e2e\STAGING_E2E_TEST_INDEX.md
Document the ACTUAL TEST OUTPUT and save and prove it passes or fails in reports at each step.
For each failure, spawn a multi-agent team to do a five whys bug fix per claude.md (access the GCP logs for errors)
MAKE A GIT COMMIT FOR THIS.
Re-Deploy the service

You MUST repeat ALL steps until ALL 466 e2e real staging tests pass. WAIT AS LONG AS IT TAKES KEEP GOING ALL NIGHT