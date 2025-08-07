from langchain_core.tools import tool
from typing import Annotated, Literal, List
from langgraph.prebuilt import InjectedState
import uuid

from .prompts import (
    WRITE_TODOS_DESCRIPTION,
    EDIT_DESCRIPTION,
    TOOL_DESCRIPTION,
)
from .state import DeepAgentState, Todo
from app.services.apex_optimizer_agent.models import ToolResult, ToolStatus

@tool
def update_state(
    completed_step: str,
    todo_list: List[str] = None,
    state: Annotated[DeepAgentState, InjectedState] = None,
) -> ToolResult:
    """Updates the state of the agent."""
    if state is None:
        state = {"completed_steps": [], "todo_list": []}
    if "completed_steps" not in state:
        state["completed_steps"] = []
    if "todo_list" not in state:
        state["todo_list"] = []
    state["completed_steps"].append(completed_step)
    if todo_list:
        state["todo_list"] = todo_list
    else:
        if completed_step in state["todo_list"]:
            state["todo_list"].remove(completed_step)
    return ToolResult(status=ToolStatus.SUCCESS, message="State updated successfully.", payload=state)

@tool
def update_todo(
    todo_id: str,
    status: Literal["pending", "in_progress", "completed"],
    state: Annotated[DeepAgentState, InjectedState],
) -> ToolResult:
    """Update the status of a todo."""
    todos = state.get("todos", [])
    for todo in todos:
        if todo["id"] == todo_id:
            todo["status"] = status
            break
    return ToolResult(status=ToolStatus.SUCCESS, message="Todo updated successfully.", payload={"todos": todos})


@tool(description=WRITE_TODOS_DESCRIPTION)
def write_todos(
    todos: list[Todo],
    state: Annotated[DeepAgentState, InjectedState],
) -> ToolResult:
    """Create new todos."""
    existing_todos = state.get("todos", [])
    for todo in todos:
        if "id" not in todo:
            todo["id"] = uuid.uuid4().hex
    all_todos = existing_todos + todos
    return ToolResult(status=ToolStatus.SUCCESS, message="Todos created successfully.", payload={"todos": all_todos})

def ls(state: Annotated[DeepAgentState, InjectedState]) -> ToolResult:
    """List all files"""
    files = list(state.get("files", {}).keys())
    return ToolResult(status=ToolStatus.SUCCESS, message="Files listed successfully.", payload=files)


@tool(description=TOOL_DESCRIPTION)
def read_file(
    file_path: str,
    state: Annotated[DeepAgentState, InjectedState],
    offset: int = 0,
    limit: int = 2000,
) -> ToolResult:
    """Read file."""
    mock_filesystem = state.get("files", {})
    if file_path not in mock_filesystem:
        return ToolResult(status=ToolStatus.ERROR, message=f"File '{file_path}' not found")

    content = mock_filesystem[file_path]

    if not content or content.strip() == "":
        return ToolResult(status=ToolStatus.SUCCESS, message="File exists but has empty contents", payload="")

    lines = content.splitlines()

    if offset >= len(lines):
        return ToolResult(status=ToolStatus.ERROR, message=f"Line offset {offset} exceeds file length ({len(lines)} lines)")

    start_idx = offset
    end_idx = min(start_idx + limit, len(lines))

    result_lines = []
    for i in range(start_idx, end_idx):
        line_content = lines[i]
        if len(line_content) > 2000:
            line_content = line_content[:2000]
        line_number = i + 1
        result_lines.append(f"{line_number:6d}\t{line_content}")

    return ToolResult(status=ToolStatus.SUCCESS, message="File read successfully.", payload="\n".join(result_lines))


@tool
def create_file(
    file_path: str,
    content: str,
    state: Annotated[DeepAgentState, InjectedState],
) -> ToolResult:
    """Create a file."""
    files = state.get("files", {})
    if file_path in files:
        return ToolResult(status=ToolStatus.ERROR, message=f"File '{file_path}' already exists.")
    files[file_path] = content
    return ToolResult(status=ToolStatus.SUCCESS, message=f"File '{file_path}' created successfully.", payload={"files": files})


@tool(description=EDIT_DESCRIPTION)
def edit_file(
    file_path: str,
    old_string: str,
    new_string: str,
    state: Annotated[DeepAgentState, InjectedState],
    replace_all: bool = False,
) -> ToolResult:
    """Edit a file."""
    mock_filesystem = state.get("files", {})
    if file_path not in mock_filesystem:
        return ToolResult(status=ToolStatus.ERROR, message=f"File '{file_path}' not found")

    content = mock_filesystem[file_path]

    if old_string not in content:
        return ToolResult(status=ToolStatus.ERROR, message=f"String not found in file: '{old_string}'")

    if not replace_all:
        occurrences = content.count(old_string)
        if occurrences > 1:
            return ToolResult(status=ToolStatus.ERROR, message=f"String '{old_string}' appears {occurrences} times in file. Use replace_all=True to replace all instances, or provide a more specific string with surrounding context.")
        elif occurrences == 0:
            return ToolResult(status=ToolStatus.ERROR, message=f"String not found in file: '{old_string}'")

    if replace_all:
        new_content = content.replace(old_string, new_string)
        replacement_count = content.count(old_string)
        result_msg = f"Successfully replaced {replacement_count} instance(s) of the string in '{file_path}'"
    else:
        new_content = content.replace(old_string, new_string, 1)
        result_msg = f"Successfully replaced string in '{file_path}'"

    mock_filesystem[file_path] = new_content
    return ToolResult(status=ToolStatus.SUCCESS, message=result_msg, payload={"files": mock_filesystem})

def get_tools():
    return [
        update_state,
        update_todo,
        write_todos,
        read_file,
        create_file,
        edit_file,
    ]