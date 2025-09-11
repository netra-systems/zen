from typing import TYPE_CHECKING, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.logging_formatters import LogEntry as Log
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.supply_catalog_service import SupplyCatalogService

if TYPE_CHECKING:
    from netra_backend.app.services.apex_optimizer_agent.tools.cost_estimator import (
        CostEstimator,
    )

class ToolContext:
    def __init__(
        self,
        db_session: AsyncSession,
        llm_manager: LLMManager,
        cost_estimator: "CostEstimator",
        state: UserExecutionContext,
        supply_catalog: SupplyCatalogService,
        logs: Optional[List[Log]] = None
    ) -> None:
        self.logs = logs if logs is not None else []
        self.db_session = db_session
        self.llm_manager = llm_manager
        self.cost_estimator = cost_estimator
        self.supply_catalog = supply_catalog
        self.state = state

    def __post_init__(self):
        # Only create a new state if one wasn't provided
        if not hasattr(self, 'state') or self.state is None:
            self.state = UserExecutionContext(
                user_id="tool_context",
                thread_id="tool_operation",
                run_id="tool_context_operation",
                metadata={"user_request": "tool_context_operation"}
            )