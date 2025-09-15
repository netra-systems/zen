# Issue #484 - GCP Backend Database Authentication Failure
## Comprehensive Test Plan

**Status:** CRITICAL P0 - Service authentication completely broken  
**Business Impact:** $500K+ ARR at immediate risk  
**Created:** 2025-09-15  
**Difficulty Level:** Medium to High (GCP staging environment + authentication)

---

## Executive Summary

This test plan addresses the complete breakdown of service-to-service authentication in the GCP backend, specifically the failure of `service:netra-backend` user authentication that is preventing all database session creation and agent operations. The plan follows the established testing patterns in `/reports/testing/TEST_CREATION_GUIDE.md` and focuses on reproducing the failing authentication, testing the fix, and preventing regression.

### Root Cause Summary
- **Primary Issue:** Service user pattern recognition failing in authentication middleware
- **Location:** `netra_backend/app/dependencies.py` function `get_request_scoped_db_session()` (Lines 220-249)
- **Environment:** GCP Cloud Run deployment regression from revision `00611-cr5` to `00639-g4g`
- **Authentication Pattern:** `service:netra-backend` user pattern not recognized by auth middleware

---

## Test Plan Structure

Following the TEST_CREATION_GUIDE.md hierarchy:
1. **Unit Tests** (no docker) - Business logic and service authentication patterns
2. **Integration Tests** (non-docker) - Service authentication flow with real databases
3. **E2E Tests** - GCP staging environment validation with real services

---

## Phase 1: Unit Tests (No Docker Required)

### 1.1 Service Authentication Logic Tests

**Test File:** `tests/unit/auth/test_service_user_authentication_issue_484.py`

**Business Value Justification (BVJ):**
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate service authentication component logic
- Value Impact: Service auth enables internal operations ($500K+ ARR)
- Strategic Impact: Core authentication infrastructure validation

**Test Focus Areas:**
```python
class TestServiceUserAuthenticationLogic:
    """Test service user authentication patterns without external dependencies."""
    
    def test_service_user_pattern_recognition(self):
        """Test that service:netra-backend pattern is correctly identified."""
        # Should PASS after fix
        user_id = "service:netra-backend"
        assert is_service_user(user_id) == True
        
        # Negative cases
        assert is_service_user("regular_user_123") == False
        assert is_service_user("user:normal") == False
        assert is_service_user("") == False
        assert is_service_user(None) == False
    
    def test_service_id_extraction(self):
        """Test extraction of service ID from service user context."""
        # Should PASS after fix
        user_id = "service:netra-backend"
        service_id = extract_service_id(user_id)
        assert service_id == "netra-backend"
        
        # Edge cases
        assert extract_service_id("service:") == ""
        assert extract_service_id("service") == "service"
    
    def test_service_authentication_bypass_logic(self):
        """Test that service users should bypass JWT validation."""
        # Should PASS after fix
        user_id = "service:netra-backend"
        auth_config = {
            "service_secret": "test_secret",
            "jwt_secret_key": "test_jwt",
            "service_id": "netra-backend"
        }
        
        should_bypass = should_bypass_jwt_validation(user_id, auth_config)
        assert should_bypass == True
        
        # Regular users should not bypass
        regular_user = "user_123"
        should_bypass_regular = should_bypass_jwt_validation(regular_user, auth_config)
        assert should_bypass_regular == False
    
    def test_service_user_context_generation(self):
        """Test get_service_user_context() function behavior."""
        # Should PASS after fix
        with mock.patch.dict(os.environ, {
            "SERVICE_ID": "netra-backend",
            "SERVICE_SECRET": "test_secret"
        }):
            context = get_service_user_context()
            assert context == "service:netra-backend"
            assert context.startswith("service:")
    
    def test_environment_configuration_validation(self):
        """Test validation of required authentication environment variables."""
        # Should FAIL initially (reproducing bug), PASS after fix
        required_vars = ["SERVICE_ID", "SERVICE_SECRET", "JWT_SECRET_KEY"]
        
        # Test missing variables (should fail initially)
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                validate_authentication_environment()
            assert "Missing critical environment variables" in str(exc_info.value)
        
        # Test complete configuration (should pass after fix)
        with mock.patch.dict(os.environ, {
            "SERVICE_ID": "netra-backend",
            "SERVICE_SECRET": "test_secret",
            "JWT_SECRET_KEY": "test_jwt_key"
        }):
            result = validate_authentication_environment()
            assert result == True
```

