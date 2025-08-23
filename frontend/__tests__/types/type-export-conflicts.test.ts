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
  const registryPath = path.resolve(__dirname, '../../types/registry.ts');
  const typesDir = path.resolve(__dirname, '../../types');

  /**
   * This test will FAIL if type-only exports conflict with runtime exports
   */
  it('should FAIL if type-only exports conflict with runtime exports', async () => {
    const content = await fs.readFile(registryPath, 'utf8');
    const typeOnlyExports = extractTypeOnlyExports(content);
    const runtimeExports = extractRuntimeExports(content);
    const conflicts = findTypeRuntimeConflicts(typeOnlyExports, runtimeExports);
    
    // This assertion will FAIL if conflicts exist
    expect(conflicts).toEqual([]);
    
    if (conflicts.length > 0) {
      console.error('❌ Type-Runtime export conflicts detected:');
      conflicts.forEach(conflict => {
        console.error(`  ${conflict.name}:`);
        if (conflict.typeExport) {
          console.error(`    Type export at line ${conflict.typeExport.line}`);
        }
        if (conflict.runtimeExport) {
          console.error(`    Runtime export at line ${conflict.runtimeExport.line}`);
        }
        console.error(`    Conflict type: ${conflict.conflictType}`);
      });
      throw new Error(`Found ${conflicts.length} type-runtime export conflicts`);
    }
  });

  /**
   * This test will FAIL on interface vs function naming conflicts
   */
  it('should detect interface vs function export naming conflicts', async () => {
    const namingConflicts = await detectNamingConflicts();
    
    // Expected to FAIL if naming conflicts exist
    expect(namingConflicts).toHaveLength(0);
    
    if (namingConflicts.length > 0) {
      console.error('❌ Interface/Function naming conflicts:');
      namingConflicts.forEach(conflict => {
        console.error(`  Name: ${conflict.name}`);
        console.error(`    Interface in: ${conflict.interfaceLocation}`);
        console.error(`    Function in: ${conflict.functionLocation}`);
      });
    }
  });

  /**
   * This test will FAIL if TypeScript compiler reports export errors
   */
  it('should FAIL if TypeScript compiler reports export errors', () => {
    const program = createTypeScriptProgram([registryPath]);
    const diagnostics = getExportDiagnostics(program);
    
    // Filter for export-related errors
    const exportErrors = diagnostics.filter(d => {
      return d.code === 2300 || // Duplicate identifier
             d.code === 2393 || // Duplicate function implementation
             d.code === 2451 || // Cannot redeclare block-scoped variable
             d.code === 2452 || // Enum member expected
             d.code === 1148;   // Cannot compile modules unless --module flag provided
    });
    
    // Will FAIL if export errors exist
    expect(exportErrors).toHaveLength(0);
    
    if (exportErrors.length > 0) {
      console.error('❌ TypeScript export errors:');
      exportErrors.forEach(error => {
        const message = ts.flattenDiagnosticMessageText(error.messageText, '\n');
        const file = error.file ? path.relative(process.cwd(), error.file.fileName) : 'unknown';
        const line = error.file && error.start ? 
          error.file.getLineAndCharacterOfPosition(error.start).line + 1 : 0;
        
        console.error(`  ${file}:${line} - Error TS${error.code}: ${message}`);
      });
    }
  });

  /**
   * Test for mixed export style conflicts (export type vs export)
   */
  it('should FAIL on mixed export style conflicts', async () => {
    const mixedStyleConflicts = await detectMixedExportStyles();
    
    // Will FAIL if mixed style conflicts exist
    expect(mixedStyleConflicts).toHaveLength(0);
    
    if (mixedStyleConflicts.length > 0) {
      console.error('❌ Mixed export style conflicts:');
      mixedStyleConflicts.forEach(conflict => {
        console.error(`  ${conflict.name}:`);
        console.error(`    Exported as type: ${conflict.exportedAsType}`);
        console.error(`    Exported as value: ${conflict.exportedAsValue}`);
        console.error(`    Files: ${conflict.files.join(', ')}`);
      });
    }
  });

  /**
   * Test for re-export type conflicts
   */
  it('should FAIL on re-export type mismatches', async () => {
    const reExportMismatches = await detectReExportTypeMismatches();
    
    // Will FAIL if mismatches exist
    expect(reExportMismatches).toHaveLength(0);
    
    if (reExportMismatches.length > 0) {
      console.error('❌ Re-export type mismatches:');
      reExportMismatches.forEach(mismatch => {
        console.error(`  ${mismatch.name}:`);
        console.error(`    Original: ${mismatch.originalType} from ${mismatch.originalFile}`);
        console.error(`    Re-exported as: ${mismatch.reExportType} in ${mismatch.reExportFile}`);
      });
    }
  });

  /**
   * Test for namespace vs named export conflicts
   */
  it('should FAIL on namespace vs named export conflicts', async () => {
    const namespaceConflicts = await detectNamespaceExportConflicts();
    
    // Will FAIL if conflicts exist
    expect(namespaceConflicts).toHaveLength(0);
    
    if (namespaceConflicts.length > 0) {
      console.error('❌ Namespace export conflicts:');
      namespaceConflicts.forEach(conflict => {
        console.error(`  Namespace: ${conflict.namespace}`);
        console.error(`    Conflicts with named exports: ${conflict.conflictingExports.join(', ')}`);
      });
    }
  });

  /**
   * Test for enum vs const conflicts
   */
  it('should FAIL if enums conflict with const exports', async () => {
    const enumConflicts = await detectEnumConstConflicts();
    
    // Will FAIL if conflicts exist
    expect(enumConflicts).toHaveLength(0);
    
    if (enumConflicts.length > 0) {
      console.error('❌ Enum/Const conflicts:');
      enumConflicts.forEach(conflict => {
        console.error(`  ${conflict.name}:`);
        console.error(`    Enum in: ${conflict.enumLocation}`);
        console.error(`    Const in: ${conflict.constLocation}`);
      });
    }
  });

  /**
   * Test for default export conflicts with named exports
   */
  it('should FAIL on default export conflicts with named exports', async () => {
    const defaultExportConflicts = await detectDefaultExportConflicts();
    
    // Will FAIL if conflicts exist
    expect(defaultExportConflicts).toHaveLength(0);
    
    if (defaultExportConflicts.length > 0) {
      console.error('❌ Default export conflicts:');
      defaultExportConflicts.forEach(conflict => {
        console.error(`  File: ${conflict.file}`);
        console.error(`    Has default export: ${conflict.hasDefault}`);
        console.error(`    Named exports that might conflict: ${conflict.namedExports.join(', ')}`);
      });
    }
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