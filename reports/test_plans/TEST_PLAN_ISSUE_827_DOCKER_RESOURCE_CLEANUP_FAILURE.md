# Test Plan: Issue #827 Docker Resource Cleanup Failure

## Executive Summary

**Issue:** Windows Docker Desktop named pipe communication failure during test teardown  
**Error Pattern:** `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`  
**Business Impact:** Test infrastructure instability affects development velocity and CI/CD reliability  
**Risk Level:** MEDIUM - Infrastructure issue that degrades developer experience but doesn't affect production

## Test Strategy Overview

### 1. Test Structure: Unit Tests (NO DOCKER REQUIRED)

Following `reports/testing/TEST_CREATION_GUIDE.md` and CLAUDE.md requirements, all tests will be unit tests using mocks to simulate the Windows Docker Desktop pipe failure without requiring actual Docker containers.

### 2. Test Focus Areas

1. **UnifiedDockerManager.graceful_shutdown()** method behavior under pipe failure scenarios
2. **Subprocess communication** error handling and recovery
3. **Resource cleanup validation** when Docker daemon becomes unavailable
4. **Fallback mechanism** testing for force_shutdown() invocation
5. **Error logging and warning** message accuracy

### 3. Mock Strategy

- Mock `_run_subprocess_safe()` to simulate Windows pipe communication failures
- Mock `subprocess.run()` to return specific error patterns from Issue #827
- Mock Docker command execution to test graceful degradation
- Use real exception types but simulated failure scenarios

## Detailed Test Cases

### Test Suite 1: Graceful Shutdown Pipe Communication Failures

**File:** `test_framework/tests/unit/test_unified_docker_manager_graceful_shutdown.py`

#### Test Case 1.1: Named Pipe Communication Failure
```python
async def test_graceful_shutdown_windows_pipe_failure(self):
    """
    Test graceful shutdown handles Windows Docker Desktop pipe failure.
    
    Reproduces: error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/containers/json?all=1": 
    open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
    """
    # Mock subprocess to simulate exact Windows pipe failure
    with patch('test_framework.unified_docker_manager._run_subprocess_safe') as mock_subprocess:
        mock_subprocess.return_value = Mock(
            returncode=1,
            stderr="error during connect: Get \"http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/containers/json?all=1\": open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified."
        )
        
        manager = UnifiedDockerManager()
        
        # Should gracefully handle pipe failure and attempt force shutdown
        with patch.object(manager, 'force_shutdown', return_value=True) as mock_force:
            result = await manager.graceful_shutdown()
            
            # Verify graceful shutdown failed and force shutdown was attempted
            mock_force.assert_called_once()
            assert result is True  # force_shutdown should succeed
```

#### Test Case 1.2: Docker Daemon Unavailable
```python
async def test_graceful_shutdown_daemon_unavailable(self):
    """Test graceful shutdown when Docker daemon is completely unavailable."""
    with patch('test_framework.unified_docker_manager._run_subprocess_safe') as mock_subprocess:
        mock_subprocess.side_effect = FileNotFoundError("Docker daemon not running")
        
        manager = UnifiedDockerManager()
        
        # Should handle daemon unavailability gracefully
        result = await manager.graceful_shutdown()
        assert result is False  # Should return False when completely failed
```

#### Test Case 1.3: Timeout During Shutdown
```python
async def test_graceful_shutdown_timeout_triggers_force(self):
    """Test that subprocess timeout triggers force shutdown."""
    import subprocess
    
    with patch('test_framework.unified_docker_manager._run_subprocess_safe') as mock_subprocess:
        mock_subprocess.side_effect = subprocess.TimeoutExpired(cmd=["docker-compose", "down"], timeout=30)
        
        manager = UnifiedDockerManager()
        
        with patch.object(manager, 'force_shutdown', return_value=True) as mock_force:
            result = await manager.graceful_shutdown(timeout=30)
            
            # Should trigger force shutdown after timeout
            mock_force.assert_called_once()
            assert result is True
```

### Test Suite 2: Resource Cleanup Validation

**File:** `test_framework/tests/unit/test_unified_docker_manager_cleanup_validation.py`

