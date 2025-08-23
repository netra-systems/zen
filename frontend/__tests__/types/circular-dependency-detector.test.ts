/**
 * Circular Dependency Detection Test Suite
 * 
 * PURPOSE: This test suite is designed to FAIL when circular dependencies exist
 * in the module system. These tests detect import cycles that can cause:
 * - Module initialization errors
 * - Temporal dead zones
 * - Undefined exports at runtime
 * - Build-time resolution failures
 * 
 * EXPECTED FAILURES:
 * - Test 1: Will FAIL if circular dependencies exist between type modules
 * - Test 2: Will FAIL on mutual imports between registry and domain modules
 * - Test 3: Will FAIL on module initialization order issues
 * - Test 4: Will FAIL on temporal dead zone detection
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { parse } from '@babel/parser';
import traverse from '@babel/traverse';

interface DependencyNode {
  path: string;
  imports: string[];
  exports: string[];
}

interface CircularDependency {
  cycle: string[];
  severity: 'critical' | 'warning' | 'info';
}

describe('Circular Dependency Detection', () => {
  const typesDirPath = path.resolve(__dirname, '../../types');

  /**
   * This test will FAIL if circular dependencies exist in type modules
   */
  it('should FAIL if circular dependencies exist in type modules', async () => {
    const graph = await buildModuleDependencyGraph();
    const cycles = detectCircularDependencies(graph);
    
    // This assertion will FAIL if cycles exist
    expect(cycles).toEqual([]);
    
    if (cycles.length > 0) {
      console.error('❌ Circular dependencies detected:');
      cycles.forEach(cycle => {
        console.error(`  Cycle: ${cycle.cycle.join(' → ')} → ${cycle.cycle[0]}`);
        console.error(`  Severity: ${cycle.severity}`);
      });
      throw new Error(`Found ${cycles.length} circular dependencies`);
    }
  });

  /**
   * This test will FAIL on mutual imports between registry and domain modules
   */
  it('should detect mutual imports between registry and domain modules', async () => {
    const mutualImports = await detectMutualImports([
      path.join(typesDirPath, 'registry.ts'),
      path.join(typesDirPath, 'domains/websocket.ts'),
      path.join(typesDirPath, 'shared/enums.ts'),
      path.join(typesDirPath, 'shared/base.ts')
    ]);
    
    // Expected to FAIL - mutual imports likely exist
    expect(mutualImports).toHaveLength(0);
    
    if (mutualImports.length > 0) {
      console.error('❌ Mutual imports detected:');
      mutualImports.forEach(mutual => {
        console.error(`  ${mutual.fileA} ↔ ${mutual.fileB}`);
        console.error(`    Shared dependencies: ${mutual.sharedDeps.join(', ')}`);
      });
    }
  });

  /**
   * This test will FAIL if module initialization creates temporal dead zones
   */
  it('should FAIL if module initialization creates temporal dead zones', () => {
    const importOrders = [
      ['../../types/registry', '../../types/shared/enums'],
      ['../../types/shared/enums', '../../types/registry'],
      ['../../types/domains/websocket', '../../types/registry'],
      ['../../types/registry', '../../types/domains/websocket', '../../types/shared/base']
    ];
    
    const failures: Array<{order: string[], error: string}> = [];
    
    importOrders.forEach(order => {
      try {
        // Clear module cache to test fresh initialization
        order.forEach(modulePath => {
          const fullPath = require.resolve(modulePath);
          delete require.cache[fullPath];
        });
        
        // Attempt to require modules in specified order
        const modules = order.map(modulePath => {
          try {
            return require(modulePath);
          } catch (err: any) {
            throw new Error(`Failed to load ${modulePath}: ${err.message}`);
          }
        });
        
        // Validate all modules loaded successfully
        modules.forEach((mod, idx) => {
          if (!mod || Object.keys(mod).length === 0) {
            throw new Error(`Module ${order[idx]} loaded but is empty`);
          }
        });
        
      } catch (error: any) {
        failures.push({ order, error: error.message });
      }
    });
    
    // This will FAIL if any import order causes issues
    expect(failures).toHaveLength(0);
    
    if (failures.length > 0) {
      console.error('❌ Module initialization failures:');
      failures.forEach(failure => {
        console.error(`  Order: ${failure.order.map(p => path.basename(p)).join(' → ')}`);
        console.error(`  Error: ${failure.error}`);
      });
    }
  });

  /**
   * Test for deep circular dependency chains
   */
  it('should FAIL on deep circular dependency chains', async () => {
    const deepChains = await findDeepCircularChains(3); // Find chains longer than 3 modules
    
    // Will FAIL if deep chains exist
    expect(deepChains).toHaveLength(0);
    
    if (deepChains.length > 0) {
      console.error('❌ Deep circular dependency chains found:');
      deepChains.forEach(chain => {
        console.error(`  Chain length ${chain.length}: ${chain.join(' → ')}`);
      });
    }
  });

  /**
   * Test for self-referential imports
   */
  it('should FAIL if modules import themselves', async () => {
    const selfImports = await detectSelfReferentialImports();
    
    // Will FAIL if self-imports exist
    expect(selfImports).toHaveLength(0);
    
    if (selfImports.length > 0) {
      console.error('❌ Self-referential imports detected:');
      selfImports.forEach(file => {
        console.error(`  ${file} imports itself`);
      });
    }
  });

  /**
   * Test for indirect circular dependencies through re-exports
   */
  it('should FAIL on indirect circular dependencies through re-exports', async () => {
    const indirectCycles = await detectIndirectCircularDependencies();
    
    // Will FAIL if indirect cycles exist
    expect(indirectCycles).toHaveLength(0);
    
    if (indirectCycles.length > 0) {
      console.error('❌ Indirect circular dependencies through re-exports:');
      indirectCycles.forEach(cycle => {
        console.error(`  ${cycle.description}`);
        console.error(`    Path: ${cycle.path.join(' → ')}`);
      });
    }
  });

  /**
   * Test for barrel file circular dependencies
   */
  it('should FAIL if barrel files create circular dependencies', async () => {
    const barrelCycles = await detectBarrelFileCircularDependencies();
    
    // Will FAIL if barrel file cycles exist
    expect(barrelCycles).toHaveLength(0);
    
    if (barrelCycles.length > 0) {
      console.error('❌ Barrel file circular dependencies:');
      barrelCycles.forEach(cycle => {
        console.error(`  Barrel: ${cycle.barrel}`);
        console.error(`    Imports from: ${cycle.importedModules.join(', ')}`);
        console.error(`    Which import back: ${cycle.circularImports.join(', ')}`);
      });
    }
  });
});

