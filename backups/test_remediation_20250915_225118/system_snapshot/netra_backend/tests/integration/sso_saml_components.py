# Shim module for SSO test components
from typing import Dict, Any, Optional
from unittest.mock import Mock
import time

from test_framework.fixtures.auth import (
    SSOTestComponents,
    EnterpriseTokenManager,
    MockIdPErrorGenerator,
    SAMLAssertionValidator,
)

# Create alias for EnterpriseSessionManager
EnterpriseSessionManager = EnterpriseTokenManager