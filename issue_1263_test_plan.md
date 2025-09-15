# 🧪 COMPREHENSIVE TEST PLAN - Issue #1263 Database Connectivity Timeout

**Status**: Ready for implementation
**Priority**: P0 - Critical (Complete system unavailability)
**Testing Strategy**: Reproduce exact 8.0-second timeout failure, then validate remediation

---

## Executive Summary

**TEST OBJECTIVE**: Reproduce the exact 8.0-second database initialization timeout in staging environment and validate different connection approaches to identify root cause and remediation path.

**ROOT CAUSE ANALYSIS FINDINGS**:
- **Timeout Configuration**: 8.0s set in `database_timeout_config.py:56` for staging environment
- **Error Location**: `smd.py:1005,1018,1882` - DeterministicStartupError during database initialization
- **Connection Method**: AsyncPG → SQLAlchemy async engine → Cloud SQL
- **Key Variables**: `POSTGRES_HOST` configuration, VPC connector routing, Secret Manager integration

---

## 📋 Test Categories Overview

### 1. Unit Tests - Configuration & Timeout Validation
**Purpose**: Validate database configuration loading and timeout threshold handling
**Infrastructure**: None required
**Execution**: Run without Docker

### 2. Integration Tests - Cloud SQL Connectivity Patterns
**Purpose**: Test actual Cloud SQL connection patterns without full system deployment
**Infrastructure**: Local test environment with Cloud SQL credentials
**Execution**: Non-Docker integration tests

### 3. E2E Staging Tests - Full System Validation
**Purpose**: Validate complete database initialization flow in actual staging environment
**Infrastructure**: GCP staging environment
**Execution**: Staging environment deployment

---

## 🧪 1. Unit Test Suite - Database Configuration & Timeout Validation

**File Location**: `netra_backend/tests/unit/test_issue_1263_database_timeout_reproduction.py`

### Test Cases:

#### Test 1.1: Database Timeout Configuration Loading
```python
async def test_staging_timeout_configuration_loads_8_second_timeout():
    """Reproduce exact 8.0s timeout configuration that causes Issue #1263."""
    from netra_backend.app.core.database_timeout_config import get_database_timeout_config

    # REPRODUCE: Get exact staging timeout config
    config = get_database_timeout_config("staging")

    # VALIDATE: Exact timeout values that cause failure
    assert config["initialization_timeout"] == 8.0
    assert config["table_setup_timeout"] == 5.0
    assert config["connection_timeout"] == 3.0

    # BUSINESS IMPACT: These timeouts are causing startup failures
```

#### Test 1.2: POSTGRES_HOST Environment Variable Validation
```python
async def test_postgres_host_configuration_validation():
    """Test POSTGRES_HOST environment variable configuration patterns."""
    from shared.database_url_builder import DatabaseURLBuilder

    test_cases = [
        ("staging-cloudsql-host", "expected"),  # From .env.staging.tests
        ("localhost", "development"),             # Local development
        ("", "missing"),                         # Missing configuration
        ("invalid-host", "unreachable")          # Unreachable host
    ]

    for postgres_host, expected_category in test_cases:
        env_vars = {"POSTGRES_HOST": postgres_host, "ENVIRONMENT": "staging"}
        builder = DatabaseURLBuilder(env_vars)

        # VALIDATE: URL construction patterns
        cloud_sql_url = builder.cloud_sql.async_url
        assert postgres_host in cloud_sql_url or not postgres_host
```

#### Test 1.3: Database Connection Timeout Simulation
```python
async def test_database_connection_timeout_simulation():
    """Simulate database connection timeout to reproduce DeterministicStartupError."""
    import asyncio
    from netra_backend.app.smd import DeterministicStartupError

    # SIMULATE: Connection that takes longer than 8.0s
    async def mock_slow_database_init():
        await asyncio.sleep(9.0)  # Exceed 8.0s timeout
        return "mock_session_factory"

    # REPRODUCE: asyncio.wait_for timeout behavior
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(mock_slow_database_init(), timeout=8.0)

    # VALIDATE: This should trigger DeterministicStartupError in real system
```

#### Test 1.4: Secret Manager Configuration Loading
```python
async def test_secret_manager_postgres_configuration():
    """Test Secret Manager integration for POSTGRES_HOST resolution."""
    from unittest.mock import patch, MagicMock

    # MOCK: Secret Manager unavailable (common in staging)
    with patch('google.cloud.secretmanager') as mock_sm:
        mock_sm.side_effect = ImportError("Secret Manager not available")

        # REPRODUCE: Fallback to environment variables when SM unavailable
        env_vars = {"POSTGRES_HOST": "fallback-host", "ENVIRONMENT": "staging"}

        # VALIDATE: System should fall back to env vars gracefully
        from shared.database_url_builder import DatabaseURLBuilder
        builder = DatabaseURLBuilder(env_vars)
        assert "fallback-host" in builder.postgres_host
```

---

## 🔗 2. Integration Test Suite - Cloud SQL Connectivity Patterns

**File Location**: `netra_backend/tests/integration/test_issue_1263_cloud_sql_connectivity.py`

