"""
Comprehensive Unit Test Suite for Unified ID Manager SSOT
========================================================

Business Value Protection: $500K+ ARR (Platform ID consistency)
Module: netra_backend/app/core/unified_id_manager.py (820 lines)

This test suite protects critical business functionality:
- Unique ID generation preventing data corruption
- ID format validation preventing system failures
- Metadata management enabling audit trails
- Performance optimization under high load
- Thread safety for concurrent users
- Migration support for format transitions

Test Coverage:
- Unit Tests: 40 tests (14 high difficulty)
- Focus Areas: ID generation, validation, metadata, concurrency, performance
- Business Scenarios: High-volume generation, format migration, thread safety
"""

import pytest
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set
from unittest.mock import Mock, patch

from netra_backend.app.core.unified_id_manager import (
    UnifiedIDManager,
    IDType,
    IDMetadata,
    get_id_manager,
    generate_id,
    generate_user_id,
    generate_session_id,
    generate_request_id,
    generate_agent_id,
    generate_websocket_id,
    generate_execution_id,
    generate_thread_id,
    is_valid_id,
    is_valid_id_format_compatible,
    convert_uuid_to_structured,
    convert_structured_to_uuid,
    validate_and_normalize_id,
    is_valid_id_format
)


class TestUnifiedIDManagerCore:
    """Core ID manager functionality tests"""
    
    def test_initialization_creates_proper_structures(self):
        """Test proper initialization of ID manager structures"""
        manager = UnifiedIDManager()
        
        assert isinstance(manager._id_registry, dict)
        assert isinstance(manager._active_ids, dict)
        assert isinstance(manager._id_counters, dict)
        assert hasattr(manager, '_lock')
        
        # Verify all ID types are initialized
        for id_type in IDType:
            assert id_type in manager._active_ids
            assert id_type in manager._id_counters
            assert manager._id_counters[id_type] == 0
    
    def test_basic_id_generation(self):
        """Test basic ID generation functionality"""
        manager = UnifiedIDManager()
        
        user_id = manager.generate_id(IDType.USER)
        session_id = manager.generate_id(IDType.SESSION)
        
        assert isinstance(user_id, str)
        assert isinstance(session_id, str)
        assert user_id != session_id
        assert "user" in user_id
        assert "session" in session_id
    
    def test_id_generation_with_prefix(self):
        """Test ID generation with custom prefix"""
        manager = UnifiedIDManager()
        
        prefixed_id = manager.generate_id(IDType.AGENT, prefix="test")
        
        assert "test" in prefixed_id
        assert "agent" in prefixed_id
        assert prefixed_id.startswith("test_")
    
    def test_id_generation_with_context(self):
        """Test ID generation with metadata context"""
        manager = UnifiedIDManager()
        
        context = {"environment": "test", "version": "1.0"}
        agent_id = manager.generate_id(IDType.AGENT, context=context)
        
        metadata = manager.get_id_metadata(agent_id)
        assert metadata is not None
        assert metadata.context["environment"] == "test"
        assert metadata.context["version"] == "1.0"
    
    def test_id_counter_increment(self):
        """Test that ID counters increment properly"""
        manager = UnifiedIDManager()
        
        # Generate multiple IDs of same type
        id1 = manager.generate_id(IDType.USER)
        id2 = manager.generate_id(IDType.USER)
        
        assert manager._id_counters[IDType.USER] == 2
        assert id1 != id2
        
        # Counter should be incremented for each type independently
        agent_id = manager.generate_id(IDType.AGENT)
        assert manager._id_counters[IDType.AGENT] == 1
        assert manager._id_counters[IDType.USER] == 2