#### Test Case 2.1: Cleanup State Tracking
```python
def test_cleanup_state_tracking_after_pipe_failure(self):
    """Test that cleanup state is properly tracked after pipe failures."""
    manager = UnifiedDockerManager()
    
    with patch('test_framework.unified_docker_manager._run_subprocess_safe') as mock_subprocess:
        mock_subprocess.return_value = Mock(
            returncode=1,
            stderr="open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified."
        )
        
        # Track cleanup attempts
        with patch.object(manager, 'force_shutdown', return_value=True):
            result = await manager.graceful_shutdown(services=["test-service"])
            
            # Verify cleanup was attempted for specific services
            mock_subprocess.assert_called_once()
            called_cmd = mock_subprocess.call_args[0][0]
            assert "test-service" in called_cmd
```

#### Test Case 2.2: Service-Specific Cleanup
```python
def test_service_specific_cleanup_pipe_failure(self):
    """Test cleanup behavior for specific services during pipe failure."""
    manager = UnifiedDockerManager()
    
    with patch('test_framework.unified_docker_manager._run_subprocess_safe') as mock_subprocess:
        mock_subprocess.return_value = Mock(
            returncode=1,
            stderr="The system cannot find the file specified."
        )
        
        # Test cleanup of specific services
        services = ["backend", "redis"]
        
        with patch.object(manager, 'force_shutdown', return_value=True) as mock_force:
            result = await manager.graceful_shutdown(services=services)
            
            # Should attempt graceful shutdown of specific services first
            mock_subprocess.assert_called_once()
            called_cmd = mock_subprocess.call_args[0][0]
            assert "stop" in called_cmd  # Uses stop for specific services
            assert all(service in called_cmd for service in services)
            
            # Then fallback to force shutdown
            mock_force.assert_called_once_with(services)
```

### Test Suite 3: Error Logging and Warning Messages

**File:** `test_framework/tests/unit/test_unified_docker_manager_error_messaging.py`

#### Test Case 3.1: Warning Message Accuracy
```python
def test_warning_message_contains_stderr(self, caplog):
    """Test that warning messages contain the actual stderr from subprocess."""
    manager = UnifiedDockerManager()
    expected_stderr = "open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified."
    
    with patch('test_framework.unified_docker_manager._run_subprocess_safe') as mock_subprocess:
        mock_subprocess.return_value = Mock(
            returncode=1,
            stderr=expected_stderr
        )
        
        with patch.object(manager, 'force_shutdown', return_value=True):
            result = await manager.graceful_shutdown()
        
        # Verify warning message contains stderr
        warning_records = [record for record in caplog.records if record.levelname == 'WARNING']
        assert len(warning_records) > 0
        
        warning_message = warning_records[0].message
        assert "Graceful shutdown had issues" in warning_message
        assert expected_stderr in warning_message
```

#### Test Case 3.2: Error Level Classification
```python
def test_error_level_classification_pipe_failure(self, caplog):
    """Test that pipe failures are classified at appropriate log levels."""
    manager = UnifiedDockerManager()
    
    with patch('test_framework.unified_docker_manager._run_subprocess_safe') as mock_subprocess:
        # Test different failure scenarios
        scenarios = [
            (1, "pipe communication failure", "WARNING"),
            (126, "permission denied", "ERROR"),  
            (127, "command not found", "ERROR")
        ]
        
        for returncode, stderr, expected_level in scenarios:
            caplog.clear()
            mock_subprocess.return_value = Mock(returncode=returncode, stderr=stderr)
            
            with patch.object(manager, 'force_shutdown', return_value=True):
                result = await manager.graceful_shutdown()
            
            # Check log level classification
            relevant_records = [record for record in caplog.records 
                              if expected_level.lower() in record.levelname.lower()]
            assert len(relevant_records) > 0, f"Expected {expected_level} log for {stderr}"
```

### Test Suite 4: Graceful Degradation Testing

**File:** `test_framework/tests/unit/test_unified_docker_manager_degradation.py`

