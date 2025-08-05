
from typing import List, Callable, Any, Dict
from app.services.deep_agent_v3.state import AgentState

class Pipeline:
    def __init__(self, steps: List[Callable]):
        self.steps = steps
        self.current_step_index = 0

    def is_complete(self) -> bool:
        return self.current_step_index >= len(self.steps)

    async def run_next_step(self, state: AgentState, tools: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
        if self.is_complete():
            return {"status": "complete", "message": "Pipeline is already complete."}

        step_func = self.steps[self.current_step_index]
        step_name = step_func.__name__

        try:
            # This is a simplified version of the tool injection. A more robust solution
            # would inspect the function signature and provide the required tools.
            if step_name == "fetch_raw_logs":
                result_message = await step_func(state, tools["log_fetcher"], request)
            elif step_name == "enrich_and_cluster":
                result_message = await step_func(state, tools["log_pattern_identifier"])
            elif step_name == "propose_optimal_policies":
                result_message = await step_func(state, tools["policy_proposer"])
            else:
                result_message = await step_func(state)

            self.current_step_index += 1
            return {"status": "success", "completed_step": step_name, "result": result_message}
        except Exception as e:
            return {"status": "failed", "step": step_name, "error": str(e)}
