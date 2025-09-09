---
description: "LOOP Audit & Fix GCP Cloud Run logs with automatic Five Whys debugging. LOGS (not offical named GCP error)"
argument-hint: "[focus area]"
---

IMPORTANT: You MUST repeat the entire PROCESS 10 times. WAIT AS LONG AS IT TAKES KEEP GOING 8-30+ Hours.

PROCESS INSTRUCTIONS START

Start
0) FROM GCP STAGING: 
Get all the the most recent log notices, warnings and errors for backend with a focus on :${1:all} .

Use existing python tools and sdk commands. Deduplicate as needed.
Choose the most important issue (Errors > Warnings > Notices > Odd info statements).

LITERALLY Write AND output YOUR CHOICE as the "ISSUE" to ACTION BEFORE PROCEEDING
Save the choice to a fresh debugging log.

1) New sub agent: ACTION Five WHYS debugging process for the ISSUE.
Update same debugging log with items.

ACTION the ISSUE:
2) PLAN: 
Spawn a sub agent to PLAN ONLY the update, align, or creation of: 
the required unit, integration (non-docker), or e2e gcp staging tests, with desired level of failing or not, difficulty, etc.: suites focused on THE ISSUE YOU WROTE DOWN.
Save the plan to the same debugging log.

2.1) GITHUB ISSUE INTEGRATION
Update existing issue or create new GITHUB ISSUE 
using tools shown in GITHUB_INTEGRATION_IMPLEMENTATION_REPORT.md


3) EXECUTE THE PLAN with new spawned sub agent
Save the status updates to the same debugging log.

43) Spawn a new sub agent to audit and review the test. And run the fake test checks. Fix issues if fixable or 
if entirely bad mark and report as such and go back to 0) with the new added info.
Save the status updates to the same debugging log.

5) Run the tests and log results with evidence of output and pass fail, timing etc.
Save the status updates to the same debugging log.

WAIT
6) Spawn a sub agent If needed, fix the system under test based on the failure
Save the status updates to the same debugging log.

7) Spawn a sub agent PROVE THAT THE CHANGES HAVE KEPT STABILITY OF SYSTEM AND NOT INTRODUCED NEW BREAKING CHANGES
otherwise go back and ensure that any code changes exclusively add value as one atomic package of commit and
do not introduce new problems.
Save the status updates to the same debugging log.

8) Git commit.
As needed cross-link, organize reports into folders, store xml learnings, store anti-repetition items etc.

You must update and save your work as you go.
PROCESS INSTRUCTIONS END.

YOU MUST Keep going and repeating the whole entire PROCESS until ALL WARNINGS ERRORS AND NOTICES ARE FIXED.
Expect this to take at least 8=20+ hours.