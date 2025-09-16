"""
Test suite for ClickHouse SSOT (Single Source of Truth) compliance.
Ensures that only ONE canonical ClickHouse client implementation exists.
References: CLAUDE.md Section 2.1, SPEC/clickhouse_client_architecture.xml
"""
import os
import re
import glob
import ast
import pytest
from pathlib import Path
from typing import List, Set
from shared.isolated_environment import IsolatedEnvironment
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class ClickHouseSSOTComplianceTests:
    """Test suite ensuring Single Source of Truth for ClickHouse clients."""

    @pytest.fixture
    def project_root(self):
        """Get the project root directory."""
        current_dir = Path(__file__).parent
        while current_dir.name != 'netra-core-generation-1' and current_dir.parent != current_dir:
            current_dir = current_dir.parent
        return current_dir

    def test_no_duplicate_clickhouse_clients(self, project_root):
        """Ensure no duplicate ClickHouse client implementations exist."""
        client_files = []
        forbidden_patterns = ['class\\s+\\w*ClickHouse\\w*Client', 'class\\s+\\w*ClickHouse\\w*Database\\w*Client']
        backend_path = project_root / 'netra_backend' / 'app'
        for py_file in backend_path.rglob('*.py'):
            if 'test' in str(py_file).lower():
                continue
            if str(py_file).endswith('clickhouse.py') and 'app/db' in str(py_file):
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in forbidden_patterns:
                        if re.search(pattern, content):
                            client_files.append(str(py_file))
                            break
            except Exception:
                continue
        assert len(client_files) == 0, f'SSOT Violation: Found {len(client_files)} duplicate ClickHouse client implementations:\n{chr(10).join(client_files)}\nAll ClickHouse operations must use get_clickhouse_client() from netra_backend/app/db/clickhouse.py'

    def test_no_test_logic_in_production(self, project_root):
        """Ensure no test/mock logic exists in production ClickHouse code."""
        canonical_file = project_root / 'netra_backend' / 'app' / 'db' / 'clickhouse.py'
        if not canonical_file.exists():
            pytest.skip('Canonical ClickHouse implementation not found')
        with open(canonical_file, 'r', encoding='utf-8') as f:
            content = f.read()
        forbidden_patterns = [('_simulate_\\w+', 'Found _simulate_* test methods in production'), ('class\\s+Mock\\w*ClickHouse', 'Found Mock* classes in production'), ('# This is what gets mocked', 'Found test-related comments in production'), ('if\\s+.*is_testing.*:', 'Found test environment checks affecting logic')]
        violations = []
        for pattern, message in forbidden_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(message)
        assert len(violations) == 0, f'Test logic found in production ClickHouse code:\n{chr(10).join(violations)}\nMove all test logic to test fixtures in netra_backend/tests/'

    def test_all_imports_use_canonical_client(self, project_root):
        """Ensure all ClickHouse imports use the canonical implementation."""
        forbidden_imports = ['from netra_backend.app.db.clickhouse_client import', 'from netra_backend.app.db.client_clickhouse import', 'from netra_backend.app.db.clickhouse import', 'import netra_backend.app.db.clickhouse_client', 'import netra_backend.app.db.client_clickhouse']
        violations = []
        backend_path = project_root / 'netra_backend'
        for py_file in backend_path.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for forbidden in forbidden_imports:
                        if forbidden in content:
                            violations.append(f'{py_file}: {forbidden}')
            except Exception:
                continue
        assert len(violations) == 0, f'Found {len(violations)} files importing non-canonical ClickHouse clients:\n{chr(10).join(violations)}\nAll imports must use: from netra_backend.app.db.clickhouse import get_clickhouse_client'

    def test_canonical_client_has_required_features(self, project_root):
        """Ensure the canonical client has all required enterprise features."""
        canonical_file = project_root / 'netra_backend' / 'app' / 'db' / 'clickhouse.py'
        if not canonical_file.exists():
            pytest.skip('Canonical ClickHouse implementation not found')
        with open(canonical_file, 'r', encoding='utf-8') as f:
            content = f.read()
        required_features = [('get_clickhouse_client', 'Missing main context manager entry point'), ('execute_with_retry', 'Missing retry logic with exponential backoff'), ('UnifiedCircuitBreaker', 'Missing circuit breaker pattern'), ('ClickHouseCache', 'Missing caching functionality'), ('check_health', 'Missing health check capability'), ('async def', 'Missing async/await support'), ('ssl_context', 'Missing SSL/TLS support')]
        missing_features = []
        for feature, message in required_features:
            if feature not in content:
                missing_features.append(message)
        assert len(missing_features) == 0, f'Canonical ClickHouse client missing required features:\n{chr(10).join(missing_features)}\nSee SPEC/clickhouse_client_architecture.xml for requirements'

    def test_no_direct_client_instantiation(self, project_root):
        """Ensure no direct instantiation of ClickHouse client classes."""
        forbidden_patterns = ['ClickHouseClient\\s*\\(', 'ClickHouseDatabaseClient\\s*\\(', 'ClickHouse.*Client\\s*\\(']
        violations = []
        backend_path = project_root / 'netra_backend' / 'app'
        for py_file in backend_path.rglob('*.py'):
            if 'test' in str(py_file).lower():
                continue
            if str(py_file).endswith('clickhouse.py') and 'app/db' in str(py_file):
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in forbidden_patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            violations.append(f'{py_file}: {matches}')
            except Exception:
                continue
        assert len(violations) == 0, f'Found direct client instantiation in {len(violations)} files:\n{chr(10).join((str(v) for v in violations))}\nUse get_clickhouse_client() context manager instead'

    def test_removed_files_do_not_exist(self, project_root):
        """Ensure all duplicate ClickHouse client files have been removed."""
        files_that_should_not_exist = ['netra_backend/app/db/clickhouse_client.py', 'netra_backend/app/db/client_clickhouse.py', 'netra_backend/app/agents/data_sub_agent/clickhouse_client.py']
        existing_files = []
        for file_path in files_that_should_not_exist:
            full_path = project_root / file_path
            if full_path.exists():
                existing_files.append(file_path)
        assert len(existing_files) == 0, f'Duplicate ClickHouse client files still exist:\n{chr(10).join(existing_files)}\nThese files violate SSOT and must be removed'

    def test_spec_documentation_exists(self, project_root):
        """Ensure ClickHouse architecture specification exists."""
        spec_file = project_root / 'SPEC' / 'clickhouse_client_architecture.xml'
        assert spec_file.exists(), 'Missing SPEC/clickhouse_client_architecture.xml\nThis specification is required to document the canonical implementation'
        with open(spec_file, 'r', encoding='utf-8') as f:
            content = f.read()
        required_sections = ['<canonical_implementation>', '<usage_patterns>', '<prohibited_patterns>', '<compliance_checks>', '<business_value_justification>']
        missing_sections = []
        for section in required_sections:
            if section not in content:
                missing_sections.append(section)
        assert len(missing_sections) == 0, f'ClickHouse spec missing required sections:\n{chr(10).join(missing_sections)}'

class ClickHouseRegressionPreventionTests:
    """Tests to prevent regression of ClickHouse SSOT violations."""

    def test_import_patterns_enforced(self):
        """Ensure correct import patterns are used."""
        from netra_backend.app.db.clickhouse import get_clickhouse_client
        assert callable(get_clickhouse_client), 'get_clickhouse_client must be callable'

    def test_context_manager_works(self):
        """Test that the context manager pattern works correctly."""
        import asyncio
        from netra_backend.app.db.clickhouse import get_clickhouse_client

        async def test_context():
            async with get_clickhouse_client() as client:
                assert client is not None
                assert hasattr(client, 'execute') or hasattr(client, 'query')
        try:
            asyncio.run(test_context())
        except Exception as e:
            pytest.fail(f'Context manager failed: {e}')

    def test_service_interface_available(self):
        """Ensure service interface is available for non-context usage."""
        from netra_backend.app.db.clickhouse import get_clickhouse_service
        service = get_clickhouse_service()
        assert service is not None, 'ClickHouse service must be available'
        assert hasattr(service, 'check_health'), 'Service must have health check'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')