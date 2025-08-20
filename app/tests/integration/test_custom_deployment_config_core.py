"""Core Tests - Split from test_custom_deployment_config.py

    BVJ: Protects $200K+ MRR from enterprise deployment requirements
"""

import pytest
import asyncio
import os
import tempfile
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
from app.tests.integration.deployment_config_fixtures import (
from app.logging_config import central_logger

    def _get_test_value_for_rule(self, rule_spec: Dict[str, Any]) -> str:
        """Generate valid test value for rule specification."""
        if rule_spec["type"] == "boolean":
            return "true"
        elif rule_spec["type"] == "integer":
            min_val = rule_spec.get("min", 1)
            max_val = rule_spec.get("max", 100)
            return str((min_val + max_val) // 2)
        elif rule_spec["type"] == "string" and "allowed_values" in rule_spec:
            return rule_spec["allowed_values"][0]
        return "valid_value"