class TestIDRegistration:
    """Test ID registration and tracking functionality"""
    
    def test_register_existing_id(self):
        """Test registration of existing IDs"""
        manager = UnifiedIDManager()
        
        existing_id = "external_system_123"
        context = {"source": "external", "migrated": True}
        
        success = manager.register_existing_id(existing_id, IDType.USER, context)
        
        assert success is True
        assert existing_id in manager._id_registry
        assert existing_id in manager._active_ids[IDType.USER]
        
        metadata = manager.get_id_metadata(existing_id)
        assert metadata.context["source"] == "external"
        assert metadata.context["migrated"] is True
    
    def test_duplicate_registration_prevention(self):
        """Test that duplicate registration is prevented"""
        manager = UnifiedIDManager()
        
        test_id = "duplicate_test_123"
        
        # First registration should succeed
        success1 = manager.register_existing_id(test_id, IDType.USER)
        assert success1 is True
        
        # Second registration should fail
        success2 = manager.register_existing_id(test_id, IDType.SESSION)
        assert success2 is False
    
    def test_id_metadata_retrieval(self):
        """Test ID metadata retrieval"""
        manager = UnifiedIDManager()
        
        test_id = manager.generate_id(IDType.WEBSOCKET, prefix="test")
        metadata = manager.get_id_metadata(test_id)
        
        assert isinstance(metadata, IDMetadata)
        assert metadata.id_value == test_id
        assert metadata.id_type == IDType.WEBSOCKET
        assert metadata.prefix == "test"
        assert isinstance(metadata.created_at, float)
    
    def test_nonexistent_id_metadata(self):
        """Test metadata retrieval for nonexistent ID"""
        manager = UnifiedIDManager()
        
        metadata = manager.get_id_metadata("nonexistent_id")
        assert metadata is None


class TestIDValidation:
    """Test ID validation functionality - CRITICAL for data integrity"""
    
    def test_valid_id_checking(self):
        """Test validation of registered IDs"""
        manager = UnifiedIDManager()
        
        user_id = manager.generate_id(IDType.USER)
        
        assert manager.is_valid_id(user_id) is True
        assert manager.is_valid_id(user_id, IDType.USER) is True
        assert manager.is_valid_id(user_id, IDType.SESSION) is False
        assert manager.is_valid_id("nonexistent_id") is False
    
    def test_id_format_validation(self):
        """Test ID format validation without registration"""
        manager = UnifiedIDManager()
        
        # Valid UUID format
        uuid_id = str(uuid.uuid4())
        assert manager.is_valid_id_format_compatible(uuid_id) is True
        
        # Valid structured format
        structured_id = "user_1_abcd1234"
        assert manager.is_valid_id_format_compatible(structured_id) is True
        
        # Invalid format
        invalid_id = "invalid-format"
        assert manager.is_valid_id_format_compatible(invalid_id) is False
    
    def test_structured_id_format_detection(self):
        """Test structured ID format detection"""
        manager = UnifiedIDManager()
        
        structured_id = "prefix_user_123_abcd1234"
        uuid_id = str(uuid.uuid4())
        
        assert manager._is_structured_id_format(structured_id) is True
        assert manager._is_structured_id_format(uuid_id) is False
    
    def test_id_type_extraction_from_structured(self):
        """Test ID type extraction from structured format"""
        manager = UnifiedIDManager()
        
        user_id = "test_user_123_abcd1234"
        agent_id = "prefix_agent_456_efgh5678"
        
        user_type = manager._extract_id_type_from_structured(user_id)
        agent_type = manager._extract_id_type_from_structured(agent_id)
        
        assert user_type == IDType.USER
        assert agent_type == IDType.AGENT
    
    def test_enhanced_format_validation_patterns(self):
        """Test enhanced format validation for various patterns"""
        # Test valid patterns
        valid_patterns = [
            str(uuid.uuid4()),  # UUID format
            "user_1_abcd1234",  # Structured format
            "prefix_session_2_efgh5678",  # Structured with prefix
            "pending_auth",  # WebSocket temporary auth
            "test-user-123",  # Test pattern
            "staging-e2e-user-001",  # E2E staging pattern
            "123456789012345678"  # OAuth numeric ID
        ]
        
        for pattern in valid_patterns:
            assert is_valid_id_format(pattern) is True, f"Should be valid: {pattern}"
        
        # Test invalid patterns
        invalid_patterns = [
            "",  # Empty
            "invalid",  # Too simple
            "a",  # Too short
            None,  # None value
            123,  # Non-string
        ]
        
        for pattern in invalid_patterns:
            assert is_valid_id_format(pattern) is False, f"Should be invalid: {pattern}"


