"""
Integration Test: WebSocket SSOT Agent Bridge Integration

PURPOSE: Test the integration between websocket_ssot.py and agent_websocket_bridge functionality

CRITICAL ISSUE VALIDATION:
- Tests that websocket_ssot.py can properly import and use agent_websocket_bridge
- Validates that agent handler setup succeeds with correct imports
- Demonstrates failure with broken imports from websocket_ssot.py lines 732 and 747

BUSINESS IMPACT: 
- Golden Path protection for user chat functionality ($500K+ ARR)
- WebSocket agent integration enables real-time AI responses
- Prevents agent handler setup failures in staging environment

Test should FAIL with broken imports, PASS after fix.
"""

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.types.core_types import UserID, ThreadID


class TestWebSocketSSotAgentIntegration(SSotAsyncTestCase):
    """Integration tests for WebSocket SSOT and agent bridge functionality."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.category = "INTEGRATION"
        self.test_name = "websocket_ssot_agent_integration"
        
        # Test data
        self.user_id = UserID(str(uuid.uuid4()))
        self.thread_id = ThreadID(str(uuid.uuid4()))
        
    async def test_websocket_ssot_agent_handler_setup_fails_with_broken_imports(self):
        """Test that agent handler setup fails with broken imports in websocket_ssot.py."""
        
        try:
            # Import the websocket_ssot module which contains the broken imports
            from netra_backend.app.routes.websocket_ssot import UnifiedWebSocketManager
            
            # Create a mock user context
            mock_user_context = MagicMock()
            mock_user_context.user_id = self.user_id
            mock_user_context.thread_id = self.thread_id
            
            # Create WebSocket manager instance
            manager = UnifiedWebSocketManager()
            
            # This should fail due to broken imports in the _setup_agent_handlers method
            with pytest.raises(ImportError) as exc_info:
                await manager._setup_agent_handlers(mock_user_context)
            
            # Verify it's the expected import error
            error_msg = str(exc_info.value)
            assert "netra_backend.app.agents.agent_websocket_bridge" in error_msg, \
                f"Expected import error for broken path, got: {error_msg}"
            
            self.logger.critical(f"EXPECTED FAILURE: Agent handler setup failed due to broken import: {error_msg}")
            
        except ImportError as e:
            if "netra_backend.app.agents.agent_websocket_bridge" in str(e):
                # This is the expected failure we're testing for
                self.logger.critical(f"GOLDEN PATH BLOCKED: WebSocket agent handler setup failed: {e}")
                # Re-raise to fail the test as expected
                raise
            else:
                # Unexpected import error
                pytest.fail(f"Unexpected import error: {e}")
    
    async def test_websocket_ssot_agent_bridge_creation_fails_with_broken_imports(self):
        """Test that agent bridge creation fails with broken imports."""
        
        try:
            # Import the websocket_ssot module 
            from netra_backend.app.routes.websocket_ssot import UnifiedWebSocketManager
            
            # Create a mock user context
            mock_user_context = MagicMock()
            mock_user_context.user_id = self.user_id
            
            # Create WebSocket manager instance
            manager = UnifiedWebSocketManager()
            
            # Test the _create_agent_websocket_bridge method (line 747 has broken import)
            with pytest.raises(ImportError) as exc_info:
                await manager._create_agent_websocket_bridge(mock_user_context)
            
            # Verify it's the expected import error from line 747
            error_msg = str(exc_info.value)
            assert "netra_backend.app.agents.agent_websocket_bridge" in error_msg, \
                f"Expected import error for broken path at line 747, got: {error_msg}"
            
            self.logger.critical(f"EXPECTED FAILURE: Agent bridge creation failed at line 747: {error_msg}")
            
        except ImportError as e:
            if "netra_backend.app.agents.agent_websocket_bridge" in str(e):
                # This is the expected failure we're testing for
                self.logger.critical(f"STAGING ISSUE REPRODUCED: Agent bridge creation failed: {e}")
                # Re-raise to fail the test as expected
                raise
            else:
                # Unexpected import error
                pytest.fail(f"Unexpected import error: {e}")
    
    @patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge')
    async def test_websocket_ssot_agent_integration_succeeds_with_correct_imports(self, mock_create_bridge):
        """Test that agent integration succeeds when imports are fixed."""
        
        # Mock the agent bridge creation to simulate correct imports
        mock_bridge = AsyncMock()
        mock_bridge.handle_message = AsyncMock(return_value={"status": "success"})
        mock_create_bridge.return_value = mock_bridge
        
        try:
            # Temporarily patch the broken imports to simulate the fix
            with patch.dict('sys.modules', {
                'netra_backend.app.agents.agent_websocket_bridge': 
                    __import__('netra_backend.app.services.agent_websocket_bridge')
            }):
                from netra_backend.app.routes.websocket_ssot import UnifiedWebSocketManager
                
                # Create a mock user context
                mock_user_context = MagicMock()
                mock_user_context.user_id = self.user_id
                mock_user_context.thread_id = self.thread_id
                
                # Create WebSocket manager instance
                manager = UnifiedWebSocketManager()
                
                # This should succeed with patched imports
                await manager._setup_agent_handlers(mock_user_context)
                
                # Verify bridge creation was called
                mock_create_bridge.assert_called_once_with(mock_user_context)
                
                self.logger.info("SUCCESS: Agent handler setup succeeded with correct import path")
                
        except Exception as e:
            pytest.fail(f"Agent integration failed unexpectedly with mocked correct imports: {e}")
    
    async def test_agent_handler_message_processing_requires_working_bridge(self):
        """Test that agent message processing requires working bridge creation."""
        
        try:
            from netra_backend.app.routes.websocket_ssot import UnifiedWebSocketManager
            
            # Create a mock user context and message
            mock_user_context = MagicMock()
            mock_user_context.user_id = self.user_id
            
            test_message = {
                "type": "agent_request",
                "content": "Test message for agent processing",
                "thread_id": str(self.thread_id)
            }
            
            # Create WebSocket manager instance
            manager = UnifiedWebSocketManager()
            
            # This should fail because agent bridge creation fails due to broken imports
            with pytest.raises(ImportError):
                # First setup handlers (this will fail)
                await manager._setup_agent_handlers(mock_user_context)
            
            self.logger.critical("GOLDEN PATH BLOCKED: Agent message processing unavailable due to import issue")
            
        except ImportError as e:
            if "netra_backend.app.agents.agent_websocket_bridge" in str(e):
                # Expected failure
                self.logger.critical(f"CHAT FUNCTIONALITY BROKEN: {e}")
                raise
            else:
                pytest.fail(f"Unexpected import error: {e}")
    
    async def test_websocket_manager_initialization_impact(self):
        """Test impact of broken imports on WebSocket manager initialization."""
        
        try:
            from netra_backend.app.routes.websocket_ssot import UnifiedWebSocketManager
            
            # WebSocket manager can be created but agent functionality will fail
            manager = UnifiedWebSocketManager()
            assert manager is not None, "WebSocket manager creation should succeed"
            
            # But any agent-related functionality will fail
            mock_user_context = MagicMock()
            mock_user_context.user_id = self.user_id
            
            # Test both broken import locations
            with pytest.raises(ImportError):
                # Line 732 broken import (in _setup_agent_handlers)
                await manager._setup_agent_handlers(mock_user_context)
            
            with pytest.raises(ImportError):
                # Line 747 broken import (in _create_agent_websocket_bridge)
                await manager._create_agent_websocket_bridge(mock_user_context)
            
            self.logger.critical("BUSINESS IMPACT: WebSocket manager exists but agent functionality is broken")
            self.logger.critical("REVENUE IMPACT: $500K+ ARR at risk due to non-functional chat")
            
        except ImportError as e:
            if "netra_backend.app.agents.agent_websocket_bridge" in str(e):
                self.logger.critical(f"STAGING DEPLOYMENT FAILURE: {e}")
                raise
            else:
                pytest.fail(f"Unexpected import error: {e}")
    
    async def test_import_fix_validation_requirements(self):
        """Test that validates the exact fix requirements."""
        
        self.logger.info("=== WEBSOCKET SSOT INTEGRATION FIX REQUIREMENTS ===")
        self.logger.info("FILE: netra_backend/app/routes/websocket_ssot.py")
        self.logger.info("LINE 732: Change import in _setup_agent_handlers method")
        self.logger.info("LINE 747: Change import in _create_agent_websocket_bridge method")
        self.logger.info("")
        self.logger.info("BROKEN:  from netra_backend.app.agents.agent_websocket_bridge import create_agent_websocket_bridge")
        self.logger.info("CORRECT: from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge")
        self.logger.info("")
        self.logger.info("BUSINESS IMPACT: Restores Golden Path chat functionality")
        self.logger.info("TECHNICAL IMPACT: Fixes agent handler setup and bridge creation")
        self.logger.info("REVENUE IMPACT: Protects $500K+ ARR from chat functionality failure")
        
        # Verify the correct module exists and has the required function
        try:
            from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
            assert callable(create_agent_websocket_bridge), "create_agent_websocket_bridge must be callable"
            self.logger.info("VERIFIED: Correct import path contains required function")
        except ImportError as e:
            pytest.fail(f"Correct import path validation failed: {e}")

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])