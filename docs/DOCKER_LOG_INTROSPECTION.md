# Docker Compose Log Introspection System

## Overview

The Docker Compose Log Introspection System provides comprehensive error detection, categorization, and automatic issue generation for Docker Compose deployments. This toolset helps identify and track errors across multiple services, creating actionable GitHub issues when problems are detected.

## Components

### 1. **docker_compose_log_introspector.py**
Main log analysis tool that:
- Retrieves and parses Docker Compose logs
- Detects errors using pattern matching
- Categorizes errors by type and severity
- Generates detailed error reports
- Supports real-time monitoring

### 2. **docker_log_issue_creator.py** 
GitHub issue automation tool that:
- Creates GitHub issues from detected errors
- Implements deduplication to prevent duplicate issues
- Groups related errors intelligently
- Provides actionable remediation steps

### 3. **test_log_introspection.py**
Test suite ensuring system reliability

## Quick Start

### Basic Analysis
```bash
# Analyze all running services
python scripts/docker_compose_log_introspector.py analyze

# Analyze specific service
python scripts/docker_compose_log_introspector.py analyze --service backend

# Analyze with custom compose file
python scripts/docker_compose_log_introspector.py analyze -f docker-compose.dev.yml
```

### Generate Reports
```bash
# Save report to file
python scripts/docker_compose_log_introspector.py analyze --output error_report.txt

# Analyze recent logs only (last 5 minutes)
python scripts/docker_compose_log_introspector.py analyze --since 5m
```

### Real-time Monitoring
```bash
# Monitor logs every 30 seconds
python scripts/docker_compose_log_introspector.py monitor --interval 30

# Monitor with limited iterations
python scripts/docker_compose_log_introspector.py monitor --max-iterations 10
```

### Create GitHub Issues
```bash
# Dry run - see what issues would be created
python scripts/docker_log_issue_creator.py --dry-run

# Actually create issues
python scripts/docker_log_issue_creator.py --create-issues

# Create issues for errors with 3+ occurrences
python scripts/docker_log_issue_creator.py --create-issues --min-occurrences 3

# Clear deduplication cache
python scripts/docker_log_issue_creator.py --clear-cache
```

## Error Categories

The system categorizes errors into the following types:

| Category | Description | Example Patterns |
|----------|-------------|------------------|
| **Database Connection** | Database connectivity issues | `connection refused`, `psycopg2.OperationalError` |
| **Authentication** | Auth/JWT failures | `401 unauthorized`, `token expired` |
| **Network** | Network connectivity problems | `ECONNREFUSED`, `ETIMEDOUT` |
| **Configuration** | Missing/invalid config | `KeyError`, `env var not set` |
| **Memory/Resource** | Resource exhaustion | `out of memory`, `too many open files` |
| **Dependency** | Missing packages/modules | `ModuleNotFoundError`, `npm ERR` |
| **Timeout** | Operation timeouts | `timeout`, `deadline exceeded` |
| **Permission** | Access denied errors | `permission denied`, `EACCES` |
| **Syntax/Code** | Runtime code errors | `SyntaxError`, `TypeError` |
| **Migration** | Database migration issues | `migration failed`, `alembic error` |
| **WebSocket** | WebSocket connectivity | `websocket error`, `ws connection failed` |
| **CORS** | Cross-origin issues | `CORS blocked`, `No Access-Control-Allow-Origin` |
| **SSL/TLS** | Certificate problems | `SSL error`, `certificate verify failed` |

## Error Severity Levels

| Severity | Description | Action Required |
|----------|-------------|-----------------|
| **CRITICAL** | System crashes, data loss risks | Immediate attention |
| **ERROR** | Failures needing fixes | High priority |
| **WARNING** | Potential issues | Monitor/investigate |
| **INFO** | Informational | Typically ignorable |

## Features

### Pattern-Based Detection
- Comprehensive regex patterns for common error types
- Context preservation (lines before/after errors)
- Ignore patterns for expected errors (e.g., in tests)