class TestIDLifecycleManagement:
    """Test ID lifecycle management - release and cleanup"""
    
    def test_id_release(self):
        """Test ID release from active use"""
        manager = UnifiedIDManager()
        
        test_id = manager.generate_id(IDType.SESSION)
        assert test_id in manager._active_ids[IDType.SESSION]
        
        success = manager.release_id(test_id)
        
        assert success is True
        assert test_id not in manager._active_ids[IDType.SESSION]
        assert test_id in manager._id_registry  # Should remain in registry
        
        # Should have release timestamp
        metadata = manager.get_id_metadata(test_id)
        assert 'released_at' in metadata.context
    
    def test_nonexistent_id_release(self):
        """Test release of nonexistent ID"""
        manager = UnifiedIDManager()
        
        success = manager.release_id("nonexistent_id")
        assert success is False
    
    def test_cleanup_released_ids(self):
        """Test cleanup of old released IDs"""
        manager = UnifiedIDManager()
        
        # Generate and release IDs
        old_ids = []
        for i in range(5):
            id_val = manager.generate_id(IDType.USER, prefix=f"cleanup_{i}")
            manager.release_id(id_val)
            old_ids.append(id_val)
        
        # Manually set old release times
        for id_val in old_ids:
            metadata = manager.get_id_metadata(id_val)
            metadata.context['released_at'] = time.time() - 7200  # 2 hours ago
        
        # Cleanup with 1 hour max age
        cleanup_count = manager.cleanup_released_ids(max_age_seconds=3600)
        
        assert cleanup_count == 5
        for id_val in old_ids:
            assert id_val not in manager._id_registry
    
    def test_active_id_tracking(self):
        """Test active ID tracking and counting"""
        manager = UnifiedIDManager()
        
        # Generate different types of IDs
        user_ids = [manager.generate_id(IDType.USER) for _ in range(3)]
        session_ids = [manager.generate_id(IDType.SESSION) for _ in range(2)]
        
        assert manager.count_active_ids(IDType.USER) == 3
        assert manager.count_active_ids(IDType.SESSION) == 2
        assert manager.count_active_ids(IDType.AGENT) == 0
        
        # Get active IDs
        active_users = manager.get_active_ids(IDType.USER)
        assert len(active_users) == 3
        assert all(uid in active_users for uid in user_ids)


