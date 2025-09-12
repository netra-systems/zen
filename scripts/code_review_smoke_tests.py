#!/usr/bin/env python3
"""
Code Review Smoke Tests
ULTRA DEEP THINK: Module-based architecture - Smoke tests extracted for 450-line compliance
"""

import subprocess
from pathlib import Path
from typing import Tuple


class CodeReviewSmokeTests:
    """Handles smoke test operations for code review"""
    
    def __init__(self, project_root: Path, mode: str):
        self.project_root = project_root
        self.mode = mode
        self.smoke_test_results = {}
        self.issues = {"critical": [], "medium": []}

    def run_command(self, cmd: str, cwd: str = None, timeout: int = 60) -> Tuple[bool, str]:
        """Run a shell command and return success status and output"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=cwd or self.project_root, timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, str(e)

    def run_smoke_tests(self):
        """Run critical system smoke tests"""
        print("\n[SMOKE TESTS] Running Critical Smoke Tests...")
        
        tests = [
            ("Backend Imports", "python -c \"from netra_backend.app.main import app; print('[U+2713] FastAPI app imports successfully')\""),
            ("Database Config", "python -c \"from netra_backend.app.db.postgres import get_engine; print('[U+2713] Database connection configured')\""),
            ("Redis Manager", "python -c \"from netra_backend.app.redis_manager import RedisManager; print('[U+2713] Redis manager available')\""),
            ("Supervisor Agent", "python -c \"from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent; print('[U+2713] Supervisor agent loads')\""),
            ("Agent Service", "python -c \"from netra_backend.app.services.agent_service import AgentService; print('[U+2713] Agent service available')\""),
            ("Tool Dispatcher", "python -c \"from netra_backend.app.agents.tool_dispatcher import ToolDispatcher; print('[U+2713] Tool dispatcher functional')\""),
            ("WebSocket Manager", "python -c \"from netra_backend.app.websocket_core.manager import WebSocketManager; print('[U+2713] WebSocket manager loads')\""),
            ("Message Handler", "python -c \"from netra_backend.app.services.websocket.message_handler import MessageHandler; print('[U+2713] Message handler available')\""),
        ]
        
        all_passed = self._run_backend_tests(tests)
        self._run_frontend_tests()
        self._run_import_tests()
        
        return all_passed

    def _run_backend_tests(self, tests) -> bool:
        """Run backend smoke tests"""
        all_passed = True
        for test_name, cmd in tests:
            success, output = self.run_command(cmd)
            self.smoke_test_results[test_name] = success
            
            if success:
                print(f"  [PASS] {test_name}")
            else:
                print(f"  [FAIL] {test_name}")
                self.issues["critical"].append(f"Smoke test failed: {test_name}")
                all_passed = False
                if self.mode == "quick":
                    print(f"     Error: {output[:200]}")
        
        return all_passed

    def _run_frontend_tests(self):
        """Run frontend smoke tests"""
        print("\n  [FRONTEND] Testing Frontend...")
        frontend_tests = [
            ("Frontend Lint", "cd frontend && npm run lint --silent"),
            ("TypeScript Check", "cd frontend && npm run type-check"),
        ]
        
        for test_name, cmd in frontend_tests:
            success, output = self.run_command(cmd, timeout=120)
            self.smoke_test_results[test_name] = success
            
            if success:
                print(f"  [PASS] {test_name}")
            else:
                print(f"  [WARN] {test_name}: FAIL (non-critical)")
                self.issues["medium"].append(f"Frontend check failed: {test_name}")

    def _run_import_tests(self):
        """Run import tests"""
        print("\n  [IMPORTS] Running Import Tests...")
        success, output = self.run_command("python test_runner.py --mode quick", timeout=180)
        self.smoke_test_results["Import Tests"] = success
        
        if success:
            print(f"  [PASS] Import Tests")
        else:
            print(f"  [FAIL] Import Tests")
            self.issues["critical"].append("Import validation tests failed")
            return False
        
        return True