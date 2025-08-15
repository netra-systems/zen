#!/usr/bin/env python3
"""
Autonomous Test Review System - Entry Point
Wrapper script for the autonomous test review system
"""

import asyncio
from autonomous_review.main import main

if __name__ == "__main__":
    asyncio.run(main())