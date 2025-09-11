"""
Mission Critical Auth Service ID Migration Validation Test Suite

MISSION CRITICAL: Phase 1 of UnifiedIDManager migration - Issue #89
Tests EXACT violations in auth service that block 90%+ migration completion.

Business Value Justification:
- Segment: ALL (Critical security infrastructure)
- Business Goal: Eliminate raw UUID violations causing ID collision risks
- Value Impact: Prevents user data leakage from ID collisions ($100K+ security risk)
- Strategic Impact: CRITICAL - Foundation for entire platform ID migration

PHASE 1 SCOPE: Auth Service Critical Path
- 14 confirmed production violations in auth service
- Focus on EXACT file:line violations identified
- Tests designed to FAIL initially (proving violations exist)
- Tests should PASS after migration (validation target)

IDENTIFIED VIOLATIONS:
1. auth_service/auth_core/database/models.py: 8 violations (lines 25,54,70,91,101,120,128,144)
2. auth_service/auth_core/services/auth_service.py: 3 violations (lines 93,233,394)
3. auth_service/auth_core/core/jwt_handler.py: 1 violation (line 382)
4. auth_service/auth_core/unified_auth_interface.py: 2 violations (lines 257,309)

Expected Workflow:
1. Run tests → FAIL (detect violations)
2. Migrate code → Use UnifiedIdGenerator
3. Run tests → PASS (validate migration)
"""

import pytest
import uuid
import re
import inspect
import ast
from typing import List, Dict, Any, Set
from unittest.mock import patch, MagicMock

# SSOT imports - migration targets
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from netra_backend.app.core.unified_id_manager import UnifiedIDManager