class TestThreadSafetyAndConcurrency:
    """Test thread safety under concurrent access - CRITICAL for multi-user system"""
    
    def test_concurrent_id_generation(self):
        """Test thread-safe concurrent ID generation"""
        manager = UnifiedIDManager()
        generated_ids = []
        errors = []
        
        def generate_worker(worker_id: int):
            try:
                worker_ids = []
                for i in range(10):
                    id_val = manager.generate_id(IDType.USER, prefix=f"worker_{worker_id}")
                    worker_ids.append(id_val)
                generated_ids.extend(worker_ids)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=generate_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0
        assert len(generated_ids) == 50  # 5 workers × 10 IDs each
        assert len(set(generated_ids)) == 50  # All should be unique
    
    def test_concurrent_registration_and_validation(self):
        """Test concurrent registration and validation operations"""
        manager = UnifiedIDManager()
        results = {}
        
        def registration_worker(worker_id: int):
            try:
                # Register external IDs
                for i in range(5):
                    ext_id = f"external_worker_{worker_id}_id_{i}"
                    success = manager.register_existing_id(ext_id, IDType.EXECUTION)
                    results[ext_id] = success
                
                # Validate registered IDs
                for i in range(5):
                    ext_id = f"external_worker_{worker_id}_id_{i}"
                    is_valid = manager.is_valid_id(ext_id)
                    results[f"{ext_id}_valid"] = is_valid
                    
            except Exception as e:
                results[f"worker_{worker_id}_error"] = str(e)
        
        # Run concurrent workers
        threads = []
        for i in range(3):
            thread = threading.Thread(target=registration_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        error_keys = [k for k in results.keys() if "error" in k]
        assert len(error_keys) == 0
        
        # Verify all registrations succeeded
        registration_results = [v for k, v in results.items() if k.startswith("external_") and not k.endswith("_valid")]
        assert all(registration_results)
    
    def test_concurrent_cleanup_operations(self):
        """Test thread safety of cleanup operations"""
        manager = UnifiedIDManager()
        
        # Generate IDs in multiple threads
        def id_generator():
            for i in range(20):
                id_val = manager.generate_id(IDType.TRACE, prefix="cleanup")
                manager.release_id(id_val)
        
        # Cleanup in separate thread
        cleanup_results = []
        def cleanup_worker():
            for _ in range(3):
                count = manager.cleanup_released_ids(max_age_seconds=0)
                cleanup_results.append(count)
                time.sleep(0.01)
        
        # Run concurrently
        gen_thread = threading.Thread(target=id_generator)
        cleanup_thread = threading.Thread(target=cleanup_worker)
        
        gen_thread.start()
        cleanup_thread.start()
        
        gen_thread.join()
        cleanup_thread.join()
        
        # Should complete without errors
        assert len(cleanup_results) == 3
        assert all(isinstance(count, int) for count in cleanup_results)


class TestFormatConversion:
    """Test ID format conversion functionality - supports migration"""
    
    def test_uuid_to_structured_conversion(self):
        """Test UUID to structured format conversion"""
        test_uuid = str(uuid.uuid4())
        
        structured_id = UnifiedIDManager.convert_uuid_to_structured(
            test_uuid, IDType.USER, prefix="migrated"
        )
        
        assert "migrated" in structured_id
        assert "user" in structured_id
        assert test_uuid[:8].replace('-', '') in structured_id
    
    def test_structured_to_uuid_conversion(self):
        """Test structured to UUID format conversion (lossy)"""
        structured_id = "test_session_123_abcd1234"
        
        uuid_result = UnifiedIDManager.convert_structured_to_uuid(structured_id)
        
        assert uuid_result is not None
        assert len(uuid_result) == 36  # Standard UUID length with dashes
        assert "abcd1234" in uuid_result
    
    def test_invalid_format_conversion(self):
        """Test conversion with invalid formats"""
        # Invalid UUID
        with pytest.raises(ValueError):
            UnifiedIDManager.convert_uuid_to_structured("not-a-uuid", IDType.USER)
        
        # Invalid structured format
        invalid_structured = "invalid_format"
        uuid_result = UnifiedIDManager.convert_structured_to_uuid(invalid_structured)
        assert uuid_result is None
    
    def test_migration_registration(self):
        """Test registering UUIDs as structured format for migration"""
        manager = UnifiedIDManager()
        test_uuid = str(uuid.uuid4())
        
        structured_id = manager.register_uuid_as_structured(
            test_uuid, IDType.WEBSOCKET, context={"migrated": True}
        )
        
        assert manager.is_valid_id(structured_id)
        metadata = manager.get_id_metadata(structured_id)
        assert metadata.context["migrated"] is True
    
    def test_id_normalization(self):
        """Test ID validation and normalization"""
        manager = UnifiedIDManager()
        
        # Valid UUID should be normalized to structured if type provided
        test_uuid = str(uuid.uuid4())
        is_valid, normalized = manager.validate_and_normalize_id(test_uuid, IDType.AGENT)
        
        assert is_valid is True
        assert normalized is not None
        if normalized != test_uuid:  # If conversion occurred
            assert "agent" in normalized


class TestClassMethodCompatibility:
    """Test class methods for compatibility with existing systems - CRITICAL for startup"""
    
    def test_generate_run_id_with_thread_id(self):
        """Test run ID generation with embedded thread ID"""
        thread_id = "test-thread-123"
        
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        assert run_id.startswith("run_")
        assert thread_id in run_id
        assert len(run_id.split('_')) >= 4  # run_thread_timestamp_uuid
    
    def test_extract_thread_id_from_run_id(self):
        """Test thread ID extraction from run ID - CRITICAL for WebSocket cleanup"""
        # Test UnifiedIDManager format
        original_thread_id = "test-thread-456"
        run_id = UnifiedIDManager.generate_run_id(original_thread_id)
        
        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted_thread_id == original_thread_id
        
        # Test UnifiedIdGenerator format (SSOT pattern support)
        generator_run_id = "websocket_factory_1757372478799"
        extracted_generator = UnifiedIDManager.extract_thread_id(generator_run_id)
        assert "thread_" in extracted_generator
        assert generator_run_id in extracted_generator
    
    def test_validate_run_id_format(self):
        """Test run ID format validation"""
        # Valid run ID
        valid_run_id = "run_thread123_12345_abcd1234"
        assert UnifiedIDManager.validate_run_id(valid_run_id) is True
        
        # Invalid run IDs
        invalid_ids = [
            "",
            "not_run_format",
            "run_only_two_parts",
            "run_thread_timestamp"  # Missing UUID part
        ]
        
        for invalid_id in invalid_ids:
            assert UnifiedIDManager.validate_run_id(invalid_id) is False
    
    def test_parse_run_id_components(self):
        """Test run ID parsing into components"""
        run_id = "run_complex_thread_id_67890_efgh5678"
        
        parsed = UnifiedIDManager.parse_run_id(run_id)
        
        assert parsed['valid'] is True
        assert parsed['thread_id'] == "complex_thread_id"
        assert parsed['timestamp'] == "67890"
        assert parsed['uuid_part'] == "efgh5678"
    
    def test_generate_thread_id_class_method(self):
        """Test class method thread ID generation"""
        thread_id = UnifiedIDManager.generate_thread_id()
        
        assert isinstance(thread_id, str)
        assert "session_" in thread_id
        assert len(thread_id.split('_')) == 3  # session_timestamp_uuid


class TestStatisticsAndMonitoring:
    """Test statistics and monitoring functionality"""
    
    def test_id_manager_statistics(self):
        """Test comprehensive statistics reporting"""
        manager = UnifiedIDManager()
        
        # Generate various IDs
        manager.generate_id(IDType.USER)
        manager.generate_id(IDType.USER)
        manager.generate_id(IDType.SESSION)
        manager.generate_id(IDType.AGENT)
        
        stats = manager.get_stats()
        
        assert 'total_registered' in stats
        assert 'active_by_type' in stats
        assert 'counters_by_type' in stats
        assert 'total_active' in stats
        
        assert stats['active_by_type']['user'] == 2
        assert stats['active_by_type']['session'] == 1
        assert stats['active_by_type']['agent'] == 1
        assert stats['total_active'] == 4
        assert stats['counters_by_type']['user'] == 2
    
    def test_counter_reset_functionality(self):
        """Test counter reset (use with caution)"""
        manager = UnifiedIDManager()
        
        # Generate some IDs
        manager.generate_id(IDType.USER)
        manager.generate_id(IDType.SESSION)
        
        assert manager._id_counters[IDType.USER] == 1
        assert manager._id_counters[IDType.SESSION] == 1
        
        # Reset counters
        manager.reset_counters()
        
        assert manager._id_counters[IDType.USER] == 0
        assert manager._id_counters[IDType.SESSION] == 0
    
    def test_clear_all_functionality(self):
        """Test clearing all IDs (use with caution)"""
        manager = UnifiedIDManager()
        
        # Generate some data
        manager.generate_id(IDType.USER)
        manager.generate_id(IDType.SESSION)
        
        assert len(manager._id_registry) > 0
        assert manager.count_active_ids(IDType.USER) > 0
        
        # Clear all
        manager.clear_all()
        
        assert len(manager._id_registry) == 0
        assert manager.count_active_ids(IDType.USER) == 0
        assert all(count == 0 for count in manager._id_counters.values())


class TestConvenienceFunctions:
    """Test module-level convenience functions"""
    
    def test_global_manager_singleton(self):
        """Test global ID manager singleton"""
        manager1 = get_id_manager()
        manager2 = get_id_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, UnifiedIDManager)
    
    def test_convenience_generate_functions(self):
        """Test convenience generation functions"""
        user_id = generate_user_id()
        session_id = generate_session_id()
        request_id = generate_request_id()
        agent_id = generate_agent_id()
        websocket_id = generate_websocket_id()
        execution_id = generate_execution_id()
        thread_id = generate_thread_id()
        
        ids = [user_id, session_id, request_id, agent_id, websocket_id, execution_id, thread_id]
        
        # All should be unique
        assert len(set(ids)) == len(ids)
        
        # Should contain appropriate type strings
        assert "user" in user_id
        assert "session" in session_id
        assert "request" in request_id
        assert "agent" in agent_id
        assert "websocket" in websocket_id
        assert "execution" in execution_id
        assert "thread" in thread_id
    
    def test_convenience_validation_functions(self):
        """Test convenience validation functions"""
        manager = get_id_manager()
        test_id = manager.generate_id(IDType.USER)
        
        # Should be valid through convenience function
        assert is_valid_id(test_id) is True
        assert is_valid_id(test_id, IDType.USER) is True
        assert is_valid_id_format_compatible(test_id) is True
    
    def test_convenience_conversion_functions(self):
        """Test convenience conversion functions"""
        test_uuid = str(uuid.uuid4())
        
        structured = convert_uuid_to_structured(test_uuid, IDType.SESSION)
        uuid_back = convert_structured_to_uuid(structured)
        
        assert "session" in structured
        assert uuid_back is not None
        
        is_valid, normalized = validate_and_normalize_id(test_uuid, IDType.SESSION)
        assert is_valid is True
        assert normalized is not None


