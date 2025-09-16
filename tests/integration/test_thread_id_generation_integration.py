"""
Integration tests for thread ID generation flow.

Tests the complete flow from thread creation API through UnifiedIDManager
to ensure contract compliance and SSOT patterns work correctly.

This test addresses the Five Whys root cause by implementing real integration
testing instead of mocked components.
"""
import pytest
import asyncio
from unittest.mock import Mock
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType, get_id_manager, generate_thread_id
from netra_backend.app.core.id_generation_contracts import validate_id_generation_contracts, IDContractValidator
from netra_backend.app.routes.utils.thread_creators import generate_thread_id as thread_creator_generate_id, prepare_thread_metadata

@pytest.mark.integration
class ThreadIDGenerationIntegrationTests:
    """Integration tests for thread ID generation patterns"""

    def test_unified_id_manager_thread_support(self):
        """Test that UnifiedIDManager supports THREAD IDType"""
        assert hasattr(IDType, 'THREAD')
        assert IDType.THREAD.value == 'thread'
        id_manager = get_id_manager()
        thread_id = id_manager.generate_id(IDType.THREAD)
        assert thread_id is not None
        assert isinstance(thread_id, str)
        assert len(thread_id) > 0
        assert 'thread' in thread_id

    def test_class_method_generate_thread_id(self):
        """Test that UnifiedIDManager.generate_thread_id() class method works"""
        thread_id = UnifiedIDManager.generate_thread_id()
        assert thread_id is not None
        assert isinstance(thread_id, str)
        assert len(thread_id) > 0
        assert 'session' in thread_id

    def test_module_level_convenience_function(self):
        """Test module-level generate_thread_id() convenience function"""
        thread_id = generate_thread_id()
        assert thread_id is not None
        assert isinstance(thread_id, str)
        assert len(thread_id) > 0
        assert 'thread' in thread_id

    def test_thread_creators_integration(self):
        """Test thread_creators.py uses correct UnifiedIDManager pattern"""
        thread_id = thread_creator_generate_id()
        assert thread_id is not None
        assert isinstance(thread_id, str)
        assert len(thread_id) > 0
        assert 'thread' in thread_id
        assert not thread_id.startswith('thread_thread')
        assert not thread_id.startswith('thread_session')

    def test_thread_metadata_preparation(self):
        """Test thread metadata preparation with generated ID"""
        mock_thread_data = Mock()
        mock_thread_data.metadata = {}
        mock_thread_data.title = 'Test Thread'
        user_id = 'test_user_123'
        metadata = prepare_thread_metadata(mock_thread_data, user_id)
        assert metadata is not None
        assert metadata['user_id'] == user_id
        assert metadata['title'] == 'Test Thread'
        assert metadata['status'] == 'active'
        assert 'created_at' in metadata

    def test_id_uniqueness_across_methods(self):
        """Test that all ID generation methods produce unique IDs"""
        ids_generated = set()
        id_manager = get_id_manager()
        for _ in range(5):
            thread_id = id_manager.generate_id(IDType.THREAD)
            assert thread_id not in ids_generated
            ids_generated.add(thread_id)
        for _ in range(5):
            thread_id = UnifiedIDManager.generate_thread_id()
            assert thread_id not in ids_generated
            ids_generated.add(thread_id)
        for _ in range(5):
            thread_id = generate_thread_id()
            assert thread_id not in ids_generated
            ids_generated.add(thread_id)
        for _ in range(5):
            thread_id = thread_creator_generate_id()
            assert thread_id not in ids_generated
            ids_generated.add(thread_id)
        assert len(ids_generated) == 20

    def test_contract_validation_passes(self):
        """Test that all ID generation contracts are satisfied"""
        results = validate_id_generation_contracts()
        assert results['valid'] is True
        assert len(results['missing_methods']) == 0
        assert len(results['signature_mismatches']) == 0
        expected_checks = ['instance.generate_id', 'class.generate_run_id', 'class.generate_thread_id']
        for expected in expected_checks:
            assert expected in results['checked_methods']

    def test_id_manager_registry_functionality(self):
        """Test that generated IDs are properly registered and trackable"""
        id_manager = get_id_manager()
        thread_id = id_manager.generate_id(IDType.THREAD, context={'test': 'integration'})
        assert id_manager.is_valid_id(thread_id)
        assert id_manager.is_valid_id(thread_id, IDType.THREAD)
        metadata = id_manager.get_id_metadata(thread_id)
        assert metadata is not None
        assert metadata.id_type == IDType.THREAD
        assert metadata.context['test'] == 'integration'
        active_thread_ids = id_manager.get_active_ids(IDType.THREAD)
        assert thread_id in active_thread_ids
        assert id_manager.release_id(thread_id) is True
        active_thread_ids_after = id_manager.get_active_ids(IDType.THREAD)
        assert thread_id not in active_thread_ids_after

    def test_error_handling_for_invalid_patterns(self):
        """Test error handling for invalid ID generation patterns"""
        id_manager = get_id_manager()
        with pytest.raises((AttributeError, ValueError, KeyError)):
            id_manager.generate_id('INVALID')

    def test_concurrent_thread_id_generation(self):
        """Test thread ID generation under concurrent access"""
        import threading
        import time
        ids_generated = set()
        lock = threading.Lock()

        def generate_concurrent_ids():
            for _ in range(10):
                thread_id = thread_creator_generate_id()
                with lock:
                    ids_generated.add(thread_id)
                time.sleep(0.001)
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=generate_concurrent_ids)
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        assert len(ids_generated) == 30

    def test_backward_compatibility_patterns(self):
        """Test that both old and new patterns work during transition"""
        id_manager = get_id_manager()
        new_pattern_id = id_manager.generate_id(IDType.THREAD)
        class_method_id = UnifiedIDManager.generate_thread_id()
        convenience_id = generate_thread_id()
        assert new_pattern_id != class_method_id
        assert new_pattern_id != convenience_id
        assert class_method_id != convenience_id
        assert all((isinstance(id_val, str) and len(id_val) > 0 for id_val in [new_pattern_id, class_method_id, convenience_id]))

@pytest.mark.integration
class ContractValidationTests:
    """Tests for contract validation system"""

    def test_contract_validator_initialization(self):
        """Test that contract validator initializes properly"""
        validator = IDContractValidator()
        assert validator is not None
        assert len(validator._contracts) > 0

    def test_contract_definitions_completeness(self):
        """Test that all expected contracts are defined"""
        validator = IDContractValidator()
        contracts = validator._contracts
        expected_contracts = {'generate_id', 'generate_run_id', 'generate_thread_id', 'module_generate_thread_id'}
        assert set(contracts.keys()) == expected_contracts

    def test_validate_specific_contracts(self):
        """Test validation of specific contract requirements"""
        validator = IDContractValidator()
        generate_id_contract = validator._contracts['generate_id']
        assert generate_id_contract.is_instance_method is True
        assert generate_id_contract.is_class_method is False
        assert 'id_type' in generate_id_contract.required_parameters
        class_method_contract = validator._contracts['generate_thread_id']
        assert class_method_contract.is_class_method is True
        assert class_method_contract.is_instance_method is False
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')