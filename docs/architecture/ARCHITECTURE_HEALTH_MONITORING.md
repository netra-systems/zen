# Architecture Health Monitoring System

## Overview

The Architecture Health Monitoring System provides comprehensive tracking and visualization of architectural compliance in the Netra AI codebase. It enforces CLAUDE.md rules and provides actionable insights for maintaining code quality.

## Key Features

### 🔍 Comprehensive Scanning
- **File Size Violations**: Identifies files exceeding 300 lines
- **Function Complexity**: Detects functions over 8 lines  
- **Duplicate Types**: Finds duplicate type definitions
- **Test Stubs**: Locates test stubs in production code
- **Type Safety**: Checks for missing type annotations
- **Architectural Debt**: Identifies TODOs, FIXMEs, and code smells
- **Code Quality**: Detects quality issues and anti-patterns

### 📊 Visual Dashboard
- Interactive HTML dashboard with charts and drill-down capabilities
- Real-time violation tracking and trend analysis
- Severity-based prioritization (Critical, High, Medium)
- Worst offenders identification with remediation suggestions

### 🚀 CI/CD Integration
- Automated GitHub Actions workflow
- Pull request commenting with health summary
- Issue creation for critical violations
- Slack notifications for team awareness
- GitHub Pages deployment for dashboard hosting

## Quick Start

### 1. CLI Usage

```bash
# Basic scan with CLI output only
python scripts/architecture_health.py --cli-only

# Full scan with dashboard generation
python scripts/architecture_health.py --path . --output-html reports/dashboard.html --output-json reports/health.json

# Fail build on violations (for CI/CD)
python scripts/architecture_health.py --fail-on-violations
```

### 2. Command Line Options

| Option | Description |
|--------|-------------|
| `--path` | Root directory to scan (default: current directory) |
| `--output-html` | HTML dashboard output path |
| `--output-json` | JSON report output path |
| `--cli-only` | Show only CLI summary (no file generation) |
| `--fail-on-violations` | Exit with error code if violations found |

### 3. GitHub Actions Integration

The system automatically runs on:
- Push to main/develop branches
- Pull requests
- Daily scheduled scans (9 AM UTC)
- Manual workflow dispatch

## Understanding the Results

### Health Score Metrics

| Score Range | Status | Action Required |
|-------------|--------|-----------------|
| 90-100% | 🟢 Excellent | Maintain current standards |
| 70-89% | 🟡 Good | Minor improvements needed |
| 0-69% | 🔴 Needs Improvement | Immediate attention required |

### Violation Severity Levels

- **Critical**: Immediate action required (files >500 lines, functions >20 lines)
- **High**: Address within current sprint (files >400 lines, functions >15 lines)
- **Medium**: Plan for next sprint (moderate violations, missing types)

### Sample Output

```
================================================================================
ARCHITECTURE HEALTH DASHBOARD
================================================================================

OVERALL HEALTH SCORE: 85% (GOOD)
Total Violations: 45
Files Scanned: 1063
Functions Scanned: 7183

VIOLATION BREAKDOWN:
  File Size (>300 lines): 12
  Function Complexity (>8 lines): 28
  Duplicate Types: 3
  Test Stubs: 2
  Missing Type Annotations: 0
  Architectural Debt: 0
  Code Quality Issues: 0

WORST OFFENDERS:
  1. app/services/complex_service.py (450 lines)
  2. app/agents/supervisor.py (380 lines)

RECOMMENDED ACTIONS:
  - Split 12 oversized files into focused modules
  - Refactor 28 complex functions into smaller units
```

## Dashboard Features

### 📈 Interactive Charts
- Violation distribution pie chart
- Severity breakdown bar chart
- Compliance score trends over time

### 📋 Detailed Tables
- **File Size Violations**: List of oversized files with recommendations
- **Function Complexity**: Complex functions requiring refactoring
- **Duplicate Types**: Type definitions needing consolidation
- **Worst Offenders**: Files requiring immediate attention

### 🎯 Actionable Recommendations
Each violation includes:
- Severity level and priority
- Specific remediation steps
- Target compliance timeline
- Links to architecture guidelines

## Best Practices

### 1. Regular Monitoring
- Run scans before major commits
- Review dashboard weekly
- Address critical violations immediately
- Track improvement trends

### 2. Team Integration
- Include health scores in sprint planning
- Set compliance targets for releases
- Use violation counts as technical debt metrics
- Share dashboard URL with stakeholders

### 3. Continuous Improvement
- Set team goals for compliance scores
- Celebrate architectural improvements
- Use metrics to guide refactoring priorities
- Establish architecture review gates

## Remediation Guidelines

### File Size Violations (>300 lines)
1. **Identify Responsibilities**: What does this file do?
2. **Find Natural Boundaries**: Separate concerns
3. **Extract Modules**: Create focused, single-purpose files
4. **Update Imports**: Ensure clean dependencies
5. **Test**: Verify functionality after splitting

### Function Complexity (>8 lines)
1. **Extract Helper Functions**: Break down logic
2. **Use Early Returns**: Reduce nesting
3. **Separate Concerns**: One function, one responsibility  
4. **Improve Readability**: Clear variable names
5. **Add Documentation**: Explain complex logic

### Type Safety Issues
1. **Add Type Annotations**: Function parameters and returns
2. **Use Strong Types**: Avoid `Any` and generic types
3. **Leverage Pydantic**: For data validation
4. **Type Guards**: For runtime type checking
5. **mypy Integration**: Static type checking

## Integration with Existing Tools

### GitHub Actions
- Automated on every push/PR
- Comments on PRs with health summary
- Creates issues for critical violations
- Deploys dashboard to GitHub Pages

### Development Workflow
```bash
# Before committing
python scripts/architecture_health.py --cli-only

# Before releasing
python scripts/architecture_health.py --fail-on-violations

# Generate reports
python scripts/architecture_health.py --output-html dashboard.html
```

### CI/CD Pipeline Integration
```yaml
- name: Architecture Health Check
  run: python scripts/architecture_health.py --fail-on-violations
  
- name: Upload Health Reports
  uses: actions/upload-artifact@v4
  with:
    name: architecture-health
    path: reports/
```

## Troubleshooting

### Common Issues

**Unicode Encoding Errors**
- Ensure Python console supports UTF-8
- Use `--cli-only` flag for basic terminals

**Large Codebase Performance**
- Use `--path` to scan specific directories
- Run incrementally for large projects
- Consider parallel processing for CI

**False Positives**
- Update skip patterns in script
- Exclude generated files
- Customize thresholds for project needs

### Performance Optimization
- Typical scan time: ~30 seconds for 1000+ files
- Memory usage: ~100MB for large codebases
- Network: Dashboard uses CDN for Chart.js

## Roadmap

### Planned Features
- Historical trend analysis
- Custom rule configuration
- Integration with code quality tools
- Automated refactoring suggestions
- Team performance metrics

### Contributing
- Report issues in GitHub
- Submit PRs for improvements
- Suggest new violation types
- Help with documentation

## Support

- **Documentation**: See CLAUDE.md for architecture rules
- **Issues**: GitHub repository issues
- **Team Chat**: Architecture health Slack channel
- **Dashboard**: Live at [Architecture Health Dashboard](./reports/architecture_dashboard.html)

---

**Remember**: Architecture health is a team effort. Regular monitoring and continuous improvement lead to maintainable, scalable codebases.