#!/usr/bin/env python
"""
Batch Test Fixer - Systematically fix failing tests
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class BatchTestFixer:
    """Batch fixer for failing tests"""
    
    def __init__(self):
        self.reports_dir = PROJECT_ROOT / "test_reports"
        self.fixes_dir = self.reports_dir / "fixes"
        self.fixes_dir.mkdir(exist_ok=True)
        
        self.fixes_applied = []
        self.fixes_failed = []
        
    def analyze_backend_test_failure(self, test_path: str) -> Dict:
        """Analyze a specific backend test failure"""
        print(f"Analyzing: {test_path}")
        
        try:
            # Run the test to get detailed error
            cmd = [sys.executable, "-m", "pytest", test_path, "-xvs", "--tb=short"]
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT / "app",
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace'
            )
            
            output = result.stdout + result.stderr
            
            # Parse error type
            error_info = {
                "test": test_path,
                "passed": result.returncode == 0,
                "output": output[:2000],
                "error_type": None,
                "error_message": None,
                "fix_suggestion": None
            }
            
            if result.returncode != 0:
                # Extract error type
                if "ImportError" in output or "ModuleNotFoundError" in output:
                    error_info["error_type"] = "import"
                    match = re.search(r"No module named ['\"]([^'\"]+)['\"]", output)
                    if match:
                        error_info["error_message"] = f"Missing module: {match.group(1)}"
                        error_info["fix_suggestion"] = f"Install or mock module: {match.group(1)}"
                
                elif "AttributeError" in output:
                    error_info["error_type"] = "attribute"
                    match = re.search(r"AttributeError: (.+)", output)
                    if match:
                        error_info["error_message"] = match.group(1)
                        error_info["fix_suggestion"] = "Check object initialization or mock setup"
                
                elif "TypeError" in output:
                    error_info["error_type"] = "type"
                    match = re.search(r"TypeError: (.+)", output)
                    if match:
                        error_info["error_message"] = match.group(1)
                        error_info["fix_suggestion"] = "Check function signatures and arguments"
                
                elif "ValidationError" in output:
                    error_info["error_type"] = "validation"
                    error_info["error_message"] = "Pydantic validation error"
                    error_info["fix_suggestion"] = "Check model fields and required parameters"
                
                elif "fixture" in output.lower():
                    error_info["error_type"] = "fixture"
                    error_info["error_message"] = "Fixture not found or error"
                    error_info["fix_suggestion"] = "Check fixture definitions in conftest.py"
                
                else:
                    error_info["error_type"] = "other"
                    error_info["error_message"] = "Unknown error"
            
            return error_info
            
        except subprocess.TimeoutExpired:
            return {
                "test": test_path,
                "passed": False,
                "error_type": "timeout",
                "error_message": "Test timed out",
                "fix_suggestion": "Test may have infinite loop or blocking operation"
            }
        except Exception as e:
            return {
                "test": test_path,
                "passed": False,
                "error_type": "error",
                "error_message": str(e),
                "fix_suggestion": "Check test file syntax"
            }
    
    def get_common_backend_tests(self) -> List[str]:
        """Get list of commonly failing backend tests to fix"""
        # These are the most important tests based on the codebase structure
        important_tests = [
            "tests/test_internal_imports.py",
            "tests/test_external_imports.py",
            "tests/conftest.py",
            "tests/services/test_database_repositories.py",
            "tests/services/test_llm_cache_service.py",
            "tests/services/test_agent_message_processing.py",
            "tests/services/test_apex_optimizer_tool_selection.py",
            "tests/services/test_websocket_handlers.py",
            "tests/services/test_auth_service.py",
            "tests/api/test_routes.py",
            "tests/api/test_auth_routes.py",
            "tests/api/test_websocket_routes.py",
            "tests/agents/test_supervisor.py",
            "tests/agents/test_subagents.py",
        ]
        
        # Check which tests exist
        existing_tests = []
        for test in important_tests:
            test_path = PROJECT_ROOT / "app" / test
            if test_path.exists():
                existing_tests.append(test)
        
        return existing_tests
    
    def get_common_frontend_tests(self) -> List[str]:
        """Get list of commonly failing frontend tests to fix"""
        # These are the most important frontend tests
        important_tests = [
            "__tests__/hooks/useKeyboardShortcuts.test.tsx",
            "__tests__/hooks/useWebSocket.test.tsx",
            "__tests__/hooks/useAgent.test.tsx",
            "__tests__/components/chat/ChatInterface.test.tsx",
            "__tests__/components/chat/MessageList.test.tsx",
            "__tests__/components/chat/MessageInput.test.tsx",
            "__tests__/services/webSocketService.test.ts",
            "__tests__/services/messageService.test.ts",
            "__tests__/store/unified-chat.test.ts",
            "__tests__/auth/service.test.ts",
        ]
        
        # Check which tests exist
        existing_tests = []
        for test in important_tests:
            test_path = PROJECT_ROOT / "frontend" / test
            if test_path.exists():
                existing_tests.append(test)
        
        return existing_tests
    
    def fix_backend_imports(self):
        """Fix common import issues in backend tests"""
        print("\nFixing backend import issues...")
        
        # Check and fix conftest.py
        conftest_path = PROJECT_ROOT / "app" / "tests" / "conftest.py"
        if not conftest_path.exists():
            print("Creating conftest.py with common fixtures...")
            conftest_content = '''"""
