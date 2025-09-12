"""
Global pytest configuration for encoding safety and performance optimization
Post-Unicode Remediation: Ensures test collection remains fast and reliable
"""

import os
import sys
import warnings
from pathlib import Path

# CRITICAL: Set encoding for all file operations
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
os.environ.setdefault('PYTHONUTF8', '1')

# Ensure UTF-8 encoding for stdout/stderr
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Performance optimization: Disable unnecessary warnings during collection
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning) 
warnings.filterwarnings("ignore", message=".*Unicode.*")

def pytest_configure(config):
    """Configure pytest for optimal performance"""
    # Set markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "mission_critical: Mission critical tests")
    config.addinivalue_line("markers", "golden_path: Golden path tests")
    
    # Performance optimizations
    if hasattr(config.option, 'collectonly') and config.option.collectonly:
        # During collection, disable some plugins for speed
        config.pluginmanager.set_blocked('cacheprovider')

def pytest_collection_modifyitems(config, items):
    """Optimize test collection items"""
    # Sort tests for better performance (fast tests first)
    fast_tests = []
    slow_tests = []
    
    for item in items:
        if 'slow' in item.keywords:
            slow_tests.append(item)
        else:
            fast_tests.append(item)
    
    # Reorder: fast tests first, then slow tests
    items[:] = fast_tests + slow_tests

# Unicode safety: Replace problematic characters in test output
import _pytest.terminal

original_write = _pytest.terminal.TerminalWriter.write

def safe_write(self, msg, **markup):
    """Safe write that handles Unicode encoding issues"""
    if isinstance(msg, str):
        # Replace problematic Unicode characters
        msg = msg.encode('ascii', errors='replace').decode('ascii')
    return original_write(self, msg, **markup)

_pytest.terminal.TerminalWriter.write = safe_write
