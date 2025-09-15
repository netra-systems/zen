# Comprehensive Test Plan for Issue #1104: SSOT WebSocket Manager Import Path Consolidation

**Issue:** [#1104](https://github.com/netra-systems/netra-apex/issues/1104)  
**Created:** 2025-09-15  
**Priority:** HIGH - Blocks Golden Path WebSocket events  
**Business Impact:** $500K+ ARR depends on reliable WebSocket event delivery  

## Executive Summary

Based on analysis following `reports/testing/TEST_CREATION_GUIDE.md` principles, this comprehensive test plan validates SSOT WebSocket Manager import path consolidation. The tests focus on **NON-DOCKER** execution (unit, integration without docker, e2e on staging GCP) and ensure business value protection through reliable WebSocket event delivery.

## Problem Analysis

### Current Import Fragmentation
1. **Legacy Path:** `from netra_backend.app.websocket_core.websocket_manager import WebSocketManager`
2. **SSOT Path:** `from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager`

### Architecture Understanding
- `websocket_manager.py` serves as the canonical interface
- `unified_manager.py` contains the actual implementation (`_UnifiedWebSocketManagerImplementation`)
- Both paths should resolve to the same class/functionality

### Files Requiring Validation
- `/netra_backend/app/dependencies.py` (line 16) - Current: legacy import
- `/netra_backend/app/services/agent_websocket_bridge.py` (line 25) - Current: legacy import  
- `/netra_backend/app/factories/websocket_bridge_factory.py` - Current: SSOT import
- `/netra_backend/app/agents/supervisor/agent_instance_factory.py` - Current: deprecated/removed

## Test Strategy Overview

### Test Philosophy Alignment
Following TEST_CREATION_GUIDE.md principles:
- **Business Value > Real System > Tests** - All tests protect $500K+ ARR WebSocket functionality
- **Real Services > Mocks** - No mocks in integration/E2E tests
- **User Context Isolation** - Factory patterns mandatory for multi-user system
- **WebSocket Events Mission Critical** - All 5 agent events must be validated

### Test Distribution
- **20% New SSOT Tests** - Import consistency and compliance validation
- **60% Existing Test Validation** - Ensure existing tests continue working with SSOT
- **20% Consolidation Tests** - Cross-module consistency and Golden Path validation

## Test Categories

### 1. Unit Tests (`unit/`) - Import Path Validation

**Purpose:** Test pure import consistency and class identity validation  
**Infrastructure:** None required  
**Mocks:** None - testing actual imports  

#### Test Files to Create:

**A. `tests/unit/websocket_ssot/test_import_path_consistency.py`**
```python
"""
Test Import Path Consistency for Issue #1104

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: SSOT Compliance & Import Consistency  
- Value Impact: Prevents race conditions in WebSocket initialization
- Strategic Impact: Ensures reliable foundation for $500K+ ARR chat functionality
"""

import pytest
import inspect
from typing import Any

class TestWebSocketManagerImportConsistency:
    """Test that all import paths resolve to consistent classes."""
    
    def test_websocket_manager_canonical_import(self):
        """Test canonical websocket_manager import resolves correctly."""
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        assert WebSocketManager is not None
        assert hasattr(WebSocketManager, '__init__')
        
    def test_unified_manager_direct_import(self):
        """Test direct unified_manager import resolves correctly."""
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        assert UnifiedWebSocketManager is not None
        assert hasattr(UnifiedWebSocketManager, '__init__')
        
    def test_import_paths_resolve_to_same_implementation(self):
        """CRITICAL: Both import paths must resolve to same underlying implementation."""
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as CanonicalManager
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as DirectManager
        
        # Both should have identical interface
        canonical_methods = set(dir(CanonicalManager))
        direct_methods = set(dir(DirectManager))
        
        # Core WebSocket methods must be present in both
        required_methods = {
            'add_connection', 'remove_connection', 'send_message',
            'broadcast_message', 'get_connections_for_user'
        }
        
        assert required_methods.issubset(canonical_methods), "Canonical manager missing required methods"
        assert required_methods.issubset(direct_methods), "Direct manager missing required methods"
        
    def test_ssot_import_consistency_across_modules(self):
        """Test that all modules use consistent import patterns."""
        # This test will FAIL initially, proving Issue #1104 exists
        # After SSOT consolidation, it should PASS
        
        legacy_imports = []
        
        # Check dependencies.py
        try:
            from netra_backend.app import dependencies
            import inspect
            source = inspect.getsource(dependencies)
            if 'from netra_backend.app.websocket_core.websocket_manager import' in source:
                legacy_imports.append('dependencies.py')
        except Exception:
            pass
            
        # Check agent_websocket_bridge.py  
        try:
            from netra_backend.app.services import agent_websocket_bridge
            source = inspect.getsource(agent_websocket_bridge)
            if 'from netra_backend.app.websocket_core.websocket_manager import' in source:
                legacy_imports.append('agent_websocket_bridge.py')
        except Exception:
            pass
            
        # This assertion will initially FAIL (proving issue exists)
        # After SSOT consolidation, no legacy imports should remain
        assert len(legacy_imports) == 0, f"Legacy imports found in: {legacy_imports}"
```

**B. `tests/unit/websocket_ssot/test_manager_class_identity.py`**
```python
"""
Test WebSocket Manager Class Identity Consistency

Validates that WebSocket manager instances maintain consistent behavior
across different import paths and initialization patterns.
"""

import pytest
from typing import Dict, Any

class TestWebSocketManagerClassIdentity:
    """Test WebSocket manager class identity and behavior consistency."""
    
    def test_manager_instance_creation_canonical(self):
        """Test WebSocket manager creation through canonical path."""
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        assert manager is not None
        assert hasattr(manager, 'connections')
        assert isinstance(manager.connections, dict)
        
    def test_manager_instance_creation_unified(self):
        """Test WebSocket manager creation through unified path."""
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        
        manager = UnifiedWebSocketManager()
        assert manager is not None
        assert hasattr(manager, 'connections')
        assert isinstance(manager.connections, dict)
        
    def test_manager_interface_consistency(self):
        """Test that both import paths provide identical interfaces."""
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as Canonical
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as Unified
        
        canonical_instance = Canonical()
        unified_instance = Unified()
        
        # Both should have identical core methods
        core_methods = ['add_connection', 'remove_connection', 'send_message']
        
        for method in core_methods:
            assert hasattr(canonical_instance, method), f"Canonical missing {method}"
            assert hasattr(unified_instance, method), f"Unified missing {method}"
            assert callable(getattr(canonical_instance, method))
            assert callable(getattr(unified_instance, method))
            
    def test_manager_singleton_behavior_consistency(self):
        """Test that singleton behavior is consistent across import paths."""
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        # Multiple calls should return same instance (singleton pattern)
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()
        
        assert manager1 is manager2, "WebSocket manager should follow singleton pattern"
```

#### Test Files to Update:

**C. Update existing: `tests/unit/websocket_core/test_websocket_manager_ssot_violations.py`**
- Enhance to validate specific Issue #1104 import paths
- Add validation for files mentioned in issue
- Ensure test fails with current fragmentation, passes after fix

### 2. Integration Tests (`integration/`) - WebSocket Event Delivery

**Purpose:** Test WebSocket event delivery consistency through unified manager  
**Infrastructure:** Local PostgreSQL, Redis (NO Docker)  
**Mocks:** External APIs only (not WebSocket components)  

#### Test Files to Create:

**A. `tests/integration/websocket_ssot/test_websocket_event_delivery_consistency.py`**
```python
"""
Test WebSocket Event Delivery Consistency Post-SSOT

Business Value Justification (BVJ):
- Segment: All (Free -> Enterprise)  
- Business Goal: Ensure WebSocket events deliver reliably
- Value Impact: Critical for real-time chat functionality
- Strategic Impact: Protects $500K+ ARR from event delivery failures
"""

import pytest
import asyncio
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

class TestWebSocketEventDeliveryConsistency(BaseIntegrationTest):
    """Test WebSocket event delivery through SSOT manager."""
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_manager_event_delivery_canonical_path(self, real_services_fixture):
        """Test event delivery through canonical import path."""
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, get_websocket_manager
        
        manager = get_websocket_manager()
        
        # Create test connection
        connection_id = "test_conn_001"
        user_id = "test_user_001"
        
        # Mock WebSocket connection for testing
        class MockWebSocket:
            def __init__(self):
                self.messages = []
                
            async def send_text(self, message: str):
                self.messages.append(message)
                
        mock_ws = MockWebSocket()
        
        # Add connection through manager
        await manager.add_connection(connection_id, mock_ws, user_id=user_id)
        
        # Send test message  
        test_message = {
            "type": "agent_started",
            "data": {"agent": "test_agent", "message": "Test execution"}
        }
        
        await manager.send_message(user_id, test_message)
        
        # Verify message was sent
        assert len(mock_ws.messages) == 1
        assert "agent_started" in mock_ws.messages[0]
        
        # Cleanup
        await manager.remove_connection(connection_id)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_user_isolation_consistency(self, real_services_fixture):
        """Test user isolation works consistently across import paths."""
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        manager = get_websocket_manager()
        
        # Create connections for two different users
        class MockWebSocket:
            def __init__(self, user_id: str):
                self.user_id = user_id
                self.messages = []
                
            async def send_text(self, message: str):
                self.messages.append(message)
                
        user1_ws = MockWebSocket("user_001")
        user2_ws = MockWebSocket("user_002")
        
        # Add connections for both users
        await manager.add_connection("conn_user1", user1_ws, user_id="user_001")
        await manager.add_connection("conn_user2", user2_ws, user_id="user_002")
        
        # Send message to user1 only
        test_message = {
            "type": "agent_thinking", 
            "data": {"message": "Processing user1 request"}
        }
        
        await manager.send_message("user_001", test_message)
        
        # Verify isolation - only user1 should receive message
        assert len(user1_ws.messages) == 1
        assert len(user2_ws.messages) == 0
        
        # Cleanup
        await manager.remove_connection("conn_user1")
        await manager.remove_connection("conn_user2")
```

**B. `tests/integration/websocket_ssot/test_websocket_manager_initialization_race.py`**
```python
"""
Test WebSocket Manager Initialization Race Conditions

Validates that SSOT consolidation eliminates race conditions during
manager initialization across different import paths.
"""

import pytest
import asyncio
from test_framework.base_integration_test import BaseIntegrationTest

class TestWebSocketManagerInitializationRace(BaseIntegrationTest):
    """Test WebSocket manager initialization consistency."""
    
    @pytest.mark.integration
    async def test_concurrent_manager_initialization(self):
        """Test concurrent initialization doesn't create race conditions."""
        
        async def get_manager_canonical():
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            return get_websocket_manager()
            
        async def get_manager_unified():
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            return UnifiedWebSocketManager()
            
        # Run concurrent initializations
        canonical_task = asyncio.create_task(get_manager_canonical())
        unified_task = asyncio.create_task(get_manager_unified())
        
        canonical_manager, unified_manager = await asyncio.gather(canonical_task, unified_task)
        
        # Both should be valid instances
        assert canonical_manager is not None
        assert unified_manager is not None
        
        # Both should have same core functionality
        assert hasattr(canonical_manager, 'connections')
        assert hasattr(unified_manager, 'connections')
        
    @pytest.mark.integration
    async def test_factory_pattern_consistency(self):
        """Test factory pattern creates consistent managers."""
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        # Multiple factory calls should return same instance (singleton)
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()
        manager3 = get_websocket_manager()
        
        # All should be the same instance
        assert manager1 is manager2
        assert manager2 is manager3
        assert manager1 is manager3
        
        # Should have consistent state
        assert manager1.connections is manager2.connections
```

### 3. Mission Critical Tests (`mission_critical/`) - Golden Path Protection

**Purpose:** Test business-critical WebSocket functionality that MUST work  
**Infrastructure:** Full system (NO Docker - uses staging GCP)  
**Special:** Run on EVERY commit, NEVER skip  

#### Test Files to Create:

**A. `tests/mission_critical/test_websocket_ssot_golden_path_validation.py`**
```python
"""
Mission Critical: WebSocket SSOT Golden Path Validation

CRITICAL: WebSocket events enable chat value delivery!
This test MUST pass or deployment is blocked.

Business Value Protection: $500K+ ARR depends on WebSocket reliability
"""

import pytest
from tests.mission_critical.base import MissionCriticalTest

class TestWebSocketSSOTGoldenPath(MissionCriticalTest):
    """Ensure WebSocket SSOT supports Golden Path user flow."""
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip  # NEVER skip this test
    async def test_websocket_ssot_supports_all_five_critical_events(self):
        """All 5 WebSocket events MUST work through SSOT manager."""
        
        # Use actual SSOT import path
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        manager = get_websocket_manager()
        
        # Test all 5 critical events through SSOT manager
        critical_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        # Mock WebSocket for testing
        class MockWebSocket:
            def __init__(self):
                self.events_received = []
                
            async def send_text(self, message: str):
                import json
                data = json.loads(message)
                self.events_received.append(data.get('type'))
        
        mock_ws = MockWebSocket()
        user_id = "critical_test_user"
        connection_id = "critical_test_conn"
        
        # Add connection
        await manager.add_connection(connection_id, mock_ws, user_id=user_id)
        
        # Send all critical events
        for event_type in critical_events:
            test_message = {
                "type": event_type,
                "data": {"test": True, "event": event_type}
            }
            await manager.send_message(user_id, test_message)
            
        # Verify all events were delivered
        assert len(mock_ws.events_received) == 5
        for event in critical_events:
            assert event in mock_ws.events_received, f"Critical event {event} not delivered"
            
        # Cleanup
        await manager.remove_connection(connection_id)
        
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_websocket_ssot_user_isolation_security(self):
        """User isolation MUST work to prevent data leakage."""
        
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        
        manager = get_websocket_manager()
        
        # Create connections for different users
        class MockWebSocket:
            def __init__(self):
                self.messages = []
                
            async def send_text(self, message: str):
                self.messages.append(message)
        
        user1_ws = MockWebSocket()
        user2_ws = MockWebSocket()
        
        await manager.add_connection("conn1", user1_ws, user_id="user_001")
        await manager.add_connection("conn2", user2_ws, user_id="user_002")
        
        # Send sensitive message to user1
        sensitive_message = {
            "type": "agent_completed",
            "data": {"sensitive_data": "user1_private_info", "result": "confidential"}
        }
        
        await manager.send_message("user_001", sensitive_message)
        
        # CRITICAL: User2 must NOT receive user1's message
        assert len(user1_ws.messages) == 1, "User1 should receive their message"
        assert len(user2_ws.messages) == 0, "User2 must NOT receive user1's sensitive data"
        
        # Verify message content isolation
        assert "user1_private_info" in user1_ws.messages[0]
        
        # Cleanup
        await manager.remove_connection("conn1")
        await manager.remove_connection("conn2")
```

### 4. SSOT Compliance Tests - Import Registry Validation

**Purpose:** Validate SSOT compliance according to `docs/SSOT_IMPORT_REGISTRY.md`  
**Infrastructure:** None - source code analysis  

#### Test Files to Create:

**A. `tests/unit/ssot_compliance/test_websocket_import_registry_validation.py`**
```python
"""
Test WebSocket Import Registry SSOT Compliance

Validates that all WebSocket manager imports comply with SSOT registry
as documented in docs/SSOT_IMPORT_REGISTRY.md
"""

import pytest
import ast
import os
from pathlib import Path

class TestWebSocketImportRegistryCompliance:
    """Test SSOT import registry compliance for WebSocket manager."""
    
    def test_dependencies_py_uses_canonical_import(self):
        """Test dependencies.py uses canonical WebSocket manager import."""
        file_path = Path("netra_backend/app/dependencies.py")
        
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Should use canonical import
        canonical_import = "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager"
        
        # Should NOT use unified import directly  
        unified_import = "from netra_backend.app.websocket_core.unified_manager import"
        
        assert canonical_import in content, "dependencies.py must use canonical WebSocket import"
        assert unified_import not in content, "dependencies.py should not import unified_manager directly"
        
    def test_agent_websocket_bridge_uses_canonical_import(self):
        """Test agent_websocket_bridge.py uses canonical import."""
        file_path = Path("netra_backend/app/services/agent_websocket_bridge.py")
        
        with open(file_path, 'r') as f:
            content = f.read()
            
        canonical_import = "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager"
        
        assert canonical_import in content, "agent_websocket_bridge.py must use canonical WebSocket import"
        
    def test_no_legacy_imports_in_core_files(self):
        """Test that core files don't have legacy WebSocket imports."""
        
        core_files = [
            "netra_backend/app/dependencies.py",
            "netra_backend/app/services/agent_websocket_bridge.py"
        ]
        
        for file_path in core_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # These are legacy patterns that should be eliminated
                legacy_patterns = [
                    "from netra_backend.app.websockets.websocket_manager import",  # Old path
                    "from netra_backend.app.websocket.manager import",              # Alternate old path
                ]
                
                for pattern in legacy_patterns:
                    assert pattern not in content, f"Legacy import pattern found in {file_path}: {pattern}"
```

## Test Execution Strategy

### Phase 1: Validation Tests (Immediate)
```bash
# Run SSOT compliance validation
python tests/unified_test_runner.py --category unit --filter websocket_ssot

# Run integration tests (no Docker)
python tests/unified_test_runner.py --category integration --filter websocket_ssot --real-services

# Run mission critical validation
python tests/mission_critical/test_websocket_ssot_golden_path_validation.py
```

### Phase 2: Post-Fix Validation (After SSOT Consolidation)
```bash
# Full WebSocket test suite validation  
python tests/unified_test_runner.py --category all --filter websocket --real-services

# Golden Path E2E validation on staging
python tests/e2e/test_golden_path_websocket_auth_staging.py
```

### Phase 3: Regression Prevention (Ongoing)
```bash
# Add to CI/CD pipeline
python tests/mission_critical/test_websocket_ssot_golden_path_validation.py  # Must pass
python tests/unified_test_runner.py --category mission_critical --filter websocket
```

## Success Criteria

### Technical Success Criteria
1. **Import Consistency:** All WebSocket manager imports use canonical path
2. **Class Identity:** Both import paths resolve to same implementation  
3. **Event Delivery:** All 5 critical WebSocket events work consistently
4. **User Isolation:** Multi-user scenarios maintain proper isolation
5. **No Regressions:** Existing WebSocket tests continue passing

### Business Success Criteria  
1. **Golden Path Functional:** Complete user flow works end-to-end
2. **Event Reliability:** WebSocket events deliver 100% consistently
3. **Performance Maintained:** No degradation in WebSocket response times
4. **Security Preserved:** User isolation prevents data leakage
5. **Revenue Protection:** $500K+ ARR chat functionality confirmed operational

## Risk Mitigation

### Testing Risks
- **Import Caching:** Python import caching may mask issues → Use `importlib.reload()`
- **Async Race Conditions:** WebSocket tests may be flaky → Use proper `wait_for` patterns  
- **State Pollution:** Tests may interfere with each other → Implement proper cleanup

### Business Risks
- **WebSocket Downtime:** SSOT changes could break live connections → Test thoroughly before deployment
- **User Experience:** Event delivery failures impact chat → Monitor events in real-time during testing
- **Revenue Impact:** Chat failures directly impact revenue → Fail-fast with immediate rollback plan

## Implementation Notes

### Test Development Principles
1. **Test First:** Create failing tests that prove Issue #1104 exists
2. **Real Services:** No mocks in integration/E2E tests
3. **Business Value:** Every test protects specific revenue functionality  
4. **Clear Failures:** Tests should fail clearly when SSOT is broken

### Maintenance Strategy
1. **CI Integration:** Add tests to automated pipeline
2. **Documentation:** Update SSOT_IMPORT_REGISTRY.md when imports change
3. **Monitoring:** Include WebSocket SSOT checks in health monitoring
4. **Regular Audits:** Quarterly review of import patterns across codebase

---

**Note:** This test plan assumes Issue #1104 SSOT consolidation is NOT yet complete, based on current code analysis showing mixed import patterns. Tests are designed to:
1. **FAIL initially** - proving the fragmentation issue exists  
2. **PASS after SSOT consolidation** - validating the fix
3. **Prevent regressions** - ongoing protection of WebSocket reliability

The test plan prioritizes **business value protection** over technical completeness, ensuring the $500K+ ARR chat functionality remains operational throughout the SSOT consolidation process.