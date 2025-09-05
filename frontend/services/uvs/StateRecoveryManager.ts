/**
 * State Recovery Manager - Handles state persistence and validation
 * 
 * CRITICAL: Implements state recovery with validation and corruption detection
 * per CLAUDE.md requirements for resilient state management.
 * 
 * Business Value: Ensures conversation continuity across sessions/disconnects
 */

import { logger } from '@/lib/logger';

interface StateValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

interface RecoveryStrategy {
  name: string;
  priority: number;
  execute: () => Promise<any | null>;
}

/**
 * State validator for ensuring state integrity
 */
class StateValidator {
  /**
   * Validate state object
   */
  validate(state: any): StateValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];
    
    // Check basic structure
    if (!state || typeof state !== 'object') {
      errors.push('State is not an object');
      return { isValid: false, errors, warnings };
    }
    
    // Check required fields
    if (!Array.isArray(state.messages)) {
      errors.push('State.messages is not an array');
    }
    
    if (typeof state.isProcessing !== 'boolean') {
      warnings.push('State.isProcessing is not a boolean');
    }
    
    if (typeof state.lastActivity !== 'number') {
      warnings.push('State.lastActivity is not a number');
    }
    
    // Validate messages
    if (Array.isArray(state.messages)) {
      for (let i = 0; i < state.messages.length; i++) {
        const msg = state.messages[i];
        
        if (!msg.id) {
          errors.push(`Message ${i} missing id`);
        }
        
        if (!msg.text && msg.text !== '') {
          warnings.push(`Message ${i} missing text`);
        }
        
        if (!msg.role || !['user', 'assistant', 'system'].includes(msg.role)) {
          errors.push(`Message ${i} has invalid role: ${msg.role}`);
        }
        
        if (typeof msg.timestamp !== 'number') {
          warnings.push(`Message ${i} has invalid timestamp`);
        }
      }
    }
    
    // Check for state corruption indicators
    if (state.messages && state.messages.length > 10000) {
      errors.push('Excessive message count indicates possible corruption');
    }
    
    if (state.lastActivity && state.lastActivity > Date.now() + 86400000) {
      errors.push('Future timestamp detected - possible corruption');
    }
    
    const isValid = errors.length === 0;
    
    if (!isValid) {
      logger.error('🚨 State validation failed', { errors, warnings });
    } else if (warnings.length > 0) {
      logger.warn('State validation warnings', { warnings });
    }
    
    return { isValid, errors, warnings };
  }
  
  /**
   * Sanitize state to fix common issues
   */
  sanitize(state: any): any {
    if (!state || typeof state !== 'object') {
      return null;
    }
    
    const sanitized = { ...state };
    
    // Ensure messages array exists
    if (!Array.isArray(sanitized.messages)) {
      sanitized.messages = [];
    }
    
    // Filter out invalid messages
    sanitized.messages = sanitized.messages.filter((msg: any) => 
      msg && msg.id && msg.text !== undefined && msg.role
    );
    
    // Fix timestamps
    const now = Date.now();
    sanitized.messages = sanitized.messages.map((msg: any) => ({
      ...msg,
      timestamp: typeof msg.timestamp === 'number' && msg.timestamp <= now 
        ? msg.timestamp 
        : now
    }));
    
    // Ensure required fields
    sanitized.isProcessing = sanitized.isProcessing === true;
    sanitized.lastActivity = typeof sanitized.lastActivity === 'number' 
      ? Math.min(sanitized.lastActivity, now) 
      : now;
    
    return sanitized;
  }
}

/**
 * State Recovery Manager - Main class
 */
export class StateRecoveryManager {
  private userId: string;
  private storageKey: string;
  private validator: StateValidator;
  private lastKnownGoodState: any = null;
  private disposed = false;
  
  // Configuration
  private readonly STATE_VERSION = 1;
  private readonly MAX_STATE_SIZE = 1024 * 1024; // 1MB limit
  private readonly COMPRESSION_THRESHOLD = 10 * 1024; // Compress if > 10KB
  
