
# Workflow Status Verification Test Report

## Summary
- **Total Tests**: 10
- **Passed**: 1
- **Failed**: 9
- **Success Rate**: 10.0%

## Test Results


### help_display - [PASS]
**Description**: Verify help text displays correctly
**Exit Code**: 0

**Output**:
```
usage: verify_workflow_status.py [-h] --repo REPO
                                 [--workflow-name WORKFLOW_NAME]
                                 [--run-id RUN_ID] [--token TOKEN]
                                 [--wait-for-completion] [--timeout TIMEOUT]
                                 [--poll-interval POLL_INTERVAL]
                                 [--output {table,json}]

Verify GitHub workflow status

options:
  -h, --help            show this help message and exit
  --repo REPO         
```


### missing_args - [FAIL]
**Description**: Should fail when missing required arguments
**Exit Code**: 1

**Output**:
```
ERROR: Either --run-id or --workflow-name must be specified

```


### invalid_wait - [FAIL]
**Description**: Should fail when --wait-for-completion used without --workflow-name
**Exit Code**: 1

**Output**:
```
ERROR: --wait-for-completion requires --workflow-name

```


### missing_token - [FAIL]
**Description**: Should fail when no token provided
**Exit Code**: 1

**Output**:
```
ERROR: GitHub token required: use --token or set GITHUB_TOKEN

```


### invalid_token - [FAIL]
**Description**: Should fail with invalid token
**Exit Code**: 1

**Output**:
```
ERROR: RetryError[<Future at 0x1a4ae3b6630 state=finished raised 
GitHubAPIError>]

```


### nonexistent_repo - [FAIL]
**Description**: Should fail with non-existent repository
**Exit Code**: 1

**Output**:
```
ERROR: RetryError[<Future at 0x1d5fea4f650 state=finished raised 
GitHubAPIError>]

```


### nonexistent_workflow - [FAIL]
**Description**: Should fail with non-existent workflow
**Exit Code**: 1

**Output**:
```
ERROR: RetryError[<Future at 0x1c49ee9ad20 state=finished raised 
GitHubAPIError>]

```


### table_output - [FAIL]
**Description**: Test table output format
**Exit Code**: 1

**Output**:
```
ERROR: RetryError[<Future at 0x1d2188efaa0 state=finished raised 
GitHubAPIError>]

```


### json_output - [FAIL]
**Description**: Test JSON output format
**Exit Code**: 1

**Output**:
```
ERROR: RetryError[<Future at 0x156b88cffb0 state=finished raised 
GitHubAPIError>]

```


### specific_run_id - [FAIL]
**Description**: Test checking specific workflow run ID
**Exit Code**: 1

**Output**:
```
ERROR: RetryError[<Future at 0x1e0bd9add90 state=finished raised 
GitHubAPIError>]

```

