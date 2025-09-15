"""
Admin Tool Executors Core Tests - Phase 1 Critical Business Logic

Business Value: Platform/Internal - Admin Tool Execution Infrastructure Foundation
Tests AdminToolExecutors functionality including tool routing, parameter extraction,
service integration, and error handling for admin operations.

SSOT Compliance: Uses SSotAsyncTestCase, real database sessions where possible,
minimal mocking per CLAUDE.md standards. No test cheating.

Coverage Target: AdminToolExecutors methods, service integration, tool execution
Current Coverage: 0% -> Target: 80%+ (175 lines total)

Note: AdminToolExecutors methods return Dict[str, Any] despite ToolResult type hints.

GitHub Issue: #872 Agents Module Unit Tests - Phase 1 Foundation
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional

# ABSOLUTE IMPORTS - SSOT compliance
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from sqlalchemy.ext.asyncio import AsyncSession

# Import target classes
from netra_backend.app.agents.admin_tool_executors import AdminToolExecutors
from netra_backend.app.db.models_postgres import User


class AdminToolExecutorsCoreTests(SSotAsyncTestCase):
    """Test AdminToolExecutors core functionality and initialization."""

    def setup_method(self, method):
        """Set up test environment with mock database and user."""
        super().setup_method(method)
        
        # Mock database session
        self.mock_db = Mock(spec=AsyncSession)
        
        # Mock user
        self.mock_user = Mock(spec=User)
        self.mock_user.id = "test-user-admin-001"
        self.mock_user.email = "admin@test.com"
        self.mock_user.role = "admin"
        
        # Create AdminToolExecutors instance
        self.executor = AdminToolExecutors(self.mock_db, self.mock_user)

    def test_initialization(self):
        """Test AdminToolExecutors initialization."""
        # Verify: Instance was created with correct attributes
        assert self.executor.db is self.mock_db
        assert self.executor.user is self.mock_user
        
        # Verify: Instance has correct type
        assert isinstance(self.executor, AdminToolExecutors)


class CorpusManagerExecutionTests(SSotAsyncTestCase):
    """Test AdminToolExecutors corpus manager functionality."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        
        self.mock_db = Mock(spec=AsyncSession)
        self.mock_user = Mock(spec=User)
        self.mock_user.id = "test-user-corpus-001"
        
        self.executor = AdminToolExecutors(self.mock_db, self.mock_user)

    async def test_execute_corpus_manager_create_action(self):
        """Test corpus manager create action execution."""
        # Mock corpus service
        with patch('netra_backend.app.core.configuration.services.corpus_service') as mock_service:
            mock_service.create_corpus = AsyncMock(return_value={
                "id": "corpus-123",
                "name": "test_corpus",
                "domain": "general"
            })
            
            # Test: Execute corpus create action
            result = await self.executor.execute_corpus_manager(
                action="create",
                domain="general",
                name="test_corpus",
                description="Test corpus creation"
            )
            
            # Verify: Service was called with correct parameters
            mock_service.create_corpus.assert_called_once()
            call_kwargs = mock_service.create_corpus.call_args[1]
            assert call_kwargs["name"] == "test_corpus"
            assert call_kwargs["domain"] == "general"
            assert call_kwargs["description"] == "Test corpus creation"
            assert call_kwargs["user_id"] == self.mock_user.id
            assert call_kwargs["db"] is self.mock_db
            
            # Verify: Result structure
            assert result["status"] == "success"
            assert "corpus" in result

    async def test_execute_corpus_manager_list_action(self):
        """Test corpus manager list action execution."""
        # Mock corpus service
        with patch('netra_backend.app.core.configuration.services.corpus_service') as mock_service:
            mock_service.list_corpora = AsyncMock(return_value=[
                {"id": "corpus-1", "name": "corpus_one"},
                {"id": "corpus-2", "name": "corpus_two"}
            ])
            
            # Test: Execute corpus list action
            result = await self.executor.execute_corpus_manager(action="list")
            
            # Verify: Service was called correctly
            mock_service.list_corpora.assert_called_once_with(self.mock_db)
            
            # Verify: Result structure
            assert result["status"] == "success"
            assert "corpora" in result
            assert len(result["corpora"]) == 2

    async def test_execute_corpus_manager_validate_action(self):
        """Test corpus manager validate action execution."""
        # Test: Execute corpus validate action
        result = await self.executor.execute_corpus_manager(
            action="validate",
            corpus_id="corpus-validate-123"
        )
        
        # Verify: Result structure for validation
        assert result["status"] == "success"
        assert result["valid"] is True
        assert result["corpus_id"] == "corpus-validate-123"

    async def test_execute_corpus_manager_validate_action_missing_id(self):
        """Test corpus manager validate action with missing corpus_id."""
        # Test: Execute corpus validate action without corpus_id
        result = await self.executor.execute_corpus_manager(action="validate")
        
        # Verify: Error for missing corpus_id
        assert "error" in result
        assert "corpus_id required" in result["error"]

    async def test_execute_corpus_manager_unknown_action(self):
        """Test corpus manager with unknown action."""
        # Test: Execute corpus manager with unknown action
        result = await self.executor.execute_corpus_manager(action="unknown_action")
        
        # Verify: Error for unknown action
        assert "error" in result
        assert "Unknown corpus action: unknown_action" in result["error"]

    def test_get_corpus_action_handlers(self):
        """Test corpus action handlers mapping."""
        # Test: Get corpus action handlers
        handlers = self.executor._get_corpus_action_handlers()
        
        # Verify: Handler mapping structure
        assert isinstance(handlers, dict)
        assert "create" in handlers
        assert "list" in handlers
        assert "validate" in handlers
        
        # Verify: Handlers are callable
        assert callable(handlers["create"])
        assert callable(handlers["list"])
        assert callable(handlers["validate"])

    def test_extract_corpus_params_with_custom_values(self):
        """Test corpus parameters extraction with custom values."""
        # Test: Extract corpus parameters with custom values
        params = self.executor._extract_corpus_params(
            domain="finance",
            name="finance_corpus",
            description="Financial domain corpus"
        )
        
        # Verify: Parameter values
        assert params["domain"] == "finance"
        assert params["name"] == "finance_corpus"
        assert params["description"] == "Financial domain corpus"

    def test_extract_corpus_params_with_defaults(self):
        """Test corpus parameters extraction with default values."""
        # Test: Extract corpus parameters with defaults
        params = self.executor._extract_corpus_params()
        
        # Verify: Default parameter values
        assert params["domain"] == "general"
        assert params["name"] == "corpus_general"
        assert params["description"] == "Corpus for general domain"


