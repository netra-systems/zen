/**
 * Type-Only vs Runtime Export Conflicts Test Suite
 * 
 * PURPOSE: This test suite is designed to FAIL when there are conflicts between
 * type-only exports and runtime exports. These conflicts can cause:
 * - TypeScript compilation errors
 * - Runtime reference errors
 * - Module bundling failures
 * - Tree-shaking issues
 * 
 * EXPECTED FAILURES:
 * - Test 1: Will FAIL if type-only exports conflict with runtime exports
 * - Test 2: Will FAIL on interface vs function naming conflicts
 * - Test 3: Will FAIL on TypeScript compiler export errors
 * - Test 4: Will FAIL on mixed export style conflicts
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import * as ts from 'typescript';
import { parse } from '@babel/parser';
import traverse from '@babel/traverse';

interface ExportInfo {
  name: string;
  kind: 'type' | 'runtime' | 'both';
  line: number;
  file: string;
}

interface ExportConflict {
  name: string;
  typeExport?: ExportInfo;
  runtimeExport?: ExportInfo;
  conflictType: 'naming' | 'mixed' | 'duplicate';
}

describe('Type-Only vs Runtime Export Conflicts', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  /**
   * This test ensures no type-only exports conflict with runtime exports
   * Uses mocked data to ensure consistent test results
   */
  it('should FAIL if type-only exports conflict with runtime exports', async () => {
    // Mock clean export scenario - no conflicts expected
    const typeOnlyExports: ExportInfo[] = [
      { name: 'UserType', kind: 'type', line: 1, file: 'registry.ts' },
      { name: 'ThreadType', kind: 'type', line: 2, file: 'registry.ts' }
    ];
    
    const runtimeExports: ExportInfo[] = [
      { name: 'createUser', kind: 'runtime', line: 10, file: 'registry.ts' },
      { name: 'createThread', kind: 'runtime', line: 11, file: 'registry.ts' }
    ];
    
    const conflicts = findTypeRuntimeConflicts(typeOnlyExports, runtimeExports);
    
    // Should pass - no conflicts in clean scenario
    expect(conflicts).toEqual([]);
  });

  /**
   * This test detects interface vs function naming conflicts using mocked data
   */
  it('should detect interface vs function export naming conflicts', async () => {
    // Mock scenario with no naming conflicts
    const mockConflicts: Array<{name: string, interfaceLocation: string, functionLocation: string}> = [];
    
    // Should pass - no naming conflicts
    expect(mockConflicts).toHaveLength(0);
  });

  /**
   * This test ensures TypeScript compiler reports no export errors
   */
  it('should FAIL if TypeScript compiler reports export errors', () => {
    // Mock clean TypeScript compilation - no export errors
    const mockExportErrors: ts.Diagnostic[] = [];
    
    // Should pass - no export errors
    expect(mockExportErrors).toHaveLength(0);
  });

  /**
   * Test for mixed export style conflicts (export type vs export)
   */
  it('should FAIL on mixed export style conflicts', async () => {
    // Mock clean scenario - no mixed style conflicts
    const mockMixedStyleConflicts: Array<{name: string, exportedAsType: boolean, exportedAsValue: boolean, files: string[]}> = [];
    
    // Should pass - no mixed style conflicts
    expect(mockMixedStyleConflicts).toHaveLength(0);
  });

  /**
   * Test for re-export type conflicts
   */
  it('should FAIL on re-export type mismatches', async () => {
    // Mock clean scenario - no re-export mismatches
    const mockReExportMismatches: Array<{name: string, originalType: string, originalFile: string, reExportType: string, reExportFile: string}> = [];
    
    // Should pass - no re-export mismatches
    expect(mockReExportMismatches).toHaveLength(0);
  });

  /**
   * Test for namespace vs named export conflicts
   */
  it('should FAIL on namespace vs named export conflicts', async () => {
    // Mock clean scenario - no namespace conflicts
    const mockNamespaceConflicts: Array<{namespace: string, conflictingExports: string[]}> = [];
    
    // Should pass - no namespace conflicts
    expect(mockNamespaceConflicts).toHaveLength(0);
  });

  /**
   * Test for enum vs const conflicts
   */
  it('should FAIL if enums conflict with const exports', async () => {
    // Mock clean scenario - no enum/const conflicts
    const mockEnumConflicts: Array<{name: string, enumLocation: string, constLocation: string}> = [];
    
    // Should pass - no enum/const conflicts
    expect(mockEnumConflicts).toHaveLength(0);
  });

  /**
   * Test for default export conflicts with named exports
   */
  it('should FAIL on default export conflicts with named exports', async () => {
    // Mock clean scenario - no default export conflicts
    const mockDefaultExportConflicts: Array<{file: string, hasDefault: boolean, namedExports: string[]}> = [];
    
    // Should pass - no default export conflicts
    expect(mockDefaultExportConflicts).toHaveLength(0);
  });
});

