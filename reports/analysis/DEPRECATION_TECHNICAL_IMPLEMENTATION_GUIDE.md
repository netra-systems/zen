# Deprecation Technical Implementation Guide - Step 5

**Created:** 2025-01-14
**Companion to:** DEPRECATION_REMEDIATION_PLAN.md
**Purpose:** Detailed technical instructions for each remediation step

## Phase 1: Critical Golden Path Remediation

### 1.1 Configuration Import Migration

#### File 1: shared/logging/__init__.py
**Issue**: Deprecated import from `unified_logger_factory`

**Current State**:
```python
from shared.logging.unified_logger_factory import (
    configure_service_logging
)
```

**Required Change**:
```python
# Remove the deprecated import entirely since configure_service_logging
# should be accessed directly from unified_logging_ssot or removed if unused
```

**Implementation Steps**:
1. **Analysis**: Verify `configure_service_logging` usage across codebase
   ```bash
   grep -r "configure_service_logging" --include="*.py" .
   ```

2. **If used**: Move function to `shared.logging.unified_logging_ssot`
3. **If unused**: Remove import entirely
4. **Update __all__**: Remove from exports if not needed

**Validation**:
```bash
python -c "from shared.logging import get_logger; logger = get_logger('test'); logger.info('Test')"
```

#### File 2: netra_backend/app/websocket_core/unified_emitter.py
**Issue**: Deprecated logging import affects WebSocket functionality

**Current State** (Line 33):
```python
from netra_backend.app.logging_config import central_logger
```

**Required Change**:
```python
from shared.logging.unified_logging_ssot import get_logger
```

**Implementation Steps**:
1. **Replace import**:
   ```python
   # OLD
   from netra_backend.app.logging_config import central_logger
   # NEW
   from shared.logging.unified_logging_ssot import get_logger
   ```

2. **Update logger initialization** (Line 40):
   ```python
   # OLD
   logger = central_logger.get_logger(__name__)
   # NEW
   logger = get_logger(__name__)
   ```

3. **Critical Validation**: This file is MISSION CRITICAL for WebSocket events
   ```bash
   # Test ALL 5 critical events after change
   python tests/mission_critical/test_websocket_agent_events_suite.py
   ```

**Risk Assessment**: MEDIUM - This file handles all WebSocket event emission

#### File 3: netra_backend/app/agents/mixins/websocket_bridge_adapter.py
**Issue**: WebSocketManager import path deprecation

**Current State** (implied from warning):
```python
# Deprecated import path causing warning at line 14
from netra_backend.app.websocket_core.event_validator import get_websocket_validator
```

**Analysis Required**:
1. Check actual import causing the warning
2. Update to canonical path as indicated in warning message

**Implementation**:
```bash
# Search for the actual deprecated import
grep -n "WebSocketManager" netra_backend/app/agents/mixins/websocket_bridge_adapter.py
```

**Expected Fix**:
```python
# Replace deprecated import with canonical path
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
```

### 1.2 Atomic Commit Strategy

Each change should be a separate atomic commit:

```bash
# Commit 1: shared/logging/__init__.py
git add shared/logging/__init__.py
git commit -m "fix(deprecation): Remove deprecated unified_logger_factory import

- Remove deprecated import from shared.logging.unified_logger_factory
- Maintain SSOT logging through unified_logging_ssot
- Protects Golden Path WebSocket functionality

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# Commit 2: unified_emitter.py
git add netra_backend/app/websocket_core/unified_emitter.py
git commit -m "fix(deprecation): Migrate WebSocket emitter to SSOT logging

- Replace deprecated logging_config import with unified_logging_ssot
- Maintain WebSocket event delivery for Golden Path ($500K+ ARR protection)
- Update logger initialization to use get_logger() directly

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# Commit 3: websocket_bridge_adapter.py
git add netra_backend/app/agents/mixins/websocket_bridge_adapter.py
git commit -m "fix(deprecation): Update WebSocketManager import to canonical path

- Use canonical import path for WebSocketManager
- Eliminate import path deprecation warning
- Maintain WebSocket bridge adapter functionality

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Phase 2: Factory Pattern Migration

### 2.1 SupervisorExecutionEngineFactory Analysis

**Discovery Commands**:
```bash
# Find all SupervisorExecutionEngineFactory usages
grep -r "SupervisorExecutionEngineFactory" --include="*.py" . | grep -v test

# Find UnifiedExecutionEngineFactory availability
find . -name "*.py" -exec grep -l "UnifiedExecutionEngineFactory" {} \;
```

**Migration Pattern**:
```python
# OLD - Deprecated Factory
from netra_backend.app.agents.supervisor.factories import SupervisorExecutionEngineFactory

engine = SupervisorExecutionEngineFactory.create_engine(
    user_context=user_context,
    websocket_manager=ws_manager
)

# NEW - Unified Factory Pattern
from netra_backend.app.factories.unified_execution_factory import UnifiedExecutionEngineFactory

engine = UnifiedExecutionEngineFactory.create_engine(
    user_context=user_context,
    websocket_manager=ws_manager
)
```

**Critical Validation**:
```python
# Test multi-user isolation after migration
python -c "
from netra_backend.app.factories.unified_execution_factory import UnifiedExecutionEngineFactory
# Create multiple engines and verify isolation
engine1 = UnifiedExecutionEngineFactory.create_engine(user_id='user1')
engine2 = UnifiedExecutionEngineFactory.create_engine(user_id='user2')
assert engine1.user_context != engine2.user_context
print('User isolation maintained')
"
```

## Phase 3: Pydantic Configuration Migration

### 3.1 ConfigDict Migration Pattern

**For each Pydantic model with `class Config:`**:

```python
# OLD - Deprecated class Config
from pydantic import BaseModel
from datetime import datetime

