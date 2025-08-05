import asyncio
import inspect
from typing import List, Callable, Any, Dict
from app.services.deep_agent_v3.state import AgentState

class Pipeline:
    def __init__(self, steps: List[Callable], max_retries: int = 3, retry_delay: int = 5):
        self.steps = steps
        self.current_step_index = 0
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def is_complete(self) -> bool:
        return self.current_step_index >= len(self.steps)

    async def run_next_step(self, state: AgentState, tools: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
        if self.is_complete():
            return {"status": "complete", "message": "Pipeline is already complete."}

        step_func = self.steps[self.current_step_index]
        step_name = step_func.__name__

        for attempt in range(self.max_retries):
            try:
                kwargs = self._prepare_step_kwargs(step_func, state, tools, request)
                result_message = await step_func(**kwargs)

                self.current_step_index += 1
                return {"status": "success", "completed_step": step_name, "result": result_message}
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    return {"status": "failed", "step": step_name, "error": str(e)}

    def _prepare_step_kwargs(
        self,
        step_func: Callable,
        state: AgentState,
        tools: Dict[str, Any],
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        kwargs = {}
        sig = inspect.signature(step_func)
        for param in sig.parameters.values():
            if param.name == "state":
                kwargs["state"] = state
            elif param.name == "request":
                kwargs["request"] = request
            elif param.name in tools:
                kwargs[param.name] = tools[param.name]
        return kwargs

    def get_current_step_name(self) -> str:
        if self.is_complete():
            return "Pipeline Complete"
        return self.steps[self.current_step_index].__name__