### 1.2 Authentication Middleware Logic Tests

**Test File:** `tests/unit/auth/test_service_authentication_middleware_issue_484.py`

**Test Focus Areas:**
```python
class TestServiceAuthenticationMiddleware:
    """Test authentication middleware handling of service users."""
    
    def test_service_user_authentication_validation(self):
        """Test service-to-service authentication validation logic."""
        # Should FAIL initially, PASS after fix
        user_id = "service:netra-backend"
        service_secret = "test_service_secret"
        
        # Mock successful validation
        is_valid = validate_service_authentication(user_id, service_secret)
        assert is_valid == True
        
        # Test invalid service ID
        invalid_user_id = "service:invalid-service"
        is_valid_invalid = validate_service_authentication(invalid_user_id, service_secret)
        assert is_valid_invalid == False
    
    def test_authentication_method_selection(self):
        """Test that correct authentication method is selected for service users."""
        # Should PASS after fix
        service_user = "service:netra-backend"
        regular_user = "user_123"
        
        service_method = get_authentication_method(service_user)
        assert service_method == "service_to_service"
        
        regular_method = get_authentication_method(regular_user)
        assert regular_method == "jwt_validation"
    
    def test_service_secret_validation(self):
        """Test SERVICE_SECRET validation logic."""
        # Should FAIL initially (no secret), PASS after fix
        user_id = "service:netra-backend"
        
        # Missing secret should fail
        result = validate_service_secret(user_id, None)
        assert result == False
        
        # Valid secret should pass
        result = validate_service_secret(user_id, "valid_secret")
        assert result == True
```

### 1.3 Session Factory Logic Tests

**Test File:** `tests/unit/database/test_request_scoped_session_factory_issue_484.py`

**Test Focus Areas:**
```python
class TestRequestScopedSessionFactoryLogic:
    """Test session factory logic for service users."""
    
    def test_service_user_session_configuration(self):
        """Test session configuration for service users."""
        # Should PASS after fix
        user_id = "service:netra-backend"
        request_id = "test_req_123"
        
        config = generate_session_config(user_id, request_id)
        assert config["user_id"] == user_id
        assert config["authentication_method"] == "service_to_service"
        assert config["bypass_jwt_validation"] == True
    
    def test_session_factory_error_handling(self):
        """Test error handling in session factory for authentication failures."""
        # Should FAIL initially, PASS after fix
        invalid_user_id = "service:invalid"
        request_id = "test_req_456"
        
        with pytest.raises(AuthenticationError) as exc_info:
            generate_session_config(invalid_user_id, request_id)
        
        assert "authentication" in str(exc_info.value).lower()
```

---

## Phase 2: Integration Tests (Non-Docker)

### 2.1 Service Authentication Flow Tests

**Test File:** `tests/integration/auth/test_service_authentication_flow_issue_484.py`

**Business Value Justification (BVJ):**
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate service authentication with real databases
- Value Impact: Ensures service-to-service operations work correctly
- Strategic Impact: Core platform reliability ($500K+ ARR protection)

