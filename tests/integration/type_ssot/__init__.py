"""
Type SSOT Integration Tests

This module contains comprehensive integration tests for validating and enforcing
Single Source of Truth (SSOT) compliance across type definitions in the Netra Apex
platform. These tests are critical for maintaining type consistency and preventing
the 110+ type duplication violations identified in the over-engineering audit.

Test Categories:
- ThreadState duplication detection and consolidation
- AuthContextType and JWTPayload consistency validation  
- Frontend/Backend type synchronization enforcement
- Props and State definition scattered pattern detection
- ReportData type definition violation analysis
- Schema generation and synchronization enforcement

Business Value:
These tests protect $120K+ MRR by ensuring type consistency across the golden path,
preventing runtime errors, API contract violations, and development confusion that
directly impacts platform reliability and user experience.
"""