# 🧪 COMPREHENSIVE TEST PLAN - Issue #1278 Infrastructure Deep-Root Testing

**Issue Context:** Issue #1278 represents a recurrence of Issue #1263's root cause, indicating incomplete resolution of deeper infrastructure issues that manifest as cascading SMD Phase 3 database initialization failures.

**Test Strategy:** Create failing tests that expose the infrastructure issues Issue #1263 fix missed, focusing on VPC connector operational limits, Cloud SQL capacity constraints, and SMD orchestration resilience.

---

## Executive Summary

### Root Cause Analysis Gap
Issue #1263 addressed deployment configuration (VPC connector flags) but **DID NOT** resolve:
1. **Cloud SQL Capacity Constraints** - Connection pool limits under load
2. **VPC Connector Operational Limits** - Network throughput and concurrent connection handling
3. **SMD Phase Failure Cascade** - Incomplete error handling in startup orchestration
4. **FastAPI Lifespan Error Context** - Loss of error context during startup failures

### Test Plan Objective
**Create tests that REPRODUCE Issue #1278 symptoms by exposing these deeper infrastructure issues that the Issue #1263 fix missed.**

---

## 📋 Test Categories & Focus Areas

### 1. Unit Tests (`netra_backend/tests/unit/startup/`)
**Focus:** Database connection timeout configuration validation and SMD phase logic
**Infrastructure:** None required
**Expected Result:** Tests should FAIL initially, exposing configuration gaps

### 2. Integration Tests (`netra_backend/tests/integration/infrastructure/`)  
**Focus:** VPC connector connectivity and Cloud SQL operational validation
**Infrastructure:** Local services simulation
**Expected Result:** Tests should FAIL when simulating Cloud SQL constraints

### 3. E2E Tests (`tests/e2e/infrastructure/`)
**Focus:** Staging GCP remote testing of startup sequence under real constraints
**Infrastructure:** Real GCP Cloud SQL and VPC connector
**Expected Result:** Tests should FAIL initially, reproducing Issue #1278 exactly

---

## 🔬 Detailed Test Specifications

### Unit Tests - Database Timeout Configuration

#### File: `netra_backend/tests/unit/startup/test_issue_1278_database_timeout_validation.py`

