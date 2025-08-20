/**
 * Optimistic Updates Service - Ultra-fast message rendering system
 * 
 * Provides instant user feedback with < 16ms response times for message sending.
 * Handles reconciliation, failure recovery, and progressive loading states.
 * 
 * BUSINESS VALUE JUSTIFICATION (BVJ):
 * - Segment: Growth & Enterprise
 * - Goal: Improve UX to increase engagement and retention
 * - Impact: 5-10% retention increase through better perceived performance
 */

import { generateUniqueId } from '@/lib/utils';
import type { ChatMessage, MessageRole } from '@/types/registry';
import { logger } from '@/utils/debug-logger';

// ============================================================================
// Core Types and Interfaces
// ============================================================================

export interface OptimisticMessage extends ChatMessage {
  isOptimistic: true;
  status: OptimisticStatus;
  localId: string;
  retry?: () => Promise<void>;
}

export type OptimisticStatus = 
  | 'pending'    // User message sent, waiting for backend
  | 'processing' // AI response generation in progress
  | 'confirmed'  // Backend confirmed message
  | 'failed'     // Send/receive failed
  | 'retrying';  // Attempting retry

export interface OptimisticState {
  messages: Map<string, OptimisticMessage>;
  pendingUserMessage?: OptimisticMessage;
  pendingAiMessage?: OptimisticMessage;
  retryQueue: string[];
}

export interface ReconciliationResult {
  confirmed: OptimisticMessage[];
  failed: OptimisticMessage[];
  updated: OptimisticMessage[];
}

// ============================================================================
// OptimisticMessageManager - Core Class
// ============================================================================

export class OptimisticMessageManager {
  private state: OptimisticState;
  private callbacks: Set<(state: OptimisticState) => void>;
  private retryAttempts: Map<string, number>;
  private maxRetries = 3;

  constructor() {
    this.state = this.createInitialState();
    this.callbacks = new Set();
    this.retryAttempts = new Map();
  }

  // ========================================================================
  // State Management (25-line functions)
  // ========================================================================

  private createInitialState(): OptimisticState {
    return {
      messages: new Map(),
      pendingUserMessage: undefined,
      pendingAiMessage: undefined,
      retryQueue: []
    };
  }

  subscribe(callback: (state: OptimisticState) => void): () => void {
    this.callbacks.add(callback);
    return () => this.callbacks.delete(callback);
  }

  private notifySubscribers(): void {
    this.callbacks.forEach(callback => {
      try {
        callback(this.state);
      } catch (error) {
        logger.error('OptimisticMessageManager callback error:', error);
      }
    });
  }

  // ========================================================================
  // Optimistic Message Creation (25-line functions)
  // ========================================================================

  createOptimisticUserMessage(content: string, threadId?: string): OptimisticMessage {
    const localId = generateUniqueId('opt-user');
    const id = generateUniqueId('msg');
    const timestamp = Date.now();
    
    return this.createOptimisticMessage({
      id, content, role: 'user', timestamp, threadId
    }, localId, 'pending');
  }

  createOptimisticAiMessage(threadId?: string): OptimisticMessage {
    const localId = generateUniqueId('opt-ai');
    const id = generateUniqueId('msg');
    const timestamp = Date.now();
    
    return this.createOptimisticMessage({
      id, content: '', role: 'assistant', timestamp, threadId
    }, localId, 'processing');
  }

  private createOptimisticMessage(
    base: Partial<ChatMessage>, 
    localId: string, 
    status: OptimisticStatus
  ): OptimisticMessage {
    return {
      ...base,
      id: base.id || generateUniqueId('msg'),
      content: base.content || '',
      role: base.role || 'user',
      timestamp: base.timestamp || Date.now(),
      isOptimistic: true,
      status,
      localId
    } as OptimisticMessage;
  }

  // ========================================================================
  // Message Lifecycle Management (25-line functions)
  // ========================================================================

  addOptimisticUserMessage(content: string, threadId?: string): OptimisticMessage {
    const message = this.createOptimisticUserMessage(content, threadId);
    this.state.messages.set(message.localId, message);
    this.state.pendingUserMessage = message;
    this.notifySubscribers();
    return message;
  }

  addOptimisticAiMessage(threadId?: string): OptimisticMessage {
    const message = this.createOptimisticAiMessage(threadId);
    this.state.messages.set(message.localId, message);
    this.state.pendingAiMessage = message;
    this.notifySubscribers();
    return message;
  }

  updateOptimisticMessage(
    localId: string, 
    updates: Partial<OptimisticMessage>
  ): void {
    const message = this.state.messages.get(localId);
    if (!message) return;
    
    const updated = { ...message, ...updates };
    this.state.messages.set(localId, updated);
    this.updatePendingReferences(localId, updated);
    this.notifySubscribers();
  }

  private updatePendingReferences(localId: string, message: OptimisticMessage): void {
    if (this.state.pendingUserMessage?.localId === localId) {
      this.state.pendingUserMessage = message;
    }
    if (this.state.pendingAiMessage?.localId === localId) {
      this.state.pendingAiMessage = message;
    }
  }

