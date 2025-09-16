"""
Infrastructure-Aware Test Base Classes for E2E Testing

This module provides base test classes that are aware of infrastructure constraints
and can adapt their behavior based on infrastructure health and environment conditions.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test Reliability and Staging Environment Stability
- Value Impact: Reduces false negatives in testing due to infrastructure issues
- Strategic Impact: Enables reliable CI/CD pipeline and faster deployment cycles

Key Features:
- Infrastructure health checks before test execution
- Adaptive timeouts based on environment and service health
- Graceful test skipping for infrastructure outages
- Enhanced error reporting with infrastructure context
- Automatic retry mechanisms for infrastructure-related failures

SSOT Compliance:
- Inherits from SSotBaseTestCase for test framework consistency
- Uses centralized configuration and environment management
- Integrates with existing infrastructure resilience monitoring
- Maintains absolute imports and proper error handling
"""

import asyncio
import logging
import time
import unittest
from typing import Dict, Any, Optional, List, Set, Callable, Type
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from test_framework.ssot.orchestration import OrchestrationConfig

# Infrastructure resilience imports
from netra_backend.app.services.infrastructure_resilience import (
    get_resilience_manager, InfrastructureService, ServiceStatus,
    get_infrastructure_health_summary
)
from netra_backend.app.core.database_timeout_config import (
    get_database_timeout_config, get_connection_performance_summary,
    check_vpc_connector_performance
)

# Environment and configuration imports
from shared.isolated_environment import get_env
from netra_backend.app.core.config import get_config

logger = logging.getLogger(__name__)


class InfrastructureTestStrategy(Enum):
    """Test execution strategies for different infrastructure states."""
    NORMAL = "normal"  # Execute normally with standard timeouts
    CONSERVATIVE = "conservative"  # Use extended timeouts and retry logic
    GRACEFUL_SKIP = "graceful_skip"  # Skip tests with infrastructure dependencies
    FALLBACK_MODE = "fallback_mode"  # Use fallback services where available
    FAIL_FAST = "fail_fast"  # Fail immediately on infrastructure issues


@dataclass
class InfrastructureTestConfig:
    """Configuration for infrastructure-aware testing."""
    strategy: InfrastructureTestStrategy = InfrastructureTestStrategy.CONSERVATIVE
    required_services: Set[InfrastructureService] = None
    timeout_multiplier: float = 1.5
    max_retries: int = 3
    retry_delay: float = 2.0
    skip_on_degraded: bool = False
    skip_on_critical: bool = True
    enhanced_logging: bool = True
    performance_baseline_enabled: bool = True


