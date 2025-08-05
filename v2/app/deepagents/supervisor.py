from typing import Literal


from langgraph.graph import END, StateGraph
from langgraph.prebuilt import tools_condition

from .state import DeepAgentState
from .tools import update_todo
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
        # If we have a plan, then we are done with planning
        if (
            state.get("todos")
            and all(todo["status"] == "completed" for todo in state["todos"])
            or not state.get("todos")
        ):
            return END
        else:
            # Otherwise, we need to replan
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
    llm = get_default_model()
    graph = create_supervisor_graph(llm)
    # You can now run the graph with some initial state
    # initial_state = DeepAgentState(messages=[("user", "your request here")])
    # for event in graph.stream(initial_state):
    #     print(event)