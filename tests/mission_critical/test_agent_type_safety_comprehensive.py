import sys
import ast
import inspect
import typing
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, get_type_hints
from dataclasses import is_dataclass
import pytest
import asyncio
import importlib
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.agents.agent_communication import AgentCommunicationMixin
from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
from netra_backend.app.agents.base.interface import (
    ExecutionContext,
    ExecutionResult
)

from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env