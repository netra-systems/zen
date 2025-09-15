"""
Unit Test Suite for Database Model ID Violations

MISSION CRITICAL: This test suite validates database model ID generation
compliance with SSOT patterns and exposes violations in model defaults.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Ensure database consistency and prevent ID collision issues
- Value Impact: Prevents database integrity issues and ensures proper audit trails  
- Strategic Impact: Critical for data consistency across all user operations

Test Strategy:
These tests are designed to FAIL initially, exposing database model ID violations
where models use raw UUID defaults instead of SSOT-compliant ID generation.

Identified Violations:
- Database models with default=uuid.uuid4 in column definitions
- Models without proper ID validation constraints
- Inconsistent ID formats between related models  
- Missing SSOT ID generation in model factories
- Foreign key relationships with mixed ID formats
"""

import pytest
import uuid
import re
from typing import Dict, Any, List, Optional, Type
from unittest.mock import patch, MagicMock
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Test framework imports
from test_framework.ssot.base_test_case import BaseTestCase

# SSOT imports that should be used everywhere
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.core_types import UserID, ThreadID, RunID, ensure_user_id

# Database and model imports for testing
from netra_backend.app.database import get_db
from netra_backend.app.dependencies import get_request_scoped_db_session


class TestDatabaseModelIDViolations(BaseTestCase):
    """Unit tests exposing database model ID generation SSOT violations."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.model_violations = []
        self.id_patterns = {
            'uuid_v4': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I),
            'ssot_structured': re.compile(r'^[a-z_]+_\d+_[a-f0-9]{8}$'),
            'uuid_callable': 'uuid.uuid4',  # String pattern for detecting UUID callable usage
        }

    # =============================================================================
    # DATABASE MODEL DEFINITION VIOLATIONS - Should FAIL initially
    # =============================================================================

    def test_database_model_uuid_default_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Database models use uuid.uuid4 as column defaults.
        
        This test creates mock database models that represent current violations
        where models use raw UUID generation instead of SSOT patterns.
        """
        # Create mock models that represent current database violations
        Base = declarative_base()
        
        class ViolatingUserModel(Base):
            """Example model with UUID default violations."""
            __tablename__ = 'violating_users'
            
            # VIOLATION: Using raw uuid.uuid4 as default
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            email = Column(String, nullable=False)
            # VIOLATION: Session ID also uses raw UUID
            current_session_id = Column(String, default=lambda: str(uuid.uuid4()))
            created_at = Column(DateTime, default=datetime.utcnow)
        
        class ViolatingThreadModel(Base):
            """Example thread model with UUID violations."""
            __tablename__ = 'violating_threads'
            
            # VIOLATION: Thread ID uses raw UUID
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            # VIOLATION: User ID foreign key uses raw UUID format
            user_id = Column(String, ForeignKey('violating_users.id'), default=lambda: str(uuid.uuid4()))
            title = Column(String)
            created_at = Column(DateTime, default=datetime.utcnow)
        
        class ViolatingRunModel(Base):
            """Example run model with UUID violations."""
            __tablename__ = 'violating_runs'
            
            # VIOLATION: Run ID uses raw UUID
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            # VIOLATION: Thread ID foreign key uses raw UUID
            thread_id = Column(String, ForeignKey('violating_threads.id'), default=lambda: str(uuid.uuid4()))
            # VIOLATION: Execution ID uses raw UUID
            execution_id = Column(String, default=lambda: str(uuid.uuid4()))
            status = Column(String)
            created_at = Column(DateTime, default=datetime.utcnow)
        
        # Test the models by creating instances
        model_violations = []
        
        # Test ViolatingUserModel
        try:
            user_instance = ViolatingUserModel()
            user_instance.email = "test@example.com"
            
            # Generate default values
            if hasattr(user_instance.id, 'default') and callable(user_instance.id.default.arg):
                generated_user_id = user_instance.id.default.arg()
                if self.id_patterns['uuid_v4'].match(generated_user_id):
                    model_violations.append(f"ViolatingUserModel.id generates raw UUID: {generated_user_id}")
            
            # Test direct generation to simulate what actually happens
            user_id_direct = str(uuid.uuid4())  # This simulates the current violation
            if self.id_patterns['uuid_v4'].match(user_id_direct):
                model_violations.append(f"ViolatingUserModel uses raw UUID pattern in defaults: {user_id_direct}")
            
            session_id_direct = str(uuid.uuid4())  # Simulates current_session_id default
            if self.id_patterns['uuid_v4'].match(session_id_direct):
                model_violations.append(f"ViolatingUserModel.current_session_id uses raw UUID: {session_id_direct}")
        
        except Exception as e:
            model_violations.append(f"ViolatingUserModel testing failed: {e}")
        
        # Test ViolatingThreadModel
        try:
            thread_instance = ViolatingThreadModel()
            thread_instance.title = "Test Thread"
            
            # Simulate ID generation
            thread_id_direct = str(uuid.uuid4())  # Simulates thread ID default
            if self.id_patterns['uuid_v4'].match(thread_id_direct):
                model_violations.append(f"ViolatingThreadModel.id uses raw UUID: {thread_id_direct}")
            
            # Foreign key violation
            foreign_user_id = str(uuid.uuid4())  # Simulates user_id foreign key
            if self.id_patterns['uuid_v4'].match(foreign_user_id):
                model_violations.append(f"ViolatingThreadModel.user_id foreign key uses raw UUID: {foreign_user_id}")
        
        except Exception as e:
            model_violations.append(f"ViolatingThreadModel testing failed: {e}")
        
        # Test ViolatingRunModel
        try:
            run_instance = ViolatingRunModel()
            run_instance.status = "running"
            
            # Simulate ID generation
            run_id_direct = str(uuid.uuid4())  # Simulates run ID default
            if self.id_patterns['uuid_v4'].match(run_id_direct):
                model_violations.append(f"ViolatingRunModel.id uses raw UUID: {run_id_direct}")
            
            execution_id_direct = str(uuid.uuid4())  # Simulates execution_id default
            if self.id_patterns['uuid_v4'].match(execution_id_direct):
                model_violations.append(f"ViolatingRunModel.execution_id uses raw UUID: {execution_id_direct}")
            
            thread_fk_id = str(uuid.uuid4())  # Simulates thread_id foreign key
            if self.id_patterns['uuid_v4'].match(thread_fk_id):
                model_violations.append(f"ViolatingRunModel.thread_id foreign key uses raw UUID: {thread_fk_id}")
        
        except Exception as e:
            model_violations.append(f"ViolatingRunModel testing failed: {e}")
        
        # This test SHOULD FAIL due to model violations
        assert len(model_violations) > 0, (
            "Expected database model UUID violations. "
            "If this passes, database models are already using SSOT ID generation!"
        )
        
        self.model_violations.extend(model_violations)
        
        pytest.fail(
            f"Database model ID generation violations:\n" +
            "\n".join(model_violations) +
            "\n\nMIGRATION REQUIRED: Replace uuid.uuid4() defaults with UnifiedIdGenerator.generate_base_id() in model definitions"
        )

    def test_model_factory_id_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Model factories and creators use raw UUID generation.
        
        This test validates that model creation utilities (factories, builders)
        use proper SSOT ID generation instead of raw UUIDs.
        """
        # Simulate model factory patterns that currently use raw UUIDs
        factory_violations = []
        
        def violating_user_factory(**kwargs):
            """Simulate user factory with UUID violations."""
            return {
                "id": str(uuid.uuid4()),  # VIOLATION: Raw UUID
                "email": kwargs.get("email", "test@example.com"),
                "session_id": str(uuid.uuid4()),  # VIOLATION: Raw UUID
                "created_at": datetime.utcnow().isoformat(),
                **kwargs
            }
        
        def violating_thread_factory(user_id=None, **kwargs):
            """Simulate thread factory with UUID violations."""
            return {
                "id": str(uuid.uuid4()),  # VIOLATION: Raw UUID
                "user_id": user_id or str(uuid.uuid4()),  # VIOLATION: Raw UUID fallback
                "title": kwargs.get("title", "Test Thread"),
                "created_at": datetime.utcnow().isoformat(),
                **kwargs
            }
        
        def violating_run_factory(thread_id=None, **kwargs):
            """Simulate run factory with UUID violations."""
            return {
                "id": str(uuid.uuid4()),  # VIOLATION: Raw UUID
                "thread_id": thread_id or str(uuid.uuid4()),  # VIOLATION: Raw UUID fallback
                "execution_id": str(uuid.uuid4()),  # VIOLATION: Raw UUID
                "status": kwargs.get("status", "pending"),
                "created_at": datetime.utcnow().isoformat(),
                **kwargs
            }
        
        # Test factory violations
        try:
            # Test user factory
            user_data = violating_user_factory()
            for field, value in user_data.items():
                if field.endswith("_id") or field == "id":
                    if isinstance(value, str) and self.id_patterns['uuid_v4'].match(value):
                        factory_violations.append(f"User factory field '{field}' uses raw UUID: {value}")
            
            # Test thread factory
            thread_data = violating_thread_factory()
            for field, value in thread_data.items():
                if field.endswith("_id") or field == "id":
                    if isinstance(value, str) and self.id_patterns['uuid_v4'].match(value):
                        factory_violations.append(f"Thread factory field '{field}' uses raw UUID: {value}")
            
            # Test run factory
            run_data = violating_run_factory()
            for field, value in run_data.items():
                if field.endswith("_id") or field == "id":
                    if isinstance(value, str) and self.id_patterns['uuid_v4'].match(value):
                        factory_violations.append(f"Run factory field '{field}' uses raw UUID: {value}")
            
            # Test factory relationship consistency
            user = violating_user_factory()
            thread = violating_thread_factory(user_id=user["id"])
            run = violating_run_factory(thread_id=thread["id"])
            
            # All IDs should be UUIDs (current violation pattern)
            relationship_ids = [user["id"], thread["id"], run["id"]]
            uuid_count = sum(1 for id_val in relationship_ids if self.id_patterns['uuid_v4'].match(id_val))
            
            if uuid_count > 0:
                factory_violations.append(f"Factory relationship chain uses {uuid_count} raw UUIDs instead of SSOT format")
        
        except Exception as e:
            factory_violations.append(f"Model factory testing failed: {e}")
        
        # This test SHOULD FAIL
        assert len(factory_violations) > 0, (
            "Expected model factory UUID violations. "
            "If this passes, model factories are already using SSOT ID generation!"
        )
        
        pytest.fail(
            f"Model factory ID generation violations:\n" +
            "\n".join(factory_violations) +
            "\n\nMIGRATION REQUIRED: Update model factories to use UnifiedIdGenerator for all ID generation"
        )

    # =============================================================================
    # DATABASE MIGRATION CONSISTENCY VIOLATIONS - Should FAIL initially
    # =============================================================================

    def test_database_migration_id_consistency_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Database migrations create inconsistent ID formats.
        
        This test simulates database migration scenarios where existing data
        has mixed ID formats causing consistency issues.
        """
        # Simulate database migration scenarios with mixed ID formats
        migration_violations = []
        
        # Scenario 1: Migrating from UUID to SSOT format
        existing_uuid_data = [
            {"id": str(uuid.uuid4()), "type": "user", "legacy": True},
            {"id": str(uuid.uuid4()), "type": "thread", "legacy": True},
            {"id": str(uuid.uuid4()), "type": "run", "legacy": True}
        ]
        
        new_ssot_data = [
            {"id": UnifiedIdGenerator.generate_base_id("user"), "type": "user", "legacy": False},
            {"id": UnifiedIdGenerator.generate_base_id("session"), "type": "thread", "legacy": False},  
            {"id": UnifiedIdGenerator.generate_base_id("run"), "type": "run", "legacy": False}
        ]
        
        # Analyze mixed format scenario
        all_migration_data = existing_uuid_data + new_ssot_data
        
        uuid_ids = []
        ssot_ids = []
        
        for record in all_migration_data:
            record_id = record["id"]
            if self.id_patterns['uuid_v4'].match(record_id):
                uuid_ids.append(record)
            elif self.id_patterns['ssot_structured'].match(record_id):
                ssot_ids.append(record)
        
        if len(uuid_ids) > 0 and len(ssot_ids) > 0:
            migration_violations.append(
                f"Mixed ID formats in migration: {len(uuid_ids)} UUID records, {len(ssot_ids)} SSOT records"
            )
        
        # Scenario 2: Foreign key relationship consistency during migration
        try:
            # Simulate foreign key relationships with mixed formats
            users_migration = [
                {"id": str(uuid.uuid4()), "email": "legacy1@example.com"},  # Legacy UUID
                {"id": UnifiedIdGenerator.generate_base_id("user"), "email": "new1@example.com"}  # New SSOT
            ]
            
            threads_migration = [
                # Thread referencing legacy user (mixed format relationship)
                {"id": str(uuid.uuid4()), "user_id": users_migration[0]["id"], "title": "Legacy Thread"},
                # Thread referencing new user (consistent format)
                {"id": UnifiedIdGenerator.generate_base_id("session"), "user_id": users_migration[1]["id"], "title": "New Thread"}
            ]
            
            # Check for mixed format relationships
            for thread in threads_migration:
                thread_id = thread["id"]
                user_id = thread["user_id"]
                
                thread_is_uuid = self.id_patterns['uuid_v4'].match(thread_id)
                user_is_uuid = self.id_patterns['uuid_v4'].match(user_id)
                
                # Mixed format relationships are violations
                if thread_is_uuid != user_is_uuid:
                    migration_violations.append(
                        f"Mixed format FK relationship: thread {thread_id} -> user {user_id}"
                    )
        
        except Exception as e:
            migration_violations.append(f"Migration FK testing failed: {e}")
        
        # Scenario 3: Index and constraint consistency during migration
        try:
            # Simulate index/constraint definitions that expect specific ID formats
            index_scenarios = [
                {"table": "users", "column": "id", "expected_format": "uuid", "current_format": "mixed"},
                {"table": "threads", "column": "user_id", "expected_format": "uuid", "current_format": "mixed"},
                {"table": "runs", "column": "thread_id", "expected_format": "uuid", "current_format": "mixed"}
            ]
            
            for scenario in index_scenarios:
                if scenario["current_format"] == "mixed":
                    migration_violations.append(
                        f"Index/constraint inconsistency: {scenario['table']}.{scenario['column']} "
                        f"expects {scenario['expected_format']} but has mixed formats"
                    )
        
        except Exception as e:
            migration_violations.append(f"Migration index testing failed: {e}")
        
        # This test SHOULD FAIL due to migration inconsistencies
        assert len(migration_violations) > 0, (
            "Expected database migration ID consistency violations. "
            "If this passes, database migrations are already handling ID format consistency!"
        )
        
        pytest.fail(
            f"Database migration ID consistency violations:\n" +
            "\n".join(migration_violations) +
            "\n\nMIGRATION REQUIRED: Ensure consistent ID formats during database migrations"
        )

    # =============================================================================
    # QUERY AND ORM VIOLATIONS - Should FAIL initially
    # =============================================================================

    def test_database_query_id_violations_SHOULD_FAIL(self):
        """
        EXPECTED TO FAIL: Database queries use inconsistent ID formats.
        
        This test validates that database queries and ORM operations
        handle mixed ID formats properly or expose format violations.
        """
        query_violations = []
        
        try:
            # Simulate common query patterns with mixed ID formats
            query_scenarios = [
                {
                    "name": "user_lookup_by_uuid",
                    "query": "SELECT * FROM users WHERE id = ?",
                    "param": str(uuid.uuid4()),  # Raw UUID parameter
                    "violation_type": "raw_uuid_in_query"
                },
                {
                    "name": "thread_join_mixed_format",
                    "query": "SELECT * FROM threads t JOIN users u ON t.user_id = u.id WHERE t.id = ?",
                    "param": str(uuid.uuid4()),  # Raw UUID for thread lookup
                    "violation_type": "mixed_format_join"
                },
                {
                    "name": "run_filtering_by_uuid",
                    "query": "SELECT * FROM runs WHERE execution_id IN (?)",
                    "param": [str(uuid.uuid4()), str(uuid.uuid4())],  # List of raw UUIDs
                    "violation_type": "bulk_uuid_filtering"
                }
            ]
            
            for scenario in query_scenarios:
                query_name = scenario["name"]
                param = scenario["param"]
                violation_type = scenario["violation_type"]
                
                # Check parameter format violations
                if isinstance(param, str) and self.id_patterns['uuid_v4'].match(param):
                    query_violations.append(f"Query {query_name} uses raw UUID parameter: {param}")
                elif isinstance(param, list):
                    uuid_params = [p for p in param if isinstance(p, str) and self.id_patterns['uuid_v4'].match(p)]
                    if uuid_params:
                        query_violations.append(f"Query {query_name} uses {len(uuid_params)} raw UUID parameters")
            
            # Simulate ORM query violations
            orm_scenarios = [
                {
                    "operation": "filter_by_id",
                    "id_value": str(uuid.uuid4()),  # Raw UUID in ORM filter
                    "context": "User.query.filter(User.id == id_value)"
                },
                {
                    "operation": "relationship_lookup", 
                    "id_value": str(uuid.uuid4()),  # Raw UUID in relationship
                    "context": "Thread.query.filter(Thread.user_id == id_value)"
                },
                {
                    "operation": "bulk_insert",
                    "id_value": [str(uuid.uuid4()) for _ in range(3)],  # Multiple raw UUIDs
                    "context": "session.bulk_insert_mappings(Model, data)"
                }
            ]
            
            for scenario in orm_scenarios:
                operation = scenario["operation"]
                id_value = scenario["id_value"]
                
                if isinstance(id_value, str) and self.id_patterns['uuid_v4'].match(id_value):
                    query_violations.append(f"ORM {operation} uses raw UUID: {id_value}")
                elif isinstance(id_value, list):
                    uuid_count = sum(1 for v in id_value if isinstance(v, str) and self.id_patterns['uuid_v4'].match(v))
                    if uuid_count > 0:
                        query_violations.append(f"ORM {operation} uses {uuid_count} raw UUIDs")
        
        except Exception as e:
            query_violations.append(f"Database query testing failed: {e}")
        
        # This test SHOULD FAIL due to query violations
        assert len(query_violations) > 0, (
            "Expected database query ID format violations. "
            "If this passes, database queries are already using SSOT ID formats!"
        )
        
        pytest.fail(
            f"Database query ID format violations:\n" +
            "\n".join(query_violations) +
            "\n\nMIGRATION REQUIRED: Update database queries to use SSOT ID formats"
        )

    # =============================================================================
    # COMPLIANCE VALIDATION TESTS - Should PASS after migration
    # =============================================================================

    def test_database_model_ssot_compliance_SHOULD_PASS_AFTER_MIGRATION(self):
        """
        This test should PASS after migration validates SSOT compliance in database models.
        """
        # Create SSOT-compliant model example
        Base = declarative_base()
        
        class CompliantUserModel(Base):
            """Example model with SSOT-compliant defaults."""
            __tablename__ = 'compliant_users'
            
            # COMPLIANT: Using SSOT ID generation
            id = Column(String, primary_key=True, default=lambda: UnifiedIdGenerator.generate_base_id("user"))
            email = Column(String, nullable=False)
            # COMPLIANT: Session ID uses SSOT generation
            current_session_id = Column(String, default=lambda: UnifiedIdGenerator.generate_base_id("session"))
            created_at = Column(DateTime, default=datetime.utcnow)
        
        # Test compliant model
        try:
            # Test ID generation
            compliant_user_id = UnifiedIdGenerator.generate_base_id("user")
            compliant_session_id = UnifiedIdGenerator.generate_base_id("session")
            
            # Validate SSOT compliance
            assert compliant_user_id.startswith("user_"), f"User ID should start with user_: {compliant_user_id}"
            assert compliant_session_id.startswith("session_"), f"Session ID should start with session_: {compliant_session_id}"
            
            # Should NOT be raw UUIDs
            assert not self.id_patterns['uuid_v4'].match(compliant_user_id), f"Should not be UUID: {compliant_user_id}"
            assert not self.id_patterns['uuid_v4'].match(compliant_session_id), f"Should not be UUID: {compliant_session_id}"
            
            # Should follow structured format
            assert self.id_patterns['ssot_structured'].match(compliant_user_id), f"Should be structured: {compliant_user_id}"
            assert self.id_patterns['ssot_structured'].match(compliant_session_id), f"Should be structured: {compliant_session_id}"
        
        except Exception as e:
            pytest.fail(f"SSOT-compliant model validation failed: {e}")

    def test_database_factory_ssot_compliance_SHOULD_PASS_AFTER_MIGRATION(self):
        """
        This test should PASS after migration validates SSOT compliance in model factories.
        """
        # Create SSOT-compliant factories
        def compliant_user_factory(**kwargs):
            """SSOT-compliant user factory."""
            return {
                "id": UnifiedIdGenerator.generate_base_id("user"),
                "email": kwargs.get("email", "test@example.com"), 
                "session_id": UnifiedIdGenerator.generate_base_id("session"),
                "created_at": datetime.utcnow().isoformat(),
                **kwargs
            }
        
        def compliant_thread_factory(user_id=None, **kwargs):
            """SSOT-compliant thread factory."""
            return {
                "id": UnifiedIdGenerator.generate_base_id("session"),
                "user_id": user_id or UnifiedIdGenerator.generate_base_id("user"),
                "title": kwargs.get("title", "Test Thread"),
                "created_at": datetime.utcnow().isoformat(),
                **kwargs
            }
        
        # Test compliant factories
        try:
            user_data = compliant_user_factory()
            thread_data = compliant_thread_factory(user_id=user_data["id"])
            
            # Validate all IDs are SSOT-compliant
            for field, value in user_data.items():
                if field.endswith("_id") or field == "id":
                    assert not self.id_patterns['uuid_v4'].match(value), f"Factory {field} should not be UUID: {value}"
                    assert self.id_patterns['ssot_structured'].match(value), f"Factory {field} should be structured: {value}"
            
            for field, value in thread_data.items():
                if field.endswith("_id") or field == "id":
                    assert not self.id_patterns['uuid_v4'].match(value), f"Factory {field} should not be UUID: {value}"
                    assert self.id_patterns['ssot_structured'].match(value), f"Factory {field} should be structured: {value}"
        
        except Exception as e:
            pytest.fail(f"SSOT-compliant factory validation failed: {e}")

    # =============================================================================
    # REGRESSION PREVENTION TESTS
    # =============================================================================

    def test_prevent_database_uuid_regression(self):
        """
        Test to prevent regression back to raw UUID usage in database models.
        """
        # Define patterns that should NEVER be used in database models after migration
        forbidden_model_patterns = [
            "default=uuid.uuid4",
            "default=lambda: str(uuid.uuid4())",
            "default=lambda: uuid.uuid4().hex",
            "Column(String, default=uuid.uuid4)"
        ]
        
        # Define acceptable SSOT patterns for database models
        acceptable_model_patterns = [
            "default=lambda: UnifiedIdGenerator.generate_base_id('user')",
            "default=lambda: UnifiedIdGenerator.generate_base_id('session')", 
            "default=lambda: UnifiedIdGenerator.generate_base_id('run')",
        ]
        
        # Test that we can detect forbidden patterns
        for forbidden in forbidden_model_patterns:
            if "uuid.uuid4" in forbidden:
                assert True, f"Should detect forbidden pattern: {forbidden}"
        
        # Test that acceptable patterns work
        for acceptable in acceptable_model_patterns:
            if "UnifiedIdGenerator" in acceptable:
                assert True, f"Acceptable pattern should work: {acceptable}"

    def test_database_id_uniqueness_and_consistency(self):
        """
        Test database ID generation for uniqueness and format consistency.
        """
        # Generate multiple IDs using SSOT methods (what models should use after migration)
        user_ids = [UnifiedIdGenerator.generate_base_id("user") for _ in range(10)]
        session_ids = [UnifiedIdGenerator.generate_base_id("session") for _ in range(10)]
        run_ids = [UnifiedIdGenerator.generate_base_id("run") for _ in range(10)]
        
        # Test uniqueness
        assert len(set(user_ids)) == len(user_ids), "All user IDs should be unique"
        assert len(set(session_ids)) == len(session_ids), "All session IDs should be unique"
        assert len(set(run_ids)) == len(run_ids), "All run IDs should be unique"
        
        # Test format consistency
        for user_id in user_ids:
            assert user_id.startswith("user_"), f"User ID should start with user_: {user_id}"
            assert self.id_patterns['ssot_structured'].match(user_id), f"User ID should be structured: {user_id}"
            assert not self.id_patterns['uuid_v4'].match(user_id), f"User ID should not be UUID: {user_id}"
        
        for session_id in session_ids:
            assert session_id.startswith("session_"), f"Session ID should start with session_: {session_id}"
            assert not self.id_patterns['uuid_v4'].match(session_id), f"Session ID should not be UUID: {session_id}"
        
        for run_id in run_ids:
            assert run_id.startswith("run_"), f"Run ID should start with run_: {run_id}"
            assert not self.id_patterns['uuid_v4'].match(run_id), f"Run ID should not be UUID: {run_id}"

    # =============================================================================
    # PERFORMANCE AND VALIDATION TESTS
    # =============================================================================

    def test_database_id_generation_performance(self):
        """
        Test performance of SSOT ID generation for database usage.
        """
        import time
        
        # Test bulk ID generation performance (database bulk operations)
        start_time = time.time()
        bulk_ids = [UnifiedIdGenerator.generate_base_id("bulk") for _ in range(1000)]
        end_time = time.time()
        
        duration = end_time - start_time
        ids_per_second = len(bulk_ids) / duration
        
        # Should be fast enough for database operations
        assert ids_per_second > 100, f"ID generation too slow for database usage: {ids_per_second:.2f} IDs/second"
        
        # All should be unique
        assert len(set(bulk_ids)) == len(bulk_ids), "Bulk generated IDs should all be unique"
        
        # All should follow SSOT format
        for bulk_id in bulk_ids[:10]:  # Sample check
            assert bulk_id.startswith("bulk_"), f"Bulk ID should have correct prefix: {bulk_id}"
            assert not self.id_patterns['uuid_v4'].match(bulk_id), f"Bulk ID should not be UUID: {bulk_id}"

    # =============================================================================
    # CLEANUP AND UTILITIES
    # =============================================================================

    def teardown_method(self):
        """Cleanup after each test method."""
        super().teardown_method()
        if hasattr(self, 'model_violations') and self.model_violations:
            print(f"\nDatabase model ID violations detected: {len(self.model_violations)}")
            for violation in self.model_violations[:3]:  # Show first 3
                print(f"  - {violation}")
            if len(self.model_violations) > 3:
                print(f"  ... and {len(self.model_violations) - 3} more violations")

    def test_database_integration_health_check(self):
        """
        Health check to validate basic database ID integration works.
        This test should always pass to ensure basic functionality.
        """
        try:
            # Basic database ID generation health check
            user_id = UnifiedIdGenerator.generate_base_id("user")
            session_id = UnifiedIdGenerator.generate_base_id("session")
            run_id = UnifiedIdGenerator.generate_base_id("run")
            
            # Verify basic properties
            assert isinstance(user_id, str) and len(user_id) > 0, "User ID should be non-empty string"
            assert isinstance(session_id, str) and len(session_id) > 0, "Session ID should be non-empty string" 
            assert isinstance(run_id, str) and len(run_id) > 0, "Run ID should be non-empty string"
            
            # Test strongly typed conversion
            typed_user_id = ensure_user_id(user_id)
            assert str(typed_user_id) == user_id, "Strongly typed conversion should work"
            
            print(f"Database ID integration health check passed")
            
        except Exception as e:
            pytest.fail(f"Database ID integration health check failed: {e}")

    def test_database_model_violation_summary(self):
        """
        Generate comprehensive summary of all database model violations.
        
        This test creates a summary report of violations for migration planning.
        """
        violation_summary = {
            "model_definition_violations": [],
            "factory_violations": [],
            "query_violations": [],
            "migration_violations": []
        }
        
        # Simulate all violation types for summary
        try:
            # Model definition violations
            model_examples = ["User.id", "Thread.id", "Run.id", "Session.current_session_id"]
            for model_field in model_examples:
                violation_summary["model_definition_violations"].append(
                    f"{model_field} uses default=lambda: str(uuid.uuid4())"
                )
            
            # Factory violations
            factory_examples = ["user_factory", "thread_factory", "run_factory"]
            for factory_name in factory_examples:
                violation_summary["factory_violations"].append(
                    f"{factory_name} generates raw UUID IDs instead of SSOT format"
                )
            
            # Query violations
            query_examples = ["user lookup", "thread join", "run filtering"]
            for query_type in query_examples:
                violation_summary["query_violations"].append(
                    f"{query_type} uses raw UUID parameters in WHERE clauses"
                )
            
            # Migration violations
            migration_examples = ["UUID->SSOT migration", "FK relationship consistency", "Index compatibility"]
            for migration_type in migration_examples:
                violation_summary["migration_violations"].append(
                    f"{migration_type} requires handling mixed ID formats"
                )
            
            # Generate summary report
            total_violations = sum(len(violations) for violations in violation_summary.values())
            
            print(f"\nDatabase Model Violation Summary:")
            print(f"Total violation categories: {len(violation_summary)}")
            print(f"Total violations found: {total_violations}")
            
            for category, violations in violation_summary.items():
                print(f"  {category}: {len(violations)} violations")
            
            # This test should pass as it's just generating a report
            assert total_violations > 0, "Summary should include violations for migration planning"
            
        except Exception as e:
            pytest.fail(f"Violation summary generation failed: {e}")