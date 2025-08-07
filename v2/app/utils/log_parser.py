import re
import ast

class LogParser:
    """
    Parses various string-formatted log entries into structured Python dictionaries.
    """

    @staticmethod
    def parse_tool_call(tool_string: str) -> dict | None:
        """
        Parses a LangChain-style tool call string into a dictionary using regex.

        Args:
            tool_string: The tool call string, e.g., 
                         'MyTool(arg1="hello", arg2=123, nested={"key": "val"})'.

        Returns:
            A dictionary with 'name' and 'args' keys, or None if parsing fails.
            e.g., {'name': 'MyTool', 'args': {'arg1': 'hello', 'arg2': 123, 'nested': {'key': 'val'}}}
        """
        # 1. Regex to extract the tool name and the arguments string
        # (?s) flag allows '.' to match newlines for multiline arguments
        match = re.match(r"(\w+)\((?s)(.*)\)$", tool_string.strip())
        if not match:
            return None

        tool_name, args_string = match.groups()
        parsed_args = {}

        if not args_string.strip():
            return {"name": tool_name, "args": {}}

        # 2. Regex to find all key=value pairs
        # This pattern correctly handles nested structures and quoted strings
        # It looks for a word (key), an equals sign, and then captures the value.
        # The value can be a quoted string or any sequence of characters
        # that are not a top-level comma.
        kv_pattern = re.compile(r'(\w+)\s*=\s*("(?:\\"|[^\"])*"|\\'(?:\\\'|[^\\\'])*\'|\[.*?\]|\{.*?\}|[^,]+)')

        for kv_match in kv_pattern.finditer(args_string):
            key = kv_match.group(1).strip()
            value_str = kv_match.group(2).strip()

            try:
                # 3. Use ast.literal_eval to safely convert the value string
                # to its Python type (str, int, bool, list, dict, etc.)
                value = ast.literal_eval(value_str)
            except (ValueError, SyntaxError):
                # If literal_eval fails, it's likely an unquoted string
                # that is not a recognized literal (like a variable name).
                # We will treat it as a raw string.
                value = value_str
            
            parsed_args[key] = value

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
        # Attempt to parse as a tool call first
        parsed_tool = LogParser.parse_tool_call(log_message)
        if parsed_tool:
            return {"type": "tool_call", "data": parsed_tool}

        # Add other parsing logic here for different log formats
        # For now, we'll just return a generic message if no specific format is matched
        return {"type": "message", "data": log_message}