  constructor(userId: string) {
    this.userId = userId;
    this.storageKey = `netra_uvs_state_${userId}`;
    this.validator = new StateValidator();
    
    logger.info('StateRecoveryManager created', { userId });
  }
  
  /**
   * Save state to storage
   */
  async saveState(state: any): Promise<void> {
    if (this.disposed) {
      return;
    }
    
    try {
      // Validate before saving
      const validation = this.validator.validate(state);
      if (!validation.isValid) {
        logger.error('🚨 Cannot save invalid state', { 
          errors: validation.errors 
        });
        return;
      }
      
      // Create versioned state
      const versionedState = {
        version: this.STATE_VERSION,
        userId: this.userId,
        state,
        savedAt: Date.now()
      };
      
      // Check size
      const serialized = JSON.stringify(versionedState);
      if (serialized.length > this.MAX_STATE_SIZE) {
        logger.error('🚨 State too large to save', { 
          size: serialized.length 
        });
        return;
      }
      
      // Save to localStorage
      if (typeof window !== 'undefined' && window.localStorage) {
        // Compress if needed
        const toSave = serialized.length > this.COMPRESSION_THRESHOLD
          ? await this.compress(serialized)
          : serialized;
        
        localStorage.setItem(this.storageKey, toSave);
        
        // Update last known good state
        this.lastKnownGoodState = structuredClone(state);
        
        logger.debug('State saved', { 
          size: toSave.length,
          compressed: toSave !== serialized 
        });
      }
      
      // Also save to sessionStorage as backup
      if (typeof window !== 'undefined' && window.sessionStorage) {
        try {
          sessionStorage.setItem(this.storageKey + '_backup', serialized);
        } catch (e) {
          // SessionStorage might be full, ignore
        }
      }
      
    } catch (error) {
      logger.error('🚨 Failed to save state', { error });
    }
  }
  
  /**
   * Recover state from storage
   */
  async recoverState(): Promise<any | null> {
    if (this.disposed) {
      return null;
    }
    
    const strategies: RecoveryStrategy[] = [
      {
        name: 'localStorage',
        priority: 1,
        execute: () => this.recoverFromLocalStorage()
      },
      {
        name: 'sessionStorage',
        priority: 2,
        execute: () => this.recoverFromSessionStorage()
      },
      {
        name: 'server',
        priority: 3,
        execute: () => this.recoverFromServer()
      },
      {
        name: 'lastKnownGood',
        priority: 4,
        execute: () => this.useLastKnownGood()
      }
    ];
    
    // Sort by priority
    strategies.sort((a, b) => a.priority - b.priority);
    
    // Try each strategy
    for (const strategy of strategies) {
      try {
        logger.info(`Attempting recovery strategy: ${strategy.name}`);
        const recovered = await strategy.execute();
        
        if (recovered) {
          // Validate recovered state
          const validation = this.validator.validate(recovered);
          
          if (validation.isValid) {
            logger.info(`✅ State recovered using ${strategy.name}`);
            return recovered;
          } else {
            // Try to sanitize
            const sanitized = this.validator.sanitize(recovered);
            const revalidation = this.validator.validate(sanitized);
            
            if (revalidation.isValid) {
              logger.warn(`State sanitized and recovered using ${strategy.name}`);
              return sanitized;
            }
          }
        }
      } catch (error) {
        logger.error(`🚨 Recovery strategy ${strategy.name} failed`, { error });
      }
    }
    
    // All strategies failed - return fresh state
    logger.warn('All recovery strategies failed, using fresh state');
    return this.createFreshState();
  }
  
