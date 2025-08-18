#!/usr/bin/env python
"""Quick script to view test results."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_framework.test_dashboard import main

if __name__ == "__main__":
    main()