### Test Cases:

#### Test 2.1: Cloud SQL Direct Connection Testing
```python
async def test_cloud_sql_direct_connection_with_timeout():
    """Test direct Cloud SQL connection with 8.0s timeout."""
    import asyncpg
    import asyncio
    from shared.database_url_builder import DatabaseURLBuilder

    # SETUP: Use actual staging environment variables
    env = get_env()
    env_vars = {
        "POSTGRES_HOST": env.get("POSTGRES_HOST"),
        "POSTGRES_USER": env.get("POSTGRES_USER"),
        "POSTGRES_PASSWORD": env.get("POSTGRES_PASSWORD"),
        "POSTGRES_DB": env.get("POSTGRES_DB"),
        "ENVIRONMENT": "staging"
    }

    builder = DatabaseURLBuilder(env_vars)
    connection_url = builder.cloud_sql.async_url

    # REPRODUCE: Connection attempt with exact staging timeout
    start_time = time.time()
    try:
        connection = await asyncio.wait_for(
            asyncpg.connect(connection_url),
            timeout=8.0  # Exact timeout that causes Issue #1263
        )
        connection_time = time.time() - start_time

        # VALIDATE: Connection succeeded within timeout
        assert connection_time < 8.0
        await connection.close()

    except asyncio.TimeoutError:
        connection_time = time.time() - start_time
        # REPRODUCE: This is the exact Issue #1263 failure
        assert connection_time >= 8.0
        pytest.fail(f"Database connection timeout after {connection_time:.2f}s - Issue #1263 reproduced")
```

#### Test 2.2: VPC Connector Routing Validation
```python
async def test_vpc_connector_routing_to_cloud_sql():
    """Test VPC connector routing to Cloud SQL instance."""
    import subprocess
    from shared.isolated_environment import get_env

    env = get_env()
    postgres_host = env.get("POSTGRES_HOST")

    if not postgres_host or postgres_host == "localhost":
        pytest.skip("VPC connector test requires Cloud SQL POSTGRES_HOST")

    # TEST: DNS resolution of POSTGRES_HOST
    try:
        result = subprocess.run(
            ["nslookup", postgres_host],
            capture_output=True,
            text=True,
            timeout=5.0
        )
        # VALIDATE: POSTGRES_HOST resolves to IP address
        assert result.returncode == 0, f"DNS resolution failed for {postgres_host}"
        assert "Address" in result.stdout

    except subprocess.TimeoutExpired:
        pytest.fail(f"DNS resolution timeout for {postgres_host} - VPC connector issue")
```

#### Test 2.3: Database URL Construction Validation
```python
async def test_database_url_construction_patterns():
    """Test different database URL construction patterns for troubleshooting."""
    from shared.database_url_builder import DatabaseURLBuilder

    # TEST: Different connection approaches
    connection_patterns = [
        {"approach": "cloud_sql_socket", "env": {"POSTGRES_HOST": "/cloudsql/project:region:instance"}},
        {"approach": "cloud_sql_tcp", "env": {"POSTGRES_HOST": "10.1.2.3"}},
        {"approach": "cloud_sql_proxy", "env": {"POSTGRES_HOST": "127.0.0.1", "POSTGRES_PORT": "5432"}},
    ]

    for pattern in connection_patterns:
        env_vars = {**pattern["env"], "ENVIRONMENT": "staging"}
        builder = DatabaseURLBuilder(env_vars)

        # VALIDATE: URL construction for different approaches
        url = builder.cloud_sql.async_url
        assert "postgresql+asyncpg://" in url
        assert pattern["env"]["POSTGRES_HOST"] in url
```

---

## 🌐 3. E2E Staging Test Suite - Full System Validation

**File Location**: `tests/e2e/staging/test_issue_1263_staging_database_validation.py`

### Test Cases:

#### Test 3.1: Complete Staging Database Initialization
```python
async def test_complete_staging_database_initialization():
    """Test complete database initialization flow in staging environment."""
    from netra_backend.app.smd import StartupOrchestrator, DeterministicStartupError
    from fastapi import FastAPI

    app = FastAPI()
    orchestrator = StartupOrchestrator(app)

    # REPRODUCE: Exact startup sequence that fails in Issue #1263
    start_time = time.time()
    try:
        await orchestrator._initialize_database()
        initialization_time = time.time() - start_time

        # VALIDATE: Database initialization completed within timeout
        assert initialization_time < 8.0
        assert app.state.database_available == True
        assert app.state.db_session_factory is not None

    except DeterministicStartupError as e:
        initialization_time = time.time() - start_time
        # REPRODUCE: This is Issue #1263 - capture exact error
        assert "Database initialization timeout after 8.0s" in str(e)
        assert initialization_time >= 8.0

        # LOG: Detailed reproduction information
        logging.error(f"Issue #1263 reproduced: {e}")
        logging.error(f"Initialization time: {initialization_time:.2f}s")
        logging.error(f"Environment: {get_env().get('ENVIRONMENT')}")
        logging.error(f"POSTGRES_HOST: {get_env().get('POSTGRES_HOST')}")

        pytest.fail(f"Issue #1263 reproduced: Database timeout after {initialization_time:.2f}s")
```