class TestPerformanceOptimizations:
    """Test performance under high load - prevents system degradation"""
    
    def test_high_volume_id_generation(self):
        """Test performance with high volume ID generation"""
        manager = UnifiedIDManager()
        start_time = time.time()
        
        # Generate many IDs
        generated_ids = []
        for i in range(1000):
            id_val = manager.generate_id(IDType.EXECUTION, prefix=f"perf_{i}")
            generated_ids.append(id_val)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time
        assert duration < 2.0  # 2 seconds for 1000 IDs
        assert len(generated_ids) == 1000
        assert len(set(generated_ids)) == 1000  # All unique
    
    def test_metadata_access_performance(self):
        """Test metadata access performance"""
        manager = UnifiedIDManager()
        
        # Generate IDs with metadata
        ids_with_metadata = []
        for i in range(100):
            context = {"iteration": i, "batch": "performance_test"}
            id_val = manager.generate_id(IDType.METRIC, context=context)
            ids_with_metadata.append(id_val)
        
        start_time = time.time()
        
        # Access metadata for all IDs
        for id_val in ids_with_metadata:
            metadata = manager.get_id_metadata(id_val)
            assert metadata is not None
            assert metadata.context["batch"] == "performance_test"
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should be fast
        assert duration < 1.0  # 1 second for 100 metadata lookups
    
    def test_memory_usage_optimization(self):
        """Test memory usage remains reasonable"""
        manager = UnifiedIDManager()
        
        # Generate and release many IDs
        for i in range(500):
            id_val = manager.generate_id(IDType.TEMPORARY)
            if i % 2 == 0:  # Release every other ID
                manager.release_id(id_val)
        
        # Clean up released IDs
        manager.cleanup_released_ids(max_age_seconds=0)
        
        # Should have cleaned up appropriately
        active_count = manager.count_active_ids(IDType.TEMPORARY)
        assert active_count <= 250  # Roughly half should remain active
        
        stats = manager.get_stats()
        assert stats['total_registered'] <= 250  # Cleaned up IDs should be gone


