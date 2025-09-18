# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Issue #1320**: Windows permission errors now properly handled
  - Added platform-specific permission mode detection
  - Windows automatically uses `bypassPermissions` mode
  - Enhanced error visibility for permission denials
  - No longer silently fails when commands are blocked
  - See [Issue #1320 Documentation](../docs/issues/ISSUE_1320_ZEN_PERMISSION_ERROR_FIX.md) for details

### Changed
- Permission mode now auto-detects platform (Windows vs Mac/Linux)
- Added prominent error reporting for command blocking issues
- Enhanced error detection in JSON responses
- Improved logging at CRITICAL level for permission errors

## [1.0.0] - 2024-01-17

### Added
- Initial release of Zen Orchestrator
- Multi-instance Claude Code orchestration
- Parallel task execution capabilities
- Token budget management and transparency
- Configurable instance management
- Support for custom workspace directories
- Dry-run mode for command inspection
- Status reporting and monitoring
- Startup delay configuration
- Scheduled execution support
- Cloud SQL integration (optional)
- Comprehensive logging and error handling

### Features
- Command-line interface with `zen` command
- JSON configuration file support
- Real-time status updates
- Token usage tracking and reporting
- Built-in slash command support
- Customizable output formats (json, stream-json)
- Timeout management per instance
- Quiet mode for minimal output
- Line length and console output controls

### Documentation
- Complete README with usage examples
- Configuration examples (minimal, standard, advanced)
- Integration guides for Netra Apex
- Token transparency documentation
- API documentation for agent interface

[Unreleased]: https://github.com/netra-systems/zen/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/netra-systems/zen/releases/tag/v1.0.0