#!/usr/bin/env python3
"""
UNIT: GCP Client Manager Unit Tests

Business Value Justification (BVJ):
- Segment: Enterprise & Mid-tier
- Business Goal: Reliable GCP service connectivity and error reporting
- Value Impact: Ensures GCP integration works correctly for monitoring requirements
- Strategic/Revenue Impact: Critical for Enterprise customers requiring external monitoring

EXPECTED INITIAL STATE: FAIL - proves missing GCP integration components
These tests validate individual GCP client manager components work correctly.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# SSOT Imports - following CLAUDE.md requirements
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import the class under test
from netra_backend.app.services.monitoring.gcp_client_manager import (
    GCPClientManager,
    GCPCredentials,
    create_gcp_client_manager,
    MockErrorReportingClient,
    MockMonitoringClient,
    MockLoggingClient
)


class TestGCPClientManagerUnit(SSotBaseTestCase):
    """
    UNIT: GCP Client Manager Unit Test Suite
    
    Tests individual components of the GCP Client Manager for proper initialization,
    configuration, and error handling patterns.
    
    Expected Initial State: FAIL - proves missing GCP client integration components
    Success Criteria: All GCP client components work independently
    """
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.test_project_id = "test-project-id"
        self.test_credentials = {
            "type": "service_account",
            "project_id": self.test_project_id,
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    
    def test_gcp_credentials_creation(self):
        """
        Test GCP credentials object creation and validation.
        
        EXPECTED RESULT: PASS - Basic credential object creation should work
        """
        print("\n🔐 UNIT TEST: GCP Credentials Creation")
        print("=" * 50)
        
        # Test basic credentials creation
        credentials = GCPCredentials(
            project_id=self.test_project_id,
            service_account_key=self.test_credentials
        )
        
        assert credentials.project_id == self.test_project_id
        assert credentials.service_account_key == self.test_credentials
        
        print("✅ GCP credentials object created successfully")
        
        # Test credentials without service account key (default credentials)
        default_credentials = GCPCredentials(project_id=self.test_project_id)
        
        assert default_credentials.project_id == self.test_project_id
        assert default_credentials.service_account_key is None
        
        print("✅ Default credentials (no service account key) created successfully")
    
    def test_gcp_client_manager_initialization_without_gcp_libraries(self):
        """
        Test GCP Client Manager initialization when GCP libraries are not available.
        
        EXPECTED RESULT: PASS - Mock clients should be created when GCP not available
        """
        print("\n📚 UNIT TEST: GCP Client Manager Without Libraries")
        print("=" * 55)
        
        credentials = GCPCredentials(project_id=self.test_project_id)
        manager = GCPClientManager(credentials)
        
        # Test initial state
        assert manager.credentials.project_id == self.test_project_id
        assert not manager._initialized
        assert manager._error_reporting_client is None
        assert manager._monitoring_client is None
        assert manager._logging_client is None
        
        print("✅ GCP Client Manager initialized with correct initial state")
        
        # Test getting mock clients when GCP not available
        error_client = manager.get_error_reporting_client()
        monitoring_client = manager.get_monitoring_client()
        logging_client = manager.get_logging_client()
        
        # These should return mock clients
        assert isinstance(error_client, MockErrorReportingClient)
        assert isinstance(monitoring_client, MockMonitoringClient)
        assert isinstance(logging_client, MockLoggingClient)
        
        print("✅ Mock clients returned when GCP libraries not available")
    
    @patch('netra_backend.app.services.monitoring.gcp_client_manager.GOOGLE_CLOUD_AVAILABLE', True)
    @patch('netra_backend.app.services.monitoring.gcp_client_manager.error_reporting')
    @patch('netra_backend.app.services.monitoring.gcp_client_manager.monitoring_v3')
    @patch('netra_backend.app.services.monitoring.gcp_client_manager.gcp_logging')
    @patch('netra_backend.app.services.monitoring.gcp_client_manager.service_account')
    @pytest.mark.asyncio
    async def test_gcp_client_manager_initialization_with_gcp_libraries(
        self, mock_service_account, mock_gcp_logging, mock_monitoring_v3, mock_error_reporting
    ):
        """
        Test GCP Client Manager initialization when GCP libraries are available.
        
        EXPECTED RESULT: INITIALLY FAIL - proves missing GCP configuration
        This test shows what should happen when GCP is properly configured.
        """
        print("\n☁️ UNIT TEST: GCP Client Manager With Libraries")
        print("=" * 50)
        
        # Setup mocks
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_info.return_value = mock_credentials
        
        mock_error_client = MagicMock()
        mock_monitoring_client = MagicMock()
        mock_logging_client = MagicMock()
        
        mock_error_reporting.Client.return_value = mock_error_client
        mock_monitoring_v3.MetricServiceClient.return_value = mock_monitoring_client
        mock_gcp_logging.Client.return_value = mock_logging_client
        
        # Test initialization
        credentials = GCPCredentials(
            project_id=self.test_project_id,
            service_account_key=self.test_credentials
        )
        manager = GCPClientManager(credentials)
        
        # Initialize clients
        await manager.initialize()
        
        # Verify initialization
        assert manager._initialized
        assert manager._error_reporting_client == mock_error_client
        assert manager._monitoring_client == mock_monitoring_client
        assert manager._logging_client == mock_logging_client
        
        print("✅ GCP Client Manager initialized with real GCP clients")
        
        # Test client access
        error_client = manager.get_error_reporting_client()
        monitoring_client = manager.get_monitoring_client()
        logging_client = manager.get_logging_client()
        
        assert error_client == mock_error_client
        assert monitoring_client == mock_monitoring_client
        assert logging_client == mock_logging_client
        
        print("✅ Real GCP clients returned after initialization")
        
        # Verify service account credentials were used
        mock_service_account.Credentials.from_service_account_info.assert_called_once_with(
            self.test_credentials
        )
        
        # Verify clients were created with proper credentials
        mock_error_reporting.Client.assert_called_once_with(
            project=self.test_project_id,
            credentials=mock_credentials
        )
        mock_monitoring_v3.MetricServiceClient.assert_called_once_with(
            credentials=mock_credentials
        )
        mock_gcp_logging.Client.assert_called_once_with(
            project=self.test_project_id,
            credentials=mock_credentials
        )
        
        print("✅ GCP clients created with correct credentials")
    
    @patch('netra_backend.app.services.monitoring.gcp_client_manager.GOOGLE_CLOUD_AVAILABLE', True)
    @patch('netra_backend.app.services.monitoring.gcp_client_manager.error_reporting')
    @pytest.mark.asyncio
    async def test_gcp_client_initialization_failure(self, mock_error_reporting):
        """
        Test GCP Client Manager handles initialization failures gracefully.
        
        EXPECTED RESULT: PASS - Error handling should work correctly
        """
        print("\n❌ UNIT TEST: GCP Client Initialization Failure")
        print("=" * 50)
        
        # Setup mock to fail
        mock_error_reporting.Client.side_effect = Exception("GCP initialization failed")
        
        credentials = GCPCredentials(project_id=self.test_project_id)
        manager = GCPClientManager(credentials)
        
        # Test that initialization failure is handled
        with pytest.raises(Exception) as exc_info:
            await manager.initialize()
        
        assert "GCP initialization failed" in str(exc_info.value)
        assert not manager._initialized
        
        print("✅ GCP initialization failure handled correctly")
    
    def test_gcp_client_manager_uninitialized_access(self):
        """
        Test accessing GCP clients before initialization raises proper error.
        
        EXPECTED RESULT: PASS - Should raise RuntimeError for uninitialized access
        """
        print("\n🚫 UNIT TEST: Uninitialized Client Access")
        print("=" * 45)
        
        # Setup manager with GCP available but not initialized
        with patch('netra_backend.app.services.monitoring.gcp_client_manager.GOOGLE_CLOUD_AVAILABLE', True):
            credentials = GCPCredentials(project_id=self.test_project_id)
            manager = GCPClientManager(credentials)
            
            # Test accessing clients before initialization
            with pytest.raises(RuntimeError) as exc_info:
                manager.get_error_reporting_client()
            assert "GCP clients not initialized" in str(exc_info.value)
            
            with pytest.raises(RuntimeError) as exc_info:
                manager.get_monitoring_client()
            assert "GCP clients not initialized" in str(exc_info.value)
            
            with pytest.raises(RuntimeError) as exc_info:
                manager.get_logging_client()
            assert "GCP clients not initialized" in str(exc_info.value)
            
            print("✅ Proper RuntimeError raised for uninitialized client access")
    
    @pytest.mark.asyncio
    async def test_gcp_client_manager_health_check_unavailable(self):
        """
        Test health check when GCP libraries are not available.
        
        EXPECTED RESULT: PASS - Should return mock status
        """
        print("\n🩺 UNIT TEST: Health Check - GCP Unavailable")
        print("=" * 45)
        
        credentials = GCPCredentials(project_id=self.test_project_id)
        manager = GCPClientManager(credentials)
        
        health_status = await manager.health_check()
        
        assert health_status["status"] == "mock"
        assert health_status["available"] is False
        assert "Google Cloud libraries not available" in health_status["message"]
        
        print("✅ Health check returns correct mock status")
    
    @patch('netra_backend.app.services.monitoring.gcp_client_manager.GOOGLE_CLOUD_AVAILABLE', True)
    @pytest.mark.asyncio
    async def test_gcp_client_manager_health_check_available(self):
        """
        Test health check when GCP libraries are available.
        
        EXPECTED RESULT: INITIALLY FAIL - proves missing GCP configuration
        """
        print("\n🩺 UNIT TEST: Health Check - GCP Available")
        print("=" * 42)
        
        credentials = GCPCredentials(project_id=self.test_project_id)
        manager = GCPClientManager(credentials)
        
        # Mock successful initialization
        manager._initialized = True
        manager._error_reporting_client = MagicMock()
        manager._monitoring_client = MagicMock()
        manager._logging_client = MagicMock()
        
        health_status = await manager.health_check()
        
        assert health_status["status"] == "healthy"
        assert health_status["project_id"] == self.test_project_id
        assert health_status["error_reporting"] is True
        assert health_status["monitoring"] is True
        assert health_status["logging"] is True
        assert isinstance(health_status["timestamp"], datetime)
        
        print("✅ Health check returns correct healthy status")
    
    def test_mock_error_reporting_client(self):
        """
        Test Mock Error Reporting Client functionality.
        
        EXPECTED RESULT: PASS - Mock client should work correctly
        """
        print("\n🎭 UNIT TEST: Mock Error Reporting Client")
        print("=" * 42)
        
        mock_client = MockErrorReportingClient()
        
        # Test exception reporting
        test_exception = Exception("Test exception")
        result = mock_client.report_exception(exception=test_exception)
        assert result is True
        
        # Test message reporting
        result = mock_client.report("Test error message")
        assert result is True
        
        print("✅ Mock Error Reporting Client functions correctly")
    
    def test_mock_monitoring_client(self):
        """
        Test Mock Monitoring Client functionality.
        
        EXPECTED RESULT: PASS - Mock client should work correctly
        """
        print("\n📊 UNIT TEST: Mock Monitoring Client")
        print("=" * 35)
        
        mock_client = MockMonitoringClient()
        
        # Test time series creation
        result = mock_client.create_time_series()
        assert result is True
        
        # Test time series listing
        result = mock_client.list_time_series()
        assert result == []
        
        print("✅ Mock Monitoring Client functions correctly")
    
    def test_mock_logging_client(self):
        """
        Test Mock Logging Client functionality.
        
        EXPECTED RESULT: PASS - Mock client should work correctly
        """
        print("\n📝 UNIT TEST: Mock Logging Client")
        print("=" * 32)
        
        mock_client = MockLoggingClient()
        
        # Test logger creation
        logger = mock_client.logger("test-logger")
        assert logger.name == "test-logger"
        
        # Test text logging
        result = logger.log_text("Test log message", severity="INFO")
        assert result is True
        
        # Test structured logging
        result = logger.log_struct({"message": "test", "level": "info"}, severity="INFO")
        assert result is True
        
        # Test log entry listing
        result = mock_client.list_entries(filter_="test filter")
        assert result == []
        
        print("✅ Mock Logging Client functions correctly")
    
    def test_gcp_client_manager_factory(self):
        """
        Test GCP Client Manager factory function.
        
        EXPECTED RESULT: PASS - Factory should create manager correctly
        """
        print("\n🏭 UNIT TEST: GCP Client Manager Factory")
        print("=" * 40)
        
        # Test factory without service account key
        manager = create_gcp_client_manager(self.test_project_id)
        
        assert isinstance(manager, GCPClientManager)
        assert manager.credentials.project_id == self.test_project_id
        assert manager.credentials.service_account_key is None
        
        print("✅ Factory creates manager without service account key")
        
        # Test factory with service account key
        manager_with_key = create_gcp_client_manager(
            self.test_project_id,
            service_account_key=self.test_credentials
        )
        
        assert isinstance(manager_with_key, GCPClientManager)
        assert manager_with_key.credentials.project_id == self.test_project_id
        assert manager_with_key.credentials.service_account_key == self.test_credentials
        
        print("✅ Factory creates manager with service account key")
    
    @pytest.mark.asyncio
    async def test_async_error_reporting_client_access(self):
        """
        Test async access to error reporting client.
        
        EXPECTED RESULT: INITIALLY FAIL - proves missing async integration
        """
        print("\n⚡ UNIT TEST: Async Error Reporting Client Access")
        print("=" * 48)
        
        credentials = GCPCredentials(project_id=self.test_project_id)
        manager = GCPClientManager(credentials)
        
        # Test that async method exists and works
        try:
            client = await manager.get_error_reporting_client_async()
            # Should return mock client when GCP not available
            assert isinstance(client, MockErrorReportingClient)
            print("✅ Async error reporting client access works")
        except AttributeError:
            pytest.fail("Missing async error reporting client access method")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])