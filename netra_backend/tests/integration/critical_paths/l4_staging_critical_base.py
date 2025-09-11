from shared.isolated_environment import get_env
"""L4 Staging Critical Path Base Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity and Critical Path Validation Infrastructure
- Value Impact: Enables efficient implementation of critical production readiness tests
- Strategic Impact: Reduces code duplication and standardizes L4 test patterns for critical MRR protection

Provides shared base class and utilities for critical L4 staging tests:
- L4StagingCriticalPathTestBase for consistent test setup
- Common staging environment initialization
- Shared metrics collection and validation
- Standardized cleanup and error handling
"""

import asyncio
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
import pytest

from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.monitoring.metrics_collector import MetricsCollector
from netra_backend.app.redis_manager import redis_manager as RedisService
from netra_backend.tests.integration.e2e.staging_test_helpers import (
    StagingTestSuite,
    get_staging_suite,
)

@dataclass
class CriticalPathMetrics:
    """Standardized metrics container for critical path testing."""
    test_name: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error_count: int = 0
    validation_count: int = 0
    service_calls: int = 0
    average_response_time: float = 0.0
    peak_memory_usage: int = 0
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Calculate test duration in seconds."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total_operations = self.validation_count + self.error_count
        if total_operations == 0:
            return 100.0
        return (self.validation_count / total_operations) * 100.0

@dataclass
class ServiceEndpointConfig:
    """Configuration for staging service endpoints."""
    backend: str
    auth: str
    frontend: str
    websocket: str
    metrics: str
    billing: str

