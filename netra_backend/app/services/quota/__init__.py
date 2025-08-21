"""Quota Management Service Package

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable test execution and prevent quota import errors
- Value Impact: Ensures test suite can import quota management dependencies
- Strategic Impact: Maintains compatibility for quota functionality
"""

from netra_backend.app.quota_manager import QuotaManager

__all__ = ["QuotaManager"]