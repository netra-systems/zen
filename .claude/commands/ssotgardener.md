---
description: "SSOT Gardener"
argument-hint: "[focus area, defaults to latest]"
---

# 🚨 ULTRA THINK DEEPLY ALWAYS. COMPLETE FEATURE FREEZE.

**CRITICAL MISSION:** Get Golden Path working - users login and get AI responses back.
Your goals are to:
1. Discover and remediate SSOT (Single Source of Truth) violations blocking golden path
2. Discover and remediate SSOT issues creating infinite or bad debugging loops.
3. Discover and remediate legacy issues, especially incomplete migrations to SSOT.

Context
1. You must keep going until all work is fully completed.
2. Have sub agents use built in github tools or direct `git` or `gh` if needed. ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
Stay on develop-long-lived branch as current branch.
3. Focus areas (output this to console) of SSOT: ${1 : latest}
4. SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
5. ALL Github output (issues, comments, prs etc.) MUST follow @GITHUB_STYLE_GUIDE.md
6. FIRST DO NO HARM. Your mandate is to SAFELY refresh to SSOT methods.
This means ensuring that SSOT updates pass tests (updating tests themselves when needed).
7. IND = {issue name}.md
8. GCIFS = Git commit and push the IND updates if safe to do so.
9. IND; GCIFS = Save to IND and then Action GCIFS
10. UINF = UPDATE a comment on the ISSUE with the human readable noise-free updates (per @GITHUB_STYLE_GUIDE.md)
11. IND_GCIFS_UINF = Do IND; GCIFS; UINF
12. LIMIT SCOPE. Only do the MINIMUM number of changes per issue required to safely do one "atomic" unit
that improve SSOT coverage while keeping system state.
13. Focus on existing SSOT classes and document opportunities for new SSOT classes as you see them.

PROCESS INSTRUCTIONS START:

0) Discover Next SSOT Issue (SSOT AUDIT) : SNST: 
0.1) Starting with the ${1 : latest} SSOT Critical index, most to least important, 
use tools to search through codebase and find the most important SSOT violations.
0.2) Make or update github ISSUE.
Minimize noise, focus on just a few readable lines of most critical context. Link to other docs for remaining context.
Issue name style: SSOT-{context (one of: regression, incomplete-migration, recent-change, {custom})}-{brief human description}}

PRIORITY TAG ASSIGNMENT (MANDATORY):
Always assign a priority tag based on SSOT violation impact:
- P0: Critical/blocking - system down, Golden Path broken, data loss, security vulnerability
- P1: High - major feature broken, significant SSOT violations
- P2: Medium - minor SSOT issues, moderate impact  
- P3: Low - cleanup items, nice-to-have improvements

Create a local md file (IND = {issue name}.md) with the same name ending in .md to record your work in progress
OUTPUT the issue name, .md progress tracker name {issue name}.md, and github link.
Action: IND; GCIFS

1) DISCOVER AND PLAN TEST : SNST : (Pass context from 0):

1.1) DISCOVER EXISTING: find collection of existing tests
tests protecting against breaking changes made by SSOT refactor or similar
After refactors: these tests must continue to pass, or now pass if failing prior, or updated as a test and pass.
Do IND_GCIFS_UINF

1.2) PLAN ONLY Plan for update, align, or creation of: the required unit,
integration (non-docker), or e2e gcp staging tests, with desired level of failing or not, difficulty, etc.: suites focused
on ideal code state AFTER SSOT refactor, gaps in current test coverage, and
to reproducing the SSOT violation in question (failing tests!). following reports\testing\TEST_CREATION_GUIDE.md
and all of the latest testing best practices as per claude.md

ONLY RUN tests that don't require docker, such as unit, integration (no docker), or e2e on staging gcp remote.
~20% of work is validating SSOT fixes, 60% existing tests (with updates if needed), ~20% new tests

Do IND_GCIFS_UINF


2) EXECUTE THE TEST PLAN for the 20% of NEW SSOT tests : SNST : with new spawned sub agent. audit and review the test. And run the fake test checks. ONLY RUN tests that don't require docker, such as unit, integration (no docker), or e2e on staging gcp remote.
Do IND_GCIFS_UINF

3) PLAN REMEDIATION OF SSOT : SNST : 
PLAN ONLY THE SSOT REMEDIATION
Do IND_GCIFS_UINF

4) EXECUTE THE REMEDIATION SSOT PLAN: SNST :
Do IND_GCIFS_UINF

5) ENTER TEST FIX LOOP:
PROOF: SNST : Spawn a sub agent PROVE THAT THE CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
otherwise go back and ensure that any code changes exclusively add value as one atomic package of commit and
do not introduce new problems.
5.1) Run and fix changes for every test case in the IND.
5.2) or each cycle Do IND_GCIFS_UINF until ALL tests in IND pass.

STOP and repeat step 5 until all tests pass or 10 cycles.
If still failing after 10 cycles do IND_GCIFS_UINF and STOP and exit PROCESS.

6) PR AND CLOSURE: SNST:
ONLY IF TESTS are PASSING.
Do IND_GCIFS_UINF
Make a NEW PR (Pull Request).
Cross link the prior generated issue so it will close on PR merge.

END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS until success.
EVERY NEW PROCESS ENTRY MUST SPAWN NEW SNST FOR EACH ITEM.
STOP AFTER 3 PROCESS CYCLES OR IF THE ISSUE IS CLOSED.