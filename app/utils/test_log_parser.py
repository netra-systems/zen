import pytest
from app.utils.log_parser import LogParser

@pytest.mark.parametrize(
    "tool_string, expected_output",
    [
        (
            'MyTool(arg1="hello", arg2=123, nested={"key": "val"})',
            {'name': 'MyTool', 'args': {'arg1': 'hello', 'arg2': 123, 'nested': {'key': 'val'}}},
        ),
        (
            'AnotherTool(arg1 =  "world")',
            {'name': 'AnotherTool', 'args': {'arg1': 'world'}},
        ),
        (
            'ToolWithNoArgs()',
            {'name': 'ToolWithNoArgs', 'args': {}},
        ),
        (
            '  SpacedTool  (  arg = 1 )  ',
            {'name': 'SpacedTool', 'args': {'arg': 1}},
        ),
        (
            'ToolWithList(items=[1, "two", True])',
            {'name': 'ToolWithList', 'args': {'items': [1, 'two', True]}},
        ),
        (
            'InvalidTool',
            None,
        ),
    ],
)
def test_parse_tool_call(tool_string, expected_output):
    assert LogParser.parse_tool_call(tool_string) == expected_output

@pytest.mark.parametrize(
    "log_message, expected_output",
    [
        (
            'MyTool(arg1="hello")',
            {'type': 'tool_call', 'data': {'name': 'MyTool', 'args': {'arg1': 'hello'}}},
        ),
        (
            'This is a regular log message.',
            {'type': 'message', 'data': 'This is a regular log message.'},
        ),
    ],
)
def test_parse_log_message(log_message, expected_output):
    assert LogParser.parse_log_message(log_message) == expected_output