"""
MCP Configuration Utilities

Configuration generators for different MCP clients.
Maintains 25-line function limit and single responsibility.
"""

import os
from typing import Dict, Any, Optional
from app.schemas import UserInDB


def get_mcp_config(user: Optional[UserInDB]) -> Dict[str, Any]:
    """Get MCP configuration for clients"""
    base_url = os.getenv("MCP_BASE_URL", "http://localhost:8000")
    return _build_all_configs(base_url)


def _build_all_configs(base_url: str) -> Dict[str, Any]:
    """Build all client configurations"""
    return {
        "claude": get_claude_config(base_url),
        "cursor": get_cursor_config(),
        "http": get_http_config(base_url),
        "websocket": get_websocket_config(base_url)
    }


def get_claude_config(base_url: str) -> Dict[str, Any]:
    """Get Claude MCP configuration"""
    return {
        "mcpServers": {
            "netra": _build_claude_server_config(base_url)
        }
    }


def _build_claude_server_config(base_url: str) -> Dict[str, Any]:
    """Build Claude server configuration"""
    return {
        "command": "python",
        "args": ["-m", "app.mcp.run_server"],
        "env": _build_claude_env_config(base_url)
    }


def _build_claude_env_config(base_url: str) -> Dict[str, str]:
    """Build Claude environment configuration"""
    return {
        "NETRA_API_KEY": "${NETRA_API_KEY}",
        "NETRA_BASE_URL": base_url
    }


def get_cursor_config() -> Dict[str, Any]:
    """Get Cursor MCP configuration"""
    return {
        "mcp": {
            "servers": _build_cursor_servers_config()
        }
    }


def _build_cursor_servers_config() -> Dict[str, Any]:
    """Build Cursor servers configuration"""
    return {
        "netra": _build_cursor_server_config()
    }


def _build_cursor_server_config() -> Dict[str, Any]:
    """Build Cursor server configuration"""
    return {
        "transport": "stdio",
        "command": "python -m app.mcp.run_server"
    }


def get_http_config(base_url: str) -> Dict[str, Any]:
    """Get HTTP MCP configuration"""
    return {
        "endpoint": f"{base_url}/api/mcp",
        "transport": "http",
        "authentication": "Bearer token or API key"
    }


def get_websocket_config(base_url: str) -> Dict[str, Any]:
    """Get WebSocket MCP configuration"""
    ws_url = _build_websocket_url(base_url)
    return {
        "endpoint": ws_url,
        "transport": "websocket",
        "authentication": "Query parameter: api_key"
    }


def _build_websocket_url(base_url: str) -> str:
    """Build WebSocket URL from base URL"""
    clean_url = base_url.replace('http://', '').replace('https://', '')
    return f"ws://{clean_url}/api/mcp/ws"