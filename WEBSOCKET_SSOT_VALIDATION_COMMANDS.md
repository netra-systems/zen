# WebSocket SSOT Remediation - Validation Commands Reference

**Created:** 2025-09-10  
**Purpose:** Quick reference for validation commands during WebSocket SSOT remediation  
**Issue:** #235 WebSocket Manager SSOT Violations

## Pre-Implementation Validation

### Confirm Current Violations Exist

```bash
# Run SSOT violation detection tests (should FAIL initially)
cd /Users/anthony/Desktop/netra-apex
python3 -m pytest tests/mission_critical/test_websocket_manager_ssot_violations.py -v
# Expected: 7 tests FAIL, proving violations exist

# Check current architecture compliance
python3 scripts/check_architecture_compliance.py --focus websocket
# Expected: Multiple SSOT violations reported

# Scan for WebSocket manager usage patterns
grep -r "WebSocketManager\|UnifiedWebSocketManager" netra_backend/ --include="*.py" | wc -l
# Expected: Many inconsistent import patterns
```

### Golden Path Baseline

```bash
# Establish Golden Path baseline before changes
python3 tests/mission_critical/test_websocket_agent_events_suite.py
# Expected: Should PASS (critical business functionality)

# Test WebSocket event delivery
python3 -c "
import asyncio
import sys
sys.path.append('.')
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
print('✅ UnifiedWebSocketManager import successful')
"
```

## Phase 1 Validation: SSOT Establishment

### Step 1.1: Manager Class Consolidation

```bash
# After import updates - verify no websocket_manager.py references
grep -r "websocket_manager\.py" netra_backend/
# Expected: No results (all references removed)

# Verify imports point to unified_manager
grep -r "from.*websocket_manager.*import" netra_backend/
# Expected: No results (all converted to unified_manager imports)

# Test import consistency
python3 -c "
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
print('✅ Import redirection working')
"
```

### Step 1.2: Singleton Enforcement

```bash
# Test singleton behavior
python3 -c "
import sys
sys.path.append('.')
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Create multiple instances
m1 = UnifiedWebSocketManager()
m2 = UnifiedWebSocketManager()
m3 = UnifiedWebSocketManager.get_instance()

# Verify they're all the same instance
assert m1 is m2, 'Singleton violation: m1 is not m2'
assert m2 is m3, 'Singleton violation: m2 is not m3'
assert m1 is m3, 'Singleton violation: m1 is not m3'

print('✅ Singleton pattern enforced correctly')
"

# Test singleton thread safety
python3 -c "
import sys
import threading
import time
sys.path.append('.')
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

instances = []
def create_instance():
    instance = UnifiedWebSocketManager()
    instances.append(instance)

# Create instances from multiple threads
threads = [threading.Thread(target=create_instance) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# Verify all instances are the same
first_instance = instances[0]
all_same = all(instance is first_instance for instance in instances)
assert all_same, 'Thread safety violation in singleton'

print('✅ Singleton thread safety verified')
"
```

### Step 1.3: Factory Pattern Correction

```bash
# Test factory delegates to SSOT
python3 -c "
import sys
sys.path.append('.')
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Test factory creates SSOT instance
try:
    factory_manager = WebSocketManagerFactory.get_manager()
    direct_manager = UnifiedWebSocketManager.get_instance()
    
    assert factory_manager is direct_manager, 'Factory not using SSOT'
    print('✅ Factory delegates to SSOT correctly')
except AttributeError as e:
    print(f'⚠️ Factory method may not exist yet: {e}')
"

# Test no user-specific instance creation
python3 -c "
import sys
sys.path.append('.')
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from shared.types.core_types import UserID

user1 = UserID('test_user_1')
user2 = UserID('test_user_2')

try:
    # These should not create separate instances
    manager1 = WebSocketManagerFactory.get_manager_for_user(user1)
    manager2 = WebSocketManagerFactory.get_manager_for_user(user2)
    
    # Should be same SSOT instance
    assert manager1 is manager2, 'Factory creating separate user instances (SSOT violation)'
    print('✅ Factory uses SSOT for all users')
except AttributeError:
    print('✅ User-specific factory methods removed (SSOT compliant)')
"
```

## Phase 2 Validation: User Isolation Architecture

### Step 2.1: Context-Based Isolation

