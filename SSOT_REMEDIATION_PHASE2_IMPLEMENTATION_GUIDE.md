# SSOT REMEDIATION PHASE 2: TEST INFRASTRUCTURE VIOLATIONS REMEDIATION

> **Issue:** #1076 | **Phase:** 2 of 4 | **Duration:** 4-8 Hours | **Priority:** HIGH
>
> **Objective:** Systematically eliminate test infrastructure SSOT violations while maintaining Golden Path protection and system stability.

---

## 🎯 PHASE 2 OBJECTIVES

1. **Mock Duplication Cleanup:** Consolidate duplicate mock implementations to SSotMockFactory
2. **Import Path Consistency:** Standardize SSOT import patterns and remove legacy fallbacks
3. **Test Configuration Cleanup:** Enforce IsolatedEnvironment usage and remove direct os.environ access
4. **Maintain Zero Regressions:** Ensure all changes preserve production system functionality

---

## 📋 SYSTEMATIC REMEDIATION APPROACH

### **Pre-Phase 2 Validation** (10 minutes)
```bash
# Confirm Phase 1 completion and baseline establishment
test -f compliance_baseline_report.txt || { echo "ERROR: Phase 1 baseline missing"; exit 1; }
test -f remediation_risk_assessment.md || { echo "ERROR: Risk assessment missing"; exit 1; }

# Verify Golden Path still protected
python tests/mission_critical/test_websocket_agent_events_suite.py || { echo "ERROR: Golden Path compromised"; exit 1; }

echo "✅ Phase 2 prerequisites validated"
```

---

## 🔧 STEP 2.1: MOCK DUPLICATION CLEANUP (2-3 Hours)

### **Step 2.1.1: Mock Implementation Audit** (30 minutes)

#### Action: Identify All Mock Duplications
```bash
# Create audit directory
mkdir -p reports/ssot_remediation/phase2/mock_audit

# Find all mock implementations
echo "=== AGENT MOCKS ===" > reports/ssot_remediation/phase2/mock_audit/mock_inventory.txt
grep -r "class Mock.*Agent" tests/ --include="*.py" -n >> reports/ssot_remediation/phase2/mock_audit/mock_inventory.txt

echo -e "\n=== MANAGER MOCKS ===" >> reports/ssot_remediation/phase2/mock_audit/mock_inventory.txt
grep -r "class Mock.*Manager" tests/ --include="*.py" -n >> reports/ssot_remediation/phase2/mock_audit/mock_inventory.txt

echo -e "\n=== WEBSOCKET MOCKS ===" >> reports/ssot_remediation/phase2/mock_audit/mock_inventory.txt
grep -r "class Mock.*WebSocket" tests/ --include="*.py" -n >> reports/ssot_remediation/phase2/mock_audit/mock_inventory.txt

echo -e "\n=== SERVICE MOCKS ===" >> reports/ssot_remediation/phase2/mock_audit/mock_inventory.txt
grep -r "class Mock.*Service" tests/ --include="*.py" -n >> reports/ssot_remediation/phase2/mock_audit/mock_inventory.txt

# Display audit results
cat reports/ssot_remediation/phase2/mock_audit/mock_inventory.txt
```

