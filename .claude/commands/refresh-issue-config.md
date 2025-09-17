---
description: "Create an issue config"
argument-hint: "[focus area]"
---

Create a new config similar to this
{
  "instances": [
    {
      "command": "/gitissueprogressorv4 {issue number}",
      "permission_mode": "acceptEdits",
      "output_format": "stream-json"
    },
    {
      "command": "/gitissueprogressorv4 {issue number}",
      "permission_mode": "acceptEdits",
      "output_format": "stream-json"
    }
  ]
}

Find all git issues with tags $1:
and without actively-being-worked-on tags

for each one found set an instance as above with the issue number unique for it.

Sets: Important note: if more than 7 issues are found, save a new file for each set of 7.

Save it as a new .json file with the format context:
  1. name = Descriptive name based on $1 (filepath safe)
  2. Format: {datetime}-named-issue-set-{name}-{set number, defaults to 0}
careful final output Format path is safe all operating systems.
in the claude_configs/ folder