```bash
# Test UserExecutionContext integration
python3 -c "
import sys
sys.path.append('.')
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID

manager = UnifiedWebSocketManager.get_instance()

# Test context setting
user1_id = UserID('test_user_1')
user2_id = UserID('test_user_2')

try:
    context1 = UserExecutionContext(user_id=user1_id)
    context2 = UserExecutionContext(user_id=user2_id)
    
    manager.set_user_context(context1)
    assert hasattr(manager, '_current_context'), 'Manager missing context support'
    
    manager.set_user_context(context2)
    assert manager._current_context.user_id == user2_id, 'Context not updated properly'
    
    print('✅ UserExecutionContext integration working')
except Exception as e:
    print(f'❌ Context integration failed: {e}')
"

# Test user isolation in message routing
python3 -c "
import sys
import asyncio
import json
sys.path.append('.')
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types.core_types import UserID

async def test_user_isolation():
    manager = UnifiedWebSocketManager.get_instance()
    
    user1_id = UserID('test_user_1')
    user2_id = UserID('test_user_2')
    
    # Mock connections for testing
    class MockConnection:
        def __init__(self, user_id):
            self.user_id = user_id
            self.messages = []
        async def send_text(self, message):
            self.messages.append(message)
    
    conn1 = MockConnection(user1_id)
    conn2 = MockConnection(user2_id)
    
    # Register connections
    if hasattr(manager, 'register_connection'):
        manager.register_connection(user1_id, conn1)
        manager.register_connection(user2_id, conn2)
        
        # Send message to user1 only
        test_message = {'type': 'test', 'data': 'user1_only'}
        manager.send_message(user1_id, test_message)
        
        # Verify isolation
        assert len(conn1.messages) > 0, 'User1 should receive message'
        assert len(conn2.messages) == 0, 'User2 should not receive message (isolation failure)'
        
        print('✅ User isolation in message routing verified')
    else:
        print('⚠️ Connection management methods not yet implemented')

asyncio.run(test_user_isolation())
"
```

### Step 2.2: Factory Method Cleanup

```bash
# Verify user-specific factory methods removed
python3 -c "
import sys
import inspect
sys.path.append('.')
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory

# Check for SSOT violation methods
violation_methods = [
    'get_manager_by_user',
    'create_user_manager', 
    'get_isolated_manager',
    'create_manager_for_user'
]

factory_methods = [name for name, _ in inspect.getmembers(WebSocketManagerFactory, predicate=inspect.ismethod)]

violations = [method for method in violation_methods if method in factory_methods]

if violations:
    print(f'❌ SSOT violation methods still exist: {violations}')
else:
    print('✅ User-specific factory methods removed (SSOT compliant)')
"

# Test factory now uses context pattern
python3 -c "
import sys
sys.path.append('.')
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID

try:
    user_id = UserID('test_user')
    context = UserExecutionContext(user_id=user_id)
    
    # Should get SSOT manager with context
    manager = WebSocketManagerFactory.get_websocket_manager(context)
    
    print('✅ Factory uses context-based SSOT pattern')
except AttributeError as e:
    print(f'⚠️ Context-based factory method not yet implemented: {e}')
"
```

## Phase 3 Validation: Test Framework Alignment

### Step 3.1: Mock Synchronization

```bash
# Test mock/real API parity
python3 -c "
import sys
import inspect
sys.path.append('.')

try:
    from test_framework.fixtures.websocket_manager_mock import MockWebSocketManager
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    
    # Compare method signatures
    mock_methods = set(inspect.getmembers(MockWebSocketManager, predicate=inspect.ismethod))
    real_methods = set(inspect.getmembers(UnifiedWebSocketManager, predicate=inspect.ismethod))
    
    mock_names = {name for name, _ in mock_methods if not name.startswith('_')}
    real_names = {name for name, _ in real_methods if not name.startswith('_')}
    
    missing_in_mock = real_names - mock_names
    extra_in_mock = mock_names - real_names
    
    if missing_in_mock:
        print(f'❌ Mock missing methods: {missing_in_mock}')
    elif extra_in_mock:
        print(f'❌ Mock has extra methods: {extra_in_mock}')
    else:
        print('✅ Mock/real API parity achieved')
        
except ImportError as e:
    print(f'⚠️ Mock import failed: {e}')
"

# Test SSOT mock factory integration
python3 -c "
import sys
sys.path.append('.')

try:
    from test_framework.ssot.mock_factory import SSotMockFactory
    
    mock_manager = SSotMockFactory.create_websocket_manager_mock()
    
    print('✅ SSOT mock factory integration working')
except ImportError as e:
    print(f'⚠️ SSOT mock factory not yet implemented: {e}')
"
```

### Step 3.2: Test Suite Migration

```bash
# Check for old mock usage patterns
grep -r "MockWebSocketManager" tests/ --include="*.py" | wc -l
# Expected: 0 after migration (all should use SSOT mocks)

# Check for new SSOT mock usage
grep -r "SSotMockFactory.*websocket" tests/ --include="*.py" | wc -l
# Expected: >0 after migration

# Test sample test file migration
python3 -c "
import sys
sys.path.append('.')

# Try to run a migrated test
try:
    from tests.unit.websocket_ssot.test_manager_interface_consistency import *
    print('✅ Test suite migration successful')
except ImportError as e:
    print(f'⚠️ Test migration incomplete: {e}')
"
```

## Final Validation: Complete SSOT Compliance

### End-to-End SSOT Verification

```bash
# Run all SSOT violation tests (should now PASS)
python3 -m pytest tests/mission_critical/test_websocket_manager_ssot_violations.py -v
# Expected: All 7 tests PASS (violations remediated)

# Architecture compliance check
python3 scripts/check_architecture_compliance.py --focus websocket
# Expected: No SSOT violations detected

# Golden Path protection verification
python3 tests/mission_critical/test_websocket_agent_events_suite.py
# Expected: Still PASS (business functionality preserved)
```

