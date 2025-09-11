# Issue #245: Deployment Script Consolidation Test Plan
**CRITICAL INFRASTRUCTURE SAFETY VALIDATION**

> **Mission Critical:** Safely consolidate 7+ conflicting deployment scripts while protecting Golden Path functionality (users login → AI responses)
> 
> **Risk Level:** EXTREME - $500K+ ARR at risk from configuration drift
> 
> **Approach:** Safety-first testing with multiple validation layers

---

## Executive Summary

**PROBLEM:** 7+ conflicting deployment scripts with unclear canonical authority:
- `scripts/deploy_to_gcp.py` (DEPRECATED - redirects to UnifiedTestRunner)
- `scripts/deploy_to_gcp_actual.py` (OFFICIAL deployment script)
- `terraform-gcp-staging/deploy.sh` (Infrastructure layer - calls missing UnifiedTestRunner mode)
- `scripts/deploy-docker.sh` (Docker-based deployment)
- Multiple validation/configuration scripts

**SOLUTION:** Establish single canonical deployment source while maintaining all existing functionality through systematic testing and validation.

**TEST STRATEGY:** 5-phase validation ensuring no regressions:
1. Pre-consolidation validation (baseline current functionality)
2. Script-by-script functional testing
3. Configuration drift detection
4. Infrastructure integration testing  
5. Golden Path protection validation

---

## Phase 1: PRE-CONSOLIDATION VALIDATION TESTS
*Must pass BEFORE any changes - establishes known working baseline*

### 1.1. Current Deployment Method Validation

#### Test File: `test_plans/phase1/test_current_deployment_baseline.py`
```python
class TestCurrentDeploymentBaseline:
    """Establish baseline functionality of existing deployment methods."""
    
    def test_deploy_to_gcp_actual_staging_dry_run(self):
        """Validate canonical deployment script works in dry-run mode."""
        # CRITICAL: Tests the OFFICIAL deployment script
        # Expected: Clean execution with proper configuration output
        
    def test_terraform_deploy_infrastructure_plan(self):
        """Validate terraform infrastructure planning works."""
        # CRITICAL: Tests infrastructure layer
        # Expected: Valid terraform plan generation
        
    def test_docker_deployment_script_validation(self):
        """Validate Docker deployment script syntax and logic."""
        # CRITICAL: Tests Docker-based deployment path
        # Expected: Script executes without syntax errors
        
    def test_unified_test_runner_deployment_mode_exists(self):
        """Validate UnifiedTestRunner deployment mode availability."""
        # CRITICAL: Tests if deprecated script fallback works
        # Expected: Mode exists and accepts deployment parameters
```

#### Test File: `test_plans/phase1/test_configuration_consistency_baseline.py`
```python
class TestConfigurationConsistencyBaseline:
    """Document current configuration outputs from each deployment method."""
    
    def test_deploy_to_gcp_actual_config_generation(self):
        """Capture configuration output from deploy_to_gcp_actual.py."""
        # Documents: Environment variables, service configs, secret mappings
        
    def test_terraform_infrastructure_config_output(self):
        """Capture configuration from terraform deployment."""
        # Documents: Infrastructure settings, VPC configs, database connections
        
    def test_docker_compose_config_comparison(self):
        """Capture Docker deployment configuration."""
        # Documents: Container configs, networking, volume mappings
```

### 1.2. Golden Path Functionality Baseline

#### Test File: `test_plans/phase1/test_golden_path_baseline_validation.py`
```python
class TestGoldenPathBaselineValidation:
    """Establish baseline Golden Path functionality before changes."""
    
    def test_user_login_flow_staging_current(self):
        """Test complete user login flow with current deployment."""
        # CRITICAL: Validates auth service functionality
        # Expected: OAuth flow completes successfully
        
    def test_websocket_connection_establishment_current(self):
        """Test WebSocket connection with current deployment."""
        # CRITICAL: Validates WebSocket infrastructure
        # Expected: Connection establishes and maintains heartbeat
        
    def test_ai_response_generation_current(self):
        """Test end-to-end AI response generation with current deployment."""
        # CRITICAL: Validates complete business value delivery
        # Expected: User message → agent processing → AI response
        
    def test_websocket_agent_events_delivery_current(self):
        """Test all 5 critical WebSocket events are delivered."""
        # CRITICAL: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        # Expected: All events delivered in correct sequence
```

