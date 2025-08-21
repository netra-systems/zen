# Test Operations Runbook

## Overview

This runbook provides operational procedures for maintaining the Netra AI Platform test infrastructure. Follow these procedures to ensure continuous test quality and system reliability.

**Business Value**: Maintains >99.9% platform reliability, protecting $100K+ MRR through proactive test management.

## Daily Operations

### Morning Health Check (5 minutes)

```bash
# 1. Check overall test health
python test_runner.py --show-failing

# 2. Quick smoke test validation
python test_runner.py --level smoke

# 3. Check test metrics dashboard
python scripts/test_metrics_dashboard.py --dashboard

# 4. Verify feature flag status
echo "Feature flags status will be shown in test output"
```

**Expected Results:**
- ✅ No failing tests or <2% failure rate
- ✅ Smoke tests complete in <30 seconds
- ✅ All metrics meet SLA requirements
- ✅ Feature flags properly configured

### Pre-Release Checklist (15 minutes)

**MANDATORY before any production deployment:**

```bash
# 1. Integration tests with real LLM (CRITICAL)
python test_runner.py --level integration --real-llm

# 2. Performance validation
python test_runner.py --level performance

# 3. Agent testing with real LLM (if agent changes)
python test_runner.py --level agents --real-llm

# 4. Generate release test report
python scripts/test_metrics_dashboard.py --daily-report > reports/pre_release_$(date +%Y%m%d).md
```

**Success Criteria:**
- ✅ Integration tests: >95% pass rate
- ✅ Performance tests: All SLAs met
- ✅ Real LLM tests: No integration failures
- ✅ Report generated successfully

### End-of-Day Summary (3 minutes)

```bash
# 1. Collect daily metrics
python scripts/test_metrics_dashboard.py --collect integration

# 2. Check for flaky tests
python scripts/test_metrics_dashboard.py --flaky-tests

# 3. Clean up temporary test files
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
```

## Weekly Maintenance

### Monday: Test Health Assessment

```bash
# 1. Comprehensive test suite validation
python test_runner.py --level comprehensive

# 2. Coverage analysis
python test_runner.py --level unit --coverage-output weekly_coverage.xml

# 3. Performance trend analysis
python scripts/test_metrics_dashboard.py --dashboard

# 4. Update test dependencies
pip install -r requirements.txt --upgrade --dry-run
```

### Wednesday: Flaky Test Resolution

```bash
# 1. Identify flaky tests
python scripts/test_metrics_dashboard.py --flaky-tests

# 2. Run flaky tests multiple times to confirm
python test_runner.py --run-failing --repeat 5

# 3. Document flaky test patterns
echo "Document findings in docs/testing/flaky_test_log.md"

# 4. Create tickets for persistent flaky tests
echo "Create GitHub issues for tests with >10% flake rate"
```

### Friday: Performance Optimization

```bash
# 1. Performance test suite
python test_runner.py --level performance

# 2. Identify slow tests
pytest --durations=20

# 3. Database cleanup
python scripts/cleanup_test_data.py

# 4. Generate weekly report
python scripts/generate_weekly_test_report.py
```

## Monthly Operations

### First Monday: Infrastructure Review

```bash
# 1. Test environment health check
python scripts/test_environment_check.py

# 2. Database maintenance
python scripts/test_db_maintenance.py

# 3. Log rotation and cleanup
python scripts/cleanup_test_logs.py --older-than 30

# 4. Dependency security audit
pip audit

# 5. Test coverage trend analysis
python scripts/analyze_coverage_trends.py --months 3
```

### Second Monday: Documentation Update

```bash
# 1. Verify documentation accuracy
python scripts/validate_test_documentation.py

# 2. Update test metrics in documentation
python scripts/update_test_metrics_docs.py

# 3. Review and update troubleshooting guides
echo "Manual review of docs/testing/COMPREHENSIVE_TEST_DOCUMENTATION.md"

# 4. Update operational procedures
echo "Manual review of this runbook for accuracy"
```

### Third Monday: Capacity Planning

