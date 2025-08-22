"""Rate Limiting Under Load Protection L4 Critical Test

Business Value Justification (BVJ):
- Segment: All tiers (platform stability foundation)
- Business Goal: Ensure system stability and fair resource allocation under high load
- Value Impact: Protects $30K+ MRR by preventing system overload and ensuring service availability
- Strategic Impact: Critical for enterprise SLA compliance, system stability, and preventing abuse

Critical Path:
Normal load baseline -> Gradual load increase -> Rate limit enforcement -> 
Load spike simulation -> Fair resource allocation -> System recovery validation

Coverage: API rate limiting, per-user quotas, burst protection, graceful degradation
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import statistics
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import pytest

from netra_backend.tests.integration.critical_paths.l4_staging_critical_base import (
    CriticalPathMetrics,
    L4StagingCriticalPathTestBase,
)

@dataclass
class LoadTestScenario:
    """Load testing scenario configuration."""
    name: str
    concurrent_users: int
    requests_per_user: int
    request_interval_seconds: float
    expected_success_rate: float
    tier: str

@dataclass
class RateLimitTestResult:
    """Result container for rate limit testing."""
    user_id: str
    tier: str
    total_requests: int
    successful_requests: int
    rate_limited_requests: int
    average_response_time: float
    max_response_time: float
    rate_limit_enforced: bool

class RateLimitingLoadL4Test(L4StagingCriticalPathTestBase):
    """L4 test for rate limiting under load in staging environment."""
    
    def __init__(self):
        super().__init__("Rate Limiting Under Load Protection")
        self.load_scenarios: List[LoadTestScenario] = []
        self.test_users: Dict[str, Dict] = {}
        self.load_test_results: List[RateLimitTestResult] = []
        self.baseline_metrics: Dict[str, float] = {}
        
    async def setup_test_specific_environment(self) -> None:
        """Setup rate limiting specific test environment."""
        # Define load test scenarios for different tiers
        self.load_scenarios = [
            LoadTestScenario(
                name="free_tier_burst",
                concurrent_users=10,
                requests_per_user=20,
                request_interval_seconds=0.1,
                expected_success_rate=0.3,  # Free tier should be heavily rate limited
                tier="free"
            ),
            LoadTestScenario(
                name="early_tier_moderate",
                concurrent_users=5,
                requests_per_user=30,
                request_interval_seconds=0.2,
                expected_success_rate=0.7,  # Early tier moderate rate limiting
                tier="early"
            ),
            LoadTestScenario(
                name="mid_tier_sustained",
                concurrent_users=8,
                requests_per_user=50,
                request_interval_seconds=0.15,
                expected_success_rate=0.85,  # Mid tier higher success rate
                tier="mid"
            ),
            LoadTestScenario(
                name="enterprise_high_volume",
                concurrent_users=15,
                requests_per_user=100,
                request_interval_seconds=0.05,
                expected_success_rate=0.95,  # Enterprise tier minimal rate limiting
                tier="enterprise"
            )
        ]
        
        # Validate rate limiting service configuration
        await self._validate_rate_limiting_configuration()
    
    async def _validate_rate_limiting_configuration(self) -> None:
        """Validate rate limiting service is properly configured."""
        try:
            # Check rate limiting configuration endpoint
            config_endpoint = f"{self.service_endpoints.backend}/admin/rate-limits/config"
            response = await self.test_client.get(config_endpoint)
            
            if response.status_code != 200:
                raise RuntimeError(f"Rate limiting config unavailable: {response.status_code}")
            
            config_data = response.json()
            
            # Validate required rate limit configurations exist
            required_configs = ["per_user_limits", "tier_based_limits", "burst_protection"]
            missing_configs = [config for config in required_configs if config not in config_data]
            
            if missing_configs:
                raise RuntimeError(f"Missing rate limit configurations: {missing_configs}")
            
        except Exception as e:
            raise RuntimeError(f"Rate limiting validation failed: {e}")
    
    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute rate limiting under load critical path test."""
        test_results = {
            "phase_1_baseline": None,
            "phase_2_user_setup": None,
            "phase_3_gradual_load": None,
            "phase_4_burst_protection": None,
            "phase_5_fair_allocation": None,
            "phase_6_recovery_validation": None,
            "service_calls": 0
        }
        
        try:
            # Phase 1: Establish baseline performance metrics
            baseline_result = await self._establish_baseline_metrics()
            test_results["phase_1_baseline"] = baseline_result
            test_results["service_calls"] += baseline_result.get("service_calls", 0)
            
            if not baseline_result["success"]:
                return test_results
            
            # Phase 2: Setup users for each tier
            user_setup_result = await self._setup_tier_users_for_load_testing()
            test_results["phase_2_user_setup"] = user_setup_result
            test_results["service_calls"] += user_setup_result.get("service_calls", 0)
            
            if not user_setup_result["success"]:
                return test_results
            
            # Phase 3: Execute gradual load increase test
            gradual_load_result = await self._execute_gradual_load_test()
            test_results["phase_3_gradual_load"] = gradual_load_result
            test_results["service_calls"] += gradual_load_result.get("service_calls", 0)
            
            # Phase 4: Test burst protection mechanisms
            burst_protection_result = await self._test_burst_protection()
            test_results["phase_4_burst_protection"] = burst_protection_result
            test_results["service_calls"] += burst_protection_result.get("service_calls", 0)
            
            # Phase 5: Validate fair resource allocation
            fair_allocation_result = await self._validate_fair_resource_allocation()
            test_results["phase_5_fair_allocation"] = fair_allocation_result
            test_results["service_calls"] += fair_allocation_result.get("service_calls", 0)
            
            # Phase 6: Validate system recovery after load
            recovery_result = await self._validate_system_recovery()
            test_results["phase_6_recovery_validation"] = recovery_result
            test_results["service_calls"] += recovery_result.get("service_calls", 0)
            
            return test_results
            
        except Exception as e:
            return {"success": False, "error": str(e), "test_results": test_results}
    
    async def _establish_baseline_metrics(self) -> Dict[str, Any]:
        """Establish baseline performance metrics under normal load."""
        try:
            # Create a single test user for baseline measurement
            baseline_user = await self.create_test_user_with_billing("mid")
            
            if not baseline_user["success"]:
                return {"success": False, "error": "Failed to create baseline user"}
            
            # Execute baseline requests to measure normal performance
            baseline_requests = 10
            response_times = []
            successful_requests = 0
            
            headers = {
                "Authorization": f"Bearer {baseline_user['access_token']}",
                "Content-Type": "application/json"
            }
            
            for i in range(baseline_requests):
                start_time = time.time()
                
                try:
                    test_request = {
                        "operation_type": "baseline_test",
                        "user_id": baseline_user["user_id"],
                        "request_id": f"baseline_{i}"
                    }
                    
                    response = await self.test_client.post(
                        f"{self.service_endpoints.backend}/api/ai/execute",
                        json=test_request,
                        headers=headers
                    )
                    
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                    
                    if response.status_code == 200:
                        successful_requests += 1
                    
                    # Small delay between baseline requests
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    response_times.append(time.time() - start_time)
            
            # Calculate baseline metrics
            self.baseline_metrics = {
                "average_response_time": statistics.mean(response_times),
                "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 5 else max(response_times),
                "success_rate": successful_requests / baseline_requests,
                "baseline_established_at": time.time()
            }
            
            return {
                "success": successful_requests >= baseline_requests * 0.9,
                "baseline_metrics": self.baseline_metrics,
                "total_requests": baseline_requests,
                "successful_requests": successful_requests,
                "service_calls": baseline_requests
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _setup_tier_users_for_load_testing(self) -> Dict[str, Any]:
        """Setup users for each tier for load testing."""
        try:
            setup_count = 0
            
            for scenario in self.load_scenarios:
                tier_users = []
                
                # Create multiple users per tier for concurrent testing
                for i in range(scenario.concurrent_users):
                    user_data = await self.create_test_user_with_billing(scenario.tier)
                    
                    if user_data["success"]:
                        tier_users.append(user_data)
                        setup_count += 1
                
                self.test_users[scenario.tier] = tier_users
            
            total_expected = sum(scenario.concurrent_users for scenario in self.load_scenarios)
            
            return {
                "success": setup_count >= total_expected * 0.8,
                "total_users_created": setup_count,
                "expected_users": total_expected,
                "tier_breakdown": {tier: len(users) for tier, users in self.test_users.items()},
                "service_calls": setup_count * 2  # user creation + billing setup
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _execute_gradual_load_test(self) -> Dict[str, Any]:
        """Execute gradual load increase test across all tiers."""
        try:
            load_test_tasks = []
            
            # Launch concurrent load tests for each tier
            for scenario in self.load_scenarios:
                tier_users = self.test_users.get(scenario.tier, [])
                
                if tier_users:
                    # Create load test task for this tier
                    tier_task = self._execute_tier_load_test(scenario, tier_users)
                    load_test_tasks.append(tier_task)
            
            # Execute all tier load tests concurrently
            tier_results = await asyncio.gather(*load_test_tasks, return_exceptions=True)
            
            # Process results
            successful_tier_tests = []
            total_requests = 0
            total_service_calls = 0
            
            for i, result in enumerate(tier_results):
                if isinstance(result, Exception):
                    continue
                
                if result.get("success", False):
                    successful_tier_tests.append(result)
                
                total_requests += result.get("total_requests", 0)
                total_service_calls += result.get("service_calls", 0)
                
                # Store results for validation
                self.load_test_results.extend(result.get("user_results", []))
            
            return {
                "success": len(successful_tier_tests) >= len(self.load_scenarios) * 0.8,
                "total_tier_tests": len(self.load_scenarios),
                "successful_tier_tests": len(successful_tier_tests),
                "total_requests": total_requests,
                "tier_results": successful_tier_tests,
                "service_calls": total_service_calls
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _execute_tier_load_test(self, scenario: LoadTestScenario, 
                                    tier_users: List[Dict]) -> Dict[str, Any]:
        """Execute load test for specific tier."""
        try:
            # Create concurrent tasks for all users in this tier
            user_tasks = []
            
            for user_data in tier_users:
                user_task = self._execute_user_load_test(user_data, scenario)
                user_tasks.append(user_task)
            
            # Execute all user load tests concurrently
            user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
            
            # Process user results
            successful_user_results = []
            total_requests = 0
            total_service_calls = 0
            
            for result in user_results:
                if isinstance(result, Exception):
                    continue
                
                if result.get("success", False):
                    successful_user_results.append(result["user_result"])
                
                total_requests += result.get("total_requests", 0)
                total_service_calls += result.get("service_calls", 0)
            
            # Calculate tier-level metrics
            tier_success_rate = len(successful_user_results) / len(tier_users) if tier_users else 0
            
            return {
                "success": tier_success_rate >= 0.8,
                "scenario": scenario.name,
                "tier": scenario.tier,
                "total_users": len(tier_users),
                "successful_users": len(successful_user_results),
                "total_requests": total_requests,
                "user_results": successful_user_results,
                "service_calls": total_service_calls
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _execute_user_load_test(self, user_data: Dict, 
                                    scenario: LoadTestScenario) -> Dict[str, Any]:
        """Execute load test for individual user."""
        try:
            user_id = user_data["user_id"]
            access_token = user_data["access_token"]
            
            # Track user request metrics
            response_times = []
            successful_requests = 0
            rate_limited_requests = 0
            total_requests = scenario.requests_per_user
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Execute requests according to scenario
            for i in range(total_requests):
                start_time = time.time()
                
                try:
                    request_data = {
                        "operation_type": "load_test",
                        "user_id": user_id,
                        "tier": scenario.tier,
                        "request_id": f"{scenario.name}_{user_id}_{i}",
                        "scenario": scenario.name
                    }
                    
                    response = await self.test_client.post(
                        f"{self.service_endpoints.backend}/api/ai/execute",
                        json=request_data,
                        headers=headers
                    )
                    
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                    
                    if response.status_code == 200:
                        successful_requests += 1
                    elif response.status_code == 429:  # Rate limited
                        rate_limited_requests += 1
                    
                    # Wait according to scenario interval
                    await asyncio.sleep(scenario.request_interval_seconds)
                    
                except Exception as e:
                    response_times.append(time.time() - start_time)
            
            # Calculate user metrics
            average_response_time = statistics.mean(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            actual_success_rate = successful_requests / total_requests
            
            # Determine if rate limiting was properly enforced
            rate_limit_enforced = rate_limited_requests > 0 or actual_success_rate < scenario.expected_success_rate * 1.1
            
            user_result = RateLimitTestResult(
                user_id=user_id,
                tier=scenario.tier,
                total_requests=total_requests,
                successful_requests=successful_requests,
                rate_limited_requests=rate_limited_requests,
                average_response_time=average_response_time,
                max_response_time=max_response_time,
                rate_limit_enforced=rate_limit_enforced
            )
            
            return {
                "success": True,
                "user_result": user_result,
                "total_requests": total_requests,
                "service_calls": total_requests
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _test_burst_protection(self) -> Dict[str, Any]:
        """Test burst protection mechanisms."""
        try:
            burst_test_results = []
            
            # Test burst protection for each tier
            for tier, users in self.test_users.items():
                if not users:
                    continue
                
                # Select one user for burst testing
                test_user = users[0]
                
                burst_result = await self._execute_burst_test(test_user, tier)
                burst_test_results.append(burst_result)
            
            successful_burst_tests = [r for r in burst_test_results if r.get("success", False)]
            
            return {
                "success": len(successful_burst_tests) >= len(burst_test_results) * 0.8,
                "total_burst_tests": len(burst_test_results),
                "successful_burst_tests": len(successful_burst_tests),
                "burst_results": burst_test_results,
                "service_calls": sum(r.get("service_calls", 0) for r in burst_test_results)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _execute_burst_test(self, user_data: Dict, tier: str) -> Dict[str, Any]:
        """Execute burst test for specific user."""
        try:
            user_id = user_data["user_id"]
            access_token = user_data["access_token"]
            
            # Send rapid burst of requests
            burst_size = 50  # Large number of simultaneous requests
            burst_tasks = []
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Create all burst requests simultaneously
            for i in range(burst_size):
                request_data = {
                    "operation_type": "burst_test",
                    "user_id": user_id,
                    "tier": tier,
                    "burst_request_id": f"burst_{user_id}_{i}"
                }
                
                task = self.test_client.post(
                    f"{self.service_endpoints.backend}/api/ai/execute",
                    json=request_data,
                    headers=headers
                )
                burst_tasks.append(task)
            
            # Execute all requests simultaneously
            start_time = time.time()
            responses = await asyncio.gather(*burst_tasks, return_exceptions=True)
            burst_duration = time.time() - start_time
            
            # Analyze burst response patterns
            successful_responses = 0
            rate_limited_responses = 0
            error_responses = 0
            
            for response in responses:
                if isinstance(response, Exception):
                    error_responses += 1
                elif hasattr(response, 'status_code'):
                    if response.status_code == 200:
                        successful_responses += 1
                    elif response.status_code == 429:
                        rate_limited_responses += 1
                    else:
                        error_responses += 1
            
            # Validate burst protection effectiveness
            burst_protection_effective = (
                rate_limited_responses > burst_size * 0.3 or  # At least 30% rate limited
                successful_responses < burst_size * 0.7       # Less than 70% succeeded
            )
            
            return {
                "success": burst_protection_effective,
                "user_id": user_id,
                "tier": tier,
                "burst_size": burst_size,
                "successful_responses": successful_responses,
                "rate_limited_responses": rate_limited_responses,
                "error_responses": error_responses,
                "burst_duration": burst_duration,
                "burst_protection_effective": burst_protection_effective,
                "service_calls": burst_size
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _validate_fair_resource_allocation(self) -> Dict[str, Any]:
        """Validate that resources are fairly allocated across tiers."""
        try:
            # Analyze load test results for fair allocation
            tier_performance = {}
            
            for result in self.load_test_results:
                tier = result.tier
                if tier not in tier_performance:
                    tier_performance[tier] = {
                        "success_rates": [],
                        "response_times": [],
                        "rate_limited_counts": []
                    }
                
                success_rate = result.successful_requests / result.total_requests
                tier_performance[tier]["success_rates"].append(success_rate)
                tier_performance[tier]["response_times"].append(result.average_response_time)
                tier_performance[tier]["rate_limited_counts"].append(result.rate_limited_requests)
            
            # Calculate tier averages
            tier_averages = {}
            for tier, performance in tier_performance.items():
                tier_averages[tier] = {
                    "avg_success_rate": statistics.mean(performance["success_rates"]),
                    "avg_response_time": statistics.mean(performance["response_times"]),
                    "avg_rate_limited": statistics.mean(performance["rate_limited_counts"])
                }
            
            # Validate fair allocation expectations
            allocation_validations = []
            
            # Enterprise should have highest success rate
            if "enterprise" in tier_averages and "free" in tier_averages:
                enterprise_success = tier_averages["enterprise"]["avg_success_rate"]
                free_success = tier_averages["free"]["avg_success_rate"]
                
                allocation_validations.append({
                    "validation": "enterprise_higher_success_than_free",
                    "success": enterprise_success > free_success,
                    "enterprise_rate": enterprise_success,
                    "free_rate": free_success
                })
            
            # Mid tier should outperform early tier
            if "mid" in tier_averages and "early" in tier_averages:
                mid_success = tier_averages["mid"]["avg_success_rate"]
                early_success = tier_averages["early"]["avg_success_rate"]
                
                allocation_validations.append({
                    "validation": "mid_tier_higher_success_than_early",
                    "success": mid_success > early_success,
                    "mid_rate": mid_success,
                    "early_rate": early_success
                })
            
            # Free tier should have more rate limiting
            if "free" in tier_averages:
                free_rate_limited = tier_averages["free"]["avg_rate_limited"]
                
                allocation_validations.append({
                    "validation": "free_tier_rate_limited",
                    "success": free_rate_limited > 5,  # Should have some rate limiting
                    "free_rate_limited": free_rate_limited
                })
            
            successful_validations = [v for v in allocation_validations if v.get("success", False)]
            
            return {
                "success": len(successful_validations) >= len(allocation_validations) * 0.8,
                "total_validations": len(allocation_validations),
                "successful_validations": len(successful_validations),
                "tier_averages": tier_averages,
                "allocation_validations": allocation_validations,
                "service_calls": 0  # Analysis only
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _validate_system_recovery(self) -> Dict[str, Any]:
        """Validate system recovers properly after load testing."""
        try:
            # Wait for system to settle after load tests
            await asyncio.sleep(5.0)
            
            # Test system responsiveness with baseline user
            recovery_user = await self.create_test_user_with_billing("mid")
            
            if not recovery_user["success"]:
                return {"success": False, "error": "Failed to create recovery test user"}
            
            # Execute post-load baseline requests
            recovery_requests = 5
            response_times = []
            successful_requests = 0
            
            headers = {
                "Authorization": f"Bearer {recovery_user['access_token']}",
                "Content-Type": "application/json"
            }
            
            for i in range(recovery_requests):
                start_time = time.time()
                
                try:
                    test_request = {
                        "operation_type": "recovery_test",
                        "user_id": recovery_user["user_id"],
                        "request_id": f"recovery_{i}"
                    }
                    
                    response = await self.test_client.post(
                        f"{self.service_endpoints.backend}/api/ai/execute",
                        json=test_request,
                        headers=headers
                    )
                    
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                    
                    if response.status_code == 200:
                        successful_requests += 1
                    
                    await asyncio.sleep(1.0)  # Normal interval
                    
                except Exception as e:
                    response_times.append(time.time() - start_time)
            
            # Compare with baseline metrics
            recovery_avg_time = statistics.mean(response_times) if response_times else float('inf')
            recovery_success_rate = successful_requests / recovery_requests
            
            baseline_avg_time = self.baseline_metrics.get("average_response_time", 0)
            baseline_success_rate = self.baseline_metrics.get("success_rate", 0)
            
            # System should perform similarly to baseline
            performance_recovered = (
                recovery_avg_time <= baseline_avg_time * 2.0 and  # Within 2x baseline time
                recovery_success_rate >= baseline_success_rate * 0.9  # 90% of baseline success rate
            )
            
            return {
                "success": performance_recovered,
                "recovery_avg_time": recovery_avg_time,
                "baseline_avg_time": baseline_avg_time,
                "recovery_success_rate": recovery_success_rate,
                "baseline_success_rate": baseline_success_rate,
                "performance_recovered": performance_recovered,
                "service_calls": recovery_requests + 1  # recovery requests + user creation
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate rate limiting meets business requirements."""
        try:
            # Validate all critical phases completed
            critical_phases = [
                results.get("phase_1_baseline", {}).get("success", False),
                results.get("phase_2_user_setup", {}).get("success", False),
                results.get("phase_3_gradual_load", {}).get("success", False),
                results.get("phase_4_burst_protection", {}).get("success", False),
                results.get("phase_5_fair_allocation", {}).get("success", False),
                results.get("phase_6_recovery_validation", {}).get("success", False)
            ]
            
            if not all(critical_phases):
                failed_phases = [f"phase_{i+1}" for i, success in enumerate(critical_phases) if not success]
                self.test_metrics.errors.append(f"Failed critical phases: {', '.join(failed_phases)}")
                return False
            
            # Validate business metrics for rate limiting
            business_requirements = {
                "max_response_time_seconds": 10.0,  # Under load, longer times acceptable
                "min_success_rate_percent": 70.0,  # Some rate limiting expected
                "max_error_count": 5  # Allow some errors under high load
            }
            
            return await self.validate_business_metrics(business_requirements)
            
        except Exception as e:
            self.test_metrics.errors.append(f"Result validation failed: {str(e)}")
            return False
    
    async def cleanup_test_specific_resources(self) -> None:
        """Clean up load testing resources."""
        # Clear test data
        self.test_users.clear()
        self.load_test_results.clear()
        self.baseline_metrics.clear()

# Pytest fixtures and test functions
@pytest.fixture
async def rate_limiting_load_test():
    """Create rate limiting load test instance."""
    test = RateLimitingLoadL4Test()
    await test.initialize_l4_environment()
    yield test
    await test.cleanup_l4_resources()

@pytest.mark.asyncio
@pytest.mark.staging
async def test_rate_limiting_under_load_l4(rate_limiting_load_test):
    """Test rate limiting protection under high load in staging."""
    # Execute complete critical path test
    metrics = await rate_limiting_load_test.run_complete_critical_path_test()
    
    # Validate test success
    assert metrics.success is True, f"Rate limiting load test failed: {metrics.errors}"
    
    # Validate performance under load
    assert metrics.duration < 600.0, f"Load test took too long: {metrics.duration:.2f}s"
    assert metrics.success_rate >= 70.0, f"Success rate too low under load: {metrics.success_rate:.1f}%"
    assert metrics.error_count <= 5, f"Too many errors under load: {metrics.error_count}"
    
    # Validate system exercised adequately
    assert metrics.service_calls >= 100, "Insufficient load testing coverage"
    
    # Log test results for monitoring
    print(f"Rate Limiting Load Test Results:")
    print(f"  Duration: {metrics.duration:.2f}s")
    print(f"  Success Rate: {metrics.success_rate:.1f}%")
    print(f"  Service Calls: {metrics.service_calls}")
    print(f"  Load Test Results: {len(rate_limiting_load_test.load_test_results)}")

@pytest.mark.asyncio
@pytest.mark.staging
async def test_tier_based_rate_limiting_l4(rate_limiting_load_test):
    """Test tier-based rate limiting differences."""
    # Setup users and execute load tests
    await rate_limiting_load_test._setup_tier_users_for_load_testing()
    await rate_limiting_load_test._execute_gradual_load_test()
    
    # Validate tier-based differences
    fair_allocation = await rate_limiting_load_test._validate_fair_resource_allocation()
    
    assert fair_allocation["success"] is True, "Fair resource allocation failed"
    
    # Check specific tier behaviors
    tier_averages = fair_allocation.get("tier_averages", {})
    
    if "enterprise" in tier_averages and "free" in tier_averages:
        enterprise_success = tier_averages["enterprise"]["avg_success_rate"]
        free_success = tier_averages["free"]["avg_success_rate"]
        
        assert enterprise_success > free_success, f"Enterprise tier ({enterprise_success:.2f}) should outperform free tier ({free_success:.2f})"

@pytest.mark.asyncio
@pytest.mark.staging
async def test_burst_protection_effectiveness_l4(rate_limiting_load_test):
    """Test burst protection prevents system overload."""
    # Setup users
    await rate_limiting_load_test._setup_tier_users_for_load_testing()
    
    # Test burst protection
    burst_results = await rate_limiting_load_test._test_burst_protection()
    
    assert burst_results["success"] is True, "Burst protection failed"
    assert burst_results["successful_burst_tests"] >= 3, "Insufficient burst protection coverage"
    
    # Validate burst protection was effective for each tier
    for result in burst_results["burst_results"]:
        if result.get("success"):
            assert result["burst_protection_effective"] is True, f"Burst protection ineffective for {result['tier']} tier"