"""Core_2 Tests - Split from test_dev_launcher_errors.py"""



import asyncio

import json

import logging

import os

import re

import signal

import socket

import subprocess

import sys

import tempfile

import threading

import time

from concurrent.futures import ThreadPoolExecutor

from pathlib import Path

from queue import Empty, Queue

from typing import Dict, List, Optional, Pattern, Tuple

from shared.isolated_environment import IsolatedEnvironment



import pytest

import requests



from dev_launcher import DevLauncher, LauncherConfig

from dev_launcher.cache_manager import CacheManager

from dev_launcher.health_monitor import HealthMonitor

from dev_launcher.process_manager import ProcessManager





class TestSyntaxFix:

    """Test class for orphaned methods"""



    def create_test_config(self, **kwargs) -> LauncherConfig:

        """Create test configuration."""

        config = LauncherConfig()

        config.backend_port = kwargs.get('backend_port', 8000)

        config.frontend_port = kwargs.get('frontend_port', 3000) if not kwargs.get('skip_frontend', True) else None

        config.dynamic_ports = False

        config.no_backend_reload = True

        config.no_browser = True

        config.verbose = kwargs.get('verbose', True)  # Enable verbose for error detection

        config.non_interactive = True

        config.startup_mode = kwargs.get('startup_mode', 'minimal')

        config.no_secrets = kwargs.get('no_secrets', True)

        config.parallel_startup = kwargs.get('parallel_startup', True)

        config.project_root = project_root

        return config