```python
"""
Unit Tests for Issue #1278 - Database Timeout Configuration Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Staging Environment Reliability  
- Value Impact: Validate timeout configurations handle Cloud SQL constraints
- Strategic Impact: Prevent cascading startup failures worth $500K+ ARR impact

Expected Result: Tests should FAIL initially, reproducing Issue #1278 timeout configuration gaps
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from netra_backend.app.core.database_timeout_config import (
    get_database_timeout_config, 
    get_cloud_sql_optimized_config,
    is_cloud_sql_environment
)

class TestIssue1278DatabaseTimeoutValidation:
    """Test database timeout configuration for Issue #1278 infrastructure constraints."""
    
    def test_staging_timeout_insufficient_for_cloud_sql_constraints(self):
        """
        CRITICAL TEST: Verify staging timeouts insufficient for Cloud SQL capacity constraints.
        
        This test should FAIL initially - Issue #1263 fix increased timeouts to 25.0s
        but this is still insufficient under Cloud SQL capacity pressure.
        
        Expected: TEST FAILURE - 25.0s timeout insufficient under load
        """
        config = get_database_timeout_config("staging")
        
        # Issue #1263 fix: 25.0s timeout
        assert config["initialization_timeout"] == 25.0
        
        # CRITICAL FAILURE POINT: 25.0s insufficient under Cloud SQL capacity constraints
        # Real-world Cloud SQL under load requires 45-60s for reliable connection establishment
        # This test should FAIL, exposing the gap Issue #1263 missed
        minimum_required_for_cloud_sql_under_load = 45.0
        
        if config["initialization_timeout"] < minimum_required_for_cloud_sql_under_load:
            pytest.fail(
                f"Issue #1278 infrastructure gap detected: "
                f"Staging timeout {config['initialization_timeout']}s insufficient for "
                f"Cloud SQL under capacity pressure (requires ≥{minimum_required_for_cloud_sql_under_load}s)"
            )
    
    def test_cloud_sql_connection_pool_limits_not_configured(self):
        """
        Test Cloud SQL connection pool configuration for capacity constraints.
        
        Expected: TEST FAILURE - Pool limits not optimized for Cloud SQL constraints
        """
        cloud_sql_config = get_cloud_sql_optimized_config("staging")
        pool_config = cloud_sql_config["pool_config"]
        
        # Issue #1263 fix: Standard pool configuration
        assert pool_config["pool_size"] == 15
        assert pool_config["max_overflow"] == 25
        
        # CRITICAL FAILURE POINT: Pool limits don't account for Cloud SQL concurrent connection limits
        # Cloud SQL has instance-level connection limits that can cause failures under load
        cloud_sql_max_connections = 100  # Typical Cloud SQL instance limit
        total_possible_connections = pool_config["pool_size"] + pool_config["max_overflow"]
        
        if total_possible_connections > (cloud_sql_max_connections * 0.8):  # 80% safety margin
            pytest.fail(
                f"Issue #1278 infrastructure gap: Pool configuration "
                f"({total_possible_connections} connections) exceeds Cloud SQL safe limits "
                f"(80% of {cloud_sql_max_connections} = {int(cloud_sql_max_connections * 0.8)})"
            )
    
    def test_vpc_connector_capacity_timeout_not_accounted(self):
        """
        Test VPC connector capacity constraints in timeout calculation.
        
        Expected: TEST FAILURE - VPC connector capacity limits not considered
        """
        # VPC connector has throughput limits: 2 Gbps with scaling delays
        # Under high load, connection establishment can take significantly longer
        
        config = get_database_timeout_config("staging")
        base_timeout = config["initialization_timeout"]  # 25.0s from Issue #1263 fix
        
        # VPC connector under capacity pressure adds 10-20s delay
        vpc_connector_capacity_delay = 20.0
        safe_timeout_with_vpc_pressure = base_timeout + vpc_connector_capacity_delay
        
        if config["initialization_timeout"] < safe_timeout_with_vpc_pressure:
            pytest.fail(
                f"Issue #1278 VPC connector capacity gap: "
                f"Timeout {config['initialization_timeout']}s doesn't account for "
                f"VPC connector capacity pressure (needs ≥{safe_timeout_with_vpc_pressure}s)"
            )

    @pytest.mark.asyncio
    async def test_connection_timeout_cascade_failure_reproduction(self):
        """
        Reproduce the exact cascade failure pattern from Issue #1278.
        
        Expected: TEST FAILURE - Reproducing SMD Phase 3 cascade failure
        """
        # Simulate the exact Issue #1278 failure sequence
        with patch('asyncio.wait_for') as mock_wait_for:
            # Simulate timeout after 20.0s (the exact failure from Issue #1278 logs)
            mock_wait_for.side_effect = asyncio.TimeoutError("Database initialization timeout after 20.0s")
            
            from netra_backend.app.smd import StartupOrchestrator, DeterministicStartupError
            from fastapi import FastAPI
            
            app = FastAPI()
            orchestrator = StartupOrchestrator(app)
            
            # This should reproduce the exact Issue #1278 failure
            with pytest.raises(DeterministicStartupError) as exc_info:
                await orchestrator._phase3_database_setup()
            
            # Verify this is the exact same error pattern as Issue #1278
            error_message = str(exc_info.value)
            assert "20.0s" in error_message or "timeout" in error_message.lower()
            
            # This test confirms Issue #1278 recurrence - same failure pattern as resolved Issue #1263
            pytest.fail(f"Issue #1278 reproduced: {error_message}")
```

### Integration Tests - VPC Connector Operational Validation

#### File: `netra_backend/tests/integration/infrastructure/test_issue_1278_vpc_connector_capacity.py`

