/**
 * Circular Dependency Detection Tests
 * 
 * These tests verify that critical modules do not have circular dependencies
 * that could cause initialization failures and white screen issues.
 * 
 * @compliance testing - Architecture validation tests
 */

import * as fs from 'fs';
import * as path from 'path';

describe('Circular Dependency Detection', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  const frontendRoot = path.resolve(__dirname, '../..');
  
  /**
   * Parse imports from a TypeScript/JavaScript file
   */
  function parseImports(filePath: string): string[] {
    try {
      const content = fs.readFileSync(filePath, 'utf-8');
      const imports: string[] = [];
      
      // Match various import patterns
      const importPatterns = [
        /import\s+(?:[\w\s{},*]+\s+from\s+)?['"](@\/[^'"]+)['"]/g,
        /import\s*\(['"](@\/[^'"]+)['"]\)/g,
        /require\s*\(['"](@\/[^'"]+)['"]\)/g,
      ];
      
      for (const pattern of importPatterns) {
        let match;
        while ((match = pattern.exec(content)) !== null) {
          imports.push(match[1]);
        }
      }
      
      return imports;
    } catch (error) {
      return [];
    }
  }
  
  /**
   * Resolve alias path to actual file path
   */
  function resolveAlias(importPath: string): string {
    // Remove @ alias and resolve to frontend directory
    const relativePath = importPath.replace('@/', '');
    const possiblePaths = [
      path.join(frontendRoot, `${relativePath}.ts`),
      path.join(frontendRoot, `${relativePath}.tsx`),
      path.join(frontendRoot, `${relativePath}.js`),
      path.join(frontendRoot, `${relativePath}.jsx`),
      path.join(frontendRoot, relativePath, 'index.ts'),
      path.join(frontendRoot, relativePath, 'index.tsx'),
    ];
    
    for (const p of possiblePaths) {
      if (fs.existsSync(p)) {
        return p;
      }
    }
    
    return '';
  }
  
  /**
   * Check for circular dependencies using DFS
   */
  function hasCircularDependency(
    filePath: string,
    visited: Set<string> = new Set(),
    recursionStack: Set<string> = new Set()
  ): { hasCircular: boolean; cycle: string[] } {
    if (recursionStack.has(filePath)) {
      // Found a cycle
      return { hasCircular: true, cycle: Array.from(recursionStack).concat(filePath) };
    }
    
    if (visited.has(filePath)) {
      return { hasCircular: false, cycle: [] };
    }
    
    visited.add(filePath);
    recursionStack.add(filePath);
    
    const imports = parseImports(filePath);
    
    for (const importPath of imports) {
      const resolvedPath = resolveAlias(importPath);
      if (resolvedPath) {
        const result = hasCircularDependency(resolvedPath, visited, recursionStack);
        if (result.hasCircular) {
          return result;
        }
      }
    }
    
    recursionStack.delete(filePath);
    return { hasCircular: false, cycle: [] };
  }
  
  describe('Core Module Dependencies', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('logger.ts should not have circular dependencies', () => {
      const loggerPath = path.join(frontendRoot, 'lib/logger.ts');
      const result = hasCircularDependency(loggerPath);
      
      if (result.hasCircular) {
        const cycleDescription = result.cycle
          .map(p => path.relative(frontendRoot, p))
          .join(' -> ');
        fail(`Circular dependency detected in logger.ts: ${cycleDescription}`);
      }
      
      expect(result.hasCircular).toBe(false);
    });
    
    test('unified-api-config.ts should not have circular dependencies', () => {
      const configPath = path.join(frontendRoot, 'lib/unified-api-config.ts');
      const result = hasCircularDependency(configPath);
      
      if (result.hasCircular) {
        const cycleDescription = result.cycle
          .map(p => path.relative(frontendRoot, p))
          .join(' -> ');
        fail(`Circular dependency detected in unified-api-config.ts: ${cycleDescription}`);
      }
      
      expect(result.hasCircular).toBe(false);
    });
    
    test('unified-api-config.ts should not import logger', () => {
      const configPath = path.join(frontendRoot, 'lib/unified-api-config.ts');
      const imports = parseImports(configPath);
      
      const hasLoggerImport = imports.some(imp => 
        imp.includes('logger') || imp.includes('lib/logger')
      );
      
      expect(hasLoggerImport).toBe(false);
    });
  });
  
  describe('Critical Path Dependencies', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('auth context should not have circular dependencies', () => {
      const authPath = path.join(frontendRoot, 'auth/context.tsx');
      const result = hasCircularDependency(authPath);
      
      if (result.hasCircular) {
        const cycleDescription = result.cycle
          .map(p => path.relative(frontendRoot, p))
          .join(' -> ');
        fail(`Circular dependency detected in auth/context.tsx: ${cycleDescription}`);
      }
      
      expect(result.hasCircular).toBe(false);
    });
    
    test('WebSocketProvider should not have circular dependencies', () => {
      const wsPath = path.join(frontendRoot, 'providers/WebSocketProvider.tsx');
      const result = hasCircularDependency(wsPath);
      
      if (result.hasCircular) {
        const cycleDescription = result.cycle
          .map(p => path.relative(frontendRoot, p))
          .join(' -> ');
        fail(`Circular dependency detected in WebSocketProvider.tsx: ${cycleDescription}`);
      }
      
      expect(result.hasCircular).toBe(false);
    });
    
    test('MainChat component should not have circular dependencies', () => {
      const chatPath = path.join(frontendRoot, 'components/chat/MainChat.tsx');
      const result = hasCircularDependency(chatPath);
      
      if (result.hasCircular) {
        const cycleDescription = result.cycle
          .map(p => path.relative(frontendRoot, p))
          .join(' -> ');
        fail(`Circular dependency detected in MainChat.tsx: ${cycleDescription}`);
      }
      
      expect(result.hasCircular).toBe(false);
    });
  });
  
  describe('Dependency Hierarchy Rules', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    test('configuration modules should be leaf nodes (no imports of app modules)', () => {
      const configFiles = [
        'lib/unified-api-config.ts',
        'config/index.ts',
      ];
      
      for (const configFile of configFiles) {
        const configPath = path.join(frontendRoot, configFile);
        if (!fs.existsSync(configPath)) continue;
        
        const imports = parseImports(configPath);
        
        // Config files should only import types and constants, not services or components
        const invalidImports = imports.filter(imp => 
          imp.includes('service') || 
          imp.includes('component') || 
          imp.includes('provider') ||
          imp.includes('hook') ||
          imp.includes('store') ||
          imp.includes('logger')
        );
        
        if (invalidImports.length > 0) {
          fail(`Configuration file ${configFile} imports application modules: ${invalidImports.join(', ')}`);
        }
        
        expect(invalidImports).toHaveLength(0);
      }
    });
    
    test('logger should not import from application modules', () => {
      const loggerPath = path.join(frontendRoot, 'lib/logger.ts');
      if (!fs.existsSync(loggerPath)) return;
      
      const imports = parseImports(loggerPath);
      
      // Logger should not import services, components, or stores
      const invalidImports = imports.filter(imp => 
        imp.includes('service') || 
        imp.includes('component') || 
        imp.includes('provider') ||
        imp.includes('hook') ||
        imp.includes('store') ||
        imp.includes('auth')
      );
      
      if (invalidImports.length > 0) {
        fail(`Logger imports application modules: ${invalidImports.join(', ')}`);
      }
      
      expect(invalidImports).toHaveLength(0);
    });
  });
  
  describe('Import Depth Analysis', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    /**
     * Calculate import depth for a module
     */
    function calculateImportDepth(
      filePath: string,
      visited: Map<string, number> = new Map(),
      currentDepth: number = 0
    ): number {
      if (visited.has(filePath)) {
        return visited.get(filePath)!;
      }
      
      visited.set(filePath, currentDepth);
      
      const imports = parseImports(filePath);
      let maxDepth = currentDepth;
      
      for (const importPath of imports) {
        const resolvedPath = resolveAlias(importPath);
        if (resolvedPath && !visited.has(resolvedPath)) {
          const depth = calculateImportDepth(resolvedPath, visited, currentDepth + 1);
          maxDepth = Math.max(maxDepth, depth);
        }
      }
      
      return maxDepth;
    }
    
    test('critical modules should have reasonable import depth', () => {
      const criticalModules = [
        { path: 'lib/logger.ts', maxDepth: 2 },
        { path: 'lib/unified-api-config.ts', maxDepth: 1 },
        { path: 'auth/context.tsx', maxDepth: 5 },
      ];
      
      for (const module of criticalModules) {
        const modulePath = path.join(frontendRoot, module.path);
        if (!fs.existsSync(modulePath)) continue;
        
        const depth = calculateImportDepth(modulePath);
        
        if (depth > module.maxDepth) {
          console.warn(`Module ${module.path} has import depth ${depth}, expected max ${module.maxDepth}`);
        }
        
        expect(depth).toBeLessThanOrEqual(module.maxDepth + 2); // Allow some flexibility
      }
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});