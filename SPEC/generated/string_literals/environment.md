# 📄 Environment Literals

No description available

*Generated on 2025-08-21 21:56:03*

## 📊 Category Statistics

| Metric | Value |
|--------|-------|
| Total Literals | 43 |
| Subcategories | 1 |
| Average Confidence | 0.800 |

## Subcategory: env_var_name {subcategory-env-var-name}

**Count**: 43 literals

### 🟢 High (≥0.8) (43 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `netra\_backend\.` | check_netra_backend_imports.py:150 | ImportAnalyzer._check_import | `netra_backend.a...`, `netra_backend.... |
| `netra\_backend\.app` | check_netra_backend_imports.py:178 | ImportAnalyzer._create_issue | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.` | check_netra_backend_imports.py:49 | ImportAnalyzer.__init__ | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.agents\.corpus\_...` | fix_all_import_issues.py:218 | ComprehensiveImportFixer.ve... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.agents\.supervis...` | fix_all_import_issues.py:217 | ComprehensiveImportFixer.ve... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.auth\_integratio...` | e2e_import_fixer_comprehensive.py:103 | E2EImportFixer.__init__ | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.dependencies` | fast_import_checker.py:399 | verify_fixes | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.main` | fix_all_import_issues.py:216 | ComprehensiveImportFixer.ve... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.main:app` | backend_starter.py:132 | BackendStarter._build_uvico... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.monitoring\.heal...` | import_management.py:171 | ImportManagementSystem.veri... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.monitoring\.metr...` | import_management.py:170 | ImportManagementSystem.veri... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.monitoring\.models` | import_management.py:169 | ImportManagementSystem.veri... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.routes\.websocke...` | e2e_import_fixer_comprehensive.py:104 | E2EImportFixer.__init__ | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.services\.apex\_...` | fast_import_checker.py:397 | verify_fixes | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.app\.services\.llm\.c...` | fast_import_checker.py:398 | verify_fixes | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.tests` | check_netra_backend_imports.py:181 | ImportAnalyzer._create_issue | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.tests\.` | check_netra_backend_imports.py:50 | ImportAnalyzer.__init__ | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.tests\.integration\.` | e2e_import_fixer_comprehensive.py:338 | E2EImportFixer._suggest_fix... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\.tests\.test\_utils` | check_test_import_order.py:25 | check_import_order | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/app` | check_netra_backend_imports.py:112 | ImportAnalyzer.analyze_file | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/app/agents` | fix_all_import_issues.py:183 | ComprehensiveImportFixer.fi... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/app/agents/github\_ana...` | fix_comprehensive_imports.py:253 | ComprehensiveImportFixerV2.... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/app/agents/supply\_res...` | fix_comprehensive_imports.py:254 | ComprehensiveImportFixerV2.... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/app/core` | fix_all_import_issues.py:186 | ComprehensiveImportFixer.fi... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/app/monitoring` | fix_all_import_issues.py:187 | ComprehensiveImportFixer.fi... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/app/routes` | fix_all_import_issues.py:185 | ComprehensiveImportFixer.fi... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/app/schemas` | check_schema_imports.py:73 | SchemaImportAnalyzer | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/app/services` | fix_all_import_issues.py:184 | ComprehensiveImportFixer.fi... | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/app/websocket` | fast_import_checker.py:256 | fix_known_import_issues | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/tests` | analyze_test_overlap.py:69 | TestOverlapAnalyzer.analyze | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/tests/agents` | test_backend.py:32 | module | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/tests/core` | test_backend.py:30 | module | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/tests/core/test\_confi...` | test_backend.py:40 | module | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/tests/core/test\_error...` | test_backend.py:39 | module | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/tests/e2e/test\_system...` | test_backend.py:42 | module | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/tests/integration` | test_backend.py:31 | module | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/tests/routes` | test_backend.py:31 | module | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/tests/services` | test_backend.py:30 | module | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/tests/services/agents` | test_backend.py:32 | module | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/tests/services/database` | test_backend.py:35 | module | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend/tests/services/test\_s...` | test_backend.py:41 | module | `netra_backend.`, `netra_backend.a...` |
| `netra\_backend\\\.tests\\\.e2e\\\.` | fix_e2e_test_imports.py:79 | ImportFixer.__init__ | `netra_backend.`, `netra_backend.a...` |
| `redis\_container\\\.RedisContainer` | fix_testcontainers_imports.py:47 | fix_testcontainers_imports | `netra_backend.`, `netra_backend.a...` |

### Usage Examples

- **scripts\check_netra_backend_imports.py:150** - `ImportAnalyzer._check_import`
- **scripts\check_netra_backend_imports.py:178** - `ImportAnalyzer._create_issue`
- **scripts\check_netra_backend_imports.py:49** - `ImportAnalyzer.__init__`

---

## 🔗 Navigation

- 🏠 [Back to Main Index](../string_literals_index.md)
- 📂 [Browse Other Categories](./)

---

*This is the detailed documentation for the `environment` category.*
*For the complete system overview, see the [Main String Literals Index](../string_literals_index.md).*