---
description: "Git Commit Gardener"
argument-hint: "[focus area, defaults to all]"
---

Have sub agents use built in github tools or direct `git` or `gh` if needed.
ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
ALWAYS PRESERVE HISTORY AND ONLY DO MINIMAL ACTIONS NEEDED.
STOP IF SERIOUS MERGE PROBLEMS ARISE
ALWAYS STAY ON CURRENT BRANCH.
ALWAYS PREFER GIT MERGE over rebase, rebase is dangerous!

File focus areas (output this to console) is: ${1 : all}

PROCESS INSTRUCTIONS START:

0: NEW SUBAGENT TASK: 

0.0: From git issues: Remove "actively-being-worked-on" tags if the last comment (or comment update time) was more than 20 minutes ago.
 
0.1: Git commit open ${1 : all} work in conceptual units as per SPEC\git_commit_atomic_units.xml
0.2: Pull and push.
0.3: SAFELY AND CAREFUL handle merge commits.
LOG AND OUTPUT AND SAVE EVERY MERGE CHOICE AND JUSTIFICATION TO A NEW FRESH FILE NAMED: MERGEISSUE-{COMMIT DATE}.MD
saved in merges/ folder (create if doesn't exist)
0.4: Push and pull.

END PROCESS INSTRUCTIONS

Repeat process up to 3 times.