---

## Phase 2: DEPLOYMENT SCRIPT FUNCTIONAL TESTS
*Individual script validation and behavior documentation*

### 2.1. deploy_to_gcp_actual.py Functional Tests

#### Test File: `test_plans/phase2/test_deploy_to_gcp_actual_comprehensive.py`
```python
class TestDeployToGcpActualComprehensive:
    """Comprehensive testing of the OFFICIAL deployment script."""
    
    def test_all_parameter_combinations(self):
        """Test all valid parameter combinations."""
        combinations = [
            "--project netra-staging --build-local",
            "--project netra-staging --build-local --check-secrets",
            "--project netra-staging --build-local --check-apis",
            "--project netra-staging --build-local --run-checks",
            "--project netra-staging --skip-build",
            "--project netra-staging --service backend",
            "--project netra-staging --no-traffic",
            "--project netra-staging --dry-run"
        ]
        # Expected: All combinations execute without errors
        
    def test_configuration_output_consistency(self):
        """Validate configuration outputs are consistent."""
        # CRITICAL: WebSocket timeouts, auth URLs, database connections
        # Expected: All outputs match specification
        
    def test_secret_mapping_validation(self):
        """Test Google Secret Manager secret mappings."""
        # CRITICAL: JWT secrets, database credentials, OAuth configs
        # Expected: All required secrets properly mapped
        
    def test_service_dependency_ordering(self):
        """Test services deploy in correct dependency order."""
        # Expected: backend → auth → frontend (or user-specified order)
        
    def test_rollback_functionality(self):
        """Test deployment rollback capabilities."""
        # Expected: --rollback flag works correctly
```

### 2.2. Terraform Infrastructure Tests

#### Test File: `test_plans/phase2/test_terraform_infrastructure_validation.py`
```python
class TestTerraformInfrastructureValidation:
    """Test terraform infrastructure deployment and integration."""
    
    def test_terraform_plan_generation(self):
        """Test terraform plan generation for all environments."""
        # Expected: Valid plans for staging, production environments
        
    def test_terraform_deploy_script_line_111_fix(self):
        """Test fix for line 111 UnifiedTestRunner mode issue."""
        # CRITICAL: Line 111 calls non-existent UnifiedTestRunner mode
        # Expected: Calls correct deployment script after fix
        
    def test_vpc_connector_configuration(self):
        """Test VPC connector settings in terraform."""
        # CRITICAL: Required for Redis/SQL connectivity
        # Expected: VPC connector properly configured
        
    def test_database_migration_script_integration(self):
        """Test PostgreSQL 17 migration script integration."""
        # Expected: Migration scripts work with new deployment flow
```

### 2.3. Docker Deployment Script Tests

#### Test File: `test_plans/phase2/test_docker_deployment_validation.py`
```python
class TestDockerDeploymentValidation:
    """Test Docker-based deployment scripts."""
    
    def test_docker_compose_build_validation(self):
        """Test Docker compose build process."""
        # Expected: All services build successfully
        
    def test_docker_environment_variable_injection(self):
        """Test environment variable handling in Docker deployment."""
        # CRITICAL: Must match GCP deployment environment variables
        # Expected: Consistent environment variable injection
        
    def test_docker_service_networking(self):
        """Test Docker service networking configuration."""
        # Expected: Services can communicate properly
```

---

## Phase 3: CONFIGURATION DRIFT DETECTION TESTS
*Protect Golden Path from configuration inconsistencies*

### 3.1. WebSocket Configuration Consistency

