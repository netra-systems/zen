# Shim module for test backward compatibility
from test_framework.fixtures import *
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.utils import setup_test_environment

__all__ = ['BaseIntegrationTest', 'setup_test_environment']
