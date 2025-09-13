---
description: "GCP log gardener. ONLY creates issues does not attempt to remediate them. Use the github issue progressor for that."
argument-hint: "[time period] [service]"
---

Your goals are to:
1. Collect GCP log issues and errors not yet in github issues 

Context:
1. You must keep going until all work is fully completed.
2. Have sub agents use built in github tools or direct `git` or `gh` if needed. ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.
3. -
4. SNST = SPAWN NEW SUBAGENT TASK  (EVERY STEP IN PROCESS)
5. ALL Github output (issues, comments, prs etc.) MUST follow @GITHUB_STYLE_GUIDE.md
Use label: "claude-code-generated-issue"
6. FIRST DO NO HARM.
7. GCP-LOG-GARDENER-WORKLOG = GCP-LOG-GARDENER-WORKLOG-${1 : latest}-{date-time}.md
8. GCP-LOG-GARDENER-WORKLOG-UPDATE = Update GCP-LOG-GARDENER-WORKLOG.
9. GCP-LOG-GARDENER-WORKLOG-UPDATE-PUSH = 1:GCP-LOG-GARDENER-WORKLOG-UPDATE 2: Git commit and pull / push safely (skip if not safe)
10. UPDATE-COMMENT = UPDATE a comment on one of (Issue, PR) with the human readable noise-free updates.
11. -
12. LIMIT SCOPE. Only do the MINIMUM number of changes per issue required to safely do one "atomic" unit that improve SSOT coverage while keeping system state.

Example_JSON_payload to get
    jsonPayload: {
        context: {
        name: "netra_backend.app.websocket_core.handlers"
        service: "netra-service"
    }
    labels: {
        function: "route_message"
        line: "1271"
        module: "netra_backend.app.websocket_core.handlers"
    }
    message: "Error routing message from demo-user-001: 'function' object has no attribute 'can_handle'"
    timestamp: "2025-09-12T23:21:43.625002+00:00"

START:
1. Get all the ${1 : latest} log notices, warnings and errors for ${2 : backend}.
Be sure to get the actual JSON payloads, such as the context, labels, traceback, line etc. one of many possible formats is exampled in Example_JSON_payload

2. Save the discovered issues to a fresh GCP-LOG-GARDENER-WORKLOG in gcp/log-gardener/ folder (or create it)

Cluster the logs into groups that are related to each other, e.g. by time or message type.

3. for each cluster of related logs start a new PROCESS with SNST:

PROCESS INSTRUCTIONS START:

    0) 
    Search if there is an existing issue similar to this.
    If there is an open issue, then make an update comment with most recent logs and context. If relevant, update the title and issue tags.

    Else: make a new issue with this format:

    GCP-{choose one - regression, new, active-dev, or other category descriptor} | {severity P0 - P10} | {human skimable name}

    1) Linking
        1.1 If other related (open or closed) issues are discovered that are relevant, link them to the issue.
        1.2 Link other relevant items, such as other related issues, other PRs, other related docs.
        1.3 GCP-LOG-GARDENER-WORKLOG-UPDATE-PUSH

END PROCESS INSTRUCTIONS


Repeat until all discovered logs have gone through the PROCESS.