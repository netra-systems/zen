# IMPROVEMENT: Test-Production Alignment for Async/Await Patterns

## Quality Assurance Enhancement - P1 HIGH

**Parent Issue**: #1184 - WebSocket Manager await error
**Business Impact**: Prevent future production-test misalignment issues
**Timeline**: 1 week

## Problem Summary

Tests validate WebSocket async/await fixes that pass in test environments but fail in production. This represents a critical gap in test coverage that allows production issues to slip through validation.

**Evidence of Misalignment**:
- Tests report 5/5 passing for async/await patterns
- Production logs show ongoing `can't be used in 'await' expression` errors
- Test environments may not reflect production async behavior
- Code scanning misses dynamic import patterns

## Root Cause Analysis

### Test Environment Differences
- [ ] Test async context differs from production runtime
- [ ] Mock implementations masking real async/await behavior
- [ ] Test fixtures not reflecting production usage patterns
- [ ] Docker/Cloud Run environment differences

### Test Coverage Gaps
- [ ] Static analysis missing dynamic async patterns
- [ ] Integration tests not covering all async/await scenarios
- [ ] End-to-end tests not validating real WebSocket behavior
- [ ] Production-like load conditions not tested

## Implementation Strategy

### Phase 1: Gap Analysis
- [ ] Compare test environment async runtime with production
- [ ] Identify specific test cases that should have caught the issue
- [ ] Document differences in async/await behavior between environments
- [ ] Map production error patterns to missing test coverage

### Phase 2: Test Environment Alignment
- [ ] Configure test environments to match production async behavior
- [ ] Remove mocks that mask async/await pattern issues
- [ ] Add real WebSocket connection testing
- [ ] Implement production-like async concurrency in tests

### Phase 3: Enhanced Test Coverage
- [ ] Add specific tests for async/await pattern violations
- [ ] Create integration tests using real WebSocket managers
- [ ] Implement automated static analysis for async pattern compliance
- [ ] Add regression tests for the specific #1184 error pattern

### Phase 4: Continuous Validation
- [ ] Implement pre-deployment async pattern validation
- [ ] Add production monitoring that feeds back to test requirements
- [ ] Create async/await pattern linting rules
- [ ] Establish test-production parity metrics

## Technical Requirements

### Real Environment Testing
- [ ] WebSocket tests use real manager implementations (no mocks)
- [ ] Async context matches Cloud Run production environment
- [ ] Database connections use real async patterns
- [ ] User context isolation tested with real factory patterns

### Static Analysis Enhancement
- [ ] Automated detection of `await non_awaitable_function()` patterns
- [ ] Custom linting rules for WebSocket async patterns
- [ ] Pre-commit hooks preventing async/await violations
- [ ] CI/CD integration for pattern validation

### Production Monitoring Integration
- [ ] Error patterns from production feed into test requirements
- [ ] Staging environment mirrors production async behavior
- [ ] Test failure alerts when production errors detected
- [ ] Feedback loop for continuous test improvement

## Specific Test Cases to Add

### Async Pattern Validation Tests
```python
def test_websocket_manager_sync_usage():
    """Ensure sync factory can't be awaited."""
    with pytest.raises(TypeError, match="can't be used in 'await' expression"):
        await get_websocket_manager(user_context=ctx)

def test_websocket_manager_async_usage():
    """Ensure async factory works correctly."""
    manager = await get_websocket_manager_async(user_context=ctx)
    assert manager is not None

def test_production_async_pattern_compliance():
    """Validate all production code follows correct async patterns."""
    # Static analysis test to catch violations
```

### Integration Test Enhancements
- [ ] Real WebSocket connection tests (no mocks)
- [ ] Multi-user concurrent async operations
- [ ] Error condition handling in async contexts
- [ ] Cloud Run environment simulation

## Acceptance Criteria

### Test Coverage
- [ ] 100% coverage of async/await patterns in WebSocket code
- [ ] Integration tests use real WebSocket managers (no mocks)
- [ ] Static analysis catches all async pattern violations
- [ ] Regression tests prevent #1184 recurrence

### Environment Alignment
- [ ] Test environment async behavior matches production
- [ ] Docker/Cloud Run differences eliminated in test setup
- [ ] Real service dependencies in async tests
- [ ] Production-like concurrency patterns tested

### Quality Gates
- [ ] Pre-deployment validation prevents async violations
- [ ] CI/CD fails on async pattern compliance issues
- [ ] Staging environment validates production patterns
- [ ] Continuous monitoring feeds test requirements

## Risk Assessment

**Low Risk**: Focused on test infrastructure improvement
**High Value**: Prevents entire class of production issues

### Benefits
- [ ] Catch similar issues before production
- [ ] Improve confidence in async/await pattern changes
- [ ] Reduce production debugging time
- [ ] Better alignment between development and production

## Related Issues

- Parent: #1184 (WebSocket Manager await error)
- Blocks: WebSocket Factory Simplification (safer to implement)
- Feeds: Documentation and Monitoring improvements
- See: Master Plan document `MASTER_PLAN_1184_20250116.md`

## Definition of Done

- [ ] Test environment async behavior matches production exactly
- [ ] All WebSocket async/await patterns covered by real tests
- [ ] Static analysis prevents async pattern violations
- [ ] Integration tests use real WebSocket connections
- [ ] Regression tests prevent #1184 recurrence
- [ ] Pre-deployment validation includes async pattern checks
- [ ] Production error monitoring feeds test requirement updates
- [ ] Documentation updated with new testing standards

**Labels**: `testing`, `priority:high`, `websocket`, `quality-assurance`, `async-patterns`