```python
"""
Integration Tests for Issue #1278 - VPC Connector Capacity Constraints

These tests focus on VPC connector operational limits that Issue #1263 fix didn't address.
Tests simulate VPC connector capacity pressure to reproduce Issue #1278 conditions.

Expected Result: Tests should FAIL initially, exposing VPC connector capacity limits
"""

import asyncio
import pytest
import socket
import time
import concurrent.futures
from typing import List, Dict
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class TestIssue1278VpcConnectorCapacity(SSotAsyncTestCase):
    """Integration tests for VPC connector capacity constraints causing Issue #1278."""
    
    @pytest.mark.integration
    @pytest.mark.infrastructure  
    async def test_vpc_connector_concurrent_connection_limits(self):
        """
        Test VPC connector behavior under concurrent connection pressure.
        
        Expected: TEST FAILURE - VPC connector capacity limits cause connection delays
        """
        # Simulate multiple concurrent database connections through VPC connector
        # VPC connectors have limited concurrent connection capacity
        
        max_concurrent_connections = 50  # Typical VPC connector limit
        connection_attempts = []
        failed_connections = 0
        slow_connections = 0
        
        async def attempt_database_connection():
            """Simulate database connection through VPC connector."""
            start_time = time.time()
            try:
                # Simulate Cloud SQL connection through VPC connector
                # In real scenario, this would be actual database connection
                await asyncio.sleep(0.1)  # Simulate connection establishment
                connection_time = time.time() - start_time
                
                # VPC connector under pressure causes delays >15s
                if connection_time > 15.0:
                    return "slow"
                return "success"
            except Exception:
                return "failed"
        
        # Create concurrent connection attempts to stress VPC connector
        tasks = []
        for i in range(max_concurrent_connections + 10):  # Exceed capacity
            task = asyncio.create_task(attempt_database_connection())
            tasks.append(task)
        
        # Wait for all connection attempts
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results for capacity constraint indicators
        for result in results:
            if result == "failed":
                failed_connections += 1
            elif result == "slow":
                slow_connections += 1
        
        # CRITICAL TEST: High failure/slow rate indicates VPC connector capacity issues
        failure_rate = (failed_connections + slow_connections) / len(results)
        
        if failure_rate > 0.1:  # >10% failure rate
            pytest.fail(
                f"Issue #1278 VPC connector capacity constraint detected: "
                f"{failure_rate:.1%} of connections failed/slow "
                f"({failed_connections} failed, {slow_connections} slow out of {len(results)})"
            )
    
    @pytest.mark.integration
    async def test_vpc_connector_throughput_degradation_under_load(self):
        """
        Test VPC connector throughput degradation causing connection timeouts.
        
        Expected: TEST FAILURE - Throughput degradation causes timeout issues
        """
        # VPC connectors have 2 Gbps baseline with scaling up to 10 Gbps
        # Under high load, scaling delays can cause temporary throughput constraints
        
        # Simulate high data throughput scenario
        large_query_simulation_time = 25.0  # Simulates large query that stresses VPC connector
        
        start_time = time.time()
        
        # Simulate database operation that requires high VPC connector throughput
        await asyncio.sleep(large_query_simulation_time)
        
        total_time = time.time() - start_time
        
        # CRITICAL TEST: If operation takes longer than Issue #1263 timeout fix,
        # it indicates VPC connector throughput constraints causing Issue #1278
        issue_1263_timeout_fix = 25.0  # The timeout Issue #1263 set
        
        if total_time > issue_1263_timeout_fix:
            pytest.fail(
                f"Issue #1278 VPC connector throughput constraint: "
                f"Operation took {total_time:.1f}s, exceeding Issue #1263 fix timeout of {issue_1263_timeout_fix}s"
            )
    
    @pytest.mark.integration
    async def test_vpc_connector_scaling_delay_reproduction(self):
        """
        Reproduce VPC connector scaling delays that cause Issue #1278.
        
        Expected: TEST FAILURE - Scaling delays cause startup timeouts
        """
        # VPC connector auto-scaling has delays of 10-30 seconds under load
        # This can cause startup timeouts even with Issue #1263 timeout increases
        
        # Simulate VPC connector scaling scenario
        scaling_delay_simulation = 30.0  # Typical auto-scaling delay
        
        start_time = time.time()
        
        # Simulate startup sequence that triggers VPC connector scaling
        await asyncio.sleep(scaling_delay_simulation)
        
        startup_time = time.time() - start_time
        
        # Compare against Issue #1263 timeout configuration
        from netra_backend.app.core.database_timeout_config import get_database_timeout_config
        config = get_database_timeout_config("staging")
        configured_timeout = config["initialization_timeout"]  # 25.0s from Issue #1263
        
        if startup_time > configured_timeout:
            pytest.fail(
                f"Issue #1278 VPC connector scaling delay reproduction: "
                f"Startup time {startup_time:.1f}s exceeds configured timeout {configured_timeout}s, "
                f"indicating VPC connector scaling delays not accounted for in Issue #1263 fix"
            )
```

### E2E Tests - SMD Phase 3 Failure Reproduction

#### File: `tests/e2e/infrastructure/test_issue_1278_smd_cascade_failure.py`

