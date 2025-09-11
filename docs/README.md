# Netra Apex Platform Documentation

## 📚 Documentation Index

### Core Architecture & Guidelines
- **[CUSTOMER_GETTING_STARTED.md](development/CUSTOMER_GETTING_STARTED.md)** ⭐ - **PRIMARY GUIDE** - Complete getting started for development and usage
- **[CONFIGURATION_GUIDE.md](configuration/CONFIGURATION_GUIDE.md)** ⭐ - **NEW** - Complete environment configuration guide
- **[STAGING_SECRETS_GUIDE.md](deployment/STAGING_SECRETS_GUIDE.md)** ⭐ - **CRITICAL** - Secrets management for all environments
- **[DEVELOPMENT_SETUP.md](development/DEVELOPMENT_SETUP.md)** - Additional development setup details
- **[DEVELOPER_WELCOME_GUIDE.md](development/DEVELOPER_WELCOME_GUIDE.md)** - Onboarding guide for new developers

### Staging & Deployment
- **[PRODUCTION_DEPLOYMENT.md](deployment/PRODUCTION_DEPLOYMENT.md)** ⭐ - **NEW** - Complete production deployment guide
- **[STAGING_DEPLOYMENT_COMPLETE_GUIDE.md](deployment/STAGING_DEPLOYMENT_COMPLETE_GUIDE.md)** ⭐ - Comprehensive staging deployment guide
- **[STAGING_TROUBLESHOOTING.md](deployment/STAGING_TROUBLESHOOTING.md)** - Staging environment troubleshooting
- **[GOOGLE_SECRET_MANAGER_SETUP.md](deployment/GOOGLE_SECRET_MANAGER_SETUP.md)** - Secret management for staging/production
- **[CREATE_GEMINI_KEY_STAGING.md](deployment/CREATE_GEMINI_KEY_STAGING.md)** - Setting up Gemini API key for staging
- **[STAGING_ENVIRONMENTS.md](deployment/STAGING_ENVIRONMENTS.md)** - Overview of staging architecture
- **[STAGING_OPTIMIZATION.md](deployment/STAGING_OPTIMIZATION.md)** - Performance optimizations for staging
- **[DEPLOYMENT_OPERATIONS.md](deployment/DEPLOYMENT_OPERATIONS.md)** - Production deployment procedures

### 🚨 CANONICAL DEPLOYMENT SOURCES (Updated)
**Week 1 SSOT Remediation - GitHub Issue #245**

**CANONICAL SOURCES:**
- **GCP Staging/Production**: `scripts/deploy_to_gcp_actual.py --project netra-staging`
- **Infrastructure**: `terraform-gcp-staging/` (All environments)
- **Local Development**: `docker-compose --profile dev up`
- **Local Testing**: `docker-compose --profile test up`

**DEPRECATED (Week 1 Wrappers Only):**
- ~~`scripts/deploy_to_gcp.py`~~ → Redirects to `scripts/deploy_to_gcp_actual.py`
- ~~`scripts/build_staging.py`~~ → Redirects to `docker-compose --profile dev`
- ~~`scripts/deploy-docker.sh/bat`~~ → Redirects to `docker-compose`
- ~~`terraform-dev-postgres/`~~ → Use `terraform-gcp-staging/` or `docker-compose`

### Architecture & Design
- **[ARCHITECTURE.md](architecture/ARCHITECTURE.md)** - System architecture overview
- **[DATABASE_SCHEMA.md](architecture/DATABASE_SCHEMA.md)** - Database design and schema
- **[AGENT_SYSTEM.md](agents/AGENT_SYSTEM.md)** - Multi-agent architecture documentation
- **[WEBSOCKET_IMPLEMENTATION.md](architecture/WEBSOCKET_IMPLEMENTATION.md)** - Real-time communication design
- **[String Literals Index](../SPEC/string_literals_index.xml)** - Platform constants reference

### API & Integration
- **[API_DOCUMENTATION.md](architecture/API_DOCUMENTATION.md)** - REST API reference
- **[API_REFERENCE.md](architecture/API_REFERENCE.md)** - Detailed API endpoints with tier-specific endpoints
- **[AUTHENTICATION_SECURITY.md](auth/AUTHENTICATION_SECURITY.md)** - Auth system documentation
- **[oauth-setup.md](auth/oauth-setup.md)** - OAuth configuration guide

