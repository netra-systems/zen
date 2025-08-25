"""
Test coverage for LogParser utility class.
"""

import pytest
from netra_backend.app.utils.log_parser import LogParser


class TestLogParser:
    """Test cases for LogParser class."""

    def test_parse_tool_call_basic_string_args(self):
        """Test parsing basic tool call with string arguments."""
        tool_string = 'MyTool(arg1="hello", arg2="world")'
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "MyTool",
            "args": {"arg1": "hello", "arg2": "world"}
        }
        assert result == expected

    def test_parse_tool_call_mixed_types(self):
        """Test parsing tool call with mixed argument types."""
        tool_string = 'TestTool(string_arg="test", int_arg=42, bool_arg=True, float_arg=3.14)'
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "TestTool",
            "args": {
                "string_arg": "test",
                "int_arg": 42,
                "bool_arg": True,
                "float_arg": 3.14
            }
        }
        assert result == expected

    def test_parse_tool_call_nested_dict(self):
        """Test parsing tool call with nested dictionary arguments."""
        tool_string = 'ComplexTool(config={"key": "value", "nested": {"num": 123}})'
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "ComplexTool",
            "args": {
                "config": {"key": "value", "nested": {"num": 123}}
            }
        }
        assert result == expected

    def test_parse_tool_call_list_args(self):
        """Test parsing tool call with list arguments."""
        tool_string = 'ListTool(items=["a", "b", "c"], numbers=[1, 2, 3])'
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "ListTool",
            "args": {
                "items": ["a", "b", "c"],
                "numbers": [1, 2, 3]
            }
        }
        assert result == expected

    def test_parse_tool_call_no_args(self):
        """Test parsing tool call with no arguments."""
        tool_string = 'EmptyTool()'
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "EmptyTool",
            "args": {}
        }
        assert result == expected

    def test_parse_tool_call_whitespace_handling(self):
        """Test parsing tool call with various whitespace patterns."""
        tool_string = '  WhiteSpaceTool  ( arg1 = "value1" , arg2 = 42 )  '
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "WhiteSpaceTool",
            "args": {"arg1": "value1", "arg2": 42}
        }
        assert result == expected

    def test_parse_tool_call_multiline(self):
        """Test parsing tool call with multiline arguments."""
        tool_string = '''MultilineTool(
            arg1="first line",
            arg2="second line",
            config={
                "key": "value"
            }
        )'''
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "MultilineTool",
            "args": {
                "arg1": "first line",
                "arg2": "second line",
                "config": {"key": "value"}
            }
        }
        assert result == expected

    def test_parse_tool_call_invalid_syntax(self):
        """Test parsing tool call with invalid syntax returns None."""
        invalid_strings = [
            'InvalidTool(arg1="unclosed_quote)',
            'BadTool(arg1=undefined_variable)',
            'NotATool',
            '',
            'MissingParens arg1="value"',
            'UnbalancedTool((arg1="value")',
        ]
        
        for invalid_string in invalid_strings:
            result = LogParser.parse_tool_call(invalid_string)
            assert result is None, f"Expected None for: {invalid_string}"

    def test_parse_tool_call_special_characters(self):
        """Test parsing tool call with special characters in values."""
        tool_string = 'SpecialTool(path="/home/user/file.txt", regex=r"\\d+", emoji="😀")'
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "SpecialTool",
            "args": {
                "path": "/home/user/file.txt",
                "regex": r"\d+",
                "emoji": "😀"
            }
        }
        assert result == expected

    def test_parse_tool_call_none_and_boolean_values(self):
        """Test parsing tool call with None and boolean values."""
        tool_string = 'NullTool(null_value=None, true_value=True, false_value=False)'
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "NullTool",
            "args": {
                "null_value": None,
                "true_value": True,
                "false_value": False
            }
        }
        assert result == expected

    def test_parse_log_message_tool_call(self):
        """Test parsing log message that contains a tool call."""
        log_message = 'LogTool(message="Hello World", level="INFO")'
        result = LogParser.parse_log_message(log_message)
        
        expected = {
            "type": "tool_call",
            "data": {
                "name": "LogTool",
                "args": {"message": "Hello World", "level": "INFO"}
            }
        }
        assert result == expected

    def test_parse_log_message_regular_message(self):
        """Test parsing log message that is not a tool call."""
        log_message = "This is just a regular log message"
        result = LogParser.parse_log_message(log_message)
        
        expected = {
            "type": "message",
            "data": "This is just a regular log message"
        }
        assert result == expected

    def test_parse_log_message_empty_string(self):
        """Test parsing empty log message."""
        log_message = ""
        result = LogParser.parse_log_message(log_message)
        
        expected = {
            "type": "message",
            "data": ""
        }
        assert result == expected

    def test_parse_log_message_tool_call_like_but_invalid(self):
        """Test parsing log message that looks like tool call but is invalid."""
        log_message = "SomeTool(invalid syntax here"
        result = LogParser.parse_log_message(log_message)
        
        expected = {
            "type": "message",
            "data": "SomeTool(invalid syntax here"
        }
        assert result == expected

    def test_parse_tool_call_numeric_edge_cases(self):
        """Test parsing tool call with various numeric edge cases."""
        tool_string = 'NumericTool(zero=0, negative=-42, scientific=1.23e-4, hex_like_string="0x123")'
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "NumericTool",
            "args": {
                "zero": 0,
                "negative": -42,
                "scientific": 1.23e-4,
                "hex_like_string": "0x123"
            }
        }
        assert result == expected

    def test_parse_tool_call_nested_structures(self):
        """Test parsing tool call with deeply nested structures."""
        tool_string = '''NestedTool(
            data={
                "level1": {
                    "level2": [
                        {"key": "value", "number": 42},
                        {"another": "item", "bool": True}
                    ]
                }
            }
        )'''
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "NestedTool",
            "args": {
                "data": {
                    "level1": {
                        "level2": [
                            {"key": "value", "number": 42},
                            {"another": "item", "bool": True}
                        ]
                    }
                }
            }
        }
        assert result == expected

    def test_parse_tool_call_underscore_tool_name(self):
        """Test parsing tool call with underscores in tool name."""
        tool_string = 'my_tool_name(arg="value")'
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "my_tool_name",
            "args": {"arg": "value"}
        }
        assert result == expected

    def test_parse_tool_call_single_character_args(self):
        """Test parsing tool call with single character argument names."""
        tool_string = 'Tool(x=1, y=2, z="test")'
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "Tool",
            "args": {"x": 1, "y": 2, "z": "test"}
        }
        assert result == expected

    def test_parse_tool_call_trailing_comma(self):
        """Test parsing tool call with trailing comma (valid Python syntax)."""
        tool_string = 'ToolWithTrailingComma(arg1="value",)'
        result = LogParser.parse_tool_call(tool_string)
        
        expected = {
            "name": "ToolWithTrailingComma",
            "args": {"arg1": "value"}
        }
        assert result == expected