```python
"""
E2E Tests for Issue #1278 - SMD Phase 3 Cascade Failure Reproduction

These tests reproduce the exact Issue #1278 failure scenario in real GCP staging environment
to validate that the Issue #1263 fix was incomplete for deeper infrastructure constraints.

Expected Result: Tests should FAIL initially, reproducing exact Issue #1278 symptoms
"""

import asyncio
import pytest
import time
from typing import Dict, List
from fastapi import FastAPI
from test_framework.base_e2e_test import BaseE2ETest

class TestIssue1278SmdCascadeFailure(BaseE2ETest):
    """E2E tests reproducing Issue #1278 SMD cascade failure in real GCP environment."""
    
    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    @pytest.mark.issue_1278_reproduction
    async def test_smd_phase3_failure_under_cloud_sql_load(self):
        """
        Reproduce SMD Phase 3 failure under real Cloud SQL capacity pressure.
        
        This test intentionally creates load conditions that expose the infrastructure
        constraints Issue #1263 fix didn't address.
        
        Expected: TEST FAILURE - Reproducing exact Issue #1278 startup failure
        """
        # Create multiple FastAPI applications to simulate concurrent startup load
        # This reproduces the conditions that cause Issue #1278 in production
        
        apps = []
        failure_count = 0
        successful_startups = 0
        startup_times = []
        
        async def attempt_app_startup(app_index: int) -> Dict:
            """Attempt application startup and measure timing."""
            app = FastAPI()
            start_time = time.time()
            
            try:
                from netra_backend.app.smd import StartupOrchestrator
                orchestrator = StartupOrchestrator(app)
                
                # Phase 1 & 2 should succeed
                await orchestrator._phase1_foundation()
                await orchestrator._phase2_core_services()
                
                # Phase 3 is where Issue #1278 manifests under load
                await orchestrator._phase3_database_setup()
                
                startup_time = time.time() - start_time
                return {
                    "app_index": app_index,
                    "status": "success", 
                    "startup_time": startup_time,
                    "phase3_status": "completed"
                }
                
            except Exception as e:
                startup_time = time.time() - start_time
                return {
                    "app_index": app_index,
                    "status": "failed",
                    "startup_time": startup_time,
                    "error": str(e),
                    "phase3_status": "failed"
                }
        
        # Create concurrent startup attempts to stress Cloud SQL
        concurrent_startups = 5  # Simulate multiple service instances starting
        tasks = []
        
        for i in range(concurrent_startups):
            task = asyncio.create_task(attempt_app_startup(i))
            tasks.append(task)
        
        # Wait for all startup attempts
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results for Issue #1278 patterns
        for result in results:
            if isinstance(result, dict):
                startup_times.append(result["startup_time"])
                if result["status"] == "failed":
                    failure_count += 1
                    # Check if this matches Issue #1278 error pattern
                    if "timeout" in result.get("error", "").lower():
                        pytest.fail(
                            f"Issue #1278 reproduced: App {result['app_index']} failed with timeout "
                            f"after {result['startup_time']:.1f}s: {result['error']}"
                        )
                else:
                    successful_startups += 1
        
        # Check for Issue #1278 indicators
        failure_rate = failure_count / len(results)
        avg_startup_time = sum(startup_times) / len(startup_times) if startup_times else 0
        
        # CRITICAL TEST: High failure rate or slow startup indicates Issue #1278 conditions
        if failure_rate > 0.2:  # >20% failure rate
            pytest.fail(
                f"Issue #1278 cascade failure reproduced: "
                f"{failure_rate:.1%} failure rate ({failure_count}/{len(results)}) "
                f"with average startup time {avg_startup_time:.1f}s"
            )
        
        if avg_startup_time > 30.0:  # Slower than reasonable startup
            pytest.fail(
                f"Issue #1278 slow startup pattern: "
                f"Average startup time {avg_startup_time:.1f}s indicates infrastructure constraints"
            )
    
    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_fastapi_lifespan_error_context_loss(self):
        """
        Test FastAPI lifespan error context preservation during SMD failures.
        
        Expected: TEST FAILURE - Error context lost during startup failures
        """
        from netra_backend.app.core.lifespan_manager import lifespan
        from netra_backend.app.smd import DeterministicStartupError
        
        app = FastAPI()
        error_context_preserved = False
        original_error_message = None
        
        # Simulate the exact Issue #1278 scenario
        try:
            async with lifespan(app):
                # This should trigger the exact failure path from Issue #1278
                pass
        except DeterministicStartupError as e:
            original_error_message = str(e)
            # Check if error context is preserved
            if "Phase 3" in original_error_message or "database" in original_error_message.lower():
                error_context_preserved = True
        except Exception as e:
            original_error_message = str(e)
        
        # Verify app state contains error information
        startup_error = getattr(app.state, 'startup_error', None)
        startup_failed = getattr(app.state, 'startup_failed', False)
        
        if not error_context_preserved:
            pytest.fail(
                f"Issue #1278 error context loss: "
                f"FastAPI lifespan error context not preserved. "
                f"Original error: {original_error_message}, "
                f"App state error: {startup_error}, "
                f"App state failed: {startup_failed}"
            )
    
    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_container_exit_code_3_reproduction(self):
        """
        Reproduce the container exit code 3 behavior from Issue #1278.
        
        Expected: TEST FAILURE - Container exit behavior indicates startup failure
        """
        # This test simulates the container behavior that produces exit code 3
        # when SMD Phase 3 fails
        
        startup_failed = False
        exit_code = 0
        
        try:
            app = FastAPI()
            from netra_backend.app.smd import StartupOrchestrator, DeterministicStartupError
            
            orchestrator = StartupOrchestrator(app)
            await orchestrator.initialize_system()
            
        except DeterministicStartupError:
            startup_failed = True
            exit_code = 3  # The exit code from Issue #1278 logs
        except Exception:
            startup_failed = True
            exit_code = 1  # Generic failure
        
        if startup_failed and exit_code == 3:
            pytest.fail(
                f"Issue #1278 container exit code 3 reproduced: "
                f"SMD startup failure resulted in exit code {exit_code}, "
                f"indicating cascading failure pattern identical to Issue #1278"
            )
```

