import sys

import os

from pathlib import Path



# Add project root to path for imports

PROJECT_ROOT = Path(__file__).resolve().parent



"""

Agent Isolation Test Module



This module contains the refactored agent resource isolation tests,

split by isolation type to maintain the 300-line file limit per SPEC/testing.xml.



The original test_agent_resource_isolation.py (1,640 lines) has been refactored into:

- test_memory_isolation.py - Memory isolation tests

- test_cpu_isolation.py - CPU isolation tests  

- test_network_isolation.py - Network isolation tests

- test_file_system_isolation.py - File system isolation tests

- test_multi_tenant_isolation.py - Multi-tenant isolation tests



Business Value Justification (BVJ):

- Segment: Enterprise (multi-tenant isolation requirements)

- Business Goal: Ensure secure per-tenant resource isolation  

- Value Impact: Prevents performance degradation affecting $500K+ enterprise contracts

- Revenue Impact: Essential for enterprise trust and SLA compliance

"""

