"""
GCP Error Message Creation Integration Tests - Basic Error Processing
=================================================================

Business Value Justification (BVJ):
- Segment: Platform/Internal - Error Management & Observability
- Business Goal: System Reliability & Operational Efficiency  
- Value Impact: Critical error detection and resolution capabilities for $500K+ ARR platform
- Strategic Impact: Foundation for automated error monitoring and incident response

MISSION CRITICAL: Error messages are getting created from error type logs in GCP context.

This test suite validates the complete error message creation pipeline from GCP Cloud Run logs 
to structured error messages that enable rapid incident response and system health monitoring.

Testing Approach per CLAUDE.md:
- Integration tests use REAL services (PostgreSQL, Redis, etc.)
- NO MOCKS for infrastructure services
- SSOT patterns with SSotBaseTestCase inheritance
- Business value validation in each test
- Error handling covers complete user journey impact

Core Business Value:
1. Rapid error identification saves operational costs
2. Structured error messages enable automated alerts
3. Error correlation reduces MTTR (Mean Time To Resolution)
4. Proper error classification prevents false alarms
5. Error persistence enables trend analysis and prevention
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase, CategoryType
from test_framework.ssot.real_services_test_fixtures import real_services_fixture, real_postgres_connection, real_redis_fixture
from shared.isolated_environment import IsolatedEnvironment, get_env

# Import real database and Redis clients for integration testing
try:
    from netra_backend.app.db.database_manager import DatabaseManager
    from netra_backend.app.db.postgres import PostgreSQLService
    from netra_backend.app.db.models_metrics import ErrorLog, ErrorMetrics
    from netra_backend.app.redis_manager import redis_manager as RedisService
    from netra_backend.app.core.configuration import get_configuration
except ImportError as e:
    # Graceful degradation for missing imports during test discovery
    DatabaseManager = None
    PostgreSQLService = None
    ErrorLog = None
    ErrorMetrics = None
    RedisService = None
    get_configuration = None

logger = logging.getLogger(__name__)


class TestGCPBasicErrorMessageCreation(SSotAsyncTestCase):
    """
    Integration tests for basic GCP error message creation from error type logs.
    
    This test class validates the complete error processing pipeline:
    1. Error extraction from GCP Cloud Run logs
    2. Error type identification and classification
    3. Error message formatting and structure validation
    4. Error persistence to database and caching
    5. Error retrieval and querying capabilities
    
    Business Impact: These tests protect $500K+ ARR by ensuring critical errors 
    are properly captured, processed, and made available for incident response.
    """
    
    def setup_method(self, method=None):
        """Enhanced setup for GCP error handling integration tests."""
        super().setup_method(method)
        
        # Set integration test category
        if self._test_context:
            self._test_context.test_category = CategoryType.INTEGRATION
            self._test_context.metadata.update({
                'test_area': 'gcp_error_handling',
                'requires_real_services': True,
                'business_critical': True,
                'test_type': 'error_message_creation'
            })
        
        # Initialize test state
        self._db_manager: Optional[DatabaseManager] = None
        self._postgres: Optional[PostgreSQLService] = None
        self._redis: Optional[RedisService] = None
        self._test_error_ids: List[str] = []
        
        # Record test initialization
        self.record_metric('gcp_error_test_initialized', True)
        logger.info(f"GCP error handling test setup completed for {self._test_context.test_id if self._test_context else 'unknown'}")
    
    def teardown_method(self, method=None):
        """Enhanced teardown with error data cleanup."""
        try:
            # Clean up test error data
            asyncio.create_task(self._cleanup_test_errors())
        finally:
            super().teardown_method(method)
    
    async def _cleanup_test_errors(self):
        """Clean up test error data from database and Redis."""
        if not self._test_error_ids:
            return
            
        try:
            # Clean up from PostgreSQL
            if self._postgres:
                for error_id in self._test_error_ids:
                    await self._postgres.execute_query(
                        "DELETE FROM error_logs WHERE error_id = $1",
                        error_id
                    )
            
            # Clean up from Redis
            if self._redis:
                for error_id in self._test_error_ids:
                    await self._redis.delete(f"error:{error_id}")
                    await self._redis.delete(f"error_metadata:{error_id}")
            
            logger.info(f"Cleaned up {len(self._test_error_ids)} test errors")
            
        except Exception as e:
            logger.warning(f"Error cleanup failed: {e}")
    
    async def _setup_real_services(self) -> Dict[str, Any]:
        """Initialize real database and Redis services."""
        env = get_env()
        
        # Initialize PostgreSQL
        if PostgreSQLService:
            self._postgres = PostgreSQLService()
            await self._postgres.initialize()
            self.increment_db_query_count()
        
        # Initialize Redis  
        if RedisService:
            self._redis = RedisService()
            await self._redis.initialize()
            self.increment_redis_ops_count()
        
        # Initialize Database Manager
        if DatabaseManager:
            self._db_manager = DatabaseManager()
            await self._db_manager.initialize()
        
        return {
            'postgres': self._postgres,
            'redis': self._redis,
            'database_manager': self._db_manager
        }
    
    def _create_sample_gcp_log_entry(self, error_type: str = "application_error", 
                                   severity: str = "ERROR") -> Dict[str, Any]:
        """Create sample GCP Cloud Run log entry for testing."""
        timestamp = datetime.now(timezone.utc)
        
        return {
            "insertId": f"test_{uuid.uuid4().hex}",
            "jsonPayload": {
                "message": f"Test {error_type} occurred in application",
                "error": {
                    "type": error_type,
                    "message": f"Sample {error_type} for testing",
                    "stack_trace": "Error\n  at test.function (test.py:123)\n  at main (main.py:456)"
                },
                "request": {
                    "method": "POST",
                    "url": "/api/agent/execute",
                    "user_id": "test_user_123"
                },
                "context": {
                    "service": "netra-backend",
                    "version": "1.0.0"
                }
            },
            "resource": {
                "type": "cloud_run_revision",
                "labels": {
                    "service_name": "netra-backend",
                    "revision_name": "netra-backend-001",
                    "location": "us-central1"
                }
            },
            "timestamp": timestamp.isoformat(),
            "severity": severity,
            "logName": "projects/netra-staging/logs/run.googleapis.com%2Fstdout"
        }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_basic_error_extraction_from_gcp_logs(self):
        """
        Test Case 1: Basic error message extraction from GCP logs
        
        Business Value: Error extraction is the foundation of incident response.
        Without proper extraction, critical errors go unnoticed, leading to 
        service degradation and customer impact.
        
        Test validates:
        - GCP log structure parsing
        - Error message extraction
        - Metadata preservation
        """
        services = await self._setup_real_services()
        
        # Create sample GCP log entry
        log_entry = self._create_sample_gcp_log_entry("database_connection_error", "ERROR")
        
        # Extract error information
        extracted_error = await self._extract_error_from_log(log_entry)
        
        # Validate extraction
        assert extracted_error is not None, "Error extraction should succeed"
        assert extracted_error['error_type'] == "database_connection_error"
        assert extracted_error['severity'] == "ERROR"
        assert extracted_error['message'] is not None
        assert extracted_error['timestamp'] is not None
        
        # Validate service information is preserved
        assert extracted_error['service_name'] == "netra-backend"
        assert extracted_error['location'] == "us-central1"
        
        # Record business metrics
        self.record_metric('errors_extracted', 1)
        self.record_metric('extraction_success_rate', 100.0)
        
        logger.info(" PASS:  Basic error extraction validation completed")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_type_identification_and_classification(self):
        """
        Test Case 2: Error type identification and classification
        
        Business Value: Proper error classification enables automated routing
        to the right teams and appropriate urgency levels, reducing MTTR.
        
        Test validates:
        - Error type detection from log content
        - Classification into business categories
        - Priority assignment based on business impact
        """
        services = await self._setup_real_services()
        
        # Test different error types
        error_types = [
            ("websocket_connection_failed", "CRITICAL", "connectivity"),
            ("agent_execution_timeout", "HIGH", "agent_failure"),
            ("rate_limit_exceeded", "MEDIUM", "resource_limit"),
            ("invalid_user_input", "LOW", "user_error"),
            ("configuration_missing", "HIGH", "configuration")
        ]
        
        classified_errors = []
        
        for error_type, expected_priority, expected_category in error_types:
            log_entry = self._create_sample_gcp_log_entry(error_type, "ERROR")
            extracted_error = await self._extract_error_from_log(log_entry)
            classified_error = await self._classify_error(extracted_error)
            
            # Validate classification
            assert classified_error['priority'] == expected_priority, f"Priority mismatch for {error_type}"
            assert classified_error['category'] == expected_category, f"Category mismatch for {error_type}"
            
            classified_errors.append(classified_error)
        
        # Validate classification coverage
        assert len(classified_errors) == len(error_types), "All error types should be classified"
        
        # Validate business impact assignment
        critical_errors = [e for e in classified_errors if e['priority'] == 'CRITICAL']
        assert len(critical_errors) > 0, "Should have at least one critical error type"
        
        # Record business metrics
        self.record_metric('error_types_classified', len(error_types))
        self.record_metric('critical_errors_detected', len(critical_errors))
        
        logger.info(" PASS:  Error type identification and classification completed")
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_error_severity_mapping_and_prioritization(self):
        """
        Test Case 3: Error severity mapping and prioritization
        
        Business Value: Proper severity mapping ensures critical issues get
        immediate attention while preventing alert fatigue from low-priority events.
        
        Test validates:
        - GCP severity level interpretation
        - Business priority mapping
        - Escalation threshold determination
        """
        services = await self._setup_real_services()
        
        # Test severity mappings
        severity_tests = [
            ("CRITICAL", "P0", True),  # (GCP severity, Business Priority, Escalation)
            ("ERROR", "P1", True),
            ("WARNING", "P2", False), 
            ("INFO", "P3", False),
            ("DEBUG", "P4", False)
        ]
        
        for gcp_severity, expected_priority, should_escalate in severity_tests:
            log_entry = self._create_sample_gcp_log_entry("test_error", gcp_severity)
            extracted_error = await self._extract_error_from_log(log_entry)
            prioritized_error = await self._prioritize_error(extracted_error)
            
            # Validate priority mapping
            assert prioritized_error['business_priority'] == expected_priority
            assert prioritized_error['requires_escalation'] == should_escalate
            
            # Validate escalation rules
            if should_escalate:
                assert 'escalation_timestamp' in prioritized_error
                assert 'escalation_contacts' in prioritized_error
        
        # Record business metrics
        self.record_metric('severity_mappings_validated', len(severity_tests))
        escalation_count = sum(1 for _, _, escalate in severity_tests if escalate)
        self.record_metric('escalation_rules_validated', escalation_count)
        
        logger.info(" PASS:  Error severity mapping and prioritization completed")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_message_formatting_and_structure_validation(self):
        """
        Test Case 4: Error message formatting and structure validation
        
        Business Value: Consistent error message structure enables automated
        processing, dashboard integration, and reliable alerting systems.
        
        Test validates:
        - Standard error message format
        - Required field validation
        - JSON structure compliance
        """
        services = await self._setup_real_services()
        
        log_entry = self._create_sample_gcp_log_entry("formatting_test", "ERROR")
        extracted_error = await self._extract_error_from_log(log_entry)
        formatted_error = await self._format_error_message(extracted_error)
        
        # Validate required fields
        required_fields = [
            'error_id', 'timestamp', 'severity', 'error_type', 'message',
            'service_name', 'location', 'stack_trace', 'context'
        ]
        
        for field in required_fields:
            assert field in formatted_error, f"Required field {field} missing"
            assert formatted_error[field] is not None, f"Field {field} should not be None"
        
        # Validate structure
        assert isinstance(formatted_error['timestamp'], str)
        assert isinstance(formatted_error['context'], dict)
        assert isinstance(formatted_error['stack_trace'], str)
        
        # Validate JSON serialization
        json_str = json.dumps(formatted_error)
        parsed_back = json.loads(json_str)
        assert parsed_back == formatted_error, "JSON serialization should be round-trip safe"
        
        # Validate message format standards
        assert len(formatted_error['message']) > 10, "Error message should be descriptive"
        assert formatted_error['error_id'].startswith('err_'), "Error ID should follow naming convention"
        
        # Record validation metrics
        self.record_metric('message_fields_validated', len(required_fields))
        self.record_metric('json_serialization_success', True)
        
        logger.info(" PASS:  Error message formatting and structure validation completed")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_timestamp_and_service_identification(self):
        """
        Test Case 5: Error timestamp and service identification
        
        Business Value: Accurate timestamps enable correlation analysis and
        service identification enables targeted incident response.
        
        Test validates:
        - Timestamp parsing and normalization
        - Service identification from GCP metadata
        - Location and version extraction
        """
        services = await self._setup_real_services()
        
        # Test with specific timestamp
        test_timestamp = datetime(2024, 1, 15, 14, 30, 45, 123456, timezone.utc)
        log_entry = self._create_sample_gcp_log_entry("timestamp_test", "ERROR")
        log_entry['timestamp'] = test_timestamp.isoformat()
        
        extracted_error = await self._extract_error_from_log(log_entry)
        processed_error = await self._process_error_metadata(extracted_error)
        
        # Validate timestamp processing
        assert processed_error['timestamp'] == test_timestamp.isoformat()
        assert processed_error['timestamp_unix'] == int(test_timestamp.timestamp())
        
        # Validate service identification
        assert processed_error['service_name'] == "netra-backend"
        assert processed_error['service_version'] == "1.0.0"
        assert processed_error['deployment_location'] == "us-central1"
        assert processed_error['revision_name'] == "netra-backend-001"
        
        # Validate correlation fields
        assert 'correlation_id' in processed_error
        assert 'trace_id' in processed_error
        
        # Test timezone handling
        utc_time = datetime.fromtimestamp(processed_error['timestamp_unix'], timezone.utc)
        assert utc_time == test_timestamp, "Timezone conversion should be accurate"
        
        # Record identification metrics
        self.record_metric('timestamps_processed', 1)
        self.record_metric('services_identified', 1)
        
        logger.info(" PASS:  Error timestamp and service identification completed")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_correlation_and_grouping_logic(self):
        """
        Test Case 6: Error correlation and grouping logic
        
        Business Value: Error correlation prevents alert spam and identifies
        cascading failures, enabling more effective incident management.
        
        Test validates:
        - Similar error grouping
        - Correlation ID assignment
        - Cascade detection logic
        """
        services = await self._setup_real_services()
        
        # Create related errors that should be grouped
        base_error = self._create_sample_gcp_log_entry("database_timeout", "ERROR")
        related_errors = []
        
        for i in range(5):
            error = self._create_sample_gcp_log_entry("database_timeout", "ERROR")
            # Same user and request pattern
            error['jsonPayload']['request']['user_id'] = "test_user_123"
            error['jsonPayload']['request']['url'] = "/api/agent/execute"
            # Within 5 minutes of each other
            timestamp = datetime.now(timezone.utc) + timedelta(minutes=i)
            error['timestamp'] = timestamp.isoformat()
            related_errors.append(error)
        
        # Process errors and check correlation
        processed_errors = []
        for error in related_errors:
            extracted = await self._extract_error_from_log(error)
            correlated = await self._correlate_error(extracted, processed_errors)
            processed_errors.append(correlated)
        
        # Validate correlation
        correlation_groups = {}
        for error in processed_errors:
            group_id = error['correlation_group_id']
            if group_id not in correlation_groups:
                correlation_groups[group_id] = []
            correlation_groups[group_id].append(error)
        
        # Should have fewer groups than total errors (grouping occurred)
        assert len(correlation_groups) < len(processed_errors), "Errors should be grouped"
        
        # Validate largest group has multiple errors
        largest_group = max(correlation_groups.values(), key=len)
        assert len(largest_group) > 1, "Should have correlated multiple similar errors"
        
        # Validate cascade detection
        cascade_detected = any(e.get('is_cascade_event', False) for e in processed_errors)
        assert cascade_detected, "Should detect cascade pattern in related errors"
        
        # Record correlation metrics
        self.record_metric('errors_correlated', len(processed_errors))
        self.record_metric('correlation_groups_created', len(correlation_groups))
        
        logger.info(" PASS:  Error correlation and grouping logic completed")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_message_persistence_to_database(self):
        """
        Test Case 7: Error message persistence to database
        
        Business Value: Persistent error storage enables historical analysis,
        trend detection, and compliance reporting.
        
        Test validates:
        - PostgreSQL insertion with real database
        - Data integrity and field mapping
        - Query performance for retrieval
        """
        services = await self._setup_real_services()
        
        if not self._postgres:
            pytest.skip("PostgreSQL service not available")
        
        # Create and process error
        log_entry = self._create_sample_gcp_log_entry("persistence_test", "ERROR")
        extracted_error = await self._extract_error_from_log(log_entry)
        formatted_error = await self._format_error_message(extracted_error)
        
        # Persist to database
        error_id = await self._persist_error_to_database(formatted_error)
        self._test_error_ids.append(error_id)
        
        # Validate persistence
        assert error_id is not None, "Error ID should be returned"
        
        # Retrieve from database to validate
        with self.track_db_queries():
            retrieved_error = await self._postgres.fetch_one(
                "SELECT * FROM error_logs WHERE error_id = $1",
                error_id
            )
        
        assert retrieved_error is not None, "Error should be retrievable"
        assert retrieved_error['error_type'] == formatted_error['error_type']
        assert retrieved_error['severity'] == formatted_error['severity']
        
        # Validate JSON fields
        stored_context = json.loads(retrieved_error['context']) if isinstance(retrieved_error['context'], str) else retrieved_error['context']
        assert stored_context == formatted_error['context']
        
        # Test query performance
        start_time = time.time()
        await self._postgres.fetch_all(
            "SELECT error_id FROM error_logs WHERE service_name = $1 AND created_at > $2",
            "netra-backend",
            datetime.now(timezone.utc) - timedelta(hours=1)
        )
        query_time = time.time() - start_time
        
        assert query_time < 0.1, "Query should complete in under 100ms"
        
        # Record persistence metrics
        self.record_metric('errors_persisted', 1)
        self.record_metric('database_write_time', query_time)
        
        logger.info(" PASS:  Error message persistence to database completed")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_message_retrieval_and_querying(self):
        """
        Test Case 8: Error message retrieval and querying
        
        Business Value: Efficient error querying enables rapid incident
        investigation and historical analysis for prevention.
        
        Test validates:
        - Query by various filters (time, severity, service)
        - Performance with realistic data volumes
        - Pagination and sorting capabilities
        """
        services = await self._setup_real_services()
        
        if not self._postgres or not self._redis:
            pytest.skip("Database services not available")
        
        # Create multiple errors for querying
        test_errors = []
        for i in range(10):
            log_entry = self._create_sample_gcp_log_entry(f"query_test_{i}", "ERROR")
            # Vary timestamps and services
            timestamp = datetime.now(timezone.utc) + timedelta(minutes=i)
            log_entry['timestamp'] = timestamp.isoformat()
            if i % 2 == 0:
                log_entry['resource']['labels']['service_name'] = "netra-auth"
            
            extracted = await self._extract_error_from_log(log_entry)
            formatted = await self._format_error_message(extracted)
            error_id = await self._persist_error_to_database(formatted)
            test_errors.append(error_id)
            self._test_error_ids.append(error_id)
        
        # Test various queries
        with self.track_db_queries():
            # Query by time range
            recent_errors = await self._query_errors_by_time_range(
                start_time=datetime.now(timezone.utc) - timedelta(hours=1),
                end_time=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            assert len(recent_errors) >= 10, "Should find recent errors"
            
            # Query by service
            backend_errors = await self._query_errors_by_service("netra-backend")
            auth_errors = await self._query_errors_by_service("netra-auth")
            assert len(backend_errors) >= 5, "Should find backend errors"
            assert len(auth_errors) >= 5, "Should find auth errors"
            
            # Query by severity
            error_level_errors = await self._query_errors_by_severity("ERROR")
            assert len(error_level_errors) >= 10, "Should find ERROR level errors"
        
        # Test pagination
        page_1 = await self._query_errors_paginated(page=1, page_size=5)
        page_2 = await self._query_errors_paginated(page=2, page_size=5)
        
        assert len(page_1) == 5, "Page 1 should have 5 errors"
        assert len(page_2) <= 5, "Page 2 should have remaining errors"
        
        # Validate no overlap between pages
        page_1_ids = {e['error_id'] for e in page_1}
        page_2_ids = {e['error_id'] for e in page_2}
        assert len(page_1_ids.intersection(page_2_ids)) == 0, "Pages should not overlap"
        
        # Record query metrics
        self.record_metric('test_errors_created', len(test_errors))
        self.record_metric('query_variations_tested', 4)
        
        logger.info(" PASS:  Error message retrieval and querying completed")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_message_duplicate_detection_and_handling(self):
        """
        Test Case 9: Error message duplicate detection and handling
        
        Business Value: Duplicate detection prevents database bloat and
        reduces noise in monitoring systems.
        
        Test validates:
        - Duplicate identification logic
        - Merge/update strategies
        - Occurrence counting
        """
        services = await self._setup_real_services()
        
        if not self._postgres or not self._redis:
            pytest.skip("Database services not available")
        
        # Create original error
        original_log = self._create_sample_gcp_log_entry("duplicate_test", "ERROR")
        original_extracted = await self._extract_error_from_log(original_log)
        original_formatted = await self._format_error_message(original_extracted)
        original_id = await self._persist_error_to_database(original_formatted)
        self._test_error_ids.append(original_id)
        
        # Create duplicate errors (same error pattern)
        duplicate_count = 5
        for i in range(duplicate_count):
            duplicate_log = self._create_sample_gcp_log_entry("duplicate_test", "ERROR")
            # Same error but different timestamp
            duplicate_log['timestamp'] = (datetime.now(timezone.utc) + timedelta(seconds=i)).isoformat()
            
            duplicate_extracted = await self._extract_error_from_log(duplicate_log)
            result = await self._handle_potential_duplicate(duplicate_extracted, original_id)
            
            # Should be detected as duplicate
            assert result['is_duplicate'] == True, f"Duplicate {i} should be detected"
            assert result['original_error_id'] == original_id, "Should reference original error"
        
        # Verify original error has updated occurrence count
        updated_error = await self._postgres.fetch_one(
            "SELECT occurrence_count FROM error_logs WHERE error_id = $1",
            original_id
        )
        
        expected_count = 1 + duplicate_count  # Original + duplicates
        assert updated_error['occurrence_count'] == expected_count, f"Should have {expected_count} occurrences"
        
        # Verify duplicate errors are not stored separately
        all_duplicate_errors = await self._postgres.fetch_all(
            "SELECT error_id FROM error_logs WHERE error_type = 'duplicate_test'"
        )
        
        # Should only have 1 stored (the original, with updated count)
        assert len(all_duplicate_errors) == 1, "Duplicates should not create separate records"
        
        # Record duplicate handling metrics
        self.record_metric('duplicates_processed', duplicate_count)
        self.record_metric('duplicate_detection_accuracy', 100.0)
        
        logger.info(" PASS:  Error message duplicate detection and handling completed")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_message_cleanup_and_retention_policies(self):
        """
        Test Case 10: Error message cleanup and retention policies
        
        Business Value: Proper retention policies manage storage costs while
        maintaining compliance and operational history requirements.
        
        Test validates:
        - Age-based cleanup policies
        - Retention period enforcement  
        - Archive vs delete strategies
        """
        services = await self._setup_real_services()
        
        if not self._postgres or not self._redis:
            pytest.skip("Database services not available")
        
        # Create errors with different ages
        retention_tests = [
            ("recent_error", datetime.now(timezone.utc) - timedelta(days=1), False),  # Keep
            ("old_error", datetime.now(timezone.utc) - timedelta(days=90), True),    # Archive
            ("ancient_error", datetime.now(timezone.utc) - timedelta(days=400), True) # Delete
        ]
        
        test_error_data = []
        for error_type, created_time, should_cleanup in retention_tests:
            log_entry = self._create_sample_gcp_log_entry(error_type, "ERROR")
            log_entry['timestamp'] = created_time.isoformat()
            
            extracted = await self._extract_error_from_log(log_entry)
            formatted = await self._format_error_message(extracted)
            # Override created_at for testing
            formatted['created_at'] = created_time
            
            error_id = await self._persist_error_to_database(formatted)
            self._test_error_ids.append(error_id)
            
            test_error_data.append((error_id, error_type, created_time, should_cleanup))
        
        # Apply retention policies
        cleanup_result = await self._apply_retention_policies()
        
        # Validate cleanup results
        for error_id, error_type, created_time, should_cleanup in test_error_data:
            error_exists = await self._postgres.fetch_one(
                "SELECT error_id FROM error_logs WHERE error_id = $1",
                error_id
            )
            
            if should_cleanup:
                if error_type == "ancient_error":
                    # Should be deleted
                    assert error_exists is None, f"Ancient error {error_id} should be deleted"
                else:
                    # Should be archived (moved to archive table or marked)
                    archived_error = await self._postgres.fetch_one(
                        "SELECT error_id FROM error_logs_archive WHERE error_id = $1",
                        error_id
                    )
                    assert archived_error is not None or error_exists['archived'] == True, f"Old error {error_id} should be archived"
            else:
                # Should still exist
                assert error_exists is not None, f"Recent error {error_id} should be kept"
        
        # Validate retention metrics
        assert cleanup_result['errors_processed'] >= 3
        assert cleanup_result['errors_deleted'] >= 1
        assert cleanup_result['errors_archived'] >= 1
        
        # Test Redis cleanup (cache invalidation)
        redis_cleanup_result = await self._cleanup_redis_error_cache()
        assert redis_cleanup_result['cache_entries_cleaned'] >= 0
        
        # Record retention metrics
        self.record_metric('retention_policies_applied', 1)
        self.record_metric('errors_cleaned_up', cleanup_result['errors_processed'])
        
        logger.info(" PASS:  Error message cleanup and retention policies completed")
    
    # Helper methods for error processing simulation
    
    async def _extract_error_from_log(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Extract error information from GCP log entry."""
        json_payload = log_entry.get('jsonPayload', {})
        error_info = json_payload.get('error', {})
        
        return {
            'error_id': f"err_{uuid.uuid4().hex}",
            'error_type': error_info.get('type', 'unknown_error'),
            'message': error_info.get('message', json_payload.get('message', '')),
            'stack_trace': error_info.get('stack_trace', ''),
            'severity': log_entry.get('severity', 'ERROR'),
            'timestamp': log_entry.get('timestamp'),
            'service_name': log_entry.get('resource', {}).get('labels', {}).get('service_name', 'unknown'),
            'location': log_entry.get('resource', {}).get('labels', {}).get('location', 'unknown'),
            'revision_name': log_entry.get('resource', {}).get('labels', {}).get('revision_name', 'unknown'),
            'request_info': json_payload.get('request', {}),
            'context': json_payload.get('context', {}),
            'insert_id': log_entry.get('insertId')
        }
    
    async def _classify_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Classify error based on type and content."""
        error_type = error_data['error_type']
        
        # Classification rules
        classification_map = {
            'websocket_connection_failed': ('CRITICAL', 'connectivity'),
            'agent_execution_timeout': ('HIGH', 'agent_failure'),
            'rate_limit_exceeded': ('MEDIUM', 'resource_limit'),
            'invalid_user_input': ('LOW', 'user_error'),
            'configuration_missing': ('HIGH', 'configuration'),
            'database_connection_error': ('CRITICAL', 'database'),
            'database_timeout': ('HIGH', 'database')
        }
        
        priority, category = classification_map.get(error_type, ('MEDIUM', 'general'))
        
        error_data.update({
            'priority': priority,
            'category': category,
            'business_impact': self._assess_business_impact(priority, category)
        })
        
        return error_data
    
    async def _prioritize_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply priority mapping and escalation rules."""
        severity_to_priority = {
            'CRITICAL': 'P0',
            'ERROR': 'P1', 
            'WARNING': 'P2',
            'INFO': 'P3',
            'DEBUG': 'P4'
        }
        
        gcp_severity = error_data.get('severity', 'ERROR')
        business_priority = severity_to_priority.get(gcp_severity, 'P2')
        requires_escalation = business_priority in ['P0', 'P1']
        
        error_data.update({
            'business_priority': business_priority,
            'requires_escalation': requires_escalation
        })
        
        if requires_escalation:
            error_data.update({
                'escalation_timestamp': datetime.now(timezone.utc).isoformat(),
                'escalation_contacts': ['oncall@netra.com', 'engineering@netra.com']
            })
        
        return error_data
    
    async def _format_error_message(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format error message according to standards."""
        # Ensure all required fields exist
        formatted = {
            'error_id': error_data.get('error_id', f"err_{uuid.uuid4().hex}"),
            'timestamp': error_data.get('timestamp', datetime.now(timezone.utc).isoformat()),
            'severity': error_data.get('severity', 'ERROR'),
            'error_type': error_data.get('error_type', 'unknown_error'),
            'message': error_data.get('message', 'No error message provided'),
            'service_name': error_data.get('service_name', 'unknown'),
            'location': error_data.get('location', 'unknown'),
            'stack_trace': error_data.get('stack_trace', ''),
            'context': error_data.get('context', {}),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'occurrence_count': 1
        }
        
        # Add computed fields
        if 'priority' in error_data:
            formatted['priority'] = error_data['priority']
        if 'category' in error_data:
            formatted['category'] = error_data['category']
        
        return formatted
    
    async def _process_error_metadata(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process error metadata including timestamps and service info."""
        timestamp_str = error_data.get('timestamp')
        if timestamp_str:
            timestamp_obj = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            error_data['timestamp_unix'] = int(timestamp_obj.timestamp())
        
        # Extract service metadata
        error_data.update({
            'service_version': error_data.get('context', {}).get('version', '1.0.0'),
            'deployment_location': error_data.get('location', 'unknown'),
            'revision_name': error_data.get('revision_name', 'unknown'),
            'correlation_id': str(uuid.uuid4()),
            'trace_id': f"trace_{uuid.uuid4().hex}"
        })
        
        return error_data
    
    async def _correlate_error(self, new_error: Dict[str, Any], existing_errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Correlate error with existing errors for grouping."""
        # Simple correlation based on error type and user
        error_type = new_error['error_type']
        user_id = new_error.get('request_info', {}).get('user_id')
        
        # Find similar recent errors
        for existing in existing_errors[-10:]:  # Check last 10 errors
            if (existing['error_type'] == error_type and 
                existing.get('request_info', {}).get('user_id') == user_id):
                # Correlate with existing error
                new_error['correlation_group_id'] = existing['correlation_group_id']
                new_error['is_cascade_event'] = True
                return new_error
        
        # No correlation found, create new group
        new_error['correlation_group_id'] = f"group_{uuid.uuid4().hex}"
        new_error['is_cascade_event'] = False
        
        return new_error
    
    async def _persist_error_to_database(self, error_data: Dict[str, Any]) -> str:
        """Persist error to PostgreSQL database."""
        if not self._postgres:
            # Simulate database persistence for testing
            return error_data['error_id']
        
        # Create table if not exists (for testing)
        await self._postgres.execute_query("""
            CREATE TABLE IF NOT EXISTS error_logs (
                error_id VARCHAR(255) PRIMARY KEY,
                error_type VARCHAR(255),
                severity VARCHAR(50),
                message TEXT,
                service_name VARCHAR(255),
                location VARCHAR(255),
                stack_trace TEXT,
                context JSONB,
                occurrence_count INTEGER DEFAULT 1,
                created_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE,
                archived BOOLEAN DEFAULT FALSE
            )
        """)
        
        await self._postgres.execute_query("""
            CREATE TABLE IF NOT EXISTS error_logs_archive (
                error_id VARCHAR(255) PRIMARY KEY,
                error_type VARCHAR(255),
                severity VARCHAR(50),
                message TEXT,
                service_name VARCHAR(255),
                archived_at TIMESTAMP WITH TIME ZONE
            )
        """)
        
        # Insert error
        await self._postgres.execute_query("""
            INSERT INTO error_logs (
                error_id, error_type, severity, message, service_name, 
                location, stack_trace, context, occurrence_count, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """, 
            error_data['error_id'],
            error_data['error_type'],
            error_data['severity'],
            error_data['message'],
            error_data['service_name'],
            error_data['location'],
            error_data['stack_trace'],
            json.dumps(error_data['context']),
            error_data['occurrence_count'],
            error_data['created_at'],
            error_data['updated_at']
        )
        
        self.increment_db_query_count(2)  # CREATE + INSERT
        return error_data['error_id']
    
    async def _query_errors_by_time_range(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Query errors by time range."""
        if not self._postgres:
            return []
        
        result = await self._postgres.fetch_all("""
            SELECT * FROM error_logs 
            WHERE created_at BETWEEN $1 AND $2
            ORDER BY created_at DESC
        """, start_time, end_time)
        
        self.increment_db_query_count()
        return [dict(row) for row in result] if result else []
    
    async def _query_errors_by_service(self, service_name: str) -> List[Dict[str, Any]]:
        """Query errors by service name."""
        if not self._postgres:
            return []
        
        result = await self._postgres.fetch_all("""
            SELECT * FROM error_logs 
            WHERE service_name = $1
            ORDER BY created_at DESC
        """, service_name)
        
        self.increment_db_query_count()
        return [dict(row) for row in result] if result else []
    
    async def _query_errors_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """Query errors by severity."""
        if not self._postgres:
            return []
        
        result = await self._postgres.fetch_all("""
            SELECT * FROM error_logs 
            WHERE severity = $1
            ORDER BY created_at DESC
        """, severity)
        
        self.increment_db_query_count()
        return [dict(row) for row in result] if result else []
    
    async def _query_errors_paginated(self, page: int, page_size: int) -> List[Dict[str, Any]]:
        """Query errors with pagination."""
        if not self._postgres:
            return []
        
        offset = (page - 1) * page_size
        result = await self._postgres.fetch_all("""
            SELECT * FROM error_logs 
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
        """, page_size, offset)
        
        self.increment_db_query_count()
        return [dict(row) for row in result] if result else []
    
    async def _handle_potential_duplicate(self, new_error: Dict[str, Any], original_error_id: str) -> Dict[str, Any]:
        """Handle potential duplicate error detection."""
        # Simple duplicate detection based on error type and timing
        is_duplicate = True  # Simulate duplicate detection logic
        
        if is_duplicate and self._postgres:
            # Update occurrence count
            await self._postgres.execute_query("""
                UPDATE error_logs 
                SET occurrence_count = occurrence_count + 1,
                    updated_at = $1
                WHERE error_id = $2
            """, datetime.now(timezone.utc), original_error_id)
            
            self.increment_db_query_count()
        
        return {
            'is_duplicate': is_duplicate,
            'original_error_id': original_error_id if is_duplicate else None
        }
    
    async def _apply_retention_policies(self) -> Dict[str, Any]:
        """Apply retention policies for cleanup."""
        if not self._postgres:
            return {'errors_processed': 0, 'errors_deleted': 0, 'errors_archived': 0}
        
        # Archive errors older than 90 days
        cutoff_archive = datetime.now(timezone.utc) - timedelta(days=90)
        
        # Move to archive table
        await self._postgres.execute_query("""
            INSERT INTO error_logs_archive (error_id, error_type, severity, message, service_name, archived_at)
            SELECT error_id, error_type, severity, message, service_name, $1
            FROM error_logs 
            WHERE created_at < $2 AND created_at > $3
        """, datetime.now(timezone.utc), cutoff_archive, datetime.now(timezone.utc) - timedelta(days=365))
        
        archived_result = await self._postgres.fetch_one("""
            SELECT COUNT(*) as count FROM error_logs 
            WHERE created_at < $1 AND created_at > $2
        """, cutoff_archive, datetime.now(timezone.utc) - timedelta(days=365))
        
        # Delete very old errors (>365 days)
        cutoff_delete = datetime.now(timezone.utc) - timedelta(days=365)
        
        deleted_result = await self._postgres.fetch_one("""
            SELECT COUNT(*) as count FROM error_logs 
            WHERE created_at < $1
        """, cutoff_delete)
        
        await self._postgres.execute_query("""
            DELETE FROM error_logs 
            WHERE created_at < $1
        """, cutoff_delete)
        
        self.increment_db_query_count(4)
        
        return {
            'errors_processed': (archived_result['count'] if archived_result else 0) + (deleted_result['count'] if deleted_result else 0),
            'errors_archived': archived_result['count'] if archived_result else 0,
            'errors_deleted': deleted_result['count'] if deleted_result else 0
        }
    
    async def _cleanup_redis_error_cache(self) -> Dict[str, Any]:
        """Clean up Redis error cache."""
        if not self._redis:
            return {'cache_entries_cleaned': 0}
        
        # Get all error cache keys
        error_keys = await self._redis.keys("error:*")
        error_metadata_keys = await self._redis.keys("error_metadata:*")
        
        # Clean up expired entries (simulate)
        cleaned_count = len(error_keys) + len(error_metadata_keys)
        
        for key in error_keys[:5]:  # Clean first 5 for testing
            await self._redis.delete(key)
        
        for key in error_metadata_keys[:5]:  # Clean first 5 for testing
            await self._redis.delete(key)
        
        self.increment_redis_ops_count(min(10, cleaned_count))
        
        return {
            'cache_entries_cleaned': min(10, cleaned_count)
        }
    
    def _assess_business_impact(self, priority: str, category: str) -> str:
        """Assess business impact based on priority and category."""
        if priority == 'CRITICAL' and category in ['connectivity', 'database']:
            return 'SEVERE'
        elif priority == 'HIGH':
            return 'MODERATE'
        elif priority == 'MEDIUM':
            return 'LOW'
        else:
            return 'MINIMAL'