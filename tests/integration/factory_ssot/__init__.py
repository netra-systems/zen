"""
Factory SSOT Integration Tests Package

This package contains integration tests that validate Single Source of Truth (SSOT)
violations in factory patterns throughout the Netra Apex codebase.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate factory pattern violations blocking golden path
- Value Impact: Protect $120K+ MRR through SSOT compliance and reduced race conditions
- Strategic Impact: Critical infrastructure stability for multi-user production deployment

Test Categories:
1. ExecutionEngineFactory vs AgentInstanceFactory duplication (5 tests)
2. WebSocket factory chain violations (4 tests)  
3. Database factory over-abstraction patterns (4 tests)
4. Configuration factory redundancy (3 tests)
5. Tool dispatcher factory violations (2 tests)
6. Message handler factory patterns (2 tests)

These tests identify SSOT violations identified in the over-engineering audit
that shows 78 factory classes creating unnecessary abstraction layers.
"""

__version__ = "1.0.0"
__author__ = "Netra Apex Development Team"