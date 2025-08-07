import re
import ast

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
        # Allow whitespace between tool name and arguments
        match = re.match(r"(\w+)\s*\((.*)\)$", tool_string.strip(), re.DOTALL)
        if not match:
            return None

        tool_name, args_string = match.groups()
        parsed_args = {}

        if not args_string.strip():
            return {"name": tool_name, "args": {}}

        try:
            # Wrap the arguments in a function call to create a valid AST
            wrapper = f"func({args_string.strip()})"
            tree = ast.parse(wrapper, mode='eval')
            
            # The body of the parsed expression is a Call node
            call_node = tree.body
            
            # Extract keyword arguments
            for keyword in call_node.keywords:
                key = keyword.arg
                # Safely evaluate the value of the argument
                value = ast.literal_eval(keyword.value)
                parsed_args[key] = value

        except (SyntaxError, ValueError):
            # Fallback for cases where parsing fails
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
