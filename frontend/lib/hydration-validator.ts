/**
 * Hydration Validator
 *
 * Business Value Justification:
 * - Segment: All (Free, Early, Mid, Enterprise)
 * - Business Goal: User experience & platform reliability
 * - Value Impact: Prevents hydration mismatches that cause UI inconsistencies
 * - Strategic Impact: Ensures smooth client-side rendering and user experience
 *
 * Implements server/client state synchronization validation to prevent hydration errors.
 */

import { logger } from './logger';

interface HydrationState {
  timestamp: number;
  userAgent: string;
  environment: string;
  apiConfig: Record<string, unknown>;
  serverRendered: boolean;
  clientRendered: boolean;
}

interface ValidationResult {
  isValid: boolean;
  mismatches: string[];
  warnings: string[];
  serverState?: unknown;
  clientState?: unknown;
}

interface HydrationConfig {
  strictMode: boolean;
  allowedMismatches: string[];
  timeoutMs: number;
  retryAttempts: number;
}

export class HydrationValidator {
  private config: HydrationConfig;
  private serverState: Map<string, unknown> = new Map();
  private clientState: Map<string, unknown> = new Map();
  private validationResults: Map<string, ValidationResult> = new Map();
  
  constructor(config?: Partial<HydrationConfig>) {
    this.config = {
      strictMode: process.env.NODE_ENV === 'development',
      allowedMismatches: ['timestamp', 'random', 'clientId'],
      timeoutMs: 5000,
      retryAttempts: 3,
      ...config
    };
  }

  /**
   * Capture server-side state for hydration validation
   */
  captureServerState(key: string, state: unknown): void {
    try {
      // Only capture on server side
      if (typeof window === 'undefined') {
        const serializedState = this.serializeState(state);
        this.serverState.set(key, serializedState);
        
        // Store in global for client-side access
        if (typeof global !== 'undefined') {
          global.__HYDRATION_STATE__ = global.__HYDRATION_STATE__ || {};
          global.__HYDRATION_STATE__[key] = serializedState;
        }
        
        logger.debug(`Captured server state for ${key}`);
      }
    } catch (error) {
      logger.error(`Failed to capture server state for ${key}:`, error);
    }
  }

  /**
   * Capture client-side state for hydration validation
   */
  captureClientState(key: string, state: unknown): void {
    try {
      // Only capture on client side
      if (typeof window !== 'undefined') {
        const serializedState = this.serializeState(state);
        this.clientState.set(key, serializedState);
        
        logger.debug(`Captured client state for ${key}`);
      }
    } catch (error) {
      logger.error(`Failed to capture client state for ${key}:`, error);
    }
  }

  /**
   * Validate hydration for a specific state key
   */
  async validateHydration(key: string): Promise<ValidationResult> {
    try {
      let serverState = this.serverState.get(key);
      const clientState = this.clientState.get(key);

      // Try to get server state from global if not found
      if (!serverState && typeof window !== 'undefined') {
        const globalState = (window as Record<string, unknown> & { __HYDRATION_STATE__?: Record<string, unknown> }).__HYDRATION_STATE__;
        if (globalState && globalState[key]) {
          serverState = globalState[key];
          this.serverState.set(key, serverState);
        }
      }

      if (!serverState || !clientState) {
        const result: ValidationResult = {
          isValid: false,
          mismatches: ['Missing state data'],
          warnings: [],
          serverState,
          clientState
        };
        
        this.validationResults.set(key, result);
        return result;
      }

      const comparison = this.compareStates(serverState, clientState);
      const result: ValidationResult = {
        isValid: comparison.mismatches.length === 0,
        mismatches: comparison.mismatches,
        warnings: comparison.warnings,
        serverState,
        clientState
      };

      this.validationResults.set(key, result);

      if (!result.isValid && this.config.strictMode) {
        logger.error(`Hydration mismatch for ${key}:`, {
          mismatches: result.mismatches,
          serverState,
          clientState
        });
      } else if (result.warnings.length > 0) {
        logger.warn(`Hydration warnings for ${key}:`, result.warnings);
      }

      return result;

    } catch (error) {
      logger.error(`Hydration validation failed for ${key}:`, error);
      
      const result: ValidationResult = {
        isValid: false,
        mismatches: [`Validation error: ${error}`],
        warnings: []
      };
      
      this.validationResults.set(key, result);
      return result;
    }
  }