// Helper functions
async function buildModuleDependencyGraph(): Promise<Map<string, DependencyNode>> {
  const graph = new Map<string, DependencyNode>();
  const typeFiles = await getTypeScriptFiles(path.resolve(__dirname, '../../types'));
  
  for (const file of typeFiles) {
    const content = await fs.readFile(file, 'utf8');
    const imports = extractImports(content);
    const exports = extractExports(content);
    
    graph.set(file, {
      path: file,
      imports: resolveImportPaths(file, imports),
      exports
    });
  }
  
  return graph;
}

async function getTypeScriptFiles(dir: string): Promise<string[]> {
  const files: string[] = [];
  
  async function walk(currentDir: string) {
    const entries = await fs.readdir(currentDir, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory() && !entry.name.startsWith('.')) {
        await walk(fullPath);
      } else if (entry.isFile() && entry.name.endsWith('.ts') && !entry.name.endsWith('.test.ts')) {
        files.push(fullPath);
      }
    }
  }
  
  await walk(dir);
  return files;
}

function extractImports(content: string): string[] {
  const imports: string[] = [];
  const importRegex = /import\s+(?:type\s+)?(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+['"]([^'"]+)['"]/g;
  let match;
  
  while ((match = importRegex.exec(content)) !== null) {
    imports.push(match[1]);
  }
  
  return imports;
}

function extractExports(content: string): string[] {
  const exports: string[] = [];
  const exportRegex = /export\s+(?:type\s+)?(?:\{([^}]+)\}|(?:const|let|var|function|class|interface|type|enum)\s+(\w+))/g;
  let match;
  
  while ((match = exportRegex.exec(content)) !== null) {
    if (match[1]) {
      // Named exports
      exports.push(...match[1].split(',').map(e => e.trim().split(' ')[0]));
    } else if (match[2]) {
      // Direct exports
      exports.push(match[2]);
    }
  }
  
  return exports;
}

function resolveImportPaths(fromFile: string, imports: string[]): string[] {
  return imports.map(imp => {
    if (imp.startsWith('.')) {
      return path.resolve(path.dirname(fromFile), imp) + '.ts';
    }
    return imp;
  });
}

function detectCircularDependencies(graph: Map<string, DependencyNode>): CircularDependency[] {
  const cycles: CircularDependency[] = [];
  const visited = new Set<string>();
  const recursionStack = new Set<string>();
  
  function dfs(node: string, path: string[] = []): void {
    visited.add(node);
    recursionStack.add(node);
    path.push(node);
    
    const nodeData = graph.get(node);
    if (nodeData) {
      for (const dep of nodeData.imports) {
        if (graph.has(dep)) {
          if (!visited.has(dep)) {
            dfs(dep, [...path]);
          } else if (recursionStack.has(dep)) {
            // Found a cycle
            const cycleStart = path.indexOf(dep);
            const cycle = path.slice(cycleStart).map(p => path.relative(process.cwd(), p));
            cycles.push({
              cycle,
              severity: cycle.length <= 2 ? 'critical' : cycle.length <= 4 ? 'warning' : 'info'
            });
          }
        }
      }
    }
    
    recursionStack.delete(node);
  }
  
  for (const node of graph.keys()) {
    if (!visited.has(node)) {
      dfs(node);
    }
  }
  
  return cycles;
}

