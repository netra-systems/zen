from typing import Literal


from langgraph.graph import END, StateGraph

from .state import DeepAgentState
from app.llm.llm_manager import LLMManager


def create_supervisor_graph(llm_manager: LLMManager, llm_name: str = "default"):
    builder = StateGraph(DeepAgentState)
    llm = llm_manager.get_llm(llm_name)

    # Define the two nodes we will cycle between
    builder.add_node("supervisor", llm)
    builder.add_node("agent", llm)

    # Define the edges
    builder.add_edge("agent", "supervisor")

    # A conditional edge will decide to go to one of the agents, or to finish
    def supervisor_condition(state: DeepAgentState) -> Literal["agent", "__end__"]:
        todos = state.get("todos")
        if not todos or any(todo["status"] == "pending" for todo in todos):
            return "agent"
        if any(todo["status"] == "in_progress" for todo in todos):
            return "agent"
        if all(todo["status"] == "completed" for todo in todos):
            return END
        return "agent"


    builder.add_conditional_edges(
        "supervisor",
        supervisor_condition,
        {
            "agent": "agent",
            END: END,
        },
    )
    builder.set_entry_point("supervisor")

    return builder.compile()


# Example usage
if __name__ == "__main__":
    from app.config import settings
    llm_manager = LLMManager(settings)
    graph = create_supervisor_graph(llm_manager)
    # You can now run the graph with some initial state
    # initial_state = DeepAgentState(messages=[("user", "your request here")])
    # for event in graph.stream(initial_state):
    #     print(event)