"""Handlers Tests - Split from test_dev_launcher_errors.py"""

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

import pytest
import requests

from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.cache_manager import CacheManager
from dev_launcher.error_detector import ErrorDetector
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.process_manager import ProcessManager


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def __init__(self, error_detector: ErrorDetector):
        super().__init__()
        self.error_detector = error_detector

    def emit(self, record):
        """Handle log record."""
        if record.levelno >= logging.ERROR:
            message = self.format(record)
            self.error_detector._check_line_for_errors(message, 'launcher', 'log')
