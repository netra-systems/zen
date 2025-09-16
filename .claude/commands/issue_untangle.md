---
description: "Untangle an issue and REPLAN, use with Opus"
argument-hint: "[Issue number] [focus area]"
---

ISSUE: ${1 : one recent open issue}
FOCUS_AREA = ${2 : think deeply}
SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
ALL Github content must follow @GITHUB_STYLE_GUIDE.md

Goal is to untangle any remaining confusions with the ISSUE.
Review the ISSUE and comments with git tools.

Do NOT try to solve this issue directly, only answer these questions

SNST A:

First a quick gut check, if the issue is actually listed as fully resolved then go ahead and close it.

Especially: FOCUS_AREA

    1. Are there infra or "meta" issues that are confusing resolution?
    OR the opposite, are real code issues getting confused by infra or unrelated misleads?
    2. Are there any remaining legacy items or non SSOT issues?
    3. Is there duplicate code?
    4. Where is the canonical mermaid diagram explaining it?
    5. What is the overall plan? Where are the blockers?
    6. It seems very strange that the auth is so tangled. What are the true root causes?
    7. Are there missing concepts? Silent failures?
    8. What category of issue is this really? is it integration?
    9. How complex is this issue? Is it trying to solve too much at once?
    Where can we divide this issue into sub issues? Is the scope wrong?
    10. Is this issue dependent on something else?
    11. Reflect on other "meta" issue questions similar to 1-10.
    12. Is the issue simply outdated? e.g. the system has changed or something else has changed but not yet updated issue text?
    13. Is the length of the issue history itself an issue? e.g. it's mostly "correct" but needs to
     be compacted into more workable chunk to progress new work?
     Is there nuggets that are correct but then misleading noise?

md_file_name = ISSUE_UNTANGLE_{ISSUE NUMBER}_{datetime}_{your name}.md
Save output to a .md file with md_file_name format.

SNST B:
    Load content from @md_file_name

    Make a new "Master plan"
    Deeply think and plan out what to do based on the content of the issue.
    Make a new git issue (or set of issues) and output relevant plan elements and links to new md files there
    Link the old ISSUE
    Close the old ISSUE.