#### Test File: `test_plans/phase3/test_websocket_configuration_drift_detection.py`
```python
class TestWebSocketConfigurationDriftDetection:
    """Detect WebSocket configuration drift across deployment methods."""
    
    def test_websocket_timeout_consistency(self):
        """Ensure WebSocket timeouts are consistent across deployments."""
        expected_timeouts = {
            "WEBSOCKET_CONNECTION_TIMEOUT": "360",  # 6 minutes
            "WEBSOCKET_HEARTBEAT_INTERVAL": "15",   # 15 seconds
            "WEBSOCKET_HEARTBEAT_TIMEOUT": "45",    # 45 seconds
            "WEBSOCKET_CLEANUP_INTERVAL": "120",    # 2 minutes
            "WEBSOCKET_STALE_TIMEOUT": "360",       # 6 minutes
            "WEBSOCKET_CONNECT_TIMEOUT": "10",      # 10 seconds
            "WEBSOCKET_HANDSHAKE_TIMEOUT": "15",    # 15 seconds
            "WEBSOCKET_PING_TIMEOUT": "5",          # 5 seconds
            "WEBSOCKET_CLOSE_TIMEOUT": "10"         # 10 seconds
        }
        # CRITICAL: Configuration drift here breaks chat functionality
        # Expected: All deployment methods produce identical timeout values
        
    def test_websocket_url_format_consistency(self):
        """Ensure WebSocket URLs are formatted consistently."""
        expected_urls = {
            "staging": "wss://api.staging.netrasystems.ai",
            "production": "wss://api.netrasystems.ai"
        }
        # CRITICAL: Wrong URL format breaks WebSocket connections
        # Expected: Consistent URL formatting across deployment methods
```

### 3.2. Authentication Configuration Consistency

#### Test File: `test_plans/phase3/test_auth_configuration_drift_detection.py`
```python
class TestAuthConfigurationDriftDetection:
    """Detect authentication configuration drift across deployment methods."""
    
    def test_jwt_secret_consistency(self):
        """Ensure JWT secrets are consistently mapped."""
        # CRITICAL: JWT_SECRET_KEY and JWT_SECRET_STAGING must map to same GSM secret
        # Expected: Both variables map to jwt-secret-staging
        
    def test_oauth_url_consistency(self):
        """Ensure OAuth URLs are consistent across deployments."""
        expected_oauth_urls = {
            "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
            "FRONTEND_URL": "https://app.staging.netrasystems.ai"
        }
        # CRITICAL: OAuth URL mismatch breaks authentication entirely
        # Expected: Consistent OAuth URLs across all deployment methods
        
    def test_service_secret_mapping_consistency(self):
        """Ensure service secrets are consistently mapped."""
        # CRITICAL: SERVICE_SECRET, SECRET_KEY consistency
        # Expected: All deployment methods use same secret mappings
```

### 3.3. Database Configuration Consistency

#### Test File: `test_plans/phase3/test_database_configuration_drift_detection.py`
```python
class TestDatabaseConfigurationDriftDetection:
    """Detect database configuration drift across deployment methods."""
    
    def test_postgres_connection_string_consistency(self):
        """Ensure PostgreSQL connection strings are built consistently."""
        # CRITICAL: Uses DatabaseURLBuilder SSOT pattern
        # Expected: All deployments use POSTGRES_* variables, not constructed URLs
        
    def test_cloud_sql_proxy_configuration_consistency(self):
        """Ensure Cloud SQL proxy settings are consistent."""
        expected_instance = "netra-staging:us-central1:staging-shared-postgres"
        # CRITICAL: Wrong instance breaks database connectivity
        # Expected: Consistent Cloud SQL instance references
        
    def test_redis_connection_consistency(self):
        """Ensure Redis connection configuration is consistent."""
        expected_redis_host = "10.107.0.3"  # Primary endpoint
        # CRITICAL: Wrong Redis endpoint breaks caching and sessions
        # Expected: Consistent Redis connection parameters
```

---

## Phase 4: TERRAFORM INTEGRATION TESTS
*Infrastructure layer validation and integration*

### 4.1. Terraform-to-Script Integration

