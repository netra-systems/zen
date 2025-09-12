---
description: "Run unit tests"
argument-hint: "[focus area, defaults to all]"
---

SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)

ALL Github output MUST follow @GITHUB_STYLE_GUIDE.md
Have sub agents use built in github tools or direct `git` or `gh` if needed.
ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.

REPEAT THIS PROCESS UNTIL ALL TESTS PASS OR 10 TIMES.

PROCESS INSTRUCTIONS START SNST:

    0) Run unit tests with a focus on ${1 : latest issues}, fast failure.

    1) ISSUE SEARCH AND UPDATE OR CREATION: SEARCH GITHUB ISSUES FOR EXISTING ISSUE.

        IF FOUND: Make or UPDATE a comment on the ISSUE.
            OUTPUT the ISSUE ID and comment ID here:
            READ THE EXISTING ISSUE AND COMMENTS and return key points to master agent.
        
        ELSE: CREATE A NEW GIT ISSUE AND OUTPUT the ISSUE ID here:

    2) STATUS UPDATE : 

        AUDIT the current codebase and linked PRs (closed and open)
        with FIVE WHYS approach and assess the current state of the issue.
        2.1) Make or UPDATE a comment on the ISSUE with your learnings.
        OUTPUT the comment ID here:

    3) PLAN REMEDIATION OF THE EXISTING FAILING TEST : SNST : 
        PLAN ONLY THE REMEDIATION TO THE SYSTEM UNDER TEST.
        to fix the issue and pass the test too.
        3.1) UPDATE the comment on the ISSUE with the results.

    4) EXECUTE THE REMEDIATION ITEM SPECIFIC PLAN: SNST :
        4.1) UPDATE the comment on the ISSUE with the results.
        add tag: actively-being-worked-on
        4.2) Git commit work in conceptual batches. 

    5) PROOF: SNST : Spawn a sub agent PROVE THAT THE TEST NOW PASSES OR STILL FAILES, AND CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
    IF BREAKING CHANGES OR TEST STILL FAILING GO BACK: ensure that any code changes exclusively add value as one atomic package of commit and
    do not introduce new problems.
    5.1) UPDATE a comment on the ISSUE with PROOF  following @GITHUB_STYLE_GUIDE.md  .

    6) PR AND CLOSURE: SNST:
    6.1) Git commit remaining related work in conceptual batches. 
    6.2) Make a NEW PR (Pull Request).
    6.3) Cross link the prior generated issue so it will close on PR merge.
    6.4) Do a final update for this loop  following @GITHUB_STYLE_GUIDE.md  .

END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS UNTIL ALL TESTS PASS OR STop afte 10 PROCESS CYCLES