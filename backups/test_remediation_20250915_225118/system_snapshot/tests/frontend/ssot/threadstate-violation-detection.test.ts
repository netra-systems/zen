/**
 * ThreadState SSOT Violation Detection Test Suite
 *
 * Purpose: Detect and validate consolidation of duplicate ThreadState definitions
 * This test SHOULD FAIL initially to reproduce the SSOT violation issue.
 *
 * @compliance CLAUDE.md - Real tests that fail properly
 * @compliance Issue #858 - ThreadState SSOT consolidation
 */

import * as fs from 'fs';
import * as path from 'path';
import { glob } from 'glob';

describe('ThreadState SSOT Violation Detection', () => {
  interface ThreadStateDefinition {
    filePath: string;
    lineNumber: number;
    definitionType: 'interface' | 'type' | 'enum';
    content: string;
    semantic: 'data-structure' | 'operation-states' | 'store-actions' | 'test-utility';
  }

  let threadStateDefinitions: ThreadStateDefinition[] = [];
  const canonicalPath = 'shared/types/frontend_types.ts';
  const projectRoot = process.cwd();

  beforeAll(async () => {
    // Scan for all ThreadState definitions across the codebase
    threadStateDefinitions = await scanForThreadStateDefinitions();
  });

  /**
   * PRIMARY TEST: This should FAIL initially with 5 definitions
   * Should PASS after SSOT consolidation with only 2 definitions:
   * 1. Canonical data interface (shared/types/frontend_types.ts)
   * 2. Operation states type union (thread-state-machine.ts - different semantic)
   */
  test('should have minimal ThreadState definitions - CANONICAL and OPERATION STATES only', () => {
    console.log('\n=== ThreadState Definitions Found ===');
    threadStateDefinitions.forEach((def, index) => {
      console.log(`${index + 1}. ${def.filePath}:${def.lineNumber}`);
      console.log(`   Type: ${def.definitionType} | Semantic: ${def.semantic}`);
      console.log(`   Content: ${def.content.substring(0, 100)}...`);
      console.log('');
    });

    console.log(`\nTotal ThreadState definitions found: ${threadStateDefinitions.length}`);
    console.log('Expected after consolidation: 2 (canonical + operation states)');

    // This SHOULD FAIL initially with 5 definitions found
    // After consolidation: should have only 2 (canonical + operation states)
    expect(threadStateDefinitions.length).toBeLessThanOrEqual(2);

    // Ensure canonical definition exists
    const canonicalFound = threadStateDefinitions.some(def =>
      def.filePath.includes(canonicalPath)
    );
    expect(canonicalFound).toBe(true);
  });

  /**
   * This test SHOULD FAIL initially due to duplicate data structure interfaces
   * Should PASS after removing duplicates in frontend/types and frontend/store
   */
  test('should have only one data-structure ThreadState definition', () => {
    const dataStructureDefinitions = threadStateDefinitions.filter(def =>
      def.semantic === 'data-structure'
    );

    console.log('\n=== Data Structure ThreadState Definitions ===');
    dataStructureDefinitions.forEach(def => {
      console.log(`- ${def.filePath}:${def.lineNumber}`);
    });

    // Should have only 1 canonical data structure definition
    expect(dataStructureDefinitions.length).toBe(1);

    // Should be the canonical one
    expect(dataStructureDefinitions[0]?.filePath).toContain(canonicalPath);
  });

  /**
   * Validate import consistency - all imports should point to canonical source
   */
  test('should have consistent ThreadState imports pointing to canonical source', async () => {
    const importViolations = await findImportViolations();

    console.log('\n=== ThreadState Import Analysis ===');
    if (importViolations.length === 0) {
      console.log('✅ All imports point to canonical source');
    } else {
      console.log('❌ Import violations found:');
      importViolations.forEach(violation => {
        console.log(`   ${violation.filePath}:${violation.lineNumber} - ${violation.importPath}`);
      });
    }

    // Should have no import violations after consolidation
    expect(importViolations).toHaveLength(0);
  });

  /**
   * Validate operation states semantic difference is preserved
   */
  test('should preserve operation states ThreadState with different semantic', () => {
    const operationStatesDefinitions = threadStateDefinitions.filter(def =>
      def.semantic === 'operation-states'
    );

    console.log('\n=== Operation States ThreadState ===');
    operationStatesDefinitions.forEach(def => {
      console.log(`- ${def.filePath}:${def.lineNumber}`);
      console.log(`  Content: ${def.content}`);
    });

    // Should have exactly 1 operation states definition
    expect(operationStatesDefinitions.length).toBe(1);

    // Should be in thread-state-machine.ts
    expect(operationStatesDefinitions[0]?.filePath).toContain('thread-state-machine.ts');

    // Should be a type union of string literals
    expect(operationStatesDefinitions[0]?.content).toMatch(/\|\s*'(idle|creating|switching|loading|error)'/);
  });

  /**
   * Generate actionable remediation report
   */
  test('should generate remediation report for SSOT consolidation', () => {
    const duplicates = threadStateDefinitions.filter(def =>
      def.semantic === 'data-structure' && !def.filePath.includes(canonicalPath)
    );

    const testUtilities = threadStateDefinitions.filter(def =>
      def.semantic === 'test-utility'
    );

    const storeActions = threadStateDefinitions.filter(def =>
      def.semantic === 'store-actions'
    );

    console.log('\n=== SSOT Consolidation Remediation Plan ===');
    console.log(`Canonical Definition: ${canonicalPath} (${threadStateDefinitions.find(d => d.filePath.includes(canonicalPath))?.lineNumber})`);

    if (duplicates.length > 0) {
      console.log('\n🔴 Duplicate Data Structures to Remove:');
      duplicates.forEach(dup => {
        console.log(`   - REMOVE: ${dup.filePath}:${dup.lineNumber}`);
        console.log(`     Action: Delete definition, update imports to canonical`);
      });
    }

    if (storeActions.length > 0) {
      console.log('\n🟡 Store Actions to Refactor:');
      storeActions.forEach(store => {
        console.log(`   - REFACTOR: ${store.filePath}:${store.lineNumber}`);
        console.log(`     Action: Extend canonical ThreadState, keep store methods`);
      });
    }

    if (testUtilities.length > 0) {
      console.log('\n🟠 Test Utilities to Consolidate:');
      testUtilities.forEach(test => {
        console.log(`   - CONSOLIDATE: ${test.filePath}:${test.lineNumber}`);
        console.log(`     Action: Import from canonical, remove duplicate definition`);
      });
    }

    console.log('\n🟢 Preserved Semantic Differences:');
    const operationStates = threadStateDefinitions.find(def => def.semantic === 'operation-states');
    if (operationStates) {
      console.log(`   - KEEP: ${operationStates.filePath}:${operationStates.lineNumber}`);
      console.log(`     Reason: Different semantic (operation states vs data structures)`);
    }

    // Fail if there are consolidation opportunities
    const needsConsolidation = duplicates.length + testUtilities.length > 0;
    if (needsConsolidation) {
      console.log(`\n❌ SSOT Consolidation Required: ${duplicates.length + testUtilities.length} violations found`);
    } else {
      console.log('\n✅ SSOT Consolidation Complete: No violations found');
    }

    // This should fail initially due to violations requiring consolidation
    expect(needsConsolidation).toBe(false);
  });

  // Helper functions
  async function scanForThreadStateDefinitions(): Promise<ThreadStateDefinition[]> {
    const definitions: ThreadStateDefinition[] = [];

    // Find all TypeScript files in frontend and shared directories
    const tsFiles = await glob('**/*.ts', {
      cwd: projectRoot,
      ignore: ['node_modules/**', 'dist/**', 'build/**', '.next/**']
    });

    for (const file of tsFiles) {
      const fullPath = path.resolve(projectRoot, file);
      if (!fs.existsSync(fullPath)) continue;

      const content = fs.readFileSync(fullPath, 'utf-8');
      const lines = content.split('\n');

      lines.forEach((line, index) => {
        // Match interface ThreadState or type ThreadState
        const interfaceMatch = line.match(/^\s*export\s+interface\s+ThreadState\s*({|\s*extends)/);
        const typeMatch = line.match(/^\s*export\s+type\s+ThreadState\s*=/);

        if (interfaceMatch || typeMatch) {
          const lineNumber = index + 1;
          const definitionType = interfaceMatch ? 'interface' : 'type';

          // Extract definition content (current line + next few lines for context)
          const contextLines = lines.slice(index, Math.min(index + 10, lines.length));
          const definitionContent = contextLines.join('\n');

          // Determine semantic meaning
          const semantic = determineSemanticMeaning(file, definitionContent);

          definitions.push({
            filePath: file,
            lineNumber,
            definitionType,
            content: definitionContent,
            semantic
          });
        }
      });
    }

    return definitions;
  }

  function determineSemanticMeaning(filePath: string, content: string): ThreadStateDefinition['semantic'] {
    // Operation states (union type with string literals)
    if (content.includes("'idle'") || content.includes("'creating'") || content.includes("'switching'")) {
      return 'operation-states';
    }

    // Test utilities
    if (filePath.includes('__tests__') || filePath.includes('test') || filePath.includes('spec')) {
      return 'test-utility';
    }

    // Store actions (contains method signatures)
    if (content.includes('setActiveThread') || content.includes('setThreadLoading')) {
      return 'store-actions';
    }

    // Default: data structure interface
    return 'data-structure';
  }

  async function findImportViolations(): Promise<{ filePath: string; lineNumber: number; importPath: string }[]> {
    const violations: { filePath: string; lineNumber: number; importPath: string }[] = [];

    // Find all TypeScript files
    const tsFiles = await glob('**/*.ts', {
      cwd: projectRoot,
      ignore: ['node_modules/**', 'dist/**', 'build/**', '.next/**']
    });

    for (const file of tsFiles) {
      const fullPath = path.resolve(projectRoot, file);
      if (!fs.existsSync(fullPath)) continue;

      const content = fs.readFileSync(fullPath, 'utf-8');
      const lines = content.split('\n');

      lines.forEach((line, index) => {
        // Match ThreadState imports that don't point to canonical source
        const importMatch = line.match(/import.*ThreadState.*from\s+['"]([^'"]+)['"]/);
        if (importMatch) {
          const importPath = importMatch[1];

          // Check if import points to canonical source or operation states
          const isCanonicalImport = importPath.includes('shared/types/frontend_types') ||
                                  importPath.includes('@/shared/types/frontend_types');
          const isOperationStatesImport = importPath.includes('thread-state-machine');

          if (!isCanonicalImport && !isOperationStatesImport) {
            violations.push({
              filePath: file,
              lineNumber: index + 1,
              importPath
            });
          }
        }
      });
    }

    return violations;
  }
});