#### Test File: `test_plans/phase4/test_terraform_script_integration.py`
```python
class TestTerraformScriptIntegration:
    """Test terraform deployment script integration."""
    
    def test_terraform_deploy_script_calls_correct_deployment(self):
        """Test terraform/deploy.sh calls correct deployment script after fix."""
        # CRITICAL: Line 111 currently calls non-existent UnifiedTestRunner mode
        # Expected: Calls deploy_to_gcp_actual.py with correct parameters
        
    def test_terraform_variable_passthrough(self):
        """Test terraform variables pass through to deployment script."""
        # Expected: PROJECT_ID, environment variables properly passed
        
    def test_terraform_infrastructure_then_deployment_sequence(self):
        """Test complete terraform → deployment sequence."""
        # Expected: Infrastructure provisioning followed by service deployment
        
    def test_terraform_rollback_integration(self):
        """Test terraform infrastructure rollback capabilities."""
        # Expected: Infrastructure can be rolled back safely
```

### 4.2. Infrastructure Consistency Validation

#### Test File: `test_plans/phase4/test_infrastructure_consistency_validation.py`
```python
class TestInfrastructureConsistencyValidation:
    """Validate infrastructure consistency across deployment methods."""
    
    def test_vpc_connector_settings_consistency(self):
        """Ensure VPC connector settings match across terraform and scripts."""
        expected_connector = "staging-connector"
        # CRITICAL: Wrong VPC connector breaks Redis/database access
        # Expected: Consistent VPC connector configuration
        
    def test_cloud_run_settings_consistency(self):
        """Ensure Cloud Run settings are consistent."""
        expected_settings = {
            "memory": {"backend": "4Gi", "auth": "512Mi", "frontend": "512Mi"},
            "cpu": {"backend": "4", "auth": "1", "frontend": "1"},
            "timeout": {"backend": "600", "auth": "600", "frontend": "300"}
        }
        # CRITICAL: Wrong resource settings cause service failures
        # Expected: Consistent Cloud Run resource allocation
        
    def test_load_balancer_configuration_consistency(self):
        """Test load balancer and domain configuration consistency."""
        # Expected: Consistent SSL, domain, and routing configuration
```

---

## Phase 5: GOLDEN PATH PROTECTION TESTS
*Business value validation throughout consolidation process*

### 5.1. End-to-End Business Value Validation

#### Test File: `test_plans/phase5/test_golden_path_protection_validation.py`
```python
class TestGoldenPathProtectionValidation:
    """Protect Golden Path business value during deployment consolidation."""
    
    def test_user_login_to_ai_response_complete_flow(self):
        """Test complete Golden Path: user login → AI responses."""
        # CRITICAL: This is the $500K+ ARR business flow
        # Expected: User can log in and receive AI responses end-to-end
        
    def test_websocket_event_delivery_under_new_deployment(self):
        """Test WebSocket events work after deployment consolidation."""
        required_events = [
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed"
        ]
        # CRITICAL: Missing events break user experience
        # Expected: All 5 events delivered in correct sequence
        
    def test_chat_functionality_regression_detection(self):
        """Test chat functionality doesn't regress during consolidation."""
        # CRITICAL: Chat = 90% of platform value
        # Expected: No degradation in chat response quality or speed
        
    def test_multi_user_isolation_preservation(self):
        """Test user isolation preserved during deployment changes."""
        # CRITICAL: Factory pattern isolation requirements
        # Expected: Multiple users can use chat simultaneously without interference
```

### 5.2. Performance and Reliability Validation

#### Test File: `test_plans/phase5/test_performance_reliability_validation.py`
```python
class TestPerformanceReliabilityValidation:
    """Validate performance and reliability during deployment consolidation."""
    
    def test_deployment_time_comparison(self):
        """Compare deployment times before and after consolidation."""
        # Expected: Deployment time improves or stays same
        
    def test_service_startup_time_validation(self):
        """Test service startup times don't regress."""
        max_startup_times = {
            "backend": 120,   # 2 minutes max
            "auth": 60,       # 1 minute max  
            "frontend": 90    # 1.5 minutes max
        }
        # Expected: Services start within time limits
        
    def test_websocket_connection_reliability(self):
        """Test WebSocket connection reliability under load."""
        # CRITICAL: WebSocket stability crucial for chat
        # Expected: Connections remain stable under normal load
        
    def test_configuration_reload_without_restart(self):
        """Test configuration updates don't require full restart."""
        # Expected: Some configuration changes can be applied dynamically
```