  /**
   * Recover from localStorage
   */
  private async recoverFromLocalStorage(): Promise<any | null> {
    if (typeof window === 'undefined' || !window.localStorage) {
      return null;
    }
    
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (!stored) {
        return null;
      }
      
      // Check if compressed
      let parsed;
      if (stored.startsWith('{')) {
        parsed = JSON.parse(stored);
      } else {
        const decompressed = await this.decompress(stored);
        parsed = JSON.parse(decompressed);
      }
      
      // Check version
      if (parsed.version !== this.STATE_VERSION) {
        logger.warn('State version mismatch', { 
          expected: this.STATE_VERSION,
          found: parsed.version 
        });
        return null;
      }
      
      // Check user ID
      if (parsed.userId !== this.userId) {
        logger.error('🚨 User ID mismatch in stored state');
        return null;
      }
      
      // Check age (discard if > 24 hours old)
      const age = Date.now() - parsed.savedAt;
      if (age > 24 * 60 * 60 * 1000) {
        logger.warn('State too old, discarding', { 
          ageHours: Math.floor(age / (60 * 60 * 1000)) 
        });
        return null;
      }
      
      return parsed.state;
      
    } catch (error) {
      logger.error('🚨 Failed to recover from localStorage', { error });
      return null;
    }
  }
  
  /**
   * Recover from sessionStorage
   */
  private async recoverFromSessionStorage(): Promise<any | null> {
    if (typeof window === 'undefined' || !window.sessionStorage) {
      return null;
    }
    
    try {
      const stored = sessionStorage.getItem(this.storageKey + '_backup');
      if (!stored) {
        return null;
      }
      
      const parsed = JSON.parse(stored);
      return parsed.state;
      
    } catch (error) {
      logger.error('🚨 Failed to recover from sessionStorage', { error });
      return null;
    }
  }
  
  /**
   * Recover from server
   */
  private async recoverFromServer(): Promise<any | null> {
    try {
      // TODO: Implement server-side state recovery
      // This would make an API call to retrieve state from backend
      logger.info('Server recovery not yet implemented');
      return null;
    } catch (error) {
      logger.error('🚨 Failed to recover from server', { error });
      return null;
    }
  }
  
  /**
   * Use last known good state
   */
  private useLastKnownGood(): any | null {
    if (this.lastKnownGoodState) {
      logger.info('Using last known good state');
      return structuredClone(this.lastKnownGoodState);
    }
    return null;
  }
  
  /**
   * Create fresh state
   */
  private createFreshState(): any {
    return {
      threadId: null,
      messages: [],
      currentAgentRunId: null,
      isProcessing: false,
      lastActivity: Date.now()
    };
  }
  
  /**
   * Clear stored state
   */
  clearState(): void {
    if (typeof window !== 'undefined') {
      if (window.localStorage) {
        localStorage.removeItem(this.storageKey);
      }
      if (window.sessionStorage) {
        sessionStorage.removeItem(this.storageKey + '_backup');
      }
    }
    
    this.lastKnownGoodState = null;
    logger.info('State cleared');
  }
  
  /**
   * Compress data (simple base64 encoding for now)
   */
  private async compress(data: string): Promise<string> {
    // In production, use proper compression library
    // For now, just use base64 encoding
    if (typeof btoa !== 'undefined') {
      return 'compressed:' + btoa(data);
    }
    return data;
  }
  
  /**
   * Decompress data
   */
  private async decompress(data: string): Promise<string> {
    if (data.startsWith('compressed:')) {
      const compressed = data.substring('compressed:'.length);
      if (typeof atob !== 'undefined') {
        return atob(compressed);
      }
    }
    return data;
  }
  
  /**
   * Dispose and cleanup
   */
  dispose(): void {
    if (this.disposed) {
      return;
    }
    
    logger.info('Disposing StateRecoveryManager', { userId: this.userId });
    
    // Save current state one last time
    if (this.lastKnownGoodState) {
      this.saveState(this.lastKnownGoodState);
    }
    
    this.disposed = true;
    
    logger.info('✅ StateRecoveryManager disposed', { userId: this.userId });
  }
}