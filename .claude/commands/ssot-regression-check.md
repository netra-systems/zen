---
allowed-tools: ["Bash", "Read"]
description: "SSOT regression check"
argument-hint: "<agent-name>"
---
 using multi agent team, audit last 40 commits for every file and line removed. catalog anything that has NOT been
  superceded by the current state. for example, new SSOT class x and deleted legacy class x = good. removed legacy,
  and system still requires that function but SSOT class is missing = bad.