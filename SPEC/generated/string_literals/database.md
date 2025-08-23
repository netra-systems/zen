# 🗄️ Database Literals

Table names, column names, SQL keywords, and database queries

*Generated on 2025-08-21 21:56:03*

## 📊 Category Statistics

| Metric | Value |
|--------|-------|
| Total Literals | 250 |
| Subcategories | 3 |
| Average Confidence | 0.900 |

## 📋 Subcategories

- [column_name (11 literals)](#subcategory-column-name)
- [sql_keyword (234 literals)](#subcategory-sql-keyword)
- [table_name (5 literals)](#subcategory-table-name)

## Subcategory: column_name {subcategory-column-name}

**Count**: 11 literals

### 🟢 High (≥0.8) (11 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `HeaderConstants\.CONTENT\_TYPE` | auth_constants_migration.py:55 | AuthConstantsMigrator.__init__ | `JWTConstants.AC...`, `JWTConstants.E... |
| `JWTConstants\.ACCESS\_TOKEN\_TYPE` | auth_constants_migration.py:41 | AuthConstantsMigrator.__init__ | `HeaderConstants...`, `JWTConstants.E... |
| `JWTConstants\.EXPIRES\_AT` | auth_constants_migration.py:47 | AuthConstantsMigrator.__init__ | `HeaderConstants...`, `JWTConstants.A... |
| `JWTConstants\.ISSUED\_AT` | auth_constants_migration.py:46 | AuthConstantsMigrator.__init__ | `HeaderConstants...`, `JWTConstants.A... |
| `JWTConstants\.REFRESH\_TOKEN\_TYPE` | auth_constants_migration.py:42 | AuthConstantsMigrator.__init__ | `HeaderConstants...`, `JWTConstants.A... |
| `JWTConstants\.SERVICE\_TOKEN\_TYPE` | auth_constants_migration.py:43 | AuthConstantsMigrator.__init__ | `HeaderConstants...`, `JWTConstants.A... |
| `JWTConstants\.TOKEN\_TYPE` | auth_constants_migration.py:39 | AuthConstantsMigrator.__init__ | `HeaderConstants...`, `JWTConstants.A... |
| `netra\_backend\.app\.routes\.factory\...` | fix_all_import_issues.py:220 | ComprehensiveImportFixer.ve... | `HeaderConstants...`, `JWTConstants.A... |
| `system:view\_status` | permission_factory.py:187 | PermissionFactory.create_re... | `HeaderConstants...`, `JWTConstants.A... |
| `test1\_name` | analyze_test_overlap.py:624 | TestOverlapAnalyzer._save_c... | `HeaderConstants...`, `JWTConstants.A... |
| `test2\_name` | analyze_test_overlap.py:627 | TestOverlapAnalyzer._save_c... | `HeaderConstants...`, `JWTConstants.A... |

### Usage Examples

- **scripts\auth_constants_migration.py:55** - `AuthConstantsMigrator.__init__`
- **scripts\auth_constants_migration.py:41** - `AuthConstantsMigrator.__init__`
- **scripts\auth_constants_migration.py:47** - `AuthConstantsMigrator.__init__`

---

## Subcategory: sql_keyword {subcategory-sql-keyword}

**Count**: 234 literals

### 🟢 High (≥0.8) (234 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `DELETE FROM` | test_security.py:130 | TestSQLInjectionPrevention.... | `Delete session ...`, `Deleted artifa... |
| `Delete session \(logout\)` | session_manager.py:120 | SessionManager.delete_session | `DELETE FROM`, `Deleted artifac...` |
| `Deleted artifact: ` | cleanup_workflow_runs.py:274 | _clean_artifacts | `DELETE FROM`, `Delete session ...` |
| `Deleted run ` | cleanup_workflow_runs.py:260 | _clean_workflow_runs | `DELETE FROM`, `Delete session ...` |
| `Deleted: ` | cleanup_workflow_runs.py:161 | clean_local_directories | `DELETE FROM`, `Delete session ...` |
| `from ` | aggressive_syntax_fix.py:121 | aggressive_fix | `DELETE FROM`, `Delete session ...` |
| `from "` | validate_frontend_tests.py:129 | FrontendTestValidator._chec... | `DELETE FROM`, `Delete session ...` |
| `from '` | validate_frontend_tests.py:129 | FrontendTestValidator._chec... | `DELETE FROM`, `Delete session ...` |
| `from \.` | auto_fix_test_violations.py:579 | TestFileSplitter._update_fi... | `DELETE FROM`, `Delete session ...` |
| `from \. import` | unified_import_manager.py:266 | UnifiedImportManager._check... | `DELETE FROM`, `Delete session ...` |
| `from \.\.` | check_e2e_imports.py:134 | E2EImportChecker.fix_common... | `DELETE FROM`, `Delete session ...` |
| `from \.\. import` | unified_import_manager.py:266 | UnifiedImportManager._check... | `DELETE FROM`, `Delete session ...` |
| `from app import` | check_netra_backend_imports.py:60 | ImportAnalyzer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from app\.` | check_e2e_imports.py:138 | E2EImportChecker.fix_common... | `DELETE FROM`, `Delete session ...` |
| `from app\\\.` | align_test_imports.py:199 | TestImportAligner.fix_modul... | `DELETE FROM`, `Delete session ...` |
| `from app\\\.auth\_integration\\\.auth...` | fix_import_issues.py:27 | fix_validate_token_imports | `DELETE FROM`, `Delete session ...` |
| `from auth\_core\.` | check_e2e_imports.py:146 | E2EImportChecker.fix_common... | `DELETE FROM`, `Delete session ...` |
| `from auth\_service\.auth\_core\.` | check_e2e_imports.py:146 | E2EImportChecker.fix_common... | `DELETE FROM`, `Delete session ...` |
| `from conftest import` | align_test_imports.py:205 | TestImportAligner.fix_modul... | `DELETE FROM`, `Delete session ...` |
| `from datetime import\.\*datetime` | enhanced_fix_datetime_deprecation.py:28 | _has_datetime_import | `DELETE FROM`, `Delete session ...` |
| `from datetime import\.\*UTC` | enhanced_fix_datetime_deprecation.py:36 | _fix_utc_imports | `DELETE FROM`, `Delete session ...` |
| `from fastapi` | validate_service_independence.py:165 | ServiceIndependenceValidato... | `DELETE FROM`, `Delete session ...` |
| `from frontend\.` | check_e2e_imports.py:149 | E2EImportChecker.fix_common... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend` | align_test_imports.py:160 | TestImportAligner.fix_sys_path | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.` | align_test_imports.py:130 | TestImportAligner.fix_relat... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.` | align_test_imports.py:199 | TestImportAligner.fix_modul... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.agents\.cor...` | fix_all_import_issues.py:123 | ComprehensiveImportFixer._b... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.agents\.cor...` | fix_all_import_issues.py:129 | ComprehensiveImportFixer._b... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.agents\.sup...` | fix_supervisor_imports.py:60 | find_files_with_bad_imports | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.agents\.sup...` | fix_supervisor_imports.py:32 | fix_supervisor_imports | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.agents\.sup...` | fix_supervisor_imports.py:33 | fix_supervisor_imports | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.agents\.val...` | fix_e2e_tests_comprehensive.py:172 | E2ETestFixer._find_import_e... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.auth\_integ...` | unified_import_manager.py:357 | UnifiedImportManager._check... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.auth\_integ...` | fix_import_issues.py:28 | fix_validate_token_imports | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.core\.auth\...` | auth_constants_migration.py:211 | AuthConstantsMigrator.migra... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.schemas import` | comprehensive_e2e_import_fixer.py:65 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.schemas\.Agent` | comprehensive_e2e_import_fixer.py:146 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.schemas\.ag...` | comprehensive_e2e_import_fixer.py:145 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.schemas\.co...` | fix_schema_imports.py:137 | SchemaImportFixer.fix_impor... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.schemas\.re...` | deduplicate_types.py:158 | TypeDeduplicator.find_pytho... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.schemas\.th...` | fix_e2e_imports.py:90 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.schemas\.un...` | fix_schema_imports.py:129 | SchemaImportFixer.fix_impor... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.schemas\.wo...` | fix_schema_imports.py:133 | SchemaImportFixer.fix_impor... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.services\.q...` | fix_remaining_e2e_imports.py:74 | main | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.services\.s...` | fix_remaining_e2e_imports.py:70 | main | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.utils\.sear...` | comprehensive_e2e_import_fixer.py:181 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.websocket\....` | fix_e2e_connection_manager_imports.py:44 | find_files_with_connection_... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.websocket\....` | fix_e2e_tests_comprehensive.py:173 | E2ETestFixer._find_import_e... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.websocket\....` | fix_remaining_e2e_imports.py:62 | main | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.app\.websocket\....` | fix_e2e_imports.py:47 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.search\_filter\_...` | comprehensive_e2e_import_fixer.py:180 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.` | check_e2e_imports.py:142 | E2EImportChecker.fix_common... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.agents\.t...` | comprehensive_e2e_import_fixer.py:87 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.agents\.t...` | comprehensive_e2e_import_fixer.py:89 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.conftest ...` | align_test_imports.py:205 | TestImportAligner.fix_modul... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.fixtures` | align_test_imports.py:203 | TestImportAligner.fix_modul... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.fixtures\...` | fix_e2e_imports.py:52 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.fixtures\...` | comprehensive_e2e_import_fixer.py:87 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.fixtures\...` | fix_e2e_imports.py:54 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.frontend\.` | check_e2e_imports.py:149 | E2EImportChecker.fix_common... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.helpers` | align_test_imports.py:202 | TestImportAligner.fix_modul... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.helpers\....` | fix_e2e_imports.py:60 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.helpers\....` | fix_e2e_imports.py:58 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.helpers\....` | fix_e2e_imports.py:62 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.integrati...` | e2e_import_fixer_comprehensive.py:93 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.integrati...` | comprehensive_e2e_import_fixer.py:91 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.l4\_stagi...` | comprehensive_e2e_import_fixer.py:91 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.model\_se...` | comprehensive_e2e_import_fixer.py:89 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.real\_cri...` | comprehensive_e2e_import_fixer.py:90 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.test\_fix...` | comprehensive_e2e_import_fixer.py:88 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.test\_utils` | check_e2e_imports.py:143 | E2EImportChecker.fix_common... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\.tests\.unified\_...` | fix_e2e_imports.py:93 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.agent\_convers...` | fix_remaining_e2e_imports.py:57 | main | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.app\\\.configu...` | fix_schema_imports.py:136 | SchemaImportFixer.fix_impor... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.app\\\.example...` | fix_remaining_e2e_imports.py:61 | main | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.app\\\.models\...` | fix_schema_imports.py:132 | SchemaImportFixer.fix_impor... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.app\\\.monitor...` | fix_remaining_e2e_imports.py:65 | main | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.app\\\.quality...` | fix_remaining_e2e_imports.py:73 | main | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.app\\\.routes\...` | fix_schema_imports.py:128 | SchemaImportFixer.fix_impor... | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.app\\\.schemas...` | fix_e2e_imports.py:89 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.app\\\.utils\\...` | fix_remaining_e2e_imports.py:69 | main | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.tests\\\.e2e\\...` | fix_e2e_test_imports.py:45 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.tests\\\.e2e\\...` | fix_e2e_test_imports.py:44 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.tests\\\.e2e\\...` | fix_e2e_test_imports.py:43 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.tests\\\.e2e\\...` | fix_e2e_test_imports.py:47 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.tests\\\.e2e\\...` | fix_e2e_test_imports.py:46 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.tests\\\.facto...` | fix_remaining_e2e_imports.py:77 | main | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.tests\\\.fixtu...` | fix_e2e_imports.py:51 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.tests\\\.l4\_s...` | fix_e2e_imports.py:61 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.tests\\\.model...` | fix_e2e_imports.py:57 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.tests\\\.real\...` | fix_e2e_imports.py:59 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.tests\\\.test\...` | fix_e2e_imports.py:53 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from netra\_backend\\\.tests\\\.test\...` | fix_e2e_test_imports.py:50 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from test\_framework\.` | e2e_import_fixer_comprehensive.py:97 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from test\_framework\.\\1 import` | align_test_imports.py:197 | TestImportAligner.fix_modul... | `DELETE FROM`, `Delete session ...` |
| `from test\_framework\\\.\(\\w\+\) import` | align_test_imports.py:197 | TestImportAligner.fix_modul... | `DELETE FROM`, `Delete session ...` |
| `from test\_utils` | check_e2e_imports.py:143 | E2EImportChecker.fix_common... | `DELETE FROM`, `Delete session ...` |
| `from tests import` | check_netra_backend_imports.py:61 | ImportAnalyzer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.` | e2e_import_fixer_comprehensive.py:85 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.clients` | fix_e2e_imports.py:65 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.conftest import` | fix_remaining_e2e_imports.py:51 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e` | fix_e2e_imports.py:66 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e import` | fix_e2e_imports.py:71 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.` | e2e_import_fixer_comprehensive.py:89 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.\\1\_core import` | fix_all_e2e_imports.py:86 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.\\1\_fixtures import` | fix_all_e2e_imports.py:88 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.\\1\_helpers import` | fix_all_e2e_imports.py:85 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.\\1\_manager import` | fix_all_e2e_imports.py:87 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.agent\_conversation\...` | fix_e2e_test_imports.py:60 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.agent\_conversation\...` | fix_remaining_e2e_imports.py:58 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.agent\_orchestration...` | fix_all_e2e_imports.py:72 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.agent\_startup\_help...` | fix_all_e2e_imports.py:70 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.agent\_startup\_vali...` | fix_all_e2e_imports.py:71 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.auth\_flow\_manager ...` | fix_all_e2e_imports.py:95 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.auth\_flow\_testers` | fix_e2e_test_imports.py:56 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.config` | fix_e2e_test_imports.py:55 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.config import` | fix_all_e2e_imports.py:65 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.data` | fix_e2e_test_imports.py:45 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.data\_factory import` | fix_all_e2e_imports.py:67 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.fixtures` | fix_e2e_test_imports.py:40 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.fixtures import` | fix_all_e2e_imports.py:76 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.fixtures\.core\.thre...` | fix_e2e_test_imports.py:65 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.fixtures\.high\_volu...` | fix_e2e_test_imports.py:69 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.harness\_complete im...` | fix_all_e2e_imports.py:49 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers` | fix_e2e_test_imports.py:39 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers import` | fix_all_e2e_imports.py:75 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.` | fix_e2e_test_imports.py:75 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.auth\.oauth...` | fix_e2e_test_imports.py:102 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.chat\_helpers` | fix_e2e_test_imports.py:103 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.core\.chat\...` | fix_e2e_test_imports.py:103 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.core\.unifi...` | fix_e2e_test_imports.py:104 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.database\.d...` | fix_e2e_test_imports.py:106 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.database\_s...` | fix_e2e_test_imports.py:106 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.journey\.jo...` | fix_e2e_test_imports.py:101 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.journey\.ne...` | fix_e2e_test_imports.py:99 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.journey\.re...` | fix_e2e_test_imports.py:100 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.journey\.us...` | fix_e2e_test_imports.py:98 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.journey\_va...` | fix_e2e_test_imports.py:101 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.new\_user\_...` | fix_e2e_test_imports.py:99 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.oauth\_jour...` | fix_e2e_test_imports.py:102 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.real\_servi...` | fix_e2e_test_imports.py:100 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.unified\_fl...` | fix_e2e_test_imports.py:104 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.user\_journ...` | fix_e2e_test_imports.py:98 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.websocket\....` | fix_e2e_test_imports.py:105 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.helpers\.websocket\_...` | fix_e2e_test_imports.py:105 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.infrastructure` | fix_e2e_test_imports.py:47 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.jwt\_token\_helpers` | fix_e2e_test_imports.py:53 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.jwt\_token\_helpers ...` | fix_e2e_test_imports.py:91 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.network\_failure\_si...` | fix_all_e2e_imports.py:52 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.oauth\_flow\_manager...` | fix_all_e2e_imports.py:64 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.oauth\_test\_providers` | fix_e2e_test_imports.py:54 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.oauth\_test\_provide...` | fix_e2e_test_imports.py:92 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.real\_client\_types ...` | fix_all_e2e_imports.py:56 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.real\_http\_client i...` | fix_all_e2e_imports.py:57 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.real\_services\_mana...` | fix_all_e2e_imports.py:61 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.real\_websocket\_cli...` | fix_all_e2e_imports.py:55 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.service\_manager import` | fix_all_e2e_imports.py:60 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.service\_orchestrator` | fix_e2e_imports.py:77 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.service\_orchestrato...` | fix_all_e2e_imports.py:79 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.test\_data\_factory ...` | fix_remaining_e2e_imports.py:45 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.test\_helpers import` | fix_remaining_e2e_imports.py:54 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.test\_helpers\.perfo...` | fix_e2e_test_imports.py:72 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.test\_utils import` | fix_all_e2e_imports.py:66 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.unified\_e2e\_harness` | fix_e2e_imports.py:76 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.unified\_e2e\_harnes...` | fix_all_e2e_imports.py:48 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.validators` | fix_e2e_test_imports.py:46 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.e2e\.websocket\_resilienc...` | fix_all_e2e_imports.py:92 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.factories import` | fix_remaining_e2e_imports.py:78 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\.test\_utils` | fix_e2e_test_imports.py:50 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\.unified` | comprehensive_e2e_import_fixer.py:174 | ComprehensiveE2EImportFixer... | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.` | fix_netra_backend_imports.py:112 | ImportFixer._determine_fix_... | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.agent\_orchestration\_f...` | fix_all_e2e_imports.py:72 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.agent\_startup\_helpers...` | fix_all_e2e_imports.py:70 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.agent\_startup\_validat...` | fix_all_e2e_imports.py:71 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.config` | fix_e2e_test_imports.py:55 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.config import` | fix_all_e2e_imports.py:65 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.auth\_flow\_testers` | fix_e2e_test_imports.py:56 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.conftest import` | fix_all_e2e_imports.py:82 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.data\_factory im...` | fix_remaining_e2e_imports.py:45 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.helpers\\\.servi...` | fix_all_e2e_imports.py:79 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.high\_volume\_data` | fix_e2e_test_imports.py:69 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.integration\\\.\...` | fix_all_e2e_imports.py:86 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.integration\\\.\...` | fix_all_e2e_imports.py:88 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.integration\\\.\...` | fix_all_e2e_imports.py:85 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.integration\\\.\...` | fix_all_e2e_imports.py:87 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.integration\\\.a...` | fix_e2e_test_imports.py:60 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.integration\\\.a...` | fix_all_e2e_imports.py:95 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.integration\\\.f...` | fix_all_e2e_imports.py:76 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.integration\\\.h...` | fix_all_e2e_imports.py:75 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.integration\\\.t...` | fix_e2e_test_imports.py:65 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.performance\_base` | fix_e2e_test_imports.py:72 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.real\_services\_...` | fix_remaining_e2e_imports.py:48 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.test\_utils import` | fix_remaining_e2e_imports.py:54 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.thread\_test\_fi...` | fix_e2e_test_imports.py:66 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.e2e\\\.websocket\_resil...` | fix_all_e2e_imports.py:91 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.fixtures` | align_test_imports.py:203 | TestImportAligner.fix_modul... | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.harness\_complete import` | fix_all_e2e_imports.py:49 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.helpers` | align_test_imports.py:202 | TestImportAligner.fix_modul... | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.jwt\_token\_helpers` | fix_e2e_test_imports.py:53 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.jwt\_token\_helpers import` | fix_e2e_test_imports.py:91 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.network\_failure\_simul...` | fix_all_e2e_imports.py:52 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.oauth\_flow\_manager im...` | fix_all_e2e_imports.py:64 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.oauth\_test\_providers` | fix_e2e_test_imports.py:54 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.oauth\_test\_providers ...` | fix_e2e_test_imports.py:92 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.real\_client\_types import` | fix_all_e2e_imports.py:56 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.real\_http\_client import` | fix_all_e2e_imports.py:57 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.real\_services\_manager...` | fix_all_e2e_imports.py:61 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.real\_websocket\_client...` | fix_all_e2e_imports.py:55 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.service\_manager import` | fix_all_e2e_imports.py:60 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.service\_orchestrator` | fix_e2e_imports.py:77 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.test\_data\_factory import` | fix_all_e2e_imports.py:67 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.test\_harness import` | fix_all_e2e_imports.py:48 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.test\_utils import` | fix_all_e2e_imports.py:66 | main | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.unified import` | fix_e2e_imports.py:71 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.unified\\\.` | fix_e2e_imports.py:72 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.unified\\\.clients` | fix_e2e_imports.py:65 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.unified\\\.e2e` | fix_e2e_imports.py:66 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.unified\\\.e2e\\\.fixtures` | fix_e2e_test_imports.py:40 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.unified\\\.e2e\\\.helpers` | fix_e2e_test_imports.py:39 | ImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.unified\_e2e\_harness` | fix_e2e_imports.py:76 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from tests\\\.unified\_system\\\.` | fix_e2e_imports.py:93 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from TestSyntaxFix` | fix_e2e_tests_comprehensive.py:222 | E2ETestFixer._fix_import_er... | `DELETE FROM`, `Delete session ...` |
| `from typing import` | fix_missing_functions.py:72 | add_missing_functions | `DELETE FROM`, `Delete session ...` |
| `from unified\\\.` | fix_e2e_imports.py:81 | E2EImportFixer.__init__ | `DELETE FROM`, `Delete session ...` |
| `from\\s\+\(?\!` | validate_type_deduplication.py:199 | TypeDeduplicationValidator.... | `DELETE FROM`, `Delete session ...` |
| `from\\s\+\(\[a\-zA\-Z\_\]\[a\-zA\-Z0\...` | deduplicate_types.py:134 | TypeDeduplicator.find_pytho... | `DELETE FROM`, `Delete session ...` |
| `from\\s\+\\S\+\\s\+import\\s\*\\\(\\s...` | fix_remaining_syntax_errors.py:18 | fix_empty_imports | `DELETE FROM`, `Delete session ...` |
| `from\\s\+app\\\.\(?\!` | validate_type_deduplication.py:198 | TypeDeduplicationValidator.... | `DELETE FROM`, `Delete session ...` |
| `SELECT 1` | connection.py:216 | AuthDatabase.test_connection | `DELETE FROM`, `Delete session ...` |
| `SELECT current\_database\(\)` | test_async_postgres.py:93 | test_auth_connection | `DELETE FROM`, `Delete session ...` |
| `SELECT version\(\)` | environment_validator.py:161 | EnvironmentValidator.test_p... | `DELETE FROM`, `Delete session ...` |
| `Update Jest snapshots` | test_frontend.py:403 | add_jest_option_args | `DELETE FROM`, `Delete session ...` |
| `Update progress` | create_enforcement_tools.py:62 | ProgressTracker.update | `DELETE FROM`, `Delete session ...` |
| `Updated ` | fix_schema_imports.py:224 | SchemaImportFixer.update_in... | `DELETE FROM`, `Delete session ...` |

### Usage Examples

- **auth_service\tests\test_security.py:130** - `TestSQLInjectionPrevention.test_token_validation_sql_injection`
- **auth_service\auth_core\core\session_manager.py:120** - `SessionManager.delete_session`
- **scripts\cleanup_workflow_runs.py:274** - `_clean_artifacts`

---

## Subcategory: table_name {subcategory-table-name}

**Count**: 5 literals

### 🟢 High (≥0.8) (5 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `agents/` | type_checker.py:185 | TypeChecker._are_legitimate... | `AgentStarted(`, `AgentStarted\s*...` |
| `agents/corpus\_admin` | extract_function_violations.py:50 | FunctionViolationExtractor.... | `AgentStarted(`, `AgentStarted\s*...` |
| `agents/supervisor` | extract_function_violations.py:48 | FunctionViolationExtractor.... | `AgentStarted(`, `AgentStarted\s*...` |
| `AgentStarted\(` | websocket_coherence_review.py:119 | check_payload_completeness | `AgentStarted\s*...`, `agents/` |
| `AgentStarted\\s\*\\\(\[^\)\]\*\\\)` | websocket_coherence_review.py:121 | check_payload_completeness | `AgentStarted(`, `agents/` |

### Usage Examples

- **scripts\compliance\type_checker.py:185** - `TypeChecker._are_legitimate_separations`
- **scripts\extract_function_violations.py:50** - `FunctionViolationExtractor._is_critical_path`
- **scripts\extract_function_violations.py:48** - `FunctionViolationExtractor._is_critical_path`

---

## 🔗 Navigation

- 🏠 [Back to Main Index](../string_literals_index.md)
- 📂 [Browse Other Categories](./)

### Related Categories

- 🏷️ [Identifiers](identifiers.md) - Database elements often serve as identifiers

---

*This is the detailed documentation for the `database` category.*
*For the complete system overview, see the [Main String Literals Index](../string_literals_index.md).*