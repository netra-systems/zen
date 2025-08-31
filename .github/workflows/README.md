# GitHub Workflows Documentation

## Overview

This repository uses a sophisticated CI/CD pipeline with three distinct execution models optimized for different scenarios. All workflows are aligned with CLAUDE.md requirements and project goals for the Netra Apex AI Optimization Platform.

## Core Principles

1. **Real Services Only**: All tests use real databases and services (PostgreSQL, Redis) - no mocks allowed per CLAUDE.md
2. **Mission Critical First**: WebSocket agent events are tested first and must always pass
3. **Business Value Focus**: Every workflow decision is made to maximize value delivery
4. **Fail Fast Philosophy**: Get feedback as quickly as possible when things break

## Execution Models

### 1. Max Parallel (`ci-max-parallel.yml`)
- **Purpose**: Fastest overall completion time
- **Strategy**: All tests run simultaneously
- **Best For**: Development branches, comprehensive testing
- **Trade-off**: Higher resource usage
- **Completion Time**: ~5-10 minutes

### 2. Balanced (`ci-balanced.yml`)
- **Purpose**: Optimal resource usage with smart dependencies
- **Strategy**: Phased execution with logical grouping
- **Best For**: Pull requests, standard development
- **Trade-off**: Balanced speed vs resource usage
- **Completion Time**: ~10-15 minutes

### 3. Fail Fast (`ci-fail-fast.yml`)
- **Purpose**: Immediate feedback on first failure
- **Strategy**: Sequential execution, stops on first error
- **Best For**: Main branch, production deployments
- **Trade-off**: Longer total time but fastest failure feedback
- **Completion Time**: ~15-20 minutes (or immediate on failure)

## Main Workflows

### CI Orchestrator (`ci-orchestrator.yml`)
The main entry point that automatically selects the appropriate execution model:
- **Pull Requests**: Uses Balanced model
- **Main Branch**: Uses Fail-Fast model
- **Develop Branch**: Uses Max-Parallel model
- **Manual Override**: Available via workflow_dispatch

### Master Orchestrator (`master-orchestrator.yml`)
Legacy orchestrator with comprehensive workflow management (being phased out in favor of ci-orchestrator.yml).

### Deployment Workflows

#### Staging Deployment (`deploy-staging.yml`)
- Automatic deployment from main branch
- Pre-deployment validation including mission critical tests
- Blue-green deployment strategy
- Health checks and smoke tests

#### Production Deployment (`deploy-production.yml`)
- Manual approval required
- Comprehensive pre-deployment testing
- Database backup before deployment
- Gradual traffic shifting (10% → 50% → 100%)
- Automatic rollback plan generation

### Utility Workflows

#### Cleanup (`cleanup.yml`)
- PR environment cleanup on close
- Old artifact removal (7-day retention)
- Unused container image cleanup (30-day retention)
- Weekly scheduled cleanup

## Workflow Selection Guide

| Scenario | Recommended Model | Reason |
|----------|------------------|---------|
| Feature Development | Max Parallel | Get all test results quickly |
| Pull Request | Balanced | Optimal feedback with resource efficiency |
| Hotfix to Main | Fail Fast | Immediate feedback if something breaks |
| Large Refactor | Max Parallel | See all impacts at once |
| Pre-Production | Fail Fast | Ensure quality gate compliance |

## Mission Critical Tests

Per CLAUDE.md section 6, the following are MISSION CRITICAL and must never fail:
- WebSocket agent event tests (`test_websocket_agent_events_suite.py`)
- Agent startup notifications
- Tool execution events
- Agent completion events

These tests run first in all workflows and block deployment if they fail.

## Test Categories

1. **Mission Critical**: WebSocket events, core agent functionality
2. **Unit Tests**: Backend, Frontend, Auth Service
3. **Integration Tests**: Service interactions, database operations
4. **E2E Tests**: Full user flows with real services
5. **Security Scans**: Vulnerability detection, dependency audits
6. **Architecture Compliance**: SSOT, import rules, type safety

## Directory Structure

```
.github/workflows/
├── ci-orchestrator.yml          # Main CI/CD orchestrator with strategy selection
├── ci-max-parallel.yml          # Maximum parallelization strategy
├── ci-balanced.yml              # Balanced execution strategy
├── ci-fail-fast.yml            # Sequential fail-fast strategy
├── deploy-staging.yml          # Staging deployment pipeline
├── deploy-production.yml       # Production deployment with approvals
├── cleanup.yml                 # Resource cleanup automation
├── master-orchestrator.yml     # Legacy orchestrator (phasing out)
├── unified-test-runner.yml     # Shared test execution logic
├── mission-critical-tests.yml  # Critical WebSocket tests
├── config/                     # Centralized configuration
│   ├── settings.json          # Workflow settings
│   └── features.json          # Feature flags
└── README.md                  # This file
```