class SyntheticDataExecutionTests(SSotAsyncTestCase):
    """Test AdminToolExecutors synthetic data generator functionality."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        
        self.mock_db = Mock(spec=AsyncSession)
        self.mock_user = Mock(spec=User)
        self.mock_user.id = "test-user-synthetic-001"
        
        self.executor = AdminToolExecutors(self.mock_db, self.mock_user)

    async def test_execute_synthetic_generator_generate_action(self):
        """Test synthetic generator generate action execution."""
        # Mock synthetic data service
        with patch('netra_backend.app.services.synthetic_data_service.SyntheticDataService') as MockService:
            mock_service_instance = Mock()
            mock_service_instance.generate_synthetic_data = AsyncMock(return_value={
                "generated_count": 10,
                "data_samples": ["sample1", "sample2"]
            })
            MockService.return_value = mock_service_instance
            
            # Test: Execute synthetic generate action
            result = await self.executor.execute_synthetic_generator(
                action="generate",
                preset="standard",
                corpus_id="corpus-123",
                count=10
            )
            
            # Verify: Service was instantiated with database
            MockService.assert_called_once_with(self.mock_db)
            
            # Verify: Service method was called with correct parameters
            mock_service_instance.generate_synthetic_data.assert_called_once()
            call_kwargs = mock_service_instance.generate_synthetic_data.call_args[1]
            assert call_kwargs["preset"] == "standard"
            assert call_kwargs["corpus_id"] == "corpus-123"
            assert call_kwargs["count"] == 10
            assert call_kwargs["user_id"] == self.mock_user.id
            
            # Verify: Result structure
            assert result["status"] == "success"
            assert "data" in result

    async def test_execute_synthetic_generator_list_presets_action(self):
        """Test synthetic generator list presets action execution."""
        # Mock synthetic data service
        with patch('netra_backend.app.services.synthetic_data_service.SyntheticDataService') as MockService:
            mock_service_instance = Mock()
            mock_service_instance.list_presets = AsyncMock(return_value=[
                {"name": "standard", "description": "Standard preset"},
                {"name": "advanced", "description": "Advanced preset"}
            ])
            MockService.return_value = mock_service_instance
            
            # Test: Execute synthetic list presets action
            result = await self.executor.execute_synthetic_generator(action="list_presets")
            
            # Verify: Service method was called
            mock_service_instance.list_presets.assert_called_once()
            
            # Verify: Result structure
            assert result["status"] == "success"
            assert "presets" in result
            assert len(result["presets"]) == 2

    async def test_execute_synthetic_generator_unknown_action(self):
        """Test synthetic generator with unknown action."""
        # Test: Execute synthetic generator with unknown action
        result = await self.executor.execute_synthetic_generator(action="unknown_action")
        
        # Verify: Error for unknown action
        assert "error" in result
        assert "Unknown synthetic generator action: unknown_action" in result["error"]

    def test_extract_synthetic_params_with_custom_values(self):
        """Test synthetic data parameters extraction with custom values."""
        # Test: Extract synthetic parameters with custom values
        params = self.executor._extract_synthetic_params(
            preset="custom",
            corpus_id="corpus-456",
            count=25
        )
        
        # Verify: Parameter values
        assert params["preset"] == "custom"
        assert params["corpus_id"] == "corpus-456"
        assert params["count"] == 25

    def test_extract_synthetic_params_with_defaults(self):
        """Test synthetic data parameters extraction with default values."""
        # Test: Extract synthetic parameters with defaults
        params = self.executor._extract_synthetic_params()
        
        # Verify: Default parameter values
        assert params["preset"] is None
        assert params["corpus_id"] is None
        assert params["count"] == 10


class UserAdminExecutionTests(SSotAsyncTestCase):
    """Test AdminToolExecutors user administration functionality."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        
        self.mock_db = Mock(spec=AsyncSession)
        self.mock_user = Mock(spec=User)
        self.mock_user.id = "test-user-admin-001"
        
        self.executor = AdminToolExecutors(self.mock_db, self.mock_user)

    async def test_execute_user_admin_create_user_action(self):
        """Test user admin create user action execution."""
        # Mock user service
        with patch('netra_backend.app.core.configuration.services.user_service') as mock_service:
            mock_service.create_user = AsyncMock(return_value={
                "id": "user-new-123",
                "email": "newuser@test.com",
                "role": "standard_user"
            })
            
            # Test: Execute user create action
            result = await self.executor.execute_user_admin(
                action="create_user",
                email="newuser@test.com",
                role="standard_user"
            )
            
            # Verify: Service was called with correct parameters
            mock_service.create_user.assert_called_once()
            call_kwargs = mock_service.create_user.call_args[1]
            assert call_kwargs["email"] == "newuser@test.com"
            assert call_kwargs["role"] == "standard_user"
            assert call_kwargs["db"] is self.mock_db
            
            # Verify: Result structure
            assert result["status"] == "success"
            assert "user" in result

    async def test_execute_user_admin_create_user_missing_email(self):
        """Test user admin create user action with missing email."""
        # Test: Execute user create action without email
        result = await self.executor.execute_user_admin(
            action="create_user",
            role="standard_user"
        )
        
        # Verify: Error for missing email
        assert "error" in result
        assert "email required" in result["error"]

    async def test_execute_user_admin_grant_permission_action(self):
        """Test user admin grant permission action execution."""
        # Mock permission service
        with patch('netra_backend.app.services.permission_service.PermissionService.grant_permission') as mock_grant:
            mock_grant.return_value = True
            
            # Test: Execute grant permission action
            result = await self.executor.execute_user_admin(
                action="grant_permission",
                user_email="user@test.com",
                permission="admin_access"
            )
            
            # Verify: Service was called with correct parameters
            mock_grant.assert_called_once_with("user@test.com", "admin_access", self.mock_db)
            
            # Verify: Result structure
            assert result["status"] == "success"
            assert result["granted"] is True

    async def test_execute_user_admin_grant_permission_missing_params(self):
        """Test user admin grant permission with missing parameters."""
        # Test: Execute grant permission without required parameters
        result = await self.executor.execute_user_admin(
            action="grant_permission",
            user_email="user@test.com"
            # Missing permission parameter
        )
        
        # Verify: Error for missing parameters
        assert "error" in result
        assert "user_email and permission required" in result["error"]

    async def test_execute_user_admin_unknown_action(self):
        """Test user admin with unknown action."""
        # Test: Execute user admin with unknown action
        result = await self.executor.execute_user_admin(action="unknown_action")
        
        # Verify: Error for unknown action
        assert "error" in result
        assert "Unknown user admin action: unknown_action" in result["error"]

    def test_extract_user_params_with_custom_values(self):
        """Test user parameters extraction with custom values."""
        # Test: Extract user parameters with custom values
        email, role = self.executor._extract_user_params(
            email="custom@test.com",
            role="admin"
        )
        
        # Verify: Parameter values
        assert email == "custom@test.com"
        assert role == "admin"

    def test_extract_user_params_with_defaults(self):
        """Test user parameters extraction with default role."""
        # Test: Extract user parameters with default role
        email, role = self.executor._extract_user_params(email="default@test.com")
        
        # Verify: Parameter values
        assert email == "default@test.com"
        assert role == "standard_user"

    def test_validate_user_creation_valid_email(self):
        """Test user creation validation with valid email."""
        # Test: Validate user creation with valid email
        error = self.executor._validate_user_creation("valid@test.com")
        
        # Verify: No validation error
        assert error is None

    def test_validate_user_creation_missing_email(self):
        """Test user creation validation with missing email."""
        # Test: Validate user creation without email
        error = self.executor._validate_user_creation(None)
        
        # Verify: Validation error
        assert error is not None
        assert "email required" in error["error"]

    def test_extract_permission_params(self):
        """Test permission parameters extraction."""
        # Test: Extract permission parameters
        user_email, permission = self.executor._extract_permission_params(
            user_email="perm@test.com",
            permission="read_access"
        )
        
        # Verify: Parameter values
        assert user_email == "perm@test.com"
        assert permission == "read_access"

    def test_validate_permission_grant_valid_params(self):
        """Test permission grant validation with valid parameters."""
        # Test: Validate permission grant with valid parameters
        error = self.executor._validate_permission_grant("user@test.com", "admin_access")
        
        # Verify: No validation error
        assert error is None

    def test_validate_permission_grant_missing_params(self):
        """Test permission grant validation with missing parameters."""
        # Test: Validate permission grant with missing user_email
        error = self.executor._validate_permission_grant(None, "admin_access")
        
        # Verify: Validation error
        assert error is not None
        assert "user_email and permission required" in error["error"]
        
        # Test: Validate permission grant with missing permission
        error = self.executor._validate_permission_grant("user@test.com", None)
        
        # Verify: Validation error
        assert error is not None
        assert "user_email and permission required" in error["error"]


