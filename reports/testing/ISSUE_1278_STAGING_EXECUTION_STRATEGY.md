# Issue #1278 Staging GCP Remote Execution Strategy

**Agent Session ID**: agent-session-20250915-143500  
**Created**: 2025-09-15  
**Purpose**: Test execution strategy for staging GCP remote environment testing  

## Executive Summary

This document defines the execution strategy for running Issue #1278 tests against the staging GCP remote environment to reproduce SMD Phase 3 database timeout failures. The strategy focuses on non-docker testing approaches that can validate infrastructure connectivity issues while preserving the integrity of the staging environment.

## Staging Environment Configuration

### GCP Staging Infrastructure
```yaml
Environment: staging
GCP Project: netra-staging
Region: us-central1
Zone: us-central1-a

Database:
  Type: Cloud SQL PostgreSQL
  Instance: netra-staging-db
  Connection: /cloudsql/netra-staging:us-central1:netra-staging-db
  Socket: Unix socket connection
  VPC Connector: staging-vpc-connector

Services:
  Backend: https://backend.staging.netrasystems.ai
  Auth: https://auth.staging.netrasystems.ai  
  Frontend: https://staging.netrasystems.ai
  WebSocket: wss://backend.staging.netrasystems.ai/ws

Load Balancer:
  Type: Global HTTP(S) Load Balancer
  Health Checks: /health endpoint monitoring
  SSL Termination: Managed SSL certificates
```

### VPC Connector Configuration
```yaml
VPC Connector: staging-vpc-connector
Throughput: 200-1000 Mbps (autoscaling)
Instance Range: 2-10 instances
Network: staging-vpc
Subnet: staging-subnet-connector
Machine Type: e2-micro (shared-core)

Capacity Constraints:
  Max Concurrent Connections: 250 per instance
  Connection Rate Limit: 600 connections/minute
  Scaling Delay: 30-60 seconds during peak
  Cool-down Period: 180 seconds between scaling events
```

### Cloud SQL Configuration
```yaml
Cloud SQL Instance: netra-staging-db
Machine Type: db-custom-2-7680 (2 vCPU, 7.5 GB RAM)
Storage: 100 GB SSD
Connections:
  Max Connections: 162 (default for 2 vCPU)
  Connection Pool Limit: 25 per application instance
  Connection Timeout: 30 seconds
  Statement Timeout: 300 seconds

High Availability: Regional persistent disk
Backup: Automated daily backups
Maintenance Window: Sunday 06:00-07:00 UTC
```

## Test Execution Strategy

### 1. Non-Docker Remote Testing Approach

#### Local to Staging Connectivity
```bash
# Environment setup for staging connectivity
export ENVIRONMENT=staging
export TESTING_MODE=staging_remote
export GCP_PROJECT=netra-staging

# Staging service URLs (canonical domains)
export STAGING_BACKEND_URL=https://backend.staging.netrasystems.ai
export STAGING_AUTH_URL=https://auth.staging.netrasystems.ai
export STAGING_WEBSOCKET_URL=wss://backend.staging.netrasystems.ai/ws
export STAGING_FRONTEND_URL=https://staging.netrasystems.ai

# Database connection configuration
export POSTGRES_HOST=/cloudsql/netra-staging:us-central1:netra-staging-db
export POSTGRES_PORT=5432
export POSTGRES_DB=netra_staging
export POSTGRES_SSL_MODE=require

# Authentication configuration
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/staging-service-account.json
export STAGING_API_KEY=staging_api_key_value
```

#### Network Connectivity Requirements
```yaml
Required Network Access:
  - Outbound HTTPS (443) to *.staging.netrasystems.ai
  - Outbound WSS (443) for WebSocket connections
  - Cloud SQL Proxy for database connections
  - GCP APIs for monitoring and metrics collection

Firewall Rules:
  - Allow outbound to 35.199.192.0/19 (Google Cloud SQL)
  - Allow outbound to 199.36.153.8/30 (Google APIs)
  - Allow outbound to staging VPC CIDR blocks

Authentication:
  - Service account key for GCP access
  - Staging API keys for service authentication
  - OAuth tokens for user authentication testing
```

### 2. Test Execution Phases