#### Action: Categorize Mock Duplications
```bash
# Create categorization script
cat > scripts/ssot_remediation/categorize_mocks.py << 'EOF'
#!/usr/bin/env python3
"""Categorize mock duplications for remediation planning."""

import os
import re
from pathlib import Path
from collections import defaultdict

def categorize_mock_duplications():
    """Find and categorize all mock duplications."""
    project_root = Path(__file__).parent.parent.parent

    mock_categories = defaultdict(list)

    for py_file in project_root.rglob("tests/**/*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find mock class definitions
            mock_pattern = r'class (Mock\w+).*:'
            matches = re.finditer(mock_pattern, content)

            for match in matches:
                mock_name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1

                # Categorize by type
                if 'Agent' in mock_name:
                    category = 'Agent Mocks'
                elif 'Manager' in mock_name or 'WebSocket' in mock_name:
                    category = 'Manager Mocks'
                elif 'Service' in mock_name:
                    category = 'Service Mocks'
                else:
                    category = 'Other Mocks'

                mock_categories[category].append({
                    'name': mock_name,
                    'file': str(py_file),
                    'line': line_num
                })

        except Exception as e:
            continue

    return mock_categories

if __name__ == "__main__":
    categories = categorize_mock_duplications()

    print("Mock Duplication Categorization Report")
    print("=" * 50)

    for category, mocks in categories.items():
        print(f"\n{category}: {len(mocks)} implementations")
        for mock in mocks:
            print(f"  - {mock['name']} ({Path(mock['file']).name}:{mock['line']})")

    total_mocks = sum(len(mocks) for mocks in categories.values())
    print(f"\nTotal Mock Duplications: {total_mocks}")
EOF

# Run categorization
python scripts/ssot_remediation/categorize_mocks.py > reports/ssot_remediation/phase2/mock_audit/categorization_report.txt
```

**Expected Categories:**
- **Agent Mocks:** MockAgent, MockSupervisorAgent, MockDataHelperAgent
- **Manager Mocks:** MockWebSocketManager, MockConnectionManager, MockLifecycleManager
- **Service Mocks:** MockAuthService, MockLLMService, MockDatabaseService
- **Other Mocks:** Various utility and helper mocks

### **Step 2.1.2: SSotMockFactory Enhancement** (45 minutes)

#### Action: Analyze Current SSotMockFactory
```bash
# Review current SSOT mock factory implementation
cat test_framework/ssot/mock_factory.py | head -50

# Check existing mock patterns
grep -r "SSotMockFactory" tests/ --include="*.py" | head -10
```

#### Action: Enhance SSotMockFactory for Consolidation
```python
# Create enhanced mock factory script
cat > scripts/ssot_remediation/enhance_mock_factory.py << 'EOF'
#!/usr/bin/env python3
"""Enhance SSotMockFactory to support all duplicate mock patterns."""

from pathlib import Path

def enhance_ssot_mock_factory():
    """Add comprehensive mock creation methods to SSotMockFactory."""

    mock_factory_path = Path("test_framework/ssot/mock_factory.py")

    if not mock_factory_path.exists():
        print(f"ERROR: SSotMockFactory not found at {mock_factory_path}")
        return False

    # Read current implementation
    with open(mock_factory_path, 'r', encoding='utf-8') as f:
        current_content = f.read()

    # Define additional mock creation methods
    additional_methods = '''
    @staticmethod
    def create_mock_agent(agent_type="supervisor", **kwargs):
        """Create unified mock agent for all agent types."""
        from unittest.mock import MagicMock

        mock_agent = MagicMock()
        mock_agent.agent_type = agent_type
        mock_agent.execute_task.return_value = {"status": "completed", "result": "mock_result"}
        mock_agent.get_capabilities.return_value = ["mock_capability"]

        # Apply any custom kwargs
        for key, value in kwargs.items():
            setattr(mock_agent, key, value)

        return mock_agent

    @staticmethod
    def create_mock_websocket_manager(**kwargs):
        """Create unified mock WebSocket manager."""
        from unittest.mock import MagicMock

        mock_manager = MagicMock()
        mock_manager.connect.return_value = True
        mock_manager.disconnect.return_value = True
        mock_manager.send_message.return_value = True
        mock_manager.get_connection_count.return_value = 0

        # Apply any custom kwargs
        for key, value in kwargs.items():
            setattr(mock_manager, key, value)

        return mock_manager

    @staticmethod
    def create_mock_service(service_type="auth", **kwargs):
        """Create unified mock service for all service types."""
        from unittest.mock import MagicMock

        mock_service = MagicMock()
        mock_service.service_type = service_type
        mock_service.is_healthy.return_value = True
        mock_service.get_status.return_value = "operational"

        # Apply any custom kwargs
        for key, value in kwargs.items():
            setattr(mock_service, key, value)

        return mock_service
'''

    # Check if methods already exist
    if "create_mock_agent" in current_content:
        print("✅ SSotMockFactory already has required methods")
        return True

    # Add methods before the last class closing
    if "class SSotMockFactory" in current_content:
        # Find the position to insert new methods
        lines = current_content.split('\n')
        insert_position = -1

        # Find the last method in the class
        for i, line in enumerate(lines):
            if line.strip().startswith("@staticmethod") or line.strip().startswith("def "):
                insert_position = i

        if insert_position > 0:
            # Insert additional methods
            lines.insert(insert_position + 1, additional_methods)

            # Write updated content
            with open(mock_factory_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            print("✅ SSotMockFactory enhanced with consolidation methods")
            return True

    print("❌ Failed to enhance SSotMockFactory")
    return False

if __name__ == "__main__":
    enhance_ssot_mock_factory()
EOF

# Run enhancement
python scripts/ssot_remediation/enhance_mock_factory.py
```

