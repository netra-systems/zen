"""
Supply Research Scheduler Job Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 549-line monolith
"""

# Import all test classes from focused modules

# Add project root to path

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from netra_backend.tests.test_scheduler_concurrency import (
    TestSupplyResearchSchedulerConcurrency,
)
from netra_backend.tests.test_scheduler_jobs_core import TestSupplyResearchSchedulerJobs
from netra_backend.tests.test_scheduler_performance import (
    TestSupplyResearchSchedulerPerformance,
)
from netra_backend.tests.test_scheduler_retry_logic import (
    TestSupplyResearchSchedulerRetryLogic,
)

# Add project root to path

# Re-export for backward compatibility
__all__ = [
    'TestSupplyResearchSchedulerJobs',
    'TestSupplyResearchSchedulerRetryLogic', 
    'TestSupplyResearchSchedulerConcurrency',
    'TestSupplyResearchSchedulerPerformance'
]