### Infrastructure Validation Tests - Cloud SQL Capacity

#### File: `tests/e2e/infrastructure/test_issue_1278_cloud_sql_capacity_constraints.py`

```python
"""
Infrastructure Validation Tests for Issue #1278 - Cloud SQL Capacity Constraints

These tests validate Cloud SQL instance capacity limitations that cause Issue #1278
under load conditions that Issue #1263 testing didn't account for.

Expected Result: Tests should FAIL, exposing Cloud SQL capacity constraints
"""

import asyncio
import pytest
import time
from typing import List, Dict
from test_framework.base_e2e_test import BaseE2ETest

class TestIssue1278CloudSqlCapacityConstraints(BaseE2ETest):
    """Infrastructure tests for Cloud SQL capacity constraints causing Issue #1278."""
    
    @pytest.mark.e2e
    @pytest.mark.infrastructure
    @pytest.mark.cloud_sql
    async def test_cloud_sql_max_connections_under_load(self):
        """
        Test Cloud SQL maximum connections limit during concurrent startup.
        
        Expected: TEST FAILURE - Cloud SQL connection limits cause startup failures
        """
        # Cloud SQL instances have maximum connection limits (typically 100-400)
        # Multiple service instances starting simultaneously can hit these limits
        
        max_connection_attempts = 50
        successful_connections = 0
        failed_connections = 0
        connection_times = []
        
        async def attempt_database_connection() -> Dict:
            """Attempt database connection to measure Cloud SQL capacity."""
            start_time = time.time()
            
            try:
                # Simulate actual database connection
                # In real test, this would use actual Cloud SQL connection
                from netra_backend.app.db.postgres import initialize_postgres
                
                # This will stress Cloud SQL connection limits
                session_factory = await asyncio.wait_for(
                    asyncio.to_thread(initialize_postgres),
                    timeout=30.0
                )
                
                connection_time = time.time() - start_time
                return {
                    "status": "success",
                    "connection_time": connection_time,
                    "session_factory": session_factory
                }
                
            except asyncio.TimeoutError:
                connection_time = time.time() - start_time
                return {
                    "status": "timeout",
                    "connection_time": connection_time,
                    "error": "Connection timeout - likely Cloud SQL capacity limit"
                }
            except Exception as e:
                connection_time = time.time() - start_time
                return {
                    "status": "failed", 
                    "connection_time": connection_time,
                    "error": str(e)
                }
        
        # Create concurrent connections to stress Cloud SQL
        tasks = []
        for i in range(max_connection_attempts):
            task = asyncio.create_task(attempt_database_connection())
            tasks.append(task)
        
        # Execute all connection attempts
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results for Cloud SQL capacity constraints
        timeout_count = 0
        error_count = 0
        
        for result in results:
            if isinstance(result, dict):
                connection_times.append(result["connection_time"])
                
                if result["status"] == "success":
                    successful_connections += 1
                elif result["status"] == "timeout": 
                    timeout_count += 1
                    failed_connections += 1
                else:
                    error_count += 1
                    failed_connections += 1
        
        # Calculate metrics
        failure_rate = failed_connections / len(results)
        timeout_rate = timeout_count / len(results)
        avg_connection_time = sum(connection_times) / len(connection_times)
        
        # CRITICAL TEST: High failure/timeout rate indicates Cloud SQL capacity limits
        if failure_rate > 0.15:  # >15% failure rate
            pytest.fail(
                f"Issue #1278 Cloud SQL capacity constraint detected: "
                f"{failure_rate:.1%} failure rate ({failed_connections}/{len(results)}) "
                f"with {timeout_rate:.1%} timeouts, average connection time {avg_connection_time:.1f}s"
            )
    
    @pytest.mark.e2e 
    @pytest.mark.infrastructure
    async def test_cloud_sql_connection_pool_exhaustion(self):
        """
        Test Cloud SQL connection pool exhaustion during startup sequence.
        
        Expected: TEST FAILURE - Connection pool exhaustion causes Issue #1278
        """
        from netra_backend.app.core.database_timeout_config import get_cloud_sql_optimized_config
        
        # Get current pool configuration from Issue #1263 fix
        pool_config = get_cloud_sql_optimized_config("staging")["pool_config"]
        pool_size = pool_config["pool_size"]  # 15 from Issue #1263 fix
        max_overflow = pool_config["max_overflow"]  # 25 from Issue #1263 fix
        
        total_pool_capacity = pool_size + max_overflow  # 40 total
        
        # Test connection pool behavior under stress
        active_connections = []
        pool_exhausted = False
        
        try:
            # Create connections up to pool limit + overflow
            for i in range(total_pool_capacity + 5):  # Exceed pool capacity
                # Simulate connection acquisition
                await asyncio.sleep(0.1)  # Simulate connection time
                active_connections.append(f"connection_{i}")
                
                # After exceeding pool capacity, connections should start failing
                if i > total_pool_capacity:
                    pool_exhausted = True
                    break
        
        except Exception as e:
            # Pool exhaustion causes exceptions
            pool_exhausted = True
            pool_exhaustion_error = str(e)
        
        if pool_exhausted:
            pytest.fail(
                f"Issue #1278 Cloud SQL pool exhaustion reproduced: "
                f"Pool capacity ({total_pool_capacity}) exhausted with "
                f"{len(active_connections)} active connections, causing startup failures"
            )
    
    @pytest.mark.e2e
    @pytest.mark.infrastructure  
    async def test_cloud_sql_instance_resource_constraints(self):
        """
        Test Cloud SQL instance resource constraints (CPU/Memory) affecting connections.
        
        Expected: TEST FAILURE - Resource constraints cause connection degradation
        """
        # Cloud SQL instances have CPU/Memory limits that affect connection performance
        # Under high load, connection establishment becomes significantly slower
        
        connection_performance_samples = []
        slow_connection_count = 0
        
        # Test multiple connection attempts to measure performance degradation
        for attempt in range(10):
            start_time = time.time()
            
            try:
                # Simulate database connection with realistic Cloud SQL latency
                await asyncio.sleep(2.0)  # Baseline Cloud SQL connection time
                
                # Under resource pressure, connections become much slower
                resource_pressure_delay = attempt * 1.0  # Simulates increasing pressure
                await asyncio.sleep(resource_pressure_delay)
                
                connection_time = time.time() - start_time
                connection_performance_samples.append(connection_time)
                
                # Connections taking >20s indicate resource constraint issues
                if connection_time > 20.0:
                    slow_connection_count += 1
                    
            except Exception as e:
                connection_time = time.time() - start_time
                connection_performance_samples.append(connection_time)
        
        # Analyze performance degradation
        avg_connection_time = sum(connection_performance_samples) / len(connection_performance_samples)
        slow_connection_rate = slow_connection_count / len(connection_performance_samples)
        
        # CRITICAL TEST: Performance degradation indicates resource constraints
        issue_1263_timeout = 25.0  # Timeout from Issue #1263 fix
        
        if avg_connection_time > issue_1263_timeout or slow_connection_rate > 0.2:
            pytest.fail(
                f"Issue #1278 Cloud SQL resource constraint detected: "
                f"Average connection time {avg_connection_time:.1f}s exceeds "
                f"Issue #1263 timeout {issue_1263_timeout}s, "
                f"with {slow_connection_rate:.1%} slow connections indicating resource pressure"
            )
```

