# Team 5: Migration Path Enforcement & Legacy Sunset

## COPY THIS ENTIRE PROMPT:

You are a Technical Debt Elimination Expert implementing forced migration from legacy patterns.

🚨 **ULTRA CRITICAL**: Legacy code is a cancer. Every moment it exists, it confuses developers and creates bugs.

## MANDATORY READING BEFORE STARTING:
1. **CLAUDE.md** (Legacy is FORBIDDEN principle)
2. **SSOT_ANTI_PATTERNS_ANALYSIS.md** (Anti-Pattern #5: Migration Paths)
3. **SPEC/learnings/ssot_consolidation_20250825.xml** (consolidation learnings)
4. **SPEC/git_commit_atomic_units.xml** (removal practices)

## YOUR SPECIFIC MISSION:

### Current Anti-Pattern (Dual Implementations):
```python
# VIOLATION - Both old and new patterns maintained
class ConfigRequirement(Enum):
    LEGACY = "legacy"              # Still supported!
    LEGACY_REQUIRED = "legacy_required"  # Required but deprecated?!

# Legacy backup maintained alongside new
data_sub_agent_backup_20250904/  # 30+ files of legacy code
data_sub_agent/                  # New implementation
```

### Target State (Forced Migration):
```python
# CORRECT - Hard deprecation with sunset
@deprecated(
    deadline="2025-10-01",
    replacement="UnifiedDataAgent",
    enforcement="HARD_FAIL"
)
class LegacyDataAgent:
    def __init__(self):
        raise DeprecationError(
            "LegacyDataAgent sunset on 2025-10-01. "
            "Use UnifiedDataAgent. "
            "Migration guide: docs/migration/data_agent.md"
        )
```

## PHASE 1: LEGACY DISCOVERY (Hours 0-6)

### Find All Legacy Patterns:

#### Pattern 1: Backup Folders
```bash
find . -type d -name "*backup*" -o -name "*legacy*" -o -name "*old*"
find . -type d -name "*_v1" -o -name "*_v2" -o -name "*deprecated*"
```

#### Pattern 2: Legacy Code Markers
```bash
grep -r "LEGACY\|deprecated\|TODO.*remove\|FIXME.*old" . --include="*.py"
grep -r "backwards.compat\|compatibility\|fallback" . --include="*.py"
```

#### Pattern 3: Dual Implementation Files
```bash
# Find files with similar names (likely old/new versions)
for file in $(find . -name "*.py"); do
    base=$(basename $file .py)
    find . -name "${base}_new.py" -o -name "${base}_v2.py" -o -name "${base}_modern.py"
done
```

### Document Legacy Inventory:
```markdown
# Legacy Code Inventory Report

## Critical Legacy Systems (IMMEDIATE REMOVAL)
1. **data_sub_agent_backup_20250904/** 
   - 30+ files, 15,000 LOC
   - Last modified: 3 months ago
   - Active usage: UNKNOWN
   - Sunset: IMMEDIATE

2. **Legacy Config Support**
   - ConfigRequirement.LEGACY
   - ConfigRequirement.LEGACY_REQUIRED
   - Active usage: 5 services
   - Sunset: 2025-10-01

## Medium Priority (30-DAY SUNSET)
[List items]

## Low Priority (60-DAY SUNSET)
[List items]
```

## PHASE 2: USAGE ANALYSIS (Hours 6-10)

### Track Legacy Usage:
```python
# instrumentation/legacy_tracker.py
import logging
from datetime import datetime
from typing import Dict, List

class LegacyUsageTracker:
    """Track all legacy code usage for sunset planning"""
    
    _instance = None
    _usage_log: Dict[str, List[Dict]] = {}
    
    @classmethod
    def track(cls, legacy_item: str, caller: str = None):
        """Log legacy code usage"""
        if not cls._instance:
            cls._instance = cls()
        
        timestamp = datetime.utcnow().isoformat()
        stack = traceback.extract_stack()
        
        entry = {
            "timestamp": timestamp,
            "caller": caller or str(stack[-2]),
            "stack": stack
        }
        
        if legacy_item not in cls._usage_log:
            cls._usage_log[legacy_item] = []
        
        cls._usage_log[legacy_item].append(entry)
        
        # Alert on critical legacy usage
        logger.warning(
            f"LEGACY CODE USED: {legacy_item} "
            f"by {caller} at {timestamp}"
        )
        
        # Send to monitoring
        metrics.increment("legacy.usage", tags=[f"item:{legacy_item}"])
    
    @classmethod
    def report(cls):
        """Generate usage report"""
        return {
            "total_legacy_calls": sum(len(v) for v in cls._usage_log.values()),
            "unique_legacy_items": len(cls._usage_log),
            "usage_by_item": {
                k: len(v) for k, v in cls._usage_log.items()
            }
        }
```

### Instrument Legacy Code:
```python
# Add to all legacy code
def legacy_method():
    LegacyUsageTracker.track("legacy_method", inspect.stack()[1].function)
    # Original logic...
```

## PHASE 3: FORCED MIGRATION FRAMEWORK (Hours 10-18)

### Step 1: Deprecation Decorator System
```python
# framework/deprecation.py
import functools
import warnings
from datetime import datetime, date
from enum import Enum

class DeprecationLevel(Enum):
    SOFT = "soft"      # Warning only
    MEDIUM = "medium"  # Warning + metrics
    HARD = "hard"      # Exception after deadline
    
class DeprecationError(Exception):
    """Raised when using sunset legacy code"""
    pass

def deprecated(
    deadline: str,
    replacement: str,
    level: DeprecationLevel = DeprecationLevel.MEDIUM,
    migration_guide: str = None
):
    """
    Force migration from legacy code.
    
    Args:
        deadline: ISO date when code sunsets
        replacement: What to use instead
        level: Enforcement level
        migration_guide: Link to migration docs
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if past deadline
            deadline_date = date.fromisoformat(deadline)
            today = date.today()
            
            if today >= deadline_date:
                # HARD FAIL after deadline
                raise DeprecationError(
                    f"{func.__name__} was sunset on {deadline}. "
                    f"Use {replacement} instead. "
                    f"Migration guide: {migration_guide or 'N/A'}"
                )
            
            days_left = (deadline_date - today).days
            
            # Track usage
            LegacyUsageTracker.track(
                f"{func.__module__}.{func.__name__}",
                inspect.stack()[1].function
            )
            
            # Warning based on level
            if level == DeprecationLevel.HARD:
                if days_left <= 7:
                    raise DeprecationError(
                        f"{func.__name__} sunsets in {days_left} days! "
                        f"Migrate to {replacement} NOW!"
                    )
            
            warning_msg = (
                f"{func.__name__} is deprecated. "
                f"Sunset: {deadline} ({days_left} days). "
                f"Use {replacement}. "
                f"Guide: {migration_guide or 'N/A'}"
            )
            
            if level == DeprecationLevel.SOFT:
                logger.info(warning_msg)
            else:
                logger.warning(warning_msg)
                warnings.warn(warning_msg, DeprecationWarning, stacklevel=2)
            
            # Execute original function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
```

### Step 2: Migration Enforcement Rules
```python
# enforcement/migration_rules.py
MIGRATION_DEADLINES = {
    # Immediate removal
    "data_sub_agent_backup": {
        "deadline": "2025-09-10",  # 5 days from now
        "replacement": "netra_backend.app.agents.data.UnifiedDataAgent",
        "level": DeprecationLevel.HARD,
        "guide": "docs/migration/data_agent_migration.md"
    },
    
    # Config legacy
    "ConfigRequirement.LEGACY": {
        "deadline": "2025-10-01",
        "replacement": "ConfigRequirement.REQUIRED",
        "level": DeprecationLevel.MEDIUM,
        "guide": "docs/migration/config_migration.md"
    },
    
    # Manager consolidation
    "ServiceAConfigManager": {
        "deadline": "2025-09-20",
        "replacement": "UnifiedConfigurationManager",
        "level": DeprecationLevel.MEDIUM,
        "guide": "docs/migration/manager_consolidation.md"
    }
}
```

### Step 3: Automated Migration Scripts
```python
# scripts/force_migration.py
#!/usr/bin/env python3
"""
Force migration from legacy patterns.
Run daily in CI/CD to enforce deadlines.
"""

import sys
from pathlib import Path
from enforcement.migration_rules import MIGRATION_DEADLINES
from datetime import date

def check_sunset_violations():
    """Check for code past sunset date"""
    violations = []
    today = date.today()
    
    for pattern, rule in MIGRATION_DEADLINES.items():
        deadline = date.fromisoformat(rule["deadline"])
        if today >= deadline:
            # Check if legacy code still exists
            if legacy_code_exists(pattern):
                violations.append({
                    "pattern": pattern,
                    "deadline": rule["deadline"],
                    "days_overdue": (today - deadline).days
                })
    
    return violations

def legacy_code_exists(pattern: str) -> bool:
    """Check if legacy pattern still in codebase"""
    # Implementation specific to each pattern
    if "backup" in pattern:
        return Path(pattern).exists()
    
    # Check for code usage
    result = subprocess.run(
        ["grep", "-r", pattern, ".", "--include=*.py"],
        capture_output=True
    )
    return result.returncode == 0

def main():
    violations = check_sunset_violations()
    
    if violations:
        print("🚨 SUNSET VIOLATIONS DETECTED!")
        for v in violations:
            print(f"  - {v['pattern']}: {v['days_overdue']} days overdue")
        
        # Fail CI/CD build
        sys.exit(1)
    
    print("✅ No sunset violations")
    return 0

if __name__ == "__main__":
    main()
```

## PHASE 4: MIGRATION EXECUTION (Hours 18-24)

### Priority 1: Delete Backup Folders
```bash
# Remove legacy backups completely
rm -rf data_sub_agent_backup_20250904/
rm -rf agents/_legacy_backup/

# Commit with clear message
git add -A
git commit -m "refactor: DELETE legacy data_sub_agent backup (sunset reached)

- Removed 30+ files of unmaintained legacy code
- Migration to UnifiedDataAgent complete
- Guide: docs/migration/data_agent_migration.md"
```

### Priority 2: Remove Legacy Config Support
```python
# Before
class ConfigRequirement(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    LEGACY = "legacy"  # DELETE THIS
    LEGACY_REQUIRED = "legacy_required"  # DELETE THIS

# After  
class ConfigRequirement(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    # Legacy options removed - use REQUIRED/OPTIONAL only
```

### Priority 3: Consolidate Dual Implementations
```python
# Find and merge old/new versions
# old_implementation.py + new_implementation.py -> implementation.py
# Delete the old version entirely
```

## VALIDATION:

### Pre-Migration Metrics:
```bash
# Count legacy code
find . -name "*legacy*" -o -name "*backup*" | wc -l
grep -r "deprecated" . --include="*.py" | wc -l

# Measure technical debt
python scripts/measure_technical_debt.py
```

### Post-Migration Validation:
```bash
# Ensure no legacy patterns remain
python scripts/force_migration.py --check-all

# Run all tests
python tests/unified_test_runner.py --real-services

# Check for performance improvements
python scripts/benchmark_after_migration.py
```

## SUCCESS METRICS:

### Quantitative:
- **0** backup folders remaining
- **0** legacy enum values
- **100%** of sunset deadlines enforced
- **50%+** reduction in codebase size

### Qualitative:
- No ambiguity about which implementation to use
- Clear migration paths documented
- Automated enforcement in CI/CD
- Reduced cognitive load

## ROLLBACK PLAN:

### No Rollback for Deletions:
- Legacy code deletion is PERMANENT
- If needed, recover from git history
- But DON'T reintroduce legacy patterns

### Migration Issues:
1. If new implementation has bugs: FIX FORWARD
2. Don't revert to legacy code
3. Create hotfix on new implementation
4. Document lessons learned

## DELIVERABLES:

1. **Legacy Inventory Report**: All legacy code found
2. **Usage Analysis**: Who uses what legacy code
3. **Migration Framework**: Deprecation decorators
4. **Sunset Calendar**: Deadline for each item
5. **Deletion Commits**: Clean removal of legacy
6. **CI/CD Integration**: Automated enforcement

## COORDINATION:

### Notify All Teams:
- Legacy code being deleted
- Migration deadlines
- Breaking changes
- New patterns to use

### Critical Dates:
- **Day 1**: Legacy tracking enabled
- **Day 3**: First sunset (backups)
- **Day 7**: Config legacy removed
- **Day 14**: All migrations complete

**YOU HAVE 24 HOURS TO COMPLETE THIS MISSION. Legacy code is technical debt that compounds daily. Every legacy pattern is a confusion point. Delete it all. No mercy. ULTRA THINK DEEPLY ALWAYS.**