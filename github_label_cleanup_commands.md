# GitHub Label Cleanup Commands

## Task: Remove "actively-being-worked-on" labels from stale issues

### Prerequisites
Ensure you're authenticated with GitHub CLI:
```bash
gh auth status
# If not authenticated, run: gh auth login
```

### Step 1: List all issues with the "actively-being-worked-on" label
```bash
gh issue list --repo netra-systems/netra-apex --label "actively-being-worked-on" --state open --json number,title,updatedAt,url
```

### Step 2: Manual approach - Check each issue and remove stale labels

For each issue from Step 1, check if it was last updated more than 20 minutes ago.

Current time reference (when this script was created): `date -u`

Calculate 20 minutes ago: `date -u -v-20M '+%Y-%m-%dT%H:%M:%SZ'` (macOS) or `date -u -d "20 minutes ago" '+%Y-%m-%dT%H:%M:%SZ'` (Linux)

### Step 3: Remove labels from stale issues
For each stale issue (replace ISSUE_NUMBER with actual issue number):
```bash
gh issue edit ISSUE_NUMBER --repo netra-systems/netra-apex --remove-label "actively-being-worked-on"
```

### Example workflow:
1. Run the list command to get all labeled issues
2. Compare each issue's `updatedAt` timestamp with the 20-minute cutoff
3. For stale issues, run the remove label command
4. Log which issues were processed

### Automated Script
Run the cleanup script (if chmod permissions work):
```bash
./cleanup_stale_actively_being_worked_on_labels.sh
```

### Manual Commands Template
```bash
# Get current time minus 20 minutes
CUTOFF=$(date -u -v-20M '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -d "20 minutes ago" '+%Y-%m-%dT%H:%M:%SZ')
echo "Cutoff time: $CUTOFF"

# List issues
gh issue list --repo netra-systems/netra-apex --label "actively-being-worked-on" --state open --json number,title,updatedAt,url > labeled_issues.json

# Process each issue (manual check required for timestamp comparison)
cat labeled_issues.json
```

### Safety Notes
- Only removes labels from issues not updated in the last 20 minutes
- Does not close or modify issues in any other way
- Preserves all other labels and issue content
- Can be safely re-run multiple times