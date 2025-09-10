---
description: "Git Commit Gardener"
argument-hint: "[focus area, defaults to all]"
---

You MUST repeat the entire PROCESS up to 10 times.

Have sub agents use built in github tools or direct `git` or `gh` if needed.

1. ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
2. ALWAYS PRESERVE HISTORY AND ONLY DO MINIMAL ACTIONS NEEDED.
3. STOP IF ANY TRULY SERIOUS MERGE PROBLEMS ARISE
4. ALWAYS STAY ON CURRENT BRANCH.
5. ALWAYS PREFER GIT MERGE over rebase, rebase is dangerous!
6. SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
7. DO_SAFE_MERGE = SAFELY AND CAREFUL handle merge commits. LOG AND OUTPUT AND SAVE EVERY MERGE CHOICE AND JUSTIFICATION TO A NEW FRESH FILE NAMED: MERGEISSUE:{COMMIT DATE}.MD saved in merges/ folder (create if doesn't exist)

File focus areas (output this to console) is: ${1 : all}

PROCESS INSTRUCTIONS START:

0: GIT Commit Work : SNST: 
0a: Git commit open ${1 : all} work in conceptual units as per SPEC\git_commit_atomic_units.xml
0b: Pull and push.
0c: DO_SAFE_MERGE
0d: Push and pull.
0e: DOUBLE check work.

1: Merge other branches : SNST
1.1: Look for other active branches to merge into this one.
1.2: DO_SAFE_MERGE

END PROCESS INSTRUCTIONS

WAIT for new changes (up to 2 minutes)
You MUST repeat the entire PROCESS up to 10 times.