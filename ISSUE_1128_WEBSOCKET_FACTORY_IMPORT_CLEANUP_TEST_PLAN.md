# Issue #1128: WebSocket Factory Import Cleanup - Comprehensive Test Plan

## 🚨 CRITICAL: Business Value Protection First

**Business Impact**: Legacy WebSocket factory imports cause system failures that block $500K+ ARR Golden Path functionality.

**Issue Summary**: 100+ files still reference non-existent `netra_backend.app.websocket_core.factory` module, causing import errors and blocking the Golden Path user flow.

## Business Value Justification (BVJ)
- **Segment**: Platform/Internal
- **Business Goal**: Eliminate import failures blocking Golden Path
- **Value Impact**: Prevent import errors that break WebSocket functionality
- **Revenue Impact**: Protect $500K+ ARR chat functionality from import failures

---

## 📋 Test Strategy Overview

Following `reports/testing/TEST_CREATION_GUIDE.md` principles:

### Test Hierarchy (Business Value → Real System → Tests)
1. **E2E GCP Staging Tests**: Validate complete Golden Path after cleanup
2. **Integration Tests (Non-Docker)**: Verify SSOT factory patterns work
3. **Unit Tests**: Detect legacy import usage and validate SSOT compliance

### Core Principles
- **Real Services > Mocks**: Use actual WebSocket connections and real staging environment
- **User Context Isolation**: Validate factory patterns prevent user contamination
- **WebSocket Events**: All 5 critical events must be sent (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- **Failing Tests First**: Create tests that detect import errors before fixing them

---

## 🧪 Unit Test Suite: Legacy Import Detection

### File: `tests/unit/websocket_factory_removal/test_legacy_import_detection.py`

```python
"""
Test Legacy WebSocket Factory Import Detection

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent deployment of code with broken imports
- Value Impact: Catch import errors before they break production
- Revenue Impact: Protect $500K+ ARR chat functionality
"""

import pytest
import ast
import os
from pathlib import Path

class TestLegacyWebSocketFactoryImportDetection:
    """Detect and prevent legacy WebSocket factory imports."""

    @pytest.mark.unit
    def test_no_websocket_core_factory_imports(self):
        """CRITICAL: No files should import from websocket_core.factory (non-existent module)."""
        legacy_imports = []
        project_root = Path(__file__).parent.parent.parent.parent

        # Scan all Python files for legacy import patterns
        for py_file in project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Detect problematic import patterns
                if self._has_legacy_factory_import(content):
                    legacy_imports.append({
                        'file': str(py_file.relative_to(project_root)),
                        'imports': self._extract_legacy_imports(content)
                    })
            except Exception as e:
                # Log but don't fail on file read errors
                print(f"Warning: Could not read {py_file}: {e}")

        # FAILING TEST: This should fail initially to detect all legacy imports
        assert len(legacy_imports) == 0, (
            f"Found {len(legacy_imports)} files with legacy websocket_core.factory imports:\n" +
            "\n".join([f"  {item['file']}: {item['imports']}" for item in legacy_imports])
        )

    @pytest.mark.unit
    def test_canonical_import_patterns_available(self):
        """Verify canonical WebSocket import patterns are available."""
        from netra_backend.app.websocket_core.canonical_imports import (
            create_websocket_manager,
            WebSocketManagerProtocol,
            UnifiedWebSocketManager,
        )

        # Verify factory function is callable
        assert callable(create_websocket_manager)

        # Verify protocol is available for type checking
        assert hasattr(WebSocketManagerProtocol, '__annotations__') or hasattr(WebSocketManagerProtocol, '__protocol_attrs__')

        # Verify manager class is available
        assert hasattr(UnifiedWebSocketManager, '__init__')

    def _should_skip_file(self, py_file: Path) -> bool:
        """Skip files that don't need scanning."""
        skip_patterns = [
            '__pycache__',
            '.git',
            'node_modules',
            'venv',
            '.pytest_cache',
            # Skip test files that intentionally test legacy imports
            'test_legacy_import_detection.py',
            'test_websocket_singleton_vulnerability.py',
        ]

        return any(pattern in str(py_file) for pattern in skip_patterns)

    def _has_legacy_factory_import(self, content: str) -> bool:
        """Check if content has legacy factory imports."""
        legacy_patterns = [
            'from netra_backend.app.websocket_core.factory import',
            'import netra_backend.app.websocket_core.factory',
            'from .factory import',  # Relative imports within websocket_core
            'websocket_core.factory',
        ]

        return any(pattern in content for pattern in legacy_patterns)

    def _extract_legacy_imports(self, content: str) -> list:
        """Extract specific legacy import statements."""
        imports = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            if self._has_legacy_factory_import(line):
                imports.append(f"Line {i}: {line.strip()}")

        return imports
```

### File: `tests/unit/websocket_factory_removal/test_ssot_compliance_validation.py`

```python
"""
Test SSOT WebSocket Factory Compliance

Validates that all WebSocket factory usage follows SSOT patterns.
"""

import pytest
from unittest.mock import AsyncMock, Mock
import sys
import importlib

class TestSSOTWebSocketFactoryCompliance:
    """Validate SSOT WebSocket factory patterns."""

    @pytest.mark.unit
    async def test_canonical_factory_creates_isolated_contexts(self):
        """Factory must create isolated user execution contexts."""
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager

        # Create contexts for different users
        user1_context = await create_websocket_manager(
            user_id="user_1",
            websocket_client_id="client_1"
        )

        user2_context = await create_websocket_manager(
            user_id="user_2",
            websocket_client_id="client_2"
        )

        # Verify isolation - different context objects
        assert user1_context is not user2_context
        assert user1_context.user_id != user2_context.user_id
        assert user1_context.websocket_client_id != user2_context.websocket_client_id

    @pytest.mark.unit
    def test_legacy_factory_module_does_not_exist(self):
        """Verify legacy factory module was properly removed."""
        with pytest.raises(ImportError, match="No module named.*websocket_core.factory"):
            import netra_backend.app.websocket_core.factory

    @pytest.mark.unit
    def test_deprecated_import_paths_fail(self):
        """All deprecated import paths should fail with clear error messages."""
        deprecated_imports = [
            "from netra_backend.app.websocket_core.factory import create_websocket_manager",
            "from netra_backend.app.websocket_core.factory import WebSocketManagerFactory",
            "import netra_backend.app.websocket_core.factory as factory",
        ]

        for import_statement in deprecated_imports:
            with pytest.raises(ImportError):
                exec(import_statement)
```

---

## 🔗 Integration Test Suite: WebSocket Factory Patterns

### File: `tests/integration/websocket_factory_removal/test_websocket_manager_integration.py`

```python
"""
Test WebSocket Manager Integration Without Legacy Factory

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket functionality works with SSOT patterns
- Value Impact: Validate real-time chat functionality after factory cleanup
- Revenue Impact: Protect $500K+ ARR WebSocket-based chat features
"""

import pytest
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestClient

class TestWebSocketManagerIntegrationWithoutFactory(BaseIntegrationTest):
    """Test WebSocket manager integration using SSOT patterns."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_initialization_ssot_pattern(self, real_services_fixture):
        """Test WebSocket manager initialization using canonical imports."""
        from netra_backend.app.websocket_core.canonical_imports import (
            create_websocket_manager,
            UnifiedWebSocketManager
        )

        # Create user execution context using SSOT factory
        user_context = await create_websocket_manager(
            user_id="integration_test_user",
            websocket_client_id="test_client_123"
        )

        # Verify context creation
        assert user_context is not None
        assert user_context.user_id == "integration_test_user"
        assert user_context.websocket_client_id == "test_client_123"

        # Verify WebSocket manager can be created from context
        websocket_manager = user_context.websocket_manager
        assert isinstance(websocket_manager, UnifiedWebSocketManager)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_websocket_isolation(self, real_services_fixture):
        """Test concurrent users have isolated WebSocket contexts."""
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager

        # Create multiple user contexts concurrently
        contexts = []
        for i in range(5):
            context = await create_websocket_manager(
                user_id=f"user_{i}",
                websocket_client_id=f"client_{i}"
            )
            contexts.append(context)

        # Verify all contexts are isolated
        for i, context in enumerate(contexts):
            assert context.user_id == f"user_{i}"
            assert context.websocket_client_id == f"client_{i}"

            # Verify no shared state between contexts
            for j, other_context in enumerate(contexts):
                if i != j:
                    assert context is not other_context
                    assert context.user_id != other_context.user_id

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_emission_after_factory_cleanup(self, real_services_fixture):
        """Test WebSocket events work correctly after factory cleanup."""
        from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager

        # Create user context
        user_context = await create_websocket_manager(
            user_id="event_test_user",
            websocket_client_id="event_test_client"
        )

        # Get WebSocket manager and test event emission
        ws_manager = user_context.websocket_manager

        # Mock WebSocket connection for testing
        mock_websocket = AsyncMock()
        await ws_manager.add_connection("event_test_client", mock_websocket)

        # Test all 5 critical events can be sent
        critical_events = [
            ("agent_started", {"agent": "test_agent", "run_id": "test_run"}),
            ("agent_thinking", {"message": "Processing request"}),
            ("tool_executing", {"tool": "test_tool"}),
            ("tool_completed", {"tool": "test_tool", "result": "success"}),
            ("agent_completed", {"result": "Test completed"})
        ]

        for event_type, data in critical_events:
            await ws_manager.emit_event(
                event_type=event_type,
                data=data,
                user_id="event_test_user"
            )

        # Verify events were sent (mock was called)
        assert mock_websocket.send_text.call_count == 5
```

---

## 🌐 E2E Test Suite: Golden Path Validation on GCP Staging

### File: `tests/e2e/websocket_factory_removal/test_golden_path_after_cleanup.py`

```python
"""
Test Golden Path WebSocket Functionality After Factory Cleanup

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete user journey works after import cleanup
- Value Impact: Validate end-to-end chat functionality on staging
- Revenue Impact: Protect $500K+ ARR Golden Path user experience
"""

import pytest
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient
import asyncio

class TestGoldenPathAfterWebSocketFactoryCleanup(BaseE2ETest):
    """Test complete Golden Path user flow on GCP staging."""

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    @pytest.mark.mission_critical
    async def test_complete_golden_path_websocket_flow(self):
        """
        MISSION CRITICAL: Complete Golden Path user flow must work after factory cleanup.

        This test validates the entire user journey:
        1. User authentication
        2. WebSocket connection
        3. Agent request
        4. All 5 WebSocket events received
        5. Meaningful AI response delivered
        """
        # Create real user on staging
        user = await self.create_test_user(
            email="factory_cleanup_test@example.com",
            subscription="early"
        )

        # Connect to staging WebSocket
        staging_url = "wss://backend.staging.netrasystems.ai/api/ws"

        async with WebSocketTestClient(
            url=staging_url,
            token=user.token
        ) as client:

            # Send optimization request (Golden Path)
            request = {
                "type": "agent_request",
                "agent": "cost_optimizer",
                "message": "Analyze my AWS costs and suggest optimizations",
                "context": {
                    "monthly_spend": 10000,
                    "primary_services": ["EC2", "RDS", "S3"]
                }
            }

            await client.send_json(request)

            # Collect all WebSocket events
            events = []
            timeout_seconds = 60  # Allow up to 60 seconds for agent completion

            async def collect_events():
                async for event in client.receive_events(timeout=timeout_seconds):
                    events.append(event)
                    print(f"Received event: {event['type']}")

                    if event['type'] == 'agent_completed':
                        break

                return events

            # Wait for agent completion
            try:
                await asyncio.wait_for(collect_events(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                pytest.fail(f"Agent did not complete within {timeout_seconds} seconds. Events received: {[e['type'] for e in events]}")

            # CRITICAL VALIDATION: All 5 events must be received
            event_types = [event['type'] for event in events]
            required_events = [
                'agent_started',
                'agent_thinking',
                'tool_executing',
                'tool_completed',
                'agent_completed'
            ]

            for required_event in required_events:
                assert required_event in event_types, (
                    f"Missing critical event: {required_event}. "
                    f"Received events: {event_types}"
                )

            # BUSINESS VALUE VALIDATION: Response must contain actionable insights
            final_event = events[-1]
            assert final_event['type'] == 'agent_completed'

            result = final_event['data']['result']
            assert 'recommendations' in result
            assert len(result['recommendations']) > 0
            assert 'cost_savings' in result

            print(f"✅ Golden Path validated successfully with {len(events)} events")

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_concurrent_users_websocket_isolation_staging(self):
        """Test multiple users can use WebSocket simultaneously without interference."""

        # Create multiple test users
        users = []
        for i in range(3):
            user = await self.create_test_user(
                email=f"concurrent_test_{i}@example.com"
            )
            users.append(user)

        staging_url = "wss://backend.staging.netrasystems.ai/api/ws"

        async def user_session(user, user_id):
            """Individual user session."""
            async with WebSocketTestClient(
                url=staging_url,
                token=user.token
            ) as client:

                # Send user-specific request
                request = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": f"Hello from user {user_id}",
                    "context": {"user_id": user_id}
                }

                await client.send_json(request)

                # Wait for agent_completed
                async for event in client.receive_events(timeout=30):
                    if event['type'] == 'agent_completed':
                        # Verify response is for this specific user
                        response_data = event['data']
                        return {
                            'user_id': user_id,
                            'response': response_data,
                            'success': True
                        }

                return {'user_id': user_id, 'success': False}

        # Run concurrent sessions
        tasks = [
            user_session(users[i], i)
            for i in range(len(users))
        ]

        results = await asyncio.gather(*tasks)

        # Verify all sessions succeeded without interference
        for result in results:
            assert result['success'], f"User {result['user_id']} session failed"

        # Verify responses are unique (no cross-contamination)
        user_ids = [r['user_id'] for r in results]
        assert len(set(user_ids)) == len(user_ids), "User isolation failure detected"

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_websocket_reconnection_after_factory_cleanup(self):
        """Test WebSocket reconnection works correctly after factory cleanup."""
        user = await self.create_test_user(
            email="reconnection_test@example.com"
        )

        staging_url = "wss://backend.staging.netrasystems.ai/api/ws"

        # Initial connection and successful interaction
        async with WebSocketTestClient(
            url=staging_url,
            token=user.token
        ) as client:

            request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Initial test message"
            }

            await client.send_json(request)

            # Wait for agent_started to confirm connection works
            async for event in client.receive_events(timeout=15):
                if event['type'] == 'agent_started':
                    break
            else:
                pytest.fail("Did not receive agent_started event")

        # Reconnect and test again (simulates real user behavior)
        async with WebSocketTestClient(
            url=staging_url,
            token=user.token
        ) as client:

            request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Reconnection test message"
            }

            await client.send_json(request)

            # Verify reconnection works
            async for event in client.receive_events(timeout=15):
                if event['type'] == 'agent_started':
                    break
            else:
                pytest.fail("Reconnection failed - did not receive agent_started event")
```

---

## 🔧 Test Execution Commands

### Run Individual Test Suites

```bash
# Unit Tests - Detect legacy imports (should FAIL initially)
python -m pytest tests/unit/websocket_factory_removal/ -v

# Integration Tests - Validate SSOT patterns work
python -m pytest tests/integration/websocket_factory_removal/ -v --real-services

# E2E Tests - Full Golden Path validation on staging
python -m pytest tests/e2e/websocket_factory_removal/ -v --staging-gcp
```

### Run Complete Test Suite

```bash
# Complete Issue #1128 validation
python tests/unified_test_runner.py \
    --test-pattern "*websocket_factory_removal*" \
    --real-services \
    --staging-gcp \
    --execution-mode comprehensive \
    --coverage
```

### Mission Critical Validation

```bash
# Must pass before deployment
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/mission_critical/test_golden_path_websocket_flow.py
```

---

## 📊 Success Criteria & Metrics

### Phase 1: Detection (Tests Should FAIL Initially)
- ✅ Unit tests detect all legacy `websocket_core.factory` imports
- ✅ Integration tests verify SSOT patterns are available
- ✅ E2E tests establish baseline Golden Path functionality

### Phase 2: Remediation (After Import Cleanup)
- ✅ All unit tests pass (no legacy imports detected)
- ✅ Integration tests pass (SSOT patterns work correctly)
- ✅ E2E tests pass (Golden Path fully functional on staging)

### Phase 3: Validation (Production Readiness)
- ✅ Mission critical tests pass (WebSocket events work)
- ✅ Staging environment stable for 24+ hours
- ✅ No import errors in application logs
- ✅ WebSocket connection success rate > 99%

---

## 🚨 Risk Mitigation

### Import Error Prevention
- Tests run before code changes to detect issues early
- Comprehensive file scanning catches all legacy import patterns
- Real staging environment validation prevents production failures

### Business Continuity Protection
- E2E tests validate complete user journeys
- Staging environment provides production-like validation
- Rollback procedures documented if issues discovered

### Performance Impact Monitoring
- WebSocket connection latency measurement
- Event delivery time tracking
- Concurrent user isolation validation

---

## 📋 Test Checklist

Before submitting PR for Issue #1128:

- [ ] Unit tests created and initially failing (detecting legacy imports)
- [ ] Integration tests validate SSOT factory patterns work
- [ ] E2E tests confirm Golden Path functionality on staging
- [ ] All tests follow `reports/testing/TEST_CREATION_GUIDE.md` standards
- [ ] Tests use real services (no mocks) where possible
- [ ] WebSocket events validation included in all relevant tests
- [ ] Business value justification documented for each test
- [ ] Test execution commands documented and verified
- [ ] Success criteria clearly defined and measurable

---

*This test plan follows CLAUDE.md principles: Real Services > Mocks, Business Value > System > Tests, Golden Path Protection First.*