class TestBusinessScenarios:
    """Test complete business scenarios - protects $500K+ ARR"""
    
    def test_user_session_lifecycle(self):
        """Test complete user session ID lifecycle"""
        manager = UnifiedIDManager()
        
        # 1. Generate user ID
        user_id = manager.generate_id(IDType.USER, context={"source": "registration"})
        assert manager.is_valid_id(user_id, IDType.USER)
        
        # 2. Generate session ID for user
        session_context = {"user_id": user_id, "login_time": time.time()}
        session_id = manager.generate_id(IDType.SESSION, context=session_context)
        
        # 3. Generate multiple request IDs for session
        request_ids = []
        for i in range(5):
            request_context = {"session_id": session_id, "request_number": i}
            request_id = manager.generate_id(IDType.REQUEST, context=request_context)
            request_ids.append(request_id)
        
        # 4. Verify all IDs are valid and tracked
        assert all(manager.is_valid_id(req_id, IDType.REQUEST) for req_id in request_ids)
        assert manager.count_active_ids(IDType.REQUEST) >= 5
        
        # 5. Session ends - release session and request IDs
        manager.release_id(session_id)
        for req_id in request_ids:
            manager.release_id(req_id)
        
        # 6. Verify release
        assert session_id not in manager._active_ids[IDType.SESSION]
        assert all(req_id not in manager._active_ids[IDType.REQUEST] for req_id in request_ids)
    
    def test_agent_execution_workflow(self):
        """Test agent execution ID workflow"""
        manager = UnifiedIDManager()
        
        # 1. Generate thread ID for chat conversation
        thread_id = manager.generate_id(IDType.THREAD, 
                                      context={"user_id": "user-123", "chat_type": "optimization"})
        
        # 2. Generate run ID using class method (compatibility)
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # 3. Generate agent execution ID
        agent_context = {"thread_id": thread_id, "run_id": run_id, "agent_type": "optimizer"}
        agent_id = manager.generate_id(IDType.AGENT, context=agent_context)
        
        # 4. Generate execution context ID
        execution_context = {"agent_id": agent_id, "phase": "data_analysis"}
        execution_id = manager.generate_id(IDType.EXECUTION, context=execution_context)
        
        # 5. Verify thread ID extraction works
        extracted_thread = UnifiedIDManager.extract_thread_id(run_id)
        assert thread_id in extracted_thread or extracted_thread == thread_id
        
        # 6. Verify all components are properly linked through metadata
        agent_metadata = manager.get_id_metadata(agent_id)
        execution_metadata = manager.get_id_metadata(execution_id)
        
        assert agent_metadata.context["thread_id"] == thread_id
        assert execution_metadata.context["agent_id"] == agent_id
    
    def test_websocket_connection_management(self):
        """Test WebSocket connection ID management"""
        manager = UnifiedIDManager()
        
        # 1. User connects - generate connection ID
        connection_context = {
            "user_id": "user-789", 
            "connection_time": time.time(),
            "client_info": {"browser": "Chrome", "version": "91"}
        }
        websocket_id = manager.generate_id(IDType.WEBSOCKET, 
                                         prefix="conn", context=connection_context)
        
        # 2. Multiple message transactions
        transaction_ids = []
        for i in range(10):
            tx_context = {"websocket_id": websocket_id, "message_number": i}
            tx_id = manager.generate_id(IDType.TRANSACTION, context=tx_context)
            transaction_ids.append(tx_id)
        
        # 3. User disconnects - release all associated IDs
        manager.release_id(websocket_id)
        for tx_id in transaction_ids:
            manager.release_id(tx_id)
        
        # 4. Verify proper cleanup tracking
        ws_metadata = manager.get_id_metadata(websocket_id)
        assert 'released_at' in ws_metadata.context
        
        # 5. Later cleanup should remove old connection data
        for tx_id in transaction_ids:
            tx_metadata = manager.get_id_metadata(tx_id)
            tx_metadata.context['released_at'] = time.time() - 7200  # 2 hours ago
        
        cleanup_count = manager.cleanup_released_ids(max_age_seconds=3600)
        assert cleanup_count >= 10  # Should clean up the transactions
    
    def test_format_migration_scenario(self):
        """Test migration from UUID to structured format - supports legacy systems"""
        manager = UnifiedIDManager()
        
        # 1. Existing system has UUID format IDs
        legacy_uuids = [str(uuid.uuid4()) for _ in range(5)]
        
        # 2. Register legacy UUIDs with structured equivalents
        migrated_ids = []
        for i, legacy_uuid in enumerate(legacy_uuids):
            structured_id = manager.register_uuid_as_structured(
                legacy_uuid, IDType.USER, 
                context={"legacy_uuid": legacy_uuid, "migration_batch": i}
            )
            migrated_ids.append(structured_id)
        
        # 3. Verify both formats are recognized during transition
        for legacy_uuid in legacy_uuids:
            assert is_valid_id_format(legacy_uuid) is True
        
        for structured_id in migrated_ids:
            assert manager.is_valid_id(structured_id, IDType.USER) is True
        
        # 4. New IDs use structured format
        new_user_id = manager.generate_id(IDType.USER, prefix="new")
        assert manager._is_structured_id_format(new_user_id) is True
        
        # 5. Normalization works for both formats
        for legacy_uuid in legacy_uuids:
            is_valid, normalized = manager.validate_and_normalize_id(legacy_uuid, IDType.USER)
            assert is_valid is True
            # May be converted to structured format
            assert normalized is not None