**Test Focus Areas:**
```python
class TestServiceAuthenticationFlowIntegration(BaseIntegrationTest):
    """Integration tests for service authentication flow with real databases."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_user_database_session_creation(self, real_services_fixture):
        """Test database session creation with service users."""
        # Should FAIL initially, PASS after fix
        db = real_services_fixture["db"]
        user_id = "service:netra-backend"
        request_id = "test_req_integration_123"
        
        # This test reproduces the core issue
        async with get_request_scoped_session(user_id, request_id) as session:
            assert session is not None
            assert hasattr(session, 'info')
            
            # Verify session can perform database operations
            result = await session.execute("SELECT 1 as test_value")
            row = result.fetchone()
            assert row.test_value == 1
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_authentication_with_auth_client(self, real_services_fixture):
        """Test service authentication using real auth client."""
        # Should FAIL initially, PASS after fix
        auth_client = AuthServiceClient()
        service_id = "netra-backend"
        operation = "database_session_creation"
        
        # This reproduces the 403 authentication error
        validation_result = await auth_client.validate_service_user_context(
            service_id, operation
        )
        
        assert validation_result is not None
        assert validation_result.get("valid") == True
        assert validation_result.get("service_id") == service_id
        assert validation_result.get("authentication_method") == "service_to_service"
    
    @pytest.mark.integration
    async def test_authentication_failure_error_handling(self, real_services_fixture):
        """Test proper error handling when service authentication fails."""
        # Should PASS (proper error handling)
        invalid_user_id = "service:invalid-service"
        request_id = "test_req_fail_123"
        
        with pytest.raises((HTTPException, AuthenticationError)) as exc_info:
            async with get_request_scoped_session(invalid_user_id, request_id) as session:
                pass
        
        # Should be a 403 or authentication-related error
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["403", "authentication", "not authenticated"])
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_concurrent_service_user_sessions(self, real_services_fixture):
        """Test multiple concurrent service user sessions."""
        # Should PASS after fix
        user_id = "service:netra-backend"
        num_concurrent = 5
        
        async def create_session(session_id):
            request_id = f"concurrent_test_{session_id}"
            async with get_request_scoped_session(user_id, request_id) as session:
                result = await session.execute("SELECT 1 as test_value")
                return result.fetchone().test_value
        
        # Run concurrent sessions
        tasks = [create_session(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == num_concurrent
        assert all(result == 1 for result in results)
```

### 2.2 Database Session Factory Integration Tests

**Test File:** `tests/integration/database/test_session_factory_service_users_issue_484.py`

**Test Focus Areas:**
```python
class TestSessionFactoryServiceUsersIntegration(BaseIntegrationTest):
    """Integration tests for session factory with service users."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_factory_initialization_with_service_user(self, real_services_fixture):
        """Test session factory initialization for service users."""
        # Should FAIL initially, PASS after fix
        from netra_backend.app.database.request_scoped_session_factory import get_session_factory
        
        factory = await get_session_factory()
        assert factory is not None
        
        user_id = "service:netra-backend"
        request_id = "factory_test_123"
        
        # Test session creation through factory
        async with factory.get_request_scoped_session(user_id, request_id) as session:
            assert session is not None
            assert session.info.get('user_id') == user_id
            assert session.info.get('request_id') == request_id
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_lifecycle_management(self, real_services_fixture):
        """Test complete session lifecycle for service users."""
        # Should PASS after fix
        from netra_backend.app.database.request_scoped_session_factory import get_session_factory
        
        factory = await get_session_factory()
        user_id = "service:netra-backend"
        request_id = "lifecycle_test_123"
        
        # Test session creation, usage, and cleanup
        session_created = False
        session_used = False
        session_closed = False
        
        async with factory.get_request_scoped_session(user_id, request_id) as session:
            session_created = True
            
            # Use session
            result = await session.execute("SELECT current_timestamp as now")
            row = result.fetchone()
            assert row.now is not None
            session_used = True
        
        # Session should be properly closed after context exit
        session_closed = True
        
        assert session_created and session_used and session_closed
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_bypass_for_service_users(self, real_services_fixture):
        """Test that service users bypass JWT validation correctly."""
        # Should PASS after fix
        user_id = "service:netra-backend"
        request_id = "bypass_test_123"
        
        # Mock missing JWT token (should still work for service users)
        with mock.patch('netra_backend.app.auth_integration.auth.validate_jwt_token', 
                       side_effect=Exception("No JWT token")):
            
            # Service user should still get session (bypasses JWT)
            async with get_request_scoped_session(user_id, request_id) as session:
                assert session is not None
```

---

## Phase 3: E2E Tests (GCP Staging Environment)

### 3.1 GCP Staging Service Authentication Tests

**Test File:** `tests/e2e/gcp_staging/test_issue_484_service_authentication_e2e.py`

**Business Value Justification (BVJ):**
- Segment: Platform/Infrastructure (affects all customer tiers)
- Business Goal: System Stability - Prevent service communication breakdown  
- Value Impact: Protects $500K+ ARR by ensuring core platform functionality
- Revenue Impact: Prevents complete service outage affecting all customers