#### Phase 1: Infrastructure Connectivity Validation (5-10 minutes)
```bash
# Phase 1.1: Basic network connectivity
python tests/connectivity/test_issue_1278_vpc_connector_validation.py::TestVPCConnectorValidation::test_direct_cloud_sql_connectivity -v

# Phase 1.2: VPC connector health check
python tests/connectivity/test_issue_1278_vpc_connector_validation.py::TestVPCConnectorValidation::test_vpc_connector_capacity_monitoring -v

# Phase 1.3: Staging service endpoints validation
python -m pytest tests/e2e/staging/ -k "connectivity" -v --tb=short
```

#### Phase 2: Database Connection Testing (10-20 minutes)
```bash
# Phase 2.1: Cloud SQL connection pool testing
python tests/integration/test_issue_1278_cloud_sql_pool_behavior.py::TestCloudSQLPoolBehavior::test_connection_pool_limit_enforcement -v

# Phase 2.2: Database initialization under pressure
python netra_backend/tests/integration/test_issue_1278_database_initialization_integration.py::TestDatabaseInitializationIntegration::test_cloud_sql_connection_establishment_timing -v

# Phase 2.3: Progressive retry mechanism validation
python netra_backend/tests/integration/test_issue_1278_database_initialization_integration.py::TestDatabaseInitializationIntegration::test_progressive_retry_mechanism_validation -v
```

#### Phase 3: SMD Sequence Reproduction (30-60 minutes)
```bash
# Phase 3.1: Complete SMD sequence testing
python tests/e2e/test_issue_1278_smd_sequence_staging_validation.py::TestSMDSequenceStagingValidation::test_complete_smd_7_phase_sequence_under_load -v -m staging

# Phase 3.2: SMD Phase 3 timeout reproduction
python tests/e2e/test_issue_1278_smd_sequence_staging_validation.py::TestSMDSequenceStagingValidation::test_smd_phase3_timeout_reproduction_staging -v -m staging

# Phase 3.3: Infrastructure capacity monitoring during failure
python tests/e2e/test_issue_1278_smd_sequence_staging_validation.py::TestSMDSequenceStagingValidation::test_staging_infrastructure_capacity_monitoring -v -m staging
```

#### Phase 4: Business Impact Validation (30-45 minutes)
```bash
# Phase 4.1: Golden Path pipeline availability testing
python tests/e2e/test_issue_1278_golden_path_pipeline_validation.py::TestGoldenPathPipelineValidation::test_golden_path_pipeline_availability_impact -v -m staging

# Phase 4.2: User login to AI response flow testing
python tests/e2e/test_issue_1278_golden_path_pipeline_validation.py::TestGoldenPathPipelineValidation::test_user_login_to_ai_response_flow_under_pressure -v -m staging

# Phase 4.3: $500K+ ARR pipeline offline validation
python tests/e2e/test_issue_1278_golden_path_pipeline_validation.py::TestGoldenPathPipelineValidation::test_500k_arr_pipeline_offline_validation -v -m staging
```

### 3. Unified Test Runner Integration

#### Fast Feedback Mode (Issue #1278 focused)
```bash
# Quick Issue #1278 validation (5-10 minutes)
python tests/unified_test_runner.py \
  --execution-mode fast_feedback \
  --test-pattern "*issue_1278*" \
  --env staging \
  --no-docker \
  --real-services
```

#### Full Issue #1278 Test Suite
```bash
# Complete Issue #1278 test execution (60-90 minutes)
python tests/unified_test_runner.py \
  --categories unit integration e2e \
  --test-pattern "*issue_1278*" \
  --env staging \
  --no-docker \
  --real-services \
  --collect-metrics \
  --output-format detailed
```

#### Staging-Specific E2E Mode
```bash
# Staging environment focused testing (45-75 minutes)
python tests/unified_test_runner.py \
  --categories e2e \
  --env staging \
  --markers staging \
  --test-pattern "*issue_1278*staging*" \
  --no-docker \
  --real-services \
  --infrastructure-monitoring \
  --business-impact-analysis
```

## Infrastructure Monitoring During Tests