```bash
# 1. Analyze test execution trends
python scripts/analyze_test_capacity.py

# 2. Review resource utilization
python scripts/test_resource_analysis.py

# 3. Plan infrastructure scaling
echo "Review test execution times and plan optimizations"

# 4. Update SLA targets if needed
echo "Review and update performance targets in test_config.py"
```

### Fourth Monday: Disaster Recovery Testing

```bash
# 1. Test backup and restore procedures
python scripts/test_backup_restore.py

# 2. Validate failover scenarios
python scripts/test_failover_scenarios.py

# 3. Test environment recreation
python scripts/recreate_test_environment.py --dry-run

# 4. Document recovery procedures
echo "Update disaster recovery documentation"
```

## Incident Response Procedures

### Test Failures (>5% failure rate)

**Priority: HIGH - Immediate action required**

```bash
# 1. Identify failing tests
python test_runner.py --show-failing

# 2. Run only failing tests for quick diagnosis
python test_runner.py --run-failing

# 3. Check for environment issues
python scripts/diagnose_test_environment.py

# 4. Check recent code changes
git log --since="24 hours ago" --oneline

# 5. Rollback if necessary
echo "Consider rollback if failures are widespread"
```

**Escalation**: If >20% tests failing, escalate to engineering lead immediately.

### Performance Degradation (Tests >2x slower)

**Priority: MEDIUM - Action within 4 hours**

```bash
# 1. Identify slow tests
pytest --durations=10

# 2. Check system resources
python scripts/check_test_resources.py

# 3. Analyze database performance
python scripts/analyze_db_performance.py

# 4. Clear test data if needed
python scripts/cleanup_test_data.py --force

# 5. Restart test infrastructure if needed
python scripts/restart_test_services.py
```

### Flaky Tests (>10% flake rate)

**Priority: MEDIUM - Action within 1 week**

```bash
# 1. Identify most flaky tests
python scripts/test_metrics_dashboard.py --flaky-tests

# 2. Analyze flaky test patterns
python scripts/analyze_flaky_patterns.py

# 3. Create improvement tickets
echo "Create GitHub issues with 'flaky-test' label"

# 4. Implement fixes or disable problematic tests
echo "Fix underlying issues or mark as @pytest.mark.skip temporarily"
```

### Test Infrastructure Outage

**Priority: CRITICAL - Immediate action required**

```bash
# 1. Check service status
python scripts/check_test_services.py

# 2. Restart services
docker-compose -f docker-compose.test.yml restart

# 3. Validate basic functionality
python test_runner.py --level smoke

# 4. Full validation after restoration
python test_runner.py --level integration

# 5. Document incident
echo "Create incident report with root cause analysis"
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Test Pass Rate**: >95% (Alert if <90%)
2. **Test Execution Time**: Within SLA (Alert if >150% of target)
3. **Flaky Test Rate**: <2% (Alert if >5%)
4. **Coverage**: >70% (Alert if <65%)
5. **Test Infrastructure Uptime**: >99% (Alert if <95%)

### Alert Thresholds

```bash
# Daily automated checks
crontab -e
# Add these entries:

# 8 AM - Morning health check
0 8 * * * /path/to/python /path/to/test_runner.py --level smoke --ci

# 6 PM - Daily metrics collection
0 18 * * * /path/to/python /path/to/scripts/test_metrics_dashboard.py --daily-report

# Every 4 hours - Check for failing tests
0 */4 * * * /path/to/python /path/to/scripts/check_test_health.py --alert-on-failures
```

### Notification Channels

- **Slack**: #test-alerts (automated notifications)
- **Email**: engineering-team@netrasystems.ai (critical failures)
- **Dashboard**: Internal test metrics dashboard
- **GitHub Issues**: Automated ticket creation for persistent issues

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Database Connection Failures

**Symptoms**: Tests failing with database connection errors

```bash
# Diagnosis
python scripts/test_db_connection.py

# Solutions
docker-compose -f docker-compose.test.yml restart postgresql
python scripts/reset_test_database.py
```

#### 2. Redis Connection Issues

**Symptoms**: WebSocket or caching tests failing

```bash
# Diagnosis
redis-cli ping

# Solutions
docker-compose -f docker-compose.test.yml restart redis
python scripts/clear_redis_test_data.py
```

#### 3. LLM API Rate Limiting

**Symptoms**: Real LLM tests failing with rate limit errors

```bash
# Diagnosis
python scripts/check_llm_api_status.py