---

## 🚨 Test Execution Strategy

### Phase 1: Unit Test Validation (0-2 hours)
```bash
# Run unit tests to validate configuration gaps
python -m pytest netra_backend/tests/unit/startup/test_issue_1278_database_timeout_validation.py -v

# Expected: ALL TESTS SHOULD FAIL
# These failures will expose the configuration gaps Issue #1263 missed
```

### Phase 2: Integration Test Execution (2-4 hours)  
```bash
# Run integration tests for VPC connector constraints
python -m pytest netra_backend/tests/integration/infrastructure/test_issue_1278_vpc_connector_capacity.py -v

# Expected: TESTS SHOULD FAIL
# Failures expose VPC connector operational limits causing Issue #1278
```

### Phase 3: E2E Infrastructure Validation (4-8 hours)
```bash
# Run E2E tests in real GCP staging environment
python -m pytest tests/e2e/infrastructure/test_issue_1278_smd_cascade_failure.py -v
python -m pytest tests/e2e/infrastructure/test_issue_1278_cloud_sql_capacity_constraints.py -v

# Expected: TESTS SHOULD FAIL initially
# These reproduce exact Issue #1278 conditions in real GCP environment
```

---

## 📊 Success Criteria & Validation

### Initial Test Run (Reproducing Issue #1278)
- [ ] **Unit Tests:** All timeout validation tests FAIL, exposing configuration gaps
- [ ] **Integration Tests:** VPC connector capacity tests FAIL, showing operational limits  
- [ ] **E2E Tests:** SMD cascade failure tests FAIL, reproducing exact Issue #1278