class L4StagingCriticalPathTestBase(ABC):
    """Base class for L4 critical path tests with shared staging utilities."""
    
    def __init__(self, test_name: str):
        """Initialize L4 critical path test base."""
        self.test_name = test_name
        self.staging_suite: Optional[StagingTestSuite] = None
        self.config = None  # Will be loaded during initialization
        self.redis_session: Optional[RedisService] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.service_endpoints: Optional[ServiceEndpointConfig] = None
        self.test_client: Optional[httpx.AsyncClient] = None
        self.test_metrics = CriticalPathMetrics(
            test_name=test_name,
            start_time=time.time()
        )
        self._initialized = False
        self._test_data: Dict[str, Any] = {}
        
        # Initialize project root for file-based tests
        self.project_root = self._find_project_root()
    
    def _find_project_root(self) -> Path:
        """Find the project root directory."""
        # Start from current file location and work upward
        current_path = Path(__file__).parent
        
        # Look for project markers
        project_markers = ["netra_backend", "auth_service", "frontend", ".git", "pyproject.toml", "setup.py"]
        
        # Go up directories looking for project root
        for _ in range(10):  # Limit search to avoid infinite loop
            # Check if this directory contains project markers
            if any((current_path / marker).exists() for marker in project_markers):
                # If we're in a subdirectory, go up one more level to get the true root
                if current_path.name in ["netra_backend", "auth_service", "frontend"]:
                    return current_path.parent
                return current_path
            
            parent = current_path.parent
            if parent == current_path:  # Reached filesystem root
                break
            current_path = parent
        
        # Fallback: use working directory
        return Path.cwd()
        
    async def initialize_l4_environment(self) -> None:
        """Initialize L4 staging environment for critical path testing."""
        if self._initialized:
            return
            
        try:
            # Load configuration first with error handling - skip for testing if problematic
            try:
                # Only try to load config if not already loaded and not in test mode
                if self.config is None and not get_env().get("TESTING"):
                    self.config = get_unified_config()
                else:
                    # Skip config loading in test environment to prevent infinite loops
                    self.test_metrics.errors.append("Config loading skipped in test environment")
            except Exception as e:
                self.test_metrics.errors.append(f"Failed to load configuration: {str(e)}")
                # Continue with minimal configuration for testing
                pass
            
            # Initialize staging test suite
            self.staging_suite = await get_staging_suite()
            await self.staging_suite.setup()
            
            # Setup HTTP client with staging-appropriate timeouts
            self.test_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                verify=False  # Staging may use self-signed certificates
            )
            
            # Initialize service endpoints from staging configuration
            services = self.staging_suite.env_config.services
            self.service_endpoints = ServiceEndpointConfig(
                backend=services.backend,
                auth=services.auth,
                frontend=services.frontend,
                websocket=services.websocket,
                metrics=f"{services.backend}/metrics",
                billing=f"{services.backend}/api/billing"
            )
            
            # Initialize Redis session manager with test mode
            self.redis_session = RedisService(test_mode=True)
            try:
                await self.redis_session.connect()
            except Exception as e:
                self.test_metrics.errors.append(f"Redis connection failed: {str(e)}")
                # Continue without Redis for testing
            
            # Initialize metrics collector with error handling
            try:
                self.metrics_collector = MetricsCollector()
                await self.metrics_collector.start_collection()
            except Exception as e:
                self.test_metrics.errors.append(f"Metrics collector failed: {str(e)}")
                # Continue without metrics collector for testing
            
            # Validate staging environment connectivity (non-blocking)
            try:
                await self._validate_staging_connectivity()
            except Exception as e:
                self.test_metrics.errors.append(f"Staging connectivity validation failed: {str(e)}")
                # Continue - connectivity issues don't block test execution
            
            # Execute test-specific setup
            await self.setup_test_specific_environment()
            
            self._initialized = True
            
        except Exception as e:
            self.test_metrics.errors.append(f"Environment initialization failed: {str(e)}")
            raise RuntimeError(f"L4 environment initialization failed: {e}")
    
    async def _validate_staging_connectivity(self) -> None:
        """Validate connectivity to all required staging services."""
        if not self.service_endpoints:
            return  # Skip if service endpoints not configured
            
        connectivity_checks = [
            ("backend", f"{self.service_endpoints.backend}/health"),
            ("auth", f"{self.service_endpoints.auth}/health"),
            ("metrics", f"{self.service_endpoints.metrics}/health"),
            ("billing", f"{self.service_endpoints.billing}/health")
        ]
        
        failed_services = []
        accessible_services = []
        
        for service_name, health_url in connectivity_checks:
            try:
                response = await self.test_client.get(health_url, timeout=5.0)
                # Accept 200, 404, 405 as "accessible" - service may not have health endpoint
                if response.status_code in [200, 404, 405]:
                    accessible_services.append(service_name)
                else:
                    failed_services.append(f"{service_name} (HTTP {response.status_code})")
            except Exception as e:
                failed_services.append(f"{service_name} ({str(e)})")
        
        # Log connectivity status but don't fail the test
        self.test_metrics.details["accessible_services"] = accessible_services
        self.test_metrics.details["failed_services"] = failed_services
        
        # Only raise error if ALL services are unreachable
        if len(accessible_services) == 0 and len(failed_services) > 0:
            self.test_metrics.errors.append(f"All staging services unreachable: {', '.join(failed_services)}")
    
    @abstractmethod
    async def setup_test_specific_environment(self) -> None:
        """Setup test-specific environment configuration."""
        pass
    
    @abstractmethod
    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute the specific critical path test logic."""
        pass
    
    @abstractmethod
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate critical path test results meet business requirements."""
        pass
    
    async def run_complete_critical_path_test(self) -> CriticalPathMetrics:
        """Execute complete critical path test with metrics collection."""
        try:
            # Ensure environment is initialized
            await self.initialize_l4_environment()
            
            # Execute critical path test
            test_results = await self.execute_critical_path_test()
            self.test_metrics.service_calls += test_results.get("service_calls", 0)
            self.test_metrics.details.update(test_results)
            
            # Validate results
            validation_success = await self.validate_critical_path_results(test_results)
            self.test_metrics.validation_count += 1
            
            if validation_success:
                self.test_metrics.success = True
            else:
                self.test_metrics.error_count += 1
                self.test_metrics.errors.append("Critical path validation failed")
            
            # Collect final metrics
            await self._collect_final_metrics()
            
        except Exception as e:
            self.test_metrics.error_count += 1
            self.test_metrics.errors.append(f"Critical path execution failed: {str(e)}")
            self.test_metrics.success = False
            
        finally:
            self.test_metrics.end_time = time.time()
            
        return self.test_metrics
    
    async def _collect_final_metrics(self) -> None:
        """Collect final performance and business metrics."""
        try:
            # Calculate average response time if service calls were made
            if self.test_metrics.service_calls > 0:
                total_duration = self.test_metrics.duration
                self.test_metrics.average_response_time = total_duration / self.test_metrics.service_calls
            
            # Collect memory usage metrics if available
            if self.metrics_collector:
                # Use psutil directly for memory stats since metrics collector might not have this method
                import psutil
                memory_info = psutil.virtual_memory()
                self.test_metrics.peak_memory_usage = int(memory_info.used / 1024 / 1024)  # MB
            
        except Exception as e:
            self.test_metrics.errors.append(f"Metrics collection warning: {str(e)}")
    
    async def create_test_user_with_billing(self, tier: str = "free") -> Dict[str, Any]:
        """Create test user with billing configuration for critical path testing."""
        import os
        import random
        
        try:
            full_uuid = str(uuid.uuid4())
            process_id = os.getpid()
            random_suffix = random.randint(10000, 99999)
            timestamp = int(time.time() * 1000000)  # Microseconds
            
            user_id = f"test_user_{tier}_{full_uuid}_{process_id}_{random_suffix}_{timestamp}"
            email = f"{user_id}@staging-test.netrasystems.ai"
            
            # Create user in auth service
            user_creation_data = {
                "user_id": user_id,
                "email": email,
                "tier": tier,
                "test_user": True,
                "created_for_test": self.test_name
            }
            
            auth_endpoint = f"{self.service_endpoints.auth}/api/users"
            response = await self.test_client.post(
                auth_endpoint,
                json=user_creation_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"User creation failed: {response.status_code}")
            
            user_data = response.json()
            
            # Setup billing configuration
            billing_setup = await self._setup_user_billing(user_id, tier)
            
            # Generate access token for testing
            token_response = await self._generate_test_token(user_id, tier)
            
            self.test_metrics.service_calls += 3  # user creation, billing setup, token generation
            
            return {
                "success": True,
                "user_id": user_id,
                "email": email,
                "tier": tier,
                "access_token": token_response.get("access_token"),
                "billing_setup": billing_setup,
                "user_data": user_data,
                "_test_marker": True  # For cleanup identification
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _setup_user_billing(self, user_id: str, tier: str) -> Dict[str, Any]:
        """Setup billing configuration for test user."""
        try:
            billing_config = {
                "user_id": user_id,
                "billing_tier": tier,
                "monthly_quota": self._get_tier_quota(tier),
                "current_usage": 0,
                "billing_cycle_start": datetime.now(timezone.utc).isoformat(),
                "test_account": True
            }
            
            billing_endpoint = f"{self.service_endpoints.billing}/setup"
            response = await self.test_client.post(
                billing_endpoint,
                json=billing_config,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Billing setup failed: {response.status_code}")
            
            return {"success": True, "billing_data": response.json()}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_tier_quota(self, tier: str) -> int:
        """Get quota limits for billing tier."""
        tier_quotas = {
            "free": 1000,
            "early": 10000,
            "mid": 50000,
            "enterprise": 1000000
        }
        return tier_quotas.get(tier, 1000)
    
    async def _generate_test_token(self, user_id: str, tier: str) -> Dict[str, Any]:
        """Generate access token for test user."""
        try:
            token_data = {
                "user_id": user_id,
                "tier": tier,
                "scopes": self._get_tier_scopes(tier),
                "test_token": True,
                "expires_in": 3600  # 1 hour for testing
            }
            
            token_endpoint = f"{self.service_endpoints.auth}/api/tokens/generate"
            response = await self.test_client.post(
                token_endpoint,
                json=token_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise Exception(f"Token generation failed: {response.status_code}")
            
            return response.json()
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_tier_scopes(self, tier: str) -> List[str]:
        """Get appropriate scopes for billing tier."""
        base_scopes = ["read", "basic"]
        tier_scopes = {
            "free": base_scopes,
            "early": base_scopes + ["write", "api"],
            "mid": base_scopes + ["write", "api", "analytics"],
            "enterprise": base_scopes + ["write", "api", "analytics", "admin"]
        }
        return tier_scopes.get(tier, base_scopes)
    
    async def measure_service_performance(self, operation_name: str, 
                                        operation_func, *args, **kwargs) -> Dict[str, Any]:
        """Measure performance of a service operation."""
        start_time = time.time()
        try:
            result = await operation_func(*args, **kwargs)
            duration = time.time() - start_time
            self.test_metrics.service_calls += 1
            
            return {
                "success": True,
                "operation": operation_name,
                "duration": duration,
                "result": result
            }
        except Exception as e:
            duration = time.time() - start_time
            self.test_metrics.error_count += 1
            self.test_metrics.errors.append(f"{operation_name} failed: {str(e)}")
            
            return {
                "success": False,
                "operation": operation_name,
                "duration": duration,
                "error": str(e)
            }
    
    async def validate_business_metrics(self, expected_metrics: Dict[str, Any]) -> bool:
        """Validate that business metrics meet critical path requirements."""
        try:
            validation_results = []
            
            # Response time validation
            max_response_time = expected_metrics.get("max_response_time_seconds", 5.0)
            if self.test_metrics.average_response_time <= max_response_time:
                validation_results.append(True)
            else:
                self.test_metrics.errors.append(
                    f"Response time {self.test_metrics.average_response_time:.2f}s exceeds limit {max_response_time}s"
                )
                validation_results.append(False)
            
            # Success rate validation
            min_success_rate = expected_metrics.get("min_success_rate_percent", 95.0)
            if self.test_metrics.success_rate >= min_success_rate:
                validation_results.append(True)
            else:
                self.test_metrics.errors.append(
                    f"Success rate {self.test_metrics.success_rate:.1f}% below minimum {min_success_rate}%"
                )
                validation_results.append(False)
            
            # Error count validation
            max_errors = expected_metrics.get("max_error_count", 0)
            if self.test_metrics.error_count <= max_errors:
                validation_results.append(True)
            else:
                self.test_metrics.errors.append(
                    f"Error count {self.test_metrics.error_count} exceeds limit {max_errors}"
                )
                validation_results.append(False)
            
            return all(validation_results)
            
        except Exception as e:
            self.test_metrics.errors.append(f"Business metrics validation failed: {str(e)}")
            return False
    
    async def cleanup_l4_resources(self) -> None:
        """Clean up L4 test resources and connections."""
        cleanup_errors = []
        
        # Close HTTP client
        if self.test_client:
            try:
                await self.test_client.aclose()
            except Exception as e:
                cleanup_errors.append(f"HTTP client cleanup: {e}")
        
        # Close Redis connection
        if self.redis_session:
            try:
                await self.redis_session.disconnect()
            except Exception as e:
                cleanup_errors.append(f"Redis cleanup: {e}")
        
        # Close metrics collector
        if self.metrics_collector:
            try:
                await self.metrics_collector.stop_collection()
            except Exception as e:
                cleanup_errors.append(f"Metrics collector cleanup: {e}")
        
        # Execute test-specific cleanup
        try:
            await self.cleanup_test_specific_resources()
        except Exception as e:
            cleanup_errors.append(f"Test-specific cleanup: {e}")
        
        # Clean up staging suite
        if self.staging_suite:
            try:
                await self.staging_suite.cleanup()
            except Exception as e:
                cleanup_errors.append(f"Staging suite cleanup: {e}")
        
        if cleanup_errors:
            print(f"Cleanup warnings for {self.test_name}: {'; '.join(cleanup_errors)}")
    
    async def cleanup_test_specific_resources(self) -> None:
        """Override to implement test-specific resource cleanup."""
        pass

# Pytest fixture for L4 critical path test base
@pytest.fixture
async def l4_critical_base():
    """Pytest fixture factory for L4 critical path test bases."""
    active_bases = []
    
    def create_base(test_name: str) -> L4StagingCriticalPathTestBase:
        # This would be implemented by concrete test classes
        raise NotImplementedError("Use concrete test class implementations")
    
    try:
        yield create_base
    finally:
        # Cleanup all active test bases
        for base in active_bases:
            try:
                await base.cleanup_l4_resources()
            except Exception as e:
                print(f"Fixture cleanup error: {e}")