#### Test Case 4.1: Fallback Chain Execution
```python
async def test_complete_fallback_chain(self):
    """Test complete fallback chain: graceful -> force -> cleanup."""
    manager = UnifiedDockerManager()
    
    # Track method call sequence
    call_sequence = []
    
    def track_graceful(*args, **kwargs):
        call_sequence.append("graceful_attempted")
        raise Exception("Graceful failed")
    
    def track_force(*args, **kwargs):
        call_sequence.append("force_attempted")
        return True
    
    with patch.object(manager, 'graceful_shutdown', side_effect=track_graceful):
        with patch.object(manager, 'force_shutdown', side_effect=track_force):
            # Trigger the fallback chain
            try:
                result = await manager.graceful_shutdown()
            except Exception:
                # Expected graceful to fail, force should be called
                pass
    
    # Verify fallback sequence
    assert "graceful_attempted" in call_sequence
    # Note: In actual implementation, need to verify force_shutdown is called from graceful_shutdown
```

#### Test Case 4.2: Resource State Consistency
```python
def test_resource_state_consistency_after_failures(self):
    """Test that resource state remains consistent after various failure modes."""
    manager = UnifiedDockerManager()
    
    # Test scenarios that should maintain consistency
    failure_scenarios = [
        "pipe communication failure",
        "timeout during shutdown", 
        "docker daemon unavailable",
        "permission denied"
    ]
    
    for scenario in failure_scenarios:
        with patch('test_framework.unified_docker_manager._run_subprocess_safe') as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=1, stderr=scenario)
            
            with patch.object(manager, 'force_shutdown', return_value=True):
                result = await manager.graceful_shutdown()
            
            # Verify manager state remains consistent
            assert hasattr(manager, '_project_name')
            assert hasattr(manager, '_compose_file')
            # Manager should not be in broken state
            assert result in [True, False]  # Should return valid boolean
```

## Test Execution Strategy

### Phase 1: Initial Failing Tests (TDD Approach)
1. Create all test files with failing tests that reproduce the exact error scenarios
2. Tests should initially fail to demonstrate they detect the issue
3. Focus on the exact error message from Issue #827

### Phase 2: Implementation Verification
1. After any fixes to UnifiedDockerManager, tests should pass
2. Verify graceful degradation works as expected
3. Ensure error messages are informative and actionable

### Phase 3: Integration Validation
1. Run tests with `python tests/unified_test_runner.py --category unit`
2. Verify tests work in CI/CD environment (especially Windows)
3. Confirm tests catch regressions in future changes

## Test File Organization

```
test_framework/tests/unit/docker_cleanup/
├── test_unified_docker_manager_graceful_shutdown.py    # Core shutdown behavior
├── test_unified_docker_manager_cleanup_validation.py   # Resource cleanup tracking
├── test_unified_docker_manager_error_messaging.py      # Logging and error handling  
├── test_unified_docker_manager_degradation.py          # Fallback mechanisms
└── __init__.py                                         # Test suite marker
```

## Success Criteria

### Immediate Success (Phase 1)
- [ ] All tests initially FAIL, demonstrating they detect the pipe communication issue
- [ ] Tests reproduce the exact error message from Issue #827
- [ ] Test suite runs without requiring Docker containers (unit tests only)
- [ ] Proper mocking isolates the subprocess communication failure

### Long-term Success (Post-fix)
- [ ] Tests PASS after UnifiedDockerManager improvements
- [ ] Graceful degradation properly handles Windows pipe failures
- [ ] Force shutdown is invoked when graceful shutdown fails
- [ ] Error messages are informative and help developers understand the issue
- [ ] Resource cleanup state remains consistent across failure scenarios

## Business Value Justification

**Segment:** Platform Infrastructure (affects all customer segments indirectly)  
**Business Goal:** Development Infrastructure Stability and Reliability  
**Value Impact:** Improved developer experience and CI/CD reliability reduces deployment friction  
**Strategic Impact:** Stable testing infrastructure enables faster feature delivery and higher confidence deployments

## Implementation Notes

1. **Mock Strategy:** Use `unittest.mock.patch` to simulate Windows-specific failures without requiring Windows environment
2. **Error Reproduction:** Focus on exact error strings from Issue #827 to ensure tests catch the real problem  
3. **Graceful Degradation:** Verify that fallback mechanisms work correctly under pipe failure scenarios
4. **Resource Safety:** Ensure cleanup state remains consistent even when Docker communication fails

## Next Steps

1. Create test files with initially failing tests
2. Verify tests reproduce Issue #827 symptoms
3. Run test suite to confirm failure detection
4. Update Issue #827 with test plan implementation status
5. Provide test results to guide UnifiedDockerManager improvements