# Netra Platform Documentation

## 📚 Documentation Index

### Getting Started
- **[CUSTOMER_GETTING_STARTED.md](CUSTOMER_GETTING_STARTED.md)** ⭐ - **PRIMARY GUIDE** - Complete getting started for development and usage
- **[STAGING_SECRETS_GUIDE.md](STAGING_SECRETS_GUIDE.md)** ⭐ - **CRITICAL** - Secrets management for all environments
- **[DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md)** - Additional development setup details
- **[DEVELOPER_WELCOME_GUIDE.md](DEVELOPER_WELCOME_GUIDE.md)** - Onboarding guide for new developers

### Staging & Deployment
- **[STAGING_DEPLOYMENT_COMPLETE_GUIDE.md](STAGING_DEPLOYMENT_COMPLETE_GUIDE.md)** ⭐ - Comprehensive staging deployment guide
- **[STAGING_TROUBLESHOOTING.md](STAGING_TROUBLESHOOTING.md)** - Staging environment troubleshooting
- **[GOOGLE_SECRET_MANAGER_SETUP.md](GOOGLE_SECRET_MANAGER_SETUP.md)** - Secret management for staging/production
- **[CREATE_GEMINI_KEY_STAGING.md](CREATE_GEMINI_KEY_STAGING.md)** - Setting up Gemini API key for staging
- **[STAGING_ENVIRONMENTS.md](STAGING_ENVIRONMENTS.md)** - Overview of staging architecture
- **[STAGING_OPTIMIZATION.md](STAGING_OPTIMIZATION.md)** - Performance optimizations for staging
- **[DEPLOYMENT_OPERATIONS.md](DEPLOYMENT_OPERATIONS.md)** - Production deployment procedures

### Architecture & Design
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture overview
- **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - Database design and schema
- **[AGENT_SYSTEM.md](AGENT_SYSTEM.md)** - Multi-agent architecture documentation
- **[WEBSOCKET_IMPLEMENTATION.md](WEBSOCKET_IMPLEMENTATION.md)** - Real-time communication design

### API & Integration
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - REST API reference
- **[API_REFERENCE.md](API_REFERENCE.md)** - Detailed API endpoints
- **[AUTHENTICATION_SECURITY.md](AUTHENTICATION_SECURITY.md)** - Auth system documentation
- **[oauth-setup.md](oauth-setup.md)** - OAuth configuration guide

### Testing
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Comprehensive testing documentation
- **[e2e-critical-tests-plan.md](e2e-critical-tests-plan.md)** - End-to-end test planning

### Subagents & Tools
- **[subagents.md](subagents.md)** - Subagent system documentation
- **[subagents-doc.md](subagents-doc.md)** - Additional subagent details
- **[MCP_IMPLEMENTATION_REPORT.md](MCP_IMPLEMENTATION_REPORT.md)** - Model Context Protocol implementation

### Troubleshooting & Reports
- **[CLICKHOUSE_PERMISSIONS_ERROR.md](CLICKHOUSE_PERMISSIONS_ERROR.md)** - ClickHouse troubleshooting
- **[backend_crash_aug_12.md](backend_crash_aug_12.md)** - Incident report
- **[SYSTEM_IMPROVEMENT_REPORT.md](SYSTEM_IMPROVEMENT_REPORT.md)** - System optimization report
- **[fake_tests_report.md](fake_tests_report.md)** - Test quality analysis

### Recent Updates & Summaries
- **[REFACTORING_COMPLETE.md](REFACTORING_COMPLETE.md)** - Recent refactoring summary
- **[CHAT_UI_IMPROVEMENTS_SUMMARY.md](CHAT_UI_IMPROVEMENTS_SUMMARY.md)** - UI enhancement summary
- **[WEBSOCKET_FIX_SUMMARY.md](WEBSOCKET_FIX_SUMMARY.md)** - WebSocket fixes
- **[JSON_EXTRACTION_FIX_DOCUMENTATION.md](JSON_EXTRACTION_FIX_DOCUMENTATION.md)** - JSON parsing improvements