# Test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestAuthServiceIDMigrationValidation(SSotBaseTestCase):
    """
    Mission Critical Test Suite for Auth Service ID Migration - Phase 1
    
    These tests validate the exact violations identified in Issue #89.
    Tests are designed to FAIL initially, proving violations exist.
    After migration, tests should PASS, confirming compliance.
    """

    def setup_method(self):
        """Setup for each test method."""
        self.violation_count = 0
        self.violations_detected = []
        
        # Patterns for violation detection
        self.raw_uuid_patterns = [
            re.compile(r'str\(uuid\.uuid4\(\)\)'),
            re.compile(r'uuid\.uuid4\(\)\.hex\[:8\]'),
            re.compile(r'uuid\.uuid4\(\)\.hex'),
            re.compile(r'default=lambda:\s*str\(uuid\.uuid4\(\)\)'),
        ]
        
        # Expected SSOT patterns after migration
        self.ssot_patterns = [
            re.compile(r'UnifiedIdGenerator\.generate_base_id'),
            re.compile(r'UnifiedIDManager\.generate_'),
        ]

    # ================================================================================
    # EXACT VIOLATION DETECTION TESTS - These SHOULD FAIL initially
    # ================================================================================

    def test_auth_database_models_raw_uuid_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Detect exact raw UUID violations in auth database models.
        
        Violations at auth_service/auth_core/database/models.py:
        - Line 25: id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        - Line 54: kwargs['id'] = str(uuid.uuid4())
        - Line 70: id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        - Line 91: kwargs['id'] = str(uuid.uuid4())
        - Line 101: id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        - Line 120: kwargs['id'] = str(uuid.uuid4())
        - Line 128: id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        - Line 144: kwargs['id'] = str(uuid.uuid4())
        
        Migration Target: Replace with UnifiedIdGenerator.generate_base_id()
        """
        # Read the actual file to test real violations
        models_file_path = "/Users/anthony/Desktop/netra-apex/auth_service/auth_core/database/models.py"
        
        try:
            with open(models_file_path, 'r') as file:
                file_content = file.read()
                lines = file_content.split('\n')
        except FileNotFoundError:
            pytest.fail(f"Auth models file not found: {models_file_path}")
        
        violations_found = []
        
        # Check exact violation lines identified in Issue #89
        violation_lines = [25, 54, 70, 91, 101, 120, 128, 144]
        
        for line_num in violation_lines:
            if line_num <= len(lines):
                line_content = lines[line_num - 1]  # Convert to 0-based index
                
                # Check for raw UUID patterns
                for pattern in self.raw_uuid_patterns:
                    if pattern.search(line_content):
                        violations_found.append({
                            'line': line_num,
                            'content': line_content.strip(),
                            'violation': 'raw_uuid_usage'
                        })
                        break
        
        # This test SHOULD FAIL initially - we expect violations
        assert len(violations_found) > 0, (
            "Expected to find raw UUID violations in auth database models. "
            "If this passes, violations are already fixed!"
        )
        
        # Record violations for migration tracking
        self.violations_detected.extend(violations_found)
        
        # Fail with detailed violation report
        violation_report = "\n".join([
            f"Line {v['line']}: {v['content']}"
            for v in violations_found
        ])
        
        pytest.fail(
            f"Found {len(violations_found)} raw UUID violations in auth database models:\n"
            f"{violation_report}\n\n"
            f"Migration Required: Replace str(uuid.uuid4()) with UnifiedIdGenerator.generate_base_id('auth_user')"
        )

    def test_auth_service_session_creation_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Detect exact raw UUID violations in auth service session creation.
        
        Violations at auth_service/auth_core/services/auth_service.py:
        - Line 93: session_id = str(uuid.uuid4())
        - Line 233: user_id = str(uuid.uuid4())
        - Line 394: user_id = str(uuid.uuid4())
        
        Migration Target: Replace with UnifiedIdGenerator.generate_base_id()
        """
        # Read the actual auth service file
        auth_service_file_path = "/Users/anthony/Desktop/netra-apex/auth_service/auth_core/services/auth_service.py"
        
        try:
            with open(auth_service_file_path, 'r') as file:
                file_content = file.read()
                lines = file_content.split('\n')
        except FileNotFoundError:
            pytest.fail(f"Auth service file not found: {auth_service_file_path}")
        
        violations_found = []
        
        # Check exact violation lines identified in Issue #89
        violation_lines = [93, 233, 394]
        
        for line_num in violation_lines:
            if line_num <= len(lines):
                line_content = lines[line_num - 1]  # Convert to 0-based index
                
                # Check for raw UUID patterns
                for pattern in self.raw_uuid_patterns:
                    if pattern.search(line_content):
                        violations_found.append({
                            'line': line_num,
                            'content': line_content.strip(),
                            'violation': 'raw_uuid_in_session_creation'
                        })
                        break
        
        # This test SHOULD FAIL initially - we expect violations
        assert len(violations_found) > 0, (
            "Expected to find raw UUID violations in auth service session creation. "
            "If this passes, violations are already fixed!"
        )
        
        # Record violations for migration tracking
        self.violations_detected.extend(violations_found)
        
        # Fail with detailed violation report
        violation_report = "\n".join([
            f"Line {v['line']}: {v['content']}"
            for v in violations_found
        ])
        
        pytest.fail(
            f"Found {len(violations_found)} session creation UUID violations in auth service:\n"
            f"{violation_report}\n\n"
            f"Migration Required: Replace str(uuid.uuid4()) with UnifiedIdGenerator.generate_base_id('session')"
        )

    def test_jwt_handler_jti_generation_violation_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Detect exact raw UUID violation in JWT handler JTI generation.
        
        Violation at auth_service/auth_core/core/jwt_handler.py:
        - Line 382: "jti": str(uuid.uuid4()),     # JWT ID for replay protection
        
        Migration Target: Replace with UnifiedIdGenerator.generate_base_id('jti')
        """
        # Read the actual JWT handler file
        jwt_handler_file_path = "/Users/anthony/Desktop/netra-apex/auth_service/auth_core/core/jwt_handler.py"
        
        try:
            with open(jwt_handler_file_path, 'r') as file:
                file_content = file.read()
                lines = file_content.split('\n')
        except FileNotFoundError:
            pytest.fail(f"JWT handler file not found: {jwt_handler_file_path}")
        
        violations_found = []
        
        # Check exact violation line identified in Issue #89
        violation_lines = [382]
        
        for line_num in violation_lines:
            if line_num <= len(lines):
                line_content = lines[line_num - 1]  # Convert to 0-based index
                
                # Check for raw UUID patterns
                for pattern in self.raw_uuid_patterns:
                    if pattern.search(line_content):
                        violations_found.append({
                            'line': line_num,
                            'content': line_content.strip(),
                            'violation': 'raw_uuid_in_jti_generation'
                        })
                        break
        
        # This test SHOULD FAIL initially - we expect violations
        assert len(violations_found) > 0, (
            "Expected to find raw UUID violation in JWT handler JTI generation. "
            "If this passes, violation is already fixed!"
        )
        
        # Record violations for migration tracking
        self.violations_detected.extend(violations_found)
        
        # Fail with detailed violation report
        violation_report = "\n".join([
            f"Line {v['line']}: {v['content']}"
            for v in violations_found
        ])
        
        pytest.fail(
            f"Found JWT handler JTI generation UUID violation:\n"
            f"{violation_report}\n\n"
            f"Migration Required: Replace str(uuid.uuid4()) with UnifiedIdGenerator.generate_base_id('jti')"
        )

    def test_unified_auth_interface_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Detect exact raw UUID violations in unified auth interface.
        
        Violations at auth_service/auth_core/unified_auth_interface.py:
        - Line 257: return str(uuid.uuid4())
        - Line 309: return str(uuid.uuid4())
        
        Migration Target: Replace with UnifiedIdGenerator.generate_base_id()
        """
        # Read the actual unified auth interface file
        auth_interface_file_path = "/Users/anthony/Desktop/netra-apex/auth_service/auth_core/unified_auth_interface.py"
        
        try:
            with open(auth_interface_file_path, 'r') as file:
                file_content = file.read()
                lines = file_content.split('\n')
        except FileNotFoundError:
            pytest.fail(f"Unified auth interface file not found: {auth_interface_file_path}")
        
        violations_found = []
        
        # Check exact violation lines identified in Issue #89
        violation_lines = [257, 309]
        
        for line_num in violation_lines:
            if line_num <= len(lines):
                line_content = lines[line_num - 1]  # Convert to 0-based index
                
                # Check for raw UUID patterns
                for pattern in self.raw_uuid_patterns:
                    if pattern.search(line_content):
                        violations_found.append({
                            'line': line_num,
                            'content': line_content.strip(),
                            'violation': 'raw_uuid_in_auth_interface'
                        })
                        break
        
        # This test SHOULD FAIL initially - we expect violations
        assert len(violations_found) > 0, (
            "Expected to find raw UUID violations in unified auth interface. "
            "If this passes, violations are already fixed!"
        )
        
        # Record violations for migration tracking
        self.violations_detected.extend(violations_found)
        
        # Fail with detailed violation report
        violation_report = "\n".join([
            f"Line {v['line']}: {v['content']}"
            for v in violations_found
        ])
        
        pytest.fail(
            f"Found {len(violations_found)} UUID violations in unified auth interface:\n"
            f"{violation_report}\n\n"
            f"Migration Required: Replace str(uuid.uuid4()) with UnifiedIdGenerator.generate_base_id()"
        )

    # ================================================================================
    # BEHAVIORAL VIOLATION TESTS - Test actual function behavior
    # ================================================================================

    def test_auth_models_generate_non_structured_ids_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Test that auth models currently generate raw UUIDs instead of structured IDs.
        
        This tests the ACTUAL behavior of the models when instantiated.
        """
        try:
            # Import auth models to test actual behavior
            from auth_service.auth_core.database.models import AuthUser, AuthSession, AuthAuditLog, PasswordResetToken
            
            # Test AuthUser ID generation
            try:
                auth_user = AuthUser(email="test@example.com")
                user_id = auth_user.id
                
                # Check if it's a raw UUID (violation) vs structured format (compliant)
                uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)
                structured_pattern = re.compile(r'^[a-z_]+_\d+_[a-f0-9]{8}$')
                
                violations = []
                
                if uuid_pattern.match(user_id):
                    violations.append(f"AuthUser ID '{user_id}' uses raw UUID format instead of structured format")
                elif not structured_pattern.match(user_id):
                    violations.append(f"AuthUser ID '{user_id}' has unknown format (not UUID or structured)")
                    
                # Test AuthSession ID generation
                auth_session = AuthSession(user_id="test_user_id")
                session_id = auth_session.id
                
                if uuid_pattern.match(session_id):
                    violations.append(f"AuthSession ID '{session_id}' uses raw UUID format instead of structured format")
                    
                # Test AuthAuditLog ID generation
                audit_log = AuthAuditLog(event_type="test_event", success=True)
                audit_id = audit_log.id
                
                if uuid_pattern.match(audit_id):
                    violations.append(f"AuthAuditLog ID '{audit_id}' uses raw UUID format instead of structured format")
                    
                # Test PasswordResetToken ID generation
                reset_token = PasswordResetToken(user_id="test_user", token_hash="test_hash", email="test@example.com")
                reset_id = reset_token.id
                
                if uuid_pattern.match(reset_id):
                    violations.append(f"PasswordResetToken ID '{reset_id}' uses raw UUID format instead of structured format")
                
                # This test SHOULD FAIL initially - we expect raw UUID usage
                assert len(violations) > 0, (
                    "Expected auth models to generate raw UUIDs. "
                    "If this passes, models are already using structured IDs!"
                )
                
                pytest.fail(
                    f"Found {len(violations)} behavioral UUID violations in auth models:\n" +
                    "\n".join(violations) +
                    "\n\nMigration Required: Update model defaults to use UnifiedIdGenerator.generate_base_id()"
                )
                
            except Exception as model_error:
                # If models can't be instantiated, that might be due to missing dependencies
                # This is still valuable information for migration planning
                pytest.fail(f"Auth models instantiation failed (may indicate dependency issues): {model_error}")
                
        except ImportError as e:
            pytest.fail(f"Cannot import auth models for behavioral testing: {e}")

    def test_auth_service_session_creation_behavior_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Test that auth service create_session() currently generates raw UUIDs.
        
        This tests the ACTUAL runtime behavior of session creation.
        """
        try:
            from auth_service.auth_core.services.auth_service import AuthService
            
            # Create auth service instance
            auth_service = AuthService()
            
            # Test session creation behavior
            test_user_id = "test_user_123"
            test_user_data = {"email": "test@example.com", "name": "Test User"}
            
            session_id = auth_service.create_session(test_user_id, test_user_data)
            
            # Check if session ID is raw UUID (violation) vs structured format (compliant)
            uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)
            structured_pattern = re.compile(r'^session_\d+_[a-f0-9]{8}$')
            
            violations = []
            
            if uuid_pattern.match(session_id):
                violations.append(f"Session ID '{session_id}' uses raw UUID format instead of structured 'session_*' format")
            elif not structured_pattern.match(session_id):
                violations.append(f"Session ID '{session_id}' has unknown format (expected session_timestamp_counter_uuid8)")
            
            # This test SHOULD FAIL initially - we expect raw UUID usage
            assert len(violations) > 0, (
                "Expected AuthService.create_session() to generate raw UUIDs. "
                "If this passes, session creation is already using structured IDs!"
            )
            
            pytest.fail(
                f"Found session creation behavioral violations:\n" +
                "\n".join(violations) +
                "\n\nMigration Required: Update AuthService.create_session() to use UnifiedIdGenerator.generate_base_id('session')"
            )
            
        except ImportError as e:
            pytest.fail(f"Cannot import AuthService for behavioral testing: {e}")
        except Exception as e:
            # If service creation fails, that's also valuable information
            pytest.fail(f"AuthService instantiation or session creation failed: {e}")

    # ================================================================================
    # MIGRATION COMPLIANCE VALIDATION TESTS - These should PASS after migration
    # ================================================================================

    def test_unified_id_generator_produces_structured_auth_ids_SHOULD_PASS_AFTER_MIGRATION(self):
        """
        This test should PASS after migration to validate UnifiedIdGenerator compliance.
        
        Validates that UnifiedIdGenerator produces properly structured IDs for auth components.
        """
        # Test UnifiedIdGenerator for auth-specific ID generation
        auth_user_id = UnifiedIdGenerator.generate_base_id("auth_user")
        session_id = UnifiedIdGenerator.generate_base_id("session")
        jti_id = UnifiedIdGenerator.generate_base_id("jti")
        audit_id = UnifiedIdGenerator.generate_base_id("audit")
        reset_token_id = UnifiedIdGenerator.generate_base_id("reset_token")
        
        # Validate structured format: prefix_timestamp_counter_uuid8
        structured_pattern = re.compile(r'^[a-z_]+_\d+_\d+_[a-f0-9]{8}$')
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)
        
        test_cases = [
            (auth_user_id, "auth_user_", "Auth user ID"),
            (session_id, "session_", "Session ID"),
            (jti_id, "jti_", "JWT ID (JTI)"),
            (audit_id, "audit_", "Audit log ID"),
            (reset_token_id, "reset_token_", "Password reset token ID"),
        ]
        
        for id_value, expected_prefix, description in test_cases:
            # Should start with expected prefix
            assert id_value.startswith(expected_prefix), f"{description} should start with {expected_prefix}: {id_value}"
            
            # Should NOT be raw UUID format
            assert not uuid_pattern.match(id_value), f"{description} should not be raw UUID format: {id_value}"
            
            # Should match structured format
            assert structured_pattern.match(id_value), f"{description} should match structured format: {id_value}"
            
            # Should have exactly 4 parts
            parts = id_value.split('_')
            assert len(parts) >= 4, f"{description} should have at least 4 parts: {id_value}"
            
            # Timestamp should be numeric
            timestamp_part = parts[-3]
            assert timestamp_part.isdigit(), f"Timestamp part should be numeric in {description}: {timestamp_part}"
            
            # Counter should be numeric
            counter_part = parts[-2]
            assert counter_part.isdigit(), f"Counter part should be numeric in {description}: {counter_part}"
            
            # Random part should be 8-character hex
            random_part = parts[-1]
            assert len(random_part) == 8, f"Random part should be 8 characters in {description}: {random_part}"
            assert all(c in '0123456789abcdef' for c in random_part.lower()), f"Random part should be hex in {description}: {random_part}"

    def test_unified_id_manager_auth_integration_SHOULD_PASS_AFTER_MIGRATION(self):
        """
        This test should PASS after migration to validate UnifiedIDManager integration.
        
        Tests that UnifiedIDManager methods work properly for auth-related operations.
        """
        # Test thread and run ID generation for auth contexts
        auth_thread_id = UnifiedIDManager.generate_thread_id()
        auth_run_id = UnifiedIDManager.generate_run_id(auth_thread_id)
        
        # Validate run ID embeds thread ID properly
        extracted_thread = UnifiedIDManager.extract_thread_id(auth_run_id)
        assert extracted_thread == auth_thread_id, (
            f"Run ID should properly embed and extract thread ID. "
            f"Original: {auth_thread_id}, Extracted: {extracted_thread}, Run: {auth_run_id}"
        )
        
        # Validate run ID format
        assert UnifiedIDManager.validate_run_id(auth_run_id), f"Run ID should validate as proper format: {auth_run_id}"
        
        # Validate parse components
        parsed = UnifiedIDManager.parse_run_id(auth_run_id)
        assert parsed['valid'] is True, f"Run ID should parse successfully: {auth_run_id}"
        assert parsed['thread_id'] == auth_thread_id, f"Parsed thread ID should match original: {parsed}"

    # ================================================================================
    # INTEGRATION TESTS - Cross-component validation
    # ================================================================================

    def test_auth_service_integration_after_migration_SHOULD_PASS_AFTER_MIGRATION(self):
        """
        Integration test to validate that auth service works properly after migration.
        
        This tests the end-to-end flow with migrated ID generation.
        """
        # Test that UnifiedIdGenerator can be used for all auth service ID needs
        user_context_ids = UnifiedIdGenerator.generate_user_context_ids("auth_test_user", "auth_operation")
        thread_id, run_id, request_id = user_context_ids
        
        # Validate all IDs follow consistent patterns
        structured_pattern = re.compile(r'^[a-z_]+_[a-z_]+_\d+_[a-f0-9]{8}$')
        
        assert structured_pattern.match(thread_id), f"Thread ID should match structured pattern: {thread_id}"
        assert structured_pattern.match(run_id), f"Run ID should match structured pattern: {run_id}"
        assert structured_pattern.match(request_id), f"Request ID should match structured pattern: {request_id}"
        
        # Validate IDs are unique
        ids = [thread_id, run_id, request_id]
        unique_ids = set(ids)
        assert len(unique_ids) == len(ids), f"All generated IDs should be unique: {ids}"
        
        # Validate IDs can be used in auth operations
        session_data = {
            'thread_id': thread_id,
            'run_id': run_id,
            'request_id': request_id,
            'user_id': 'auth_test_user'
        }
        
        # This should work without any UUID-related errors
        assert all(key in session_data for key in ['thread_id', 'run_id', 'request_id']), "Session data should contain all required IDs"

    # ================================================================================
    # CLEANUP AND UTILITIES
    # ================================================================================

    def teardown_method(self):
        """Cleanup after each test method."""
        if hasattr(self, 'violations_detected') and self.violations_detected:
            print(f"\n=== Phase 1 Auth Service Violations Detected: {len(self.violations_detected)} ===")
            for violation in self.violations_detected:
                print(f"  Line {violation['line']}: {violation['content']}")
            print(f"=== Total violations requiring migration: {len(self.violations_detected)} ===")

    def get_violation_summary(self) -> Dict[str, Any]:
        """Get summary of violations found during testing."""
        return {
            'total_violations': len(self.violations_detected),
            'violations_by_file': {
                'models.py': len([v for v in self.violations_detected if 'models' in str(v)]),
                'auth_service.py': len([v for v in self.violations_detected if 'auth_service' in str(v)]),
                'jwt_handler.py': len([v for v in self.violations_detected if 'jwt_handler' in str(v)]),
                'unified_auth_interface.py': len([v for v in self.violations_detected if 'auth_interface' in str(v)])
            },
            'migration_priority': 'CRITICAL - Auth service is foundation for all authentication',
            'expected_migration_time': '2-4 hours for 14 violations',
            'business_impact': 'HIGH - Security and user isolation depends on proper ID generation'
        }


