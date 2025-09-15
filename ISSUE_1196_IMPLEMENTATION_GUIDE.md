# Issue #1196 - SSOT Import Path Fragmentation Implementation Guide

**Generated:** 2025-09-15
**Status:** 📋 **READY FOR IMPLEMENTATION**
**Approval Required:** Yes - Do not execute until approved

---

## Phase 1: WebSocket Manager Consolidation (CRITICAL - 1,772 variations)

### Step 1.1: Create Compatibility Shim

```python
# File: /netra_backend/app/websocket_core/websocket_manager.py
# Add at the END of the file (temporary compatibility layer):

# TEMPORARY COMPATIBILITY LAYER - Remove after Phase 1 complete
# Issue #1196 - Supporting migration from 1,772 import variations
import warnings

# Alias for UnifiedWebSocketManager references
UnifiedWebSocketManager = WebSocketManager

def _deprecated_import_warning(old_path, new_path):
    warnings.warn(
        f"DEPRECATED: Import from '{old_path}' is deprecated. "
        f"Use '{new_path}' instead. This will be removed in the next sprint.",
        DeprecationWarning,
        stacklevel=2
    )

# Log deprecated import usage for tracking
import logging
_logger = logging.getLogger(__name__)
_logger.info("WebSocket Manager compatibility layer loaded for Issue #1196 migration")
```

### Step 1.2: Automated Import Replacement Commands

```bash
# Create backup of all Python files
find /Users/rindhujajohnson/Netra/GitHub/netra-apex -name "*.py" -type f -exec cp {} {}.bak1196 \;

# Fix most common WebSocket import patterns
# Pattern 1: Missing .websocket_manager
find /Users/rindhujajohnson/Netra/GitHub/netra-apex -name "*.py" -type f -exec sed -i '' \
  's/from netra_backend\.app\.websocket_core import WebSocketManager/from netra_backend.app.websocket_core.websocket_manager import WebSocketManager/g' {} \;

# Pattern 2: UnifiedWebSocketManager from unified_manager
find /Users/rindhujajohnson/Netra/GitHub/netra-apex -name "*.py" -type f -exec sed -i '' \
  's/from netra_backend\.app\.websocket_core\.unified_manager import UnifiedWebSocketManager/from netra_backend.app.websocket_core.websocket_manager import WebSocketManager/g' {} \;

# Pattern 3: Factory imports
find /Users/rindhujajohnson/Netra/GitHub/netra-apex -name "*.py" -type f -exec sed -i '' \
  's/from netra_backend\.app\.websocket_core\.factory import WebSocketManagerFactory/from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, get_websocket_manager/g' {} \;

# Pattern 4: get_websocket_manager imports
find /Users/rindhujajohnson/Netra/GitHub/netra-apex -name "*.py" -type f -exec sed -i '' \
  's/from netra_backend\.app\.websocket_core import get_websocket_manager/from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager/g' {} \;
```

### Step 1.3: Manual Review List (Complex Cases)

Files requiring manual review:
```bash
# Find files with complex WebSocket patterns
grep -r "WebSocketManager\|websocket_manager\|UnifiedWebSocketManager" \
  --include="*.py" \
  /Users/rindhujajohnson/Netra/GitHub/netra-apex | \
  grep -v "from netra_backend.app.websocket_core.websocket_manager import" | \
  cut -d: -f1 | sort -u > websocket_manual_review.txt
```

---

## Phase 2: ExecutionEngine Consolidation (97 variations)

### Step 2.1: Update Legacy Imports

```bash
# Fix ExecutionEngine imports to use UserExecutionEngine
find /Users/rindhujajohnson/Netra/GitHub/netra-apex -name "*.py" -type f -exec sed -i '' \
  's/from netra_backend\.app\.agents\.supervisor\.execution_engine import ExecutionEngine/from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine/g' {} \;

# Fix consolidated execution engine imports
find /Users/rindhujajohnson/Netra/GitHub/netra-apex -name "*.py" -type f -exec sed -i '' \
  's/from netra_backend\.app\.agents\.execution_engine_consolidated import ExecutionEngine/from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine/g' {} \;

# Fix factory imports
find /Users/rindhujajohnson/Netra/GitHub/netra-apex -name "*.py" -type f -exec sed -i '' \
  's/from netra_backend\.app\.core\.managers\.execution_engine_factory import ExecutionEngineFactory/from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory/g' {} \;
```

