"""
Test Startup Types - Pydantic Models for Status Tracking

Business Value Justification (BVJ):
- Segment: Platform/Internal (enables all customer segments)
- Business Goal: Data Integrity and System Observability
- Value Impact: Ensures startup status data is validated and consistent
- Strategic Impact: Enables reliable startup monitoring and troubleshooting

CRITICAL: These models are the SSOT for all startup status tracking.
Tests MUST validate field constraints, enum values, and data serialization.
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, List, Any
from test_framework.base import BaseTestCase
from pydantic import ValidationError

from netra_backend.app.schemas.startup_types import (
    ServiceType, Environment, LastStartup, MigrationStatus,
    ServiceConfig, CrashEntry, HealthCheckHistory, StartupStatus,
    StartupEvent, ErrorPhase, ErrorType, StartupError,
    ErrorPattern, ErrorTrend
)


class TestServiceTypeEnum(BaseTestCase):
    """Test ServiceType enum values and validation."""
    
    def test_service_type_values(self):
        """Test all ServiceType enum values are correct."""
        assert ServiceType.BACKEND == "backend"
        assert ServiceType.FRONTEND == "frontend"
        
    def test_service_type_string_conversion(self):
        """Test ServiceType can be created from strings."""
        assert ServiceType("backend") == ServiceType.BACKEND
        assert ServiceType("frontend") == ServiceType.FRONTEND
        
    def test_service_type_invalid_value_raises_error(self):
        """Test invalid ServiceType values raise ValidationError."""
        with pytest.raises(ValueError):
            ServiceType("invalid_service")
            
    def test_service_type_case_sensitive(self):
        """Test ServiceType is case sensitive."""
        with pytest.raises(ValueError):
            ServiceType("BACKEND")
        with pytest.raises(ValueError):
            ServiceType("Frontend")


class TestEnvironmentEnum(BaseTestCase):
    """Test Environment enum values and validation."""
    
    def test_environment_values(self):
        """Test all Environment enum values are correct."""
        assert Environment.DEV == "dev"
        assert Environment.TEST == "test"
        assert Environment.STAGING == "staging"
        assert Environment.PROD == "prod"
        
    def test_environment_string_conversion(self):
        """Test Environment can be created from strings."""
        assert Environment("dev") == Environment.DEV
        assert Environment("test") == Environment.TEST
        assert Environment("staging") == Environment.STAGING
        assert Environment("prod") == Environment.PROD
        
    def test_environment_invalid_value_raises_error(self):
        """Test invalid Environment values raise ValidationError."""
        with pytest.raises(ValueError):
            Environment("production")  # Should be "prod"
        with pytest.raises(ValueError):
            Environment("development")  # Should be "dev"
            
    def test_environment_case_sensitive(self):
        """Test Environment is case sensitive."""
        with pytest.raises(ValueError):
            Environment("DEV")
        with pytest.raises(ValueError):
            Environment("Test")


class TestLastStartupModel(BaseTestCase):
    """Test LastStartup Pydantic model validation."""
    
    def test_last_startup_creation_valid(self):
        """Test LastStartup model creation with valid data."""
        timestamp = datetime.now(timezone.utc)
        startup = LastStartup(
            timestamp=timestamp,
            success=True,
            duration_ms=1500,
            environment=Environment.DEV,
            errors=[],
            warnings=[]
        )
        
        assert startup.timestamp == timestamp
        assert startup.success is True
        assert startup.duration_ms == 1500
        assert startup.environment == Environment.DEV
        assert startup.errors == []
        assert startup.warnings == []
        
    def test_last_startup_with_errors_and_warnings(self):
        """Test LastStartup model with errors and warnings."""
        startup = LastStartup(
            timestamp=datetime.now(timezone.utc),
            success=False,
            duration_ms=5000,
            environment=Environment.STAGING,
            errors=["Database connection failed", "Redis unavailable"],
            warnings=["ClickHouse optional service down"]
        )
        
        assert startup.success is False
        assert startup.duration_ms == 5000
        assert len(startup.errors) == 2
        assert len(startup.warnings) == 1
        assert "Database connection failed" in startup.errors
        assert "ClickHouse optional service down" in startup.warnings
        
    def test_last_startup_duration_validation(self):
        """Test LastStartup duration_ms field validation (must be >= 0)."""
        # Valid duration
        startup = LastStartup(
            timestamp=datetime.now(timezone.utc),
            success=True,
            duration_ms=0,
            environment=Environment.TEST
        )
        assert startup.duration_ms == 0
        
        # Invalid negative duration
        with pytest.raises(ValidationError) as excinfo:
            LastStartup(
                timestamp=datetime.now(timezone.utc),
                success=True,
                duration_ms=-100,
                environment=Environment.TEST
            )
        assert "greater than or equal to 0" in str(excinfo.value)
        
    def test_last_startup_defaults(self):
        """Test LastStartup model with default values."""
        timestamp = datetime.now(timezone.utc)
        startup = LastStartup(
            timestamp=timestamp,
            success=True,
            duration_ms=1000,
            environment=Environment.PROD
        )
        
        # Default values should be empty lists
        assert startup.errors == []
        assert startup.warnings == []


class TestMigrationStatusModel(BaseTestCase):
    """Test MigrationStatus Pydantic model validation."""
    
    def test_migration_status_creation_defaults(self):
        """Test MigrationStatus model creation with defaults."""
        migration = MigrationStatus()
        
        assert migration.last_run is None
        assert migration.current_version is None
        assert migration.pending_migrations == []
        assert migration.failed_migrations == []
        assert migration.auto_run is True
        
    def test_migration_status_with_data(self):
        """Test MigrationStatus model with complete data."""
        last_run = datetime.now(timezone.utc)
        migration = MigrationStatus(
            last_run=last_run,
            current_version="v2.1.3",
            pending_migrations=["001_add_user_table", "002_add_indexes"],
            failed_migrations=["003_broken_migration"],
            auto_run=False
        )
        
        assert migration.last_run == last_run
        assert migration.current_version == "v2.1.3"
        assert len(migration.pending_migrations) == 2
        assert "001_add_user_table" in migration.pending_migrations
        assert len(migration.failed_migrations) == 1
        assert "003_broken_migration" in migration.failed_migrations
        assert migration.auto_run is False
        
    def test_migration_status_optional_fields(self):
        """Test MigrationStatus model with None optional fields."""
        migration = MigrationStatus(
            last_run=None,
            current_version=None,
            auto_run=True
        )
        
        assert migration.last_run is None
        assert migration.current_version is None
        assert migration.pending_migrations == []
        assert migration.failed_migrations == []
        assert migration.auto_run is True


class TestServiceConfigModel(BaseTestCase):
    """Test ServiceConfig Pydantic model validation."""
    
    def test_service_config_creation_defaults(self):
        """Test ServiceConfig model creation with defaults."""
        config = ServiceConfig()
        
        assert config.hash is None
        assert config.last_validated is None
        assert config.validation_errors == []
        
    def test_service_config_with_data(self):
        """Test ServiceConfig model with complete data."""
        validated_time = datetime.now(timezone.utc)
        config = ServiceConfig(
            hash="sha256:abc123def456",
            last_validated=validated_time,
            validation_errors=["Missing required field: DATABASE_URL", "Invalid port range"]
        )
        
        assert config.hash == "sha256:abc123def456"
        assert config.last_validated == validated_time
        assert len(config.validation_errors) == 2
        assert "Missing required field: DATABASE_URL" in config.validation_errors
        
    def test_service_config_empty_validation_errors(self):
        """Test ServiceConfig with empty validation errors (successful validation)."""
        config = ServiceConfig(
            hash="sha256:valid_hash",
            last_validated=datetime.now(timezone.utc),
            validation_errors=[]
        )
        
        assert config.hash == "sha256:valid_hash"
        assert config.validation_errors == []


class TestCrashEntryModel(BaseTestCase):
    """Test CrashEntry Pydantic model validation."""
    
    def test_crash_entry_creation_minimal(self):
        """Test CrashEntry model creation with minimal required data."""
        timestamp = datetime.now(timezone.utc)
        crash = CrashEntry(
            service=ServiceType.BACKEND,
            timestamp=timestamp,
            error="NoneType object has no attribute 'execute'"
        )
        
        assert crash.service == ServiceType.BACKEND
        assert crash.timestamp == timestamp
        assert crash.error == "NoneType object has no attribute 'execute'"
        assert crash.stack_trace is None
        assert crash.recovery_attempted is False
        assert crash.recovery_success is False
        
    def test_crash_entry_creation_complete(self):
        """Test CrashEntry model creation with all fields."""
        timestamp = datetime.now(timezone.utc)
        stack_trace = """Traceback (most recent call last):
  File "agent.py", line 42, in execute
    result = manager.execute()