### 1. VPC Connector Monitoring
```python
# VPC connector metrics collection
vpc_metrics = {
    "concurrent_connections": "current active connections",
    "throughput_utilization": "bandwidth usage percentage", 
    "scaling_events": "autoscaling events during test period",
    "connection_latency": "average connection establishment time",
    "capacity_pressure_indicators": "signs of capacity constraints",
    "error_rates": "connection failure rates"
}

# Monitoring implementation
async def monitor_vpc_connector_during_test():
    """Monitor VPC connector metrics during test execution."""
    start_time = time.time()
    metrics_history = []
    
    while test_running:
        current_metrics = await collect_vpc_metrics()
        metrics_history.append({
            "timestamp": time.time(),
            "metrics": current_metrics,
            "test_phase": current_test_phase
        })
        await asyncio.sleep(10)  # Collect every 10 seconds
    
    return analyze_vpc_performance_during_test(metrics_history)
```

### 2. Cloud SQL Monitoring
```python
# Cloud SQL metrics collection
cloud_sql_metrics = {
    "active_connections": "current connection count",
    "connection_pool_utilization": "pool usage percentage",
    "query_latency": "average query response time",
    "connection_errors": "failed connection attempts",
    "resource_utilization": "CPU/memory usage during tests",
    "lock_contention": "database lock wait times"
}

# Monitoring implementation
async def monitor_cloud_sql_during_test():
    """Monitor Cloud SQL metrics during test execution."""
    # Collect Cloud SQL performance metrics
    # Monitor connection pool behavior
    # Track query performance degradation
    # Document resource constraint patterns
```

### 3. Application Performance Monitoring
```python
# Application performance metrics
app_metrics = {
    "smd_phase_timing": "individual phase execution times",
    "startup_sequence_duration": "total startup time measurement",
    "error_propagation_timing": "time from failure to error",
    "resource_cleanup_duration": "cleanup time after failures",
    "memory_usage_patterns": "memory consumption during startup",
    "thread_pool_utilization": "async task pool usage"
}
```

## Test Result Collection and Analysis

### 1. Automated Test Result Processing
```bash
# Test result collection script
#!/bin/bash
# collect_issue_1278_test_results.sh

TEST_SESSION_ID="issue_1278_$(date +%Y%m%d_%H%M%S)"
RESULTS_DIR="/Users/anthony/Desktop/netra-apex/reports/testing/issue_1278_results"

mkdir -p "$RESULTS_DIR/$TEST_SESSION_ID"

# Run tests with detailed output
python tests/unified_test_runner.py \
  --categories unit integration e2e \
  --test-pattern "*issue_1278*" \
  --env staging \
  --output-format json \
  --collect-metrics \
  --infrastructure-monitoring \
  > "$RESULTS_DIR/$TEST_SESSION_ID/test_execution_log.json" 2>&1

# Collect infrastructure metrics
gcloud monitoring metrics list \
  --filter="resource.type=gce_instance AND metric.type=compute.googleapis.com/instance/network/received_bytes_count" \
  --format=json \
  > "$RESULTS_DIR/$TEST_SESSION_ID/vpc_connector_metrics.json"

# Collect Cloud SQL metrics
gcloud sql operations list \
  --instance=netra-staging-db \
  --format=json \
  > "$RESULTS_DIR/$TEST_SESSION_ID/cloud_sql_operations.json"

# Generate test summary report
python scripts/generate_issue_1278_test_report.py \
  --session-id "$TEST_SESSION_ID" \
  --results-dir "$RESULTS_DIR/$TEST_SESSION_ID"
```

### 2. Test Failure Analysis Framework
```python
class Issue1278TestFailureAnalyzer:
    """Analyze test failures to categorize Issue #1278 reproduction patterns."""
    
    def analyze_test_results(self, test_session_results):
        """Analyze test results for Issue #1278 patterns."""
        failure_categories = {
            "smd_phase3_timeout": [],
            "vpc_connector_capacity": [],
            "cloud_sql_pool_exhaustion": [],
            "fastapi_lifespan_breakdown": [],
            "container_exit_code_3": [],
            "golden_path_offline": []
        }
        
        for test_result in test_session_results:
            failure_category = self.categorize_failure(test_result)
            if failure_category:
                failure_categories[failure_category].append(test_result)
        
        return self.generate_failure_analysis_report(failure_categories)
    
    def categorize_failure(self, test_result):
        """Categorize test failure based on error patterns."""
        error_message = test_result.get("error_message", "").lower()
        
        if "phase 3" in error_message and "timeout" in error_message:
            return "smd_phase3_timeout"
        elif "vpc connector" in error_message or "capacity" in error_message:
            return "vpc_connector_capacity"
        elif "connection pool" in error_message or "pool exhaustion" in error_message:
            return "cloud_sql_pool_exhaustion"
        elif "lifespan" in error_message and "startup" in error_message:
            return "fastapi_lifespan_breakdown"
        elif "exit code 3" in error_message or "container exit" in error_message:
            return "container_exit_code_3"
        elif "golden path" in error_message or "pipeline offline" in error_message:
            return "golden_path_offline"
        
        return None
```

