"""Handlers Tests - Split from test_dev_launcher_errors.py"""

import asyncio
import pytest
import time
import sys
import os
import subprocess
import signal
import requests
import logging
import re
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Pattern
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import tempfile
from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.process_manager import ProcessManager
from dev_launcher.cache_manager import CacheManager
import socket


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