  /**
   * Validate all captured states
   */
  async validateAllStates(): Promise<Record<string, ValidationResult>> {
    const results: Record<string, ValidationResult> = {};
    
    const allKeys = new Set([
      ...this.serverState.keys(),
      ...this.clientState.keys()
    ]);

    for (const key of allKeys) {
      results[key] = await this.validateHydration(key);
    }

    return results;
  }

  /**
   * Compare server and client states
   */
  private compareStates(serverState: unknown, clientState: unknown): { mismatches: string[]; warnings: string[] } {
    const mismatches: string[] = [];
    const warnings: string[] = [];

    try {
      const serverObj = typeof serverState === 'string' ? JSON.parse(serverState) : serverState;
      const clientObj = typeof clientState === 'string' ? JSON.parse(clientState) : clientState;

      this.deepCompare('', serverObj, clientObj, mismatches, warnings);

    } catch (error) {
      mismatches.push(`State comparison error: ${error}`);
    }

    return { mismatches, warnings };
  }

  /**
   * Deep compare two objects and track differences
   */
  private deepCompare(
    path: string,
    serverValue: unknown,
    clientValue: unknown,
    mismatches: string[],
    warnings: string[]
  ): void {
    const fullPath = path || 'root';

    // Check if this path is in allowed mismatches
    const isAllowedMismatch = this.config.allowedMismatches.some(allowed => 
      fullPath.includes(allowed)
    );

    if (serverValue === null && clientValue === null) {
      return;
    }

    if (serverValue === null || clientValue === null) {
      if (isAllowedMismatch) {
        warnings.push(`${fullPath}: null mismatch (allowed)`);
      } else {
        mismatches.push(`${fullPath}: null mismatch - server: ${serverValue}, client: ${clientValue}`);
      }
      return;
    }

    const serverType = typeof serverValue;
    const clientType = typeof clientValue;

    if (serverType !== clientType) {
      if (isAllowedMismatch) {
        warnings.push(`${fullPath}: type mismatch (allowed) - server: ${serverType}, client: ${clientType}`);
      } else {
        mismatches.push(`${fullPath}: type mismatch - server: ${serverType}, client: ${clientType}`);
      }
      return;
    }

    if (serverType === 'object') {
      if (Array.isArray(serverValue) !== Array.isArray(clientValue)) {
        if (isAllowedMismatch) {
          warnings.push(`${fullPath}: array/object mismatch (allowed)`);
        } else {
          mismatches.push(`${fullPath}: array/object mismatch`);
        }
        return;
      }

      if (Array.isArray(serverValue)) {
        if (serverValue.length !== clientValue.length) {
          if (isAllowedMismatch) {
            warnings.push(`${fullPath}: array length mismatch (allowed) - server: ${serverValue.length}, client: ${clientValue.length}`);
          } else {
            mismatches.push(`${fullPath}: array length mismatch - server: ${serverValue.length}, client: ${clientValue.length}`);
          }
          return;
        }

        for (let i = 0; i < serverValue.length; i++) {
          this.deepCompare(`${fullPath}[${i}]`, serverValue[i], clientValue[i], mismatches, warnings);
        }
      } else {
        const serverKeys = Object.keys(serverValue).sort();
        const clientKeys = Object.keys(clientValue).sort();

        const missingInClient = serverKeys.filter(key => !clientKeys.includes(key));
        const missingInServer = clientKeys.filter(key => !serverKeys.includes(key));

        for (const key of missingInClient) {
          const keyPath = `${fullPath}.${key}`;
          if (this.config.allowedMismatches.some(allowed => keyPath.includes(allowed))) {
            warnings.push(`${keyPath}: missing in client (allowed)`);
          } else {
            mismatches.push(`${keyPath}: missing in client`);
          }
        }

        for (const key of missingInServer) {
          const keyPath = `${fullPath}.${key}`;
          if (this.config.allowedMismatches.some(allowed => keyPath.includes(allowed))) {
            warnings.push(`${keyPath}: missing in server (allowed)`);
          } else {
            mismatches.push(`${keyPath}: missing in server`);
          }
        }

        for (const key of serverKeys) {
          if (clientKeys.includes(key)) {
            this.deepCompare(`${fullPath}.${key}`, serverValue[key], clientValue[key], mismatches, warnings);
          }
        }
      }
    } else if (serverValue !== clientValue) {
      if (isAllowedMismatch) {
        warnings.push(`${fullPath}: value mismatch (allowed) - server: ${JSON.stringify(serverValue)}, client: ${JSON.stringify(clientValue)}`);
      } else {
        mismatches.push(`${fullPath}: value mismatch - server: ${JSON.stringify(serverValue)}, client: ${JSON.stringify(clientValue)}`);
      }
    }
  }

