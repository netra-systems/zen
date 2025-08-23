# 🏷️ Identifiers Literals

Component names, class names, field names, and identifiers

*Generated on 2025-08-21 21:56:03*

## 📊 Category Statistics

| Metric | Value |
|--------|-------|
| Total Literals | 30 |
| Subcategories | 2 |
| Average Confidence | 0.800 |

## 📋 Subcategories

- [component_name (27 literals)](#subcategory-component-name)
- [id_field (3 literals)](#subcategory-id-field)

## Subcategory: component_name {subcategory-component-name}

**Count**: 27 literals

### 🟢 High (≥0.8) (27 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `= get\_connection\_manager` | fix_e2e_connection_manager_imports.py:92 | fix_connection_manager_imports | `HeaderConstants...`, `JWTConstants.N... |
| `agents/data\_sub\_agent` | extract_function_violations.py:49 | FunctionViolationExtractor.... | `= get_connectio...`, `HeaderConstant... |
| `agents/triage\_sub\_agent` | extract_function_violations.py:51 | FunctionViolationExtractor.... | `= get_connectio...`, `HeaderConstant... |
| `app\.agents\.demo\_agent` | validate_type_deduplication.py:62 | TypeDeduplicationValidator.... | `= get_connectio...`, `HeaderConstant... |
| `app\.core\.secret\_manager` | test_staging_config.py:86 | _clear_config_cache | `= get_connectio...`, `HeaderConstant... |
| `auth\_core\.routes\.auth\_routes\.aut...` | test_security.py:40 | mock_auth_service | `= get_connectio...`, `HeaderConstant... |
| `dev\_launcher\.startup\_validator\.wa...` | test_startup_validator.py:21 | TestStartupValidator.test_v... | `= get_connectio...`, `HeaderConstant... |
| `dev\_launcher\.utils\.wait\_for\_service` | test_launcher.py:350 | TestIntegration.test_full_l... | `= get_connectio...`, `HeaderConstant... |
| `from tests\.e2e\.account\_deletion\_f...` | fix_e2e_test_imports.py:59 | ImportFixer.__init__ | `= get_connectio...`, `HeaderConstant... |
| `from tests\.e2e\.integration\.auth\_f...` | fix_e2e_test_imports.py:61 | ImportFixer.__init__ | `= get_connectio...`, `HeaderConstant... |
| `from tests\.e2e\.onboarding\_flow\_ex...` | fix_e2e_test_imports.py:62 | ImportFixer.__init__ | `= get_connectio...`, `HeaderConstant... |
| `from tests\.e2e\.user\_journey\_executor` | fix_e2e_imports.py:78 | E2EImportFixer.__init__ | `= get_connectio...`, `HeaderConstant... |
| `from tests\\\.e2e\\\.integration\\\.a...` | fix_e2e_test_imports.py:59 | ImportFixer.__init__ | `= get_connectio...`, `HeaderConstant... |
| `from tests\\\.e2e\\\.integration\\\.a...` | fix_e2e_test_imports.py:61 | ImportFixer.__init__ | `= get_connectio...`, `HeaderConstant... |
| `from tests\\\.e2e\\\.integration\\\.o...` | fix_e2e_test_imports.py:62 | ImportFixer.__init__ | `= get_connectio...`, `HeaderConstant... |
| `from tests\\\.user\_journey\_executor` | fix_e2e_imports.py:78 | E2EImportFixer.__init__ | `= get_connectio...`, `HeaderConstant... |
| `HeaderConstants\.USER\_AGENT` | auth_constants_migration.py:56 | AuthConstantsMigrator.__init__ | `= get_connectio...`, `JWTConstants.N... |
| `JWTConstants\.NETRA\_AUTH\_SERVICE` | auth_constants_migration.py:50 | AuthConstantsMigrator.__init__ | `= get_connectio...`, `HeaderConstant... |
| `netra\_backend\.app\.services\.connec...` | e2e_import_fixer_comprehensive.py:105 | E2EImportFixer.__init__ | `= get_connectio...`, `HeaderConstant... |
| `netra\_backend\.app\.services\.thread...` | fast_import_checker.py:396 | verify_fixes | `= get_connectio...`, `HeaderConstant... |
| `netra\_backend\.app\.services\.websoc...` | e2e_import_fixer_comprehensive.py:106 | E2EImportFixer.__init__ | `= get_connectio...`, `HeaderConstant... |
| `netra\_backend\.app\.websocket\.conne...` | fix_all_connection_manager_imports.py:34 | fix_file | `= get_connectio...`, `HeaderConstant... |
| `netra\_backend\.app\.websocket\.ws\_m...` | fast_import_checker.py:400 | verify_fixes | `= get_connectio...`, `HeaderConstant... |
| `netra\_backend/app/agents/data\_sub\_...` | fix_comprehensive_imports.py:251 | ComprehensiveImportFixerV2.... | `= get_connectio...`, `HeaderConstant... |
| `netra\_backend/app/agents/demo\_service` | fix_comprehensive_imports.py:252 | ComprehensiveImportFixerV2.... | `= get_connectio...`, `HeaderConstant... |
| `netra\_backend/tests/services/apex\_o...` | test_backend.py:32 | module | `= get_connectio...`, `HeaderConstant... |
| `postgresql\+asyncpg://postgres:postgr...` | test_env.py:193 | EnvironmentPresets.postgres... | `= get_connectio...`, `HeaderConstant... |

### Usage Examples

- **scripts\fix_e2e_connection_manager_imports.py:92** - `fix_connection_manager_imports`
- **scripts\extract_function_violations.py:49** - `FunctionViolationExtractor._is_critical_path`
- **scripts\extract_function_violations.py:51** - `FunctionViolationExtractor._is_critical_path`

---

## Subcategory: id_field {subcategory-id-field}

**Count**: 3 literals

### 🟢 High (≥0.8) (3 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `AuthConstants\.SERVICE\_ID` | auth_constants_migration.py:81 | AuthConstantsMigrator.__init__ | `CredentialConst...`, `OAuthConstants... |
| `CredentialConstants\.GOOGLE\_CLIENT\_ID` | auth_constants_migration.py:62 | AuthConstantsMigrator.__init__ | `AuthConstants.S...`, `OAuthConstants... |
| `OAuthConstants\.CLIENT\_ID` | auth_constants_migration.py:71 | AuthConstantsMigrator.__init__ | `AuthConstants.S...`, `CredentialCons... |

### Usage Examples

- **scripts\auth_constants_migration.py:81** - `AuthConstantsMigrator.__init__`
- **scripts\auth_constants_migration.py:62** - `AuthConstantsMigrator.__init__`
- **scripts\auth_constants_migration.py:71** - `AuthConstantsMigrator.__init__`

---

## 🔗 Navigation

- 🏠 [Back to Main Index](../string_literals_index.md)
- 📂 [Browse Other Categories](./)

---

*This is the detailed documentation for the `identifiers` category.*
*For the complete system overview, see the [Main String Literals Index](../string_literals_index.md).*