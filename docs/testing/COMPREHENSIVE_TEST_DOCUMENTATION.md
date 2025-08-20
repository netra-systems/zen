# Netra AI Platform - Comprehensive Test Documentation

## Overview

This documentation provides complete guidance for running, understanding, and maintaining the Netra AI Platform test suite. The test architecture is designed with business value in mind, ensuring every test validates revenue-critical functionality.

## Business Value Context

**BVJ (Business Value Justification):**
1. **Segment**: All customer segments (Free, Early, Mid, Enterprise)  
2. **Business Goal**: Ensure platform reliability and reduce customer churn
3. **Value Impact**: Prevents production issues that could lose 15-20% of customers
4. **Revenue Impact**: Protects $100K+ MRR through reliable service delivery

## Table of Contents

1. [Quick Start](#quick-start)
2. [Test Architecture](#test-architecture)
3. [Running Tests Locally](#running-tests-locally)
4. [Test Levels Explained](#test-levels-explained)
5. [Adding New Tests](#adding-new-tests)
6. [Test Metrics & Coverage](#test-metrics--coverage)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [CI/CD Integration](#cicd-integration)
9. [Real LLM Testing](#real-llm-testing)
10. [Performance Testing](#performance-testing)

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 16+ (for frontend tests)
- Docker (for database tests)
- Valid .env.test file

### Run Default Tests (Recommended)
```bash
# Default integration tests - RECOMMENDED for most development
python test_runner.py --level integration --no-coverage --fast-fail

# Quick smoke tests before commits  
python test_runner.py --level smoke

# Comprehensive testing before releases
python test_runner.py --level comprehensive --real-llm
```

### Environment Setup
```bash
# Copy test environment template
cp .env.example .env.test

# Install dependencies
pip install -r requirements.txt
npm install  # For frontend tests

# Initialize test database
python scripts/init_test_db.py
```

---

## Test Architecture

### Test Framework Structure
```
test_framework/
├── test_runner.py          # SINGLE AUTHORITATIVE TEST RUNNER
├── test_config.py          # Test levels and configuration  
├── test_discovery.py       # Test discovery and categorization
├── runner.py              # Core execution engine
├── feature_flags.py       # Feature flag management for TDD
└── reporters/             # Test reporting and metrics
```

### Test Categories (1,211 Total Tests)

| Category | Count | Purpose | Business Value |
|----------|-------|---------|---------------|
| **frontend** | 407 | React UI validation | User experience quality |
| **other** | 251 | Miscellaneous tests | General system reliability |
| **e2e** | 158 | End-to-end workflows | Customer journey validation |
| **agent** | 93 | AI agent testing | Core value proposition |
| **unit** | 70 | Component isolation | Development speed |
| **integration** | 60 | Feature validation | Release confidence |
| **websocket** | 42 | Real-time communication | Enterprise requirements |
| **api** | 33 | API endpoint testing | Integration reliability |
| **real_e2e** | 31 | Real LLM integration | Production accuracy |
| **performance** | 26 | SLA compliance | Customer satisfaction |
| **database** | 16 | Data persistence | Data integrity |
| **security** | 16 | Auth and security | Trust and compliance |
| **llm** | 8 | LLM integration | AI functionality |

### Key Principles

1. **Revenue-Driven Testing**: Every test validates business-critical functionality
2. **450-line Module Limit**: All test files must be ≤300 lines
3. **25-line Function Limit**: All test functions must be ≤8 lines  
4. **Single Test Runner**: Only use `test_runner.py` - no alternative runners
5. **Feature Flag Support**: Tests can be written before implementation using feature flags

---

## Running Tests Locally

### Test Levels Overview

| Level | Duration | Purpose | When to Use |
|-------|----------|---------|-------------|
| `smoke` | <30s | Pre-commit validation | Before every commit |
| `unit` | 1-2min | Component testing | During development |
| `integration` | 3-5min | Feature validation | **DEFAULT** - after changes |
| `agents` | 2-3min | Agent testing | After agent modifications |
| `critical` | 1-2min | Essential paths | Quick validation |
| `comprehensive` | 30-45min | Full validation | Before releases |
| `real_e2e` | 15-20min | Real LLM testing | **CRITICAL** before production |
| `performance` | 3-5min | SLA compliance | Performance validation |

### Common Commands

#### Development Workflow
```bash
# Default command for most development work
python test_runner.py --level integration --no-coverage --fast-fail

# Quick pre-commit check
python test_runner.py --level smoke

# Component development  
python test_runner.py --level unit --backend-only

# Agent development
python test_runner.py --level agents
```

#### Release Workflow  
```bash
# Before any major release (MANDATORY)
python test_runner.py --level integration --real-llm

# Full comprehensive testing
python test_runner.py --level comprehensive --real-llm

# Performance validation
python test_runner.py --level performance
```

#### Specialized Testing
```bash
# Backend only
python test_runner.py --level unit --backend-only

# Frontend only  
python test_runner.py --level unit --frontend-only

# Specific component testing
python test_runner.py --level comprehensive-agents
python test_runner.py --level comprehensive-websocket
python test_runner.py --level comprehensive-database

# Speed optimizations
python test_runner.py --level unit --ci --no-warnings --fast-fail
```

### Test Discovery
```bash
# List all available tests
python test_runner.py --list

# List tests in JSON format
python test_runner.py --list --list-format json

# List specific category
python test_runner.py --list --list-category unit

# Show failing tests
python test_runner.py --show-failing

# Run only failing tests
python test_runner.py --run-failing
```

---

## Test Levels Explained

### Default Level: Integration
**Command**: `python test_runner.py --level integration --no-coverage --fast-fail`
- **Duration**: 3-5 minutes
- **Purpose**: Feature validation, API testing  
- **Coverage**: Integration tests for component interaction
- **When**: After any feature change (DEFAULT)

### Smoke Tests  
**Command**: `python test_runner.py --level smoke`
- **Duration**: <30 seconds
- **Purpose**: Pre-commit validation, basic health checks
- **Coverage**: Critical path validation only
- **When**: Before every commit

### Unit Tests
**Command**: `python test_runner.py --level unit`  
- **Duration**: 1-2 minutes
- **Purpose**: Development validation, component testing
- **Coverage**: Unit tests with coverage enabled
- **When**: During active development

### Agent Tests
**Command**: `python test_runner.py --level agents --real-llm`
- **Duration**: 2-3 minutes (10+ with real LLM)
- **Purpose**: Quick validation of agent functionality
- **Coverage**: AI agent and workflow tests
- **When**: After agent changes (**MANDATORY with --real-llm**)

### Comprehensive Tests
**Command**: `python test_runner.py --level comprehensive`
- **Duration**: 30-45 minutes  
- **Purpose**: Pre-release validation, full system testing
- **Coverage**: Full test suite with coverage
- **When**: Before production deployments

### Real E2E Tests (CRITICAL)
**Command**: `python test_runner.py --level real_e2e --real-llm`
- **Duration**: 15-20 minutes
- **Purpose**: End-to-end validation with real LLM calls  
- **Coverage**: Real service integrations
- **When**: **MANDATORY** before major releases

### Performance Tests  
**Command**: `python test_runner.py --level performance`
- **Duration**: 3-5 minutes
- **Purpose**: Validate response times meet business SLA requirements
- **Coverage**: Performance and load tests  
- **When**: Performance validation and SLA compliance

---

## Adding New Tests

### Test File Structure
```python
"""
Test module for [Component Name].
MANDATORY: File must be ≤300 lines, functions ≤8 lines.

BVJ (Business Value Justification):
1. Segment: [Free/Early/Mid/Enterprise]
2. Business Goal: [Specific business objective]  
3. Value Impact: [Quantified impact]
4. Revenue Impact: [Revenue protection/growth]
"""

import pytest
from unittest.mock import Mock, patch
from app.core.types import [StronglyTypedModels]

class TestComponentName:
    """Test class following 450-line limit."""
    
    def test_core_functionality(self):
        """Test core business-critical functionality (≤8 lines)."""
        # Setup
        component = ComponentName()
        
        # Execute  
        result = component.core_method()
        
        # Assert business value
        assert result.is_successful
        assert result.meets_sla_requirements()
```

### Test Categories and Markers
```python
# Smoke tests (critical path only)
@pytest.mark.smoke
def test_critical_path():
    pass

# Unit tests (component isolation)  
@pytest.mark.unit
def test_component_unit():
    pass

# Integration tests (feature validation)
@pytest.mark.integration  
def test_feature_integration():
    pass

# Agent tests (AI functionality)
@pytest.mark.agent
def test_agent_workflow():
    pass

# Real LLM tests (production validation)
@pytest.mark.real_services
def test_real_llm_integration():
    pass

# Performance tests (SLA validation)
@pytest.mark.performance
def test_response_time_sla():
    pass
```

### Async Test Patterns
```python
@pytest.mark.asyncio
async def test_async_functionality():
    """Async test following 25-line limit."""
    # Setup
    service = await ServiceFactory.create_async()
    
    # Execute
    result = await service.async_method()
    
    # Assert
    assert result.success
```

### Feature Flag Support (TDD)
```python
from test_framework.feature_flags import feature_flag

@feature_flag("new_feature", default=False)  
def test_new_feature():
    """Test can be written before implementation."""
    # Test implementation for future feature
    pass
```

### Strong Type Safety (MANDATORY)
```python
from app.core.types import (
    AgentRequest,
    AgentResponse,
    ValidationResult
)

def test_strongly_typed_interfaces():
    """All tests must use strongly typed models."""
    request = AgentRequest(
        session_id="test_session",
        message="test message"
    )
    
    result = process_agent_request(request)
    
    assert isinstance(result, AgentResponse)
    assert result.success is True
```

---

## Test Metrics & Coverage

### Coverage Requirements
- **Minimum Coverage**: 70% (enforced)
- **Critical Components**: 90%+ coverage required
- **Agent Components**: 85%+ coverage required  
- **API Endpoints**: 80%+ coverage required

### Coverage Commands
```bash
# Run with coverage (default for comprehensive levels)
python test_runner.py --level comprehensive

# Skip coverage for speed  
python test_runner.py --level integration --no-coverage

# Generate coverage report
python test_runner.py --level unit --coverage-output coverage.xml

# View coverage report
open reports/coverage/html/index.html
```

### Performance Metrics
- **Smoke Tests**: <30 seconds (SLA)
- **Unit Tests**: <2 minutes (SLA)  
- **Integration Tests**: <5 minutes (SLA)
- **Comprehensive Tests**: <45 minutes (SLA)

### Test Quality Metrics
- **Pass Rate Target**: >95%
- **Flaky Test Rate**: <2%  
- **Test Execution Time**: Monitored and optimized
- **Coverage Trend**: Must be improving or stable

---

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Import Errors
**Problem**: `ModuleNotFoundError` or import issues
```bash
# Solution: Check Python path
python -c "import sys; print(sys.path)"

# Ensure project root is in path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### 2. Database Connection Issues
**Problem**: Database tests failing
```bash
# Solution: Initialize test database
python scripts/init_test_db.py

# Check database status  
python -c "from app.db.connection import get_db; print('DB OK')"
```

#### 3. Test Environment Issues
**Problem**: Configuration or environment errors
```bash
# Solution: Verify test environment
cp .env.example .env.test

# Check environment loading
python -c "from dotenv import load_dotenv; load_dotenv('.env.test'); print('ENV OK')"
```

#### 4. Feature Flag Issues  
**Problem**: Tests behaving unexpectedly
```bash
# Solution: Check feature flag status
python test_runner.py  # Shows feature flag summary

# Reset feature flags if needed
rm -f .feature_flags.json
```

#### 5. Coverage Issues
**Problem**: Coverage requirements not met
```bash
# Solution: Run coverage analysis
python test_runner.py --level unit --coverage-output coverage.xml

# Identify missing coverage
coverage html --show-contexts
open htmlcov/index.html
```

#### 6. Slow Test Performance
**Problem**: Tests taking too long
```bash
# Solution: Use speed optimizations
python test_runner.py --level unit --ci --no-warnings --fast-fail

# Profile slow tests
python test_runner.py --level unit --profile
```

#### 7. Real LLM Test Issues
**Problem**: LLM integration tests failing
```bash
# Solution: Check API keys and configuration
python -c "import os; print('OPENAI_API_KEY' in os.environ)"

# Use mock mode for development
python test_runner.py --level agents  # Without --real-llm

# Test with real LLM (use sparingly due to cost)
python test_runner.py --level agents --real-llm --llm-model gemini-2.5-flash
```

### Debug Commands
```bash
# Verbose output for debugging
python test_runner.py --level unit --verbose

# Run specific test file
pytest app/tests/specific_test.py -v

# Run with debugging
pytest app/tests/specific_test.py -v -s --pdb

# Show failing test details
python test_runner.py --show-failing
```

### Log Analysis
```bash
# Check test logs
tail -f logs/test_runner.log

# Check application logs during tests
tail -f logs/app.log

# Check for error patterns
grep -r "ERROR" logs/
```

---

## CI/CD Integration

### GitHub Actions Integration
```yaml
# Example workflow configuration
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Tests  
        run: |
          python test_runner.py --level integration --ci --output results.json
```

### Speed Optimizations for CI
```bash
# CI-optimized testing (safe optimizations)
python test_runner.py --level unit --ci

# Maximum speed (with warnings)
python test_runner.py --level unit --speed

# Parallel execution
python test_runner.py --level unit --parallel 4
```

### Output Formats
```bash
# JSON output for CI systems
python test_runner.py --level unit --output results.json --report-format json

# Markdown reports
python test_runner.py --level unit --output report.md --report-format markdown

# XML coverage for CI
python test_runner.py --level unit --coverage-output coverage.xml
```

### Shard Support for Parallel CI
```bash
# Run specific test shards in parallel CI jobs
python test_runner.py --level unit --shard core
python test_runner.py --level unit --shard agents  
python test_runner.py --level unit --shard websocket
python test_runner.py --level unit --shard database
python test_runner.py --level unit --shard api
python test_runner.py --level unit --shard frontend
```

---

## Real LLM Testing

### Why Real LLM Testing is Critical
- **Integration Validation**: Ensures LLM integrations work in production
- **Prompt Testing**: Validates prompt effectiveness  
- **Response Handling**: Tests real response parsing
- **Error Handling**: Validates error scenarios with real APIs
- **Performance**: Tests actual response times

### Real LLM Commands
```bash
# MANDATORY before releases - Integration tests with real LLM
python test_runner.py --level integration --real-llm

# Agent testing with real LLM (MANDATORY after agent changes)  
python test_runner.py --level agents --real-llm

# Full E2E with real services
python test_runner.py --level real_e2e --real-llm --llm-timeout 60

# Specific model testing
python test_runner.py --level integration --real-llm --llm-model gemini-2.5-flash
python test_runner.py --level integration --real-llm --llm-model gemini-2.5-pro  
```

### Cost Management
```bash
# Use cost-effective model for testing
python test_runner.py --level agents --real-llm --llm-model gemini-2.5-flash

# Sequential execution to avoid rate limits
python test_runner.py --level agents --real-llm --parallel 1

# Limit timeout to control costs  
python test_runner.py --level agents --real-llm --llm-timeout 30
```

### Environment Variables
```bash
# Required for real LLM testing
export TEST_USE_REAL_LLM=true
export ENABLE_REAL_LLM_TESTING=true

# API keys (required)
export OPENAI_API_KEY=your_key
export GOOGLE_API_KEY=your_key  
export ANTHROPIC_API_KEY=your_key
```

---

## Performance Testing

### Performance Test Categories
1. **Response Time Validation**: API endpoints meet SLA (<500ms)
2. **Load Testing**: System handles expected concurrent users  
3. **Memory Usage**: Memory consumption within limits
4. **Database Performance**: Query performance optimization
5. **Agent Performance**: AI agent response times

### Performance Commands
```bash
# Run performance test suite
python test_runner.py --level performance

# Specific performance categories
pytest app/tests/performance/ -m performance -v

# Load testing
pytest app/tests/performance/test_load.py -v

# Memory profiling
pytest app/tests/performance/test_memory.py -v --profile-memory
```

### Performance SLA Requirements
- **API Response Time**: <500ms (95th percentile)
- **Agent Response Time**: <2000ms (95th percentile)  
- **Database Query Time**: <100ms (95th percentile)
- **WebSocket Message Latency**: <50ms
- **Memory Usage**: <2GB per service

### Performance Monitoring
```bash
# Performance metrics collection
python test_runner.py --level performance --collect-metrics

# Generate performance report  
python scripts/generate_performance_report.py

# Continuous performance monitoring
python scripts/performance_monitor.py --continuous
```

---

## Operational Runbook

### Daily Operations

#### Morning Checklist
```bash
# Check test health
python test_runner.py --show-failing

# Quick smoke test
python test_runner.py --level smoke

# Check feature flag status
python -c "from test_framework.feature_flags import get_feature_flag_manager; print(get_feature_flag_manager().get_feature_summary())"
```

#### Before Each Release
```bash
# MANDATORY release checklist
python test_runner.py --level integration --real-llm
python test_runner.py --level performance
python test_runner.py --level comprehensive --real-llm  # For major releases
```

### Weekly Maintenance
```bash
# Clean up test artifacts
python scripts/cleanup_test_artifacts.py

# Update test dependencies
pip install -r requirements-test.txt --upgrade

# Performance trend analysis
python scripts/analyze_performance_trends.py
```

### Monthly Health Check
```bash
# Comprehensive health check
python scripts/test_health_check.py

# Coverage trend analysis
python scripts/analyze_coverage_trends.py

# Test performance optimization  
python scripts/optimize_test_performance.py
```

### Emergency Procedures

#### When Tests Are Failing
```bash
# 1. Check current failing tests
python test_runner.py --show-failing

# 2. Run only failing tests for faster feedback
python test_runner.py --run-failing

# 3. Clear failing tests log after fixes
python test_runner.py --clear-failing
```

#### When Tests Are Slow
```bash
# 1. Use speed optimizations
python test_runner.py --level unit --ci --fast-fail

# 2. Profile slow tests
pytest --durations=10

# 3. Run specific components only
python test_runner.py --level unit --shard core
```

#### Production Issues
```bash
# Quick validation after production fixes
python test_runner.py --level critical

# Full validation for hotfixes  
python test_runner.py --level integration --real-llm --fast-fail
```

---

## Advanced Features

### Staging Environment Testing
```bash
# Test against staging environment
python test_runner.py --level integration --staging

# Override staging URLs
python test_runner.py --staging --staging-url https://staging.netra.ai --staging-api-url https://api.staging.netra.ai
```

### Test Data Management
```bash
# Reset test data
python scripts/reset_test_data.py

# Generate synthetic test data
python scripts/generate_test_data.py --scenario user_journeys

# Backup test data
python scripts/backup_test_data.py
```

### Custom Test Configurations
```bash
# Create custom test configuration
python scripts/create_test_config.py --name custom_config

# Run with custom configuration  
python test_runner.py --config custom_config
```

---

## Conclusion

This test documentation ensures the Netra AI Platform maintains the highest quality standards while supporting business objectives. The test architecture is designed to:

1. **Protect Revenue**: Prevent production issues that could lose customers
2. **Enable Fast Development**: Quick feedback loops for developers
3. **Ensure Reliability**: Comprehensive validation before releases  
4. **Support Growth**: Scalable test architecture for future expansion
5. **Maintain Quality**: Continuous monitoring and improvement

### Key Success Metrics
- **Test Pass Rate**: >95% (Target)
- **Coverage**: >70% (Enforced), >85% for critical components  
- **Performance**: All tests meet SLA requirements
- **Developer Experience**: Fast feedback (<5 minutes for integration tests)
- **Production Reliability**: <0.1% incident rate from test-covered code

### Remember
- **Use the single test runner**: `test_runner.py` is the only approved method
- **Follow the 300/8 rule**: ≤300 lines per file, ≤8 lines per function
- **Test with real LLMs before releases**: Use `--real-llm` for production confidence
- **Maintain business value focus**: Every test should protect or enhance revenue

For questions or issues, refer to the troubleshooting guide or contact the development team.

---
*Generated by AGENT 20 - Documentation and Final Validation*
*Last Updated: 2025-08-19*