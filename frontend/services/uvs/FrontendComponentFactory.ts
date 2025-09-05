/**
 * Frontend Component Factory - SSOT for user isolation
 * 
 * CRITICAL: Implements factory pattern for complete user isolation
 * per USER_CONTEXT_ARCHITECTURE.md and CLAUDE.md requirements.
 * 
 * Business Value: Multi-user support with zero cross-contamination
 */

import { ConversationManager } from './ConversationManager';
import { WebSocketBridgeClient } from './WebSocketBridgeClient';
import { StateRecoveryManager } from './StateRecoveryManager';
import { logger } from '@/lib/logger';

interface ComponentInstance<T> {
  instance: T;
  userId: string;
  createdAt: number;
  lastAccessed: number;
}

interface FactoryConfig {
  maxInstanceAge?: number;  // Max age in ms before cleanup (default: 30 minutes)
  cleanupInterval?: number; // Cleanup check interval (default: 5 minutes)
  maxInstancesPerUser?: number; // Max instances per user (default: 1)
}

/**
 * SSOT: Frontend component factory for user isolation
 * Ensures each user has completely isolated component instances
 */
export class FrontendComponentFactory {
  private static conversationManagers = new Map<string, ComponentInstance<ConversationManager>>();
  private static webSocketClients = new Map<string, ComponentInstance<WebSocketBridgeClient>>();
  private static recoveryManagers = new Map<string, ComponentInstance<StateRecoveryManager>>();
  
  private static cleanupTimer: NodeJS.Timeout | null = null;
  private static config: FactoryConfig = {
    maxInstanceAge: 30 * 60 * 1000, // 30 minutes
    cleanupInterval: 5 * 60 * 1000,  // 5 minutes
    maxInstancesPerUser: 1
  };
  
  private static initialized = false;