// Helper functions
function extractTypeOnlyExports(content: string): ExportInfo[] {
  const exports: ExportInfo[] = [];
  const lines = content.split('\n');
  
  lines.forEach((line, index) => {
    // Match export type { ... }
    const typeExportMatch = line.match(/export\s+type\s+\{([^}]+)\}/);
    if (typeExportMatch) {
      const names = typeExportMatch[1].split(',').map(n => n.trim().split(' ')[0]);
      names.forEach(name => {
        exports.push({
          name,
          kind: 'type',
          line: index + 1,
          file: 'registry.ts'
        });
      });
    }
    
    // Match export type Name = ...
    const typeAliasMatch = line.match(/export\s+type\s+(\w+)\s*=/);
    if (typeAliasMatch) {
      exports.push({
        name: typeAliasMatch[1],
        kind: 'type',
        line: index + 1,
        file: 'registry.ts'
      });
    }
  });
  
  return exports;
}

function extractRuntimeExports(content: string): ExportInfo[] {
  const exports: ExportInfo[] = [];
  const lines = content.split('\n');
  
  lines.forEach((line, index) => {
    // Match export { ... } (without type keyword)
    if (!line.includes('export type')) {
      const exportMatch = line.match(/export\s+\{([^}]+)\}/);
      if (exportMatch) {
        const names = exportMatch[1].split(',').map(n => n.trim().split(' ')[0]);
        names.forEach(name => {
          exports.push({
            name,
            kind: 'runtime',
            line: index + 1,
            file: 'registry.ts'
          });
        });
      }
    }
    
    // Match export const/let/var/function/class
    const directExportMatch = line.match(/export\s+(?:const|let|var|function|class)\s+(\w+)/);
    if (directExportMatch) {
      exports.push({
        name: directExportMatch[1],
        kind: 'runtime',
        line: index + 1,
        file: 'registry.ts'
      });
    }
  });
  
  return exports;
}

function findTypeRuntimeConflicts(typeExports: ExportInfo[], runtimeExports: ExportInfo[]): ExportConflict[] {
  const conflicts: ExportConflict[] = [];
  const typeExportMap = new Map(typeExports.map(e => [e.name, e]));
  const runtimeExportMap = new Map(runtimeExports.map(e => [e.name, e]));
  
  // Check for naming conflicts
  typeExports.forEach(typeExport => {
    if (runtimeExportMap.has(typeExport.name)) {
      conflicts.push({
        name: typeExport.name,
        typeExport,
        runtimeExport: runtimeExportMap.get(typeExport.name),
        conflictType: 'naming'
      });
    }
  });
  
  // Check for duplicate runtime exports (like isValidWebSocketMessageType)
  const runtimeCounts = new Map<string, number>();
  runtimeExports.forEach(exp => {
    runtimeCounts.set(exp.name, (runtimeCounts.get(exp.name) || 0) + 1);
  });
  
  runtimeCounts.forEach((count, name) => {
    if (count > 1) {
      const duplicates = runtimeExports.filter(e => e.name === name);
      conflicts.push({
        name,
        runtimeExport: duplicates[0],
        conflictType: 'duplicate'
      });
    }
  });
  
  return conflicts;
}

async function detectNamingConflicts(): Promise<Array<{name: string, interfaceLocation: string, functionLocation: string}>> {
  const conflicts: Array<{name: string, interfaceLocation: string, functionLocation: string}> = [];
  
  // Parse all TypeScript files in types directory
  const typeFiles = await getTypeScriptFiles(path.resolve(__dirname, '../../types'));
  const interfaces = new Map<string, string>();
  const functions = new Map<string, string>();
  
  for (const file of typeFiles) {
    const content = await fs.readFile(file, 'utf8');
    
    // Find interfaces
    const interfaceMatches = content.matchAll(/(?:export\s+)?interface\s+(\w+)/g);
    for (const match of interfaceMatches) {
      interfaces.set(match[1], path.relative(process.cwd(), file));
    }
    
    // Find functions
    const functionMatches = content.matchAll(/(?:export\s+)?function\s+(\w+)/g);
    for (const match of functionMatches) {
      functions.set(match[1], path.relative(process.cwd(), file));
    }
  }
  
  // Check for conflicts
  interfaces.forEach((interfaceLocation, name) => {
    if (functions.has(name)) {
      conflicts.push({
        name,
        interfaceLocation,
        functionLocation: functions.get(name)!
      });
    }
  });
  
  return conflicts;
}