  // ========================================================================
  // Backend Reconciliation (25-line functions)
  // ========================================================================

  reconcileWithBackend(backendMessages: ChatMessage[]): ReconciliationResult {
    const result: ReconciliationResult = {
      confirmed: [],
      failed: [],
      updated: []
    };
    
    this.processReconciliation(backendMessages, result);
    this.cleanupConfirmedMessages(result.confirmed);
    this.notifySubscribers();
    return result;
  }

  private processReconciliation(
    backendMessages: ChatMessage[], 
    result: ReconciliationResult
  ): void {
    for (const [localId, optimisticMsg] of this.state.messages) {
      const backendMatch = this.findBackendMatch(optimisticMsg, backendMessages);
      
      if (backendMatch) {
        this.confirmOptimisticMessage(optimisticMsg, backendMatch, result);
      } else if (this.shouldMarkAsFailed(optimisticMsg)) {
        this.markMessageFailed(optimisticMsg, result);
      }
    }
  }

  private findBackendMatch(
    optimistic: OptimisticMessage, 
    backendMessages: ChatMessage[]
  ): ChatMessage | undefined {
    return backendMessages.find(msg => 
      msg.content === optimistic.content && 
      msg.role === optimistic.role &&
      Math.abs((msg.timestamp || 0) - (optimistic.timestamp || 0)) < 5000
    );
  }

  private confirmOptimisticMessage(
    optimistic: OptimisticMessage,
    backend: ChatMessage,
    result: ReconciliationResult
  ): void {
    const confirmed = { ...optimistic, ...backend, status: 'confirmed' as const };
    result.confirmed.push(confirmed);
    this.state.messages.set(optimistic.localId, confirmed);
  }

  private shouldMarkAsFailed(message: OptimisticMessage): boolean {
    const ageMs = Date.now() - (message.timestamp || 0);
    const isOld = ageMs > 30000; // 30 seconds
    const isPending = message.status === 'pending';
    return isOld && isPending;
  }

  private markMessageFailed(
    message: OptimisticMessage,
    result: ReconciliationResult
  ): void {
    const failed = { ...message, status: 'failed' as const };
    result.failed.push(failed);
    this.state.messages.set(message.localId, failed);
    this.state.retryQueue.push(message.localId);
  }

  private cleanupConfirmedMessages(confirmed: OptimisticMessage[]): void {
    confirmed.forEach(msg => {
      if (this.state.pendingUserMessage?.localId === msg.localId) {
        this.state.pendingUserMessage = undefined;
      }
      if (this.state.pendingAiMessage?.localId === msg.localId) {
        this.state.pendingAiMessage = undefined;
      }
    });
  }

  // ========================================================================
  // Failure Handling and Retry (25-line functions)
  // ========================================================================

  retryMessage(localId: string): Promise<void> {
    const message = this.state.messages.get(localId);
    if (!message || message.status !== 'failed') return Promise.resolve();
    
    const attempts = this.retryAttempts.get(localId) || 0;
    if (attempts >= this.maxRetries) return Promise.reject('Max retries exceeded');
    
    return this.executeRetry(message, attempts);
  }

  private async executeRetry(message: OptimisticMessage, attempts: number): Promise<void> {
    this.updateOptimisticMessage(message.localId, { status: 'retrying' });
    this.retryAttempts.set(message.localId, attempts + 1);
    
    try {
      await this.performRetryLogic(message);
      this.updateOptimisticMessage(message.localId, { status: 'pending' });
    } catch (error) {
      this.updateOptimisticMessage(message.localId, { status: 'failed' });
      throw error;
    }
  }

  private async performRetryLogic(message: OptimisticMessage): Promise<void> {
    // Retry logic will be implemented by the calling component
    // This provides the hook for the actual retry mechanism
    if (message.retry) {
      await message.retry();
    }
  }

  // ========================================================================
  // Utility Methods (25-line functions)
  // ========================================================================

  getOptimisticMessages(): OptimisticMessage[] {
    return Array.from(this.state.messages.values())
      .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
  }

  getPendingMessages(): OptimisticMessage[] {
    return this.getOptimisticMessages()
      .filter(msg => msg.status === 'pending' || msg.status === 'processing');
  }

  getFailedMessages(): OptimisticMessage[] {
    return this.getOptimisticMessages()
      .filter(msg => msg.status === 'failed');
  }

  clearAllOptimisticMessages(): void {
    this.state.messages.clear();
    this.state.pendingUserMessage = undefined;
    this.state.pendingAiMessage = undefined;
    this.state.retryQueue = [];
    this.retryAttempts.clear();
    this.notifySubscribers();
  }

  getState(): OptimisticState {
    return { ...this.state };
  }
}

// ============================================================================
// Singleton Instance Export
// ============================================================================

export const optimisticMessageManager = new OptimisticMessageManager();