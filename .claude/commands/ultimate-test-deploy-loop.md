---
description: "Real e2e test fix deploy loop (backend focused by default)"
argument-hint: "[focus area]"
---

Your goals are to:
1. Run E2E tests. 
2. If needed: Remediate issues & create a PR (Pull Request).

Context:
1. You must keep going until all work is fully completed.
2. Have sub agents use built in github tools or direct `git` or `gh` if needed. ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
3. Focus areas (output this to console) of SSOT: ${1 : latest}
4. SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
5. ALL Github output (issues, comments, prs etc.) MUST follow @GITHUB_STYLE_GUIDE.md
6. FIRST DO NO HARM. Your mandate is to SAFELY see IF the PR can be merged.
7. E2E-DEPLOY-REMEDIATE-WORKLOG = E2E-DEPLOY-REMEDIATE-WORKLOG-${1 : latest}-{date-time}.md
8. E2E-DEPLOY-REMEDIATE-WORKLOG-UPDATE = Update E2E-DEPLOY-REMEDIATE-WORKLOG.
9. E2E-DEPLOY-REMEDIATE-WORKLOG-UPDATE-PUSH = 1:E2E-DEPLOY-REMEDIATE-WORKLOG-UPDATE 2: Git commit and push safely (stop if not safe)
10. UPDATE-COMMENT = UPDATE a comment on one of (Issue, PR) with the human readable noise-free updates.
11. -
12. LIMIT SCOPE. Only do the MINIMUM number of changes per issue required to safely do one "atomic" unit
that improve SSOT coverage while keeping system state.



PROCESS INSTRUCTIONS START:

0) Check recent backend service revisions.
If it hasn't been deployed in last few minutes do a fresh deploy with scripts\deploy_to_gcp.py
WAIT for service revision success.

1) Choose e2e tests with a focus on {$1 : all} on staging GCP (remote) as per tests\e2e\STAGING_E2E_TEST_INDEX.md
Read recent logs in e2e/test_results/ for tests with ongoing issues or recently passed tests to do last.
Save the choice of tests a fresh LOG = e2e testing log. in e2e/test_results/ folder (or create it)
Literally output the named of the LOG.

1.1) GITHUB ISSUE INTEGRATION
Update existing issue or create new GITHUB ISSUE 
using tools shown in GITHUB_INTEGRATION_IMPLEMENTATION_REPORT.md or if missing tool local `gh` command.
Tag issue with label: "claude-code-generated-issue"
Output to console the issue path

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

6)  GITHUB PR INTEGRATION
Use github python tools or local (gh) commands.
Git commit in conceptual batches. Then make a NEW PR (Pull Request).
Cross link the prior generated issue.

END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS until ALL 1000 e2e real staging tests pass. WAIT AS LONG AS IT TAKES KEEP GOING ALL NIGHT. At least 8-20+ hours.