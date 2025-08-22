#!/usr/bin/env python3
"""Fix WebSocket test patterns across the codebase."""

import os
import re
from pathlib import Path

def fix_backend_websocket_tests():
    """Fix backend WebSocket test issues."""
    backend_tests_dir = Path("netra_backend/tests")
    if not backend_tests_dir.exists():
        print("Backend tests directory not found")
        return
    
    fixes_applied = 0
    
    # Find all Python test files that mention websocket
    for test_file in backend_tests_dir.rglob("*.py"):
        if "websocket" not in test_file.name.lower():
            continue
            
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix 1: Replace relative imports with absolute imports
            content = re.sub(
                r"patch\('app\.([^']+)'\)",
                r"patch('netra_backend.app.\1')",
                content
            )
            
            # Fix 2: Replace validate_token with validate_token_jwt
            content = re.sub(
                r"mock_auth_client\.validate_token\s*=",
                "mock_auth_client.validate_token_jwt =",
                content
            )
            
            content = re.sub(
                r"mock_auth_client\.validate_token\.assert_called",
                "mock_auth_client.validate_token_jwt.assert_called",
                content
            )
            
            # Fix 3: Import nonexistent modules 
            content = re.sub(
                r"from netra_backend\.app\.routes\.websocket_enhanced import",
                "from netra_backend.app.routes.websocket import",
                content
            )
            
            # Fix 4: Fix connection_manager imports
            content = re.sub(
                r"from netra_backend\.app\.core\.websocket_connection_manager import connection_manager",
                "from netra_backend.app.ws_manager import WebSocketManager",
                content
            )
            
            # Fix 5: Ensure AsyncMock is used for async methods
            if "validate_token_jwt = Mock" in content:
                content = content.replace("validate_token_jwt = Mock", "validate_token_jwt = AsyncMock")
            
            if content != original_content:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Fixed backend test: {test_file}")
                fixes_applied += 1
                
        except Exception as e:
            print(f"Error fixing {test_file}: {e}")
    
    return fixes_applied

def fix_frontend_websocket_tests():
    """Fix frontend WebSocket test issues."""
    frontend_tests_dir = Path("frontend/__tests__")
    if not frontend_tests_dir.exists():
        print("Frontend tests directory not found")
        return
    
    fixes_applied = 0
    
    # Find all TypeScript test files
    for test_file in frontend_tests_dir.rglob("*.tsx"):
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix incomplete imports that have already been partially fixed
            content = re.sub(
                r"import \* as (\w+) from ('@/__tests__/helpers/[^']+');\s*\n\s*(\w+): \1;",
                r"import * as \1 from \2;\n  let \3: any;",
                content
            )
            
            # Fix function calls that need module prefix
            if "WebSocketTestManager" in content:
                content = re.sub(
                    r"\bcreateWebSocketManager\(",
                    "WebSocketTestManager.createWebSocketManager(",
                    content
                )
            
            # Fix common WebSocket mock patterns
            content = re.sub(
                r"jest\.mock\('@/lib/websocket'\)",
                "jest.mock('@/lib/websocket', () => ({}));",
                content
            )
            
            if content != original_content:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Fixed frontend test: {test_file}")
                fixes_applied += 1
                
        except Exception as e:
            print(f"Error fixing {test_file}: {e}")
    
    return fixes_applied

def create_websocket_test_helpers():
    """Create reusable WebSocket test helpers."""
    
    # Backend helper
    backend_helper = """\"\"\"WebSocket test helpers for backend tests.\"\"\"

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

class MockWebSocket:
    \"\"\"Mock WebSocket for testing.\"\"\"
    
    def __init__(self, query_params=None, headers=None):
        self.query_params = query_params or {}
        self.headers = headers or {}
        self.state = MagicMock()
        self.app = MagicMock()
        self.accept = AsyncMock()
        self.close = AsyncMock()
        self.send_text = AsyncMock()
        self.send_json = AsyncMock()
        self.receive_text = AsyncMock()
        self.receive_json = AsyncMock()

class MockAuthClient:
    \"\"\"Mock auth client for testing.\"\"\"
    
    def __init__(self, valid_response=True):
        self.valid_response = valid_response
        self.validate_token_jwt = AsyncMock(return_value={
            "valid": valid_response,
            "user_id": "test-user-123" if valid_response else None,
            "email": "test@example.com" if valid_response else None,
            "permissions": [] if valid_response else None
        })

class MockWebSocketManager:
    \"\"\"Mock WebSocket manager for testing.\"\"\"
    
    def __init__(self):
        self.connections = {}
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()
        self.send_message = AsyncMock()
        self.broadcast = AsyncMock()
        self.get_connections = MagicMock(return_value=[])

def create_mock_websocket(token="valid-token", **kwargs):
    \"\"\"Create a mock WebSocket with common settings.\"\"\"
    query_params = {"token": token}
    query_params.update(kwargs.get("query_params", {}))
    
    return MockWebSocket(
        query_params=query_params,
        headers=kwargs.get("headers", {})
    )

def create_mock_auth_client(valid=True):
    \"\"\"Create a mock auth client with standard responses.\"\"\"
    return MockAuthClient(valid_response=valid)
"""
    
    backend_helper_path = Path("netra_backend/tests/helpers/websocket_test_helpers.py")
    backend_helper_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(backend_helper_path, 'w', encoding='utf-8') as f:
        f.write(backend_helper)
    
    print(f"Created backend WebSocket test helpers: {backend_helper_path}")
    
    # Frontend helper  
    frontend_helper = """/**
 * WebSocket test helpers for frontend tests.
 */

export class MockWebSocket {
  constructor(url, protocols) {
    this.url = url;
    this.protocols = protocols;
    this.readyState = WebSocket.CONNECTING;
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;
    this.messageQueue = [];
  }

  send(data) {
    this.messageQueue.push(data);
  }

  close(code, reason) {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose({ code, reason });
    }
  }

  simulateOpen() {
    this.readyState = WebSocket.OPEN;
    if (this.onopen) {
      this.onopen({});
    }
  }

  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage({ data });
    }
  }

  simulateError(error) {
    if (this.onerror) {
      this.onerror(error);
    }
  }
}

export function createMockWebSocket() {
  return MockWebSocket;
}

export function setupWebSocketMocks() {
  global.WebSocket = MockWebSocket;
  return MockWebSocket;
}

export const mockWebSocketMessage = (type, data) => ({
  type,
  data,
  timestamp: Date.now()
});

export const mockWebSocketConnection = (connected = true) => ({
  connected,
  reconnectAttempts: 0,
  lastError: null,
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn()
});
"""
    
    frontend_helper_path = Path("frontend/__tests__/helpers/websocket-test-helpers.ts")
    frontend_helper_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(frontend_helper_path, 'w', encoding='utf-8') as f:
        f.write(frontend_helper)
    
    print(f"Created frontend WebSocket test helpers: {frontend_helper_path}")

def main():
    """Run all WebSocket test fixes."""
    print("Starting WebSocket test fixes...")
    
    backend_fixes = fix_backend_websocket_tests()
    frontend_fixes = fix_frontend_websocket_tests()
    
    create_websocket_test_helpers()
    
    print(f"\nCompleted WebSocket test fixes:")
    print(f"- Backend tests fixed: {backend_fixes}")
    print(f"- Frontend tests fixed: {frontend_fixes}")
    print(f"- Test helpers created")
    
    total_fixes = backend_fixes + frontend_fixes
    print(f"\nTotal fixes applied: {total_fixes}")

if __name__ == "__main__":
    main()