# GitHub Workflows Architecture

This directory contains the master workflow orchestrator and reusable workflow components following the architecture specified in `SPEC/MASTER_GITHUB_WORKFLOW.xml`.

## Overview

The workflow architecture is designed around a single entry point (`master-orchestrator.yml`) that provides:

- **Conditional Execution**: Smart routing based on triggers, changes, and configuration
- **Centralized Configuration**: JSON-based configuration management
- **ACT Compatibility**: Full support for local testing with the ACT tool
- **Reusable Components**: DRY principle applied to workflow components
- **Intelligent Skipping**: Automatic detection of when workflows should be skipped

## Directory Structure

```
.github/workflows/
├── master-orchestrator.yml      # Single entry point for all workflows
├── config/                      # Centralized configuration
│   ├── settings.json           # Global workflow settings
│   ├── features.json           # Feature flags and toggles
│   ├── environments.json       # Environment-specific configurations
│   └── secrets-mapping.json    # Secret name mappings
├── reusable/                    # Reusable workflow library
│   ├── test-runner.yml         # Test execution with multiple levels
│   ├── deploy-staging.yml      # Staging deployment workflow
│   ├── deploy-production.yml   # Production deployment workflow
│   ├── security-scan.yml       # Security vulnerability scanning
│   ├── code-quality.yml        # Code quality and compliance checks
│   ├── cleanup.yml             # Resource cleanup operations
│   └── notification-handler.yml # Notification management
├── jobs/                        # Atomic job definitions (future)
├── pending/                     # Non-vetted workflows (experimental)
└── README.md                   # This documentation
```

## Master Orchestrator

The `master-orchestrator.yml` serves as the central dispatcher with these phases:

### Phase 1: Determine Strategy
- **Environment Detection**: ACT vs GitHub Actions
- **Change Analysis**: Analyze modified files and determine risk level
- **Execution Planning**: Decide which workflows to run based on context

### Phase 2: Test Execution
- **Conditional Testing**: Run tests based on change analysis
- **Multiple Levels**: smoke, unit, integration, comprehensive
- **ACT Compatible**: Mock execution for local testing

### Phase 3: Deployment
- **Staging Deployment**: Automatic for qualifying branches
- **Production Deployment**: Manual approval required, main branch only
- **Environment-Specific**: Different configurations per environment

### Phase 4: Cleanup
- **Resource Management**: Clean up staging environments on PR close
- **Scheduled Cleanup**: Remove stale resources automatically

### Phase 5: Security & Quality
- **Security Scanning**: Dependency, static analysis, secrets detection
- **Code Quality**: Architecture compliance, linting, type checking
- **Risk Assessment**: Automatic scoring and reporting

### Phase 6: Notifications
- **Multi-Channel**: PR comments, Slack, email (configurable)
- **Smart Filtering**: Only notify when configured conditions are met
- **Unified Updates**: Single comment per PR, always updated

## Trigger Support

The master orchestrator responds to these GitHub events:

- **Pull Requests**: `opened`, `synchronize`, `reopened`, `closed`
- **Push Events**: `main`, `develop` branches
- **Manual Dispatch**: `workflow_dispatch` with parameters
- **External Events**: `repository_dispatch` for integrations
- **Scheduled Runs**: Daily health checks via cron

## Configuration

### Settings (`config/settings.json`)
Global workflow behavior including test timeouts, deployment policies, and notification preferences.

### Features (`config/features.json`)
Feature flags to enable/disable specific workflow capabilities without code changes.

### Environments (`config/environments.json`)
Environment-specific settings for staging, production, and development.

### Secrets Mapping (`config/secrets-mapping.json`)
Maps logical secret names to actual GitHub secret names for different environments.

## Skip Conditions

The orchestrator intelligently skips workflows when:

- Commit message contains `[skip ci]` or `[ci skip]`
- Only documentation files (`.md`, `docs/`, `SPEC/`) were changed
- Frontend-only changes (skips backend tests)
- Backend-only changes (skips frontend builds)

## ACT Compatibility

All workflows are designed to run locally using the [ACT tool](https://github.com/nektos/act):

```bash
# Test the master orchestrator
act pull_request

# Test with specific event
act workflow_dispatch -e test-events/manual-deploy.json

# List available workflows
act --list
```

Key ACT compatibility features:
- No self-referencing environment variables
- Static defaults for all variables
- Mock services and external dependencies
- Conditional logic for local vs cloud execution

## Permissions

All workflows follow the least-privilege principle with explicit permissions:

```yaml
permissions:
  contents: read          # Always needed for checkout
  deployments: write      # For deployment operations
  pull-requests: write    # For PR comments
  issues: write          # For issue operations (PRs are issues)
  statuses: write        # For commit status updates
```

## Error Handling

- **Retry Logic**: Automatic retry for transient failures
- **Graceful Degradation**: Continue with warnings when possible
- **Always Cleanup**: Resource cleanup even on failures
- **Detailed Reporting**: Comprehensive logging and artifacts

## Best Practices

1. **Single Entry Point**: All workflows route through master-orchestrator.yml
2. **Configuration Over Code**: Use JSON configs instead of hardcoded values
3. **DRY Principle**: Reusable workflows for common patterns
4. **Fail Fast**: Validate early to save resources
5. **Test Locally**: Use ACT to validate changes before push
6. **Version Control**: Tag reusable workflows for stability

## Migration from Legacy Workflows

To migrate from existing individual workflows:

1. **Extract Common Logic**: Move shared steps to reusable workflows
2. **Update Triggers**: Route through master orchestrator
3. **Test Thoroughly**: Validate with ACT and staging environments
4. **Monitor**: Watch for issues during rollout
5. **Cleanup**: Remove old workflow files once stable

## Monitoring and Debugging

- **GitHub Step Summary**: Detailed reports for each workflow run
- **Artifacts**: Logs, reports, and debugging information preserved
- **Status Updates**: Real-time commit status updates
- **Notifications**: Configurable alerts for failures

## Future Enhancements

- **Matrix Testing**: Cross-platform and multi-version testing
- **Performance Metrics**: Workflow execution time tracking
- **Advanced Security**: Integration with external security tools
- **Blue-Green Deployments**: Zero-downtime deployment strategies
- **Auto-Scaling**: Dynamic resource allocation based on load

---

For questions or issues with the workflow architecture, consult the `SPEC/MASTER_GITHUB_WORKFLOW.xml` specification or review the existing workflow runs for examples.