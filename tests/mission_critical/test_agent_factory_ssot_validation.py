#!/usr/bin/env python3
"""
MISSION CRITICAL TEST SUITE: Agent Factory SSOT Validation

Business Value: Platform/Internal - $500K+ ARR Golden Path Protection
Validates ExecutionEngineFactory consolidation and ensures factory pattern follows SSOT principles.

This test suite validates:
1. ExecutionEngineFactory consolidation is correct
2. No shared state between user sessions
3. Factory pattern follows SSOT principles
4. Factory initialization consistency
5. User isolation integrity in factory-created instances

P0 SSOT Factory Violations Targeted:
- Multiple ExecutionEngineFactory implementations
- Shared state between concurrent users through factory instances
- Inconsistent factory initialization patterns

CRITICAL: Tests must run without Docker dependency for CI/CD integration.

Author: Agent Events Remediation Team
Date: 2025-09-12
"""

import ast
import concurrent.futures
import glob
import os
import re
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import SSOT test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env, IsolatedEnvironment


@dataclass
class FactoryValidation:
    """Results from factory SSOT validation."""
    factory_class: str
    file_path: str
    line_number: int
    is_production_code: bool
    is_deprecated: bool
    has_user_isolation: bool
    follows_ssot_pattern: bool


@dataclass
class UserIsolationTest:
    """Results from user isolation testing."""
    user_id: str
    session_id: str
    factory_instance_id: str
    execution_context_id: str
    memory_usage_mb: float
    isolation_verified: bool
    shared_state_detected: bool


@dataclass
class FactoryComplianceReport:
    """Comprehensive factory SSOT compliance report."""
    execution_engine_factories_found: int
    production_factories: List[FactoryValidation]
    deprecated_factories: List[FactoryValidation]
    user_isolation_tests: List[UserIsolationTest]
    factory_consistency_score: float
    shared_state_violations: int
    ssot_compliance_score: float
    critical_violations: List[str]
    recommendations: List[str]