## 🚀 Quick Links

### For Developers
1. **Start with [CUSTOMER_GETTING_STARTED.md](CUSTOMER_GETTING_STARTED.md)** - Primary development guide
2. **Configure secrets with [STAGING_SECRETS_GUIDE.md](STAGING_SECRETS_GUIDE.md)** - Critical for all environments
3. Review [STAGING_DEPLOYMENT_COMPLETE_GUIDE.md](STAGING_DEPLOYMENT_COMPLETE_GUIDE.md) for cloud deployment
4. Check [TESTING_GUIDE.md](TESTING_GUIDE.md) for testing practices

### For DevOps
1. **[STAGING_SECRETS_GUIDE.md](STAGING_SECRETS_GUIDE.md)** - Complete secrets architecture
2. [STAGING_DEPLOYMENT_COMPLETE_GUIDE.md](STAGING_DEPLOYMENT_COMPLETE_GUIDE.md) - Deployment procedures
3. [GOOGLE_SECRET_MANAGER_SETUP.md](GOOGLE_SECRET_MANAGER_SETUP.md) - Secret Manager setup
4. [STAGING_TROUBLESHOOTING.md](STAGING_TROUBLESHOOTING.md) - Troubleshooting guide

### For Product Managers
1. [ARCHITECTURE.md](ARCHITECTURE.md)
2. [AGENT_SYSTEM.md](AGENT_SYSTEM.md)
3. [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

## 📖 Documentation Standards

### File Naming Convention
- Use UPPERCASE for main documentation: `STAGING_DEPLOYMENT.md`
- Use lowercase for specific guides: `oauth-setup.md`
- Include dates for reports: `backend_crash_aug_12.md`

### Content Structure
Each document should include:
1. **Title** - Clear, descriptive title
2. **Table of Contents** - For documents > 100 lines
3. **Overview** - Brief introduction
4. **Main Content** - Well-organized sections
5. **Examples** - Code snippets and commands
6. **Troubleshooting** - Common issues
7. **References** - Links to related docs

### Updating Documentation
When making changes:
1. Update the relevant `.md` file
2. Update this index if adding new files
3. Update [CLAUDE.md](../CLAUDE.md) for AI assistant context
4. Include in PR description what docs were updated

## 🔄 Recent Updates (December 2025)

### Staging Environment Enhancements
- ✅ Automatic `-staging` suffix for secrets
- ✅ Numerical project ID support for Secret Manager
- ✅ Gemini API key as primary LLM provider
- ✅ Optional branded LLM providers (OpenAI, Anthropic, etc.)
- ✅ Improved environment detection
- ✅ Comprehensive troubleshooting guide

### Documentation Improvements
- ✅ **UPDATED: Unified Getting Started Guide** - Combined development and user documentation
- ✅ **UPDATED: Comprehensive Secrets Guide** - Complete security architecture for all environments
- ✅ **ALIGNED: Dev launcher commands** - Updated to match actual `dev_launcher.py` and `test_runner.py`
- ✅ **ADDED: Security isolation details** - Production secrets isolation architecture
- ✅ Complete staging deployment guide
- ✅ Troubleshooting guide for staging
- ✅ Documentation index (this file)

## 📝 Contributing to Documentation

### Guidelines
1. **Be Clear**: Write for developers who are new to the project
2. **Be Complete**: Include all necessary steps and context
3. **Be Current**: Update docs when code changes
4. **Be Concise**: Get to the point, use examples
5. **Be Correct**: Test all commands and code snippets

### Review Process
1. Documentation changes require review
2. Test all commands in the documentation
3. Update related documents if needed
4. Include screenshots for UI changes

## 🆘 Getting Help

- **Slack**: #platform-docs
- **GitHub Issues**: Label with `documentation`
- **Wiki**: Internal confluence (for sensitive info)

---

**Last Updated**: December 2025
**Maintained By**: Netra Platform Team
**Version**: 2.0.0