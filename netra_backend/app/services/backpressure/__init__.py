"""Backpressure Service Package

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable test execution and prevent backpressure import errors
- Value Impact: Ensures test suite can import backpressure management dependencies
- Strategic Impact: Maintains compatibility for backpressure functionality
"""

from netra_backend.app.services.backpressure.backpressure_service import BackpressureService

__all__ = ["BackpressureService"]