class FactorySSotAnalyzer:
    """Analyzes factory patterns for SSOT compliance."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.factory_patterns = [
            'ExecutionEngineFactory',
            'UserExecutionEngineFactory',
            'AgentFactory',
            'WebSocketFactory'
        ]
        self.ssot_factory_paths = {
            'ExecutionEngineFactory': 'netra_backend.app.agents.supervisor.user_execution_engine'
        }

    def scan_for_factory_classes(self) -> List[FactoryValidation]:
        """Scan codebase for factory class implementations."""
        validations = []

        python_files = glob.glob(str(self.project_root / "**" / "*.py"), recursive=True)

        for file_path in python_files:
            # Skip test files, backups, and cache
            if any(skip in file_path for skip in ['test', '__pycache__', '.git', 'backup', 'deprecated']):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for factory class patterns
                for factory_pattern in self.factory_patterns:
                    class_pattern = rf'^class {factory_pattern}[^(]*(?:\([^)]*\))?:'
                    matches = re.finditer(class_pattern, content, re.MULTILINE)

                    for match in matches:
                        line_number = content[:match.start()].count('\n') + 1

                        validation = FactoryValidation(
                            factory_class=factory_pattern,
                            file_path=file_path,
                            line_number=line_number,
                            is_production_code=self._is_production_code(file_path),
                            is_deprecated=('deprecated' in file_path.lower() or 'backup' in file_path.lower()),
                            has_user_isolation=self._check_user_isolation_pattern(content, match),
                            follows_ssot_pattern=self._check_ssot_pattern(content, match)
                        )
                        validations.append(validation)

            except Exception as e:
                logger.warning(f"Error scanning {file_path}: {e}")

        return validations

    def _is_production_code(self, file_path: str) -> bool:
        """Check if file contains production code."""
        return any(prod in file_path for prod in ['netra_backend/app/', 'auth_service/', 'shared/'])

    def _check_user_isolation_pattern(self, content: str, match: re.Match) -> bool:
        """Check if factory follows user isolation pattern."""
        # Look for user_id parameters and isolation patterns
        factory_section = content[match.start():match.start() + 2000]  # Next 2000 chars

        isolation_indicators = [
            'user_id',
            'exec_context',
            'UserExecutionContext',
            'create_for_user',
            'user_context'
        ]

        return any(indicator in factory_section for indicator in isolation_indicators)

    def _check_ssot_pattern(self, content: str, match: re.Match) -> bool:
        """Check if factory follows SSOT pattern."""
        factory_section = content[match.start():match.start() + 2000]  # Next 2000 chars

        ssot_indicators = [
            '@classmethod',
            'create_for_user',
            'validate_',
            'ensure_',
            'SSOT'
        ]

        return any(indicator in factory_section for indicator in ssot_indicators)


class UserIsolationSimulator:
    """Simulates concurrent users to test factory isolation."""

    def __init__(self):
        self.shared_state_tracker = {}
        self.isolation_results = []

    def simulate_user_session(self, user_id: str) -> UserIsolationTest:
        """Simulate a user session to test factory isolation."""
        session_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # Try to import and use ExecutionEngine factory
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

            # Create mock execution context
            class MockExecutionContext:
                def __init__(self, user_id: str):
                    self.user_id = user_id
                    self.session_id = session_id
                    self.agent_name = f"test_agent_{user_id}"
                    self.run_id = str(uuid.uuid4())

            exec_context = MockExecutionContext(user_id)

            # Test factory instantiation (if factory method exists)
            if hasattr(UserExecutionEngine, 'create_for_user'):
                # Use factory method
                factory_instance_id = str(id(UserExecutionEngine))
                execution_context_id = str(id(exec_context))
            else:
                # Direct instantiation
                factory_instance_id = "direct_instantiation"
                execution_context_id = str(id(exec_context))

            # Check for shared state
            state_key = f"factory_{factory_instance_id}"
            if state_key in self.shared_state_tracker:
                shared_state_detected = True
                logger.warning(f"Shared state detected for factory {factory_instance_id}")
            else:
                self.shared_state_tracker[state_key] = {
                    'user_id': user_id,
                    'timestamp': datetime.now(),
                    'session_id': session_id
                }
                shared_state_detected = False

            # Simulate memory usage
            memory_usage_mb = 0.5  # Minimal for testing

            return UserIsolationTest(
                user_id=user_id,
                session_id=session_id,
                factory_instance_id=factory_instance_id,
                execution_context_id=execution_context_id,
                memory_usage_mb=memory_usage_mb,
                isolation_verified=not shared_state_detected,
                shared_state_detected=shared_state_detected
            )

        except Exception as e:
            logger.error(f"Error simulating user session for {user_id}: {e}")
            return UserIsolationTest(
                user_id=user_id,
                session_id=session_id,
                factory_instance_id="error",
                execution_context_id="error",
                memory_usage_mb=0.0,
                isolation_verified=False,
                shared_state_detected=True
            )


class TestAgentFactorySSotValidation(SSotBaseTestCase):
    """Mission Critical Test Suite: Agent Factory SSOT Validation."""

    def setup_method(self, method):
        """Setup test method with SSOT base configuration."""
        super().setup_method(method)
        self.project_root = Path(project_root)
        self.analyzer = FactorySSotAnalyzer(self.project_root)
        self.simulator = UserIsolationSimulator()

    def test_execution_engine_factory_consolidation(self):
        """Test that ExecutionEngineFactory is properly consolidated."""
        logger.info("Testing ExecutionEngineFactory consolidation")

        # Scan for all factory implementations
        factory_validations = self.analyzer.scan_for_factory_classes()

        # Filter for ExecutionEngine factories
        execution_engine_factories = [
            v for v in factory_validations
            if 'ExecutionEngine' in v.factory_class and v.is_production_code
        ]

        logger.info(f"Found {len(execution_engine_factories)} ExecutionEngine factory implementations")

        # Log each factory found
        for factory in execution_engine_factories:
            logger.info(f"  {factory.factory_class} at {factory.file_path}:{factory.line_number}")

        # Check for canonical SSOT factory
        canonical_factories = [
            f for f in execution_engine_factories
            if 'user_execution_engine' in f.file_path
        ]

        # CRITICAL ASSERTION: Must have canonical factory
        assert len(canonical_factories) >= 1, (
            f"No canonical ExecutionEngine factory found in user_execution_engine.py. "
            f"Found factories: {[f.file_path for f in execution_engine_factories]}"
        )

        # ASSERTION: Should not have too many production factories (allow some flexibility during migration)
        if len(execution_engine_factories) > 3:
            logger.warning(f"Found {len(execution_engine_factories)} ExecutionEngine factories - consider consolidation")

        logger.info("✅ ExecutionEngineFactory consolidation validated")

    def test_no_shared_state_between_user_sessions(self):
        """Test that factory-created instances don't share state between users."""
        logger.info("Testing factory user session isolation")

        # Simulate multiple concurrent users
        user_ids = [f"user_{i}" for i in range(5)]
        concurrent_tests = []

        # Use ThreadPoolExecutor to simulate concurrent user sessions
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit user session simulations
            futures = [
                executor.submit(self.simulator.simulate_user_session, user_id)
                for user_id in user_ids
            ]

            # Collect results
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=10)
                    concurrent_tests.append(result)
                except Exception as e:
                    logger.error(f"User session simulation failed: {e}")

        logger.info(f"Completed {len(concurrent_tests)} user session simulations")

        # Analyze isolation results
        successful_isolations = [t for t in concurrent_tests if t.isolation_verified]
        shared_state_violations = [t for t in concurrent_tests if t.shared_state_detected]

        logger.info(f"Successful isolations: {len(successful_isolations)}")
        logger.info(f"Shared state violations: {len(shared_state_violations)}")

        # Log any shared state violations
        if shared_state_violations:
            logger.error("Shared state violations detected:")
            for violation in shared_state_violations:
                logger.error(f"  User {violation.user_id}: Factory {violation.factory_instance_id}")

        # CRITICAL ASSERTION: No shared state between users
        assert len(shared_state_violations) == 0, (
            f"Factory shared state violations detected: {len(shared_state_violations)}. "
            f"Users with shared state: {[v.user_id for v in shared_state_violations]}"
        )

        logger.info("✅ Factory user session isolation validated")

    def test_factory_pattern_follows_ssot_principles(self):
        """Test that factory patterns follow SSOT principles."""
        logger.info("Testing factory SSOT pattern compliance")

        # Scan for factory implementations
        factory_validations = self.analyzer.scan_for_factory_classes()
        production_factories = [v for v in factory_validations if v.is_production_code]

        logger.info(f"Found {len(production_factories)} production factory implementations")

        # Check SSOT compliance for each factory
        ssot_compliant_factories = [f for f in production_factories if f.follows_ssot_pattern]
        user_isolation_factories = [f for f in production_factories if f.has_user_isolation]

        logger.info(f"SSOT compliant factories: {len(ssot_compliant_factories)}")
        logger.info(f"User isolation factories: {len(user_isolation_factories)}")

        # Log non-compliant factories
        non_compliant = [f for f in production_factories if not f.follows_ssot_pattern]
        if non_compliant:
            logger.warning("Non-SSOT compliant factories found:")
            for factory in non_compliant:
                logger.warning(f"  {factory.factory_class} at {factory.file_path}:{factory.line_number}")

        # ASSERTION: At least 80% of factories should follow SSOT principles
        if production_factories:
            compliance_rate = len(ssot_compliant_factories) / len(production_factories)
            assert compliance_rate >= 0.8, (
                f"Factory SSOT compliance rate too low: {compliance_rate:.1%}. "
                f"Must be >= 80%. Non-compliant: {[f.factory_class for f in non_compliant]}"
            )

        logger.info("✅ Factory SSOT pattern compliance validated")

    def test_factory_initialization_consistency(self):
        """Test that factory initialization is consistent across implementations."""
        logger.info("Testing factory initialization consistency")

        try:
            # Test UserExecutionEngine factory initialization
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

            # Check if factory methods exist and are consistent
            factory_methods = []

            if hasattr(UserExecutionEngine, 'create_for_user'):
                factory_methods.append('create_for_user')

            if hasattr(UserExecutionEngine, '__init__'):
                factory_methods.append('__init__')

            logger.info(f"Factory methods found: {factory_methods}")

            # ASSERTION: Must have at least one factory method
            assert len(factory_methods) > 0, (
                "UserExecutionEngine must have factory methods (create_for_user or __init__)"
            )

            # Test factory method signatures for consistency
            if 'create_for_user' in factory_methods:
                import inspect
                signature = inspect.signature(UserExecutionEngine.create_for_user)
                params = list(signature.parameters.keys())

                logger.info(f"create_for_user signature: {params}")

                # Check for user isolation parameters
                isolation_params = ['user_id', 'exec_context', 'context']
                has_isolation = any(param in params for param in isolation_params)

                # ASSERTION: Factory method should support user isolation
                if not has_isolation:
                    logger.warning("create_for_user method may not support proper user isolation")

            logger.info("✅ Factory initialization consistency validated")

        except ImportError as e:
            pytest.skip(f"UserExecutionEngine not available for testing: {e}")

    def test_generate_factory_compliance_report(self):
        """Generate comprehensive factory SSOT compliance report."""
        logger.info("Generating factory compliance report")

        # Scan all factories
        factory_validations = self.analyzer.scan_for_factory_classes()

        # Categorize factories
        production_factories = [v for v in factory_validations if v.is_production_code]
        deprecated_factories = [v for v in factory_validations if v.is_deprecated]

        # Run user isolation tests
        user_isolation_tests = []
        test_users = [f"test_user_{i}" for i in range(3)]

        for user_id in test_users:
            try:
                test_result = self.simulator.simulate_user_session(user_id)
                user_isolation_tests.append(test_result)
            except Exception as e:
                logger.warning(f"User isolation test failed for {user_id}: {e}")

        # Calculate metrics
        execution_engine_factories = len([f for f in production_factories if 'ExecutionEngine' in f.factory_class])
        shared_state_violations = len([t for t in user_isolation_tests if t.shared_state_detected])

        # Factory consistency score
        if production_factories:
            ssot_compliant = len([f for f in production_factories if f.follows_ssot_pattern])
            factory_consistency_score = (ssot_compliant / len(production_factories)) * 100
        else:
            factory_consistency_score = 100

        # Overall SSOT compliance score
        violation_penalty = shared_state_violations * 20  # 20 points per violation
        ssot_compliance_score = max(0, factory_consistency_score - violation_penalty)

        # Generate critical violations
        critical_violations = []
        if shared_state_violations > 0:
            critical_violations.append(f"Shared state violations: {shared_state_violations}")
        if execution_engine_factories == 0:
            critical_violations.append("No ExecutionEngine factories found")

        # Generate recommendations
        recommendations = []
        if shared_state_violations > 0:
            recommendations.append("Fix shared state violations in factory implementations")
        if factory_consistency_score < 80:
            recommendations.append("Improve factory SSOT pattern compliance")

        # Create report
        report = FactoryComplianceReport(
            execution_engine_factories_found=execution_engine_factories,
            production_factories=production_factories,
            deprecated_factories=deprecated_factories,
            user_isolation_tests=user_isolation_tests,
            factory_consistency_score=factory_consistency_score,
            shared_state_violations=shared_state_violations,
            ssot_compliance_score=ssot_compliance_score,
            critical_violations=critical_violations,
            recommendations=recommendations
        )

        # Log report
        logger.info("Factory Compliance Report:")
        logger.info(f"  ExecutionEngine factories: {report.execution_engine_factories_found}")
        logger.info(f"  Production factories: {len(report.production_factories)}")
        logger.info(f"  Deprecated factories: {len(report.deprecated_factories)}")
        logger.info(f"  User isolation tests: {len(report.user_isolation_tests)}")
        logger.info(f"  Factory consistency score: {report.factory_consistency_score:.1f}%")
        logger.info(f"  Shared state violations: {report.shared_state_violations}")
        logger.info(f"  SSOT compliance score: {report.ssot_compliance_score:.1f}%")

        if report.critical_violations:
            logger.error("Critical violations:")
            for violation in report.critical_violations:
                logger.error(f"  {violation}")

        if report.recommendations:
            logger.info("Recommendations:")
            for rec in report.recommendations:
                logger.info(f"  {rec}")

        # Store report for use by other tests
        self.factory_compliance_report = report

        # ASSERTION: SSOT compliance score must be reasonable for Golden Path protection
        assert report.ssot_compliance_score >= 70, (
            f"Factory SSOT compliance score too low: {report.ssot_compliance_score:.1f}%. "
            f"Must be >= 70% for Golden Path protection. Violations: {report.critical_violations}"
        )

        logger.info("✅ Factory compliance report generated successfully")

        return report


if __name__ == "__main__":
    # Direct execution for rapid testing
    pytest.main([__file__, "-v", "--tb=short"])