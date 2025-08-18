"""
Agent System Tests - Index
Imports all modular agent test suites. This file serves as a central index
for all agent tests split across multiple modules for 300-line compliance.
"""

# Import all test modules to ensure they're discovered by pytest
from app.tests.test_agents_supervisor import TestSupervisorAgent, TestIntegration
from app.tests.test_agents_subagents import (
    TestTriageSubAgent,
    TestDataSubAgent, 
    TestOptimizationSubAgent,
    TestActionsSubAgent,
    TestReportingSubAgent
)
from app.tests.test_agents_infrastructure import (
    TestToolDispatcher,
    TestStateManagement,
    TestAgentLifecycle
)

# Re-export all test classes for pytest discovery
__all__ = [
    "TestSupervisorAgent",
    "TestTriageSubAgent", 
    "TestDataSubAgent",
    "TestOptimizationSubAgent",
    "TestActionsSubAgent",
    "TestReportingSubAgent",
    "TestToolDispatcher",
    "TestStateManagement", 
    "TestAgentLifecycle",
    "TestIntegration"
]