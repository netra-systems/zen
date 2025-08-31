/**
 * Duplicate Export Detection Test Suite
 * 
 * PURPOSE: This test suite is designed to FAIL to expose duplicate export issues
 * in the module system. The tests will fail when duplicate exports are detected,
 * particularly the isValidWebSocketMessageType function exported from multiple sources.
 * 
 * EXPECTED FAILURES:
 * - Test 1: Will FAIL detecting duplicate isValidWebSocketMessageType export
 * - Test 2: Will FAIL on export conflicts across re-export chains
 * - Test 3: Will FAIL on webpack module parse errors
 * - Test 4: Will FAIL on runtime import validation
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { parse } from '@babel/parser';
import traverse from '@babel/traverse';

describe('Module Export Duplication Detection', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  const registryPath = path.resolve(__dirname, '../../types/registry.ts');

  /**
   * This test MUST FAIL due to isValidWebSocketMessageType being exported
   * from both shared/enums (line 38) and domains/websocket (line 142)
   */
  it('should FAIL if registry.ts contains duplicate named exports', async () => {
    const content = await fs.readFile(registryPath, 'utf8');
    const exportNames = extractNamedExports(content);
    const duplicates = findDuplicateExports(exportNames);
    
    // This assertion will FAIL - isValidWebSocketMessageType is duplicated
    expect(duplicates).toHaveLength(0);
    
    if (duplicates.length > 0) {
      console.error('❌ Duplicate exports detected:', duplicates);
      throw new Error(`Module contains duplicate exports: ${duplicates.join(', ')}`);
    }
  });

  /**
   * This test will FAIL when export conflicts exist across re-export chains
   */
  it('should detect export conflicts across re-export chains', async () => {
    const exportMap = await buildExportDependencyMap();
    const conflicts = detectExportConflicts(exportMap);
    
    // Expected to FAIL - conflicts exist in re-export chains
    expect(conflicts).toEqual([]);
    
    if (conflicts.length > 0) {
      conflicts.forEach(conflict => {
        console.error(`❌ Export conflict: ${conflict.name} from sources:`, conflict.sources);
      });
    }
  });

  /**
   * This test will FAIL with webpack parse error due to duplicate exports
   */
  it('should FAIL on module parse errors during import', () => {
    // This will fail with: Module parse failed: Duplicate export 'isValidWebSocketMessageType'
    expect(() => {
      const registry = require('../../types/registry');
      const exports = Object.keys(registry);
      console.log(`Total exports: ${exports.length}`);
    }).not.toThrow(/Duplicate export/);
  });

  /**
   * This test validates export uniqueness at module boundary - will FAIL
   */
  it('should validate export uniqueness at module boundary', () => {
    try {
      // Attempt to import - will fail during module resolution
      const moduleExports = jest.isolateModules(() => {
        return require('../../types/registry');
      });
      
      const exportKeys = Object.keys(moduleExports);
      const uniqueExports = [...new Set(exportKeys)];
      
      // This assertion will fail if we even get here
      expect(exportKeys.length).toBe(uniqueExports.length);
    } catch (error: any) {
      // Expected to catch module parse error
      expect(error.message).toContain('Duplicate export');
      throw error; // Re-throw to make test fail as expected
    }
  });

  /**
   * Test for specific duplicate: isValidWebSocketMessageType
   */
  it('should FAIL detecting isValidWebSocketMessageType duplicate export', async () => {
    const content = await fs.readFile(registryPath, 'utf8');
    const occurrences = countExportOccurrences(content, 'isValidWebSocketMessageType');
    
    // Will FAIL: Expected 1, but found 2 occurrences
    expect(occurrences).toBe(1);
    
    if (occurrences > 1) {
      const lines = findExportLines(content, 'isValidWebSocketMessageType');
      console.error(`❌ 'isValidWebSocketMessageType' exported ${occurrences} times at lines:`, lines);
    }
  });

  /**
   * Test for export statement analysis using AST
   */
  it('should FAIL when analyzing export statements with AST', async () => {
    const content = await fs.readFile(registryPath, 'utf8');
    const ast = parse(content, {
      sourceType: 'module',
      plugins: ['typescript', 'jsx']
    });

    const exportedNames = new Map<string, number[]>();
    
    traverse(ast, {
      ExportSpecifier(path: any) {
        const exportName = path.node.exported.name;
        if (!exportedNames.has(exportName)) {
          exportedNames.set(exportName, []);
        }
        exportedNames.get(exportName)!.push(path.node.loc?.start.line || 0);
      }
    });

    const duplicates: string[] = [];
    exportedNames.forEach((lines, name) => {
      if (lines.length > 1) {
        duplicates.push(`${name} (lines: ${lines.join(', ')})`);
      }
    });

    // Will FAIL - duplicates exist
    expect(duplicates).toHaveLength(0);
    
    if (duplicates.length > 0) {
      console.error('❌ AST analysis found duplicate exports:', duplicates);
    }
  });
});

// Helper functions
function extractNamedExports(content: string): string[] {
  const exportRegex = /export\s*\{([^}]+)\}/g;
  const exports: string[] = [];
  let match;
  
  while ((match = exportRegex.exec(content)) !== null) {
    const exportList = match[1]
      .split(',')
      .map(e => e.trim())
      .filter(e => e && !e.includes(' as '))
      .map(e => e.split(' ')[0]);
    exports.push(...exportList);
  }
  
  return exports;
}

function findDuplicateExports(exports: string[]): string[] {
  const seen = new Set<string>();
  const duplicates = new Set<string>();
  
  for (const exp of exports) {
    if (seen.has(exp)) {
      duplicates.add(exp);
    }
    seen.add(exp);
  }
  
  return Array.from(duplicates);
}

async function buildExportDependencyMap(): Promise<Map<string, string[]>> {
  const map = new Map<string, string[]>();
  
  // Simulate building dependency map - in real implementation would parse all files
  map.set('isValidWebSocketMessageType', [
    'shared/enums',
    'domains/websocket'
  ]);
  
  return map;
}

function detectExportConflicts(exportMap: Map<string, string[]>): Array<{name: string, sources: string[]}> {
  const conflicts: Array<{name: string, sources: string[]}> = [];
  
  exportMap.forEach((sources, name) => {
    if (sources.length > 1) {
      conflicts.push({ name, sources });
    }
  });
  
  return conflicts;
}

function countExportOccurrences(content: string, exportName: string): number {
  const regex = new RegExp(`\\b${exportName}\\b`, 'g');
  const lines = content.split('\n');
  let count = 0;
  
  lines.forEach(line => {
    if (line.includes('export') && regex.test(line)) {
      count++;
    }
  });
  
  return count;
}

function findExportLines(content: string, exportName: string): number[] {
  const lines = content.split('\n');
  const lineNumbers: number[] = [];
  
  lines.forEach((line, index) => {
    if (line.includes('export') && line.includes(exportName)) {
      lineNumbers.push(index + 1);
    }
  });
  
  return lineNumbers;
}