async function detectMutualImports(files: string[]): Promise<Array<{fileA: string, fileB: string, sharedDeps: string[]}>> {
  const mutualImports: Array<{fileA: string, fileB: string, sharedDeps: string[]}> = [];
  const importMap = new Map<string, Set<string>>();
  
  // Build import map
  for (const file of files) {
    try {
      const content = await fs.readFile(file, 'utf8');
      const imports = extractImports(content);
      importMap.set(file, new Set(resolveImportPaths(file, imports)));
    } catch {
      // File might not exist, skip
    }
  }
  
  // Check for mutual imports
  const checked = new Set<string>();
  for (const [fileA, importsA] of importMap.entries()) {
    for (const [fileB, importsB] of importMap.entries()) {
      if (fileA !== fileB && !checked.has(`${fileA}-${fileB}`) && !checked.has(`${fileB}-${fileA}`)) {
        const sharedDeps: string[] = [];
        
        // Check if A imports B and B imports A (directly or indirectly)
        if (importsA.has(fileB) && importsB.has(fileA)) {
          mutualImports.push({
            fileA: path.relative(process.cwd(), fileA),
            fileB: path.relative(process.cwd(), fileB),
            sharedDeps
          });
        }
        
        checked.add(`${fileA}-${fileB}`);
      }
    }
  }
  
  return mutualImports;
}

async function findDeepCircularChains(minLength: number): Promise<string[][]> {
  const graph = await buildModuleDependencyGraph();
  const cycles = detectCircularDependencies(graph);
  
  return cycles
    .filter(c => c.cycle.length >= minLength)
    .map(c => c.cycle);
}

async function detectSelfReferentialImports(): Promise<string[]> {
  const selfImports: string[] = [];
  const typeFiles = await getTypeScriptFiles(path.resolve(__dirname, '../../types'));
  
  for (const file of typeFiles) {
    const content = await fs.readFile(file, 'utf8');
    const imports = extractImports(content);
    const resolvedImports = resolveImportPaths(file, imports);
    
    if (resolvedImports.includes(file)) {
      selfImports.push(path.relative(process.cwd(), file));
    }
  }
  
  return selfImports;
}

async function detectIndirectCircularDependencies(): Promise<Array<{description: string, path: string[]}>> {
  const indirectCycles: Array<{description: string, path: string[]}> = [];
  
  // Simulated detection - in real implementation would trace through re-export chains
  // Check if registry re-exports from modules that import registry
  const registryPath = path.resolve(__dirname, '../../types/registry.ts');
  const registryContent = await fs.readFile(registryPath, 'utf8');
  
  // Extract re-export sources
  const reExportRegex = /export\s+(?:\{[^}]+\}|\*)\s+from\s+['"]([^'"]+)['"]/g;
  let match;
  const reExportSources: string[] = [];
  
  while ((match = reExportRegex.exec(registryContent)) !== null) {
    reExportSources.push(match[1]);
  }
  
  // Check if any re-export source imports registry
  for (const source of reExportSources) {
    const sourcePath = path.resolve(path.dirname(registryPath), source) + '.ts';
    try {
      const sourceContent = await fs.readFile(sourcePath, 'utf8');
      if (sourceContent.includes("from './registry'") || sourceContent.includes('from "../registry"')) {
        indirectCycles.push({
          description: `Registry re-exports from ${source} which imports registry`,
          path: ['registry.ts', source, 'registry.ts']
        });
      }
    } catch {
      // Source file might not exist
    }
  }
  
  return indirectCycles;
}

async function detectBarrelFileCircularDependencies(): Promise<Array<{barrel: string, importedModules: string[], circularImports: string[]}>> {
  const barrelCycles: Array<{barrel: string, importedModules: string[], circularImports: string[]}> = [];
  
  // Registry.ts is a barrel file
  const registryPath = path.resolve(__dirname, '../../types/registry.ts');
  const registryContent = await fs.readFile(registryPath, 'utf8');
  
  // Get all modules registry imports from
  const importedModules = extractImports(registryContent);
  const circularImports: string[] = [];
  
  // Check if any of those modules import back from registry
  for (const module of importedModules) {
    const modulePath = path.resolve(path.dirname(registryPath), module) + '.ts';
    try {
      const moduleContent = await fs.readFile(modulePath, 'utf8');
      if (moduleContent.includes("from './registry'") || 
          moduleContent.includes('from "../registry"') ||
          moduleContent.includes("from '@/types/registry'")) {
        circularImports.push(module);
      }
    } catch {
      // Module might not exist
    }
  }
  
  if (circularImports.length > 0) {
    barrelCycles.push({
      barrel: 'types/registry.ts',
      importedModules,
      circularImports
    });
  }
  
  return barrelCycles;
}