### **Step 2.1.3: Systematic Mock Consolidation** (60-90 minutes)

#### Action: Consolidate Agent Mocks (Atomic Commit 1)
```bash
# Create consolidation script for Agent mocks
cat > scripts/ssot_remediation/consolidate_agent_mocks.py << 'EOF'
#!/usr/bin/env python3
"""Consolidate all Agent mock implementations to SSotMockFactory."""

import re
from pathlib import Path

def consolidate_agent_mocks():
    """Replace all MockAgent implementations with SSotMockFactory calls."""
    project_root = Path(__file__).parent.parent.parent

    consolidated_files = []

    for py_file in project_root.rglob("tests/**/*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Replace MockAgent class definitions
            agent_mock_pattern = r'class (Mock\w*Agent).*?(?=\n\s*class|\n\s*def|\Z)'
            content = re.sub(agent_mock_pattern, '', content, flags=re.DOTALL)

            # Replace MockAgent instantiations
            content = re.sub(r'Mock(\w*Agent)\(\)', r'SSotMockFactory.create_mock_agent(agent_type="\1".lower())', content)

            # Add SSotMockFactory import if needed
            if 'SSotMockFactory' in content and 'from test_framework.ssot.mock_factory import SSotMockFactory' not in content:
                import_line = 'from test_framework.ssot.mock_factory import SSotMockFactory\n'

                # Find appropriate location for import
                if 'import' in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith('from '):
                            lines.insert(i + 1, import_line.strip())
                            content = '\n'.join(lines)
                            break
                else:
                    content = import_line + content

            if content != original_content:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                consolidated_files.append(str(py_file))

        except Exception as e:
            print(f"Warning: Could not process {py_file}: {e}")
            continue

    return consolidated_files

if __name__ == "__main__":
    files = consolidate_agent_mocks()
    print(f"✅ Consolidated Agent mocks in {len(files)} files")
    for file in files:
        print(f"  - {file}")
EOF

# Run Agent mock consolidation
python scripts/ssot_remediation/consolidate_agent_mocks.py

# Validate no regressions
python tests/mission_critical/test_websocket_agent_events_suite.py || { echo "ERROR: Agent mock consolidation broke Golden Path"; exit 1; }

# Commit Agent mock consolidation
git add -A
git commit -m "refactor: consolidate Agent mock implementations to SSotMockFactory

- Replace all MockAgent class definitions with SSotMockFactory.create_mock_agent()
- Remove duplicate Agent mock implementations from test files
- Add SSotMockFactory imports where needed
- Maintain test functionality with unified mock creation

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### Action: Consolidate Manager Mocks (Atomic Commit 2)
```bash
# Create consolidation script for Manager mocks
cat > scripts/ssot_remediation/consolidate_manager_mocks.py << 'EOF'
#!/usr/bin/env python3
"""Consolidate all Manager mock implementations to SSotMockFactory."""

import re
from pathlib import Path

