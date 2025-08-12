# CI/CD Testing Guide

## Overview

Netra's CI/CD testing pipeline provides comprehensive, intelligent test automation with AI-powered auto-fixing capabilities. The system automatically maps git events to appropriate test depths, provides transparent results directly in PRs, and can automatically fix many common test failures.

## Quick Start

### Running Tests Locally

```bash
# Quick validation (30s)
python test_runner.py --level smoke

# Component testing (1-2min)
python test_runner.py --level unit

# Feature validation (3-5min)  
python test_runner.py --level integration

# Full coverage (10-15min)
python test_runner.py --level comprehensive

# Essential paths only (1-2min)
python test_runner.py --level critical
```

### Triggering Tests in PRs

Add a comment to your PR:

```
@test                    # Runs default integration tests
@test smoke             # Quick smoke tests
@test unit              # Unit tests with sharding
@test comprehensive     # Full test suite
@test performance       # Performance benchmarks
@test security          # Security scans
```

### Auto-Fix for Failed Tests

The system automatically attempts to fix failed tests. To control this:

```
@autofix                # Manually trigger auto-fix
@disable-autofix        # Disable for this PR
```

Add label `no-autofix` to permanently disable for a PR.

## Test Levels

### Smoke Tests (30s)
- **Purpose**: Quick validation of basic functionality
- **When**: Every push to feature branches
- **Coverage**: Critical paths, imports, basic operations
- **Required for merge**: Yes

### Unit Tests (1-2min)
- **Purpose**: Component-level testing
- **When**: PR opened or updated
- **Coverage**: Individual modules and functions
- **Sharding**: Parallel execution across 5 shards
- **Required for merge**: Yes

### Integration Tests (3-5min)
- **Purpose**: Feature validation
- **When**: PR marked ready for review
- **Coverage**: API endpoints, service interactions
- **Sharding**: Backend, frontend, E2E
- **Required for merge**: No (recommended)

### Comprehensive Tests (10-15min)
- **Purpose**: Complete coverage validation
- **When**: Pre-merge, nightly builds
- **Coverage**: Full test suite, 97% coverage target
- **Sharding**: All available
- **Required for merge**: No

### Critical Tests (1-2min)
- **Purpose**: Production stability
- **When**: Push to main branch
- **Coverage**: Essential business logic
- **Required for merge**: Yes (for main)

### Performance Tests (30min)
- **Purpose**: Benchmark and regression detection
- **When**: On-demand, release candidates
- **Coverage**: Load tests, memory profiling
- **Required for merge**: No

### Security Tests (10min)
- **Purpose**: Vulnerability scanning
- **When**: On-demand, releases
- **Coverage**: Dependencies, SAST, secrets
- **Required for merge**: No (for releases)

## AI Auto-Fix System

### How It Works

1. **Detection**: Test failure in PR triggers analysis
2. **Classification**: Error type and fixability determined
3. **Generation**: AI generates fix using Claude/Gemini/GPT-4
4. **Validation**: Fix is tested in isolation
5. **Application**: Validated fix is committed to PR

### Supported Fix Types

**High Confidence (90%+)**
- Import/module errors
- Syntax errors
- Indentation issues
- Simple type errors

**Medium Confidence (50-90%)**
- Assertion failures
- Attribute errors
- Missing arguments
- Value errors

**Low/No Auto-Fix**
- Network timeouts
- External dependencies
- Complex logic errors
- Security issues

### Controlling Auto-Fix

```yaml
# In .github/netra.yml
auto_fix:
  enabled: false  # Disable globally
```

```bash
# In PR comments
@disable-autofix  # Disable for this PR
@autofix         # Manually trigger
```

## Test Results

### PR Comments

Every test run updates a comment in your PR with:
- Pass/fail status with visual indicators
- Failed test details with stack traces
- Coverage changes
- Performance metrics
- Links to full logs

### Commit Statuses