### Testing
- **[TESTING_GUIDE.md](testing/TESTING_GUIDE.md)** - Comprehensive testing documentation
- **[e2e-critical-tests-plan.md](testing/e2e-critical-tests-plan.md)** - End-to-end test planning
- **[TESTING_WITH_FEATURE_FLAGS.md](testing/TESTING_WITH_FEATURE_FLAGS.md)** - Feature flag testing approach

### Operations & Monitoring
- **[MONITORING_GUIDE.md](operations/MONITORING_GUIDE.md)** ⭐ - **NEW** - Complete monitoring and SLA compliance guide
- **[Performance Monitoring](operations/MONITORING_GUIDE.md#performance-benchmarks)** - Performance benchmarks and SLOs
- **[Business Metrics](business/REVENUE_TRACKING.md)** ⭐ - **NEW** - Revenue tracking and ROI calculations

### Subagents & Tools
- **[subagents.md](agents/subagents.md)** - Subagent system documentation
- **[subagents-doc.md](agents/subagents-doc.md)** - Additional subagent details
- **[MCP_IMPLEMENTATION_REPORT.md](reports/MCP_IMPLEMENTATION_REPORT.md)** - Model Context Protocol implementation

### Business & Revenue
- **[REVENUE_TRACKING.md](business/REVENUE_TRACKING.md)** ⭐ - **NEW** - Complete revenue tracking and ROI methodology
- **[Business Metrics Integration](business/REVENUE_TRACKING.md#business-metrics-monitoring)** - Customer value analytics
- **[Tier-Based Value Creation](business/REVENUE_TRACKING.md#tier-based-value-metrics)** - Value creation by customer segment

### Configuration Management
- **[CONFIGURATION_GUIDE.md](configuration/CONFIGURATION_GUIDE.md)** ⭐ - **NEW** - Complete environment configuration reference
- **[Secrets Management](configuration/CONFIGURATION_GUIDE.md#secrets-management)** - Google Secret Manager integration
- **[Environment Variables](configuration/CONFIGURATION_GUIDE.md#environment-variables-reference)** - Complete variable reference

### Troubleshooting & Reports
- **[CLICKHOUSE_PERMISSIONS_ERROR.md](legacy/CLICKHOUSE_PERMISSIONS_ERROR.md)** - ClickHouse troubleshooting
- **[SYSTEM_IMPROVEMENT_REPORT.md](reports/SYSTEM_IMPROVEMENT_REPORT.md)** - System optimization report
- **[fake_tests_report.md](testing/fake_tests_report.md)** - Test quality analysis

### Recent Updates & Summaries
- **[REFACTORING_COMPLETE.md](reports/REFACTORING_COMPLETE.md)** - Recent refactoring summary
- **[CHAT_UI_IMPROVEMENTS_SUMMARY.md](reports/CHAT_UI_IMPROVEMENTS_SUMMARY.md)** - UI enhancement summary
- **[WEBSOCKET_FIX_SUMMARY.md](reports/WEBSOCKET_FIX_SUMMARY.md)** - WebSocket fixes
- **[JSON_EXTRACTION_FIX_DOCUMENTATION.md](reports/JSON_EXTRACTION_FIX_DOCUMENTATION.md)** - JSON parsing improvements

## 🚀 Quick Links

### For Developers
1. **Start with [CUSTOMER_GETTING_STARTED.md](development/CUSTOMER_GETTING_STARTED.md)** - Primary development guide with string literals validation
2. **Configure environment with [CONFIGURATION_GUIDE.md](configuration/CONFIGURATION_GUIDE.md)** - Complete configuration reference
3. **Setup secrets with [STAGING_SECRETS_GUIDE.md](deployment/STAGING_SECRETS_GUIDE.md)** - Critical for all environments
4. Review [PRODUCTION_DEPLOYMENT.md](deployment/PRODUCTION_DEPLOYMENT.md) for production deployment
5. Check [TESTING_GUIDE.md](testing/TESTING_GUIDE.md) for testing practices

### For DevOps
1. **[PRODUCTION_DEPLOYMENT.md](deployment/PRODUCTION_DEPLOYMENT.md)** - Complete production deployment procedures
2. **[MONITORING_GUIDE.md](operations/MONITORING_GUIDE.md)** - Comprehensive monitoring and SLA compliance
3. **[CONFIGURATION_GUIDE.md](configuration/CONFIGURATION_GUIDE.md)** - Environment configuration management
4. **[STAGING_SECRETS_GUIDE.md](deployment/STAGING_SECRETS_GUIDE.md)** - Complete secrets architecture
5. **CANONICAL:** `scripts/deploy_to_gcp_actual.py --project netra-staging` - Staging deployment
6. [GOOGLE_SECRET_MANAGER_SETUP.md](deployment/GOOGLE_SECRET_MANAGER_SETUP.md) - Secret Manager setup
7. [STAGING_TROUBLESHOOTING.md](deployment/STAGING_TROUBLESHOOTING.md) - Troubleshooting guide

### For Product Managers
1. **[REVENUE_TRACKING.md](business/REVENUE_TRACKING.md)** - Business metrics and ROI methodology
2. **[Customer Value Analytics](business/REVENUE_TRACKING.md#customer-value-analytics)** - Customer value scoring and churn prediction
3. [ARCHITECTURE.md](architecture/ARCHITECTURE.md) - System architecture overview
4. [AGENT_SYSTEM.md](agents/AGENT_SYSTEM.md) - Multi-agent system capabilities
5. [API_DOCUMENTATION.md](architecture/API_DOCUMENTATION.md) - API reference with tier-specific features

### For Business Teams
1. **[Business Value Creation](business/REVENUE_TRACKING.md#tier-based-value-metrics)** - Value creation by customer tier
2. **[ROI Calculation Framework](business/REVENUE_TRACKING.md#roi-calculation-framework)** - Customer and business ROI calculations
3. **[Savings Methodology](business/REVENUE_TRACKING.md#savings-calculation-methodology)** - How customer savings are calculated and validated

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

## 🔄 Recent Updates (January 2025)

### 🎯 Major Documentation Overhaul (January 20, 2025)
- ✅ **NEW: Production Deployment Guide** - Complete enterprise-grade deployment procedures
- ✅ **NEW: Monitoring & Observability Guide** - Comprehensive SLA compliance and performance monitoring
- ✅ **NEW: Revenue Tracking & Business Metrics** - Complete ROI methodology and customer value analytics
- ✅ **NEW: Configuration Management Guide** - Consolidated environment variable and secrets reference
- ✅ **UPDATED: README.md** - Added String Literals Index, tier-specific API endpoints, business metrics integration
- ✅ **ENHANCED: Getting Started Guide** - Added string literals validation workflow and complete developer workflow

### Business Intelligence Integration
- ✅ **Performance-Based Pricing Model** - 20% of customer savings revenue tracking
- ✅ **Tier-Based Value Creation** - Free, Early, Mid, Enterprise customer segment strategies
- ✅ **Customer ROI Calculations** - Comprehensive ROI tracking and validation framework
- ✅ **Business Metrics Monitoring** - Real-time revenue and customer value analytics

### System Reliability & Monitoring
- ✅ **Service Level Objectives (SLOs)** - 99.9% availability, <2s p99 latency, <30s agent response
- ✅ **Error Budget Management** - Automatic feature freeze when SLO breached
- ✅ **Three Pillars Implementation** - Comprehensive logging, metrics, and distributed tracing
- ✅ **Production Monitoring Stack** - Prometheus, Grafana, OpenTelemetry, structured logging

### Developer Experience Improvements
- ✅ **String Literals Index** - Centralized platform constants to prevent LLM hallucination
- ✅ **Configuration Validation** - Comprehensive environment validation and testing
- ✅ **Complete Developer Workflow** - From setup to first commit with validation checkpoints
- ✅ **Business Value Justification (BVJ)** - Required for all development tasks

### Platform Maturity Enhancements
- ✅ **Production-Grade Security** - Complete secrets management with Google Secret Manager
- ✅ **Enterprise Deployment** - Docker, Kubernetes, load balancing, auto-scaling
- ✅ **Disaster Recovery** - Complete backup and recovery procedures
- ✅ **Compliance Ready** - SOC2, GDPR preparation with audit trails

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

**Last Updated**: January 20, 2025
**Maintained By**: Netra Platform Team
**Version**: 3.0.0 - **Major Documentation Overhaul**

**🎯 Key Additions in Version 3.0:**
- Complete production deployment procedures
- Comprehensive monitoring and SLA compliance
- Business metrics and revenue tracking methodology
- Consolidated configuration management
- String literals index for consistency
- Enterprise-grade security and compliance documentation