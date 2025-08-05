
import pytest
from app.deepagents.supervisor import create_supervisor_graph
from app.deepagents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.config import settings

@pytest.fixture
def llm_manager():
    return LLMManager(settings)

def test_supervisor_terminates_with_empty_todos(llm_manager):
    graph = create_supervisor_graph(llm_manager)
    initial_state = DeepAgentState(messages=[("user", "test")], todos=[])
    events = list(graph.stream(initial_state))
    # The last event should be the end event
    assert events[-1]['event'] == 'end'