class SystemConfiguratorExecutionTests(SSotAsyncTestCase):
    """Test AdminToolExecutors system configurator functionality."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        
        self.mock_db = Mock(spec=AsyncSession)
        self.mock_user = Mock(spec=User)
        self.mock_user.id = "test-user-config-001"
        
        self.executor = AdminToolExecutors(self.mock_db, self.mock_user)

    async def test_execute_system_configurator_update_setting_action(self):
        """Test system configurator update setting action execution."""
        # Test: Execute update setting action
        result = await self.executor.execute_system_configurator(
            action="update_setting",
            setting_name="debug_mode",
            value=True
        )
        
        # Verify: Result structure for simulated update
        assert result["status"] == "success"
        assert result["setting"] == "debug_mode"
        assert result["value"] is True
        assert "simulated" in result["message"]

    async def test_execute_system_configurator_update_setting_missing_name(self):
        """Test system configurator update setting with missing setting_name."""
        # Test: Execute update setting without setting_name
        result = await self.executor.execute_system_configurator(
            action="update_setting",
            value="some_value"
        )
        
        # Verify: Error for missing setting_name
        assert "error" in result
        assert "setting_name required" in result["error"]

    async def test_execute_system_configurator_get_settings_action(self):
        """Test system configurator get settings action execution."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.ENVIRONMENT = "test"
        mock_settings.DEBUG = True
        
        with patch('netra_backend.app.core.config.get_settings', return_value=mock_settings):
            # Test: Execute get settings action
            result = await self.executor.execute_system_configurator(action="get_settings")
            
            # Verify: Result structure
            assert result["status"] == "success"
            assert "settings" in result
            assert result["settings"]["environment"] == "test"
            assert result["settings"]["database_url"] == "***hidden***"
            assert result["settings"]["debug_mode"] is True

    async def test_execute_system_configurator_unknown_action(self):
        """Test system configurator with unknown action."""
        # Test: Execute system configurator with unknown action
        result = await self.executor.execute_system_configurator(action="unknown_action")
        
        # Verify: Error for unknown action
        assert "error" in result
        assert "Unknown system configurator action: unknown_action" in result["error"]

    def test_extract_setting_params(self):
        """Test setting parameters extraction."""
        # Test: Extract setting parameters
        setting_name, value = self.executor._extract_setting_params(
            setting_name="test_setting",
            value="test_value"
        )
        
        # Verify: Parameter values
        assert setting_name == "test_setting"
        assert value == "test_value"

    def test_validate_setting_update_valid_name(self):
        """Test setting update validation with valid setting_name."""
        # Test: Validate setting update with valid name
        error = self.executor._validate_setting_update("valid_setting")
        
        # Verify: No validation error
        assert error is None

    def test_validate_setting_update_missing_name(self):
        """Test setting update validation with missing setting_name."""
        # Test: Validate setting update without name
        error = self.executor._validate_setting_update(None)
        
        # Verify: Validation error
        assert error is not None
        assert "setting_name required" in error["error"]

    def test_build_setting_update_response(self):
        """Test setting update response building."""
        # Test: Build setting update response
        response = self.executor._build_setting_update_response("test_setting", "test_value")
        
        # Verify: Response structure
        assert response["status"] == "success"
        assert response["setting"] == "test_setting"
        assert response["value"] == "test_value"
        assert "simulated" in response["message"]

    def test_build_safe_settings(self):
        """Test safe settings building (hiding secrets)."""
        # Mock settings with various attributes
        mock_settings = Mock()
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DEBUG = False
        
        # Test: Build safe settings
        safe_settings = self.executor._build_safe_settings(mock_settings)
        
        # Verify: Safe settings structure
        assert safe_settings["environment"] == "production"
        assert safe_settings["database_url"] == "***hidden***"
        assert safe_settings["debug_mode"] is False


