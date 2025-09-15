"""PHASE 2: UNIFIED ID GENERATOR ADOPTION VALIDATION TESTS

Issue #841: SSOT-ID-Generation-Incomplete-Migration-Authentication-WebSocket-Factories

INTEGRATION PRIORITY: These tests validate UnifiedIdGenerator adoption after SSOT migration.
Tests should PASS after successful migration from uuid.uuid4() to UnifiedIdGenerator patterns.

Post-Migration Validation:
- auth.py uses UnifiedIdGenerator.generate_session_id()
- unified_websocket_auth.py uses UnifiedIdGenerator.generate_connection_id()
- Factory modules use UnifiedIdGenerator.generate_client_id()
- audit_models.py uses UnifiedIdGenerator.generate_audit_id()

Business Value Protection: $500K+ ARR Golden Path SSOT compliance verification
"""
import pytest
import re
import inspect
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

class TestUnifiedIdGeneratorAdoption(SSotBaseTestCase):
    """Integration tests validating UnifiedIdGenerator adoption across all components"""

    def test_auth_session_id_uses_unified_generator_post_migration(self):
        """INTEGRATION: Verify auth.py uses UnifiedIdGenerator for session IDs after migration

        This test validates that auth.py has been successfully migrated from
        uuid.uuid4() to UnifiedIdGenerator.generate_session_id().

        Expected Behavior: POST-MIGRATION SUCCESS
        Pre-Migration: Would fail due to uuid.uuid4() usage
        """
        try:
            from netra_backend.app.auth_integration import auth
            source_code = inspect.getsource(auth)
            unified_import_pattern = 'from\\s+shared\\.id_generation\\.unified_id_generator\\s+import\\s+UnifiedIdGenerator'
            import_found = re.search(unified_import_pattern, source_code)
            assert import_found is not None, f"POST-MIGRATION FAILURE: auth.py should import UnifiedIdGenerator after migration. Missing import: 'from shared.id_generation.unified_id_generator import UnifiedIdGenerator'"
            session_id_pattern = 'generate_session_id\\('
            session_id_usage = re.search(session_id_pattern, source_code)
            assert session_id_usage is not None, f'POST-MIGRATION FAILURE: auth.py should use generate_session_id() after migration. Expected pattern: UnifiedIdGenerator().generate_session_id()'
            uuid4_pattern = 'str\\(uuid\\.uuid4\\(\\)\\)'
            uuid4_usage = re.search(uuid4_pattern, source_code)
            assert uuid4_usage is None, f'MIGRATION INCOMPLETE: auth.py still contains uuid.uuid4() usage. All instances should be replaced with UnifiedIdGenerator patterns.'
            print(f'\n✅ AUTH SSOT MIGRATION VALIDATION SUCCESS:')
            print(f'   ✓ UnifiedIdGenerator import found')
            print(f'   ✓ generate_session_id() usage confirmed')
            print(f'   ✓ uuid.uuid4() patterns removed')
            print(f'   Status: auth.py successfully migrated to SSOT pattern')
        except ImportError as e:
            pytest.fail(f'Cannot import auth module for post-migration validation: {e}')

    def test_websocket_connection_id_uses_unified_generator_post_migration(self):
        """INTEGRATION: Verify WebSocket modules use UnifiedIdGenerator for connection IDs

        This test validates that WebSocket authentication has been successfully
        migrated to use UnifiedIdGenerator.generate_connection_id().

        Expected Behavior: POST-MIGRATION SUCCESS
        Pre-Migration: Would fail due to uuid.uuid4() usage
        """
        try:
            from netra_backend.app.websocket_core import unified_websocket_auth
            source_code = inspect.getsource(unified_websocket_auth)
            unified_import_pattern = 'from\\s+shared\\.id_generation\\.unified_id_generator\\s+import\\s+UnifiedIdGenerator'
            import_found = re.search(unified_import_pattern, source_code)
            assert import_found is not None, f'POST-MIGRATION FAILURE: unified_websocket_auth.py should import UnifiedIdGenerator after migration.'
            connection_id_pattern = 'generate_connection_id\\('
            connection_id_usage = re.search(connection_id_pattern, source_code)
            assert connection_id_usage is not None, f'POST-MIGRATION FAILURE: unified_websocket_auth.py should use generate_connection_id() after migration.'
            uuid4_pattern = 'str\\(uuid\\.uuid4\\(\\)\\)'
            uuid4_usage = re.search(uuid4_pattern, source_code)
            assert uuid4_usage is None, f'MIGRATION INCOMPLETE: unified_websocket_auth.py still contains uuid.uuid4() usage at line ~1303.'
            print(f'\n✅ WEBSOCKET SSOT MIGRATION VALIDATION SUCCESS:')
            print(f'   ✓ UnifiedIdGenerator import found')
            print(f'   ✓ generate_connection_id() usage confirmed')
            print(f'   ✓ uuid.uuid4() patterns removed from line ~1303')
            print(f'   Status: WebSocket auth successfully migrated to SSOT pattern')
        except ImportError as e:
            pytest.fail(f'Cannot import WebSocket auth module for post-migration validation: {e}')

    def test_redis_factory_client_id_uses_unified_generator_post_migration(self):
        """INTEGRATION: Verify Redis factory uses UnifiedIdGenerator for client IDs

        This test validates that Redis factory has been successfully migrated
        from uuid4().hex[:8] to UnifiedIdGenerator.generate_client_id().

        Expected Behavior: POST-MIGRATION SUCCESS
        Pre-Migration: Would fail due to uuid4().hex[:8] usage
        """
        try:
            from netra_backend.app.factories import redis_factory
            source_code = inspect.getsource(redis_factory)
            unified_import_pattern = 'from\\s+shared\\.id_generation\\.unified_id_generator\\s+import\\s+UnifiedIdGenerator'
            import_found = re.search(unified_import_pattern, source_code)
            assert import_found is not None, f'POST-MIGRATION FAILURE: redis_factory.py should import UnifiedIdGenerator after migration.'
            client_id_pattern = 'generate_client_id\\('
            client_id_usage = re.search(client_id_pattern, source_code)
            assert client_id_usage is not None, f'POST-MIGRATION FAILURE: redis_factory.py should use generate_client_id() after migration.'
            uuid4_hex_pattern = 'uuid4\\(\\)\\.hex\\[:8\\]'
            uuid4_hex_usage = re.search(uuid4_hex_pattern, source_code)
            assert uuid4_hex_usage is None, f'MIGRATION INCOMPLETE: redis_factory.py still contains uuid4().hex[:8] usage at line ~594.'
            print(f'\n✅ REDIS FACTORY SSOT MIGRATION VALIDATION SUCCESS:')
            print(f'   ✓ UnifiedIdGenerator import found')
            print(f'   ✓ generate_client_id() usage confirmed')
            print(f'   ✓ uuid4().hex[:8] patterns removed from line ~594')
            print(f'   Status: Redis factory successfully migrated to SSOT pattern')
        except ImportError as e:
            pytest.fail(f'Cannot import Redis factory module for post-migration validation: {e}')

    def test_clickhouse_factory_client_id_uses_unified_generator_post_migration(self):
        """INTEGRATION: Verify ClickHouse factory uses UnifiedIdGenerator for client IDs

        This test validates that ClickHouse factory has been successfully migrated
        from uuid4().hex[:8] to UnifiedIdGenerator.generate_client_id().

        Expected Behavior: POST-MIGRATION SUCCESS
        Pre-Migration: Would fail due to uuid4().hex[:8] usage
        """
        try:
            from netra_backend.app.factories import clickhouse_factory
            source_code = inspect.getsource(clickhouse_factory)
            unified_import_pattern = 'from\\s+shared\\.id_generation\\.unified_id_generator\\s+import\\s+UnifiedIdGenerator'
            import_found = re.search(unified_import_pattern, source_code)
            assert import_found is not None, f'POST-MIGRATION FAILURE: clickhouse_factory.py should import UnifiedIdGenerator after migration.'
            client_id_pattern = 'generate_client_id\\('
            client_id_usage = re.search(client_id_pattern, source_code)
            assert client_id_usage is not None, f'POST-MIGRATION FAILURE: clickhouse_factory.py should use generate_client_id() after migration.'
            uuid4_hex_pattern = 'uuid4\\(\\)\\.hex\\[:8\\]'
            uuid4_hex_usage = re.search(uuid4_hex_pattern, source_code)
            assert uuid4_hex_usage is None, f'MIGRATION INCOMPLETE: clickhouse_factory.py still contains uuid4().hex[:8] usage at line ~522.'
            print(f'\n✅ CLICKHOUSE FACTORY SSOT MIGRATION VALIDATION SUCCESS:')
            print(f'   ✓ UnifiedIdGenerator import found')
            print(f'   ✓ generate_client_id() usage confirmed')
            print(f'   ✓ uuid4().hex[:8] patterns removed from line ~522')
            print(f'   Status: ClickHouse factory successfully migrated to SSOT pattern')
        except ImportError as e:
            pytest.fail(f'Cannot import ClickHouse factory module for post-migration validation: {e}')

    def test_audit_models_id_uses_unified_generator_post_migration(self):
        """INTEGRATION: Verify audit models use UnifiedIdGenerator for audit record IDs

        This test validates that audit models have been successfully migrated
        from uuid.uuid4() to UnifiedIdGenerator.generate_audit_id().

        Expected Behavior: POST-MIGRATION SUCCESS
        Pre-Migration: Would fail due to uuid.uuid4() usage in default_factory
        """
        try:
            from netra_backend.app.schemas import audit_models
            source_code = inspect.getsource(audit_models)
            unified_import_pattern = 'from\\s+shared\\.id_generation\\.unified_id_generator\\s+import\\s+UnifiedIdGenerator'
            import_found = re.search(unified_import_pattern, source_code)
            assert import_found is not None, f'POST-MIGRATION FAILURE: audit_models.py should import UnifiedIdGenerator after migration.'
            audit_id_pattern = 'generate_audit_id\\('
            audit_id_usage = re.search(audit_id_pattern, source_code)
            assert audit_id_usage is not None, f'POST-MIGRATION FAILURE: audit_models.py should use generate_audit_id() in Field default_factory after migration.'
            uuid4_default_pattern = 'Field\\(default_factory=lambda:\\s*str\\(uuid\\.uuid4\\(\\)\\)\\)'
            uuid4_default_usage = re.search(uuid4_default_pattern, source_code)
            assert uuid4_default_usage is None, f'MIGRATION INCOMPLETE: audit_models.py still contains uuid.uuid4() in Field default_factory at line ~41.'
            print(f'\n✅ AUDIT MODELS SSOT MIGRATION VALIDATION SUCCESS:')
            print(f'   ✓ UnifiedIdGenerator import found')
            print(f'   ✓ generate_audit_id() usage confirmed')
            print(f'   ✓ uuid.uuid4() default_factory patterns removed from line ~41')
            print(f'   Status: Audit models successfully migrated to SSOT pattern')
        except ImportError as e:
            pytest.fail(f'Cannot import audit models module for post-migration validation: {e}')

    def test_unified_id_generator_integration_functionality(self):
        """INTEGRATION: Verify UnifiedIdGenerator functions correctly across all use cases

        This test validates that UnifiedIdGenerator provides correct functionality
        for all the migrated components and use cases.

        Expected Behavior: POST-MIGRATION SUCCESS
        Validates: All ID generation methods work correctly and produce SSOT formats
        """
        unified_generator = UnifiedIdGenerator()
        session_id = unified_generator.generate_session_id(user_id='integration_test_user', request_id='integration_test_request')
        session_pattern = re.compile('^sess_[a-zA-Z0-9]+_[a-zA-Z0-9]+_\\d+_[a-f0-9]{8}$')
        assert session_pattern.match(session_id), f"SSOT SESSION ID FORMAT ERROR: '{session_id}' doesn't match expected pattern"
        connection_id = unified_generator.generate_connection_id(user_id='integration_test_user', session_id='integration_test_session')
        connection_pattern = re.compile('^conn_[a-zA-Z0-9]+_[a-zA-Z0-9]+_\\d+_[a-f0-9]{8}$')
        assert connection_pattern.match(connection_id), f"SSOT CONNECTION ID FORMAT ERROR: '{connection_id}' doesn't match expected pattern"
        redis_client_id = unified_generator.generate_client_id(service_type='redis', user_id='integration_test_user', request_id='integration_test_request')
        clickhouse_client_id = unified_generator.generate_client_id(service_type='clickhouse', user_id='integration_test_user', request_id='integration_test_request')
        client_pattern = re.compile('^client_[a-z]+_[a-zA-Z0-9]+_[a-zA-Z0-9]+_\\d+_[a-f0-9]{8}$')
        assert client_pattern.match(redis_client_id), f"SSOT REDIS CLIENT ID FORMAT ERROR: '{redis_client_id}' doesn't match expected pattern"
        assert client_pattern.match(clickhouse_client_id), f"SSOT CLICKHOUSE CLIENT ID FORMAT ERROR: '{clickhouse_client_id}' doesn't match expected pattern"
        audit_id = unified_generator.generate_audit_id(record_type='corpus', user_id='integration_test_user', resource_id='integration_test_resource')
        audit_pattern = re.compile('^audit_[a-z]+_[a-zA-Z0-9]+_\\d+_[a-f0-9]{8}$')
        assert audit_pattern.match(audit_id), f"SSOT AUDIT ID FORMAT ERROR: '{audit_id}' doesn't match expected pattern"
        generated_ids = {'session': session_id, 'connection': connection_id, 'redis_client': redis_client_id, 'clickhouse_client': clickhouse_client_id, 'audit': audit_id}
        unique_ids = set(generated_ids.values())
        assert len(unique_ids) == 5, f'UNIQUENESS FAILURE: Generated {len(unique_ids)}/5 unique IDs. IDs: {list(generated_ids.values())}'
        print(f'\n✅ UNIFIED ID GENERATOR INTEGRATION FUNCTIONALITY SUCCESS:')
        print(f'   ✓ Session ID:     {session_id}')
        print(f'   ✓ Connection ID:  {connection_id}')
        print(f'   ✓ Redis Client:   {redis_client_id}')
        print(f'   ✓ ClickHouse:     {clickhouse_client_id}')
        print(f'   ✓ Audit ID:       {audit_id}')
        print(f'   ✓ All formats valid, all IDs unique')
        print(f'   Status: UnifiedIdGenerator integration fully functional')

    def test_cross_component_id_consistency_post_migration(self):
        """INTEGRATION: Verify ID consistency across all migrated components

        This test validates that all migrated components generate IDs with
        consistent format and predictable correlation capabilities.

        Expected Behavior: POST-MIGRATION SUCCESS
        Validates: Cross-component ID format consistency and correlation
        """
        unified_generator = UnifiedIdGenerator()
        test_user_id = 'consistency_test_user'
        test_request_id = 'consistency_test_request'
        session_id = unified_generator.generate_session_id(user_id=test_user_id, request_id=test_request_id)
        connection_id = unified_generator.generate_connection_id(user_id=test_user_id, session_id=session_id)
        redis_client_id = unified_generator.generate_client_id(service_type='redis', user_id=test_user_id, request_id=test_request_id)
        clickhouse_client_id = unified_generator.generate_client_id(service_type='clickhouse', user_id=test_user_id, request_id=test_request_id)
        audit_id = unified_generator.generate_audit_id(record_type='consistency', user_id=test_user_id, resource_id='consistency_test_resource')
        all_ids = [session_id, connection_id, redis_client_id, clickhouse_client_id, audit_id]

        def extract_user_context(id_string: str) -> str:
            parts = id_string.split('_')
            if len(parts) >= 3:
                return parts[1]
            return 'unknown'
        user_contexts = [extract_user_context(id_str) for id_str in all_ids]
        consistent_user_contexts = all((ctx == 'consistency' for ctx in user_contexts))
        assert consistent_user_contexts, f'CROSS-COMPONENT CONSISTENCY FAILURE: User contexts not consistent: {user_contexts}'

        def extract_timestamp(id_string: str) -> int:
            parts = id_string.split('_')
            for part in parts:
                if part.isdigit() and len(part) >= 10:
                    return int(part)
            return 0
        timestamps = [extract_timestamp(id_str) for id_str in all_ids]
        valid_timestamps = [ts for ts in timestamps if ts > 0]
        assert len(valid_timestamps) == 5, f'TIMESTAMP EXTRACTION FAILURE: Found {len(valid_timestamps)}/5 valid timestamps'
        timestamp_range = max(valid_timestamps) - min(valid_timestamps)
        assert timestamp_range <= 10, f'TIMESTAMP CONSISTENCY FAILURE: {timestamp_range}s range exceeds 10s limit'
        print(f'\n✅ CROSS-COMPONENT ID CONSISTENCY SUCCESS:')
        print(f'   ✓ All IDs contain consistent user context')
        print(f'   ✓ All IDs have valid timestamps within {timestamp_range}s range')
        print(f'   ✓ Session ID:    {session_id}')
        print(f'   ✓ Connection:    {connection_id}')
        print(f'   ✓ Redis:         {redis_client_id}')
        print(f'   ✓ ClickHouse:    {clickhouse_client_id}')
        print(f'   ✓ Audit:         {audit_id}')
        print(f'   Status: Cross-component ID consistency validated')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')