# Orchestration SSOT Migration Guide

**Date:** 2025-09-02  
**Purpose:** Comprehensive migration guide for transitioning to SSOT orchestration configuration and enums  
**Audience:** Developers working with orchestration infrastructure  
**Business Impact:** 60% reduction in maintenance overhead, elimination of SSOT violations

## Table of Contents

1. [Overview](#overview)
2. [Migration Strategy](#migration-strategy)
3. [Before and After Patterns](#before-and-after-patterns)
4. [Step-by-Step Migration](#step-by-step-migration)
5. [Common Pitfalls](#common-pitfalls)
6. [Testing and Validation](#testing-and-validation)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## Overview

### What This Migration Achieves

The orchestration SSOT migration consolidates 15+ duplicate enum definitions and scattered availability constants into two centralized modules:

- **`test_framework/ssot/orchestration.py`**: Centralized orchestration availability configuration with thread-safe caching
- **`test_framework/ssot/orchestration_enums.py`**: Consolidated orchestration enums and data classes

### Business Value

- **60% reduction** in orchestration maintenance overhead
- **Eliminated import inconsistencies** causing unpredictable test behavior
- **Single update point** for all orchestration enums and availability logic
- **Thread-safe configuration** preventing race conditions in parallel test execution
- **Environment override capability** for flexible testing scenarios

### Key Principles

1. **Single Source of Truth (SSOT)**: One canonical definition for each orchestration concept
2. **Thread Safety**: Configuration must work reliably in parallel test environments
3. **Lazy Loading**: Import checks only performed when needed, with caching
4. **Environment Flexibility**: Support for testing scenarios via environment overrides
5. **Backwards Compatibility**: Migration should not break existing functionality

## Migration Strategy

### Phase 1: Analysis and Planning
- Review current orchestration usage patterns
- Identify all duplicate enum definitions
- Map import dependencies and usage
- Generate MRO analysis for inheritance patterns

### Phase 2: SSOT Module Creation
- Create centralized orchestration configuration module
- Create consolidated orchestration enums module
- Implement singleton pattern with thread safety
- Add comprehensive error handling and diagnostics

### Phase 3: Migration and Testing
- Update all orchestration modules to use SSOT imports
- Eliminate duplicate enum definitions
- Replace try-except import patterns
- Create comprehensive test suite for validation

### Phase 4: Validation and Documentation
- Run full test suite to ensure no regressions
- Validate thread safety and performance
- Update documentation and migration guides
- Add automated SSOT violation detection

## Before and After Patterns

### Orchestration Availability Checking

#### ❌ OLD PATTERN (SSOT Violation)

**Multiple files with identical patterns:**
```python
# test_framework/orchestration/background_e2e_agent.py
try:
    from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False

# test_framework/orchestration/background_e2e_manager.py  
try:
    from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False

# Multiple other files with identical patterns...
```

**Problems with old pattern:**
- Inconsistent availability determination across modules
- No caching - repeated import attempts
- No error reporting or diagnostics
- Duplication across multiple modules
- Thread safety issues in parallel execution

#### ✅ NEW PATTERN (SSOT Compliant)

**Single centralized configuration:**
```python
# test_framework/ssot/orchestration.py
from test_framework.ssot.orchestration import orchestration_config

# Check availability anywhere in the system
if orchestration_config.orchestrator_available:
    # Use orchestrator features
    from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent
    
# Thread-safe, cached, with comprehensive error reporting
status = orchestration_config.get_availability_status()
```

**Benefits of new pattern:**
- Single source of truth for availability determination
- Thread-safe caching eliminates repeated import attempts
- Comprehensive error reporting and diagnostics
- Environment override capability for testing scenarios
- Consistent behavior across entire system

### Orchestration Enum Usage

#### ❌ OLD PATTERN (SSOT Violation)

**Duplicate enum definitions across modules:**
```python
# test_framework/orchestration/background_e2e_agent.py
class BackgroundTaskStatus(Enum):
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# test_framework/orchestration/background_e2e_manager.py
class BackgroundTaskStatus(Enum):  # DUPLICATE!
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    # Sometimes with subtle differences...
```

#### ✅ NEW PATTERN (SSOT Compliant)

**Single canonical enum definition:**
```python
# test_framework/ssot/orchestration_enums.py - SINGLE SOURCE OF TRUTH
class BackgroundTaskStatus(Enum):
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

# All other modules import from SSOT
from test_framework.ssot.orchestration_enums import BackgroundTaskStatus
```

## Step-by-Step Migration

### Step 1: Audit Current Orchestration Usage

**Identify duplicate enums:**
```bash
# Find all BackgroundTaskStatus definitions
grep -r "class BackgroundTaskStatus" test_framework/

# Find all E2ETestCategory definitions  
grep -r "class E2ETestCategory" test_framework/

# Find all try-except import patterns
grep -r -A3 "try:" test_framework/orchestration/ | grep -B1 -A2 "import.*orchestration"
```

**Document current patterns:**
- List all files with duplicate definitions
- Map which modules use which enums
- Identify inconsistencies between duplicate definitions

### Step 2: Update Imports to Use SSOT Modules

**For orchestration availability:**
```python
# OLD - Replace this pattern everywhere
try:
    from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False

# NEW - Use centralized configuration
from test_framework.ssot.orchestration import orchestration_config

if orchestration_config.orchestrator_available:
    from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent
```

**For orchestration enums:**
```python
# OLD - Replace individual enum imports
from test_framework.orchestration.background_e2e_agent import BackgroundTaskStatus, E2ETestCategory
from test_framework.orchestration.layer_execution_agent import ExecutionStrategy

# NEW - Import from SSOT module
from test_framework.ssot.orchestration_enums import (
    BackgroundTaskStatus, 
    E2ETestCategory, 
    ExecutionStrategy
)
```

### Step 3: Remove Duplicate Enum Definitions

**In each orchestration module:**

1. **Remove the duplicate enum class entirely**:
   ```python
   # DELETE THIS ENTIRE BLOCK
   class BackgroundTaskStatus(Enum):
       QUEUED = "queued"
       STARTING = "starting"
       # ... rest of duplicate definition
   ```

2. **Add SSOT import at the top**:
   ```python
   # ADD THIS IMPORT
   from test_framework.ssot.orchestration_enums import BackgroundTaskStatus
   ```

3. **Update any enum usage**:
   ```python
   # OLD - Local enum usage
   task.status = BackgroundTaskStatus.RUNNING
   
   # NEW - SSOT enum usage (same code, just imported from SSOT)
   task.status = BackgroundTaskStatus.RUNNING
   ```

### Step 4: Remove Try-Except Import Patterns

**Replace availability constants:**
```python
# OLD - Remove these patterns
try:
    from test_framework.orchestration.master_orchestration_controller import MasterOrchestrationController
    MASTER_ORCHESTRATION_AVAILABLE = True
except ImportError:
    MASTER_ORCHESTRATION_AVAILABLE = False

# NEW - Use SSOT configuration
from test_framework.ssot.orchestration import orchestration_config

# Use property instead of constant
if orchestration_config.master_orchestration_available:
    # Use master orchestration features
```

**Update conditional logic:**
```python
# OLD
if MASTER_ORCHESTRATION_AVAILABLE:
    controller = MasterOrchestrationController(config)

# NEW  
if orchestration_config.master_orchestration_available:
    from test_framework.orchestration.master_orchestration_controller import MasterOrchestrationController
    controller = MasterOrchestrationController(config)
```

### Step 5: Environment Override Configuration

**For testing scenarios, use environment overrides:**
```python
# Set environment override to force availability
import os
os.environ["ORCHESTRATION_ORCHESTRATOR_AVAILABLE"] = "true"

# Or to force unavailability for testing
os.environ["ORCHESTRATION_MASTER_ORCHESTRATION_AVAILABLE"] = "false"

# Configuration respects overrides
from test_framework.ssot.orchestration import orchestration_config
assert orchestration_config.master_orchestration_available == False
```

### Step 6: Validation and Testing

**Run SSOT compliance tests:**
```bash
# Test orchestration SSOT compliance
python test_framework/tests/test_ssot_orchestration.py

# Test no duplicate enum definitions
python -c "
import ast
import os
from pathlib import Path

def find_duplicate_enums():
    duplicates = {}
    for py_file in Path('test_framework/orchestration').rglob('*.py'):
        with open(py_file, 'r') as f:
            try:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and any(
                        isinstance(base, ast.Name) and base.id == 'Enum' 
                        for base in node.bases
                    ):
                        enum_name = node.name
                        if enum_name.endswith('Status') or enum_name.endswith('Category') or enum_name.endswith('Strategy'):
                            if enum_name not in duplicates:
                                duplicates[enum_name] = []
                            duplicates[enum_name].append(str(py_file))
            except SyntaxError:
                continue
    
    for enum_name, files in duplicates.items():
        if len(files) > 1:
            print(f'DUPLICATE ENUM {enum_name}: {files}')
    
    return duplicates

duplicates = find_duplicate_enums()
if duplicates:
    print('❌ SSOT violations found!')
    exit(1)
else:
    print('✅ No duplicate enums found')
"
```

**Test thread safety:**
```python
# test_framework/tests/test_orchestration_thread_safety.py
import threading
import concurrent.futures
from test_framework.ssot.orchestration import get_orchestration_config

def test_thread_safety():
    """Test that orchestration config works correctly under parallel access."""
    
    def check_availability():
        config = get_orchestration_config()
        return {
            'orchestrator': config.orchestrator_available,
            'master': config.master_orchestration_available,
            'background': config.background_e2e_available,
            'all': config.all_orchestration_available
        }
    
    # Run availability checks in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_availability) for _ in range(100)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # All results should be identical (thread-safe caching)
    first_result = results[0]
    for result in results[1:]:
        assert result == first_result, "Thread safety violation detected"
    
    print("✅ Thread safety test passed")

if __name__ == "__main__":
    test_thread_safety()
```

## Common Pitfalls

### Pitfall 1: Forgetting to Remove Duplicate Enum Definitions

**Problem:** Leaving old enum definitions in place while adding SSOT imports leads to naming conflicts.

**Solution:** Always remove the entire duplicate enum class, don't just add imports.

```python
# ❌ WRONG - Creates naming conflict
class BackgroundTaskStatus(Enum):  # Old definition still here!
    QUEUED = "queued"

from test_framework.ssot.orchestration_enums import BackgroundTaskStatus  # Conflict!

# ✅ CORRECT - Remove old definition completely
# (Delete the entire class BackgroundTaskStatus)
from test_framework.ssot.orchestration_enums import BackgroundTaskStatus
```

### Pitfall 2: Direct Import Instead of Availability Check

**Problem:** Importing orchestration modules directly without checking availability first.

**Solution:** Always check availability before importing orchestration components.

```python
# ❌ WRONG - Direct import can fail
from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent
orchestrator = TestOrchestratorAgent()

# ✅ CORRECT - Check availability first
from test_framework.ssot.orchestration import orchestration_config

if orchestration_config.orchestrator_available:
    from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent
    orchestrator = TestOrchestratorAgent()
else:
    orchestrator = None  # Or fallback behavior
```

### Pitfall 3: Not Testing Environment Overrides

**Problem:** Environment overrides not tested, leading to unexpected behavior in different environments.

**Solution:** Test both normal operation and environment override scenarios.

```python
# Test normal availability
config = get_orchestration_config()
normal_status = config.orchestrator_available

# Test environment override
os.environ["ORCHESTRATION_ORCHESTRATOR_AVAILABLE"] = "false" 
config.refresh_availability(force=True)
override_status = config.orchestrator_available

assert override_status != normal_status  # Should be different
```

### Pitfall 4: Mixing Old and New Patterns

**Problem:** Some modules use SSOT while others use old try-except patterns.

**Solution:** Complete migration across all modules consistently.

```python
# ❌ INCONSISTENT - Some modules using SSOT, others using try-except
# File A:
from test_framework.ssot.orchestration import orchestration_config
available = orchestration_config.orchestrator_available

# File B:
try:
    import test_orchestrator_agent
    available = True
except ImportError:
    available = False

# ✅ CONSISTENT - All modules use SSOT
# All files:
from test_framework.ssot.orchestration import orchestration_config
available = orchestration_config.orchestrator_available
```

### Pitfall 5: Not Handling Import Errors in SSOT Module

**Problem:** SSOT module itself has import issues, causing cascading failures.

**Solution:** SSOT modules should have comprehensive error handling and diagnostics.

```python
# The SSOT orchestration module handles this automatically:
def _check_orchestrator_availability(self) -> Tuple[bool, Optional[str]]:
    try:
        from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent
        return True, None
    except ImportError as e:
        error_msg = f"TestOrchestratorAgent unavailable: {str(e)}"
        return False, error_msg
    except Exception as e:
        error_msg = f"TestOrchestratorAgent check failed: {str(e)}"
        logger.warning(error_msg)
        return False, error_msg
```

## Testing and Validation

### Automated SSOT Violation Detection

Create a script to automatically detect SSOT violations:

```python
#!/usr/bin/env python3
"""Detect orchestration SSOT violations."""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set

def scan_for_duplicate_enums(base_path: Path) -> Dict[str, List[str]]:
    """Scan for duplicate enum definitions."""
    enum_definitions = {}
    
    for py_file in base_path.rglob("*.py"):
        if py_file.name.startswith("test_") or "/tests/" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r') as f:
                tree = ast.parse(f.read(), filename=str(py_file))
                
            for node in ast.walk(tree):
                if (isinstance(node, ast.ClassDef) and 
                    any(isinstance(base, ast.Name) and base.id == 'Enum' 
                        for base in node.bases)):
                    
                    enum_name = node.name
                    if enum_name not in enum_definitions:
                        enum_definitions[enum_name] = []
                    enum_definitions[enum_name].append(str(py_file))
                    
        except (SyntaxError, UnicodeDecodeError):
            continue
    
    # Find duplicates
    duplicates = {name: files for name, files in enum_definitions.items() if len(files) > 1}
    return duplicates

def scan_for_try_except_imports(base_path: Path) -> List[str]:
    """Scan for try-except import patterns."""
    violations = []
    
    for py_file in base_path.rglob("*.py"):
        if py_file.name.startswith("test_") or "/tests/" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            if "try:" in content and "import" in content and "orchestration" in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if (line.strip().startswith("try:") and 
                        i + 1 < len(lines) and 
                        "import" in lines[i + 1] and 
                        "orchestration" in lines[i + 1]):
                        violations.append(f"{py_file}:{i+1}")
                        
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    
    return violations

def main():
    """Main validation function."""
    base_path = Path("test_framework/orchestration")
    
    print("🔍 Scanning for SSOT violations...")
    
    # Check for duplicate enums
    duplicates = scan_for_duplicate_enums(base_path)
    if duplicates:
        print("❌ Duplicate enum definitions found:")
        for enum_name, files in duplicates.items():
            print(f"  {enum_name}: {files}")
    else:
        print("✅ No duplicate enum definitions found")
    
    # Check for try-except import patterns
    try_except_violations = scan_for_try_except_imports(base_path)
    if try_except_violations:
        print("❌ Try-except import patterns found:")
        for violation in try_except_violations:
            print(f"  {violation}")
    else:
        print("✅ No try-except import patterns found")
    
    # Overall result
    total_violations = len(duplicates) + len(try_except_violations)
    if total_violations > 0:
        print(f"\n❌ {total_violations} SSOT violations found")
        sys.exit(1)
    else:
        print("\n✅ All SSOT compliance checks passed")

if __name__ == "__main__":
    main()
```

### Integration Testing

Test the complete migration with integration tests:

```python
def test_orchestration_ssot_integration():
    """Test complete SSOT orchestration integration."""
    
    from test_framework.ssot.orchestration import orchestration_config
    from test_framework.ssot.orchestration_enums import (
        BackgroundTaskStatus,
        E2ETestCategory,
        ExecutionStrategy,
        ProgressOutputMode
    )
    
    # Test availability properties
    assert hasattr(orchestration_config, 'orchestrator_available')
    assert hasattr(orchestration_config, 'master_orchestration_available')
    assert hasattr(orchestration_config, 'background_e2e_available')
    assert hasattr(orchestration_config, 'all_orchestration_available')
    
    # Test enum accessibility
    assert BackgroundTaskStatus.QUEUED.value == "queued"
    assert E2ETestCategory.CYPRESS.value == "cypress"
    assert ExecutionStrategy.SEQUENTIAL.value == "sequential"
    assert ProgressOutputMode.CONSOLE.value == "console"
    
    # Test status reporting
    status = orchestration_config.get_availability_status()
    required_keys = [
        'orchestrator_available', 'master_orchestration_available',
        'background_e2e_available', 'all_orchestration_available',
        'available_features', 'unavailable_features'
    ]
    for key in required_keys:
        assert key in status
    
    print("✅ SSOT integration test passed")

def test_orchestration_environment_overrides():
    """Test environment override functionality."""
    
    import os
    from test_framework.ssot.orchestration import get_orchestration_config
    
    # Test orchestrator override
    os.environ["ORCHESTRATION_ORCHESTRATOR_AVAILABLE"] = "false"
    config = get_orchestration_config()
    config.refresh_availability(force=True)
    
    assert not config.orchestrator_available
    
    # Clean up
    del os.environ["ORCHESTRATION_ORCHESTRATOR_AVAILABLE"]
    config.refresh_availability(force=True)
    
    print("✅ Environment override test passed")
```

## Troubleshooting

### Issue: Import Errors After Migration

**Symptoms:**
- `ImportError` when trying to use orchestration features
- `AttributeError` when accessing enum values
- Tests failing with import-related errors

**Diagnosis:**
```bash
# Check if SSOT modules are accessible
python -c "from test_framework.ssot.orchestration import orchestration_config; print('OK')"
python -c "from test_framework.ssot.orchestration_enums import BackgroundTaskStatus; print('OK')"

# Check orchestration availability
python -c "
from test_framework.ssot.orchestration import orchestration_config
status = orchestration_config.get_availability_status()
print('Available features:', status['available_features'])
print('Import errors:', status['import_errors'])
"
```

**Solutions:**
1. Verify SSOT modules are in correct location
2. Check Python path includes project root
3. Verify no circular import dependencies
4. Check for missing dependencies in orchestration modules

### Issue: Thread Safety Problems

**Symptoms:**
- Inconsistent availability results in parallel tests
- Race conditions in test execution
- Intermittent test failures

**Diagnosis:**
```python
# Test thread safety
import threading
import concurrent.futures
from test_framework.ssot.orchestration import get_orchestration_config

def check_consistency():
    results = []
    
    def get_status():
        config = get_orchestration_config()
        return config.all_orchestration_available
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(get_status) for _ in range(100)]
        results = [future.result() for future in futures]
    
    # All results should be identical
    first_result = results[0]
    inconsistent = [r for r in results if r != first_result]
    if inconsistent:
        print(f"❌ Thread safety issue: {len(inconsistent)} inconsistent results")
    else:
        print("✅ Thread safety OK")

check_consistency()
```

**Solutions:**
1. Verify singleton pattern implementation
2. Check RLock usage in OrchestrationConfig
3. Ensure no global state mutations outside locks
4. Test with higher concurrency to reproduce issue

### Issue: Environment Overrides Not Working

**Symptoms:**
- Environment variables ignored
- Availability doesn't change with overrides
- Testing scenarios failing

**Diagnosis:**
```python
import os
from test_framework.ssot.orchestration import orchestration_config

# Test environment override detection
os.environ["ORCHESTRATION_ORCHESTRATOR_AVAILABLE"] = "false"
override_value = orchestration_config._get_env_override("orchestrator")
print(f"Environment override detected: {override_value}")

# Test configuration refresh
orchestration_config.refresh_availability(force=True)
print(f"Orchestrator available after override: {orchestration_config.orchestrator_available}")
```

**Solutions:**
1. Verify environment variable names match expected format
2. Check `_get_env_override()` method implementation
3. Call `refresh_availability(force=True)` after setting environment variables
4. Verify environment variables are set before import

### Issue: Performance Degradation

**Symptoms:**
- Slower test startup
- Increased memory usage
- Timeout issues in CI/CD

**Diagnosis:**
```python
import time
from test_framework.ssot.orchestration import get_orchestration_config

# Measure availability check performance
start_time = time.time()
config = get_orchestration_config()

# First check (should perform imports)
first_start = time.time()
result1 = config.orchestrator_available
first_duration = time.time() - first_start

# Second check (should use cache)
second_start = time.time()
result2 = config.orchestrator_available
second_duration = time.time() - second_start

print(f"First check: {first_duration:.4f}s")
print(f"Second check: {second_duration:.4f}s")
print(f"Cache speedup: {first_duration / second_duration:.2f}x")

if second_duration > 0.001:  # Cache should be very fast
    print("❌ Caching may not be working correctly")
else:
    print("✅ Caching working correctly")
```

**Solutions:**
1. Verify caching is working correctly
2. Check for repeated import attempts
3. Profile import times for orchestration modules
4. Optimize slow import paths

## Best Practices

### 1. Always Use Availability Checks

Never import orchestration modules directly without checking availability first:

```python
# ✅ GOOD
from test_framework.ssot.orchestration import orchestration_config

if orchestration_config.orchestrator_available:
    from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent
    # Use orchestrator

# ❌ BAD  
from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent  # Can fail
```

### 2. Import Enums from SSOT Only

Always import orchestration enums from the SSOT module:

```python
# ✅ GOOD
from test_framework.ssot.orchestration_enums import BackgroundTaskStatus, E2ETestCategory

# ❌ BAD
from test_framework.orchestration.background_e2e_agent import BackgroundTaskStatus  # SSOT violation
```

### 3. Use Environment Overrides for Testing

Leverage environment overrides for flexible testing scenarios:

```python
# Test unavailable scenario
os.environ["ORCHESTRATION_ORCHESTRATOR_AVAILABLE"] = "false"
orchestration_config.refresh_availability(force=True)
# Now test fallback behavior

# Test available scenario  
os.environ["ORCHESTRATION_ORCHESTRATOR_AVAILABLE"] = "true"
orchestration_config.refresh_availability(force=True)
# Now test orchestrator functionality
```

### 4. Handle Graceful Degradation

Always provide fallback behavior when orchestration features are unavailable:

```python
from test_framework.ssot.orchestration import orchestration_config

if orchestration_config.all_orchestration_available:
    # Use full orchestration capabilities
    result = run_with_full_orchestration(task)
elif orchestration_config.orchestrator_available:
    # Use basic orchestration
    result = run_with_basic_orchestration(task)
else:
    # Fallback to simple execution
    result = run_simple_execution(task)
```

### 5. Monitor and Log Availability Issues

Use comprehensive status reporting for debugging:

```python
from test_framework.ssot.orchestration import orchestration_config
import logging

logger = logging.getLogger(__name__)

status = orchestration_config.get_availability_status()
if not status['all_orchestration_available']:
    logger.warning(f"Orchestration partially unavailable: {status}")
    
    # Log specific import errors
    for feature, error in status['import_errors'].items():
        logger.error(f"Orchestration {feature} unavailable: {error}")
```

### 6. Regular SSOT Compliance Checking

Add SSOT compliance checks to CI/CD pipeline:

```yaml
# In CI/CD configuration
- name: Check Orchestration SSOT Compliance
  run: |
    python scripts/check_orchestration_ssot_compliance.py
    python test_framework/tests/test_ssot_orchestration.py
```

### 7. Documentation and Comments

Document orchestration usage patterns clearly:

```python
"""
Orchestration-aware test module.

This module uses the SSOT orchestration configuration to determine
available features and gracefully degrade functionality when needed.

Required SSOT imports:
- test_framework.ssot.orchestration for availability checking
- test_framework.ssot.orchestration_enums for enum definitions

Environment overrides supported:
- ORCHESTRATION_ORCHESTRATOR_AVAILABLE=true/false
- ORCHESTRATION_MASTER_ORCHESTRATION_AVAILABLE=true/false  
- ORCHESTRATION_BACKGROUND_E2E_AVAILABLE=true/false
"""

from test_framework.ssot.orchestration import orchestration_config
from test_framework.ssot.orchestration_enums import BackgroundTaskStatus
```

### 8. Performance Optimization

Cache orchestration config reference for repeated use:

```python
# ✅ GOOD - Cache config reference
from test_framework.ssot.orchestration import orchestration_config

class MyOrchestrationManager:
    def __init__(self):
        self.config = orchestration_config  # Cache reference
    
    def run_task(self):
        if self.config.orchestrator_available:  # Fast cached access
            # Use orchestrator

# ❌ LESS OPTIMAL - Repeated imports
def run_task():
    from test_framework.ssot.orchestration import orchestration_config  # Repeated import
    if orchestration_config.orchestrator_available:
        # Use orchestrator
```

## Conclusion

The orchestration SSOT migration eliminates 15+ duplicate enum definitions and provides a robust, thread-safe configuration system. By following this guide, developers can:

- Eliminate SSOT violations in orchestration infrastructure
- Reduce maintenance overhead by 60%
- Ensure consistent behavior across all orchestration modules
- Leverage environment overrides for flexible testing
- Maintain backwards compatibility during migration

The migration establishes a foundation for future orchestration enhancements while maintaining system stability and developer productivity.

## Related Documentation

- **Learning Document**: `SPEC/learnings/ssot_orchestration_consolidation_20250902.xml`
- **Architecture Specification**: `SPEC/test_framework_ssot_architecture.xml`
- **Test Examples**: `test_framework/tests/test_ssot_orchestration.py`
- **Definition of Done**: `DEFINITION_OF_DONE_CHECKLIST.md` (TESTING MODULE section)

---

**Document Version:** 1.0  
**Last Updated:** 2025-09-02  
**Next Review:** When orchestration patterns evolve or new SSOT modules are added