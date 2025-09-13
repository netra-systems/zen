"""
Mission Critical Test Helper Utilities

This module provides specialized utilities for mission critical tests including:
- GitHub integration test helpers
- Business value validation utilities
- SSOT compliance verification
- Performance and reliability testing helpers
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock, patch

# Test framework imports
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

# Business logic imports
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from shared.isolated_environment import IsolatedEnvironment


class MissionCriticalTestHelper:
    """
    Central helper class for mission critical test infrastructure.

    Provides utilities for:
    - Business value validation testing
    - SSOT compliance verification
    - GitHub integration testing
    - WebSocket event validation
    - Performance and reliability testing
    """

    def __init__(self):
        """Initialize mission critical test helper."""
        self.isolated_env = IsolatedEnvironment()
        self.id_manager = UnifiedIDManager()

    # GitHub Integration Helpers

    def create_github_test_context(self, issue_number: Optional[int] = None) -> Dict[str, Any]:
        """Create a standardized GitHub test context."""
        return {
            "issue_number": issue_number or self._generate_test_issue_number(),
            "repository": "netra-systems/netra-apex",
            "test_session_id": self.id_manager.generate_id(IDType.REQUEST, context={"test": True}),
            "created_at": time.time(),
            "test_environment": "mission_critical"
        }

    def _generate_test_issue_number(self) -> int:
        """Generate a test issue number that won't conflict with real issues."""
        # Use a high number range for test issues (90000-99999)
        return 90000 + (int(str(uuid.uuid4()).replace('-', ''), 16) % 10000)

    def validate_github_issue_creation(self, issue_data: Dict[str, Any]) -> bool:
        """Validate that GitHub issue creation follows expected patterns."""
        required_fields = ["title", "body", "labels"]

        for field in required_fields:
            if field not in issue_data:
                return False

        # Validate title format
        if not issue_data["title"] or len(issue_data["title"]) < 10:
            return False

        # Validate body content
        if not issue_data["body"] or len(issue_data["body"]) < 50:
            return False

        # Validate labels
        if not isinstance(issue_data["labels"], list) or len(issue_data["labels"]) == 0:
            return False

        return True

    # Business Value Validation Helpers

    def validate_business_critical_functionality(self, test_result: Any) -> Dict[str, Any]:
        """Validate that test results align with business critical requirements."""
        validation_result = {
            "is_business_critical": False,
            "revenue_impact": "none",
            "functionality_status": "unknown",
            "validation_errors": []
        }

        if test_result is None:
            validation_result["validation_errors"].append("Test result is None")
            return validation_result

        # Check for revenue-impacting functionality
        revenue_indicators = [
            "chat", "websocket", "authentication", "agent", "golden_path",
            "user_flow", "ai_response", "login"
        ]

        result_str = str(test_result).lower()
        for indicator in revenue_indicators:
            if indicator in result_str:
                validation_result["is_business_critical"] = True
                validation_result["revenue_impact"] = "high"
                break

        # Validate functionality status
        if hasattr(test_result, 'status'):
            validation_result["functionality_status"] = test_result.status
        elif isinstance(test_result, bool):
            validation_result["functionality_status"] = "operational" if test_result else "failed"
        else:
            validation_result["functionality_status"] = "needs_validation"

        return validation_result

    # SSOT Compliance Helpers

    def validate_ssot_compliance(self, module_path: str, expected_patterns: List[str]) -> Dict[str, Any]:
        """Validate that a module follows SSOT patterns."""
        compliance_result = {
            "is_compliant": True,
            "violations": [],
            "score": 100.0,
            "recommendations": []
        }

        try:
            # Import the module for analysis
            module = __import__(module_path, fromlist=[''])

            # Check for SSOT patterns
            for pattern in expected_patterns:
                if not hasattr(module, pattern):
                    compliance_result["violations"].append(f"Missing SSOT pattern: {pattern}")
                    compliance_result["is_compliant"] = False

            # Calculate compliance score
            if compliance_result["violations"]:
                violation_penalty = len(compliance_result["violations"]) * 20
                compliance_result["score"] = max(0, 100 - violation_penalty)

            # Generate recommendations
            if not compliance_result["is_compliant"]:
                compliance_result["recommendations"].append(
                    "Implement missing SSOT patterns to improve compliance"
                )

        except ImportError as e:
            compliance_result["violations"].append(f"Module import failed: {e}")
            compliance_result["is_compliant"] = False
            compliance_result["score"] = 0.0

        return compliance_result

    # User Context Helpers

    def create_test_user_context(self,
                                user_id: Optional[str] = None,
                                thread_id: Optional[str] = None,
                                run_id: Optional[str] = None,
                                demo_mode: bool = True) -> UserExecutionContext:
        """Create a standardized test user execution context."""

        # Generate IDs using SSOT patterns
        user_id = user_id or self.id_manager.generate_id(IDType.USER, context={"test": True})
        thread_id = thread_id or UnifiedIDManager.generate_thread_id()
        run_id = run_id or UnifiedIDManager.generate_run_id(thread_id)
        request_id = self.id_manager.generate_id(IDType.REQUEST, context={"test": True})

        return UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            websocket_client_id=f"test_client_{uuid.uuid4().hex[:8]}",
            agent_context={"test_mode": True, "demo_mode": demo_mode},
            audit_metadata={"test_session": True, "helper_created": True}
        )

    # WebSocket Event Validation Helpers

    def validate_websocket_event_sequence(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate that WebSocket events follow the expected business sequence."""
        validation_result = {
            "is_valid_sequence": True,
            "missing_events": [],
            "unexpected_events": [],
            "business_value_score": 0.0
        }

        # Expected business-critical event sequence
        expected_events = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

        event_types = [event.get("type", "") for event in events]

        # Check for missing critical events
        for expected in expected_events:
            if expected not in event_types:
                validation_result["missing_events"].append(expected)
                validation_result["is_valid_sequence"] = False

        # Calculate business value score
        present_events = len([e for e in expected_events if e in event_types])
        validation_result["business_value_score"] = (present_events / len(expected_events)) * 100.0

        return validation_result

    # Performance and Reliability Helpers

    async def measure_performance(self, async_func, *args, **kwargs) -> Dict[str, Any]:
        """Measure performance of an async function."""
        start_time = time.time()
        start_memory = self._get_memory_usage()

        try:
            result = await async_func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)

        end_time = time.time()
        end_memory = self._get_memory_usage()

        return {
            "duration_ms": (end_time - start_time) * 1000,
            "memory_delta_mb": (end_memory - start_memory) / (1024 * 1024),
            "success": success,
            "error": error,
            "result": result
        }

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            # Fallback if psutil not available
            return 0

    # Test Data Generation Helpers

    def generate_test_data(self, data_type: str, **kwargs) -> Any:
        """Generate standardized test data for different scenarios."""

        if data_type == "user_message":
            return {
                "content": kwargs.get("content", "Test user message for mission critical validation"),
                "type": "user_message",
                "timestamp": time.time(),
                "user_id": kwargs.get("user_id", "test_user_123"),
                "session_id": kwargs.get("session_id", str(uuid.uuid4()))
            }

        elif data_type == "github_issue":
            return {
                "title": kwargs.get("title", f"Mission Critical Test Issue - {uuid.uuid4().hex[:8]}"),
                "body": kwargs.get("body", "Generated by mission critical test helper for validation purposes."),
                "labels": kwargs.get("labels", ["bug", "mission-critical", "test-generated"]),
                "assignees": kwargs.get("assignees", []),
                "milestone": kwargs.get("milestone", None)
            }

        elif data_type == "websocket_event":
            return {
                "type": kwargs.get("event_type", "agent_started"),
                "data": kwargs.get("data", {"agent_name": "test_agent"}),
                "timestamp": time.time(),
                "connection_id": kwargs.get("connection_id", str(uuid.uuid4())),
                "user_id": kwargs.get("user_id", "test_user")
            }

        else:
            raise ValueError(f"Unknown test data type: {data_type}")

    # Cleanup and Validation Helpers

    def validate_test_cleanup(self, test_artifacts: List[str]) -> Dict[str, Any]:
        """Validate that test artifacts are properly cleaned up."""
        cleanup_result = {
            "all_cleaned": True,
            "remaining_artifacts": [],
            "cleanup_errors": []
        }

        for artifact in test_artifacts:
            try:
                # Check if artifact still exists (implementation depends on artifact type)
                if self._check_artifact_exists(artifact):
                    cleanup_result["remaining_artifacts"].append(artifact)
                    cleanup_result["all_cleaned"] = False
            except Exception as e:
                cleanup_result["cleanup_errors"].append(f"Error checking {artifact}: {e}")
                cleanup_result["all_cleaned"] = False

        return cleanup_result

    def _check_artifact_exists(self, artifact: str) -> bool:
        """Check if a test artifact still exists."""
        # This is a placeholder - real implementation would depend on artifact type
        # (files, database records, cached data, etc.)
        return False

    # Utility Methods

    def get_mission_critical_config(self) -> Dict[str, Any]:
        """Get mission critical test configuration."""
        return {
            "test_timeout_seconds": 300,  # 5 minutes max for mission critical tests
            "max_memory_mb": 1024,  # 1GB memory limit
            "required_services": ["backend", "auth", "database"],
            "business_value_threshold": 75.0,  # Minimum business value score
            "ssot_compliance_threshold": 90.0,  # Minimum SSOT compliance score
            "performance_thresholds": {
                "max_response_time_ms": 5000,
                "max_memory_delta_mb": 100
            }
        }

    def log_mission_critical_result(self, test_name: str, result: Dict[str, Any]) -> None:
        """Log mission critical test results for tracking."""
        log_entry = {
            "test_name": test_name,
            "timestamp": time.time(),
            "result": result,
            "session_id": getattr(self, 'session_id', str(uuid.uuid4()))
        }

        # In a real implementation, this would log to appropriate system
        print(f"MISSION CRITICAL TEST: {test_name} - {result}")


# Backwards compatibility alias
TestHelper = MissionCriticalTestHelper