  /**
   * Initialize factory with automatic cleanup
   */
  static initialize(config?: Partial<FactoryConfig>): void {
    if (this.initialized) {
      logger.warn('🚨 FrontendComponentFactory already initialized - idempotent call ignored');
      return;
    }
    
    this.config = { ...this.config, ...config };
    
    // Start cleanup timer
    this.startCleanupTimer();
    this.initialized = true;
    
    logger.info('✅ FrontendComponentFactory initialized', {
      maxInstanceAge: this.config.maxInstanceAge,
      cleanupInterval: this.config.cleanupInterval
    });
    
    // Register cleanup on page unload
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => this.cleanup());
    }
  }
  
  /**
   * Get or create ConversationManager for user
   * CRITICAL: Ensures complete isolation per user
   */
  static getConversationManager(userId: string): ConversationManager {
    const key = `conv_${userId}`;
    
    // Check existing instance
    const existing = this.conversationManagers.get(key);
    if (existing) {
      existing.lastAccessed = Date.now();
      logger.debug('Reusing ConversationManager', { userId });
      return existing.instance;
    }
    
    // Create new isolated instance
    logger.info('Creating new ConversationManager', { userId });
    const instance = new ConversationManager(userId);
    
    this.conversationManagers.set(key, {
      instance,
      userId,
      createdAt: Date.now(),
      lastAccessed: Date.now()
    });
    
    // Enforce max instances per user
    this.enforceMaxInstances(this.conversationManagers, userId);
    
    return instance;
  }
  
  /**
   * Get or create WebSocketBridgeClient for user
   */
  static getWebSocketClient(userId: string): WebSocketBridgeClient {
    const key = `ws_${userId}`;
    
    const existing = this.webSocketClients.get(key);
    if (existing) {
      existing.lastAccessed = Date.now();
      logger.debug('Reusing WebSocketBridgeClient', { userId });
      return existing.instance;
    }
    
    logger.info('Creating new WebSocketBridgeClient', { userId });
    const instance = new WebSocketBridgeClient(userId);
    
    this.webSocketClients.set(key, {
      instance,
      userId,
      createdAt: Date.now(),
      lastAccessed: Date.now()
    });
    
    this.enforceMaxInstances(this.webSocketClients, userId);
    
    return instance;
  }
  
  /**
   * Get or create StateRecoveryManager for user
   */
  static getStateRecoveryManager(userId: string): StateRecoveryManager {
    const key = `recovery_${userId}`;
    
    const existing = this.recoveryManagers.get(key);
    if (existing) {
      existing.lastAccessed = Date.now();
      logger.debug('Reusing StateRecoveryManager', { userId });
      return existing.instance;
    }
    
    logger.info('Creating new StateRecoveryManager', { userId });
    const instance = new StateRecoveryManager(userId);
    
    this.recoveryManagers.set(key, {
      instance,
      userId,
      createdAt: Date.now(),
      lastAccessed: Date.now()
    });
    
    this.enforceMaxInstances(this.recoveryManagers, userId);
    
    return instance;
  }
  
  /**
   * Clean up resources for specific user
   */
  static cleanupUser(userId: string): void {
    logger.info('Cleaning up user resources', { userId });
    
    // Cleanup conversation manager
    const convKey = `conv_${userId}`;
    const convManager = this.conversationManagers.get(convKey);
    if (convManager) {
      convManager.instance.dispose();
      this.conversationManagers.delete(convKey);
    }
    
    // Cleanup WebSocket client
    const wsKey = `ws_${userId}`;
    const wsClient = this.webSocketClients.get(wsKey);
    if (wsClient) {
      wsClient.instance.dispose();
      this.webSocketClients.delete(wsKey);
    }
    
    // Cleanup recovery manager
    const recoveryKey = `recovery_${userId}`;
    const recoveryManager = this.recoveryManagers.get(recoveryKey);
    if (recoveryManager) {
      recoveryManager.instance.dispose();
      this.recoveryManagers.delete(recoveryKey);
    }
    
    logger.info('✅ User resources cleaned up', { userId });
  }
  
  /**
   * Clean up all resources
   */
  static cleanup(): void {
    logger.info('🔄 Cleaning up all factory resources');
    
    // Stop cleanup timer
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
    
    // Cleanup all conversation managers
    for (const [key, instance] of this.conversationManagers) {
      instance.instance.dispose();
    }
    this.conversationManagers.clear();
    
    // Cleanup all WebSocket clients
    for (const [key, instance] of this.webSocketClients) {
      instance.instance.dispose();
    }
    this.webSocketClients.clear();
    
    // Cleanup all recovery managers
    for (const [key, instance] of this.recoveryManagers) {
      instance.instance.dispose();
    }
    this.recoveryManagers.clear();
    
    this.initialized = false;
    logger.info('✅ All factory resources cleaned up');
  }
  
  /**
   * Get current factory stats
   */
  static getStats() {
    return {
      conversationManagers: this.conversationManagers.size,
      webSocketClients: this.webSocketClients.size,
      recoveryManagers: this.recoveryManagers.size,
      totalInstances: this.conversationManagers.size + 
                     this.webSocketClients.size + 
                     this.recoveryManagers.size
    };
  }
  
  /**
   * Start automatic cleanup timer
   */
  private static startCleanupTimer(): void {
    this.cleanupTimer = setInterval(() => {
      this.performCleanup();
    }, this.config.cleanupInterval!);
  }
  
  /**
   * Perform cleanup of stale instances
   */
  private static performCleanup(): void {
    const now = Date.now();
    const maxAge = this.config.maxInstanceAge!;
    let cleanedCount = 0;
    
    // Cleanup old conversation managers
    for (const [key, instance] of this.conversationManagers) {
      if (now - instance.lastAccessed > maxAge) {
        instance.instance.dispose();
        this.conversationManagers.delete(key);
        cleanedCount++;
      }
    }
    
    // Cleanup old WebSocket clients
    for (const [key, instance] of this.webSocketClients) {
      if (now - instance.lastAccessed > maxAge) {
        instance.instance.dispose();
        this.webSocketClients.delete(key);
        cleanedCount++;
      }
    }
    
    // Cleanup old recovery managers
    for (const [key, instance] of this.recoveryManagers) {
      if (now - instance.lastAccessed > maxAge) {
        instance.instance.dispose();
        this.recoveryManagers.delete(key);
        cleanedCount++;
      }
    }
    
    if (cleanedCount > 0) {
      logger.info('Cleaned up stale instances', { cleanedCount });
    }
  }
  
  /**
   * Enforce max instances per user
   */
  private static enforceMaxInstances<T>(
    map: Map<string, ComponentInstance<T>>,
    userId: string
  ): void {
    const userInstances: Array<[string, ComponentInstance<T>]> = [];
    
    // Find all instances for this user
    for (const [key, instance] of map) {
      if (instance.userId === userId) {
        userInstances.push([key, instance]);
      }
    }
    
    // If exceeding max, remove oldest
    if (userInstances.length > this.config.maxInstancesPerUser!) {
      userInstances.sort((a, b) => a[1].createdAt - b[1].createdAt);
      const toRemove = userInstances.slice(0, userInstances.length - this.config.maxInstancesPerUser!);
      
      for (const [key, instance] of toRemove) {
        if ('dispose' in instance.instance && typeof (instance.instance as any).dispose === 'function') {
          (instance.instance as any).dispose();
        }
        map.delete(key);
        logger.warn('🚨 Removed excess instance for user', { userId, key });
      }
    }
  }
}

// Auto-initialize on import if in browser
if (typeof window !== 'undefined') {
  FrontendComponentFactory.initialize();
}