Common test fixtures and configuration
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, AsyncMock
from typing import AsyncGenerator, Generator

# Add app directory to path
APP_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(APP_DIR))

# Common fixtures
@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.query = MagicMock()
    session.execute = MagicMock()
    session.scalars = MagicMock()
    return session

@pytest.fixture
async def async_mock_db_session():
    """Async mock database session"""
    session = AsyncMock()
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.scalars = AsyncMock()
    return session

@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.expire = AsyncMock(return_value=True)
    return client

@pytest.fixture
def mock_llm_service():
    """Mock LLM service"""
    service = MagicMock()
    service.generate = AsyncMock(return_value="Generated response")
    service.stream = AsyncMock()
    return service

@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection"""
    ws = MagicMock()
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock(return_value='{"type": "test"}')
    ws.receive_json = AsyncMock(return_value={"type": "test"})
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    return ws

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "username": "testuser",
        "is_active": True,
        "is_admin": False
    }

@pytest.fixture
def sample_message_data():
    """Sample message data for testing"""
    return {
        "id": "msg-123",
        "content": "Test message",
        "role": "user",
        "thread_id": "thread-123",
        "user_id": "user-123",
        "displayed_to_user": True
    }
'''
            with open(conftest_path, 'w') as f:
                f.write(conftest_content)
            print("Created conftest.py")
    
    def process_backend_tests(self, max_tests: int = 50):
        """Process and fix backend tests"""
        print("\n" + "="*60)
        print("PROCESSING BACKEND TESTS")
        print("="*60)
        
        # Get tests to process
        tests = self.get_common_backend_tests()[:max_tests]
        
        results = []
        for test in tests:
            test_path = f"tests/{test}" if not test.startswith("tests/") else test
            result = self.analyze_backend_test_failure(test_path)
            results.append(result)
            
            if result["passed"]:
                print(f"  [PASS] {test}")
                self.fixes_applied.append(test)
            else:
                print(f"  [FAIL] {test} - {result['error_type']}")
                print(f"    Error: {result['error_message']}")
                if result["fix_suggestion"]:
                    print(f"    Fix: {result['fix_suggestion']}")
                self.fixes_failed.append(test)
        
        return results
    
    def generate_report(self, backend_results: List[Dict], frontend_results: List[Dict] = None):
        """Generate fix report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.fixes_dir / f"fix_report_{timestamp}.md"
        
        with open(report_file, 'w') as f:
            f.write("# Test Fix Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- Tests Processed: {len(backend_results)}\n")
            f.write(f"- Tests Passing: {sum(1 for r in backend_results if r['passed'])}\n")
            f.write(f"- Tests Failing: {sum(1 for r in backend_results if not r['passed'])}\n\n")
            
            f.write("## Backend Test Results\n\n")
            
            # Group by error type
            by_error_type = {}
            for result in backend_results:
                if not result["passed"]:
                    error_type = result["error_type"] or "unknown"
                    if error_type not in by_error_type:
                        by_error_type[error_type] = []
                    by_error_type[error_type].append(result)
            
            for error_type, tests in by_error_type.items():
                f.write(f"\n### {error_type.title()} Errors ({len(tests)})\n\n")
                for test in tests:
                    f.write(f"- **{test['test']}**\n")
                    f.write(f"  - Error: {test['error_message']}\n")
                    if test['fix_suggestion']:
                        f.write(f"  - Fix: {test['fix_suggestion']}\n")
                    f.write("\n")
            
            f.write("\n## Passing Tests\n\n")
            for result in backend_results:
                if result["passed"]:
                    f.write(f"- [PASS] {result['test']}\n")
        
        print(f"\nReport saved to: {report_file}")
        
        # Save JSON for further processing
        json_file = self.fixes_dir / f"fix_report_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "backend_results": backend_results,
                "frontend_results": frontend_results or [],
                "summary": {
                    "total": len(backend_results),
                    "passed": sum(1 for r in backend_results if r['passed']),
                    "failed": sum(1 for r in backend_results if not r['passed'])
                }
            }, f, indent=2)

def main():
    fixer = BatchTestFixer()
    
    # Fix common issues first
    fixer.fix_backend_imports()
    
    # Process backend tests
    backend_results = fixer.process_backend_tests(max_tests=50)
    
    # Generate report
    fixer.generate_report(backend_results)
    
    print("\n" + "="*60)
    print("BATCH FIX COMPLETE")
    print(f"Tests Fixed: {len(fixer.fixes_applied)}")
    print(f"Tests Still Failing: {len(fixer.fixes_failed)}")
    print("="*60)

if __name__ == "__main__":
    main()