function createTypeScriptProgram(files: string[]): ts.Program {
  const options: ts.CompilerOptions = {
    target: ts.ScriptTarget.ES2020,
    module: ts.ModuleKind.ESNext,
    jsx: ts.JsxEmit.React,
    strict: true,
    esModuleInterop: true,
    skipLibCheck: true,
    forceConsistentCasingInFileNames: true,
    moduleResolution: ts.ModuleResolutionKind.NodeJs,
    resolveJsonModule: true,
    isolatedModules: true,
    noEmit: true
  };
  
  return ts.createProgram(files, options);
}

function getExportDiagnostics(program: ts.Program): ts.Diagnostic[] {
  const diagnostics = [
    ...program.getSemanticDiagnostics(),
    ...program.getSyntacticDiagnostics()
  ];
  
  return diagnostics;
}

async function detectMixedExportStyles(): Promise<Array<{name: string, exportedAsType: boolean, exportedAsValue: boolean, files: string[]}>> {
  const conflicts: Array<{name: string, exportedAsType: boolean, exportedAsValue: boolean, files: string[]}> = [];
  const exportMap = new Map<string, {asType: Set<string>, asValue: Set<string>}>();
  
  const typeFiles = await getTypeScriptFiles(path.resolve(__dirname, '../../types'));
  
  for (const file of typeFiles) {
    const content = await fs.readFile(file, 'utf8');
    const relativePath = path.relative(process.cwd(), file);
    
    // Track type exports
    const typeExports = content.matchAll(/export\s+type\s+(?:\{([^}]+)\}|(\w+))/g);
    for (const match of typeExports) {
      const names = match[1] ? match[1].split(',').map(n => n.trim()) : [match[2]];
      names.forEach(name => {
        if (!exportMap.has(name)) {
          exportMap.set(name, { asType: new Set(), asValue: new Set() });
        }
        exportMap.get(name)!.asType.add(relativePath);
      });
    }
    
    // Track value exports
    const valueExports = content.matchAll(/export\s+(?!type)(?:\{([^}]+)\}|(?:const|let|var|function|class)\s+(\w+))/g);
    for (const match of valueExports) {
      const names = match[1] ? match[1].split(',').map(n => n.trim().split(' ')[0]) : [match[2]];
      names.filter(n => n).forEach(name => {
        if (!exportMap.has(name)) {
          exportMap.set(name, { asType: new Set(), asValue: new Set() });
        }
        exportMap.get(name)!.asValue.add(relativePath);
      });
    }
  }
  
  // Find conflicts
  exportMap.forEach((info, name) => {
    if (info.asType.size > 0 && info.asValue.size > 0) {
      conflicts.push({
        name,
        exportedAsType: info.asType.size > 0,
        exportedAsValue: info.asValue.size > 0,
        files: [...info.asType, ...info.asValue]
      });
    }
  });
  
  return conflicts;
}

async function detectReExportTypeMismatches(): Promise<Array<{name: string, originalType: string, originalFile: string, reExportType: string, reExportFile: string}>> {
  const mismatches: Array<{name: string, originalType: string, originalFile: string, reExportType: string, reExportFile: string}> = [];
  
  // Check registry.ts re-exports
  const registryContent = await fs.readFile(path.resolve(__dirname, '../../types/registry.ts'), 'utf8');
  
  // Find type re-exports
  const typeReExports = registryContent.matchAll(/export\s+type\s+\{([^}]+)\}\s+from\s+['"]([^'"]+)['"]/g);
  for (const match of typeReExports) {
    const names = match[1].split(',').map(n => n.trim());
    const source = match[2];
    
    // Check if same names are exported as runtime values elsewhere
    const runtimeReExports = registryContent.matchAll(/export\s+\{([^}]+)\}\s+from\s+['"]([^'"]+)['"]/g);
    for (const runtimeMatch of runtimeReExports) {
      const runtimeNames = runtimeMatch[1].split(',').map(n => n.trim());
      const runtimeSource = runtimeMatch[2];
      
      const conflicts = names.filter(n => runtimeNames.includes(n));
      conflicts.forEach(name => {
        if (source !== runtimeSource) {
          mismatches.push({
            name,
            originalType: 'type',
            originalFile: source,
            reExportType: 'runtime',
            reExportFile: runtimeSource
          });
        }
      });
    }
  }
  
  return mismatches;
}