### Smart Grouping
- Groups similar errors across services
- Prevents duplicate issue creation
- Tracks error frequency and timing

### Actionable Output
- Detailed error reports with statistics
- Service-specific breakdowns
- Recommended remediation steps
- Direct GitHub issue creation

### Flexible Configuration
- Support for different compose files
- Configurable tail length and time ranges
- Project name specification
- Service-specific analysis

## Use Cases

### 1. Post-Deployment Validation
After deploying changes, run analysis to catch any new errors:
```bash
python scripts/docker_compose_log_introspector.py analyze --since 10m --create-issues
```

### 2. Continuous Monitoring
Set up monitoring during development:
```bash
python scripts/docker_compose_log_introspector.py monitor --interval 60
```

### 3. Debugging Specific Issues
Focus on a problematic service:
```bash
python scripts/docker_compose_log_introspector.py analyze --service backend --tail 1000
```

### 4. CI/CD Integration
Add to CI pipeline for automatic error detection:
```yaml
- name: Check for Docker errors
  run: |
    python scripts/docker_compose_log_introspector.py analyze --output errors.txt
    if grep -q "Total Errors: [1-9]" errors.txt; then
      echo "Errors detected in Docker logs"
      exit 1
    fi
```

## Example Output

### Error Report
```
============================================================
DOCKER COMPOSE LOG INTROSPECTION REPORT
============================================================
Generated: 2024-01-15T10:30:45

SUMMARY
----------------------------------------
Services Analyzed: 3
Total Log Lines: 5432
Total Errors: 12
Total Warnings: 5

ERRORS BY CATEGORY
----------------------------------------
  Database Connection: 8
  Authentication: 3
  Configuration: 1

ERRORS BY SEVERITY
----------------------------------------
  error: 11
  warning: 5
  critical: 1

DETAILED ERRORS BY SERVICE
============================================================

BACKEND
----------------------------------------
  [Database Connection] (8 occurrences)
    Line 234: psycopg2.OperationalError: could not connect to server...
    Line 567: connection refused to database at localhost:5432...
    ... and 6 more
```

### GitHub Issue
```markdown
## [ERROR] Database Connection - 8 occurrences in 2 service(s)

**Generated:** 2024-01-15T10:30:45
**Category:** Database Connection
**Severity:** error
**Total Occurrences:** 8
**Affected Services:** backend, worker

### Error Samples
...

### Recommended Actions
- [ ] Check PostgreSQL container status
- [ ] Verify database credentials
- [ ] Review connection pool settings
```

## Troubleshooting

### Docker Compose Not Found
Ensure Docker and Docker Compose are installed:
```bash
docker --version
docker compose --version
```

### GitHub CLI Not Available
Install GitHub CLI for issue creation:
```bash
# Windows
winget install GitHub.cli

# Mac
brew install gh

# Linux
sudo apt install gh
```

### Permission Errors
Ensure you have permissions to:
- Read Docker logs
- Access compose files
- Create GitHub issues (authenticate with `gh auth login`)

## Best Practices

1. **Regular Monitoring**: Run analysis after deployments and during testing
2. **Issue Deduplication**: The system tracks created issues to prevent duplicates
3. **Severity Focus**: Prioritize CRITICAL and ERROR level issues
4. **Context Review**: Check log context for root cause analysis
5. **Pattern Updates**: Add new error patterns as they're discovered

## Integration Points

- **CI/CD Pipelines**: Add as validation step
- **Monitoring Systems**: Export metrics to monitoring tools
- **Alerting**: Trigger alerts on critical errors
- **Documentation**: Auto-generate error documentation
- **Dashboards**: Create error trend visualizations

## Future Enhancements

Potential improvements:
- Machine learning for error pattern detection
- Automatic error remediation suggestions
- Integration with APM tools
- Slack/Teams notifications
- Error trend analysis
- Performance impact correlation