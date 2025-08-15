# ACT Testing Guide for Monitoring Workflows

This guide explains how to test the GitHub Actions monitoring and health check workflows locally using [ACT (Act)](https://github.com/nektos/act).

## Overview

All monitoring and health check workflows have been updated with ACT compatibility features:

- **health-monitoring.yml** - Continuous health monitoring for production and staging
- **workflow-health-monitor.yml** - Monitor workflow performance, costs, and failures  
- **architecture-health.yml** - Monitor architecture compliance and violations

## ACT Compatibility Features

### 1. ACT Detection
All workflows automatically detect when running in ACT environment:
```bash
ACT_DETECTION: ${{ github.event.inputs.act_local_run || env.ACT || 'false' }}
```

### 2. Mock Data Generation
When running in ACT, workflows generate realistic mock data instead of making external calls:
- Health check endpoints return mock HTTP responses
- Workflow metrics use sample data
- Architecture scans generate mock compliance reports

### 3. External Service Bypass
External services are automatically bypassed in ACT:
- Slack/Discord notifications are logged locally
- GitHub Pages deployment is skipped
- API calls are mocked with local data

### 4. Debug Output
Enhanced debug information for local testing:
- Environment variable inspection
- ACT detection status
- Mock data generation logs

## Prerequisites

1. Install ACT: https://github.com/nektos/act
2. Docker installed and running
3. GitHub repository cloned locally

## Quick Start

### Option 1: Use the Test Script

```bash
# Run the automated test suite
chmod +x .github/scripts/test_workflows_with_act.sh
./.github/scripts/test_workflows_with_act.sh
```

### Option 2: Manual Testing

```bash
# Test health monitoring workflow
act workflow_dispatch \
  --workflows .github/workflows/health-monitoring.yml \
  --input act_local_run=true \
  --input environment=all \
  --input detailed_check=true

# Test workflow health monitor  
act workflow_dispatch \
  --workflows .github/workflows/workflow-health-monitor.yml \
  --input act_local_run=true \
  --input report_type=summary \
  --input days_back=7

# Test architecture health monitor
act workflow_dispatch \
  --workflows .github/workflows/architecture-health.yml \
  --input act_local_run=true \
  --input fail_on_violations=false \
  --input generate_reports=true
```

## ACT-Specific Features by Workflow

### Health Monitoring Workflow

**Mock Features:**
- Production endpoint health checks with random response times
- Mock staging environment discovery
- Sample diagnostic data (database, cache, system metrics)
- Local notification logging instead of Slack/Discord

**Generated Files:**
- `production_health.json` - Mock production health metrics
- `db_performance.json` - Mock database performance data
- `cache_performance.json` - Mock cache performance data  
- `system_metrics.json` - Mock system metrics
- `local_notifications.json` - Mock notification log

### Workflow Health Monitor

**Mock Features:**
- Sample workflow run data with realistic timing
- Mock cost calculations with different runner types
- Text-based performance charts for environments without plotting libraries
- Sample failure analysis data

**Generated Files:**
- `workflow_runs.json` - Mock workflow execution data
- `workflows.json` - Mock workflow metadata
- `workflow_health_report.json` - Complete mock health analysis
- `cost_report.json` - Mock cost breakdown
- `workflow_performance.txt` - Text-based performance summary

### Architecture Health Monitor

**Mock Features:**
- Mock compliance scoring (85.5% overall compliance)
- Sample violation counts by category
- Mock HTML dashboard with ACT branding
- Performance benchmarking with mock timing data

**Generated Files:**
- `reports/architecture-health/health-report.json` - Mock compliance report
- `reports/architecture-health/dashboard.html` - Mock HTML dashboard
- `scan-output.txt` - Mock scan results
- `act_slack_notification.json` - Mock notification log

## Utility Functions

The workflows use shared utility functions from `.github/scripts/act_utils.sh`:

```bash
# Check if running in ACT
is_act_environment

# Print debug information
print_act_debug

# Mock HTTP responses
mock_http_response "https://api.example.com/health" "200"

# Create mock JSON data
create_mock_json "health.json" "health_check"

# Log notifications instead of sending
log_act_notification "slack" "Test message" "warning"

# Skip external services
skip_external_service "GitHub Pages" "echo 'Skipped deployment'"

# Create mock dashboards
create_mock_dashboard "dashboard.html" "Test Dashboard"
```

## Troubleshooting

### Common Issues

1. **ACT not detecting properly**
   ```bash
   # Ensure ACT environment variable is set
   export ACT=true
   # Or use the input parameter
   --input act_local_run=true
   ```

2. **Missing dependencies**
   ```bash
   # For workflows requiring Python packages
   act --container-architecture linux/amd64 --pull
   ```

3. **Workflow is disabled/commented out**
   ```bash
   # Temporarily uncomment the workflow trigger:
   sed 's/^# on:/on:/' workflow.yml > workflow-test.yml
   act workflow_dispatch --workflows workflow-test.yml
   ```

### Debug Mode

Enable verbose ACT output:
```bash
act workflow_dispatch --verbose --input act_local_run=true
```

### Environment Variables

Create `.act.env` for consistent testing:
```bash
ACT=true
ACT_DETECTION=true
CI=true
GITHUB_ACTIONS=true
```

## Mock Data Samples

### Health Check Response
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T12:00:00Z",
  "services": {
    "database": {"status": "healthy", "response_time": 45},
    "cache": {"status": "healthy", "hit_rate": 0.95},
    "storage": {"status": "healthy", "free_space": "85%"}
  },
  "act_mock": true
}
```

### Architecture Health Report
```json
{
  "timestamp": "2024-01-15T12:00:00Z", 
  "metrics": {
    "compliance_scores": {
      "overall_compliance": 85.5,
      "file_size_compliance": 90.0,
      "function_complexity_compliance": 82.0,
      "type_safety_compliance": 88.0
    },
    "violation_counts": {
      "total_violations": 15,
      "file_size_violations": 3,
      "function_complexity_violations": 8,
      "duplicate_types": 2,
      "test_stubs": 2
    }
  },
  "files_analyzed": 125,
  "act_mock": true
}
```

## Benefits of ACT Testing

1. **Fast Feedback** - Test workflow logic without GitHub Actions quotas
2. **Offline Development** - Work on workflows without internet connection
3. **Safe Experimentation** - No risk of triggering real notifications or deployments
4. **Cost Savings** - Avoid GitHub Actions minutes during development
5. **Debugging** - Better visibility into workflow execution locally

## Best Practices

1. **Always test with ACT** before pushing workflow changes
2. **Use mock data** that represents real scenarios
3. **Test both success and failure paths** with different inputs
4. **Verify ACT detection** is working properly in your workflows
5. **Keep mock data realistic** but clearly marked as test data
6. **Document ACT-specific behavior** in workflow comments

## Contributing

When updating monitoring workflows:

1. Ensure ACT compatibility is maintained
2. Update mock data to reflect real scenarios
3. Test locally with ACT before committing
4. Update this guide if adding new ACT features
5. Add ACT tests for new workflow features

## Resources

- [ACT Documentation](https://github.com/nektos/act)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)