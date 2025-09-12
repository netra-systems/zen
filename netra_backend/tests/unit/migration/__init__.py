"""
DeepAgentState  ->  UserExecutionContext Migration Test Suite

This test suite validates the migration from DeepAgentState to UserExecutionContext
for Issue #271 remediation (user isolation vulnerability).

Tests are designed to FAIL while DeepAgentState is still in use,
and PASS once migration to UserExecutionContext is complete.
"""