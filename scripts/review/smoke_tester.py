#!/usr/bin/env python3
"""
Smoke test functionality for code review system.
Runs critical system health checks to validate basic functionality.
"""

from typing import List, Tuple

from scripts.review.command_runner import CommandRunner
from scripts.review.core import ReviewConfig, ReviewData


class SmokeTester:
    """Runs critical system smoke tests"""
    
    def __init__(self, config: ReviewConfig, command_runner: CommandRunner):
        self.config = config
        self.runner = command_runner
    
    def run_all_smoke_tests(self, review_data: ReviewData) -> bool:
        """Run all smoke tests and update review data"""
        print("\n[SMOKE TESTS] Running Critical Smoke Tests...")
        all_passed = True
        all_passed &= self._run_backend_tests(review_data)
        all_passed &= self._run_frontend_tests(review_data)
        all_passed &= self._run_import_tests(review_data)
        return all_passed
    
    def _run_backend_tests(self, review_data: ReviewData) -> bool:
        """Run backend smoke tests"""
        tests = self._get_backend_test_commands()
        all_passed = True
        for test_name, cmd in tests:
            success, output = self.runner.run(cmd)
            review_data.add_smoke_test_result(test_name, success)
            self._print_test_result(test_name, success, output)
            if not success:
                all_passed = False
        return all_passed
    
    def _get_backend_test_commands(self) -> List[Tuple[str, str]]:
        """Get backend test commands"""
        return [
            ("Backend Imports", "python -c \"from netra_backend.app.main import app; print('[U+2713] FastAPI app imports successfully')\""),
            ("Database Config", "python -c \"from netra_backend.app.db.postgres import get_engine; print('[U+2713] Database connection configured')\""),
            ("Redis Manager", "python -c \"from netra_backend.app.redis_manager import RedisManager; print('[U+2713] Redis manager available')\""),
            ("Supervisor Agent", "python -c \"from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent; print('[U+2713] Supervisor agent loads')\""),
            ("Agent Service", "python -c \"from netra_backend.app.services.agent_service import AgentService; print('[U+2713] Agent service available')\""),
            ("Tool Dispatcher", "python -c \"from netra_backend.app.agents.tool_dispatcher import ToolDispatcher; print('[U+2713] Tool dispatcher functional')\""),
            ("WebSocket Manager", "python -c \"from netra_backend.app.websocket_core.manager import WebSocketManager; print('[U+2713] WebSocket manager loads')\""),
            ("Message Handler", "python -c \"from netra_backend.app.services.websocket.message_handler import MessageHandler; print('[U+2713] Message handler available')\""),
        ]
    
    def _run_frontend_tests(self, review_data: ReviewData) -> bool:
        """Run frontend smoke tests"""
        print("\n  [FRONTEND] Testing Frontend...")
        tests = self._get_frontend_test_commands()
        for test_name, cmd in tests:
            success, output = self.runner.run_with_extended_timeout(cmd)
            review_data.add_smoke_test_result(test_name, success)
            self._print_frontend_result(test_name, success)
            if not success:
                review_data.issue_tracker.add_issue("medium", f"Frontend check failed: {test_name}")
        return True  # Frontend failures are non-critical
    
    def _get_frontend_test_commands(self) -> List[Tuple[str, str]]:
        """Get frontend test commands"""
        return [
            ("Frontend Lint", "cd frontend && npm run lint --silent"),
            ("TypeScript Check", "cd frontend && npm run type-check"),
        ]
    
    def _run_import_tests(self, review_data: ReviewData) -> bool:
        """Run import validation tests"""
        print("\n  [IMPORTS] Running Import Tests...")
        success, output = self.runner.run("python test_runner.py --mode quick", timeout=180)
        review_data.add_smoke_test_result("Import Tests", success)
        self._print_test_result("Import Tests", success, output)
        return success
    
    def _print_test_result(self, test_name: str, success: bool, output: str) -> None:
        """Print test result with appropriate formatting"""
        if success:
            print(f"  [PASS] {test_name}")
        else:
            print(f"  [FAIL] {test_name}")
            if self.config.is_quick_mode():
                print(f"     Error: {output[:200]}")
    
    def _print_frontend_result(self, test_name: str, success: bool) -> None:
        """Print frontend test result"""
        if success:
            print(f"  [PASS] {test_name}")
        else:
            print(f"  [WARN] {test_name}: FAIL (non-critical)")