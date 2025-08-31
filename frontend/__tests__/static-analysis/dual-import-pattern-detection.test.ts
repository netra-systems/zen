/**
 * Dual Import Pattern Detection Tests
 * 
 * Static analysis tests to detect and prevent the dual import patterns
 * that caused the WebSocket logger context binding issue.
 * 
 * Reference: SPEC/learnings/websocket_logger_dual_import_context_binding_issue.xml
 * 
 * Problematic Pattern:
 * import { logger } from '@/lib/logger';
 * import { logger as debugLogger } from '@/lib/logger';
 */

import fs from 'fs';
import path from 'path';
import { glob } from 'glob';

interface ImportStatement {
  line: number;
  statement: string;
  module: string;
  imports: string[];
  hasAlias: boolean;
  aliasName?: string;
}

interface DualImportViolation {
  file: string;
  module: string;
  imports: ImportStatement[];
  severity: 'ERROR' | 'WARNING';
  description: string;
}

class DualImportDetector {
  private violations: DualImportViolation[] = [];
  
  // Modules that are particularly vulnerable to dual import issues
  private singletonModules = [
    '@/lib/logger',
    '@/services/webSocketService',
    '@/lib/unified-auth-service',
    '@/config',
    '@/store'
  ];

  async scanDirectory(basePath: string): Promise<DualImportViolation[]> {
    this.violations = [];
    
    const files = await glob('**/*.{ts,tsx,js,jsx}', {
      cwd: basePath,
      ignore: ['node_modules/**', 'dist/**', 'build/**', '__tests__/**/*.test.*']
    });

    for (const file of files) {
      const fullPath = path.join(basePath, file);
      await this.scanFile(fullPath, file);
    }

    return this.violations;
  }

  private async scanFile(filePath: string, relativePath: string): Promise<void> {
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      const lines = content.split('\n');
      
      const imports = this.extractImports(lines);
      const duplicateImports = this.findDuplicateImports(imports);
      
      duplicateImports.forEach(violation => {
        this.violations.push({
          file: relativePath,
          ...violation
        });
      });
    } catch (error) {
      // Skip files that can't be read
    }
  }

  private extractImports(lines: string[]): ImportStatement[] {
    const imports: ImportStatement[] = [];
    const importRegex = /^import\s+(.+?)\s+from\s+['"]([^'"]+)['"];?$/;
    
    lines.forEach((line, index) => {
      const trimmed = line.trim();
      if (trimmed.startsWith('import ')) {
        const match = trimmed.match(importRegex);
        if (match) {
          const [, importClause, module] = match;
          const hasAlias = importClause.includes(' as ');
          
          imports.push({
            line: index + 1,
            statement: trimmed,
            module,
            imports: this.parseImportClause(importClause),
            hasAlias,
            aliasName: hasAlias ? this.extractAliasName(importClause) : undefined
          });
        }
      }
    });
    
    return imports;
  }

  private parseImportClause(clause: string): string[] {
    // Handle different import patterns
    if (clause.includes('{')) {
      // Named imports: { logger, config }
      const namedImports = clause.match(/\{([^}]+)\}/)?.[1];
      if (namedImports) {
        return namedImports.split(',').map(imp => imp.trim().split(' as ')[0].trim());
      }
    } else if (clause.includes(' as ')) {
      // Default import with alias: logger as debugLogger
      return [clause.split(' as ')[0].trim()];
    } else {
      // Default import: logger
      return [clause.trim()];
    }
    
    return [];
  }

  private extractAliasName(clause: string): string | undefined {
    const aliasMatch = clause.match(/\bas\s+(\w+)/);
    return aliasMatch?.[1];
  }

  private findDuplicateImports(imports: ImportStatement[]): Omit<DualImportViolation, 'file'>[] {
    const violations: Omit<DualImportViolation, 'file'>[] = [];
    const moduleImports = new Map<string, ImportStatement[]>();
    
    // Group imports by module
    imports.forEach(imp => {
      if (!moduleImports.has(imp.module)) {
        moduleImports.set(imp.module, []);
      }
      moduleImports.get(imp.module)!.push(imp);
    });

    // Check for violations
    moduleImports.forEach((moduleImportList, module) => {
      if (moduleImportList.length > 1) {
        // Check if it's the exact problematic pattern from the learning
        const hasDirectAndAliasedImport = this.hasDirectAndAliasedImport(moduleImportList);
        
        if (hasDirectAndAliasedImport && this.singletonModules.includes(module)) {
          violations.push({
            module,
            imports: moduleImportList,
            severity: 'ERROR',
            description: `Critical dual import pattern detected for singleton module '${module}'. This pattern caused the WebSocket logger context binding issue.`
          });
        } else if (moduleImportList.length > 1) {
          violations.push({
            module,
            imports: moduleImportList,
            severity: 'WARNING',
            description: `Multiple imports detected for module '${module}'. Consider consolidating to prevent potential context binding issues.`
          });
        }
      }
    });

    return violations;
  }

  private hasDirectAndAliasedImport(imports: ImportStatement[]): boolean {
    const hasDirectImport = imports.some(imp => !imp.hasAlias);
    const hasAliasedImport = imports.some(imp => imp.hasAlias);
    
    // Check for the exact pattern from the learning:
    // import { logger } from '@/lib/logger';
    // import { logger as debugLogger } from '@/lib/logger';
    const loggerImports = imports.filter(imp => 
      imp.imports.includes('logger') || 
      (imp.hasAlias && imp.aliasName?.includes('logger'))
    );
    
    return hasDirectImport && hasAliasedImport && loggerImports.length >= 2;
  }
}

