# Unit Test Import Remediation Plan

## Critical Issue Summary
Unit tests are failing due to **ImportError** from renamed manager classes, NOT pytest-timeout issues. The core problem is that tests are importing old class names (`UnifiedLifecycleManager`) while the actual classes have been renamed to business-focused names (`SystemLifecycle`).

## Immediate Fixes Required

### 1. 🚨 CRITICAL: Fix Primary ImportError (PRIORITY 1)

**File:** `C:\GitHub\netra-apex\netra_backend\tests\unit\core\managers\test_unified_lifecycle_manager_comprehensive.py`
**Line:** 44-50
**Issue:** Importing `UnifiedLifecycleManager` which no longer exists

**Current Import:**
```python
from netra_backend.app.core.managers.unified_lifecycle_manager import (
    UnifiedLifecycleManager,
    LifecycleManagerFactory,
    # ... other imports
)
```

**Required Fix:**
```python
from netra_backend.app.core.managers.unified_lifecycle_manager import (
    SystemLifecycle,
    SystemLifecycleFactory as LifecycleManagerFactory,  # Factory alias exists
    # ... other imports remain same (enums, etc.)
)
```

### 2. 🔴 Update All Related Test Files (PRIORITY 2)

**Files requiring UnifiedLifecycleManager → SystemLifecycle updates:**
- `C:\GitHub\netra-apex\netra_backend\tests\unit\core\managers\test_unified_lifecycle_manager_real.py`
- `C:\GitHub\netra-apex\netra_backend\tests\unit\core\managers\test_unified_lifecycle_manager_race_conditions.py` 
- `C:\GitHub\netra-apex\netra_backend\tests\unit\core\managers\test_unified_lifecycle_manager.py`
- `C:\GitHub\netra-apex\tests\ssot\test_lifecycle_manager_ssot_migration.py`
- `C:\GitHub\netra-apex\netra_backend\tests\unit\test_service_dependencies_unit.py`
- `C:\GitHub\netra-apex\tests\core\test_ssot_managers.py`

**Search and Replace Command:**
```bash
# Update all imports in one sweep
find . -name "*.py" -type f -exec sed -i 's/from.*UnifiedLifecycleManager/from netra_backend.app.core.managers.unified_lifecycle_manager import SystemLifecycle/g' {} \;
find . -name "*.py" -type f -exec sed -i 's/UnifiedLifecycleManager/SystemLifecycle/g' {} \;
```

### 3. 🟡 Add Missing Test Dependency (PREVENTIVE)

**File:** `C:\GitHub\netra-apex\requirements.txt`
**Addition:** Add after line 136:
```
# Pytest timeout plugin to prevent hanging tests
pytest-timeout>=2.4.0
```

## Comprehensive Audit Commands

### Find All Stale Imports
```bash
# Search for any remaining old manager class references
grep -r "UnifiedLifecycleManager\|UnifiedConfigurationManager\|UnifiedStateManager\|UnifiedWebSocketManager" --include="*.py" netra_backend/tests/ tests/
```

### Verify Factory Aliases
```bash
# Confirm backward compatibility aliases exist
grep -r "LifecycleManagerFactory\|ConfigurationManagerFactory\|StateManagerFactory\|WebSocketManagerFactory" --include="*.py" netra_backend/app/core/managers/
```

## Implementation Steps

### Step 1: Immediate Fix (5 minutes)
```bash
# Fix the critical import in comprehensive test
sed -i 's/UnifiedLifecycleManager/SystemLifecycle/g' netra_backend/tests/unit/core/managers/test_unified_lifecycle_manager_comprehensive.py
```

### Step 2: Bulk Update (10 minutes)
```bash
# Update all test files with old imports
find netra_backend/tests/ tests/ -name "*.py" -type f -exec sed -i 's/UnifiedLifecycleManager/SystemLifecycle/g' {} \;
find netra_backend/tests/ tests/ -name "*.py" -type f -exec sed -i 's/from.*unified_lifecycle_manager import UnifiedLifecycleManager/from netra_backend.app.core.managers.unified_lifecycle_manager import SystemLifecycle/g' {} \;
```

### Step 3: Add Dependency (2 minutes)
```bash
# Add pytest-timeout to requirements
echo "pytest-timeout>=2.4.0" >> requirements.txt
```

### Step 4: Validation (5 minutes)
```bash
# Run targeted test to verify fix
python -m pytest netra_backend/tests/unit/core/managers/test_unified_lifecycle_manager_comprehensive.py::test_basic_lifecycle -v

# Run broader unit test sweep
python tests/unified_test_runner.py --category unit --fast-fail
```

## Other Renamed Classes to Audit

Based on the business-focused naming initiative, also check for:
- `UnifiedConfigurationManager` → `PlatformConfiguration`
- `UnifiedStateManager` → `ApplicationState` 
- `UnifiedWebSocketManager` → `RealtimeCommunications`
- `DatabaseManager` → `DataAccess`

## Expected Outcome

After remediation:
- ✅ All ImportError issues resolved
- ✅ Unit tests execute without import failures
- ✅ No breaking changes to test logic (only import paths updated)
- ✅ Factory pattern backward compatibility maintained
- ✅ pytest-timeout available for future hanging test prevention

## Risk Assessment

**Low Risk Changes:**
- Import path updates (no logic changes)
- Factory aliases provide backward compatibility
- All renamed classes maintain same interfaces

**Validation Required:**
- Confirm factory aliases exist for all renamed classes
- Verify no semantic changes in class interfaces
- Run comprehensive test suite after changes

## Success Criteria

1. **Unit tests run without ImportError failures**
2. **All manager class references use new business-focused names**  
3. **Factory backward compatibility maintained**
4. **pytest-timeout available as safety net**
5. **No regression in test coverage or functionality**