### Step 2.2: Create Compatibility Re-exports

```python
# File: /netra_backend/app/agents/supervisor/execution_engine.py
# Add this compatibility layer:

"""
Compatibility module for ExecutionEngine migration.
Issue #1196 - Consolidating 97 import variations to SSOT.
"""

import warnings
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

# Re-export for backward compatibility
ExecutionEngine = UserExecutionEngine

warnings.warn(
    "Importing ExecutionEngine from execution_engine.py is deprecated. "
    "Use 'from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine'",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ['ExecutionEngine']
```

---

## Phase 3: AgentRegistry Verification

### Step 3.1: Verify Issue #863 Completion

```bash
# Check for non-canonical AgentRegistry imports
grep -r "from.*AgentRegistry\|import.*AgentRegistry" \
  --include="*.py" \
  /Users/rindhujajohnson/Netra/GitHub/netra-apex | \
  grep -v "from netra_backend.app.agents.supervisor.agent_registry import" | \
  grep -v "from netra_backend.app.agents.registry import" > agent_registry_check.txt

# If any found, update them:
find /Users/rindhujajohnson/Netra/GitHub/netra-apex -name "*.py" -type f -exec sed -i '' \
  's/from netra_backend\.app\.core\.registry\.universal_registry import AgentRegistry/from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry/g' {} \;
```

---

## Phase 4: Registry Documentation Update

### Step 4.1: Fix SSOT_IMPORT_REGISTRY.md

```python
# Script to update registry documentation
cat > fix_registry.py << 'EOF'
import re

registry_file = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/docs/SSOT_IMPORT_REGISTRY.md"

with open(registry_file, 'r') as f:
    content = f.read()

# Remove broken UnifiedWebSocketManager references
content = re.sub(
    r'from netra_backend\.app\.websocket_core\.unified_manager import UnifiedWebSocketManager.*\n',
    '',
    content
)

# Update ExecutionEngine references
content = re.sub(
    r'from netra_backend\.app\.agents\.supervisor\.execution_engine import ExecutionEngine',
    'from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine',
    content
)

with open(registry_file, 'w') as f:
    f.write(content)

print("Registry documentation updated")
EOF

python fix_registry.py
```

---

## Validation Scripts

### Comprehensive Import Validation

```python
# File: /scripts/validate_import_consolidation.py

#!/usr/bin/env python3
"""
Validate SSOT import consolidation for Issue #1196
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def scan_imports(root_dir):
    """Scan all Python files for import patterns"""

    patterns = {
        'websocket': defaultdict(list),
        'execution_engine': defaultdict(list),
        'agent_registry': defaultdict(list)
    }

    websocket_regex = re.compile(r'from\s+([\w\.]+)\s+import\s+.*WebSocketManager')
    execution_regex = re.compile(r'from\s+([\w\.]+)\s+import\s+.*ExecutionEngine')
    registry_regex = re.compile(r'from\s+([\w\.]+)\s+import\s+.*AgentRegistry')

    for py_file in Path(root_dir).rglob('*.py'):
        if '.bak1196' in str(py_file):
            continue

        try:
            with open(py_file, 'r') as f:
                content = f.read()

            for match in websocket_regex.finditer(content):
                patterns['websocket'][match.group(1)].append(str(py_file))

            for match in execution_regex.finditer(content):
                patterns['execution_engine'][match.group(1)].append(str(py_file))

            for match in registry_regex.finditer(content):
                patterns['agent_registry'][match.group(1)].append(str(py_file))

        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    return patterns

def validate_consolidation(patterns):
    """Check if consolidation is successful"""

    canonical_paths = {
        'websocket': 'netra_backend.app.websocket_core.websocket_manager',
        'execution_engine': 'netra_backend.app.agents.supervisor.user_execution_engine',
        'agent_registry': 'netra_backend.app.agents.supervisor.agent_registry'
    }

    results = {}
    for component, imports in patterns.items():
        canonical = canonical_paths[component]
        total_files = sum(len(files) for files in imports.values())
        canonical_files = len(imports.get(canonical, []))

        results[component] = {
            'total_variations': len(imports),
            'total_files': total_files,
            'canonical_files': canonical_files,
            'success': len(imports) == 1 and canonical in imports,
            'non_canonical': [path for path in imports if path != canonical]
        }

    return results

def main():
    root_dir = '/Users/rindhujajohnson/Netra/GitHub/netra-apex'

    print("Scanning imports...")
    patterns = scan_imports(root_dir)

    print("\nValidating consolidation...")
    results = validate_consolidation(patterns)

    print("\n" + "="*80)
    print("SSOT IMPORT CONSOLIDATION VALIDATION REPORT")
    print("="*80)

    for component, result in results.items():
        print(f"\n{component.upper()}:")
        print(f"  Variations: {result['total_variations']}")
        print(f"  Files affected: {result['total_files']}")
        print(f"  Using canonical: {result['canonical_files']}")
        print(f"  Status: {'✅ PASS' if result['success'] else '❌ FAIL'}")

        if result['non_canonical']:
            print(f"  Non-canonical paths found:")
            for path in result['non_canonical'][:5]:
                print(f"    - {path}")
            if len(result['non_canonical']) > 5:
                print(f"    ... and {len(result['non_canonical']) - 5} more")

    # Overall status
    all_success = all(r['success'] for r in results.values())
    print("\n" + "="*80)
    print(f"OVERALL STATUS: {'✅ ALL COMPONENTS CONSOLIDATED' if all_success else '❌ CONSOLIDATION INCOMPLETE'}")
    print("="*80)

if __name__ == '__main__':
    main()
```