describe('Dual Import Pattern Detection', () => {
  let detector: DualImportDetector;

  beforeEach(() => {
    detector = new DualImportDetector();
  });

  it('should detect the exact problematic dual import pattern from the learning', async () => {
    // Create test files with the exact problematic patterns
    const testFiles = [
      {
        path: 'test-websocket-provider.tsx',
        content: `
import React from 'react';
import { logger } from '@/lib/logger';
import { logger as debugLogger } from '@/lib/logger';

export const TestComponent = () => {
  return <div>Test</div>;
};
        `
      },
      {
        path: 'test-websocket-service.ts',
        content: `
import { WebSocketMessage } from '@/types/unified';
import { logger } from '@/lib/logger';
import { logger as debugLogger } from '@/lib/logger';

export class TestService {
  connect() {}
}
        `
      }
    ];

    const violations: DualImportViolation[] = [];

    for (const testFile of testFiles) {
      const lines = testFile.content.split('\n');
      const imports = (detector as any).extractImports(lines);
      const fileViolations = (detector as any).findDuplicateImports(imports);
      
      fileViolations.forEach((violation: any) => {
        violations.push({
          file: testFile.path,
          ...violation
        });
      });
    }

    // Should detect the exact problematic pattern
    expect(violations).toHaveLength(2);
    
    violations.forEach(violation => {
      expect(violation.module).toBe('@/lib/logger');
      expect(violation.severity).toBe('ERROR');
      expect(violation.description).toContain('Critical dual import pattern detected');
      expect(violation.imports).toHaveLength(2);
      
      // Verify both direct and aliased imports are detected
      const hasDirectImport = violation.imports.some(imp => !imp.hasAlias);
      const hasAliasedImport = violation.imports.some(imp => imp.hasAlias);
      expect(hasDirectImport).toBe(true);
      expect(hasAliasedImport).toBe(true);
    });
  });

  it('should NOT flag safe import patterns', async () => {
    const safeTestFiles = [
      {
        path: 'safe-single-import.tsx',
        content: `
import React from 'react';
import { logger } from '@/lib/logger';

export const SafeComponent = () => {
  logger.info('Safe single import');
  return <div>Safe</div>;
};
        `
      },
      {
        path: 'safe-different-modules.tsx',
        content: `
import { logger } from '@/lib/logger';
import { logger as httpLogger } from '@/lib/http-logger';

export const DifferentModules = () => {
  return <div>Different modules OK</div>;
};
        `
      }
    ];

    const violations: DualImportViolation[] = [];

    for (const testFile of safeTestFiles) {
      const lines = testFile.content.split('\n');
      const imports = (detector as any).extractImports(lines);
      const fileViolations = (detector as any).findDuplicateImports(imports);
      
      fileViolations.forEach((violation: any) => {
        violations.push({
          file: testFile.path,
          ...violation
        });
      });
    }

    // Should not detect violations in safe patterns
    const errorViolations = violations.filter(v => v.severity === 'ERROR');
    expect(errorViolations).toHaveLength(0);
  });

  it('should detect violations in actual codebase files', async () => {
    // Scan the actual frontend directory for violations
    const frontendPath = path.join(process.cwd(), 'frontend');
    
    // Only scan if the directory exists (test environment may not have it)
    if (fs.existsSync(frontendPath)) {
      const violations = await detector.scanDirectory(frontendPath);
      
      // Log violations for awareness but don't fail the test
      // (since the issue should be fixed according to the learning)
      if (violations.length > 0) {
        console.warn('Dual import pattern violations found:', violations);
      }
      
      // The learning indicates this issue was resolved, so we shouldn't find ERROR level violations
      const errorViolations = violations.filter(v => v.severity === 'ERROR');
      expect(errorViolations).toHaveLength(0);
    }
  });

  it('should validate specific files mentioned in the learning are fixed', async () => {
    const filesToCheck = [
      'frontend/providers/WebSocketProvider.tsx',
      'frontend/services/webSocketService.ts'
    ];

    const violations: DualImportViolation[] = [];

    for (const filePath of filesToCheck) {
      const fullPath = path.join(process.cwd(), filePath);
      
      if (fs.existsSync(fullPath)) {
        const content = fs.readFileSync(fullPath, 'utf8');
        const lines = content.split('\n');
        const imports = (detector as any).extractImports(lines);
        const fileViolations = (detector as any).findDuplicateImports(imports);
        
        fileViolations.forEach((violation: any) => {
          violations.push({
            file: filePath,
            ...violation
          });
        });
      }
    }

    // According to the learning, these files should be fixed
    const loggerViolations = violations.filter(v => v.module === '@/lib/logger');
    expect(loggerViolations).toHaveLength(0);
  });

  it('should detect context binding vulnerabilities in extracted methods', () => {
    // Test the method extraction pattern that can cause context loss
    const testMethodExtraction = () => {
      // Mock logger with unbound methods (simulating the vulnerability)
      const vulnerableLogger = {
        log: function(this: any, message: string) {
          // This would fail if 'this' is undefined
          return this.internalLog(message);
        },
        internalLog: function(message: string) {
          return `Logged: ${message}`;
        }
      };

      // The vulnerable pattern: extracting method without binding
      const extractedLog = vulnerableLogger.log;
      
      try {
        extractedLog('test message');
        return 'NO_CONTEXT_LOSS';
      } catch (error: any) {
        if (error.message.includes('Cannot read properties of undefined')) {
          return 'CONTEXT_BINDING_VULNERABILITY';
        }
        return 'UNEXPECTED_ERROR';
      }
    };

    const result = testMethodExtraction();
    
    // This test documents the vulnerability - unbound methods lose context
    expect(result).toBe('CONTEXT_BINDING_VULNERABILITY');
  });

  it('should verify logger constructor binding prevents the vulnerability', () => {
    // Test that proper constructor binding prevents the issue
    class ProperlyBoundLogger {
      constructor() {
        // Bind methods in constructor (like FrontendLogger does)
        this.log = this.log.bind(this);
      }

      log(message: string) {
        return this.internalLog(message);
      }

      private internalLog(message: string) {
        return `Bound logged: ${message}`;
      }
    }

    const boundLogger = new ProperlyBoundLogger();
    
    // Extract method (the pattern that would cause issues)
    const extractedLog = boundLogger.log;
    
    try {
      const result = extractedLog('test message');
      expect(result).toBe('Bound logged: test message');
    } catch (error) {
      fail('Constructor binding should prevent context loss');
    }
  });
});