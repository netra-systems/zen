"""
Modular configuration system for Netra Apex.

This package provides a consolidated configuration system with clear separation:
- schemas.py: All configuration data models  
- environment.py: Environment detection logic
- secrets.py: Secret management operations
- loaders.py: Environment variable loading utilities

Single source of truth: app.config provides the main interface.
"""