### Quick Validation Commands

```bash
# Count remaining WebSocket variations
echo "WebSocket variations:"
grep -r "import.*WebSocketManager" --include="*.py" . | \
  sed 's/.*from \([^ ]*\) import.*/\1/' | sort -u | wc -l

# Count remaining ExecutionEngine variations
echo "ExecutionEngine variations:"
grep -r "import.*ExecutionEngine" --include="*.py" . | \
  sed 's/.*from \([^ ]*\) import.*/\1/' | sort -u | wc -l

# Count remaining AgentRegistry variations
echo "AgentRegistry variations:"
grep -r "import.*AgentRegistry" --include="*.py" . | \
  sed 's/.*from \([^ ]*\) import.*/\1/' | sort -u | wc -l
```

---

## Test Execution After Each Phase

```bash
# After Phase 1 (WebSocket):
python tests/mission_critical/test_websocket_agent_events_suite.py
python -m pytest tests/unit/ssot/test_import_path_fragmentation_issue_1196.py::test_websocket_manager_fragmentation

# After Phase 2 (ExecutionEngine):
python -m pytest tests/unit/ssot/test_import_path_fragmentation_issue_1196.py::test_execution_engine_fragmentation

# After Phase 3 (AgentRegistry):
python -m pytest tests/unit/ssot/test_import_path_fragmentation_issue_1196.py::test_agent_registry_fragmentation

# After Phase 4 (Complete):
python -m pytest tests/unit/ssot/test_import_path_fragmentation_issue_1196.py
python -m pytest tests/integration/test_ssot_import_registry_compliance_1196.py
```

---

## Rollback Procedures

```bash
# If issues occur, rollback specific phase:

# Rollback Phase 1 (WebSocket)
find /Users/rindhujajohnson/Netra/GitHub/netra-apex -name "*.bak1196" -type f | while read backup; do
  original="${backup%.bak1196}"
  mv "$backup" "$original"
done

# Or use git to rollback
git checkout -- .
```

---

## Success Verification

After all phases complete:

```bash
# Run validation script
python scripts/validate_import_consolidation.py

# Expected output:
# WEBSOCKET: Variations: 1, Status: ✅ PASS
# EXECUTION_ENGINE: Variations: 1, Status: ✅ PASS
# AGENT_REGISTRY: Variations: 1, Status: ✅ PASS
# OVERALL STATUS: ✅ ALL COMPONENTS CONSOLIDATED
```

---

## Notes

1. **DO NOT EXECUTE** until approved
2. **Test after each phase** to ensure stability
3. **Keep backups** until fully validated
4. **Monitor logs** for deprecation warnings
5. **Remove compatibility shims** after 1 sprint

---

*Implementation guide prepared for Issue #1196 - Awaiting approval to proceed*