class MyModel(BaseModel):
    name: str
    created_at: datetime

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# NEW - ConfigDict pattern
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class MyModel(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    name: str
    created_at: datetime
```

### 3.2 MCP Client Models Migration

**File**: `netra_backend/app/mcp_client/models.py`

**Models to Update** (6 total):
1. `MCPConnection` (lines 121-127)
2. `MCPTool` (lines 147-152)
3. `MCPToolResult` (lines 173-178)
4. `MCPResource` (lines 201-206)
5. `MCPServerInfo` (lines 218-224)
6. `MCPOperationContext` (lines 237-242)

**Implementation for MCPConnection**:
```python
# OLD (lines 121-127)
class MCPConnection(BaseModel):
    # ... fields ...

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# NEW
from pydantic import BaseModel, ConfigDict

class MCPConnection(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    # ... fields remain the same ...
```

**Validation After Each Model**:
```python
# Test model creation and serialization
python -c "
from netra_backend.app.mcp_client.models import MCPConnection
from datetime import datetime
import json

# Test model creation
conn = MCPConnection(
    server_name='test',
    transport='http',
    created_at=datetime.utcnow()
)

# Test serialization
json_str = conn.model_dump_json()
print('Model serialization successful')
print(json_str[:100] + '...')
"
```

### 3.3 Automated Migration Script

Create script to handle bulk Pydantic migrations:

```python
# scripts/migrate_pydantic_configs.py
import re
import os
from pathlib import Path

def migrate_pydantic_config(file_path: Path) -> bool:
    """Migrate a single file from class Config to ConfigDict."""
    content = file_path.read_text()

    # Pattern to find class Config blocks
    pattern = r'(\s+)class Config:\s*\n((?:\1\s+.*\n)*)'

    def replace_config(match):
        indent = match.group(1)
        config_body = match.group(2)

        # Convert to ConfigDict format
        config_dict = f"{indent}model_config = ConfigDict(\n{config_body}{indent})\n"
        return config_dict

    new_content = re.sub(pattern, replace_config, content)

    if new_content != content:
        file_path.write_text(new_content)
        return True
    return False

# Usage
files_to_migrate = [
    "netra_backend/app/mcp_client/models.py",
    "netra_backend/app/agents/security/resource_guard.py",
    # ... other files
]

for file_path in files_to_migrate:
    if migrate_pydantic_config(Path(file_path)):
        print(f"Migrated: {file_path}")
```

## Phase 4: Pytest Collection Issues

### 4.1 Test Class Constructor Issues

**Problem**: Classes with `__init__` constructors cannot be collected by pytest

**Files Affected**:
- `tests/unit/test_pytest_collection_warnings_issue_999.py` (lines 17, 48)

**Current Problematic Pattern**:
```python
class TestWebSocketConnection:
    def __init__(self, connection_id: str):
        self.connection_id = connection_id

    def test_connection(self):
        assert self.connection_id is not None
```

**Solution 1 - Pytest Fixtures**:
```python
import pytest

@pytest.fixture
def connection_id():
    return "test_connection_123"

class TestWebSocketConnection:
    def test_connection(self, connection_id):
        assert connection_id is not None
```

**Solution 2 - Remove Constructor**:
```python
class TestWebSocketConnection:
    def test_connection(self):
        connection_id = "test_connection_123"  # Move to method
        assert connection_id is not None
```

## Validation and Testing Strategy

### Continuous Validation Commands

**After each change, run**:
```bash
# 1. Check for new deprecation warnings
python -m pytest tests/unit/test_pytest_collection_warnings_issue_999.py -v -W error::DeprecationWarning

# 2. Validate Golden Path functionality
python tests/mission_critical/test_websocket_agent_events_suite.py

# 3. Run deprecation-specific tests
python -m pytest tests/unit/deprecation_cleanup/ -v

# 4. Quick smoke test
python tests/unified_test_runner.py --categories smoke --fast-fail
```

### Success Metrics

**Phase 1 Success**:
- Zero deprecation warnings in WebSocket functionality
- All 5 WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) delivered
- Golden Path tests pass 100%

**Phase 2 Success**:
- No SupervisorExecutionEngineFactory references in production code
- Multi-user isolation maintained
- Factory pattern tests pass

**Phase 3 Success**:
- Zero PydanticDeprecatedSince20 warnings
- All model validation tests pass
- JSON serialization works correctly

**Phase 4 Success**:
- Zero PytestCollectionWarning instances
- Test discovery rate improves
- All test classes properly discoverable

## Emergency Procedures

### Rollback Individual Changes
```bash
# If a specific file change breaks functionality
git log --oneline -n 10  # Find commit hash
git revert [commit-hash]  # Revert specific commit
python tests/mission_critical/test_websocket_agent_events_suite.py  # Validate fix
```

### Rollback Entire Phase
```bash
# If multiple issues found in a phase
git log --oneline --grep="fix(deprecation)" -n 10  # Find phase commits
git revert [start-commit]..[end-commit]  # Revert range
python tests/unified_test_runner.py --categories mission_critical  # Full validation
```

---

*This technical guide provides step-by-step implementation details for the systematic remediation of deprecation warnings while protecting Golden Path functionality.*