#### Test 3.2: Staging Environment Configuration Validation
```python
async def test_staging_environment_configuration_validation():
    """Validate all staging environment configuration for database connectivity."""
    from shared.isolated_environment import get_env

    env = get_env()

    # VALIDATE: Critical environment variables are set
    required_vars = ["POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
    missing_vars = [var for var in required_vars if not env.get(var)]

    assert not missing_vars, f"Missing required environment variables: {missing_vars}"

    # VALIDATE: POSTGRES_HOST is not placeholder
    postgres_host = env.get("POSTGRES_HOST")
    placeholder_patterns = ["localhost", "placeholder", "CHANGE_ME", "staging-cloudsql-host"]

    is_placeholder = any(pattern in postgres_host.lower() for pattern in placeholder_patterns)
    if is_placeholder:
        pytest.fail(f"POSTGRES_HOST appears to be placeholder: {postgres_host}")

    # VALIDATE: Environment is correctly set to staging
    assert env.get("ENVIRONMENT").lower() == "staging"
```

#### Test 3.3: Cloud SQL Instance Accessibility Test
```python
async def test_cloud_sql_instance_accessibility():
    """Test Cloud SQL instance accessibility from staging environment."""
    import socket
    from shared.isolated_environment import get_env

    env = get_env()
    postgres_host = env.get("POSTGRES_HOST")
    postgres_port = int(env.get("POSTGRES_PORT", "5432"))

    # TEST: Direct socket connection to Cloud SQL
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(8.0)  # Same timeout as Issue #1263
            result = sock.connect_ex((postgres_host, postgres_port))

            if result == 0:
                # SUCCESS: Cloud SQL instance is accessible
                assert True
            else:
                pytest.fail(f"Cloud SQL instance not accessible: {postgres_host}:{postgres_port}")

    except socket.timeout:
        pytest.fail(f"Cloud SQL connection timeout to {postgres_host}:{postgres_port}")
    except socket.gaierror as e:
        pytest.fail(f"DNS resolution failed for {postgres_host}: {e}")
```

---

## 📊 Test Execution Strategy

### Phase 1: Unit Tests (Local Development)
```bash
# Run unit tests to validate configuration loading
python tests/unified_test_runner.py --test-file netra_backend/tests/unit/test_issue_1263_database_timeout_reproduction.py

# Expected: Tests should PASS for configuration loading, REPRODUCE timeout scenarios
```

### Phase 2: Integration Tests (Non-Docker)
```bash
# Run integration tests with actual environment variables
# Note: Replace with actual Cloud SQL IP
POSTGRES_HOST=<CLOUD_SQL_IP> python tests/unified_test_runner.py --test-file netra_backend/tests/integration/test_issue_1263_cloud_sql_connectivity.py

# Expected: Tests should FAIL initially, reproducing Issue #1263 connectivity problems
```

### Phase 3: E2E Staging Tests
```bash
# Deploy to staging and run E2E tests
python scripts/deploy_to_gcp.py --project netra-staging --build-local
python tests/unified_test_runner.py --test-file tests/e2e/staging/test_issue_1263_staging_database_validation.py

# Expected: Tests should FAIL, reproducing Issue #1263 in staging environment
```

---

## 🔧 Test-Driven Remediation Approach

### Remediation Test Strategy:
1. **Tests FAIL First**: All tests should fail initially, reproducing Issue #1263
2. **Root Cause Identification**: Test failures will pinpoint exact connectivity issues
3. **Iterative Fixes**: Apply fixes for each identified root cause
4. **Validation**: Tests pass after each fix, confirming remediation
5. **Regression Prevention**: Tests remain as permanent safeguards

### Expected Root Causes to Test:
- **VPC Egress Configuration**: Test VPC connector routing
- **POSTGRES_HOST Placeholders**: Test for actual vs placeholder values
- **Secret Manager Integration**: Test fallback when Secret Manager unavailable
- **Timeout Thresholds**: Test if 8.0s is sufficient for Cloud SQL connection establishment

---

## 📈 Success Criteria

### Test Success Metrics:
- [ ] **Unit Tests**: 100% pass rate for configuration loading and timeout validation
- [ ] **Integration Tests**: Successful Cloud SQL connection within 8.0s timeout
- [ ] **E2E Tests**: Complete staging database initialization without DeterministicStartupError
- [ ] **Remediation Validation**: All tests pass after applying fixes

### Business Value Validation:
- [ ] **Chat Functionality**: End-to-end user flow operational in staging
- [ ] **System Startup**: Backend service starts successfully within timeout limits
- [ ] **Golden Path**: Complete user journey from login to AI responses working
- [ ] **Deployment Readiness**: Staging environment ready for production promotion

---

**Implementation Priority**: P0 - Critical
**Est. Development Time**: 4-6 hours for complete test suite
**Est. Execution Time**: 30 minutes for full test cycle
**Business Impact Protection**: $500K+ ARR chat functionality validation

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>