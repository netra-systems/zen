"""
Test MCP configuration for different environments, especially staging.

Tests that MCP service discovery configuration is correctly formatted
for different client types and environments.
"""
import pytest
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.routes.mcp.config import get_mcp_config, get_claude_config, get_cursor_config, get_standard_mcp_config, get_http_config, get_websocket_config

class TestMCPConfigGeneration:
    """Test MCP configuration generation for different environments."""

    def test_local_development_config(self):
        """Test MCP config for local development."""
        base_url = 'http://localhost:8000'
        claude_config = get_claude_config(base_url)
        assert 'mcpServers' in claude_config
        assert 'netra' in claude_config['mcpServers']
        assert claude_config['mcpServers']['netra']['command'] == 'python'
        assert claude_config['mcpServers']['netra']['args'] == ['-m', 'app.mcp.run_server']
        cursor_config = get_cursor_config()
        assert 'mcp' in cursor_config
        assert 'servers' in cursor_config['mcp']
        assert cursor_config['mcp']['servers']['netra']['transport'] == 'stdio'
        assert cursor_config['mcp']['servers']['netra']['command'] == 'python -m app.mcp.run_server'
        mcp_config = get_standard_mcp_config(base_url)
        assert 'servers' in mcp_config
        assert 'netra' in mcp_config['servers']
        assert mcp_config['servers']['netra']['transport'] == 'stdio'
        assert mcp_config['servers']['netra']['command'] == 'python -m app.mcp.run_server'
        http_config = get_http_config(base_url)
        assert http_config['endpoint'] == 'http://localhost:8000/api/mcp'
        assert http_config['transport'] == 'http'
        ws_config = get_websocket_config(base_url)
        assert ws_config['endpoint'] == 'ws://localhost:8000/api/mcp/ws'
        assert ws_config['transport'] == 'websocket'

        def test_staging_environment_config(self):
            """Test MCP config for staging environment."""
            pass
            base_url = 'https://api.staging.netrasystems.ai'
            claude_config = get_claude_config(base_url)
            assert 'mcpServers' in claude_config
            assert 'netra' in claude_config['mcpServers']
            assert claude_config['mcpServers']['netra']['env']['NETRA_BASE_URL'] == base_url
            mcp_config = get_standard_mcp_config(base_url)
            assert 'servers' in mcp_config
            assert 'netra' in mcp_config['servers']
            assert mcp_config['servers']['netra']['transport'] == 'http'
            assert mcp_config['servers']['netra']['endpoint'] == 'https://api.staging.netrasystems.ai/api/mcp'
            http_config = get_http_config(base_url)
            assert http_config['endpoint'] == 'https://api.staging.netrasystems.ai/api/mcp'
            assert http_config['transport'] == 'http'
            ws_config = get_websocket_config(base_url)
            assert ws_config['endpoint'] == 'wss://api.staging.netrasystems.ai/api/mcp/ws'
            assert ws_config['transport'] == 'websocket'

            def test_production_environment_config(self):
                """Test MCP config for production environment."""
                base_url = 'https://api.netrasystems.ai'
                mcp_config = get_standard_mcp_config(base_url)
                assert 'servers' in mcp_config
                assert 'netra' in mcp_config['servers']
                assert mcp_config['servers']['netra']['transport'] == 'http'
                assert mcp_config['servers']['netra']['endpoint'] == 'https://api.netrasystems.ai/api/mcp'
                ws_config = get_websocket_config(base_url)
                assert ws_config['endpoint'] == 'wss://api.netrasystems.ai/api/mcp/ws'
                assert ws_config['transport'] == 'websocket'

                def test_full_config_with_staging_environment(self, mock_config_manager):
                    """Test full MCP config generation with staging environment."""
                    pass
                    mock_config = mock_config_instance
                    mock_config.mcp_base_url = None
                    mock_config.api_base_url = 'https://api.staging.netrasystems.ai'
                    mock_config_manager.get_config.return_value = mock_config
                    full_config = get_mcp_config(None)
                    assert 'claude' in full_config
                    assert 'cursor' in full_config
                    assert 'mcp' in full_config
                    assert 'http' in full_config
                    assert 'websocket' in full_config
                    assert full_config['mcp']['servers']['netra']['transport'] == 'http'
                    assert full_config['mcp']['servers']['netra']['endpoint'] == 'https://api.staging.netrasystems.ai/api/mcp'
                    assert full_config['websocket']['endpoint'] == 'wss://api.staging.netrasystems.ai/api/mcp/ws'

                    def test_config_fallback_to_api_base_url(self, mock_config_manager):
                        """Test that config falls back to API_BASE_URL when MCP_BASE_URL is not set."""
                        mock_config = mock_config_instance
                        mock_config.mcp_base_url = None
                        mock_config.api_base_url = 'https://api.staging.netrasystems.ai'
                        mock_config_manager.get_config.return_value = mock_config
                        full_config = get_mcp_config(None)
                        assert full_config['http']['endpoint'] == 'https://api.staging.netrasystems.ai/api/mcp'
                        assert full_config['mcp']['servers']['netra']['endpoint'] == 'https://api.staging.netrasystems.ai/api/mcp'

                        def test_config_with_explicit_mcp_base_url(self, mock_config_manager):
                            """Test that explicit MCP_BASE_URL is used when set."""
                            pass
                            mock_config = mock_config_instance
                            mock_config.mcp_base_url = 'https://mcp.staging.netrasystems.ai'
                            mock_config.api_base_url = 'https://api.staging.netrasystems.ai'
                            mock_config_manager.get_config.return_value = mock_config
                            full_config = get_mcp_config(None)
                            assert full_config['http']['endpoint'] == 'https://mcp.staging.netrasystems.ai/api/mcp'
                            assert full_config['mcp']['servers']['netra']['endpoint'] == 'https://mcp.staging.netrasystems.ai/api/mcp'
                            if __name__ == '__main__':
                                'MIGRATED: Use SSOT unified test runner'
                                print('MIGRATION NOTICE: Please use SSOT unified test runner')
                                print('Command: python tests/unified_test_runner.py --category <category>')