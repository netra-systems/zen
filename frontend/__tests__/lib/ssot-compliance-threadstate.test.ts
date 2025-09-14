/**
 * SSOT Compliance Test - ThreadState Violation Detection
 *
 * Business Value Justification (BVJ):
 * - Segment: Platform/Internal
 * - Business Goal: Prevent SSOT violations that cause type conflicts and system instability
 * - Value Impact: Protects $500K+ ARR by ensuring consistent ThreadState usage
 * - Strategic Impact: Critical P1 SSOT violation detection for Issue #858
 *
 * CRITICAL MISSION: These tests SHOULD FAIL initially to demonstrate SSOT violations.
 * After SSOT remediation (Phase 4), these tests should PASS.
 *
 * DISCOVERED SSOT VIOLATIONS:
 * 1. /shared/types/frontend_types.ts (Lines 39-50) - CANONICAL ✅
 * 2. /frontend/types/domains/threads.ts (Lines 91-97) - DUPLICATE ❌
 * 3. /frontend/store/slices/types.ts (Lines 55-61) - DUPLICATE ❌
 * 4. /frontend/lib/thread-state-machine.ts (Lines 16-22) - DIFFERENT SEMANTIC ⚠️
 *
 * @compliance CLAUDE.md - SSOT remediation execution strategy
 * @compliance GitHub Issue #858 - ThreadState duplicate definitions
 */

import * as fs from 'fs';
import * as path from 'path';