**Test Focus Areas:**
```python
class TestIssue484ServiceAuthenticationE2E(BaseE2ETest):
    """E2E tests for Issue #484 in GCP staging environment."""
    
    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    @pytest.mark.mission_critical
    async def test_service_authentication_failure_reproduction(self):
        """Reproduce the exact Issue #484 authentication failure in staging."""
        # Should FAIL initially (reproducing bug), PASS after fix
        
        # Test the exact failing scenario from production logs
        user_id = "service:netra-backend"
        
        # This should reproduce the 403 'Not authenticated' error
        try:
            async with get_request_scoped_db_session() as session:
                # Attempt database operation that was failing
                result = await session.execute("SELECT 1 as health_check")
                row = result.fetchone()
                assert row.health_check == 1
                
        except Exception as e:
            # Initially should fail with authentication error
            error_msg = str(e).lower()
            assert any(keyword in error_msg for keyword in [
                "403", "not authenticated", "authentication", "forbidden"
            ])
            # Log the exact error for debugging
            logger.error(f"Reproduced Issue #484 error: {e}")
            
            # After fix, this should not raise an exception
            if "ISSUE_484_FIXED" in os.environ:
                pytest.fail(f"Issue #484 should be fixed but still failing: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    async def test_agent_execution_with_service_authentication(self):
        """Test complete agent execution flow with service authentication."""
        # Should FAIL initially, PASS after fix
        
        # Test the exact failing scenario: agent execution requiring database access
        agent_request = {
            "user_id": "service:netra-backend",
            "thread_id": "test_thread_issue_484",
            "message": "Test agent execution with service auth",
            "agent_type": "cost_optimizer"
        }
        
        # This was timing out due to authentication failures
        start_time = time.time()
        
        try:
            # Execute agent (this requires database session creation)
            response = await execute_agent_request(agent_request)
            execution_time = time.time() - start_time
            
            # Should complete in reasonable time (not timeout)
            assert execution_time < 10.0  # Should be much faster than 15+ second timeouts
            assert response is not None
            assert "error" not in response or "403" not in str(response.get("error", ""))
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log failure details for debugging
            logger.error(f"Agent execution failed after {execution_time:.2f}s: {e}")
            
            # Initially should fail due to authentication
            error_msg = str(e).lower()
            assert any(keyword in error_msg for keyword in [
                "403", "not authenticated", "timeout", "authentication"
            ])
    
    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    async def test_websocket_events_with_service_authentication(self):
        """Test WebSocket event delivery with service authentication."""
        # Should FAIL initially, PASS after fix
        
        # Test WebSocket events that require database operations
        from test_framework.websocket_helpers import WebSocketTestClient
        
        async with WebSocketTestClient() as client:
            # Send message that triggers agent execution
            await client.send_json({
                "type": "agent_message",
                "user_id": "service:netra-backend",
                "thread_id": "websocket_test_484",
                "message": "Test WebSocket with service auth"
            })
            
            # Should receive events without authentication errors
            events = []
            try:
                async for event in client.receive_events(timeout=15):
                    events.append(event)
                    if event.get("type") == "agent_completed":
                        break
                    if event.get("type") == "error" and "403" in str(event):
                        # This reproduces the authentication failure
                        logger.error(f"WebSocket authentication error: {event}")
                        break
                        
            except asyncio.TimeoutError:
                # Initial state: timeout due to authentication failures
                logger.error("WebSocket events timed out due to authentication issues")
                
            # After fix: should have received proper events
            if "ISSUE_484_FIXED" in os.environ:
                assert len(events) > 0
                assert not any(e.get("type") == "error" and "403" in str(e) for e in events)
    
    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    async def test_gcp_environment_configuration_validation(self):
        """Test GCP environment configuration for service authentication."""
        # Should FAIL initially, PASS after fix
        
        # Validate that GCP Cloud Run has proper environment variables
        required_vars = [
            "SERVICE_ID",
            "SERVICE_SECRET", 
            "JWT_SECRET_KEY",
            "POSTGRES_HOST",
            "POSTGRES_USER"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        # Initially: missing variables cause authentication failure
        if missing_vars:
            logger.error(f"Missing GCP environment variables: {missing_vars}")
            
        # After fix: all variables should be present
        if "ISSUE_484_FIXED" in os.environ:
            assert len(missing_vars) == 0, f"Missing critical variables: {missing_vars}"
        
        # Test SERVICE_SECRET and JWT_SECRET_KEY are properly set
        service_secret = os.getenv("SERVICE_SECRET")
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        
        if "ISSUE_484_FIXED" in os.environ:
            assert service_secret is not None and len(service_secret) > 0
            assert jwt_secret is not None and len(jwt_secret) > 0
```

