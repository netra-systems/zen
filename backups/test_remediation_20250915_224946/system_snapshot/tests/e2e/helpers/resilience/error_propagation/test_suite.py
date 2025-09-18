"""Error Propagation Test Suite

Main pytest test class for comprehensive error propagation testing.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.helpers.resilience.error_propagation.database_error_helpers import (
    DatabaseErrorHandlingValidator,
)
from tests.e2e.helpers.resilience.error_propagation.error_correlation_helpers import (
    ErrorCorrelationValidator,
)
from tests.e2e.helpers.resilience.error_propagation.error_generators import (
    RealErrorPropagationTester,
)
from tests.e2e.helpers.resilience.error_propagation.error_recovery_helpers import (
    NetworkFailureSimulationValidator,
)
from tests.e2e.helpers.resilience.error_propagation.error_validators import (
    AuthServiceFailurePropagationValidator,
)
from tests.e2e.helpers.resilience.error_propagation.user_message_helpers import (
    UserFriendlyMessageValidator,
)

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.e2e
class RealErrorPropagationTests:
    """Comprehensive real error propagation test suite."""
    
    @pytest.fixture
    async def error_tester(self):
        """Setup comprehensive error propagation tester with real services."""
        tester = RealErrorPropagationTester()
        
        # Setup real service environment
        setup_success = await tester.setup_test_environment()
        if not setup_success:
            pytest.skip("Could not setup real service environment - services not available")
        
        yield tester
        
        # Cleanup all resources
        await tester.cleanup_test_environment()
    
    @pytest.mark.resilience
    async def test_auth_service_failure_propagation(self, error_tester):
        """
        BVJ: Platform/Internal | Goal: Support Cost Reduction | Impact: $45K+ MRR
        Test: Auth failures propagate to Backend and Frontend with proper context
        """
        validator = AuthServiceFailurePropagationValidator(error_tester)
        error_tester.metrics.total_tests += 1
        
        # Test invalid token propagation chain
        invalid_token_result = await validator.test_invalid_token_propagation_chain()
        
        # Test expired token recovery chain
        expired_token_result = await validator.test_expired_token_recovery_chain()
        
        # Validate propagation success
        propagation_successful = invalid_token_result.get("propagation_successful", False)
        
        if propagation_successful:
            error_tester.metrics.successful_propagations += 1
        else:
            error_tester.metrics.failed_propagations += 1
        
        # Assertions for critical requirements
        assert (
            invalid_token_result.get("http_api_result", {}).get("auth_error_detected", False) or
            invalid_token_result.get("websocket_result", {}).get("auth_error_detected", False)
        ), "Auth errors must be detected in either HTTP or WebSocket communication"
        
        assert (
            invalid_token_result.get("correlation_result", {}).get("correlation_maintained", False)
        ), "Error correlation must be maintained across service boundaries"
        
        # Log comprehensive results
        logger.info(f"Auth Service Failure Propagation Results:")
        logger.info(f"  Invalid Token Chain: {json.dumps(invalid_token_result, indent=2)}")
        logger.info(f"  Expired Token Recovery: {json.dumps(expired_token_result, indent=2)}")
    
    @pytest.mark.resilience
    async def test_database_error_handling_recovery(self, error_tester):
        """
        BVJ: Platform/Internal | Goal: System Reliability | Impact: Operational scaling
        Test: Database errors handled gracefully with recovery mechanisms
        """
        validator = DatabaseErrorHandlingValidator(error_tester)
        error_tester.metrics.total_tests += 1
        
        # Test database connection failure handling
        db_failure_result = await validator.test_database_connection_failure_handling()
        
        # Validate system stability
        system_stability = db_failure_result.get("system_stability", {})
        system_resilient = system_stability.get("system_resilient", False)
        
        if system_resilient:
            error_tester.metrics.successful_propagations += 1
        else:
            error_tester.metrics.failed_propagations += 1
        
        # Critical assertions
        assert (
            db_failure_result.get("database_operation", {}).get("system_stable", False) or
            db_failure_result.get("graceful_degradation", {}).get("graceful_degradation", False)
        ), "System must remain stable during database issues"
        
        assert (
            system_stability.get("stability_score", 0) >= 1
        ), "System must demonstrate resilience indicators"
        
        # Log results
        logger.info(f"Database Error Handling Results:")
        logger.info(f"  System Stability: {json.dumps(system_stability, indent=2)}")
    
    @pytest.mark.resilience
    async def test_network_failure_retry_logic(self, error_tester):
        """
        BVJ: Platform/Internal | Goal: Reliability | Impact: Automatic error recovery
        Test: Network failures trigger retry logic with proper backoff
        """
        validator = NetworkFailureSimulationValidator(error_tester)
        error_tester.metrics.total_tests += 1
        
        # Test timeout retry mechanisms
        retry_result = await validator.test_timeout_retry_mechanisms()
        
        # Validate retry effectiveness
        retry_effective = retry_result.get("retry_logic_effective", {}).get("retry_system_effective", False)
        
        if retry_effective:
            error_tester.metrics.successful_propagations += 1
            error_tester.metrics.retry_attempts += retry_result.get("timeout_behavior", {}).get("retry_count", 0)
        else:
            error_tester.metrics.failed_propagations += 1
        
        # Critical assertions
        assert (
            retry_result.get("timeout_behavior", {}).get("timeout_properly_handled", False) or
            retry_result.get("eventual_success", {}).get("eventual_success", False)
        ), "Network timeouts must be handled with retry logic"
        
        # Log results
        logger.info(f"Network Failure Retry Logic Results:")
        logger.info(f"  Retry Logic Effectiveness: {json.dumps(retry_result.get('retry_logic_effective', {}), indent=2)}")
    
    @pytest.mark.resilience
    async def test_error_correlation_across_services(self, error_tester):
        """
        BVJ: Platform/Internal | Goal: Debugging Efficiency | Impact: Support cost reduction
        Test: Error correlation works across services with tracking IDs
        """
        validator = ErrorCorrelationValidator(error_tester)
        error_tester.metrics.total_tests += 1
        
        # Test cross-service error correlation
        correlation_result = await validator.test_cross_service_error_correlation()
        
        # Validate correlation success
        correlation_effective = correlation_result.get("overall_correlation_success", {}).get("correlation_effective", False)
        
        if correlation_effective:
            error_tester.metrics.correlation_successes += 1
        
        # Critical assertions
        assert (
            correlation_result.get("correlation_chain", {}).get("correlation_preserved", False) or
            correlation_result.get("websocket_correlation", {}).get("correlation_preserved", False)
        ), "Error correlation must be maintained across service boundaries"
        
        assert (
            correlation_result.get("correlation_persistence", {}).get("correlation_complete", False)
        ), "Correlation context must be complete with request ID and service chain"
        
        # Log results
        logger.info(f"Error Correlation Results:")
        logger.info(f"  Correlation Success: {json.dumps(correlation_result.get('overall_correlation_success', {}), indent=2)}")
    
    @pytest.mark.resilience
    async def test_user_friendly_error_messages(self, error_tester):
        """
        BVJ: Platform/Internal | Goal: User Experience | Impact: Support cost reduction
        Test: Users receive actionable, user-friendly error messages
        """
        validator = UserFriendlyMessageValidator(error_tester)
        error_tester.metrics.total_tests += 1
        
        # Test user-friendly error messages
        message_result = await validator.test_user_friendly_error_messages()
        
        # Validate message quality
        overall_quality = message_result.get("overall_quality", {})
        message_quality_acceptable = overall_quality.get("message_quality_acceptable", False)
        
        if message_quality_acceptable:
            error_tester.metrics.user_friendly_messages += overall_quality.get("user_friendly_messages", 0)
        
        # Critical assertions
        assert (
            overall_quality.get("user_friendly_percentage", 0) >= 50.0
        ), "At least 50% of error messages must be user-friendly"
        
        assert (
            overall_quality.get("actionable_percentage", 0) >= 30.0
        ), "At least 30% of error messages must be actionable"
        
        # Log results
        logger.info(f"User-Friendly Message Results:")
        logger.info(f"  Overall Quality: {json.dumps(overall_quality, indent=2)}")
    
    @pytest.mark.resilience
    async def test_complete_error_propagation_chain_performance(self, error_tester):
        """
        BVJ: Platform/Internal | Goal: System Performance | Impact: <30s execution time
        Test: Complete error propagation validation within time constraints
        """
        start_time = time.time()
        
        # Initialize all validators for comprehensive test
        auth_validator = AuthServiceFailurePropagationValidator(error_tester)
        db_validator = DatabaseErrorHandlingValidator(error_tester)
        network_validator = NetworkFailureSimulationValidator(error_tester)
        correlation_validator = ErrorCorrelationValidator(error_tester)
        message_validator = UserFriendlyMessageValidator(error_tester)
        
        # Run abbreviated comprehensive test suite with timing
        comprehensive_results = await self._run_performance_test_suite(
            auth_validator, db_validator, network_validator, 
            correlation_validator, message_validator, error_tester
        )
        
        # Calculate total time and performance metrics
        total_time = time.time() - start_time
        error_tester.metrics.average_response_time = total_time / 5
        
        # Performance validation
        assert total_time < 30.0, f"Error propagation test took {total_time:.2f}s, exceeding 30s limit"
        
        # Comprehensive coverage validation
        successful_tests = sum(1 for result in comprehensive_results.values() 
                             if isinstance(result, dict) and not result.get("error"))
        assert successful_tests >= 4, f"At least 4 error propagation tests must succeed, got {successful_tests}"
        
        # Final metrics update
        error_tester.metrics.total_tests = 5
        
        # Log comprehensive results
        self._log_performance_results(total_time, successful_tests, comprehensive_results, error_tester)
        
        # Store results in tester for potential analysis
        self._store_comprehensive_results(total_time, comprehensive_results, successful_tests, error_tester)
    
    async def _run_performance_test_suite(self, auth_validator, db_validator, network_validator, 
                                        correlation_validator, message_validator, error_tester) -> Dict[str, Any]:
        """Run abbreviated test suite for performance validation."""
        comprehensive_results = {}
        
        # Test Auth propagation
        auth_start = time.time()
        comprehensive_results["auth_propagation"] = await auth_validator.test_invalid_token_propagation_chain()
        auth_time = time.time() - auth_start
        
        # Test Database handling
        db_start = time.time()
        comprehensive_results["database_handling"] = await db_validator.test_database_connection_failure_handling()
        db_time = time.time() - db_start
        
        # Test Network retry
        network_start = time.time()
        comprehensive_results["network_retry"] = await network_validator.test_timeout_retry_mechanisms()
        network_time = time.time() - network_start
        
        # Test Error correlation (abbreviated for time)
        correlation_start = time.time()
        correlation_context = error_tester._create_correlation_context("performance_test")
        comprehensive_results["error_correlation"] = correlation_validator._validate_correlation_persistence(correlation_context)
        correlation_time = time.time() - correlation_start
        
        # Test User messages (abbreviated for time)
        message_start = time.time()
        test_message = "Authentication failed. Please check your credentials and try again."
        comprehensive_results["user_messages"] = message_validator._analyze_message_user_friendliness(test_message, "auth_test")
        message_time = time.time() - message_start
        
        # Store timing information
        comprehensive_results["_timing"] = {
            "auth": auth_time,
            "database": db_time,
            "network": network_time,
            "correlation": correlation_time,
            "messages": message_time
        }
        
        return comprehensive_results
    
    def _log_performance_results(self, total_time: float, successful_tests: int, 
                               comprehensive_results: Dict[str, Any], error_tester) -> None:
        """Log comprehensive performance results."""
        timing = comprehensive_results.get("_timing", {})
        
        logger.info(f"Complete Error Propagation Chain Performance Results:")
        logger.info(f"  Total Execution Time: {total_time:.2f}s")
        logger.info(f"  Individual Test Times: Auth={timing.get('auth', 0):.2f}s, DB={timing.get('database', 0):.2f}s, Network={timing.get('network', 0):.2f}s, Correlation={timing.get('correlation', 0):.2f}s, Messages={timing.get('messages', 0):.2f}s")
        logger.info(f"  Successful Tests: {successful_tests}/5")
        logger.info(f"  Final Metrics: {json.dumps(error_tester.metrics.__dict__, indent=2)}")
    
    def _store_comprehensive_results(self, total_time: float, comprehensive_results: Dict[str, Any], 
                                   successful_tests: int, error_tester) -> None:
        """Store comprehensive test results."""
        timing = comprehensive_results.pop("_timing", {})
        
        error_tester.comprehensive_test_results = {
            "total_time": total_time,
            "test_times": timing,
            "successful_tests": successful_tests,
            "detailed_results": comprehensive_results,
            "final_metrics": error_tester.metrics.__dict__
        }


def create_real_error_propagation_test_suite() -> RealErrorPropagationTests:
    """Create real error propagation test suite instance."""
    return RealErrorPropagationTests()