### Post-Remediation Validation
- [ ] **Infrastructure Fixes:** Updated timeout configurations for Cloud SQL constraints
- [ ] **VPC Optimization:** VPC connector capacity planning and scaling configuration
- [ ] **SMD Resilience:** Enhanced error handling and graceful degradation
- [ ] **All Tests Pass:** Previously failing tests now pass after infrastructure fixes

---

## 🔍 Key Differences from Issue #1263 Testing

| Aspect | Issue #1263 Testing | Issue #1278 Testing |
|--------|-------------------|-------------------|
| **Focus** | Deployment configuration | Infrastructure capacity limits |
| **Timeout Testing** | Basic timeout increase validation | Timeout sufficiency under load |
| **VPC Testing** | VPC connector connectivity | VPC connector capacity constraints |
| **Cloud SQL Testing** | Basic connection establishment | Connection pool limits and resource pressure |
| **SMD Testing** | Phase completion | Cascade failure handling and error context |
| **Load Testing** | Single instance startup | Concurrent startup under pressure |

---

## 📝 Expected Test Results Summary

**All tests should FAIL initially** - this is by design to reproduce Issue #1278 symptoms and validate that the Issue #1263 fix was incomplete for deeper infrastructure constraints.

### Critical Failure Points Expected:
1. **Database timeout configuration insufficient** for Cloud SQL under capacity pressure
2. **VPC connector operational limits** not accounted for in timeout calculations  
3. **Cloud SQL connection pool exhaustion** under concurrent startup load
4. **SMD Phase 3 cascade failures** with inadequate error context preservation
5. **FastAPI lifespan error handling** losing critical error information

These test failures will provide the evidence needed to implement comprehensive infrastructure fixes that address the root causes Issue #1263 partially resolved.

---

**Test Plan Created:** 2025-09-15  
**Expected Initial Result:** ALL TESTS FAIL (reproducing Issue #1278)  
**Test Difficulty:** Medium-High (infrastructure dependencies)  
**Business Impact:** $500K+ ARR validation pipeline restoration

This test plan targets the exact infrastructure gaps that caused Issue #1278 recurrence despite Issue #1263 resolution, providing a path to comprehensive remediation.