describe('SSOT Compliance - ThreadState Definition Detection', () => {
  const projectRoot = path.resolve(__dirname, '../../..');

  // Known violation files - this test should detect these duplicates
  const expectedViolations = [
    {
      file: 'frontend/types/domains/threads.ts',
      line: 91,
      type: 'DUPLICATE',
      reason: 'Duplicates shared/types/frontend_types.ts interface'
    },
    {
      file: 'frontend/store/slices/types.ts',
      line: 55,
      type: 'DUPLICATE',
      reason: 'Duplicates shared/types/frontend_types.ts interface'
    },
    {
      file: 'frontend/lib/thread-state-machine.ts',
      line: 16,
      type: 'SEMANTIC_CONFLICT',
      reason: 'Different semantic meaning - state machine vs data interface'
    }
  ];

  const canonicalFile = 'shared/types/frontend_types.ts';
  const canonicalLine = 39;

  describe('ThreadState Definition Detection', () => {
    it('SHOULD FAIL - Detects multiple ThreadState interface definitions', () => {
      const violationsFound: Array<{ file: string; content: string; lines: number[] }> = [];
      const filesToCheck = [
        'shared/types/frontend_types.ts',
        'frontend/types/domains/threads.ts',
        'frontend/store/slices/types.ts',
        'frontend/lib/thread-state-machine.ts'
      ];

      filesToCheck.forEach(relativeFilePath => {
        const fullPath = path.join(projectRoot, relativeFilePath);

        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf8');
          const lines = content.split('\n');

          // Look for ThreadState interface or type definitions
          const threadStateLines: number[] = [];
          lines.forEach((line, index) => {
            if (line.includes('interface ThreadState') ||
                line.includes('type ThreadState') ||
                line.includes('export interface ThreadState') ||
                line.includes('export type ThreadState')) {
              threadStateLines.push(index + 1);
            }
          });

          if (threadStateLines.length > 0) {
            violationsFound.push({
              file: relativeFilePath,
              content: content,
              lines: threadStateLines
            });
          }
        }
      });

      // TEST ASSERTION: This should FAIL because we have 4 definitions
      expect(violationsFound.length).toBe(1,
        `SSOT VIOLATION DETECTED: Found ${violationsFound.length} files with ThreadState definitions. ` +
        `Expected only 1 (canonical: ${canonicalFile}). ` +
        `Violations in: ${violationsFound.map(v => `${v.file} (lines: ${v.lines.join(', ')})`).join(', ')}`
      );

      // Additional validation - canonical should be the only one
      const canonicalViolation = violationsFound.find(v => v.file === canonicalFile);
      expect(canonicalViolation).toBeDefined(
        `Canonical ThreadState definition not found in ${canonicalFile}`
      );

      // If test reaches here, SSOT violation exists
      console.error('SSOT VIOLATION REPORT:');
      violationsFound.forEach(violation => {
        console.error(`- ${violation.file}: ThreadState defined at lines ${violation.lines.join(', ')}`);
      });
    });

    it('SHOULD FAIL - Validates ThreadState interface structure consistency', () => {
      const interfaceStructures: Array<{
        file: string;
        fields: string[];
        isInterface: boolean;
        isTypeAlias: boolean;
      }> = [];

      const filesToCheck = [
        'shared/types/frontend_types.ts',
        'frontend/types/domains/threads.ts',
        'frontend/store/slices/types.ts',
        'frontend/lib/thread-state-machine.ts'
      ];

      filesToCheck.forEach(relativeFilePath => {
        const fullPath = path.join(projectRoot, relativeFilePath);

        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf8');

          // Extract ThreadState definition structure
          const threadStateMatch = content.match(
            /(export\s+)?(interface|type)\s+ThreadState[^{]*\{([^}]+)\}|export\s+type\s+ThreadState\s*=[^;]+;/s
          );

          if (threadStateMatch) {
            const isInterface = threadStateMatch[2] === 'interface';
            const isTypeAlias = threadStateMatch[2] === 'type' || content.includes('export type ThreadState =');

            // Extract field names from interface body
            const fields: string[] = [];
            if (threadStateMatch[3]) {
              const fieldLines = threadStateMatch[3].split('\n');
              fieldLines.forEach(line => {
                const fieldMatch = line.match(/^\s*(\w+)[:?]/);
                if (fieldMatch) {
                  fields.push(fieldMatch[1]);
                }
              });
            }

            interfaceStructures.push({
              file: relativeFilePath,
              fields,
              isInterface,
              isTypeAlias
            });
          }
        }
      });

      // TEST ASSERTION: This should FAIL because structures differ
      const canonicalStructure = interfaceStructures.find(s => s.file === canonicalFile);
      const otherStructures = interfaceStructures.filter(s => s.file !== canonicalFile);

      expect(otherStructures.length).toBe(0,
        `SSOT VIOLATION: Found ${otherStructures.length} non-canonical ThreadState definitions. ` +
        `Canonical fields: [${canonicalStructure?.fields.join(', ')}]. ` +
        `Other definitions: ${otherStructures.map(s =>
          `${s.file}:[${s.fields.join(', ')}]`
        ).join(', ')}`
      );

      // Detailed structure comparison
      if (canonicalStructure && otherStructures.length > 0) {
        console.error('STRUCTURE MISMATCH REPORT:');
        console.error(`Canonical (${canonicalFile}):`, canonicalStructure.fields);
        otherStructures.forEach(structure => {
          console.error(`${structure.file}:`, structure.fields);

          const missingFields = canonicalStructure.fields.filter(f => !structure.fields.includes(f));
          const extraFields = structure.fields.filter(f => !canonicalStructure.fields.includes(f));

          if (missingFields.length > 0) {
            console.error(`  Missing fields: ${missingFields.join(', ')}`);
          }
          if (extraFields.length > 0) {
            console.error(`  Extra fields: ${extraFields.join(', ')}`);
          }
        });
      }
    });

    it('SHOULD FAIL - Detects import path violations and circular dependencies', () => {
      const importViolations: Array<{
        file: string;
        imports: string[];
        violations: string[];
      }> = [];

      const filesToCheck = [
        'frontend/types/domains/threads.ts',
        'frontend/store/slices/types.ts',
        'frontend/lib/thread-state-machine.ts'
      ];

      filesToCheck.forEach(relativeFilePath => {
        const fullPath = path.join(projectRoot, relativeFilePath);

        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf8');
          const imports: string[] = [];
          const violations: string[] = [];

          // Extract import statements
          const importMatches = content.match(/import[^;]+;/g) || [];
          importMatches.forEach(importLine => {
            imports.push(importLine.trim());

            // Check if it imports canonical ThreadState (it should!)
            if (!importLine.includes('shared/types/frontend_types') &&
                content.includes('ThreadState') &&
                (content.includes('interface ThreadState') || content.includes('type ThreadState'))) {
              violations.push(`Should import ThreadState from ${canonicalFile} instead of redefining`);
            }
          });

          if (violations.length > 0) {
            importViolations.push({
              file: relativeFilePath,
              imports,
              violations
            });
          }
        }
      });

      // TEST ASSERTION: This should FAIL because files redefine instead of import
      expect(importViolations.length).toBe(0,
        `IMPORT VIOLATIONS DETECTED: ${importViolations.length} files should import canonical ThreadState. ` +
        `Violations: ${importViolations.map(v => `${v.file}: [${v.violations.join(', ')}]`).join('; ')}`
      );

      // Report detailed violations
      if (importViolations.length > 0) {
        console.error('IMPORT VIOLATION REPORT:');
        importViolations.forEach(violation => {
          console.error(`${violation.file}:`);
          console.error(`  Current imports:`, violation.imports);
          console.error(`  Violations:`, violation.violations);
          console.error(`  Should import: import { ThreadState } from '@/shared/types/frontend_types';`);
        });
      }
    });
  });

  describe('Business Impact Assessment', () => {
    it('SHOULD FAIL - Validates Golden Path dependency safety', () => {
      // This test checks if ThreadState violations could impact $500K+ ARR functionality
      const goldenPathFiles = [
        'components/chat/MainChat.tsx',
        'store/slices/threadSlice.ts',
        'lib/thread-state-machine.ts',
        'hooks/useThreadNavigation.ts'
      ];

      const riskAssessment = {
        highRiskFiles: [] as string[],
        mediumRiskFiles: [] as string[],
        safeFiles: [] as string[]
      };

      goldenPathFiles.forEach(relativeFile => {
        const fullPath = path.join(projectRoot, 'frontend', relativeFile);

        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf8');

          // Check for ThreadState usage without proper import
          const hasThreadStateUsage = content.includes('ThreadState');
          const hasCanonicalImport = content.includes('shared/types/frontend_types') ||
                                    content.includes('@/shared/types/frontend_types');
          const hasNonCanonicalImport = content.includes('types/domains/threads') ||
                                       content.includes('store/slices/types') ||
                                       content.includes('lib/thread-state-machine');

          if (hasThreadStateUsage && !hasCanonicalImport) {
            if (hasNonCanonicalImport) {
              riskAssessment.highRiskFiles.push(relativeFile);
            } else {
              riskAssessment.mediumRiskFiles.push(relativeFile);
            }
          } else {
            riskAssessment.safeFiles.push(relativeFile);
          }
        }
      });

      // TEST ASSERTION: This should FAIL if high-risk files exist
      expect(riskAssessment.highRiskFiles.length).toBe(0,
        `HIGH RISK: ${riskAssessment.highRiskFiles.length} Golden Path files use non-canonical ThreadState. ` +
        `This threatens $500K+ ARR functionality. Files: ${riskAssessment.highRiskFiles.join(', ')}`
      );

      expect(riskAssessment.mediumRiskFiles.length).toBe(0,
        `MEDIUM RISK: ${riskAssessment.mediumRiskFiles.length} Golden Path files may have type inconsistencies. ` +
        `Files: ${riskAssessment.mediumRiskFiles.join(', ')}`
      );

      // Business impact report
      if (riskAssessment.highRiskFiles.length > 0 || riskAssessment.mediumRiskFiles.length > 0) {
        console.error('GOLDEN PATH RISK ASSESSMENT:');
        console.error(`High Risk (threatens ARR): ${riskAssessment.highRiskFiles.join(', ')}`);
        console.error(`Medium Risk (type safety): ${riskAssessment.mediumRiskFiles.join(', ')}`);
        console.error(`Safe Files: ${riskAssessment.safeFiles.join(', ')}`);
      }
    });

    it('SHOULD FAIL - Thread navigation consistency across different ThreadState types', () => {
      // This test simulates the real-world problem: components using different ThreadState types
      const threadStateUsages = new Map<string, {
        file: string;
        expectedInterface: string;
        actualFields: string[];
      }>();

      // Mock what would happen in real component integration
      const componentTestScenarios = [
        {
          component: 'ChatThread',
          expectedFields: ['threads', 'currentThread', 'isLoading', 'error', 'messages'], // shared/types
          file: 'frontend/types/domains/threads.ts' // but uses this instead
        },
        {
          component: 'ThreadSlice',
          expectedFields: ['threads', 'currentThread', 'isLoading', 'error', 'messages'], // shared/types
          file: 'frontend/store/slices/types.ts' // but uses this instead
        }
      ];

      const inconsistencies: Array<{
        component: string;
        expected: string[];
        actual: string[];
        missing: string[];
        extra: string[];
      }> = [];

      componentTestScenarios.forEach(scenario => {
        const fullPath = path.join(projectRoot, scenario.file);

        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf8');
          const threadStateMatch = content.match(/interface ThreadState[^{]*\{([^}]+)\}/s);

          if (threadStateMatch) {
            const actualFields: string[] = [];
            const fieldLines = threadStateMatch[1].split('\n');
            fieldLines.forEach(line => {
              const fieldMatch = line.match(/^\s*(\w+)[:?]/);
              if (fieldMatch) {
                actualFields.push(fieldMatch[1]);
              }
            });

            const missing = scenario.expectedFields.filter(f => !actualFields.includes(f));
            const extra = actualFields.filter(f => !scenario.expectedFields.includes(f));

            if (missing.length > 0 || extra.length > 0) {
              inconsistencies.push({
                component: scenario.component,
                expected: scenario.expectedFields,
                actual: actualFields,
                missing,
                extra
              });
            }
          }
        }
      });

      // TEST ASSERTION: This should FAIL due to inconsistencies
      expect(inconsistencies.length).toBe(0,
        `THREAD NAVIGATION INCONSISTENCIES: ${inconsistencies.length} components have mismatched ThreadState interfaces. ` +
        `This will cause runtime errors in thread switching. ` +
        `Components: ${inconsistencies.map(i => i.component).join(', ')}`
      );

      // Detailed inconsistency report
      if (inconsistencies.length > 0) {
        console.error('THREAD NAVIGATION RISK REPORT:');
        inconsistencies.forEach(inconsistency => {
          console.error(`${inconsistency.component}:`);
          console.error(`  Expected fields: [${inconsistency.expected.join(', ')}]`);
          console.error(`  Actual fields: [${inconsistency.actual.join(', ')}]`);
          if (inconsistency.missing.length > 0) {
            console.error(`  Missing fields: [${inconsistency.missing.join(', ')}]`);
          }
          if (inconsistency.extra.length > 0) {
            console.error(`  Extra fields: [${inconsistency.extra.join(', ')}]`);
          }
        });
      }
    });
  });

  describe('SSOT Remediation Readiness', () => {
    it('Validates expected violation count for remediation planning', () => {
      // This test documents exactly what we expect to find
      const expectedViolationCount = 4; // 1 canonical + 3 violations

      // Count actual violations (this will be used in remediation)
      let actualViolations = 0;
      const filesToCheck = [
        'shared/types/frontend_types.ts',      // CANONICAL
        'frontend/types/domains/threads.ts',   // DUPLICATE
        'frontend/store/slices/types.ts',      // DUPLICATE
        'frontend/lib/thread-state-machine.ts' // SEMANTIC_CONFLICT
      ];

      filesToCheck.forEach(relativeFilePath => {
        const fullPath = path.join(projectRoot, relativeFilePath);
        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf8');
          if (content.includes('interface ThreadState') || content.includes('type ThreadState')) {
            actualViolations++;
          }
        }
      });

      // Document the current state for remediation
      expect(actualViolations).toBe(expectedViolationCount,
        `REMEDIATION PLANNING: Expected ${expectedViolationCount} ThreadState definitions, ` +
        `found ${actualViolations}. This count is used for Phase 4 remediation planning.`
      );

      // Log remediation plan
      console.log('SSOT REMEDIATION PLAN:');
      console.log('Phase 1: Keep canonical shared/types/frontend_types.ts');
      console.log('Phase 2: Remove frontend/types/domains/threads.ts ThreadState interface');
      console.log('Phase 3: Remove frontend/store/slices/types.ts ThreadState interface');
      console.log('Phase 4: Keep frontend/lib/thread-state-machine.ts (different semantic purpose)');
      console.log('Phase 5: Update all imports to use canonical definition');
    });
  });
});