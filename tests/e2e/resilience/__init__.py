import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent
while not (PROJECT_ROOT / 'netra_backend').exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

"""
E2E Resilience Tests

This package contains end-to-end tests focused on system resilience, including:
- Error handling and recovery mechanisms
- Network failure scenarios
- Resource exhaustion and limits
- Circuit breaker patterns
- Scaling edge cases and integrity
- Health monitoring and cascading failures
- WebSocket resilience and recovery
"""