  /**
   * Serialize state for comparison
   */
  private serializeState(state: unknown): unknown {
    try {
      // Handle functions, dates, and other non-serializable items
      return JSON.parse(JSON.stringify(state, (key, value) => {
        if (typeof value === 'function') {
          return '[Function]';
        }
        if (value instanceof Date) {
          return value.toISOString();
        }
        if (value instanceof RegExp) {
          return value.toString();
        }
        return value;
      }));
    } catch (error) {
      logger.warn('Failed to serialize state:', error);
      return state;
    }
  }

  /**
   * Get validation statistics
   */
  getValidationStats() {
    const results = Array.from(this.validationResults.values());
    const totalValidations = results.length;
    const validValidations = results.filter(r => r.isValid).length;
    const invalidValidations = totalValidations - validValidations;

    const allMismatches = results.flatMap(r => r.mismatches);
    const allWarnings = results.flatMap(r => r.warnings);

    return {
      totalValidations,
      validValidations,
      invalidValidations,
      successRate: totalValidations > 0 ? (validValidations / totalValidations) * 100 : 0,
      totalMismatches: allMismatches.length,
      totalWarnings: allWarnings.length,
      commonMismatches: this.getCommonIssues(allMismatches),
      commonWarnings: this.getCommonIssues(allWarnings)
    };
  }

  /**
   * Get common issues from a list of issues
   */
  private getCommonIssues(issues: string[]): Record<string, number> {
    const counts: Record<string, number> = {};
    
    for (const issue of issues) {
      // Extract the path/type from the issue string
      const match = issue.match(/^([^:]+):/);
      if (match) {
        const issueType = match[1];
        counts[issueType] = (counts[issueType] || 0) + 1;
      }
    }

    return counts;
  }

  /**
   * Clear all captured state
   */
  clearState(): void {
    this.serverState.clear();
    this.clientState.clear();
    this.validationResults.clear();
    
    // Clear global state
    if (typeof window !== 'undefined') {
      delete (window as Record<string, unknown> & { __HYDRATION_STATE__?: Record<string, unknown> }).__HYDRATION_STATE__;
    }
    
    logger.debug('Hydration validator state cleared');
  }

  /**
   * Setup automatic hydration validation
   */
  setupAutoValidation(): void {
    if (typeof window !== 'undefined') {
      // Validate after hydration is complete
      const originalConsoleError = console.error;
      
      console.error = (...args) => {
        // Check for React hydration errors
        const errorString = args.join(' ');
        if (errorString.includes('Hydration') || errorString.includes('hydration')) {
          logger.error('React hydration error detected:', ...args);
          
          // Perform validation to get more details
          this.validateAllStates().then(results => {
            logger.error('Hydration validation results:', results);
          });
        }
        
        originalConsoleError.apply(console, args);
      };

      // Validate on page load
      if (document.readyState === 'complete') {
        setTimeout(() => this.performAutoValidation(), 100);
      } else {
        window.addEventListener('load', () => {
          setTimeout(() => this.performAutoValidation(), 100);
        });
      }
    }
  }

  /**
   * Perform automatic validation
   */
  private async performAutoValidation(): Promise<void> {
    try {
      const results = await this.validateAllStates();
      const stats = this.getValidationStats();
      
      if (stats.invalidValidations > 0) {
        logger.warn('Hydration validation completed with issues:', {
          stats,
          results
        });
      } else {
        logger.debug('Hydration validation completed successfully:', stats);
      }
    } catch (error) {
      logger.error('Auto-validation failed:', error);
    }
  }
}

// Global instance
let hydrationValidator: HydrationValidator | null = null;

export function getHydrationValidator(config?: Partial<HydrationConfig>): HydrationValidator {
  if (!hydrationValidator) {
    hydrationValidator = new HydrationValidator(config);
    
    // Setup automatic validation in development
    if (process.env.NODE_ENV === 'development') {
      hydrationValidator.setupAutoValidation();
    }
  }
  return hydrationValidator;
}

// Convenience functions
export function captureServerState(key: string, state: unknown): void {
  const validator = getHydrationValidator();
  validator.captureServerState(key, state);
}

export function captureClientState(key: string, state: unknown): void {
  const validator = getHydrationValidator();
  validator.captureClientState(key, state);
}

export async function validateHydration(key: string): Promise<ValidationResult> {
  const validator = getHydrationValidator();
  return validator.validateHydration(key);
}

export async function validateAllHydration(): Promise<Record<string, ValidationResult>> {
  const validator = getHydrationValidator();
  return validator.validateAllStates();
}

export default HydrationValidator;