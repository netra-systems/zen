"""Analytics service module.

Business Value Justification (BVJ):
- Segment: Enterprise (comprehensive cost tracking and analytics requirements)
- Business Goal: Provide detailed analytics and cost tracking for AI operations
- Value Impact: Enables cost optimization and usage insights for all tiers
- Revenue Impact: Supports cost-conscious customers and enterprise analytics needs
"""

from .cost_tracker import CostTracker

__all__ = ["CostTracker"]