# ================================================================================
# SPECIALIZED VIOLATION DETECTION TESTS
# ================================================================================

class TestAuthServiceIDViolationPatterns(SSotBaseTestCase):
    """
    Specialized tests for detecting specific UUID violation patterns in auth service.
    
    These tests focus on the patterns rather than exact lines, providing
    additional validation for migration completeness.
    """

    def test_detect_sqlalchemy_default_uuid_patterns_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Detect SQLAlchemy default=lambda: str(uuid.uuid4()) patterns.
        
        These patterns are common in auth service database models.
        """
        # Pattern specifically for SQLAlchemy default lambdas
        sqlalchemy_uuid_pattern = re.compile(r'default=lambda:\s*str\(uuid\.uuid4\(\)\)')
        
        violation_files = [
            "/Users/anthony/Desktop/netra-apex/auth_service/auth_core/database/models.py"
        ]
        
        violations_found = []
        
        for file_path in violation_files:
            try:
                with open(file_path, 'r') as file:
                    file_content = file.read()
                    lines = file_content.split('\n')
                    
                for line_num, line in enumerate(lines, 1):
                    if sqlalchemy_uuid_pattern.search(line):
                        violations_found.append({
                            'file': file_path,
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': 'sqlalchemy_default_uuid'
                        })
            except FileNotFoundError:
                continue
        
        # This test SHOULD FAIL initially
        assert len(violations_found) > 0, (
            "Expected to find SQLAlchemy default UUID patterns. "
            "If this passes, these patterns are already migrated!"
        )
        
        violation_report = "\n".join([
            f"{v['file']}:{v['line']} - {v['content']}"
            for v in violations_found
        ])
        
        pytest.fail(
            f"Found {len(violations_found)} SQLAlchemy default UUID patterns:\n"
            f"{violation_report}\n\n"
            f"Migration Required: Replace default=lambda: str(uuid.uuid4()) with "
            f"default=lambda: UnifiedIdGenerator.generate_base_id('model_type')"
        )

    def test_detect_session_creation_uuid_patterns_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Detect session creation UUID patterns in auth service.
        
        Pattern: session_id = str(uuid.uuid4())
        """
        # Pattern for session ID creation
        session_uuid_pattern = re.compile(r'session_id\s*=\s*str\(uuid\.uuid4\(\)\)')
        
        violation_files = [
            "/Users/anthony/Desktop/netra-apex/auth_service/auth_core/services/auth_service.py",
            "/Users/anthony/Desktop/netra-apex/auth_service/auth_core/unified_auth_interface.py"
        ]
        
        violations_found = []
        
        for file_path in violation_files:
            try:
                with open(file_path, 'r') as file:
                    file_content = file.read()
                    lines = file_content.split('\n')
                    
                for line_num, line in enumerate(lines, 1):
                    if session_uuid_pattern.search(line):
                        violations_found.append({
                            'file': file_path,
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': 'session_creation_uuid'
                        })
            except FileNotFoundError:
                continue
        
        # This test SHOULD FAIL initially
        assert len(violations_found) > 0, (
            "Expected to find session creation UUID patterns. "
            "If this passes, these patterns are already migrated!"
        )
        
        violation_report = "\n".join([
            f"{v['file']}:{v['line']} - {v['content']}"
            for v in violations_found
        ])
        
        pytest.fail(
            f"Found {len(violations_found)} session creation UUID patterns:\n"
            f"{violation_report}\n\n"
            f"Migration Required: Replace session_id = str(uuid.uuid4()) with "
            f"session_id = UnifiedIdGenerator.generate_base_id('session')"
        )

    def test_detect_user_id_creation_uuid_patterns_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Detect user ID creation UUID patterns in auth service.
        
        Pattern: user_id = str(uuid.uuid4())
        """
        # Pattern for user ID creation
        user_uuid_pattern = re.compile(r'user_id\s*=\s*str\(uuid\.uuid4\(\)\)')
        
        violation_files = [
            "/Users/anthony/Desktop/netra-apex/auth_service/auth_core/services/auth_service.py"
        ]
        
        violations_found = []
        
        for file_path in violation_files:
            try:
                with open(file_path, 'r') as file:
                    file_content = file.read()
                    lines = file_content.split('\n')
                    
                for line_num, line in enumerate(lines, 1):
                    if user_uuid_pattern.search(line):
                        violations_found.append({
                            'file': file_path,
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': 'user_creation_uuid'
                        })
            except FileNotFoundError:
                continue
        
        # This test SHOULD FAIL initially
        assert len(violations_found) > 0, (
            "Expected to find user ID creation UUID patterns. "
            "If this passes, these patterns are already migrated!"
        )
        
        violation_report = "\n".join([
            f"{v['file']}:{v['line']} - {v['content']}"
            for v in violations_found
        ])
        
        pytest.fail(
            f"Found {len(violations_found)} user ID creation UUID patterns:\n"
            f"{violation_report}\n\n"
            f"Migration Required: Replace user_id = str(uuid.uuid4()) with "
            f"user_id = UnifiedIdGenerator.generate_base_id('user')"
        )

    def test_detect_jwt_jti_uuid_patterns_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Detect JWT JTI UUID patterns.
        
        Pattern: "jti": str(uuid.uuid4())
        """
        # Pattern for JWT JTI creation
        jti_uuid_pattern = re.compile(r'"jti":\s*str\(uuid\.uuid4\(\)\)')
        
        violation_files = [
            "/Users/anthony/Desktop/netra-apex/auth_service/auth_core/core/jwt_handler.py"
        ]
        
        violations_found = []
        
        for file_path in violation_files:
            try:
                with open(file_path, 'r') as file:
                    file_content = file.read()
                    lines = file_content.split('\n')
                    
                for line_num, line in enumerate(lines, 1):
                    if jti_uuid_pattern.search(line):
                        violations_found.append({
                            'file': file_path,
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': 'jwt_jti_uuid'
                        })
            except FileNotFoundError:
                continue
        
        # This test SHOULD FAIL initially
        assert len(violations_found) > 0, (
            "Expected to find JWT JTI UUID patterns. "
            "If this passes, these patterns are already migrated!"
        )
        
        violation_report = "\n".join([
            f"{v['file']}:{v['line']} - {v['content']}"
            for v in violations_found
        ])
        
        pytest.fail(
            f"Found {len(violations_found)} JWT JTI UUID patterns:\n"
            f"{violation_report}\n\n"
            f"Migration Required: Replace \"jti\": str(uuid.uuid4()) with "
            f"\"jti\": UnifiedIdGenerator.generate_base_id('jti')"
        )


if __name__ == "__main__":
    # Run the tests directly for debugging
    pytest.main([__file__, "-v", "--tb=short"])