---

## Configuration Comparison Matrices

### 5.3. Pre/Post Consolidation Configuration Matrix

| Configuration Item | Before Consolidation | After Consolidation | Risk Level |
|-------------------|---------------------|-------------------|------------|
| **WebSocket Timeouts** | Multiple inconsistent values | Single SSOT source | HIGH |
| **JWT Secret Mapping** | Potentially inconsistent | Unified GSM mapping | CRITICAL |
| **OAuth URLs** | Environment-specific | Consistent per environment | HIGH |
| **Database Connections** | Multiple construction methods | DatabaseURLBuilder SSOT | CRITICAL |
| **Redis Configuration** | Hard-coded in multiple places | Single configuration source | MEDIUM |
| **VPC Connector** | Terraform vs script mismatch | Single truth source | HIGH |
| **Service Resources** | Different across scripts | Consistent allocation | MEDIUM |

### 5.4. Environment Configuration Validation Matrix

| Environment | Auth URL | API URL | WebSocket URL | Database Instance | Status |
|-------------|----------|---------|---------------|-------------------|--------|
| **Staging** | https://auth.staging.netrasystems.ai | https://api.staging.netrasystems.ai | wss://api.staging.netrasystems.ai | netra-staging:us-central1:staging-shared-postgres | ✅ |
| **Production** | https://auth.netrasystems.ai | https://api.netrasystems.ai | wss://api.netrasystems.ai | netra-production:us-central1:prod-postgres | 🔍 |

---

## Rollback Procedures

### 6.1. Emergency Rollback Plan

#### Immediate Rollback (< 5 minutes)
1. **Service Level Rollback**
   ```bash
   # Rollback Cloud Run services to previous revision
   gcloud run services update-traffic netra-backend-staging --to-revisions=PREVIOUS=100
   gcloud run services update-traffic netra-auth-service --to-revisions=PREVIOUS=100
   gcloud run services update-traffic netra-frontend-staging --to-revisions=PREVIOUS=100
   ```

2. **Configuration Rollback**
   ```bash
   # Restore previous deployment script if needed
   git checkout HEAD~1 -- scripts/deploy_to_gcp_actual.py
   git checkout HEAD~1 -- terraform-gcp-staging/deploy.sh
   ```

#### Infrastructure Rollback (< 15 minutes)
1. **Terraform State Rollback**
   ```bash
   cd terraform-gcp-staging
   terraform state pull > backup.tfstate
   terraform apply -target=resource_to_rollback
   ```

2. **Database Configuration Rollback**
   ```bash
   # Restore previous database connection settings
   gcloud sql instances patch staging-shared-postgres --backup-configuration
   ```

### 6.2. Rollback Success Criteria

| Check | Expected Result | Command |
|-------|----------------|---------|
| **Golden Path Test** | User login → AI response works | Manual test in staging |
| **WebSocket Events** | All 5 events delivered | `python tests/mission_critical/test_websocket_agent_events_suite.py` |
| **Service Health** | All services healthy | `curl https://api.staging.netrasystems.ai/health` |
| **Auth Integration** | OAuth flow completes | Manual OAuth test |

---

## Test Execution Plan

### 7.1. Execution Schedule

| Phase | Duration | Dependencies | Risk Level |
|-------|----------|--------------|------------|
| **Phase 1: Pre-Consolidation** | 2 hours | None | LOW - Documentation only |
| **Phase 2: Script Functional** | 4 hours | Phase 1 complete | MEDIUM - Individual script testing |
| **Phase 3: Configuration Drift** | 3 hours | Phase 2 complete | HIGH - Configuration validation |
| **Phase 4: Terraform Integration** | 3 hours | Phase 3 complete | HIGH - Infrastructure changes |
| **Phase 5: Golden Path Protection** | 2 hours | All phases complete | CRITICAL - Business value |

### 7.2. Test Commands Summary