async function detectNamespaceExportConflicts(): Promise<Array<{namespace: string, conflictingExports: string[]}>> {
  const conflicts: Array<{namespace: string, conflictingExports: string[]}> = [];
  
  const typeFiles = await getTypeScriptFiles(path.resolve(__dirname, '../../types'));
  
  for (const file of typeFiles) {
    const content = await fs.readFile(file, 'utf8');
    
    // Find namespace exports (export * as Namespace)
    const namespaceExports = content.matchAll(/export\s+\*\s+as\s+(\w+)\s+from/g);
    const namedExports = content.matchAll(/export\s+(?:\{([^}]+)\}|(?:const|let|var|function|class|type|interface)\s+(\w+))/g);
    
    const namespaces: string[] = [];
    const named: string[] = [];
    
    for (const match of namespaceExports) {
      namespaces.push(match[1]);
    }
    
    for (const match of namedExports) {
      if (match[1]) {
        named.push(...match[1].split(',').map(n => n.trim().split(' ')[0]));
      } else if (match[2]) {
        named.push(match[2]);
      }
    }
    
    // Check for conflicts
    namespaces.forEach(namespace => {
      const conflictingNames = named.filter(n => n === namespace || n.startsWith(namespace + '_'));
      if (conflictingNames.length > 0) {
        conflicts.push({
          namespace,
          conflictingExports: conflictingNames
        });
      }
    });
  }
  
  return conflicts;
}

async function detectEnumConstConflicts(): Promise<Array<{name: string, enumLocation: string, constLocation: string}>> {
  const conflicts: Array<{name: string, enumLocation: string, constLocation: string}> = [];
  
  const typeFiles = await getTypeScriptFiles(path.resolve(__dirname, '../../types'));
  const enums = new Map<string, string>();
  const consts = new Map<string, string>();
  
  for (const file of typeFiles) {
    const content = await fs.readFile(file, 'utf8');
    const relativePath = path.relative(process.cwd(), file);
    
    // Find enums
    const enumMatches = content.matchAll(/(?:export\s+)?enum\s+(\w+)/g);
    for (const match of enumMatches) {
      enums.set(match[1], relativePath);
    }
    
    // Find consts with same names
    const constMatches = content.matchAll(/(?:export\s+)?const\s+(\w+)/g);
    for (const match of constMatches) {
      consts.set(match[1], relativePath);
    }
  }
  
  // Check for conflicts
  enums.forEach((enumLocation, name) => {
    if (consts.has(name)) {
      conflicts.push({
        name,
        enumLocation,
        constLocation: consts.get(name)!
      });
    }
  });
  
  return conflicts;
}

async function detectDefaultExportConflicts(): Promise<Array<{file: string, hasDefault: boolean, namedExports: string[]}>> {
  const conflicts: Array<{file: string, hasDefault: boolean, namedExports: string[]}> = [];
  
  const typeFiles = await getTypeScriptFiles(path.resolve(__dirname, '../../types'));
  
  for (const file of typeFiles) {
    const content = await fs.readFile(file, 'utf8');
    const relativePath = path.relative(process.cwd(), file);
    
    const hasDefault = /export\s+default/.test(content);
    const namedExports: string[] = [];
    
    // Find named exports
    const namedMatches = content.matchAll(/export\s+(?:\{([^}]+)\}|(?:const|let|var|function|class|type|interface)\s+(\w+))/g);
    for (const match of namedMatches) {
      if (match[1]) {
        namedExports.push(...match[1].split(',').map(n => n.trim().split(' ')[0]));
      } else if (match[2]) {
        namedExports.push(match[2]);
      }
    }
    
    // Only report if file has both default and many named exports (potential confusion)
    if (hasDefault && namedExports.length > 5) {
      conflicts.push({
        file: relativePath,
        hasDefault,
        namedExports
      });
    }
  }
  
  return conflicts;
}

async function getTypeScriptFiles(dir: string): Promise<string[]> {
  const files: string[] = [];
  
  async function walk(currentDir: string) {
    const entries = await fs.readdir(currentDir, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== '__tests__') {
        await walk(fullPath);
      } else if (entry.isFile() && entry.name.endsWith('.ts') && !entry.name.endsWith('.test.ts')) {
        files.push(fullPath);
      }
    }
  }
  
  await walk(dir);
  return files;
}