# Solutions
python test_runner.py --level agents --real-llm --parallel 1 --llm-timeout 60
# Or use mock mode temporarily
python test_runner.py --level agents  # Without --real-llm
```

#### 4. Memory Issues

**Symptoms**: Tests crashing with out-of-memory errors

```bash
# Diagnosis
python scripts/analyze_memory_usage.py

# Solutions
python scripts/cleanup_test_processes.py
docker system prune -f
```

#### 5. Import Errors

**Symptoms**: ModuleNotFoundError or import failures

```bash
# Diagnosis
python -c "import sys; print(sys.path)"

# Solutions
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pip install -e .
```

## Quality Gates

### Pre-Commit Quality Gate

**Automated checks before code commit:**

```bash
# Required checks
python test_runner.py --level smoke
python scripts/lint_check.py
python scripts/type_check.py
```

**Success Criteria**: All checks must pass.

### Pre-Merge Quality Gate

**Required for pull request approval:**

```bash
# Integration validation
python test_runner.py --level integration --no-coverage --fast-fail

# Code quality validation
python scripts/code_quality_check.py
```

**Success Criteria**: >95% test pass rate, no quality issues.

### Pre-Release Quality Gate

**MANDATORY before production deployment:**

```bash
# Comprehensive validation
python test_runner.py --level integration --real-llm
python test_runner.py --level performance
python test_runner.py --level comprehensive  # For major releases
```

**Success Criteria**: 100% critical test pass rate, all SLAs met.

## Performance Benchmarks

### Target Performance (SLA Requirements)

| Test Level | Target Time | Max Acceptable |
|------------|-------------|----------------|
| smoke | <30s | 45s |
| unit | <120s | 180s |
| integration | <300s | 450s |
| agents | <180s | 300s |
| comprehensive | <2700s | 3600s |
| performance | <300s | 450s |

### Memory Limits

- **Per test process**: <2GB
- **Total test execution**: <8GB
- **Database during tests**: <1GB

### Network Requirements

- **LLM API calls**: <5 calls/second (to avoid rate limits)
- **Database connections**: <50 concurrent connections
- **WebSocket connections**: <100 concurrent connections

## Continuous Improvement

### Weekly Review Process

1. **Metrics Analysis**: Review test execution trends
2. **Failure Pattern Analysis**: Identify recurring issues
3. **Performance Optimization**: Address slow tests
4. **Process Improvement**: Update procedures based on learnings

### Quarterly Goals

- **Reduce flaky test rate** by 25%
- **Improve test execution speed** by 15%
- **Increase coverage** by 5% for critical components
- **Reduce manual intervention** by 30%

### Success Metrics

- **Test Reliability**: >99% infrastructure uptime
- **Developer Experience**: <5 minute feedback cycle
- **Production Protection**: Zero production issues from untested code
- **Cost Efficiency**: Optimize LLM testing costs while maintaining quality

## Emergency Contacts

### Escalation Matrix

| Issue Level | Response Time | Contact |
|-------------|---------------|---------|
| Critical | Immediate | On-call engineer |
| High | 2 hours | Engineering lead |
| Medium | 24 hours | QA team |
| Low | 1 week | Development team |

### Communication Channels

- **Immediate**: Slack #engineering-alerts
- **Updates**: Slack #test-status
- **Documentation**: Update this runbook
- **Post-mortem**: Document in docs/post-mortems/

---

## Conclusion

This runbook ensures systematic maintenance of the test infrastructure while supporting business objectives. Regular execution of these procedures maintains:

1. **High Reliability**: >99% platform uptime
2. **Fast Feedback**: Quick test execution for development velocity
3. **Quality Assurance**: Comprehensive validation before releases
4. **Cost Control**: Efficient resource utilization
5. **Continuous Improvement**: Data-driven optimization

**Remember**: The goal is to maintain customer trust and platform reliability while enabling rapid development. Every procedure should contribute to these objectives.

---
*Generated by AGENT 20 - Documentation and Final Validation*
*Last Updated: 2025-08-19*