```bash
# Phase 1: Baseline validation
python -m pytest test_plans/phase1/ -v --tb=short

# Phase 2: Script functional tests  
python -m pytest test_plans/phase2/ -v --tb=short

# Phase 3: Configuration drift detection
python -m pytest test_plans/phase3/ -v --tb=short --strict-config

# Phase 4: Terraform integration
python -m pytest test_plans/phase4/ -v --tb=short

# Phase 5: Golden Path protection
python -m pytest test_plans/phase5/ -v --tb=short --golden-path

# Complete test suite
python -m pytest test_plans/ -v --tb=short --coverage --report
```

### 7.3. Success Criteria for Each Phase

#### Phase 1 Success Criteria
- [ ] All existing deployment methods execute without errors
- [ ] Configuration outputs documented and consistent
- [ ] Golden Path baseline established and working
- [ ] No regressions from current state

#### Phase 2 Success Criteria  
- [ ] deploy_to_gcp_actual.py works with all parameter combinations
- [ ] Terraform infrastructure deploys correctly
- [ ] Docker deployment scripts execute successfully
- [ ] All configuration outputs match specifications

#### Phase 3 Success Criteria
- [ ] No configuration drift detected across deployment methods
- [ ] WebSocket configurations identical across all methods
- [ ] Authentication URLs consistent across all methods
- [ ] Database configurations use consistent patterns

#### Phase 4 Success Criteria
- [ ] Terraform integration works end-to-end
- [ ] Infrastructure → service deployment sequence functions
- [ ] VPC connector and networking settings consistent
- [ ] Rollback procedures tested and functional

#### Phase 5 Success Criteria
- [ ] Golden Path functions identically before and after changes
- [ ] All 5 WebSocket events delivered correctly
- [ ] Chat functionality performs at baseline levels
- [ ] Multi-user isolation preserved

---

## Risk Mitigation

### 8.1. High-Risk Scenarios and Mitigation

| Risk Scenario | Impact | Likelihood | Mitigation |
|---------------|--------|------------|------------|
| **Configuration drift breaks WebSocket** | CRITICAL - Chat fails | MEDIUM | Phase 3 drift detection tests |
| **JWT secret mismatch breaks auth** | CRITICAL - No user access | MEDIUM | Phase 3 auth consistency tests |
| **Terraform script calls wrong deployment** | HIGH - Infrastructure mismatch | HIGH | Phase 4 integration tests |
| **Database connection string changes** | CRITICAL - Data access fails | LOW | Phase 3 database consistency tests |
| **VPC connector misconfiguration** | HIGH - Redis/DB access fails | MEDIUM | Phase 4 infrastructure tests |

### 8.2. Monitoring and Alerting During Testing

```bash
# Monitor service health during testing
watch -n 5 'curl -s https://api.staging.netrasystems.ai/health | jq .'

# Monitor WebSocket connections
python scripts/monitor_websocket_health.py --environment staging

# Monitor database connections  
python scripts/monitor_database_health.py --environment staging

# Monitor authentication flow
python scripts/monitor_auth_health.py --environment staging
```

### 8.3. Emergency Contacts and Escalation

| Issue Type | Contact | Response Time |
|------------|---------|---------------|
| **Golden Path Failure** | Primary Engineer | < 15 minutes |
| **Database Connectivity** | Infrastructure Team | < 30 minutes |
| **WebSocket Issues** | Backend Team | < 15 minutes |
| **Auth Service Problems** | Security Team | < 30 minutes |

---

## Conclusion

This comprehensive test plan ensures safe consolidation of deployment scripts while protecting the Golden Path business functionality. The 5-phase approach provides multiple validation layers, from baseline documentation through business value protection.

**Key Success Factors:**
1. **Safety First:** Extensive pre-consolidation validation
2. **Business Focus:** Golden Path protection throughout
3. **Configuration Vigilance:** Drift detection for critical settings  
4. **Infrastructure Integration:** Terraform and script coordination
5. **Rollback Readiness:** Quick recovery procedures

**Expected Outcome:** Single canonical deployment source (`deploy_to_gcp_actual.py`) with all functionality preserved and infrastructure properly integrated via terraform.

**Risk Level:** MANAGED - Comprehensive testing reduces risk from EXTREME to MEDIUM with proper execution.