Required checks:
- `continuous-integration/netra/smoke`
- `continuous-integration/netra/unit`

Optional checks:
- `continuous-integration/netra/integration`
- `continuous-integration/netra/coverage`

### Artifacts

Test results are stored as artifacts:
- JSON test results
- Coverage reports (HTML, XML)
- Performance profiles
- Test logs

## Advanced Features

### Test Sharding

Tests are automatically distributed across parallel jobs:

```python
# In test_runner.py
python test_runner.py --level unit --shard core
python test_runner.py --level unit --shard agents
```

### Test Impact Analysis

Only runs tests affected by your changes:

```bash
# Analyzes git diff and dependency graph
python scripts/ci/test_impact_analysis.py
```

### Flaky Test Detection

Tests failing intermittently are:
1. Automatically retried (up to 3 times)
2. Tracked in dashboard
3. Quarantined after threshold

### Debug Mode

For failing tests in CI:

```
@debug  # Enables SSH access for 30min (admin only)
@replay # Reruns with verbose logging
```

## Cost Optimization

### Current Settings

- **Monthly budget**: $300
- **Spot instances**: Enabled for non-critical
- **Test deduplication**: 24h cache
- **Heavy tests**: Scheduled 2-6am UTC

### Cost Breakdown

| Component | Monthly Cost |
|-----------|-------------|
| GitHub runners | $0 (free tier) |
| GCP spot instances | ~$150 |
| Storage | ~$50 |
| AI auto-fix | ~$100 |

## Troubleshooting

### Common Issues

**Tests not running**
- Check PR permissions
- Verify branch protection rules
- Check workflow concurrency limits

**Auto-fix not working**
- Verify API keys are set
- Check error is in fixable list
- Review cost limits

**Slow test execution**
- Check runner availability
- Review test sharding
- Consider test impact analysis

**Flaky tests**
- Review quarantine list
- Check for race conditions
- Add retries for network calls

### Getting Help

1. Check workflow logs in Actions tab
2. Review artifact outputs
3. Use `@debug` for interactive debugging
4. Create issue with `ci-testing` label

## Configuration

### Repository Settings

Required secrets:
```
ANTHROPIC_API_KEY    # For Claude auto-fix
GOOGLE_API_KEY       # For Gemini auto-fix
OPENAI_API_KEY       # For GPT-4 auto-fix
SLACK_WEBHOOK        # Optional notifications
```

### Branch Protection

Recommended settings for `main`:
- Require status checks
- Require branches up to date
- Require conversation resolution
- Include administrators

### Custom Configuration

Edit `.github/netra.yml`:

```yaml
test_mapping:
  push:
    feature_branch: unit  # Change from smoke
    
auto_fix:
  enabled: false  # Disable auto-fix
  
cost_optimization:
  monthly_budget: 500  # Increase budget
```

## Best Practices

1. **Write fast tests**: Keep smoke < 30s, unit < 2min
2. **Use appropriate levels**: Don't run comprehensive for every push
3. **Fix flaky tests**: Don't just retry, fix root cause
4. **Review auto-fixes**: Verify AI-generated fixes make sense
5. **Monitor costs**: Check dashboard weekly
6. **Cache aggressively**: Dependencies, Docker layers
7. **Parallelize smartly**: Balance shards by time
8. **Clean up artifacts**: Set appropriate retention

## Metrics and Monitoring

Dashboard: https://netra-tests.web.app

Key metrics:
- **Test success rate**: Target > 95%
- **P95 execution time**: Track trends
- **Flaky test count**: Keep < 5
- **Auto-fix success**: Target > 50%
- **Monthly cost**: Stay under budget

## Future Enhancements

Planned improvements:
- [ ] Visual regression testing
- [ ] Mutation testing
- [ ] Distributed tracing
- [ ] Test prioritization ML model
- [ ] Cross-browser testing
- [ ] Mobile app testing
- [ ] Contract testing
- [ ] Chaos engineering