---
description: "Git Commit Gardener"
argument-hint: "[focus area, defaults to all]"
---

You MUST repeat the entire PROCESS
WAIT AS LONG AS IT TAKES KEEP GOING ALL NIGHT. At least 8-20+ hours.

Have sub agents use built in github tools or direct `git` or `gh` if needed.
ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
ALWAYS PRESERVE HISTORY AND ONLY DO MINIMAL ACTIONS NEEDED.
STOP IF ANY TRULY SERIOUS MERGE PROBLEMS ARISE
ALWAYS STAY ON CURRENT BRANCH.
ALWAYS PREFER GIT MERGE over rebase, rebase is dangerous!

File focus areas (output this to console) is: ${1 : all}

PROCESS INSTRUCTIONS START:

0: NEW SUBAGENT TASK: 
0a: Git commit open ${1 : all} work in conceptual units as per SPEC\git_commit_atomic_units.xml
0b: Pull and push.
0c: SAFELY AND CAREFUL handle merge commits.
LOG AND OUTPUT AND SAVE EVERY MERGE CHOICE AND JUSTIFICATION TO A NEW FRESH FILE NAMED: MERGEISSUE-{COMMIT DATE}.MD
saved in merges/ folder (create if doesn't exist)
0d: Push and pull.
0e: Doubel check work.

END PROCESS INSTRUCTIONS

WAIT for new changes (up to 2 minutes)
You MUST repeat the entire PROCESS until ALL NIGHT. At least 8-20+ hours.