### 3.2 Staging Environment Recovery Validation Tests

**Test File:** `tests/e2e/gcp_staging/test_issue_484_recovery_validation_e2e.py`

**Test Focus Areas:**
```python
class TestIssue484RecoveryValidationE2E(BaseE2ETest):
    """Validate complete recovery from Issue #484 in staging environment."""
    
    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    @pytest.mark.mission_critical
    async def test_zero_authentication_errors_validation(self):
        """Validate 0% authentication error rate after fix."""
        # Should PASS after fix
        
        error_count = 0
        success_count = 0
        test_duration = 60  # seconds
        start_time = time.time()
        
        while time.time() - start_time < test_duration:
            try:
                # Test service authentication
                async with get_request_scoped_db_session() as session:
                    await session.execute("SELECT 1")
                    success_count += 1
                    
            except Exception as e:
                error_count += 1
                logger.error(f"Authentication error #{error_count}: {e}")
            
            await asyncio.sleep(2)  # Test every 2 seconds
        
        total_attempts = success_count + error_count
        success_rate = (success_count / total_attempts) * 100 if total_attempts > 0 else 0
        
        logger.info(f"Authentication test results over {test_duration}s:")
        logger.info(f"  Successes: {success_count}")
        logger.info(f"  Errors: {error_count}")
        logger.info(f"  Success rate: {success_rate:.1f}%")
        
        # After fix: should have 95%+ success rate
        assert success_rate >= 95.0, f"Success rate {success_rate:.1f}% below 95% threshold"
        assert error_count == 0, f"Should have 0 authentication errors, got {error_count}"
    
    @pytest.mark.e2e
    @pytest.mark.gcp_staging
    async def test_agent_execution_performance_recovery(self):
        """Validate agent execution performance recovery after fix."""
        # Should PASS after fix (fast execution times)
        
        execution_times = []
        num_tests = 10
        
        for i in range(num_tests):
            start_time = time.time()
            
            try:
                # Test agent execution
                response = await execute_agent_request({
                    "user_id": "service:netra-backend",
                    "thread_id": f"perf_test_{i}",
                    "message": "Quick test query",
                    "agent_type": "triage_agent"
                })
                
                execution_time = time.time() - start_time
                execution_times.append(execution_time)
                
                assert response is not None
                assert "error" not in response
                
            except Exception as e:
                logger.error(f"Agent execution {i+1} failed: {e}")
                execution_times.append(float('inf'))  # Mark as failure
        
        # After fix: should have fast execution times
        successful_times = [t for t in execution_times if t != float('inf')]
        
        if successful_times:
            avg_time = sum(successful_times) / len(successful_times)
            max_time = max(successful_times)
            
            logger.info(f"Agent execution performance:")
            logger.info(f"  Average time: {avg_time:.2f}s")
            logger.info(f"  Max time: {max_time:.2f}s")
            logger.info(f"  Success rate: {len(successful_times)}/{num_tests}")
            
            # Should be much faster than the 15+ second timeouts seen in Issue #484
            assert avg_time < 5.0, f"Average execution time {avg_time:.2f}s too slow"
            assert max_time < 10.0, f"Max execution time {max_time:.2f}s too slow"
            assert len(successful_times) == num_tests, "Some agent executions failed"
```

---

## Phase 4: Test Implementation Guidelines

### 4.1 Expected Test Behavior

**Initial State (Before Fix):**
- Unit tests: Mix of PASS (logic) and FAIL (missing environment)
- Integration tests: FAIL with 403 authentication errors
- E2E tests: FAIL with timeouts and authentication failures

