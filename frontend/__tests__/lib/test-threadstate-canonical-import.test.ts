/**
 * ThreadState Canonical Import Validation Test
 * 
 * Business Value Justification (BVJ):
 * - Segment: Platform/Internal
 * - Business Goal: Ensure all ThreadState usage follows canonical import patterns
 * - Value Impact: Protects $500K+ ARR chat functionality from import-related type conflicts
 * - Strategic Impact: Issue #879 ThreadState SSOT migration - canonical import enforcement
 *
 * PURPOSE: This test SHOULD FAIL initially to demonstrate canonical import violations.
 * It validates that ALL files importing or using ThreadState follow the canonical 
 * import pattern from @/shared/types/frontend_types.
 *
 * EXPECTED FAILURES:
 * 1. Files import ThreadState from non-canonical paths
 * 2. Files use ThreadState without proper canonical import
 * 3. Import aliases create confusion about canonical source
 * 4. Circular import dependencies due to multiple ThreadState definitions
 *
 * @compliance CLAUDE.md - SSOT import pattern enforcement
 * @compliance GitHub Issue #879 - ThreadState SSOT migration
 */

import * as fs from 'fs';
import * as path from 'path';

describe('ThreadState Canonical Import Validation', () => {
  const projectRoot = path.resolve(__dirname, '../../..');
  const canonicalImportPath = '@/shared/types/frontend_types';
  const canonicalFilePath = 'shared/types/frontend_types.ts';

  describe('Import Path Validation', () => {
    it('SHOULD FAIL - All ThreadState imports should use canonical path', () => {
      const filesToCheck = [
        'frontend/components/chat/MainChat.tsx',
        'frontend/components/threads/ThreadList.tsx',
        'frontend/store/slices/threadSlice.ts',
        'frontend/hooks/useThreadNavigation.ts',
        'frontend/types/domains/threads.ts',
        'frontend/store/slices/types.ts',
        'frontend/lib/thread-state-machine.ts'
      ];

      const importViolations: Array<{
        file: string;
        nonCanonicalImports: string[];
        missingCanonicalImport: boolean;
        violationType: 'NON_CANONICAL' | 'MISSING_CANONICAL' | 'BOTH';
      }> = [];

      filesToCheck.forEach(relativeFile => {
        const fullPath = path.join(projectRoot, relativeFile);

        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf8');
          const nonCanonicalImports: string[] = [];

          // Check for non-canonical ThreadState imports
          const importPatterns = [
            /@\/types\/domains\/threads.*ThreadState/,
            /@\/store\/slices\/types.*ThreadState/,
            /from\s+['"]\.\/.*ThreadState/,
            /from\s+['"]\.\.\/.*ThreadState/,
            /import.*ThreadState.*from\s+['"][^@]/
          ];

          importPatterns.forEach(pattern => {
            const matches = content.match(pattern);
            if (matches) {
              nonCanonicalImports.push(matches[0]);
            }
          });

          // Check if file uses ThreadState but doesn't import it canonically
          const usesThreadState = content.includes('ThreadState') && 
                                 !content.includes('// ThreadState type only comment');
          const hasCanonicalImport = content.includes(canonicalImportPath) ||
                                   content.includes('shared/types/frontend_types');

          let violationType: 'NON_CANONICAL' | 'MISSING_CANONICAL' | 'BOTH';
          if (nonCanonicalImports.length > 0 && !hasCanonicalImport) {
            violationType = 'BOTH';
          } else if (nonCanonicalImports.length > 0) {
            violationType = 'NON_CANONICAL';
          } else {
            violationType = 'MISSING_CANONICAL';
          }

          if (nonCanonicalImports.length > 0 || (usesThreadState && !hasCanonicalImport)) {
            importViolations.push({
              file: relativeFile,
              nonCanonicalImports,
              missingCanonicalImport: usesThreadState && !hasCanonicalImport,
              violationType
            });
          }
        }
      });

      // TEST ASSERTION: This should FAIL due to non-canonical imports
      expect(importViolations.length).toBe(0,
        `CANONICAL IMPORT VIOLATIONS: ${importViolations.length} files use non-canonical ThreadState imports. ` +
        `All ThreadState usage must import from ${canonicalImportPath}. ` +
        `Violations: ${importViolations.map(v => v.file).join(', ')}`
      );

      // Report import violations
      if (importViolations.length > 0) {
        console.error('CANONICAL IMPORT VIOLATION REPORT:');
        importViolations.forEach(violation => {
          console.error(`File: ${violation.file} (${violation.violationType})`);
          if (violation.nonCanonicalImports.length > 0) {
            console.error(`  Non-canonical imports:`);
            violation.nonCanonicalImports.forEach(imp => {
              console.error(`    ❌ ${imp}`);
            });
          }
          if (violation.missingCanonicalImport) {
            console.error(`  ❌ Uses ThreadState without canonical import`);
          }
          console.error(`  ✅ Should import: import { ThreadState } from '${canonicalImportPath}';`);
        });
      }
    });

    it('SHOULD FAIL - No files should re-export ThreadState from non-canonical sources', () => {
      const reExportViolations: Array<{
        file: string;
        reExports: string[];
        shouldRemove: boolean;
      }> = [];

      const filesToCheck = [
        'frontend/types/domains/threads.ts',
        'frontend/store/slices/types.ts',
        'frontend/types/index.ts',
        'frontend/lib/types.ts'
      ];

      filesToCheck.forEach(relativeFile => {
        const fullPath = path.join(projectRoot, relativeFile);

        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf8');
          const reExports: string[] = [];

          // Look for re-export patterns
          const reExportPatterns = [
            /export.*ThreadState.*from/g,
            /export\s*\{[^}]*ThreadState[^}]*\}/g,
            /export\s+\{[^}]*ThreadState[^}]*\}\s+from/g
          ];

          reExportPatterns.forEach(pattern => {
            const matches = content.match(pattern);
            if (matches) {
              matches.forEach(match => reExports.push(match));
            }
          });

          // Check for interface/type definitions that should be re-exports
          const definesThreadState = content.includes('interface ThreadState') ||
                                   content.includes('type ThreadState =');

          if (reExports.length > 0 || definesThreadState) {
            reExportViolations.push({
              file: relativeFile,
              reExports,
              shouldRemove: definesThreadState // If it defines ThreadState, it should be removed
            });
          }
        }
      });

      // TEST ASSERTION: This should FAIL due to re-export violations
      expect(reExportViolations.length).toBe(0,
        `RE-EXPORT VIOLATIONS: ${reExportViolations.length} files re-export or redefine ThreadState. ` +
        `Only ${canonicalFilePath} should define ThreadState. All others should import it. ` +
        `Files: ${reExportViolations.map(v => v.file).join(', ')}`
      );

      // Report re-export violations
      if (reExportViolations.length > 0) {
        console.error('RE-EXPORT VIOLATION REPORT:');
        reExportViolations.forEach(violation => {
          console.error(`File: ${violation.file}`);
          if (violation.reExports.length > 0) {
            violation.reExports.forEach(reExport => {
              console.error(`  ❌ Re-export: ${reExport}`);
            });
          }
          if (violation.shouldRemove) {
            console.error(`  ❌ Defines ThreadState instead of importing canonical`);
          }
          console.error(`  ✅ Should: Remove definition and import from ${canonicalImportPath}`);
        });
      }
    });

    it('SHOULD FAIL - Import aliases should not create confusion about canonical source', () => {
      const aliasViolations: Array<{
        file: string;
        confusingAliases: string[];
        issue: string;
      }> = [];

      const filesToCheck = [
        'frontend/components/chat/MainChat.tsx',
        'frontend/components/threads/ThreadList.tsx',
        'frontend/store/slices/threadSlice.ts',
        'frontend/hooks/useThreadNavigation.ts'
      ];

      filesToCheck.forEach(relativeFile => {
        const fullPath = path.join(projectRoot, relativeFile);

        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf8');
          const confusingAliases: string[] = [];
          let issue = '';

          // Look for confusing alias patterns
          const aliasPatterns = [
            {
              pattern: /import\s*\{[^}]*ThreadState\s+as\s+(\w+)[^}]*\}/g,
              issue: 'ThreadState aliased - should use direct import'
            },
            {
              pattern: /import.*ThreadState.*from\s+['"]@\/types\/domains/g,
              issue: 'Imports ThreadState from non-canonical domains path'
            },
            {
              pattern: /import.*ThreadState.*from\s+['"]@\/store\/slices/g,
              issue: 'Imports ThreadState from non-canonical store path'
            }
          ];

          aliasPatterns.forEach(({ pattern, issue: patternIssue }) => {
            const matches = content.match(pattern);
            if (matches) {
              matches.forEach(match => confusingAliases.push(match));
              issue = patternIssue;
            }
          });

          // Check for multiple ThreadState imports in same file
          const threadStateImports = content.match(/import[^;]*ThreadState[^;]*;/g);
          if (threadStateImports && threadStateImports.length > 1) {
            confusingAliases.push(...threadStateImports);
            issue = 'Multiple ThreadState imports create confusion';
          }

          if (confusingAliases.length > 0) {
            aliasViolations.push({
              file: relativeFile,
              confusingAliases,
              issue
            });
          }
        }
      });

      // TEST ASSERTION: This should FAIL due to confusing aliases
      expect(aliasViolations.length).toBe(0,
        `IMPORT ALIAS VIOLATIONS: ${aliasViolations.length} files use confusing ThreadState aliases. ` +
        `ThreadState should be imported directly from canonical source without aliases. ` +
        `Files: ${aliasViolations.map(v => v.file).join(', ')}`
      );

      // Report alias violations
      if (aliasViolations.length > 0) {
        console.error('IMPORT ALIAS VIOLATION REPORT:');
        aliasViolations.forEach(violation => {
          console.error(`File: ${violation.file}`);
          console.error(`  Issue: ${violation.issue}`);
          violation.confusingAliases.forEach(alias => {
            console.error(`    ❌ ${alias}`);
          });
          console.error(`  ✅ Should use: import { ThreadState } from '${canonicalImportPath}';`);
        });
      }
    });
  });

  describe('Circular Import Detection', () => {
    it('SHOULD FAIL - No circular imports should exist due to multiple ThreadState definitions', () => {
      // Check for potential circular import scenarios
      const circularImportRisks: Array<{
        file: string;
        imports: string[];
        exportsThreadState: boolean;
        risk: 'HIGH' | 'MEDIUM' | 'LOW';
        reason: string;
      }> = [];

      const filesToCheck = [
        'shared/types/frontend_types.ts',
        'frontend/types/domains/threads.ts',
        'frontend/store/slices/types.ts',
        'frontend/lib/thread-state-machine.ts'
      ];

      filesToCheck.forEach(relativeFile => {
        const fullPath = path.join(projectRoot, relativeFile);

        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf8');
          
          // Extract imports
          const imports = (content.match(/import[^;]+;/g) || []).map(imp => imp.trim());
          
          // Check if file exports ThreadState
          const exportsThreadState = content.includes('export interface ThreadState') ||
                                    content.includes('export type ThreadState') ||
                                    content.includes('export { ThreadState }');

          let risk: 'HIGH' | 'MEDIUM' | 'LOW' = 'LOW';
          let reason = '';

          // High risk: File defines ThreadState and imports from other files that might also define it
          if (exportsThreadState && imports.some(imp => 
            imp.includes('types/domains') || 
            imp.includes('store/slices') ||
            imp.includes('lib/thread-state-machine'))) {
            risk = 'HIGH';
            reason = 'Defines ThreadState and imports from files that may also define it';
          }
          // Medium risk: File defines ThreadState but is not canonical
          else if (exportsThreadState && relativeFile !== canonicalFilePath) {
            risk = 'MEDIUM';
            reason = 'Non-canonical file defines ThreadState';
          }
          // Low risk but track for monitoring
          else if (imports.some(imp => imp.includes('ThreadState'))) {
            risk = 'LOW';
            reason = 'Imports ThreadState but doesn\'t define it';
          }

          if (risk !== 'LOW' || exportsThreadState) {
            circularImportRisks.push({
              file: relativeFile,
              imports,
              exportsThreadState,
              risk,
              reason
            });
          }
        }
      });

      // Count high-risk scenarios
      const highRiskScenarios = circularImportRisks.filter(r => r.risk === 'HIGH');
      const mediumRiskScenarios = circularImportRisks.filter(r => r.risk === 'MEDIUM');

      // TEST ASSERTION: This should FAIL due to circular import risks
      expect(highRiskScenarios.length).toBe(0,
        `HIGH RISK CIRCULAR IMPORTS: ${highRiskScenarios.length} files create high risk of circular imports. ` +
        `This will cause TypeScript compilation failures. ` +
        `Files: ${highRiskScenarios.map(r => r.file).join(', ')}`
      );

      expect(mediumRiskScenarios.length).toBe(0,
        `MEDIUM RISK CIRCULAR IMPORTS: ${mediumRiskScenarios.length} files define ThreadState in non-canonical locations. ` +
        `This creates import confusion and potential circular dependencies. ` +
        `Files: ${mediumRiskScenarios.map(r => r.file).join(', ')}`
      );

      // Report circular import risks
      if (circularImportRisks.length > 0) {
        console.error('CIRCULAR IMPORT RISK REPORT:');
        circularImportRisks.forEach(risk => {
          console.error(`${risk.risk} RISK - ${risk.file}:`);
          console.error(`  Reason: ${risk.reason}`);
          console.error(`  Exports ThreadState: ${risk.exportsThreadState}`);
          if (risk.imports.length > 0) {
            console.error(`  Imports: ${risk.imports.length} statements`);
          }
        });
      }
    });

    it('SHOULD FAIL - TypeScript module resolution should be unambiguous', () => {
      // Test TypeScript module resolution with multiple ThreadState definitions
      const moduleResolutionIssues: Array<{
        importPath: string;
        resolvedType: string;
        isCanonical: boolean;
        ambiguityRisk: 'HIGH' | 'MEDIUM' | 'LOW';
      }> = [];

      const importPaths = [
        '@/shared/types/frontend_types',
        '@/types/domains/threads',
        '@/store/slices/types', 
        '@/lib/thread-state-machine',
        '../types/domains/threads',
        './types/thread-state',
        '../../store/slices/types'
      ];

      importPaths.forEach(importPath => {
        let resolvedType = 'UNKNOWN';
        let isCanonical = false;
        let ambiguityRisk: 'HIGH' | 'MEDIUM' | 'LOW' = 'LOW';

        if (importPath.includes('shared/types/frontend_types')) {
          resolvedType = 'CANONICAL_INTERFACE';
          isCanonical = true;
          ambiguityRisk = 'LOW';
        } else if (importPath.includes('domains/threads')) {
          resolvedType = 'DUPLICATE_INTERFACE';
          isCanonical = false;
          ambiguityRisk = 'HIGH'; // Same interface structure but different location
        } else if (importPath.includes('slices/types')) {
          resolvedType = 'STORE_SPECIFIC_INTERFACE';
          isCanonical = false;
          ambiguityRisk = 'HIGH'; // Different interface structure
        } else if (importPath.includes('thread-state-machine')) {
          resolvedType = 'STRING_UNION_TYPE';
          isCanonical = false;
          ambiguityRisk = 'MEDIUM'; // Different semantic meaning
        } else if (importPath.startsWith('../') || importPath.startsWith('./')) {
          resolvedType = 'RELATIVE_PATH_AMBIGUOUS';
          isCanonical = false;
          ambiguityRisk = 'HIGH'; // Relative paths are context-dependent
        }

        if (!isCanonical) {
          moduleResolutionIssues.push({
            importPath,
            resolvedType,
            isCanonical,
            ambiguityRisk
          });
        }
      });

      const highRiskResolutions = moduleResolutionIssues.filter(issue => issue.ambiguityRisk === 'HIGH');

      // TEST ASSERTION: This should FAIL due to ambiguous module resolution
      expect(highRiskResolutions.length).toBe(0,
        `MODULE RESOLUTION AMBIGUITY: ${highRiskResolutions.length} import paths create ambiguous ThreadState resolution. ` +
        `TypeScript may resolve to different types based on context. ` +
        `Ambiguous paths: ${highRiskResolutions.map(r => r.importPath).join(', ')}`
      );

      // Report module resolution issues
      if (moduleResolutionIssues.length > 0) {
        console.error('MODULE RESOLUTION AMBIGUITY REPORT:');
        moduleResolutionIssues.forEach(issue => {
          console.error(`${issue.ambiguityRisk} RISK - ${issue.importPath}:`);
          console.error(`  Resolves to: ${issue.resolvedType}`);
          console.error(`  Canonical: ${issue.isCanonical}`);
        });
        console.error(`Only ${canonicalImportPath} should be used for ThreadState imports`);
      }
    });
  });

  describe('Migration Readiness Assessment', () => {
    it('Documents canonical import migration requirements', () => {
      // Document what needs to be done for canonical import migration
      const migrationPlan = {
        canonicalSource: canonicalImportPath,
        canonicalFile: canonicalFilePath,
        migrationSteps: [
          'Update all files to import ThreadState from canonical path',
          'Remove all duplicate ThreadState interface definitions',
          'Fix import aliases to use direct ThreadState import',
          'Resolve any circular import dependencies',
          'Update TypeScript path mappings if necessary',
          'Update all re-exports to use canonical source',
          'Test all components for TypeScript compilation'
        ],
        expectedFileChanges: [
          'frontend/types/domains/threads.ts - Remove ThreadState definition, import canonical',
          'frontend/store/slices/types.ts - Remove ThreadState definition, import canonical',
          'frontend/components/**/*.tsx - Update import paths to canonical',
          'frontend/hooks/**/*.ts - Update import paths to canonical',
          'frontend/store/slices/**/*.ts - Update import paths to canonical'
        ],
        riskMitigation: [
          'Run TypeScript compiler after each file change',
          'Test component rendering after import changes',
          'Verify Redux store state compatibility',
          'Check for runtime type errors in development'
        ]
      };

      console.log('CANONICAL IMPORT MIGRATION PLAN:');
      console.log('Canonical Source:', migrationPlan.canonicalSource);
      console.log('Migration Steps:');
      migrationPlan.migrationSteps.forEach((step, index) => {
        console.log(`  ${index + 1}. ${step}`);
      });
      console.log('Expected File Changes:', migrationPlan.expectedFileChanges.length);
      console.log('Risk Mitigation Steps:', migrationPlan.riskMitigation.length);

      // This test always passes - it's for documentation
      expect(migrationPlan.migrationSteps.length).toBeGreaterThan(0);
    });
  });
});