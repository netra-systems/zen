import asyncio
import time
import pytest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import get_env