## Expected Test Execution Timeline

### Daily Test Execution Schedule
```yaml
Morning Session (9:00 AM - 11:00 AM PST):
  - Phase 1: Infrastructure Connectivity (15 minutes)
  - Phase 2: Database Connection Testing (30 minutes)
  - Phase 3: SMD Sequence Reproduction (60 minutes)
  - Phase 4: Results Analysis (15 minutes)
  Total Duration: 2 hours

Afternoon Session (2:00 PM - 4:00 PM PST):
  - Business Impact Validation (45 minutes)
  - Golden Path Pipeline Testing (60 minutes)
  - Comprehensive Results Analysis (15 minutes)
  Total Duration: 2 hours

Evening Session (Optional - 6:00 PM - 7:00 PM PST):
  - Infrastructure Monitoring Data Collection (30 minutes)
  - Test Result Consolidation (30 minutes)
  Total Duration: 1 hour
```

### Weekly Test Execution Cycle
```yaml
Monday: Baseline infrastructure health validation
Tuesday: Unit and integration test execution
Wednesday: E2E staging environment testing
Thursday: Business impact and Golden Path testing
Friday: Results analysis and reporting

Weekend: Infrastructure monitoring and metrics analysis
```

## Risk Mitigation and Safety Measures

### 1. Staging Environment Protection
```yaml
Safety Measures:
  - Read-only database connections where possible
  - Rate limiting for connection pool testing
  - Automatic test termination after 90 minutes
  - Resource cleanup after each test phase
  - Monitoring for staging environment impact

Connection Limits:
  - Maximum 5 concurrent database connections per test
  - Maximum 10 WebSocket connections per test session
  - Connection timeout of 30 seconds for safety
  - Automatic connection cleanup on test completion
```

### 2. Test Isolation and Cleanup
```python
@pytest.fixture(autouse=True)
async def staging_test_safety():
    """Ensure staging test safety and cleanup."""
    # Pre-test safety checks
    staging_health = await check_staging_environment_health()
    if not staging_health.is_healthy:
        pytest.skip("Staging environment not healthy - skipping test")
    
    yield  # Run test
    
    # Post-test cleanup
    await cleanup_test_resources()
    await verify_staging_environment_stability()
```

### 3. Monitoring and Alerting
```yaml
Monitoring Setup:
  - Real-time staging environment health monitoring
  - Automatic alerts for staging service degradation
  - Test execution impact monitoring
  - Resource utilization tracking during tests

Alert Thresholds:
  - CPU utilization > 80% for more than 5 minutes
  - Connection pool utilization > 90%
  - Error rate > 5% during test execution
  - Response time degradation > 200% baseline
```

## Success Metrics and KPIs

### Test Execution Success Metrics
```yaml
Technical Metrics:
  - Test completion rate: Target 95%+
  - Infrastructure issue reproduction rate: Target 90%+
  - SMD Phase 3 timeout reproduction: Target 100%
  - Container exit code 3 validation: Target 100%
  - VPC connector capacity measurement accuracy: Target 95%+

Business Impact Metrics:
  - Golden Path pipeline offline validation: Target 100%
  - $500K+ ARR impact measurement: Target accurate quantification
  - Staging environment availability during tests: Target 99%+
  - Test execution time efficiency: Target <2 hours per full cycle
```

### Performance Benchmarks
```yaml
Expected Performance Baselines:
  - SMD Phase 3 timeout: 75.0 seconds in staging
  - VPC connector scaling delay: 30-60 seconds
  - Cloud SQL connection establishment: 5-10 seconds normal, 25+ seconds under pressure
  - Container restart cycle: 2-3 minutes
  - Golden Path pipeline recovery: 5-10 minutes after infrastructure resolution
```

---

**Staging Execution Strategy Status**: COMPLETE  
**Environment**: GCP Staging Remote  
**Testing Approach**: Non-Docker Connectivity-Focused  
**Expected Duration**: 2-5 hours per complete test cycle  
**Business Value**: Systematic reproduction and resolution planning for $500K+ ARR pipeline outage