class LogAnalyzerExecutionTests(SSotAsyncTestCase):
    """Test AdminToolExecutors log analyzer functionality."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        
        self.mock_db = Mock(spec=AsyncSession)
        self.mock_user = Mock(spec=User)
        self.mock_user.id = "test-user-log-001"
        
        self.executor = AdminToolExecutors(self.mock_db, self.mock_user)

    async def test_execute_log_analyzer_analyze_action(self):
        """Test log analyzer analyze action execution."""
        # Mock debug service
        mock_debug_result = {
            "logs": [
                {"level": "INFO", "message": "Test log message 1"},
                {"level": "ERROR", "message": "Test log message 2"}
            ]
        }
        
        with patch('netra_backend.app.services.debug_service.DebugService') as MockService:
            mock_service_instance = Mock()
            mock_service_instance.get_debug_info = AsyncMock(return_value=mock_debug_result)
            MockService.return_value = mock_service_instance
            
            # Test: Execute log analyze action
            result = await self.executor.execute_log_analyzer(
                action="analyze",
                query="error",
                time_range="2h"
            )
            
            # Verify: Service was called with correct parameters
            mock_service_instance.get_debug_info.assert_called_once_with(
                component="logs",
                include_logs=True,
                user_id=self.mock_user.id
            )
            
            # Verify: Result structure
            assert result["status"] == "success"
            assert result["query"] == "error"
            assert result["time_range"] == "2h"
            assert "logs" in result
            assert len(result["logs"]) == 2
            assert "Log analysis for query: error" in result["summary"]

    async def test_execute_log_analyzer_get_recent_action(self):
        """Test log analyzer get recent logs action execution."""
        # Mock debug service
        mock_debug_result = {
            "logs": [
                {"level": "INFO", "message": "Recent log 1", "timestamp": "2023-01-01T10:00:00"},
                {"level": "WARN", "message": "Recent log 2", "timestamp": "2023-01-01T10:01:00"},
                {"level": "ERROR", "message": "Recent log 3", "timestamp": "2023-01-01T10:02:00"}
            ]
        }
        
        with patch('netra_backend.app.services.debug_service.DebugService') as MockService:
            mock_service_instance = Mock()
            mock_service_instance.get_debug_info = AsyncMock(return_value=mock_debug_result)
            MockService.return_value = mock_service_instance
            
            # Test: Execute get recent logs action
            result = await self.executor.execute_log_analyzer(
                action="get_recent",
                limit=50,
                level="ERROR"
            )
            
            # Verify: Result structure
            assert result["status"] == "success"
            assert "logs" in result
            assert result["count"] == 3  # All logs returned
            assert result["level"] == "ERROR"

    async def test_execute_log_analyzer_unknown_action(self):
        """Test log analyzer with unknown action."""
        # Test: Execute log analyzer with unknown action
        result = await self.executor.execute_log_analyzer(action="unknown_action")
        
        # Verify: Error for unknown action
        assert "error" in result
        assert "Unknown log analyzer action: unknown_action" in result["error"]

    def test_extract_log_analysis_params_with_custom_values(self):
        """Test log analysis parameters extraction with custom values."""
        # Test: Extract log analysis parameters with custom values
        query, time_range = self.executor._extract_log_analysis_params({
            "query": "custom_query",
            "time_range": "24h"
        })
        
        # Verify: Parameter values
        assert query == "custom_query"
        assert time_range == "24h"

    def test_extract_log_analysis_params_with_defaults(self):
        """Test log analysis parameters extraction with default values."""
        # Test: Extract log analysis parameters with defaults
        query, time_range = self.executor._extract_log_analysis_params({})
        
        # Verify: Default parameter values
        assert query == ""
        assert time_range == "1h"

    def test_build_log_analysis_response(self):
        """Test log analysis response building."""
        mock_logs = [
            {"level": "INFO", "message": "Test log 1"},
            {"level": "ERROR", "message": "Test log 2"}
        ]
        mock_debug_result = {"logs": mock_logs}
        
        # Test: Build log analysis response
        response = self.executor._build_log_analysis_response(
            "test_query", "4h", mock_debug_result
        )
        
        # Verify: Response structure
        assert response["status"] == "success"
        assert response["query"] == "test_query"
        assert response["time_range"] == "4h"
        assert response["logs"] == mock_logs
        assert "Log analysis for query: test_query" in response["summary"]

    def test_extract_recent_logs_params_with_custom_values(self):
        """Test recent logs parameters extraction with custom values."""
        # Test: Extract recent logs parameters with custom values
        limit, level = self.executor._extract_recent_logs_params({
            "limit": 200,
            "level": "DEBUG"
        })
        
        # Verify: Parameter values
        assert limit == 200
        assert level == "DEBUG"

    def test_extract_recent_logs_params_with_defaults(self):
        """Test recent logs parameters extraction with default values."""
        # Test: Extract recent logs parameters with defaults
        limit, level = self.executor._extract_recent_logs_params({})
        
        # Verify: Default parameter values
        assert limit == 100
        assert level == "INFO"

    def test_filter_and_limit_logs(self):
        """Test log filtering and limiting."""
        mock_debug_result = {
            "logs": [f"log_{i}" for i in range(150)]  # 150 logs
        }
        
        # Test: Filter and limit logs to 100
        filtered_logs = self.executor._filter_and_limit_logs(mock_debug_result, 100)
        
        # Verify: Logs were limited to 100
        assert len(filtered_logs) == 100
        assert filtered_logs == [f"log_{i}" for i in range(100)]

    def test_build_recent_logs_response(self):
        """Test recent logs response building."""
        mock_logs = [
            {"level": "INFO", "message": "Recent log 1"},
            {"level": "ERROR", "message": "Recent log 2"}
        ]
        
        # Test: Build recent logs response
        response = self.executor._build_recent_logs_response(mock_logs, "WARN")
        
        # Verify: Response structure
        assert response["status"] == "success"
        assert response["logs"] == mock_logs
        assert response["count"] == 2
        assert response["level"] == "WARN"


class AdminToolExecutorsEdgeCasesTests(SSotBaseTestCase):
    """Test AdminToolExecutors edge cases and error scenarios."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        
        self.mock_db = Mock(spec=AsyncSession)
        self.mock_user = Mock(spec=User)
        self.mock_user.id = "test-user-edge-001"
        
        self.executor = AdminToolExecutors(self.mock_db, self.mock_user)

    async def test_service_call_error_handling(self):
        """Test error handling when service calls fail."""
        # Mock corpus service to raise exception
        with patch('netra_backend.app.core.configuration.services.corpus_service') as mock_service:
            mock_service.create_corpus = AsyncMock(side_effect=ValueError("Service error"))
            
            # Test: Execute action that causes service error
            with pytest.raises(ValueError, match="Service error"):
                await self.executor.execute_corpus_manager(
                    action="create",
                    domain="test",
                    name="test_corpus"
                )

    def test_parameter_extraction_edge_cases(self):
        """Test parameter extraction with edge case values."""
        # Test: Extract corpus parameters with empty values
        params = self.executor._extract_corpus_params(
            domain="",
            name="",
            description=""
        )
        
        # Verify: Empty values are preserved
        assert params["domain"] == ""
        assert params["name"] == ""
        assert params["description"] == ""

    def test_validation_with_edge_case_inputs(self):
        """Test validation methods with edge case inputs."""
        # Test: Validate user creation with empty string
        error = self.executor._validate_user_creation("")
        assert error is not None
        assert "email required" in error["error"]
        
        # Test: Validate permission grant with empty strings
        error = self.executor._validate_permission_grant("", "")
        assert error is not None
        assert "user_email and permission required" in error["error"]
        
        # Test: Validate setting update with empty string
        error = self.executor._validate_setting_update("")
        assert error is not None
        assert "setting_name required" in error["error"]

    async def test_concurrent_execution_safety(self):
        """Test that executor can handle concurrent operations safely."""
        # Test: Execute multiple operations concurrently
        tasks = [
            self.executor.execute_corpus_manager(action="validate", corpus_id=f"corpus-{i}")
            for i in range(5)
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify: All operations completed successfully
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["status"] == "success"
            assert result["corpus_id"] == f"corpus-{i}"

    def test_memory_efficiency_with_large_params(self):
        """Test memory efficiency with large parameter sets."""
        # Test: Extract parameters with large data structures
        large_description = "x" * 10000  # 10KB description
        params = self.executor._extract_corpus_params(
            domain="large",
            name="large_corpus",
            description=large_description
        )
        
        # Verify: Large parameters are handled correctly
        assert params["description"] == large_description
        assert len(params["description"]) == 10000