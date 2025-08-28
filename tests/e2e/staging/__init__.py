"""Staging environment specific tests.

These tests are designed to run against staging infrastructure and validate
critical integration issues that have been found in production-like environments.

All tests in this module are marked with @staging_only to ensure they only run
when explicitly targeting the staging environment.
"""