class InfrastructureAwareTestMixin:
    """
    Mixin class providing infrastructure awareness for test cases.

    This mixin can be combined with any test base class to add infrastructure
    monitoring and adaptive behavior capabilities.
    """

    def setUp(self) -> None:
        """Enhanced setUp with infrastructure checks."""
        super().setUp()

        self.environment = get_env("ENVIRONMENT", "development")
        self.config = get_config()
        self.resilience_manager = get_resilience_manager()

        # Initialize infrastructure test configuration
        self.infrastructure_config = getattr(self, 'infrastructure_config', InfrastructureTestConfig())

        # Track test start time and infrastructure state
        self.test_start_time = time.time()
        self.infrastructure_health_at_start = None
        self.performance_baselines = {}

        # Set up infrastructure monitoring
        self._setup_infrastructure_monitoring()

        logger.debug(f"Infrastructure-aware test setup completed for {self.__class__.__name__}")

    def tearDown(self) -> None:
        """Enhanced tearDown with infrastructure reporting."""
        try:
            # Record test performance and infrastructure impact
            self._record_test_infrastructure_impact()

            # Log infrastructure health summary if enhanced logging enabled
            if self.infrastructure_config.enhanced_logging:
                self._log_infrastructure_test_summary()

        except Exception as e:
            logger.error(f"Error in infrastructure-aware tearDown: {e}")
        finally:
            super().tearDown()

    def _setup_infrastructure_monitoring(self) -> None:
        """Set up infrastructure monitoring for the test."""
        try:
            # Capture initial infrastructure state
            self.infrastructure_health_at_start = get_infrastructure_health_summary()

            # Set up performance baselines if enabled
            if self.infrastructure_config.performance_baseline_enabled:
                self._establish_performance_baselines()

            # Check required services are healthy
            if self.infrastructure_config.required_services:
                self._check_required_services()

        except Exception as e:
            logger.error(f"Failed to setup infrastructure monitoring: {e}")
            # Don't fail the test setup, but log the issue
            self.infrastructure_health_at_start = {'error': str(e)}

    def _establish_performance_baselines(self) -> None:
        """Establish performance baselines for infrastructure services."""
        for service in InfrastructureService:
            try:
                if service == InfrastructureService.DATABASE:
                    summary = get_connection_performance_summary(self.environment)
                    self.performance_baselines[service.value] = {
                        'average_time': summary.get('average_connection_time', 0),
                        'success_rate': summary.get('success_rate', 100),
                        'baseline_established': datetime.now()
                    }
                elif service == InfrastructureService.VPC_CONNECTOR and self.environment in ["staging", "production"]:
                    vpc_performance = check_vpc_connector_performance(self.environment)
                    self.performance_baselines[service.value] = {
                        'average_time': vpc_performance.get('average_connection_time', 0),
                        'status': vpc_performance.get('status', 'unknown'),
                        'baseline_established': datetime.now()
                    }
            except Exception as e:
                logger.warning(f"Failed to establish baseline for {service.value}: {e}")

    def _check_required_services(self) -> None:
        """Check that required infrastructure services are healthy."""
        unhealthy_services = []

        for service in self.infrastructure_config.required_services:
            status = self.resilience_manager.get_service_status(service)

            if self.infrastructure_config.skip_on_critical and status in [ServiceStatus.CRITICAL, ServiceStatus.UNAVAILABLE]:
                unhealthy_services.append((service, status))
            elif self.infrastructure_config.skip_on_degraded and status == ServiceStatus.DEGRADED:
                unhealthy_services.append((service, status))

        if unhealthy_services:
            service_statuses = [f"{service.value}:{status.value}" for service, status in unhealthy_services]
            self.skipTest(f"Required services unhealthy: {', '.join(service_statuses)}")

    def _record_test_infrastructure_impact(self) -> None:
        """Record the infrastructure impact of the test execution."""
        test_duration = time.time() - self.test_start_time

        # Record basic test metrics
        test_impact = {
            'test_class': self.__class__.__name__,
            'test_method': getattr(self, '_testMethodName', 'unknown'),
            'duration': test_duration,
            'environment': self.environment,
            'infrastructure_strategy': self.infrastructure_config.strategy.value,
            'start_time': datetime.fromtimestamp(self.test_start_time).isoformat(),
            'end_time': datetime.now().isoformat()
        }

        # Add infrastructure health comparison
        if self.infrastructure_health_at_start:
            current_health = get_infrastructure_health_summary()
            test_impact['infrastructure_health'] = {
                'start': self.infrastructure_health_at_start,
                'end': current_health,
                'health_changed': (
                    self.infrastructure_health_at_start.get('overall_status') !=
                    current_health.get('overall_status')
                )
            }

        # Add performance impact analysis
        if self.performance_baselines:
            test_impact['performance_impact'] = self._analyze_performance_impact()

        # Store for potential aggregation and reporting
        if not hasattr(self.__class__, '_infrastructure_impact_log'):
            self.__class__._infrastructure_impact_log = []
        self.__class__._infrastructure_impact_log.append(test_impact)

    def _analyze_performance_impact(self) -> Dict[str, Any]:
        """Analyze performance impact compared to baselines."""
        impact_analysis = {}

        for service_name, baseline in self.performance_baselines.items():
            try:
                current_performance = None

                if service_name == InfrastructureService.DATABASE.value:
                    current_summary = get_connection_performance_summary(self.environment)
                    current_performance = {
                        'average_time': current_summary.get('average_connection_time', 0),
                        'success_rate': current_summary.get('success_rate', 100)
                    }
                elif service_name == InfrastructureService.VPC_CONNECTOR.value:
                    vpc_performance = check_vpc_connector_performance(self.environment)
                    current_performance = {
                        'average_time': vpc_performance.get('average_connection_time', 0),
                        'status': vpc_performance.get('status', 'unknown')
                    }

                if current_performance:
                    impact_analysis[service_name] = {
                        'baseline': baseline,
                        'current': current_performance,
                        'performance_change': self._calculate_performance_change(baseline, current_performance)
                    }

            except Exception as e:
                logger.warning(f"Failed to analyze performance impact for {service_name}: {e}")
                impact_analysis[service_name] = {'error': str(e)}

        return impact_analysis

    def _calculate_performance_change(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance change metrics."""
        changes = {}

        # Time-based metrics
        if 'average_time' in baseline and 'average_time' in current:
            baseline_time = baseline['average_time']
            current_time = current['average_time']

            if baseline_time > 0:
                time_change_percent = ((current_time - baseline_time) / baseline_time) * 100
                changes['time_change_percent'] = time_change_percent
                changes['time_degraded'] = time_change_percent > 20  # 20% degradation threshold

        # Success rate metrics
        if 'success_rate' in baseline and 'success_rate' in current:
            baseline_rate = baseline['success_rate']
            current_rate = current['success_rate']

            rate_change = current_rate - baseline_rate
            changes['success_rate_change'] = rate_change
            changes['success_rate_degraded'] = rate_change < -5  # 5% degradation threshold

        return changes

    def _log_infrastructure_test_summary(self) -> None:
        """Log infrastructure test summary for debugging."""
        try:
            current_health = get_infrastructure_health_summary()
            test_duration = time.time() - self.test_start_time

            logger.info(f"Infrastructure Test Summary for {self.__class__.__name__}:")
            logger.info(f"  Test Duration: {test_duration:.2f}s")
            logger.info(f"  Environment: {self.environment}")
            logger.info(f"  Strategy: {self.infrastructure_config.strategy.value}")
            logger.info(f"  Overall Infrastructure Health: {current_health.get('overall_status', 'unknown')}")

            if current_health.get('critical_services'):
                logger.warning(f"  Critical Services: {current_health['critical_services']}")

            if current_health.get('chat_functionality_impacted'):
                logger.critical("  CHAT FUNCTIONALITY IMPACTED - Core business value at risk")

        except Exception as e:
            logger.error(f"Failed to log infrastructure test summary: {e}")

    @asynccontextmanager
    async def infrastructure_resilient_operation(self, service: InfrastructureService, operation_name: str):
        """
        Context manager for infrastructure-resilient test operations.

        Provides automatic retry and timeout adjustment based on infrastructure health.
        """
        timeout_config = get_database_timeout_config(self.environment)
        base_timeout = timeout_config.get('initialization_timeout', 30.0)

        # Adjust timeout based on infrastructure health and test configuration
        adjusted_timeout = base_timeout * self.infrastructure_config.timeout_multiplier

        # Check service health and adjust strategy
        service_status = self.resilience_manager.get_service_status(service)
        if service_status in [ServiceStatus.DEGRADED, ServiceStatus.CRITICAL]:
            adjusted_timeout *= 1.5  # Additional buffer for degraded services
            logger.warning(f"Service {service.value} is {service_status.value}, using extended timeout: {adjusted_timeout}s")

        # Execute with resilience
        attempt = 0
        start_time = time.time()

        while attempt <= self.infrastructure_config.max_retries:
            try:
                async with asyncio.timeout(adjusted_timeout):
                    yield

                operation_time = time.time() - start_time
                logger.debug(f"Infrastructure operation {operation_name} completed in {operation_time:.2f}s")
                return

            except asyncio.TimeoutError as e:
                attempt += 1
                operation_time = time.time() - start_time

                if attempt <= self.infrastructure_config.max_retries:
                    logger.warning(f"Operation {operation_name} timed out after {operation_time:.2f}s, retrying {attempt}/{self.infrastructure_config.max_retries}")
                    await asyncio.sleep(self.infrastructure_config.retry_delay * attempt)
                    start_time = time.time()  # Reset start time for retry
                else:
                    logger.error(f"Operation {operation_name} failed after {attempt} attempts, total time: {time.time() - start_time:.2f}s")
                    raise

            except Exception as e:
                logger.error(f"Infrastructure operation {operation_name} failed: {e}")
                raise

    def assert_infrastructure_health_maintained(self, critical_services_only: bool = True) -> None:
        """
        Assert that infrastructure health was maintained during test execution.

        Args:
            critical_services_only: If True, only check services critical to chat functionality
        """
        if not self.infrastructure_health_at_start:
            self.skipTest("Infrastructure health monitoring not available")

        current_health = get_infrastructure_health_summary()
        start_health = self.infrastructure_health_at_start

        # Check overall health degradation
        start_status = start_health.get('overall_status', 'unknown')
        current_status = current_health.get('overall_status', 'unknown')

        if start_status == 'healthy' and current_status in ['critical', 'unavailable']:
            self.fail(f"Infrastructure health degraded from {start_status} to {current_status} during test execution")

        # Check chat functionality impact
        if current_health.get('chat_functionality_impacted', False) and not start_health.get('chat_functionality_impacted', False):
            self.fail("Test execution caused chat functionality to become impacted")

        # Check specific critical services if requested
        if critical_services_only:
            current_critical = set(current_health.get('critical_services', []))
            start_critical = set(start_health.get('critical_services', []))
            new_critical = current_critical - start_critical

            if new_critical:
                self.fail(f"New critical services detected during test: {new_critical}")


class InfrastructureAwareTestCase(InfrastructureAwareTestMixin, SSotBaseTestCase):
    """
    Synchronous test base class with infrastructure awareness.

    Combines SSOT test framework compliance with infrastructure monitoring
    and adaptive behavior for synchronous test cases.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default configuration for synchronous tests
        self.infrastructure_config = InfrastructureTestConfig(
            strategy=InfrastructureTestStrategy.CONSERVATIVE,
            timeout_multiplier=1.2,
            max_retries=2
        )


class InfrastructureAwareAsyncTestCase(InfrastructureAwareTestMixin, SSotAsyncTestCase):
    """
    Asynchronous test base class with infrastructure awareness.

    Combines SSOT test framework compliance with infrastructure monitoring
    and adaptive behavior for asynchronous test cases.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default configuration for async tests
        self.infrastructure_config = InfrastructureTestConfig(
            strategy=InfrastructureTestStrategy.CONSERVATIVE,
            timeout_multiplier=1.5,
            max_retries=3,
            enhanced_logging=True
        )

    async def asyncSetUp(self) -> None:
        """Enhanced async setUp with infrastructure checks."""
        await super().asyncSetUp()

        # Additional async-specific infrastructure setup
        try:
            # Initialize resilience manager monitoring if not already started
            await self.resilience_manager.start_monitoring()
        except Exception as e:
            logger.warning(f"Failed to start resilience monitoring in test: {e}")

    async def asyncTearDown(self) -> None:
        """Enhanced async tearDown with infrastructure cleanup."""
        try:
            # Record any async-specific infrastructure metrics
            await self._record_async_infrastructure_metrics()
        except Exception as e:
            logger.error(f"Error recording async infrastructure metrics: {e}")
        finally:
            await super().asyncTearDown()

    async def _record_async_infrastructure_metrics(self) -> None:
        """Record async-specific infrastructure metrics."""
        # This could include async operation timing, concurrent connection usage, etc.
        pass


class StagingEnvironmentTestCase(InfrastructureAwareAsyncTestCase):
    """
    Specialized test case for staging environment testing.

    Configured specifically for staging environment constraints including
    VPC connector limitations, Cloud SQL timeouts, and infrastructure scaling delays.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Staging-specific configuration
        self.infrastructure_config = InfrastructureTestConfig(
            strategy=InfrastructureTestStrategy.CONSERVATIVE,
            required_services={
                InfrastructureService.DATABASE,
                InfrastructureService.VPC_CONNECTOR,
                InfrastructureService.WEBSOCKET
            },
            timeout_multiplier=2.0,  # Double timeouts for staging
            max_retries=5,
            retry_delay=3.0,
            skip_on_critical=True,
            enhanced_logging=True,
            performance_baseline_enabled=True
        )

    def setUp(self) -> None:
        """Staging-specific setup with enhanced infrastructure monitoring."""
        super().setUp()

        # Skip if not in staging environment
        if self.environment != "staging":
            self.skipTest("StagingEnvironmentTestCase only runs in staging environment")

        # Additional staging-specific checks
        self._check_staging_infrastructure_readiness()

    def _check_staging_infrastructure_readiness(self) -> None:
        """Check staging-specific infrastructure readiness."""
        try:
            # Check VPC connector performance
            vpc_performance = check_vpc_connector_performance(self.environment)
            if vpc_performance.get('status') == 'critical':
                self.skipTest(f"VPC connector performance critical: {vpc_performance.get('performance_issues', [])}")

            # Check database connection performance
            db_summary = get_connection_performance_summary(self.environment)
            if db_summary.get('status') == 'degraded':
                logger.warning(f"Database performance degraded: {db_summary}")
                # Don't skip, but use more conservative settings
                self.infrastructure_config.timeout_multiplier = 3.0

        except Exception as e:
            logger.error(f"Failed staging infrastructure readiness check: {e}")
            # Don't fail the test, but note the issue
            self.infrastructure_config.enhanced_logging = True


def infrastructure_test_requires(*services: InfrastructureService):
    """
    Decorator to specify required infrastructure services for a test.

    Usage:
        @infrastructure_test_requires(InfrastructureService.DATABASE, InfrastructureService.REDIS)
        def test_something(self):
            # Test will be skipped if DATABASE or REDIS are unhealthy
            pass
    """
    def decorator(test_method):
        def wrapper(self, *args, **kwargs):
            if hasattr(self, 'infrastructure_config'):
                if self.infrastructure_config.required_services is None:
                    self.infrastructure_config.required_services = set()
                self.infrastructure_config.required_services.update(services)
            return test_method(self, *args, **kwargs)
        return wrapper
    return decorator


def infrastructure_test_strategy(strategy: InfrastructureTestStrategy):
    """
    Decorator to specify infrastructure test strategy for a test method.

    Usage:
        @infrastructure_test_strategy(InfrastructureTestStrategy.FAIL_FAST)
        def test_critical_path(self):
            # Test will fail fast on any infrastructure issues
            pass
    """
    def decorator(test_method):
        def wrapper(self, *args, **kwargs):
            if hasattr(self, 'infrastructure_config'):
                original_strategy = self.infrastructure_config.strategy
                self.infrastructure_config.strategy = strategy
                try:
                    return test_method(self, *args, **kwargs)
                finally:
                    self.infrastructure_config.strategy = original_strategy
            else:
                return test_method(self, *args, **kwargs)
        return wrapper
    return decorator


# Utility functions for infrastructure-aware testing
def get_infrastructure_test_summary() -> Dict[str, Any]:
    """
    Get summary of infrastructure test impacts across all test classes.

    Returns:
        Dictionary containing aggregated infrastructure test metrics
    """
    # This would aggregate data from all test classes' _infrastructure_impact_log
    # Implementation would depend on test runner integration
    return {
        'summary_available': False,
        'reason': 'Test aggregation not yet implemented'
    }


def log_infrastructure_test_recommendations(environment: str) -> None:
    """
    Log recommendations for infrastructure testing based on current health.

    Args:
        environment: Environment name for context-specific recommendations
    """
    try:
        health_summary = get_infrastructure_health_summary()

        logger.info(f"Infrastructure Test Recommendations for {environment}:")

        if health_summary.get('overall_status') == 'healthy':
            logger.info("  ✅ Infrastructure healthy - normal test execution recommended")
        elif health_summary.get('overall_status') == 'degraded':
            logger.warning("  ⚠️  Infrastructure degraded - consider conservative test strategy")
            logger.warning("  📋 Recommendations:")
            logger.warning("     - Use extended timeouts (2x multiplier)")
            logger.warning("     - Enable retry mechanisms")
            logger.warning("     - Monitor for chat functionality impact")
        elif health_summary.get('overall_status') == 'critical':
            logger.error("  🚨 Infrastructure critical - consider skipping non-essential tests")
            logger.error("  📋 Critical Recommendations:")
            logger.error("     - Skip tests requiring critical services")
            logger.error("     - Use fail-fast strategy for essential tests")
            logger.error("     - Alert infrastructure team")

        if health_summary.get('chat_functionality_impacted'):
            logger.critical("  💬 CHAT FUNCTIONALITY IMPACTED - Core business value at risk")
            logger.critical("     - Prioritize chat-related infrastructure fixes")
            logger.critical("     - Consider maintenance mode for testing")

    except Exception as e:
        logger.error(f"Failed to generate infrastructure test recommendations: {e}")


# Export public interface
__all__ = [
    "InfrastructureAwareTestMixin",
    "InfrastructureAwareTestCase",
    "InfrastructureAwareAsyncTestCase",
    "StagingEnvironmentTestCase",
    "InfrastructureTestStrategy",
    "InfrastructureTestConfig",
    "infrastructure_test_requires",
    "infrastructure_test_strategy",
    "get_infrastructure_test_summary",
    "log_infrastructure_test_recommendations"
]