AttributeError: 'NoneType' object has no attribute 'execute'"""
        
        crash = CrashEntry(
            service=ServiceType.FRONTEND,
            timestamp=timestamp,
            error="LLM manager not initialized",
            stack_trace=stack_trace,
            recovery_attempted=True,
            recovery_success=False
        )
        
        assert crash.service == ServiceType.FRONTEND
        assert crash.timestamp == timestamp
        assert crash.error == "LLM manager not initialized"
        assert crash.stack_trace == stack_trace
        assert crash.recovery_attempted is True
        assert crash.recovery_success is False
        
    def test_crash_entry_service_type_validation(self):
        """Test CrashEntry service field validates ServiceType enum."""
        # Valid ServiceType
        crash = CrashEntry(
            service=ServiceType.BACKEND,
            timestamp=datetime.now(timezone.utc),
            error="Test error"
        )
        assert crash.service == ServiceType.BACKEND
        
        # Invalid service type should raise ValidationError
        with pytest.raises(ValidationError):
            CrashEntry(
                service="invalid_service",  # Not a valid ServiceType
                timestamp=datetime.now(timezone.utc),
                error="Test error"
            )


class TestHealthCheckHistoryModel(BaseTestCase):
    """Test HealthCheckHistory Pydantic model validation."""
    
    def test_health_check_history_creation_defaults(self):
        """Test HealthCheckHistory model creation with defaults."""
        history = HealthCheckHistory()
        
        assert history.consecutive_failures == {}
        assert history.last_healthy == {}
        
    def test_health_check_history_with_data(self):
        """Test HealthCheckHistory model with service data."""
        last_healthy_time = datetime.now(timezone.utc)
        history = HealthCheckHistory(
            consecutive_failures={"database": 3, "redis": 0, "clickhouse": 5},
            last_healthy={
                "database": last_healthy_time,
                "redis": last_healthy_time,
                "clickhouse": None
            }
        )
        
        assert history.consecutive_failures["database"] == 3
        assert history.consecutive_failures["redis"] == 0
        assert history.consecutive_failures["clickhouse"] == 5
        assert history.last_healthy["database"] == last_healthy_time
        assert history.last_healthy["redis"] == last_healthy_time
        assert history.last_healthy["clickhouse"] is None
        
    def test_health_check_history_mixed_types(self):
        """Test HealthCheckHistory handles mixed data types correctly."""
        history = HealthCheckHistory(
            consecutive_failures={"service1": 0, "service2": 10},
            last_healthy={"service1": datetime.now(timezone.utc), "service2": None}
        )
        
        assert isinstance(history.consecutive_failures["service1"], int)
        assert isinstance(history.consecutive_failures["service2"], int)
        assert isinstance(history.last_healthy["service1"], datetime)
        assert history.last_healthy["service2"] is None


class TestStartupStatusModel(BaseTestCase):
    """Test StartupStatus main SSOT model validation."""
    
    def test_startup_status_creation_defaults(self):
        """Test StartupStatus model creation with all defaults."""
        status = StartupStatus()
        
        assert status.last_startup is None
        assert isinstance(status.migration_status, MigrationStatus)
        assert isinstance(status.service_config, ServiceConfig)
        assert status.crash_history == []
        assert isinstance(status.health_check_history, HealthCheckHistory)
        
    def test_startup_status_creation_complete(self):
        """Test StartupStatus model creation with complete data."""
        last_startup = LastStartup(
            timestamp=datetime.now(timezone.utc),
            success=True,
            duration_ms=2000,
            environment=Environment.PROD
        )
        
        migration = MigrationStatus(current_version="v3.0.0")
        config = ServiceConfig(hash="sha256:prod_config")
        
        crash1 = CrashEntry(
            service=ServiceType.BACKEND,
            timestamp=datetime.now(timezone.utc),
            error="Connection timeout"
        )
        
        health_history = HealthCheckHistory(
            consecutive_failures={"database": 0},
            last_healthy={"database": datetime.now(timezone.utc)}
        )
        
        status = StartupStatus(
            last_startup=last_startup,
            migration_status=migration,
            service_config=config,
            crash_history=[crash1],
            health_check_history=health_history
        )
        
        assert status.last_startup == last_startup
        assert status.migration_status == migration
        assert status.service_config == config
        assert len(status.crash_history) == 1
        assert status.crash_history[0] == crash1
        assert status.health_check_history == health_history
        
    def test_startup_status_crash_history_limit_validator(self):
        """Test StartupStatus crash_history validator limits to 50 entries."""
        # Create 60 crash entries
        crashes = []
        for i in range(60):
            crashes.append(CrashEntry(
                service=ServiceType.BACKEND,
                timestamp=datetime.now(timezone.utc),
                error=f"Error {i}"
            ))
        
        status = StartupStatus(crash_history=crashes)
        
        # Should be limited to last 50 entries
        assert len(status.crash_history) == 50
        # Should keep the last 50 entries (10-59)
        assert status.crash_history[0].error == "Error 10"
        assert status.crash_history[49].error == "Error 59"
        
    def test_startup_status_crash_history_under_limit(self):
        """Test StartupStatus crash_history validator with under 50 entries."""
        # Create 25 crash entries
        crashes = []
        for i in range(25):
            crashes.append(CrashEntry(
                service=ServiceType.FRONTEND,
                timestamp=datetime.now(timezone.utc),
                error=f"Frontend Error {i}"
            ))
        
        status = StartupStatus(crash_history=crashes)
        
        # Should keep all 25 entries
        assert len(status.crash_history) == 25
        assert status.crash_history[0].error == "Frontend Error 0"
        assert status.crash_history[24].error == "Frontend Error 24"
        
    def test_startup_status_crash_history_exactly_50(self):
        """Test StartupStatus crash_history validator with exactly 50 entries."""
        # Create exactly 50 crash entries
        crashes = []
        for i in range(50):
            crashes.append(CrashEntry(
                service=ServiceType.BACKEND,
                timestamp=datetime.now(timezone.utc),
                error=f"Exact Error {i}"
            ))
        
        status = StartupStatus(crash_history=crashes)
        
        # Should keep all 50 entries
        assert len(status.crash_history) == 50
        assert status.crash_history[0].error == "Exact Error 0"
        assert status.crash_history[49].error == "Exact Error 49"


class TestStartupEventModel(BaseTestCase):
    """Test StartupEvent Pydantic model validation."""
    
    def test_startup_event_creation_minimal(self):
        """Test StartupEvent model creation with minimal data."""
        timestamp = datetime.now(timezone.utc)
        event = StartupEvent(
            event_type="service_initialized",
            timestamp=timestamp,
            success=True
        )
        
        assert event.event_type == "service_initialized"
        assert event.timestamp == timestamp
        assert event.success is True
        assert event.message is None
        assert event.context == {}
        
    def test_startup_event_creation_complete(self):
        """Test StartupEvent model creation with complete data."""
        timestamp = datetime.now(timezone.utc)
        context = {"service": "database", "duration_ms": 1500, "retry_count": 2}
        
        event = StartupEvent(
            event_type="health_check_completed",
            timestamp=timestamp,
            success=False,
            message="Database connection timeout after 3 retries",
            context=context
        )
        
        assert event.event_type == "health_check_completed"
        assert event.timestamp == timestamp
        assert event.success is False
        assert event.message == "Database connection timeout after 3 retries"
        assert event.context == context
        assert event.context["service"] == "database"
        assert event.context["retry_count"] == 2
        
    def test_startup_event_context_default(self):
        """Test StartupEvent context field defaults to empty dict."""
        event = StartupEvent(
            event_type="test_event",
            timestamp=datetime.now(timezone.utc),
            success=True
        )
        
        assert event.context == {}
        assert isinstance(event.context, dict)


class TestErrorPhaseEnum(BaseTestCase):
    """Test ErrorPhase enum values and validation."""
    
    def test_error_phase_values(self):
        """Test all ErrorPhase enum values are correct."""
        assert ErrorPhase.STARTUP == "startup"
        assert ErrorPhase.RUNTIME == "runtime"
        assert ErrorPhase.SHUTDOWN == "shutdown"
        
    def test_error_phase_string_conversion(self):
        """Test ErrorPhase can be created from strings."""
        assert ErrorPhase("startup") == ErrorPhase.STARTUP
        assert ErrorPhase("runtime") == ErrorPhase.RUNTIME
        assert ErrorPhase("shutdown") == ErrorPhase.SHUTDOWN
        
    def test_error_phase_invalid_value_raises_error(self):
        """Test invalid ErrorPhase values raise ValidationError."""
        with pytest.raises(ValueError):
            ErrorPhase("initialization")  # Should be "startup"
        with pytest.raises(ValueError):
            ErrorPhase("execution")  # Should be "runtime"


class TestErrorTypeEnum(BaseTestCase):
    """Test ErrorType enum values and validation."""
    
    def test_error_type_values(self):
        """Test all ErrorType enum values are correct."""
        assert ErrorType.CONNECTION == "connection"
        assert ErrorType.CONFIGURATION == "configuration"
        assert ErrorType.DEPENDENCY == "dependency"
        assert ErrorType.MIGRATION == "migration"
        assert ErrorType.TIMEOUT == "timeout"
        assert ErrorType.PERMISSION == "permission"
        assert ErrorType.RESOURCE == "resource"
        assert ErrorType.OTHER == "other"
        
    def test_error_type_string_conversion(self):
        """Test ErrorType can be created from strings."""
        assert ErrorType("connection") == ErrorType.CONNECTION
        assert ErrorType("configuration") == ErrorType.CONFIGURATION
        assert ErrorType("dependency") == ErrorType.DEPENDENCY
        assert ErrorType("migration") == ErrorType.MIGRATION
        assert ErrorType("timeout") == ErrorType.TIMEOUT
        assert ErrorType("permission") == ErrorType.PERMISSION
        assert ErrorType("resource") == ErrorType.RESOURCE
        assert ErrorType("other") == ErrorType.OTHER
        
    def test_error_type_invalid_value_raises_error(self):
        """Test invalid ErrorType values raise ValidationError."""
        with pytest.raises(ValueError):
            ErrorType("network")  # Should be "connection"
        with pytest.raises(ValueError):
            ErrorType("auth")  # Should be "permission"


class TestStartupErrorModel(BaseTestCase):
    """Test StartupError Pydantic model validation."""
    
    def test_startup_error_creation_minimal(self):
        """Test StartupError model creation with minimal required data."""
        timestamp = datetime.now(timezone.utc)
        error = StartupError(
            timestamp=timestamp,
            service="backend",
            phase=ErrorPhase.STARTUP,
            severity="error",
            error_type=ErrorType.CONNECTION,
            message="Database connection failed"
        )
        
        assert error.id is None
        assert error.timestamp == timestamp
        assert error.service == "backend"
        assert error.phase == ErrorPhase.STARTUP
        assert error.severity == "error"
        assert error.error_type == ErrorType.CONNECTION
        assert error.message == "Database connection failed"
        assert error.stack_trace is None
        assert error.context == {}
        assert error.resolved is False
        assert error.resolution is None
        
    def test_startup_error_creation_complete(self):
        """Test StartupError model creation with complete data."""
        timestamp = datetime.now(timezone.utc)
        stack_trace = "Traceback: Connection refused"
        context = {"host": "localhost", "port": 5432, "database": "netra"}
        
        error = StartupError(
            id=123,
            timestamp=timestamp,
            service="database",
            phase=ErrorPhase.RUNTIME,
            severity="critical",
            error_type=ErrorType.TIMEOUT,
            message="Query timeout after 30 seconds",
            stack_trace=stack_trace,
            context=context,
            resolved=True,
            resolution="Increased timeout to 60 seconds"
        )
        
        assert error.id == 123
        assert error.timestamp == timestamp
        assert error.service == "database"
        assert error.phase == ErrorPhase.RUNTIME
        assert error.severity == "critical"
        assert error.error_type == ErrorType.TIMEOUT
        assert error.message == "Query timeout after 30 seconds"
        assert error.stack_trace == stack_trace
        assert error.context == context
        assert error.context["port"] == 5432
        assert error.resolved is True
        assert error.resolution == "Increased timeout to 60 seconds"


class TestErrorPatternModel(BaseTestCase):
    """Test ErrorPattern Pydantic model validation."""
    
    def test_error_pattern_creation_minimal(self):
        """Test ErrorPattern model creation with minimal required data."""
        last_seen = datetime.now(timezone.utc)
        pattern = ErrorPattern(
            pattern="NoneType.*attribute.*execute",
            last_seen=last_seen
        )
        
        assert pattern.pattern_id is None
        assert pattern.pattern == "NoneType.*attribute.*execute"
        assert pattern.frequency == 1  # Default value
        assert pattern.last_seen == last_seen
        assert pattern.suggested_fix is None
        assert pattern.auto_fixable is False
        
    def test_error_pattern_creation_complete(self):
        """Test ErrorPattern model creation with complete data."""
        last_seen = datetime.now(timezone.utc)
        pattern = ErrorPattern(
            pattern_id=456,
            pattern="ConnectionError.*Redis.*timeout",
            frequency=15,
            last_seen=last_seen,
            suggested_fix="Increase Redis connection timeout",
            auto_fixable=True
        )
        
        assert pattern.pattern_id == 456
        assert pattern.pattern == "ConnectionError.*Redis.*timeout"
        assert pattern.frequency == 15
        assert pattern.last_seen == last_seen
        assert pattern.suggested_fix == "Increase Redis connection timeout"
        assert pattern.auto_fixable is True
        
    def test_error_pattern_frequency_validation(self):
        """Test ErrorPattern frequency field validation (must be >= 1)."""
        # Valid frequency
        pattern = ErrorPattern(
            pattern="test_pattern",
            frequency=1,
            last_seen=datetime.now(timezone.utc)
        )
        assert pattern.frequency == 1
        
        # Test edge case
        pattern = ErrorPattern(
            pattern="test_pattern",
            frequency=100,
            last_seen=datetime.now(timezone.utc)
        )
        assert pattern.frequency == 100
        
        # Invalid frequency (0 or negative)
        with pytest.raises(ValidationError) as excinfo:
            ErrorPattern(
                pattern="test_pattern",
                frequency=0,
                last_seen=datetime.now(timezone.utc)
            )
        assert "greater than or equal to 1" in str(excinfo.value)


class TestErrorTrendModel(BaseTestCase):
    """Test ErrorTrend Pydantic model validation."""
    
    def test_error_trend_creation_minimal(self):
        """Test ErrorTrend model creation with minimal required data."""
        trend = ErrorTrend(
            period="daily",
            total_errors=45
        )
        
        assert trend.period == "daily"
        assert trend.total_errors == 45
        assert trend.error_types == {}
        assert trend.services == {}
        assert trend.severity_breakdown == {}
        assert trend.patterns == []
        
    def test_error_trend_creation_complete(self):
        """Test ErrorTrend model creation with complete data."""
        pattern1 = ErrorPattern(
            pattern="Connection.*failed",
            frequency=10,
            last_seen=datetime.now(timezone.utc)
        )
        
        pattern2 = ErrorPattern(
            pattern="Timeout.*Redis",
            frequency=5,
            last_seen=datetime.now(timezone.utc)
        )
        
        trend = ErrorTrend(
            period="weekly",
            total_errors=250,
            error_types={
                "connection": 150,
                "timeout": 75,
                "configuration": 25
            },
            services={
                "backend": 200,
                "frontend": 30,
                "database": 20
            },
            severity_breakdown={
                "critical": 10,
                "error": 40,
                "warning": 200
            },
            patterns=[pattern1, pattern2]
        )
        
        assert trend.period == "weekly"
        assert trend.total_errors == 250
        assert trend.error_types["connection"] == 150
        assert trend.error_types["timeout"] == 75
        assert trend.services["backend"] == 200
        assert trend.services["frontend"] == 30
        assert trend.severity_breakdown["critical"] == 10
        assert trend.severity_breakdown["warning"] == 200
        assert len(trend.patterns) == 2
        assert trend.patterns[0].pattern == "Connection.*failed"
        assert trend.patterns[1].frequency == 5


class TestModelSerialization(BaseTestCase):
    """Test serialization and deserialization of all models."""
    
    def test_startup_status_model_dict_serialization(self):
        """Test StartupStatus model can be serialized to dict."""
        last_startup = LastStartup(
            timestamp=datetime.now(timezone.utc),
            success=True,
            duration_ms=1000,
            environment=Environment.TEST
        )
        
        status = StartupStatus(last_startup=last_startup)
        
        # Test model_dump (Pydantic v2)
        data_dict = status.model_dump()
        
        assert isinstance(data_dict, dict)
        assert "last_startup" in data_dict
        assert "migration_status" in data_dict
        assert "service_config" in data_dict
        assert "crash_history" in data_dict
        assert "health_check_history" in data_dict
        
        # Test nested model serialization
        assert data_dict["last_startup"]["success"] is True
        assert data_dict["last_startup"]["duration_ms"] == 1000
        assert data_dict["last_startup"]["environment"] == "test"
        
    def test_crash_entry_json_serialization(self):
        """Test CrashEntry model JSON serialization."""
        timestamp = datetime.now(timezone.utc)
        crash = CrashEntry(
            service=ServiceType.BACKEND,
            timestamp=timestamp,
            error="Test error message",
            recovery_attempted=True
        )
        
        # Test JSON serialization
        json_str = crash.model_dump_json()
        assert isinstance(json_str, str)
        assert "backend" in json_str
        assert "Test error message" in json_str
        assert "true" in json_str  # recovery_attempted
        
    def test_error_pattern_round_trip_serialization(self):
        """Test ErrorPattern model round-trip serialization."""
        original_timestamp = datetime.now(timezone.utc)
        original_pattern = ErrorPattern(
            pattern_id=789,
            pattern="Test.*Pattern",
            frequency=20,
            last_seen=original_timestamp,
            suggested_fix="Test fix",
            auto_fixable=True
        )
        
        # Serialize to dict
        data_dict = original_pattern.model_dump()
        
        # Deserialize from dict
        reconstructed_pattern = ErrorPattern(**data_dict)
        
        # Verify round-trip integrity
        assert reconstructed_pattern.pattern_id == original_pattern.pattern_id
        assert reconstructed_pattern.pattern == original_pattern.pattern
        assert reconstructed_pattern.frequency == original_pattern.frequency
        assert reconstructed_pattern.last_seen == original_pattern.last_seen
        assert reconstructed_pattern.suggested_fix == original_pattern.suggested_fix
        assert reconstructed_pattern.auto_fixable == original_pattern.auto_fixable


class TestFieldConstraintsAndEdgeCases(BaseTestCase):
    """Test field constraints and edge cases across all models."""
    
    def test_empty_list_fields_behavior(self):
        """Test behavior of list fields when empty."""
        # LastStartup with empty errors/warnings
        startup = LastStartup(
            timestamp=datetime.now(timezone.utc),
            success=True,
            duration_ms=100,
            environment=Environment.DEV,
            errors=[],
            warnings=[]
        )
        
        assert startup.errors == []
        assert startup.warnings == []
        assert len(startup.errors) == 0
        assert len(startup.warnings) == 0
        
        # StartupStatus with empty crash_history
        status = StartupStatus(crash_history=[])
        assert status.crash_history == []
        assert len(status.crash_history) == 0
        
    def test_none_values_for_optional_fields(self):
        """Test None values for optional fields."""
        # MigrationStatus with all None optionals
        migration = MigrationStatus(
            last_run=None,
            current_version=None,
            pending_migrations=[],
            failed_migrations=[],
            auto_run=True
        )
        
        assert migration.last_run is None
        assert migration.current_version is None
        
        # ServiceConfig with None optionals
        config = ServiceConfig(
            hash=None,
            last_validated=None,
            validation_errors=[]
        )
        
        assert config.hash is None
        assert config.last_validated is None
        
    def test_datetime_timezone_handling(self):
        """Test datetime fields handle timezone correctly."""
        # UTC timezone
        utc_time = datetime.now(timezone.utc)
        startup = LastStartup(
            timestamp=utc_time,
            success=True,
            duration_ms=500,
            environment=Environment.STAGING
        )
        
        assert startup.timestamp.tzinfo == timezone.utc
        
        # Test that model preserves timezone info
        serialized = startup.model_dump()
        reconstructed = LastStartup(**serialized)
        assert reconstructed.timestamp.tzinfo == timezone.utc
        
    def test_large_data_handling(self):
        """Test models handle large data appropriately."""
        # Large error message
        large_error = "Error: " + "x" * 10000  # 10KB error message
        crash = CrashEntry(
            service=ServiceType.FRONTEND,
            timestamp=datetime.now(timezone.utc),
            error=large_error
        )
        
        assert len(crash.error) == len(large_error)
        assert crash.error == large_error
        
        # Large context dictionary
        large_context = {f"key_{i}": f"value_{i}" for i in range(1000)}
        event = StartupEvent(
            event_type="large_context_test",
            timestamp=datetime.now(timezone.utc),
            success=True,
            context=large_context
        )
        
        assert len(event.context) == 1000
        assert event.context["key_999"] == "value_999"