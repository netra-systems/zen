# Test Architecture Documentation

## Overview
The Netra Apex test suite has been consolidated from 4,133+ files with 61,872+ functions 
into a streamlined, comprehensive architecture with zero duplication.

## Consolidated Test Structure

### Service-Specific Tests
- `auth_service/tests/test_auth_comprehensive.py` - Complete auth service testing
- `netra_backend/tests/core/test_core_comprehensive.py` - Core backend functionality  
- `netra_backend/tests/agents/test_agents_comprehensive.py` - Agent system testing

### Test Categories
1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Service interaction testing  
3. **E2E Tests**: Complete workflow testing
4. **Performance Tests**: Load and performance validation

### Key Principles
- **SSOT Compliance**: Each concept tested once and only once
- **Environment Awareness**: Tests marked for dev/staging/prod
- **Real Over Mock**: Prefer real services over mocks where possible
- **Fast Feedback**: Optimized for developer productivity

## Test Execution
- Default: `python unified_test_runner.py --category integration --no-coverage --fast-fail`
- Full Suite: `python unified_test_runner.py --categories smoke unit integration api`
- Environment-Specific: `python unified_test_runner.py --env staging`
