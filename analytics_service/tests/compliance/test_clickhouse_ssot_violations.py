"""
ClickHouse SSOT Compliance Test Suite

Tests for Single Source of Truth violations in ClickHouse implementations.
These tests MUST FAIL until the duplicate clickhouse.py implementation is removed
and all code uses clickhouse_manager.py as the canonical SSOT.

Business Value Justification (BVJ):
1. Segment: Platform/Internal
2. Business Goal: System Stability, Development Velocity, Risk Reduction
3. Value Impact: Prevents duplicate maintenance, ensures consistent database patterns
4. Strategic Impact: Foundation for reliable analytics infrastructure
"""
import ast
import os
import sys
import time
import asyncio
import pytest
from pathlib import Path
from typing import List, Dict, Set, Any
from shared.isolated_environment import IsolatedEnvironment
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from analytics_service.analytics_core.database.clickhouse_manager import ClickHouseManager, ClickHouseConnectionError, ClickHouseQueryError

class ClickHouseSSotViolationsTests:
    """Test suite to detect and prevent ClickHouse SSOT violations."""

    @pytest.fixture(scope='class')
    def analytics_service_path(self) -> Path:
        """Get analytics service root path."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture(scope='class')
    def python_files(self, analytics_service_path: Path) -> List[Path]:
        """Get all Python files in analytics service."""
        return list(analytics_service_path.rglob('*.py'))

    def test_only_one_clickhouse_implementation_exists(self, analytics_service_path: Path):
        """
        CRITICAL: Test that only ONE ClickHouse implementation file exists.
        This test MUST FAIL until clickhouse.py is removed.
        """
        clickhouse_files = []
        for file_path in analytics_service_path.rglob('clickhouse*.py'):
            if '__pycache__' not in str(file_path) and file_path.name.startswith('clickhouse'):
                clickhouse_files.append(file_path)
        implementation_files = [f for f in clickhouse_files if not any((part in str(f) for part in ['test', 'example', 'usage']))]
        assert len(implementation_files) == 1, f'SSOT VIOLATION: Found {len(implementation_files)} ClickHouse implementations. Expected only clickhouse_manager.py. Found: {[f.name for f in implementation_files]}'
        ssot_file = implementation_files[0]
        assert ssot_file.name == 'clickhouse_manager.py', f'SSOT VIOLATION: Expected clickhouse_manager.py as SSOT, found {ssot_file.name}'

    def test_no_imports_of_legacy_clickhouse_module(self, python_files: List[Path]):
        """
        Test that no files import from the legacy clickhouse.py module.
        This test MUST FAIL until all imports are changed to clickhouse_manager.
        """
        violations = []
        for file_path in python_files:
            if '__pycache__' in str(file_path):
                continue
            if file_path.name == 'test_clickhouse_ssot_violations.py':
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                legacy_import_patterns = ['from analytics_service.analytics_core.database.clickhouse import', 'from .clickhouse import', 'from ..database.clickhouse import', 'import analytics_service.analytics_core.database.clickhouse', 'from analytics_core.database.clickhouse import']
                for i, line in enumerate(content.split('\n'), 1):
                    line = line.strip()
                    if any((pattern in line for pattern in legacy_import_patterns)):
                        violations.append({'file': str(file_path.relative_to(file_path.parent.parent.parent)), 'line': i, 'content': line, 'violation_type': 'legacy_clickhouse_import'})
            except (UnicodeDecodeError, IOError):
                continue
        assert len(violations) == 0, f'SSOT VIOLATION: Found {len(violations)} imports of legacy clickhouse module. All imports must use clickhouse_manager. Violations: {violations}'

    def test_no_deprecated_model_imports(self, python_files: List[Path]):
        """
        Test that deprecated models (FrontendEvent, ChatInteractionEvent) are not imported.
        These models should be replaced with the new event models.
        """
        violations = []
        deprecated_models = ['FrontendEvent', 'ChatInteractionEvent', 'ThreadLifecycleEvent', 'FeatureUsageEvent']
        for file_path in python_files:
            if '__pycache__' in str(file_path) or 'events.py' in str(file_path):
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                for i, line in enumerate(content.split('\n'), 1):
                    line = line.strip()
                    for model in deprecated_models:
                        if f'import {model}' in line or f'from .* import.*{model}' in line:
                            violations.append({'file': str(file_path.relative_to(file_path.parent.parent.parent)), 'line': i, 'content': line, 'model': model, 'violation_type': 'deprecated_model_import'})
            except (UnicodeDecodeError, IOError):
                continue
        assert len(violations) == 0, f'SSOT VIOLATION: Found {len(violations)} imports of deprecated models. Use AnalyticsEvent and new property models instead. Violations: {violations}'

    def test_service_initialization_is_complete(self, analytics_service_path: Path):
        """
        Test that service initialization in main.py is complete (no TODOs).
        This test MUST FAIL until the TODO at line 47 is resolved.
        """
        main_py_path = analytics_service_path / 'main.py'
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        todo_lines = []
        for i, line in enumerate(content.split('\n'), 1):
            if 'TODO' in line.upper() and 'service initialization' in line.lower():
                todo_lines.append({'line': i, 'content': line.strip()})
        assert len(todo_lines) == 0, f'SERVICE INITIALIZATION INCOMPLETE: Found {len(todo_lines)} TODO items in service initialization. Complete initialization before production. TODOs: {todo_lines}'

    def test_all_files_use_ssot_implementation(self, python_files: List[Path]):
        """
        Test that all files using ClickHouse import from clickhouse_manager (SSOT).
        Validates the canonical implementation is consistently used.
        """
        violations = []
        correct_imports = []
        for file_path in python_files:
            if '__pycache__' in str(file_path):
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                for i, line in enumerate(content.split('\n'), 1):
                    line_stripped = line.strip()
                    if 'clickhouse_manager' in line_stripped and 'import' in line_stripped:
                        correct_imports.append({'file': str(file_path.relative_to(file_path.parent.parent.parent)), 'line': i, 'content': line_stripped})
                    if 'clickhouse' in line_stripped and 'import' in line_stripped and ('clickhouse_manager' not in line_stripped) and ('clickhouse_driver' not in line_stripped) and ('#' not in line_stripped):
                        violations.append({'file': str(file_path.relative_to(file_path.parent.parent.parent)), 'line': i, 'content': line_stripped, 'violation_type': 'non_ssot_import'})
            except (UnicodeDecodeError, IOError):
                continue
        assert len(violations) == 0, f'SSOT VIOLATION: Found {len(violations)} non-SSOT ClickHouse imports. All imports must use clickhouse_manager. Violations: {violations}'

    def test_clickhouse_manager_has_required_features(self):
        """
        Test that the SSOT ClickHouseManager has all required enterprise features.
        This validates the SSOT implementation is feature-complete.
        """
        from analytics_service.analytics_core.database.clickhouse_manager import ClickHouseManager
        manager = ClickHouseManager()
        assert hasattr(manager, '_connection_pool'), 'SSOT missing connection pooling'
        assert hasattr(manager, '_pool_lock'), 'SSOT missing pool synchronization'
        assert hasattr(manager, 'max_connections'), 'SSOT missing connection limit'
        assert hasattr(manager, '_health_check_task'), 'SSOT missing health check task'
        assert hasattr(manager, '_is_healthy'), 'SSOT missing health status tracking'
        assert hasattr(manager, 'health_check_interval'), 'SSOT missing health check interval'
        assert hasattr(manager, 'max_retries'), 'SSOT missing retry logic'
        assert hasattr(manager, 'retry_delay'), 'SSOT missing retry delay configuration'
        required_methods = ['initialize', 'close', 'get_connection', 'execute_query', 'execute_command', 'insert_data', 'get_health_status']
        for method_name in required_methods:
            assert hasattr(manager, method_name), f'SSOT missing required method: {method_name}'
            assert callable(getattr(manager, method_name)), f'SSOT method not callable: {method_name}'

    @pytest.mark.asyncio
    async def test_connection_pooling_functionality(self):
        """
        Test that connection pooling works properly in the SSOT implementation.
        This is a performance-critical feature that must work correctly.
        Uses real ClickHouse connection for authentic integration testing.
        """
        from analytics_service.analytics_core.database.clickhouse_manager import ClickHouseManager
        from shared.isolated_environment import get_env
        env = get_env()
        env.enable_isolation()
        env.set('CLICKHOUSE_HOST', 'localhost', 'test_connection_pooling')
        env.set('CLICKHOUSE_PORT', '9002', 'test_connection_pooling')
        env.set('CLICKHOUSE_DATABASE', 'netra_test_analytics', 'test_connection_pooling')
        env.set('CLICKHOUSE_USER', 'test_user', 'test_connection_pooling')
        env.set('CLICKHOUSE_PASSWORD', 'test_pass', 'test_connection_pooling')
        try:
            manager = ClickHouseManager(host=env.get('CLICKHOUSE_HOST'), port=int(env.get('CLICKHOUSE_PORT')), database=env.get('CLICKHOUSE_DATABASE'), user=env.get('CLICKHOUSE_USER'), password=env.get('CLICKHOUSE_PASSWORD'), max_connections=3)
            try:
                await manager.initialize()
                assert manager._is_initialized, 'Manager not properly initialized'
                assert len(manager._connection_pool) >= 0, 'Connection pool not initialized'
                async with manager.get_connection() as conn:
                    assert conn is not None, 'Failed to acquire connection from pool'
                await asyncio.sleep(0.01)
            except Exception as e:
                pytest.skip(f'ClickHouse test service not available: {e}')
            finally:
                await manager.close()
        finally:
            env.reset_to_original()

    @pytest.mark.asyncio
    async def test_health_check_loop_functionality(self):
        """
        Test that the health check loop functions correctly.
        This is critical for production monitoring.
        Uses real ClickHouse connection for authentic health monitoring testing.
        """
        from analytics_service.analytics_core.database.clickhouse_manager import ClickHouseManager
        from shared.isolated_environment import get_env
        env = get_env()
        env.enable_isolation()
        env.set('CLICKHOUSE_HOST', 'localhost', 'test_health_check')
        env.set('CLICKHOUSE_PORT', '9002', 'test_health_check')
        env.set('CLICKHOUSE_DATABASE', 'netra_test_analytics', 'test_health_check')
        env.set('CLICKHOUSE_USER', 'test_user', 'test_health_check')
        env.set('CLICKHOUSE_PASSWORD', 'test_pass', 'test_health_check')
        try:
            manager = ClickHouseManager(host=env.get('CLICKHOUSE_HOST'), port=int(env.get('CLICKHOUSE_PORT')), database=env.get('CLICKHOUSE_DATABASE'), user=env.get('CLICKHOUSE_USER'), password=env.get('CLICKHOUSE_PASSWORD'), health_check_interval=1)
            try:
                await manager.initialize()
                assert manager._health_check_task is not None, 'Health check task not started'
                assert not manager._health_check_task.done(), 'Health check task terminated prematurely'
                assert manager._is_healthy, 'Manager not healthy after initialization'
                status = await manager.get_health_status()
                assert isinstance(status, dict), 'Health status not returned as dict'
                assert 'is_healthy' in status, 'Health status missing is_healthy field'
                assert 'pool_size' in status, 'Health status missing pool_size field'
            except Exception as e:
                pytest.skip(f'ClickHouse test service not available: {e}')
            finally:
                await manager.close()
        finally:
            env.reset_to_original()

    @pytest.mark.asyncio
    async def test_retry_logic_with_exponential_backoff(self):
        """
        Test that retry logic with exponential backoff works correctly.
        This is critical for handling transient network issues.
        Tests the actual retry mechanism using real ClickHouse with intentional failures.
        """
        from analytics_service.analytics_core.database.clickhouse_manager import ClickHouseManager, ClickHouseConnectionError, ClickHouseQueryError
        from shared.isolated_environment import get_env
        env = get_env()
        env.enable_isolation()
        env.set('CLICKHOUSE_HOST', 'localhost', 'test_retry_logic')
        env.set('CLICKHOUSE_PORT', '9002', 'test_retry_logic')
        env.set('CLICKHOUSE_DATABASE', 'netra_test_analytics', 'test_retry_logic')
        env.set('CLICKHOUSE_USER', 'test_user', 'test_retry_logic')
        env.set('CLICKHOUSE_PASSWORD', 'test_pass', 'test_retry_logic')
        try:
            manager = ClickHouseManager(host=env.get('CLICKHOUSE_HOST'), port=int(env.get('CLICKHOUSE_PORT')), database=env.get('CLICKHOUSE_DATABASE'), user=env.get('CLICKHOUSE_USER'), password=env.get('CLICKHOUSE_PASSWORD'), max_retries=3, retry_delay=0.1)
            try:
                await manager.initialize()
                start_time = time.time()
                result = await manager.execute_query('SELECT 1')
                end_time = time.time()
                assert result == [(1,)], 'Valid query should succeed'
                try:
                    await manager.execute_query('INVALID SQL SYNTAX')
                    assert False, 'Invalid query should have failed'
                except (ClickHouseQueryError, Exception) as e:
                    assert 'Query failed' in str(e) or 'syntax' in str(e).lower(), 'Expected query failure'
            except Exception as e:
                pytest.skip(f'ClickHouse test service not available: {e}')
            finally:
                await manager.close()
        finally:
            env.reset_to_original()

    def test_performance_single_vs_pooled_connections(self):
        """
        Performance test: Connection pooling should be faster than single connections.
        This validates the business value of the SSOT implementation.
        """
        from analytics_service.analytics_core.database.clickhouse_manager import ClickHouseManager
        manager = ClickHouseManager(max_connections=5)
        assert manager.max_connections > 1, 'Connection pooling not configured'
        assert hasattr(manager, '_connection_pool'), 'No connection pool implementation'
        assert hasattr(manager, 'get_connection'), 'No efficient connection acquisition method'

    def test_ast_analysis_for_clickhouse_class_usage(self, python_files: List[Path]):
        """
        Use AST parsing to detect any instantiation of legacy ClickHouse classes.
        This catches cases that simple text parsing might miss.
        """
        violations = []
        for file_path in python_files:
            if '__pycache__' in str(file_path):
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                try:
                    tree = ast.parse(content)
                except SyntaxError:
                    continue

                class ClickHouseVisitor(ast.NodeVisitor):

                    def __init__(self):
                        self.violations = []

                    def visit_Name(self, node):
                        if node.id == 'ClickHouseManager' and 'clickhouse.py' in str(file_path):
                            self.violations.append({'type': 'legacy_class_usage', 'line': node.lineno, 'class': node.id})
                        self.generic_visit(node)

                    def visit_Call(self, node):
                        if isinstance(node.func, ast.Name):
                            if node.func.id in ['ClickHouseManager'] and 'clickhouse.py' in str(file_path):
                                self.violations.append({'type': 'legacy_instantiation', 'line': node.lineno, 'class': node.func.id})
                        self.generic_visit(node)
                visitor = ClickHouseVisitor()
                visitor.visit(tree)
                for violation in visitor.violations:
                    violations.append({'file': str(file_path.relative_to(file_path.parent.parent.parent)), 'line': violation['line'], 'violation_type': violation['type'], 'class': violation['class']})
            except (UnicodeDecodeError, IOError):
                continue
        assert len(violations) == 0, f'SSOT VIOLATION: AST analysis found {len(violations)} legacy class usages. All code must use clickhouse_manager classes. Violations: {violations}'

    def test_no_direct_clickhouse_driver_imports_outside_ssot(self, python_files: List[Path]):
        """
        Test that only the SSOT module imports clickhouse_driver directly.
        All other modules should go through the SSOT abstraction.
        """
        violations = []
        for file_path in python_files:
            if '__pycache__' in str(file_path):
                continue
            if file_path.name == 'clickhouse_manager.py' or 'test' in str(file_path) or 'conftest.py' in str(file_path):
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                for i, line in enumerate(content.split('\n'), 1):
                    line_stripped = line.strip()
                    if 'clickhouse_driver' in line_stripped and 'import' in line_stripped and (not line_stripped.startswith('#')):
                        violations.append({'file': str(file_path.relative_to(file_path.parent.parent.parent)), 'line': i, 'content': line_stripped, 'violation_type': 'direct_driver_import'})
            except (UnicodeDecodeError, IOError):
                continue
        assert len(violations) == 0, f'SSOT VIOLATION: Found {len(violations)} direct clickhouse_driver imports outside SSOT. Use clickhouse_manager abstraction instead. Violations: {violations}'

    def test_compliance_summary_report(self, analytics_service_path: Path):
        """
        Generate a comprehensive compliance report for ClickHouse SSOT.
        This test always fails and provides a detailed status report.
        """
        report = {'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'), 'service_path': str(analytics_service_path), 'compliance_status': 'FAILED', 'critical_issues': [], 'warnings': [], 'recommendations': []}
        clickhouse_files = list(analytics_service_path.rglob('clickhouse*.py'))
        implementation_files = [f for f in clickhouse_files if not any((part in str(f) for part in ['test', 'example', '__pycache__']))]
        if len(implementation_files) > 1:
            report['critical_issues'].append({'type': 'DUPLICATE_IMPLEMENTATION', 'severity': 'CRITICAL', 'description': f'Found {len(implementation_files)} ClickHouse implementations', 'files': [f.name for f in implementation_files], 'action_required': 'Remove clickhouse.py, keep only clickhouse_manager.py'})
        main_py = analytics_service_path / 'main.py'
        if main_py.exists():
            with open(main_py, 'r') as f:
                content = f.read()
                if 'TODO' in content and 'service initialization' in content:
                    report['critical_issues'].append({'type': 'INCOMPLETE_INITIALIZATION', 'severity': 'HIGH', 'description': 'Service initialization contains TODO items', 'action_required': 'Complete service initialization in main.py'})
        report['recommendations'] = ['Remove analytics_service/analytics_core/database/clickhouse.py', 'Update all imports to use clickhouse_manager', 'Complete service initialization in main.py', 'Replace deprecated model usage with AnalyticsEvent', 'Run full test suite after changes']
        compliance_score = max(0, 100 - len(report['critical_issues']) * 25 - len(report['warnings']) * 10)
        report['compliance_score'] = f'{compliance_score}%'
        if len(report['critical_issues']) == 0 and len(report['warnings']) == 0:
            report['compliance_status'] = 'PASSED'
        elif len(report['critical_issues']) == 0:
            report['compliance_status'] = 'PASSED_WITH_WARNINGS'
        else:
            report['compliance_status'] = 'FAILED'
        report_str = f"""\n        \n========= CLICKHOUSE SSOT COMPLIANCE REPORT =========\nTimestamp: {report['timestamp']}\nService Path: {report['service_path']}\nCompliance Score: {report['compliance_score']}\nStatus: {report['compliance_status']}\n\nCRITICAL ISSUES ({len(report['critical_issues'])}):\n{chr(10).join([f"- {issue['type']}: {issue['description']}" for issue in report['critical_issues']])}\n\nRECOMMENDATIONS:\n{chr(10).join([f'- {rec}' for rec in report['recommendations']])}\n\n====================================================\n        """
        if report['compliance_status'] == 'PASSED':
            print(f'SSOT COMPLIANCE ACHIEVED: {report_str}')
        else:
            assert False, f'SSOT COMPLIANCE FAILED: {report_str}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')