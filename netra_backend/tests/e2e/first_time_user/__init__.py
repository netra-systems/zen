import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent

"""
First-Time User E2E Test Package

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Free users  ->  Paid conversions (10,000+ potential users)
2. **Business Goal**: Increase conversion rate from 2% to 15% = 6.5x improvement
3. **Value Impact**: Each test validates $99-$999/month revenue per conversion
4. **Revenue Impact**: Optimized journey = +$1.2M ARR from improved conversions
5. **Growth Engine**: First experience determines 95% of conversion probability

This package contains the TOP 10 CRITICAL First-Time User E2E Tests split into
modular components following the MANDATORY 450-line limit.

Modules:
- test_onboarding_e2e.py: Tests 1, 2, 5 (onboarding and demo)
- test_provider_connection_e2e.py: Tests 3, 4, 6 (AI provider and optimization)
- test_conversion_flow_e2e.py: Tests 7, 8 (cost calculator and upgrade)
- test_recovery_support_e2e.py: Tests 9, 10 (abandonment and errors)
- helpers.py: Shared fixtures and utilities
"""