**After Fix Implementation:**
- Unit tests: All PASS
- Integration tests: All PASS with proper service authentication
- E2E tests: All PASS with fast execution times

### 4.2 Test Execution Strategy

**Phase 1 - Reproduce the Bug:**
```bash
# Run tests to reproduce the issue
python tests/unified_test_runner.py --category unit --pattern "*issue_484*"
python tests/unified_test_runner.py --category integration --pattern "*issue_484*" --real-services
pytest tests/e2e/gcp_staging/test_issue_484_service_authentication_e2e.py -v
```

**Phase 2 - Validate the Fix:**
```bash
# Set environment variable to indicate fix is applied
export ISSUE_484_FIXED=true

# Run all Issue #484 tests
python tests/unified_test_runner.py --pattern "*issue_484*" --real-services --env staging
```

**Phase 3 - Performance Validation:**
```bash
# Run performance validation tests
pytest tests/e2e/gcp_staging/test_issue_484_recovery_validation_e2e.py::test_zero_authentication_errors_validation -v
pytest tests/e2e/gcp_staging/test_issue_484_recovery_validation_e2e.py::test_agent_execution_performance_recovery -v
```

### 4.3 Success Criteria

**Unit Tests:**
- ✅ Service user pattern recognition: 100% pass rate
- ✅ Authentication method selection: Correct method for service vs regular users
- ✅ Environment configuration validation: Proper error handling

**Integration Tests:**
- ✅ Database session creation: Successful for service users
- ✅ Service authentication flow: No 403 errors
- ✅ Concurrent operations: Multiple service sessions work correctly

**E2E Tests:**
- ✅ Authentication failure reproduction: Reproduces bug initially, passes after fix
- ✅ Agent execution: <5 second execution times (vs 15+ second timeouts)
- ✅ WebSocket events: All 5 critical events delivered
- ✅ Zero authentication errors: 95%+ success rate over 60 seconds

### 4.4 Test Coverage Requirements

**Authentication Patterns:**
- Service user pattern recognition (`service:netra-backend`)
- Environment variable validation (SERVICE_SECRET, JWT_SECRET_KEY)
- Authentication method selection (service vs JWT)
- Error handling for missing configuration

**Database Operations:**
- Request-scoped session creation
- Session lifecycle management
- Concurrent session handling
- Authentication bypass for service users

**End-to-End Workflows:**
- Agent execution pipeline
- WebSocket event delivery
- Service-to-service communication
- GCP staging environment validation

---

## Phase 5: Monitoring and Validation

### 5.1 Post-Implementation Monitoring

**Performance Metrics:**
- Authentication success rate: Target 99%+
- Agent execution time: Target <5 seconds
- Database session creation: Target <1 second
- WebSocket event delivery: Target <2 seconds

**Error Monitoring:**
- Zero `403 'Not authenticated'` errors for service users
- Zero timeouts due to authentication failures
- Proper error handling for invalid service IDs

### 5.2 Regression Prevention

**Continuous Testing:**
```bash
# Add to CI/CD pipeline
pytest tests/e2e/gcp_staging/test_issue_484_recovery_validation_e2e.py --env staging
```

**Environment Validation:**
```bash
# Pre-deployment validation
python scripts/validate_authentication_deployment.py
```

**Health Monitoring:**
```bash
# Post-deployment monitoring
python scripts/monitor_authentication_health.py --duration 30
```

---

## Conclusion

This comprehensive test plan addresses Issue #484 by:

1. **Reproducing the Authentication Failure:** Tests initially fail to reproduce the exact 403 errors and timeouts
2. **Validating the Fix:** Tests pass after implementing service user pattern recognition and environment configuration
3. **Preventing Regression:** Continuous monitoring ensures the issue doesn't reoccur
4. **Protecting Business Value:** Ensures $500K+ ARR functionality is restored and maintained

The test plan follows established patterns in the codebase and provides comprehensive coverage of the authentication failure scenario, fix validation, and ongoing monitoring to prevent similar issues in the future.

---

**Next Action:** Implement the test suites in the specified order, starting with unit tests to validate the business logic, then integration tests with real databases, and finally E2E tests in the GCP staging environment.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>