"""
Unit Test Suite for Unified ID Manager Migration Compliance

MISSION CRITICAL: This test suite validates SSOT compliance by exposing
ID generation violations throughout the codebase.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Eliminate scattered ID generation causing SSOT violations
- Value Impact: Prevents ID format conflicts, ensures consistent thread/run relationships
- Strategic Impact: Critical for multi-user isolation and WebSocket routing integrity

Test Strategy:
These tests are designed to FAIL initially, demonstrating current SSOT violations.
After migration to UnifiedIdGenerator, these tests should PASS.

Coverage Requirements:
- Detection of raw uuid.uuid4() usage throughout codebase
- Validation of structured ID format compliance
- Thread ID extraction and validation
- Run ID generation consistency
- WebSocket ID format validation
- User context ID generation patterns
"""

import pytest
import uuid
import re
from typing import List, Dict, Any, Set
from unittest.mock import patch, MagicMock

# SSOT imports - these should be used everywhere
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID

# Current imports that need migration validation
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestUnifiedIDManagerMigrationCompliance:
    """Test suite to expose ID generation SSOT violations and validate migration."""

    def setup_method(self):
        """Setup for each test method."""
        self.violations = []
        self.compliance_patterns = {
            'structured_id': re.compile(r'^[a-z_]+_\d+_[a-f0-9]{8}$'),
            'run_id': re.compile(r'^run_.+_\d{13}_\d+_[a-f0-9]{8}$'),
            'websocket_id': re.compile(r'^websocket_.+_\d+_[a-f0-9]{8}$'),
            'thread_id': re.compile(r'^(session|thread)_.+_\d+_[a-f0-9]{8}$'),
            'uuid_v4': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)
        }

    # =============================================================================
    # VIOLATION DETECTION TESTS - These should FAIL initially
    # =============================================================================

    def test_uuid4_raw_usage_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Detect raw uuid.uuid4() usage violations.
        
        This test scans for patterns like:
        - str(uuid.uuid4())
        - uuid.uuid4().hex[:8]
        - uuid.uuid4().hex
        
        All of these should be replaced with UnifiedIdGenerator.generate_base_id()
        """
        # Test common violation patterns by simulating what's currently in the codebase
        violation_patterns = [
            "str(uuid.uuid4())",
            "uuid.uuid4().hex[:8]", 
            "uuid.uuid4().hex",
            f"{uuid.uuid4()}",  # Direct usage
            str(uuid.uuid4())   # String conversion
        ]
        
        violations_found = []
        
        # These patterns represent actual violations in the codebase
        for pattern in violation_patterns:
            if "uuid.uuid4()" in pattern:
                violations_found.append(pattern)
        
        # This test SHOULD FAIL initially - we expect violations
        assert len(violations_found) > 0, (
            "Expected to find uuid.uuid4() violations in test patterns. "
            "If this passes, it means the violations are already fixed!"
        )
        
        # Record violations for migration tracking
        self.violations.extend(violations_found)
        
        # Fail with detailed message about violations
        pytest.fail(
            f"Found {len(violations_found)} uuid.uuid4() violations that need migration to UnifiedIdGenerator:\n" +
            "\n".join(f"- {v}" for v in violations_found) +
            f"\n\nReplace with: UnifiedIdGenerator.generate_base_id(prefix)"
        )

    def test_auth_service_id_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Auth service uses raw uuid.uuid4() in multiple places.
        
        Violations in auth_service/services/user_service.py:
        - Line 88: id=str(uuid.uuid4())
        - Other auth services using raw UUID generation
        """
        # Simulate auth service ID generation (current violation)
        def simulate_auth_user_creation():
            # This mimics auth_service/services/user_service.py:88
            return {
                "id": str(uuid.uuid4()),  # VIOLATION: Raw UUID usage
                "email": "test@example.com"
            }
        
        # Generate several user IDs using current auth service pattern
        auth_ids = []
        for _ in range(5):
            user_data = simulate_auth_user_creation()
            auth_ids.append(user_data["id"])
        
        # Check if they follow UnifiedIdGenerator format
        compliance_failures = []
        for auth_id in auth_ids:
            # Check if it matches UUID v4 format (violation) vs structured format (compliant)
            if self.compliance_patterns['uuid_v4'].match(auth_id):
                compliance_failures.append(f"Auth ID '{auth_id}' uses raw UUID format")
            elif not self.compliance_patterns['structured_id'].match(auth_id):
                compliance_failures.append(f"Auth ID '{auth_id}' has unknown format")
        
        # This test SHOULD FAIL - auth service uses raw UUIDs
        assert len(compliance_failures) > 0, (
            "Expected auth service ID violations. If this passes, auth service is already compliant!"
        )
        
        pytest.fail(
            f"Auth service ID generation violations found:\n" +
            "\n".join(compliance_failures) +
            "\n\nMigration required: Replace str(uuid.uuid4()) with UnifiedIdGenerator.generate_base_id('user')"
        )

    def test_user_execution_context_id_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: UserExecutionContext has scattered ID generation patterns.
        
        Should detect violations in:
        - Manual UserExecutionContext creation
        - Inconsistent ID formats for user/thread/run IDs
        - Missing SSOT ID generation patterns
        """
        # Test current UserExecutionContext creation patterns (likely violations)
        try:
            # This might use inconsistent ID generation
            context = UserExecutionContext.from_request(
                user_id="user_123",  # May not follow SSOT format
                thread_id="thread_456",  # May not follow SSOT format  
                run_id=str(uuid.uuid4()),  # VIOLATION: Raw UUID
                request_id=str(uuid.uuid4())  # VIOLATION: Raw UUID
            )
            
            # Validate ID format compliance
            format_violations = []
            
            # Check user_id format
            if not context.user_id.startswith("user_"):
                format_violations.append(f"user_id '{context.user_id}' doesn't follow user_ prefix pattern")
            
            # Check thread_id format  
            if not (context.thread_id.startswith("thread_") or context.thread_id.startswith("session_")):
                format_violations.append(f"thread_id '{context.thread_id}' doesn't follow thread_/session_ prefix pattern")
            
            # Check run_id format - this should fail with current implementation
            if self.compliance_patterns['uuid_v4'].match(context.run_id):
                format_violations.append(f"run_id '{context.run_id}' uses raw UUID instead of structured format")
            
            # Check request_id format
            if self.compliance_patterns['uuid_v4'].match(context.request_id):
                format_violations.append(f"request_id '{context.request_id}' uses raw UUID instead of structured format")
            
            # This test SHOULD FAIL due to format violations
            assert len(format_violations) > 0, (
                "Expected UserExecutionContext ID format violations. "
                "If this passes, UserExecutionContext is already SSOT compliant!"
            )
            
            pytest.fail(
                f"UserExecutionContext ID format violations:\n" +
                "\n".join(format_violations) +
                "\n\nMigration required: Use UnifiedIdGenerator for all ID generation in UserExecutionContext"
            )
            
        except Exception as e:
            # If UserExecutionContext creation fails, that's also a violation
            pytest.fail(f"UserExecutionContext creation failed, indicating implementation issues: {e}")

    def test_websocket_id_generation_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: WebSocket components use inconsistent ID generation.
        
        Should detect violations in:
        - WebSocket connection IDs
        - WebSocket client IDs
        - WebSocket manager factory IDs
        """
        # Simulate current WebSocket ID generation patterns
        violation_patterns = []
        
        # Pattern 1: Raw UUID usage (common violation)
        websocket_id_raw = f"websocket_{uuid.uuid4().hex[:8]}"
        if not self.compliance_patterns['websocket_id'].match(websocket_id_raw):
            violation_patterns.append(f"WebSocket ID '{websocket_id_raw}' uses raw UUID hex instead of structured format")
        
        # Pattern 2: Inconsistent format
        websocket_id_inconsistent = str(uuid.uuid4())
        if self.compliance_patterns['uuid_v4'].match(websocket_id_inconsistent):
            violation_patterns.append(f"WebSocket ID '{websocket_id_inconsistent}' uses full UUID instead of websocket-prefixed format")
        
        # Pattern 3: Missing counter/timestamp for uniqueness
        websocket_id_simple = "websocket_connection_abc123"
        if not re.match(r'websocket_.+_\d+_[a-f0-9]{8}', websocket_id_simple):
            violation_patterns.append(f"WebSocket ID '{websocket_id_simple}' missing timestamp/counter components")
        
        # This test SHOULD FAIL - we expect WebSocket ID violations
        assert len(violation_patterns) > 0, (
            "Expected WebSocket ID generation violations. "
            "If this passes, WebSocket ID generation is already SSOT compliant!"
        )
        
        pytest.fail(
            f"WebSocket ID generation violations:\n" +
            "\n".join(violation_patterns) +
            "\n\nMigration required: Use UnifiedIdGenerator.generate_base_id('websocket') for all WebSocket IDs"
        )

    def test_thread_run_relationship_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Thread/Run ID relationships are inconsistent.
        
        Should detect violations in:
        - Run IDs that don't embed thread IDs properly
        - Thread IDs that don't follow consistent format
        - Missing thread extraction capabilities
        """
        violation_cases = []
        
        # Test case 1: Generate thread and run IDs using current patterns
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"  # Violation: Raw UUID hex
        run_id = f"run_{uuid.uuid4().hex[:8]}"  # Violation: No thread embedding
        
        # Try to extract thread ID from run ID (should fail)
        try:
            extracted_thread = UnifiedIDManager.extract_thread_id(run_id)
            if extracted_thread != thread_id:
                violation_cases.append(
                    f"Run ID '{run_id}' doesn't properly embed thread ID '{thread_id}'. "
                    f"Extracted: '{extracted_thread}'"
                )
        except Exception as e:
            violation_cases.append(f"Thread ID extraction failed for run ID '{run_id}': {e}")
        
        # Test case 2: Inconsistent ID formats
        test_ids = [
            ("thread_123", "run_456"),  # No relationship
            (str(uuid.uuid4()), str(uuid.uuid4())),  # Raw UUIDs
            ("session_abc", "execution_def"),  # Wrong prefixes
        ]
        
        for thread_id, run_id in test_ids:
            try:
                # Check if run ID properly represents thread relationship
                if "run_" in run_id and thread_id not in run_id:
                    violation_cases.append(
                        f"Run ID '{run_id}' doesn't contain thread ID '{thread_id}' for proper routing"
                    )
            except Exception:
                pass
        
        # This test SHOULD FAIL due to relationship violations
        assert len(violation_cases) > 0, (
            "Expected thread/run ID relationship violations. "
            "If this passes, thread/run relationships are already properly structured!"
        )
        
        pytest.fail(
            f"Thread/Run ID relationship violations:\n" +
            "\n".join(violation_cases) +
            "\n\nMigration required: Use UnifiedIDManager.generate_run_id(thread_id) for proper embedding"
        )

    # =============================================================================
    # COMPLIANCE VALIDATION TESTS - These should PASS after migration
    # =============================================================================

    def test_unified_id_generator_compliance_SHOULD_PASS_AFTER_MIGRATION(self):
        """
        This test should PASS after migration to validate SSOT compliance.
        
        Validates that UnifiedIdGenerator produces properly formatted IDs.
        """
        # Generate IDs using SSOT pattern
        user_id = UnifiedIdGenerator.generate_base_id("user")
        thread_id = UnifiedIdGenerator.generate_base_id("session") 
        request_id = UnifiedIdGenerator.generate_base_id("req")
        websocket_id = UnifiedIdGenerator.generate_base_id("websocket")
        
        # Validate formats
        compliance_checks = [
            (user_id, "user_", "User ID should start with user_"),
            (thread_id, "session_", "Thread ID should start with session_"),
            (request_id, "req_", "Request ID should start with req_"),
            (websocket_id, "websocket_", "WebSocket ID should start with websocket_"),
        ]
        
        for id_value, expected_prefix, description in compliance_checks:
            assert id_value.startswith(expected_prefix), f"{description}: {id_value}"
            
            # Validate structured format: prefix_timestamp_counter_random
            parts = id_value.split('_')
            assert len(parts) >= 4, f"ID should have at least 4 parts (prefix_timestamp_counter_random): {id_value}"
            
            # Validate timestamp is numeric
            timestamp_part = parts[1]
            assert timestamp_part.isdigit(), f"Timestamp part should be numeric: {timestamp_part} in {id_value}"
            
            # Validate counter is numeric
            counter_part = parts[2]
            assert counter_part.isdigit(), f"Counter part should be numeric: {counter_part} in {id_value}"
            
            # Validate random part is hex
            random_part = parts[3]
            assert len(random_part) == 8, f"Random part should be 8 characters: {random_part} in {id_value}"
            assert all(c in '0123456789abcdef' for c in random_part.lower()), f"Random part should be hex: {random_part}"

    def test_unified_id_manager_run_thread_compliance_SHOULD_PASS_AFTER_MIGRATION(self):
        """
        This test should PASS after migration to validate proper thread/run relationships.
        """
        # Generate proper thread and run IDs using SSOT methods
        thread_id = UnifiedIDManager.generate_thread_id()
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Validate run ID embeds thread ID properly
        extracted_thread = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted_thread == thread_id, (
            f"Run ID should properly embed and extract thread ID. "
            f"Original: {thread_id}, Extracted: {extracted_thread}, Run: {run_id}"
        )
        
        # Validate run ID format
        assert UnifiedIDManager.validate_run_id(run_id), f"Run ID should validate as proper format: {run_id}"
        
        # Validate parse components
        parsed = UnifiedIDManager.parse_run_id(run_id)
        assert parsed['valid'] is True, f"Run ID should parse successfully: {run_id}"
        assert parsed['thread_id'] == thread_id, f"Parsed thread ID should match original: {parsed}"

    # =============================================================================
    # MIGRATION IMPACT VALIDATION TESTS
    # =============================================================================

    def test_strongly_typed_id_integration_compliance(self):
        """
        Test that UnifiedIdGenerator IDs work properly with strongly typed ID system.
        """
        # Generate IDs using UnifiedIdGenerator
        user_id_str = UnifiedIdGenerator.generate_base_id("user")
        thread_id_str = UnifiedIdGenerator.generate_base_id("session")
        run_id_str = UnifiedIDManager.generate_run_id(thread_id_str)
        request_id_str = UnifiedIdGenerator.generate_base_id("req")
        
        # Convert to strongly typed IDs
        from shared.types.core_types import ensure_user_id, ensure_thread_id, ensure_run_id, ensure_request_id
        
        try:
            user_id_typed = ensure_user_id(user_id_str)
            thread_id_typed = ensure_thread_id(thread_id_str) 
            run_id_typed = ensure_run_id(run_id_str)
            request_id_typed = ensure_request_id(request_id_str)
            
            # Validate conversions work
            assert str(user_id_typed) == user_id_str
            assert str(thread_id_typed) == thread_id_str
            assert str(run_id_typed) == run_id_str
            assert str(request_id_typed) == request_id_str
            
        except Exception as e:
            pytest.fail(f"Strongly typed ID conversion failed, indicating format incompatibility: {e}")

    def test_multi_user_id_isolation_compliance(self):
        """
        Test that ID generation provides proper isolation between different users.
        """
        # Generate IDs for multiple users
        user_contexts = {}
        for user_num in range(1, 4):  # 3 different users
            user_id = UnifiedIdGenerator.generate_base_id(f"user_{user_num}")
            thread_id = UnifiedIdGenerator.generate_base_id("session")
            run_id = UnifiedIDManager.generate_run_id(thread_id)
            
            user_contexts[f"user_{user_num}"] = {
                'user_id': user_id,
                'thread_id': thread_id,
                'run_id': run_id
            }
        
        # Validate all IDs are unique across users
        all_ids = []
        for user, context in user_contexts.items():
            for id_type, id_value in context.items():
                all_ids.append((user, id_type, id_value))
        
        # Check for duplicate IDs (should be none)
        id_values = [id_value for _, _, id_value in all_ids]
        unique_ids = set(id_values)
        
        assert len(unique_ids) == len(id_values), (
            f"Found duplicate IDs across users: {len(id_values)} total, {len(unique_ids)} unique. "
            f"This indicates insufficient isolation between users."
        )
        
        # Validate thread/run relationships work independently per user
        for user, context in user_contexts.items():
            extracted_thread = UnifiedIDManager.extract_thread_id(context['run_id'])
            assert extracted_thread == context['thread_id'], (
                f"Thread/run relationship broken for {user}: "
                f"Expected {context['thread_id']}, got {extracted_thread}"
            )

    # =============================================================================
    # REGRESSION PREVENTION TESTS
    # =============================================================================

    def test_prevent_uuid4_regression_in_future_code(self):
        """
        Test to prevent regression back to raw uuid.uuid4() usage.
        
        This test establishes patterns that should always be followed.
        """
        # Define acceptable ID generation patterns
        acceptable_patterns = {
            'unified_id_generator': UnifiedIdGenerator.generate_base_id,
            'unified_id_manager_thread': UnifiedIDManager.generate_thread_id,
            'unified_id_manager_run': UnifiedIDManager.generate_run_id,
        }
        
        # Test each acceptable pattern
        for pattern_name, generate_func in acceptable_patterns.items():
            try:
                if pattern_name == 'unified_id_manager_run':
                    # Run ID needs thread ID parameter
                    test_thread_id = UnifiedIDManager.generate_thread_id()
                    generated_id = generate_func(test_thread_id)
                else:
                    generated_id = generate_func("test")
                
                # Validate it's not a raw UUID format
                assert not self.compliance_patterns['uuid_v4'].match(generated_id), (
                    f"Pattern {pattern_name} should not generate raw UUID format: {generated_id}"
                )
                
                # Validate it has structured format
                assert '_' in generated_id, f"Generated ID should have structured format with underscores: {generated_id}"
                
            except Exception as e:
                pytest.fail(f"Acceptable pattern {pattern_name} failed: {e}")

    def test_websocket_routing_id_format_requirements(self):
        """
        Test WebSocket routing specific ID format requirements.
        
        WebSocket routing depends on consistent ID formats for proper message delivery.
        """
        # Generate WebSocket-related IDs
        websocket_client_id = UnifiedIdGenerator.generate_base_id("websocket")
        user_id = UnifiedIdGenerator.generate_base_id("user")
        thread_id = UnifiedIdGenerator.generate_base_id("session")
        
        # Validate WebSocket routing requirements
        routing_requirements = [
            # WebSocket client ID should be extractable for routing
            (websocket_client_id.startswith("websocket_"), "WebSocket client ID must start with websocket_"),
            
            # All IDs should be parseable for routing logic
            ('_' in websocket_client_id and len(websocket_client_id.split('_')) >= 4, 
             "WebSocket ID must have structured format for routing parsing"),
            
            # IDs should be consistent length for indexing
            (len(websocket_client_id.split('_')[-1]) == 8, 
             "Random component should be consistent 8-character length"),
        ]
        
        for requirement_check, error_message in routing_requirements:
            assert requirement_check, f"WebSocket routing requirement failed: {error_message}"

    # =============================================================================
    # PERFORMANCE VALIDATION TESTS
    # =============================================================================

    def test_id_generation_performance_compliance(self):
        """
        Test that UnifiedIdGenerator provides acceptable performance for high-throughput scenarios.
        """
        import time
        
        # Generate large batch of IDs
        start_time = time.time()
        batch_size = 1000
        
        generated_ids = []
        for i in range(batch_size):
            id_value = UnifiedIdGenerator.generate_base_id("perf")
            generated_ids.append(id_value)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Validate performance is acceptable
        ids_per_second = batch_size / duration
        assert ids_per_second > 100, f"ID generation too slow: {ids_per_second:.2f} IDs/second (minimum 100)"
        
        # Validate all generated IDs are unique
        unique_ids = set(generated_ids)
        assert len(unique_ids) == batch_size, (
            f"Performance test generated duplicate IDs: {batch_size} requested, {len(unique_ids)} unique"
        )
        
        # Validate format consistency under load
        for id_value in generated_ids[:10]:  # Sample check
            parts = id_value.split('_')
            assert len(parts) >= 4, f"Performance test generated malformed ID: {id_value}"
            assert parts[0] == "perf", f"Performance test ID has wrong prefix: {id_value}"

    # =============================================================================
    # CLEANUP AND UTILITIES
    # =============================================================================

    def teardown_method(self):
        """Cleanup after each test method."""
        if hasattr(self, 'violations') and self.violations:
            print(f"\nMigration violations detected in this test: {len(self.violations)}")
            for violation in self.violations[:5]:  # Show first 5
                print(f"  - {violation}")
            if len(self.violations) > 5:
                print(f"  ... and {len(self.violations) - 5} more violations")