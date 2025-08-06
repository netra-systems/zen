from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from typing import Annotated, Literal, List
from langgraph.prebuilt import InjectedState
import uuid

from .prompts import (
    WRITE_TODOS_DESCRIPTION,
    EDIT_DESCRIPTION,
    TOOL_DESCRIPTION,
)
from .state import DeepAgentState, Todo


@tool
def update_state(state: dict, completed_step: str, new_todo: List[str] = None) -> dict:
    """Updates the state of the agent.

    Args:
        state: The current state of the agent.
        completed_step: The step that has been completed.
        new_todo: A new todo list to replace the old one.

    Returns:
        The updated state.
    """
    state["completed_steps"].append(completed_step)
    if new_todo:
        state["todo_list"] = new_todo
    else:
        state["todo_list"].remove(completed_step)
    return state

@tool
def update_todo(
    todo_id: str,
    status: Literal["pending", "in_progress", "completed"],
    state: Annotated[DeepAgentState, InjectedState],
) -> dict:
    """Update the status of a todo."""
    todos = state.get("todos", [])
    for todo in todos:
        if todo["id"] == todo_id:
            todo["status"] = status
            break
    return {"todos": todos}


@tool(description=WRITE_TODOS_DESCRIPTION)
def write_todos(
    todos: list[Todo],
    state: Annotated[DeepAgentState, InjectedState],
) -> dict:
    # Get the existing todos
    existing_todos = state.get("todos", [])
    # Add the new todos, assigning a unique ID to each
    for todo in todos:
        if "id" not in todo:
            todo["id"] = uuid.uuid4().hex
    all_todos = existing_todos + todos
    return {"todos": all_todos}

def ls(state: Annotated[DeepAgentState, InjectedState]) -> list[str]:
    """List all files"""
    return list(state.get("files", {}).keys())


@tool(description=TOOL_DESCRIPTION)
def read_file(
    file_path: str,
    state: Annotated[DeepAgentState, InjectedState],
    offset: int = 0,
    limit: int = 2000,
) -> str:
    """Read file."""
    mock_filesystem = state.get("files", {})
    if file_path not in mock_filesystem:
        return f"Error: File '{file_path}' not found"

    # Get file content
    content = mock_filesystem[file_path]

    # Handle empty file
    if not content or content.strip() == "":
        return "System reminder: File exists but has empty contents"

    # Split content into lines
    lines = content.splitlines()

    # Apply line offset and limit
    start_idx = offset
    end_idx = min(start_idx + limit, len(lines))

    # Handle case where offset is beyond file length
    if start_idx >= len(lines):
        return f"Error: Line offset {offset} exceeds file length ({len(lines)} lines)"

    # Format output with line numbers (cat -n format)
    result_lines = []
    for i in range(start_idx, end_idx):
        line_content = lines[i]

        # Truncate lines longer than 2000 characters
        if len(line_content) > 2000:
            line_content = line_content[:2000]

        # Line numbers start at 1, so add 1 to the index
        line_number = i + 1
        result_lines.append(f"{line_number:6d}\t{line_content}")

    return "\n".join(result_lines)


def write_file(
    file_path: str,
    content: str,
    state: Annotated[DeepAgentState, InjectedState],
) -> dict:
    """Write to a file."""
    files = state.get("files", {})
    files[file_path] = content
    return {"files": files}


@tool(description=EDIT_DESCRIPTION)
def edit_file(
    file_path: str,
    old_string: str,
    new_string: str,
    state: Annotated[DeepAgentState, InjectedState],
    replace_all: bool = False,
) -> dict:
    """Write to a file."""
    mock_filesystem = state.get("files", {})
    # Check if file exists in mock filesystem
    if file_path not in mock_filesystem:
        return f"Error: File '{file_path}' not found"

    # Get current file content
    content = mock_filesystem[file_path]

    # Check if old_string exists in the file
    if old_string not in content:
        return f"Error: String not found in file: '{old_string}'"

    # If not replace_all, check for uniqueness
    if not replace_all:
        occurrences = content.count(old_string)
        if occurrences > 1:
            return f"Error: String '{old_string}' appears {occurrences} times in file. Use replace_all=True to replace all instances, or provide a more specific string with surrounding context."
        elif occurrences == 0:
            return f"Error: String not found in file: '{old_string}'"

    # Perform the replacement
    if replace_all:
        new_content = content.replace(old_string, new_string)
        replacement_count = content.count(old_string)
        result_msg = f"Successfully replaced {replacement_count} instance(s) of the string in '{file_path}'"
    else:
        new_content = content.replace(
            old_string, new_string, 1
        )  # Replace only first occurrence
        result_msg = f"Successfully replaced string in '{file_path}'"

    # Update the mock filesystem
    mock_filesystem[file_path] = new_content
    return {"files": mock_filesystem}

def get_tools():
    return [
        update_state,
        update_todo,
        write_todos,
        read_file,
        edit_file,
    ]
