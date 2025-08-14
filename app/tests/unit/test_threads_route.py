"""
Main test file for threads route - imports all split test modules.

This file was refactored to meet the 300-line limit by splitting into:
- test_threads_route_list.py - list_threads tests
- test_threads_route_create.py - create_thread tests  
- test_threads_route_get.py - get_thread tests
- test_threads_route_update.py - update_thread tests
- test_threads_route_delete.py - delete_thread tests
- test_threads_route_messages.py - get_thread_messages tests
- test_threads_route_rename.py - auto_rename_thread tests
- test_threads_route_models.py - router and model tests

All functions were refactored to be ≤8 lines using helper functions from:
- app.tests.helpers.thread_test_helpers

To run all thread tests:
pytest app/tests/unit/test_threads_route*.py -v
"""

# Import all test classes to ensure they run when this file is executed
from app.tests.unit.test_threads_route_list import TestListThreads
from app.tests.unit.test_threads_route_create import TestCreateThread  
from app.tests.unit.test_threads_route_get import TestGetThread
from app.tests.unit.test_threads_route_update import TestUpdateThread
from app.tests.unit.test_threads_route_delete import TestDeleteThread
from app.tests.unit.test_threads_route_messages import TestGetThreadMessages
from app.tests.unit.test_threads_route_rename import TestAutoRenameThread
from app.tests.unit.test_threads_route_models import TestRouterConfiguration, TestPydanticModels

__all__ = [
    'TestListThreads',
    'TestCreateThread', 
    'TestGetThread',
    'TestUpdateThread',
    'TestDeleteThread',
    'TestGetThreadMessages',
    'TestAutoRenameThread',
    'TestRouterConfiguration',
    'TestPydanticModels'
]