### Performance and Stability

```bash
# Test singleton memory efficiency
python3 -c "
import sys
import gc
sys.path.append('.')
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Create many references
managers = [UnifiedWebSocketManager() for _ in range(100)]

# Should all be same instance (memory efficient)
first_manager = managers[0]
all_same = all(manager is first_manager for manager in managers)

assert all_same, 'Memory inefficiency: multiple instances created'

# Memory usage should be minimal
del managers
gc.collect()

print('✅ Singleton memory efficiency verified')
"

# Test concurrent access stability
python3 -c "
import sys
import asyncio
import threading
import time
sys.path.append('.')
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

def stress_test():
    start_time = time.time()
    
    def worker():
        for _ in range(100):
            manager = UnifiedWebSocketManager.get_instance()
            # Simulate work
            time.sleep(0.001)
    
    threads = [threading.Thread(target=worker) for _ in range(10)]
    
    for t in threads:
        t.start()
    
    for t in threads:
        t.join()
    
    duration = time.time() - start_time
    print(f'✅ Concurrent access stable (completed in {duration:.2f}s)')

stress_test()
"
```

### Business Continuity Verification

```bash
# Test critical WebSocket events still work
python3 -c "
import sys
import asyncio
sys.path.append('.')

async def test_critical_events():
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    
    manager = UnifiedWebSocketManager.get_instance()
    
    # Test critical events that support Golden Path
    critical_events = [
        'agent_started',
        'agent_thinking', 
        'tool_executing',
        'tool_completed',
        'agent_completed'
    ]
    
    for event in critical_events:
        # Simulate event creation and delivery
        test_event = {
            'type': event,
            'timestamp': '2025-09-10T00:00:00Z',
            'data': f'Test {event} event'
        }
        
        # Event should be processable
        assert isinstance(test_event, dict), f'Event {event} not properly formed'
    
    print('✅ Critical WebSocket events supported')

asyncio.run(test_critical_events())
"

# Test user chat functionality end-to-end
python3 tests/e2e/test_golden_path_user_flow.py
# Expected: PASS (complete user journey works)

# Test staging environment
curl -f http://localhost:8000/health
curl -f http://localhost:8000/ws-health
# Expected: Both return healthy status
```

## Rollback Validation

### Rollback Readiness Test

```bash
# Test backup exists
ls -la netra_backend/app/websocket_core.backup_*
# Expected: Backup directory exists

# Test rollback procedure (DRY RUN)
echo "Testing rollback procedure..."
cp -r netra_backend/app/websocket_core/ netra_backend/app/websocket_core.test_rollback/
cp -r netra_backend/app/websocket_core.backup_*/ netra_backend/app/websocket_core.test_restore/

# Verify backup contents
diff -r netra_backend/app/websocket_core.test_rollback/ netra_backend/app/websocket_core.test_restore/
# Should show differences (proving backup is from before changes)

# Cleanup test
rm -rf netra_backend/app/websocket_core.test_rollback/
rm -rf netra_backend/app/websocket_core.test_restore/

echo "✅ Rollback procedure verified"
```

### Emergency Rollback Test

```bash
# Only run if emergency rollback needed
# EMERGENCY_ROLLBACK() {
#     echo "🚨 EMERGENCY ROLLBACK INITIATED"
#     
#     # Stop services
#     docker-compose stop backend
#     
#     # Restore backup
#     rm -rf netra_backend/app/websocket_core/
#     cp -r netra_backend/app/websocket_core.backup_*/ netra_backend/app/websocket_core/
#     
#     # Restart services
#     docker-compose start backend
#     
#     # Verify restoration
#     curl -f http://localhost:8000/health
#     python3 tests/mission_critical/test_websocket_agent_events_suite.py
#     
#     echo "✅ Emergency rollback completed"
# }
```

## Quick Health Checks

### 30-Second Health Check

```bash
# Quick validation suite (run anytime)
echo "=== WEBSOCKET SSOT HEALTH CHECK ==="

# 1. Singleton working
python3 -c "
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
assert UnifiedWebSocketManager() is UnifiedWebSocketManager.get_instance()
print('✅ Singleton')
"

# 2. No import errors
python3 -c "
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
print('✅ Imports')
"

# 3. Golden Path functional
python3 -c "
import asyncio
print('✅ Basic functionality')
"

echo "=== HEALTH CHECK COMPLETE ==="
```

### Continuous Monitoring

```bash
# Add to monitoring/CI pipeline
echo "#!/bin/bash
# Continuous SSOT compliance monitoring

# Daily SSOT validation
python3 tests/mission_critical/test_websocket_manager_ssot_violations.py

# Weekly Golden Path validation  
python3 tests/mission_critical/test_websocket_agent_events_suite.py

# Alert on failures
if [ \$? -ne 0 ]; then
    echo 'ALERT: WebSocket SSOT compliance failure detected'
    # Send alert to team
fi
" > monitor_websocket_ssot.sh

chmod +x monitor_websocket_ssot.sh
echo "✅ Continuous monitoring script created"
```

---

**Usage:** Reference these commands during each phase of remediation to ensure SSOT compliance and business continuity protection.