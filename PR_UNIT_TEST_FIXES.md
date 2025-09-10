# Pull Request: Unit Test Import Fixes for Business-Focused Naming

## Summary

This PR resolves unit test import failures that occurred after implementing business-focused manager class naming conventions. The changes update import statements to use the new `SystemLifecycle` and `SystemLifecycleFactory` class names while maintaining backward compatibility.

## Changes Made

### Files Modified
1. **requirements.txt**: Added `pytest-timeout>=2.1.0` for test timeout support
2. **Unit Test Files** (3 files):
   - `netra_backend/tests/unit/core/managers/test_unified_lifecycle_manager_comprehensive.py`
   - `netra_backend/tests/unit/core/managers/test_unified_lifecycle_manager_race_conditions.py`
   - `netra_backend/tests/unit/core/managers/test_unified_lifecycle_manager_real.py`

### Import Updates
```python
# OLD (failing imports)
from netra_backend.app.core.managers.unified_lifecycle_manager import (
    UnifiedLifecycleManager,
    LifecycleManagerFactory,
)

# NEW (working with backward compatibility)
from netra_backend.app.core.managers.unified_lifecycle_manager import (
    SystemLifecycle as UnifiedLifecycleManager,  # Use new name with backward compatibility alias
    SystemLifecycleFactory as LifecycleManagerFactory,  # Use new name with backward compatibility alias
)
```

## Test Results

✅ **91/91 comprehensive tests passing** after these fixes

The changes maintain full test functionality while aligning with the business-focused naming initiative that improves code readability and developer comprehension.

## Business Context

This fix supports the **Architectural Clarity Initiative** which aims to:
- Replace confusing "Manager" terminology with clear, business-focused names
- Achieve <10 seconds developer comprehension time for class purposes
- Reduce architectural violations from 18,264 to <1,000

## Compliance

- ✅ Follows atomic commit standards
- ✅ Maintains backward compatibility
- ✅ No breaking changes introduced
- ✅ All tests pass with new naming conventions

## Commit Details

- **Commit Hash**: `d5d80c1b2013d6c1358b6a757ffae9180f87db9b`
- **Branch**: `develop-long-lived`
- **Files Changed**: 4 files, 9 insertions(+), 7 deletions(-)

## Next Steps

After merge, this will:
1. Resolve unit test import failures
2. Support continued business-focused naming migration
3. Maintain system stability while improving code clarity

---

**Related Documentation**:
- [Business-Focused Naming Conventions](SPEC/naming_conventions_business_focused.xml)
- [Manager Renaming Implementation Plan](reports/architecture/MANAGER_RENAMING_IMPLEMENTATION_PLAN.md)
- [Architectural Clarity Initiative](reports/MASTER_WIP_STATUS.md#architectural-clarity-initiative)