def consolidate_manager_mocks():
    """Replace all MockManager implementations with SSotMockFactory calls."""
    project_root = Path(__file__).parent.parent.parent

    consolidated_files = []

    for py_file in project_root.rglob("tests/**/*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Replace MockManager and MockWebSocket class definitions
            manager_mock_pattern = r'class (Mock\w*(?:Manager|WebSocket)).*?(?=\n\s*class|\n\s*def|\Z)'
            content = re.sub(manager_mock_pattern, '', content, flags=re.DOTALL)

            # Replace Manager mock instantiations
            content = re.sub(r'Mock(WebSocketManager|ConnectionManager|LifecycleManager)\(\)',
                           r'SSotMockFactory.create_mock_websocket_manager()', content)

            # Add SSotMockFactory import if needed
            if 'SSotMockFactory' in content and 'from test_framework.ssot.mock_factory import SSotMockFactory' not in content:
                import_line = 'from test_framework.ssot.mock_factory import SSotMockFactory\n'

                if 'import' in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith('from '):
                            lines.insert(i + 1, import_line.strip())
                            content = '\n'.join(lines)
                            break
                else:
                    content = import_line + content

            if content != original_content:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                consolidated_files.append(str(py_file))

        except Exception as e:
            print(f"Warning: Could not process {py_file}: {e}")
            continue

    return consolidated_files

if __name__ == "__main__":
    files = consolidate_manager_mocks()
    print(f"✅ Consolidated Manager mocks in {len(files)} files")
    for file in files:
        print(f"  - {file}")
EOF

# Run Manager mock consolidation
python scripts/ssot_remediation/consolidate_manager_mocks.py

# Validate no regressions
python tests/mission_critical/test_websocket_agent_events_suite.py || { echo "ERROR: Manager mock consolidation broke Golden Path"; exit 1; }
python tests/mission_critical/test_ssot_websocket_compliance.py || { echo "ERROR: WebSocket compliance affected"; exit 1; }

# Commit Manager mock consolidation
git add -A
git commit -m "refactor: consolidate Manager mock implementations to SSotMockFactory

- Replace all MockManager, MockWebSocketManager class definitions
- Use SSotMockFactory.create_mock_websocket_manager() for unified mocks
- Remove duplicate Manager mock implementations from test files
- Maintain WebSocket functionality with SSOT mock patterns

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### Action: Consolidate Service Mocks (Atomic Commit 3)
```bash
# Similar approach for Service mocks
python scripts/ssot_remediation/consolidate_service_mocks.py  # (Implementation similar to above)

# Validate and commit
python tests/mission_critical/test_websocket_agent_events_suite.py || { echo "ERROR: Service mock consolidation broke Golden Path"; exit 1; }

git add -A
git commit -m "refactor: consolidate Service mock implementations to SSotMockFactory"
```

---

## 🔗 STEP 2.2: IMPORT PATH CONSISTENCY (1-2 Hours)

### **Step 2.2.1: Import Pattern Audit** (30 minutes)

#### Action: Identify Legacy Import Patterns
```bash
# Find all try/except import patterns
echo "=== TRY/EXCEPT IMPORT PATTERNS ===" > reports/ssot_remediation/phase2/import_audit.txt
grep -r "try:.*import.*except:" tests/ --include="*.py" -n >> reports/ssot_remediation/phase2/import_audit.txt

# Find inconsistent SSOT import paths
echo -e "\n=== INCONSISTENT SSOT IMPORTS ===" >> reports/ssot_remediation/phase2/import_audit.txt
grep -r "from.*websocket" tests/ --include="*.py" -n | grep -v "websocket_core" >> reports/ssot_remediation/phase2/import_audit.txt

# Display audit results
cat reports/ssot_remediation/phase2/import_audit.txt
```

### **Step 2.2.2: Standardize SSOT Imports** (45-75 minutes)

#### Action: Replace Try/Except Import Patterns (Atomic Commit 4)
```bash
# Create import standardization script
cat > scripts/ssot_remediation/standardize_imports.py << 'EOF'
#!/usr/bin/env python3
"""Standardize SSOT import patterns and remove legacy fallbacks."""

import re
from pathlib import Path

def standardize_ssot_imports():
    """Replace try/except imports with direct SSOT imports."""
    project_root = Path(__file__).parent.parent.parent

    # SSOT import mappings
    ssot_mappings = {
        r'try:\s*from.*websocket.*import.*except.*:.*from.*websocket.*import':
        'from netra_backend.app.websocket_core.unified_manager import get_websocket_manager',

        r'try:\s*from.*agent.*import.*except.*:.*from.*agent.*import':
        'from netra_backend.app.agents.registry import get_agent_registry',

        r'try:\s*from.*auth.*import.*except.*:.*from.*auth.*import':
        'from netra_backend.app.auth_integration.auth import get_auth_service'
    }

    standardized_files = []

    for py_file in project_root.rglob("tests/**/*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Apply SSOT import standardizations
            for pattern, replacement in ssot_mappings.items():
                content = re.sub(pattern, replacement, content, flags=re.DOTALL | re.IGNORECASE)

            if content != original_content:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                standardized_files.append(str(py_file))

        except Exception as e:
            print(f"Warning: Could not process {py_file}: {e}")
            continue

    return standardized_files

if __name__ == "__main__":
    files = standardize_ssot_imports()
    print(f"✅ Standardized SSOT imports in {len(files)} files")
    for file in files:
        print(f"  - {file}")
EOF

# Run import standardization
python scripts/ssot_remediation/standardize_imports.py

# Validate no regressions
python tests/mission_critical/test_websocket_agent_events_suite.py || { echo "ERROR: Import standardization broke Golden Path"; exit 1; }

# Commit import standardization
git add -A
git commit -m "refactor: standardize SSOT import patterns in test framework

- Replace try/except import fallbacks with direct SSOT imports
- Use canonical import paths for WebSocket, Agent, and Auth components
- Remove legacy import compatibility patterns
- Ensure consistent SSOT import usage across test infrastructure

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## 🔧 STEP 2.3: TEST CONFIGURATION CLEANUP (1-2 Hours)

### **Step 2.3.1: Environment Access Audit** (20 minutes)

#### Action: Identify Direct os.environ Usage
```bash
# Find all direct os.environ access in test framework
echo "=== DIRECT OS.ENVIRON ACCESS ===" > reports/ssot_remediation/phase2/environment_audit.txt
grep -r "os.environ" test_framework/ --include="*.py" -n >> reports/ssot_remediation/phase2/environment_audit.txt

# Find all direct environment variable access in tests
echo -e "\n=== DIRECT ENV VAR ACCESS IN TESTS ===" >> reports/ssot_remediation/phase2/environment_audit.txt
grep -r "os.environ\|os.getenv" tests/ --include="*.py" -n | head -20 >> reports/ssot_remediation/phase2/environment_audit.txt

# Display audit results
cat reports/ssot_remediation/phase2/environment_audit.txt
```

### **Step 2.3.2: Enforce IsolatedEnvironment Usage** (40-60 minutes)

#### Action: Replace Direct Environment Access (Atomic Commit 5)
```bash
# Create environment standardization script
cat > scripts/ssot_remediation/standardize_environment_access.py << 'EOF'
#!/usr/bin/env python3
"""Replace direct os.environ access with IsolatedEnvironment usage."""

import re
from pathlib import Path

def standardize_environment_access():
    """Replace os.environ with IsolatedEnvironment in test framework."""
    project_root = Path(__file__).parent.parent.parent

    standardized_files = []

    # Focus on test_framework directory first
    test_framework_path = project_root / "test_framework"

    for py_file in test_framework_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # Replace os.environ access patterns
            content = re.sub(r'import os', 'import os\nfrom shared.isolated_environment import IsolatedEnvironment', content)
            content = re.sub(r'os\.environ\.get\(["\']([^"\']+)["\'](?:,\s*[^)]+)?\)', r'IsolatedEnvironment().get("\1")', content)
            content = re.sub(r'os\.environ\[["\']([^"\']+)["\']\]', r'IsolatedEnvironment().get("\1")', content)
            content = re.sub(r'os\.getenv\(["\']([^"\']+)["\'](?:,\s*[^)]+)?\)', r'IsolatedEnvironment().get("\1")', content)

            # Remove duplicate imports
            lines = content.split('\n')
            seen_imports = set()
            filtered_lines = []

            for line in lines:
                if line.strip().startswith('from shared.isolated_environment import'):
                    if line not in seen_imports:
                        seen_imports.add(line)
                        filtered_lines.append(line)
                else:
                    filtered_lines.append(line)

            content = '\n'.join(filtered_lines)

            if content != original_content:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                standardized_files.append(str(py_file))

        except Exception as e:
            print(f"Warning: Could not process {py_file}: {e}")
            continue

    return standardized_files

if __name__ == "__main__":
    files = standardize_environment_access()
    print(f"✅ Standardized environment access in {len(files)} files")
    for file in files:
        print(f"  - {file}")
EOF

# Run environment access standardization
python scripts/ssot_remediation/standardize_environment_access.py

# Validate no regressions
python tests/mission_critical/test_websocket_agent_events_suite.py || { echo "ERROR: Environment standardization broke Golden Path"; exit 1; }

# Commit environment standardization
git add -A
git commit -m "refactor: replace os.environ with IsolatedEnvironment in test framework

- Replace all os.environ.get() calls with IsolatedEnvironment().get()
- Replace all os.getenv() calls with unified environment access
- Add IsolatedEnvironment imports to test framework modules
- Ensure consistent SSOT environment management across test infrastructure

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## ✅ PHASE 2 SUCCESS CRITERIA

### **Validation Checkpoints:**
- [ ] **Mock Consolidation Complete:** All duplicate mocks replaced with SSotMockFactory
- [ ] **Import Consistency Achieved:** All legacy import patterns standardized
- [ ] **Environment Access Unified:** All direct os.environ usage replaced
- [ ] **Golden Path Protected:** All critical tests continue passing
- [ ] **Zero Regressions:** Production functionality unaffected

### **Atomic Commit Summary:**
1. ✅ **Agent Mock Consolidation:** `refactor: consolidate Agent mock implementations to SSotMockFactory`
2. ✅ **Manager Mock Consolidation:** `refactor: consolidate Manager mock implementations to SSotMockFactory`
3. ✅ **Service Mock Consolidation:** `refactor: consolidate Service mock implementations to SSotMockFactory`
4. ✅ **Import Standardization:** `refactor: standardize SSOT import patterns in test framework`
5. ✅ **Environment Standardization:** `refactor: replace os.environ with IsolatedEnvironment in test framework`

### **Post-Phase 2 Validation:**
```bash
# Run comprehensive compliance check
python scripts/check_architecture_compliance.py

# Verify Golden Path still operational
python tests/mission_critical/test_websocket_agent_events_suite.py

# Run broader test validation
python tests/unified_test_runner.py --categories mission_critical integration --fast-fail

# Expected: Compliance score improved from 98.7% toward 100%
```

---

## 🚀 PHASE 2 COMPLETION

**Upon successful completion of Phase 2:**
1. All test infrastructure SSOT violations remediated
2. Compliance score significantly improved (target: 99.5%+)
3. Golden Path functionality preserved
4. Atomic commit history created for easy rollback if needed

**Phase 2 Exit Criteria:**
- All atomic commits completed successfully
- No Golden Path test failures
- Compliance score improvement validated
- Ready for Phase 3 final validation

---

**Next Phase:** [SSOT_REMEDIATION_PHASE3_IMPLEMENTATION_GUIDE.md](SSOT_REMEDIATION_PHASE3_IMPLEMENTATION_GUIDE.md)