# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Refactor admin_tool_dispatcher.py - Create module init file
# Git: anthony-aug-13-2 | Refactoring for modularity
# Change: Create | Scope: Module | Risk: Low
# Session: admin-tool-refactor | Seq: 5
# Review: Pending | Score: 95
# ================================
"""
Admin Tool Dispatcher Module

Modular implementation of admin tool dispatcher functionality
split from monolithic file to comply with CLAUDE.md standards.
"""
from .dispatcher_core import AdminToolDispatcher

__all__ = ["AdminToolDispatcher"]