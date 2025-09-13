---
description: "Create Tests V2 with coverage"
argument-hint: "[focus area, defaults to all] [test type, defaults unit]"
---

Your goal is to create tests and achieve 100% coverage.

Context:
    1. SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
    2. GIT_COMMIT_SAFE = pull, git commit, push, safely resolve merges.
    3. DO NOT USE DOCKER in any case to run tests.
        If test type == e2e: test on gcp staging.
    4. ALL Github output MUST follow @GITHUB_STYLE_GUIDE.md
        Have sub agents use built in github tools or direct `git` or `gh` if needed.
        ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
        Use github to validate context and log progress.


FOCUS_AREA = ${1 : worst coverage areas}
TEST_TYPE = ${2 : unit} tests. 

If TEST_TYPE == integration: then do non-docker integration tests

REPEAT THIS PROCESS UNTIL ALL TESTS PASS OR 10 TIMES.

AGENT_SESSION_ID = agent-session-{date}-{time}

PROCESS INSTRUCTIONS START:

    0) SNST: Run test coverage reports for FOCUS_AREA
    
        Make a plan for a single agent context scope of work to create new tests to increase coverage.
    
        Search github for FOCUS_AREA existing similar test coverage:

        IF FOUND: 
            Make or UPDATE a comment on the ISSUE.
            Update title = [test-coverage] {current % coveraged} | FOCUS_AREA
            OUTPUT the ISSUE ID and comment ID here:
            READ THE EXISTING ISSUE AND COMMENTS
        
        ELSE: 
            CREATE A NEW GIT ISSUE AND OUTPUT the ISSUE ID here:
            Format: [test-coverage] {current % coveraged} | FOCUS_AREA

        All cases:
            add tags to the issue: actively-being-worked-on, AGENT_SESSION_ID


    1) SNST: Create new tests

        Following the plan provided by agent 0, create the actual real tests.
        Cheating or bad quailty tests are forbidden.

        Update the git issue with new tests
        GIT_COMMIT_SAFE

    2) SNST: RUN the new tests and PLAN REMEDIATION OF FAILING TESTs

        PLAN ONLY THE REMEDIATION TO THE SYSTEM UNDER TEST.
        update the ISSUE comment with the results.
        GIT_COMMIT_SAFE

    3) SNST : EXECUTE THE REMEDIATION ITEM SPECIFIC PLAN:

        UPDATE the comment on the ISSUE with the results.
        GIT_COMMIT_SAFE

    4) PROOF: SNST : 
        Spawn a sub agent PROVE THAT THE TEST NOW PASSES OR STILL FAILES, AND CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
        IF BREAKING CHANGES OR TEST STILL FAILING GO BACK: ensure that any code changes exclusively add value as one atomic package of commit and
        do not introduce new problems.
        5.1) UPDATE a comment on the ISSUE with PROOF

    5) PR AND CLOSURE: SNST:
        6.1) Git commit remaining related work in conceptual batches. 
        6.2) Make a NEW PR (Pull Request).
        6.3) Cross link the prior generated issue.
        6.4) Update related test coverage readmes and tracking docs
        6.5) remove tag: actively-being-worked-on from issue
        If FOCUS_AREA is at 100% close issue.
        6.6) Safely merge PR

END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS UNTIL ALL TESTS PASS OR stop after 10 PROCESS CYCLES