## Environment Variables

All workflows use consistent environment variables:
- `PYTHON_VERSION`: 3.11
- `NODE_VERSION`: 20
- `NETRA_ENV`: test/staging/production
- `TEST_DATABASE_URL`: PostgreSQL connection
- `TEST_REDIS_URL`: Redis connection
- `CI`: true

## Triggering Workflows

### Automatic Triggers
- **Push to main**: Fail-fast CI → Staging deployment
- **Pull Request**: Balanced CI
- **PR Close**: Cleanup resources
- **Weekly Schedule**: Resource cleanup

### Manual Triggers
All workflows support `workflow_dispatch` for manual execution with options:
- Select CI strategy
- Skip non-critical tests
- Force deployment
- Start from specific phase

## Best Practices

1. **Never Skip Mission Critical Tests**: These ensure core functionality
2. **Use Real Services**: Mocks are forbidden per CLAUDE.md
3. **Check Architecture Compliance**: Run before major changes
4. **Monitor Resource Usage**: Use appropriate model for the task
5. **Review Rollback Plans**: Always have a way back

## GCP Deployment

Deployments use the official script:
```bash
python scripts/deploy_to_gcp.py --project netra-staging --build-local
```

### Service Configuration
- **Backend**: Cloud Run, 2-4 CPU, 4-8Gi RAM
- **Auth Service**: Cloud Run, 1-2 CPU, 2-4Gi RAM  
- **Frontend**: Cloud Run, 1-2 CPU, 2-4Gi RAM
- **Database**: Cloud SQL PostgreSQL
- **Cache**: Memorystore Redis

## ACT Compatibility

All workflows support local testing with [act](https://github.com/nektos/act):

```bash
# Test specific workflow
act -W .github/workflows/ci-balanced.yml

# Test with specific event
act pull_request -W .github/workflows/ci-orchestrator.yml

# Test with custom inputs
act workflow_dispatch -W .github/workflows/ci-orchestrator.yml \
  --input ci_strategy=fail-fast
```

## Troubleshooting

### Common Issues

1. **Mission Critical Tests Failing**
   - Priority: IMMEDIATE
   - Action: Block all deployments until fixed
   - Check: WebSocket event handling, agent registry

2. **Resource Cleanup Not Running**
   - Check: PR close events, scheduled triggers
   - Manual: Run cleanup workflow manually

3. **Deployment Blocked**
   - Verify: All pre-deployment checks passing
   - Check: Manual approval for production
   - Ensure: Staging is healthy first

4. **Workflow Selection Wrong**
   - Check: ci-orchestrator.yml logic
   - Override: Use workflow_dispatch with manual selection

## Security Considerations

- Secrets stored in GitHub Secrets
- GCP authentication via Workload Identity Federation
- Database credentials in Secret Manager
- JWT secrets rotated regularly
- No hardcoded credentials in workflows

## Performance Metrics

Target metrics for workflow execution:
- **Unit Tests**: < 5 minutes
- **Integration Tests**: < 10 minutes
- **E2E Tests**: < 15 minutes
- **Full CI Pipeline**: < 20 minutes
- **Staging Deployment**: < 10 minutes
- **Production Deployment**: < 30 minutes (including approvals)

## Contributing

When modifying workflows:
1. Maintain compatibility with CLAUDE.md requirements
2. Ensure mission critical tests remain first priority
3. Test locally with act before committing
4. Document any new environment variables or secrets
5. Update this README with changes
6. Follow git commit standards in `SPEC/git_commit_atomic_units.xml`

## Related Documentation

- [`CLAUDE.md`](../../CLAUDE.md) - Core system requirements
- [`SPEC/learnings/websocket_agent_integration_critical.xml`](../../SPEC/learnings/websocket_agent_integration_critical.xml) - WebSocket requirements
- [`MASTER_WIP_STATUS.md`](../../MASTER_WIP_STATUS.md) - Current system status
- [`DEFINITION_OF_DONE_CHECKLIST.md`](../../DEFINITION_OF_DONE_CHECKLIST.md) - Module completion checklist
- [`unified_test_runner.py`](../../unified_test_runner.py) - Test execution framework