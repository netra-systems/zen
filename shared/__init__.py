"""
Shared utilities package (minimal vendored subset for zen --apex CLI).

This package contains only the minimal files required by agent_cli.py:
- windows_encoding.py: Windows UTF-8 console fixes
- types/websocket_closure_codes.py: WebSocket closure code validation

TODO: Manually sync these files if Apex updates its closure-code definitions
or Windows handling logic.
"""

__version__ = "1.0.0"
