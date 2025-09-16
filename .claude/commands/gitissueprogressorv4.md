---
description: "Git Issue progressor V4 SINGLE for use with orchestration"
argument-hint: "[focus area, defaults to latest]"
---

Context:
    1. Have sub agents use built in github tools or direct `git` or `gh` if needed.
    2. By default, ignore issues with the tag "actively-being-worked-on" and that have an "agent-session-{datetime}" within the last 20 minutes. Note: Expect multiple "agent-session-{datetime}" tags.
    3. ISSUE: ${1 : one recent open issue}
    4. SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
    5. ALL Github content must follow @GITHUB_STYLE_GUIDE.md
    6.  **CRITICAL BRANCH SAFETY POLICY:**
        - ALWAYS stay on Branch = develop-long-lived
        - **All work performed on**: develop-long-lived
        - No PR, issue creation is the log and all work is done directly on the dev branch.
    7.  Issue Exclusion List (IEL): generally do not create issues for the following cases: merge conflicts, local env specific issues
    8. AGENT_SESSION_ID = agent-session-{datetime}


PROCESS INSTRUCTIONS START:

0) Init: SNST: 

    Verify current branch is develop-long-lived: `git branch --show-current`
    If not on develop-long-lived, STOP and switch: `git checkout develop-long-lived`
    Record branch state for safety monitoring throughout process.

    Clean working state:
        git commit, pull latest, and handle merge conflicts

    If ISSUE is not a single literal number:
        Search git issues to determine most important issue to work on relative to ISSUE text.
        Be mindful of dependency tags
        ISSUE = to that number

    add a tags to the issue: actively-being-worked-on, AGENT_SESSION_ID
    return ISSUE number to master

1) Research and review : SNST :

    1.0 First analyze the existing issue.

    1.1 Also consider relevant questions like:
        1.1. Are there infra or "meta" issues that are confusing the issue?
        OR the opposite, are real code issues getting confused by infra or unrelated misleads?
        1.1.2. Are there any remaining legacy items or non SSOT issues?
        1.1.3. Is there duplicate code?
        1.1.4. Where is the canonical mermaid diagram explaining it?
        1.1.5. What is the overall plan? Where are the blockers?
        1.1.6. It seems very strange that the auth is so tangled. What are the true root causes?
        1.1.7. Are there missing concepts? Silent failures?
        1.1.8. What category of issue is this really? is it integration?
        1.1.9. How complex is this issue? Is it trying to solve too much at once?
        Where can we divide this issue into sub issues? Is the scope wrong?
        1.1.10. Is this issue dependent on something else?
        1.1.11. Reflect on other "meta" issue questions similar to 1-10.
        1.1.12. Is the issue simply outdated? e.g. the system has changed or something else has changed but not yet updated issue text?
        1.1.13. Is the length of the issue history itself an issue? e.g. it's mostly "correct" but needs to
        be compacted into more workable chunk to progress new work?
        Is there nuggets that are correct but then misleading noise?

    1.14 As complexlity requires:
        AUDIT the current codebase and linked PRs (closed and open) with FIVE WHYS approach and assess the current state of the issue.

    1.15 UPDATE Comment:
        Make or UPDATE a comment on the ISSUE with your learnings.
        OUTPUT the comment ID here:

    1.16 STATUS DECISION:
        IF the issue appears to already be resolved:
            close the issue and repeat PROCESS loop, otherwise continue to the next step.
            If closing issue: remove label: actively-being-worked-on
            update the existing comment on the ISSUE with your learnings

Master:
    Pull latest, and handle merge conflicts
    OPTIONAL STEPS IF ISSUE IS OPEN:

2) PLANNING: SNST:

    Make a new "Master plan"
    Deeply think and plan out what to do based on the content of the issue.

    Define the scope of the issue and overall definition of done.

    Give holistic consideration to the overall resolution approaches:
        1. Infra or config
        2. Code
        3. Docs
        4. Tests
        5. Other ways to fix it
        
        resolution notes: Deeply consider some issues may require only one appraoch, others may require all five.

    PLAN ONLY the update, align, or creation of required tests (if any): 
        
        the required unit, integration (non-docker), or e2e gcp staging tests, with desired level of failing or not, difficulty, etc.: suites focused
    on reproducing the item in question (failing tests). following reports\testing\TEST_CREATION_GUIDE.md
    and all of the latest testing best practices as per claude.md
    ONLY RUN tests that don't require docker, such as unit, integration (no docker), or e2e on staging gcp remote.
    
    UPDATE the comment on the ISSUE with the PLANs

3) Action the plans: SNST :
    
    Work the plan.

    IF testing is called for:
        audit and review the test. And run the fake test checks. 
        ONLY RUN tests that don't require docker, such as unit, integration (no docker), or e2e on staging gcp remote.
        Decision (one of): Fix the TEST if fixable OR
        if very bad mark and report as such and go back to 3) with the new added info.
        UPDATE the comment on the ISSUE with the test results and decision

        PLAN REMEDIATION ITEM SPECIFIC PLAN : SNST : 
        PLAN ONLY THE REMEDIATION TO THE SYSTEM UNDER TEST.
        to fix the original issue and pass the test too.
        UPDATE the comment on the ISSUE with the results

4) EXECUTE THE REMEDIATION ITEM SPECIFIC PLAN: SNST :
    4.1) UPDATE the comment on the ISSUE with the results
    4.2) Run startup tests (non docker) fix import or other types of startup issues related to this change.
    4.3) Git commit work in conceptual batches. 
    4.4) Sync with origin: push/pull latest, and handle merge conflicts

5) PROOF: SNST : Spawn a sub agent 
    
    PROVE THAT THE CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
    otherwise go back and ensure that any code changes exclusively add value as one atomic package of commit and
    do not introduce new problems.
    5.1)  Run startup tests (non docker) fix import or other types of startup issues related to this change.
    5.2) UPDATE a comment on the ISSUE with PROOF

*Skip step 6 if recently deployed*
6) Staging Deploy SNST :  Spawn a sub agent PROVE THAT THE CHANGES WORK OR FAIL IN STAGING.
    6.1) Deploy the service (only deploy the service(s) with the files edited/updated)
    if it hasn't been deployed last 3 minutes.
    6.2) WAIT for service revision success or failure.
    6.3) Read service logs to audit no net new breaking changes
    6.4) Run relevant tests on staging gcp (either newly created tests and relevant existing e2e tests related to this)
    6.5) UPDATE a comment with Staging deploy information.
    6.6) IF new directly related and significant issues introduced log them and exit process, restart process from 1) (exit this agent and go back to main loop so it can spawn new agents)

7) Wrap up: SNST:
    7.1) Git commit remaining related work in conceptual batches. 
    7.2) Do a final update for this loop,
    especially linking created docs and related commits
    7.3) If closing issue: remove label: actively-being-worked-on

END PROCESS INSTRUCTIONS
