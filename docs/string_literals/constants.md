# 🔒 Constants Literals

Enumeration values and constant definitions

*Generated on 2025-08-21 22:03:59*

## 📊 Category Statistics

| Metric | Value |
|--------|-------|
| Total Literals | 17 |
| Subcategories | 2 |
| Average Confidence | 0.559 |

## 📋 Subcategories

- [enum (10 literals)](#subcategory-enum)
- [number (7 literals)](#subcategory-number)

## Subcategory: enum {subcategory-enum}

**Count**: 10 literals

### 🟡 Medium (0.5-0.8) (10 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `   JWT\_SECRET: ` | validate_jwt_consistency.py:156 | validate_jwt_secret_consist... | `"JWT_SECRET_KEY...`, `"FERNET_KEY"` |
| `   JWT\_SECRET\_KEY: ` | validate_jwt_consistency.py:155 | validate_jwt_secret_consist... | `"JWT_SECRET_KEY...`, `"FERNET_KEY"` |
| `"DATABASE\_URL"` | auth_constants_migration.py:66 | AuthConstantsMigrator.__init__ | `"JWT_SECRET_KEY...`, `"FERNET_KEY"` |
| `"FERNET\_KEY"` | auth_constants_migration.py:36 | AuthConstantsMigrator.__init__ | `"JWT_SECRET_KEY...`, `"GEMINI_API_KE... |
| `"GEMINI\_API\_KEY"` | auth_constants_migration.py:64 | AuthConstantsMigrator.__init__ | `"JWT_SECRET_KEY...`, `"FERNET_KEY"` |
| `"JWT\_SECRET\_KEY"` | auth_constants_migration.py:35 | AuthConstantsMigrator.__init__ | `"FERNET_KEY"`, `"GEMINI_API_KEY...` |
| `,NEXT\_PUBLIC\_AUTH\_URL=` | deploy_to_gcp.py:505 | GCPDeployer.deploy_service | `"JWT_SECRET_KEY...`, `"FERNET_KEY"` |
| `\`NETRA\_\`, \`APP\_\`, \`DB\_\`` | markdown_reporter.py:321 | MarkdownReporter._generate_... | `"JWT_SECRET_KEY...`, `"FERNET_KEY"` |
| `NEXT\_PUBLIC\_API\_URL=` | build_staging.py:112 | StagingBuilder.build_frontend | `"JWT_SECRET_KEY...`, `"FERNET_KEY"` |
| `NEXT\_PUBLIC\_API\_URL=` | deploy_to_gcp.py:505 | GCPDeployer.deploy_service | `"JWT_SECRET_KEY...`, `"FERNET_KEY"` |

### Usage Examples

- **scripts\validate_jwt_consistency.py:156** - `validate_jwt_secret_consistency`
- **scripts\validate_jwt_consistency.py:155** - `validate_jwt_secret_consistency`
- **scripts\auth_constants_migration.py:66** - `AuthConstantsMigrator.__init__`

---

## Subcategory: number {subcategory-number}

**Count**: 7 literals

### 🟡 Medium (0.5-0.8) (7 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `10` | deploy_to_gcp.py:702 | GCPDeployer.deploy_all | `8001`, `8443` |
| `20` | startup_environment.py:156 | DependencyChecker._display_... | `8001`, `10` |
| `30` | startup_reporter.py:191 | StartupReporter._print_indi... | `8001`, `10` |
| `8001` | debug_uvicorn_recursion.py:19 | module | `10`, `8443` |
| `8081` | start_auth_service.py:59 | AuthServiceManager.start_au... | `8001`, `10` |
| `8443` | reset_clickhouse.py:12 | module | `8001`, `10` |
| `8443` | reset_clickhouse_auto.py:13 | module | `8001`, `10` |

### Usage Examples

- **scripts\deploy_to_gcp.py:702** - `GCPDeployer.deploy_all`
- **scripts\startup_environment.py:156** - `DependencyChecker._display_results`
- **scripts\startup_reporter.py:191** - `StartupReporter._print_individual_results`

---

## 🔗 Navigation

- 🏠 [Back to Main Index](../string_literals_index.md)
- 📂 [Browse Other Categories](./)

---

*This is the detailed documentation for the `constants` category.*
*For the complete system overview, see the [Main String Literals Index](../string_literals_index.md).*