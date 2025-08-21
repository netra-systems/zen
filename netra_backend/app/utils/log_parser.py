import ast
import re


class LogParser:
    """
    Parses various string-formatted log entries into structured Python dictionaries.
    """

    @staticmethod
    def parse_tool_call(tool_string: str) -> dict | None:
        """
        Parses a LangChain-style tool call string into a dictionary using AST.

        Args:
            tool_string: The tool call string, e.g., 
                         'MyTool(arg1="hello", arg2=123, nested={"key": "val"})'.

        Returns:
            A dictionary with 'name' and 'args' keys, or None if parsing fails.
            e.g., {'name': 'MyTool', 'args': {'arg1': 'hello', 'arg2': 123, 'nested': {'key': 'val'}}}
        """
        tool_match = _extract_tool_name_and_args(tool_string)
        if not tool_match:
            return None
        
        tool_name, args_string = tool_match
        if not args_string.strip():
            return {"name": tool_name, "args": {}}
        
        parsed_args = _parse_tool_arguments(args_string)
        if parsed_args is None:
            return None
        
        return {"name": tool_name, "args": parsed_args}

    @staticmethod
    def parse_log_message(log_message: str) -> dict | None:
        """
        Parses a log message and attempts to extract structured data.

        Args:
            log_message: The log message string.

        Returns:
            A dictionary with the parsed data, or None if parsing fails.
        """
        parsed_tool = LogParser.parse_tool_call(log_message)
        if parsed_tool:
            return {"type": "tool_call", "data": parsed_tool}
        return {"type": "message", "data": log_message}


def _extract_tool_name_and_args(tool_string: str) -> tuple | None:
    """Extract tool name and arguments string from tool call."""
    match = re.match(r"(\w+)\s*\((.*)\)$", tool_string.strip(), re.DOTALL)
    if not match:
        return None
    return match.groups()


def _parse_tool_arguments(args_string: str) -> dict | None:
    """Parse tool arguments using AST."""
    try:
        wrapper = f"func({args_string.strip()})"
        tree = ast.parse(wrapper, mode='eval')
        call_node = tree.body
        return _extract_keyword_arguments(call_node)
    except (SyntaxError, ValueError):
        return None


def _extract_keyword_arguments(call_node) -> dict:
    """Extract keyword arguments from AST call node."""
    parsed_args = {}
    for keyword in call_node.keywords:
        key = keyword.arg
        value = ast.literal_eval(keyword.value)
        parsed_args[key] = value
    return parsed_args
