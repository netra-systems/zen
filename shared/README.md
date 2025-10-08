# Shared Utilities (Vendored Subset)

This directory contains a **minimal vendored subset** of the Apex `shared/` package, containing only the files required by `zen --apex` CLI functionality.

## Included Files

### 1. `__init__.py`
Package initialization stub with basic documentation.

### 2. `windows_encoding.py`
Windows UTF-8 console encoding fixes. The `setup_windows_encoding()` function is called early in `agent_cli.py` startup to ensure proper Unicode handling on Windows platforms.

### 3. `types/__init__.py`
Type definitions package that re-exports WebSocket closure code utilities.

### 4. `types/websocket_closure_codes.py`
WebSocket closure code validation utilities:
- `WebSocketClosureCode`: Enum of standard RFC 6455 closure codes
- `WebSocketClosureCategory`: Categories for classifying closure types
- `categorize_closure_code()`: Categorize a code into normal/client/server/infrastructure
- `get_closure_description()`: Human-readable description of closure codes
- `is_infrastructure_error()`: Check if a code represents infrastructure failure

## Maintenance

⚠️ **Important**: These files are vendored from the Apex repository. If Apex updates its closure-code definitions or Windows encoding logic, these files must be manually synchronized.

### What's NOT Included

Everything else under Apex's `shared/` directory is intentionally excluded because it's not referenced by `agent_cli.py`. This keeps the vendored code minimal and avoids pulling in backend logic, secrets, or unnecessary dependencies.

## Usage

These modules are imported by `scripts/agent_cli.py`:

```python
from shared.windows_encoding import setup_windows_encoding
from shared.types.websocket_closure_codes import (
    WebSocketClosureCode,
    WebSocketClosureCategory,
    categorize_closure_code,
    get_closure_description,
    is_infrastructure_error
)
```

The `setup_windows_encoding()` function is called immediately at startup, before any console I/O operations.
