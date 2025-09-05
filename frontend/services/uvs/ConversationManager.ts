/**
 * Conversation Manager - Handles multiturn conversations with queueing
 * 
 * CRITICAL: Implements race condition prevention and message queueing
 * per CLAUDE.md requirements for reliable multi-user conversations.
 * 
 * Business Value: Ensures reliable conversation flow for substantive chat value
 */

import { logger } from '@/lib/logger';
import { WebSocketBridgeClient } from './WebSocketBridgeClient';
import { StateRecoveryManager } from './StateRecoveryManager';
import { FrontendComponentFactory } from './FrontendComponentFactory';

export interface Message {
  id: string;
  text: string;
  timestamp: number;
  role: 'user' | 'assistant' | 'system';
  status: 'pending' | 'sending' | 'sent' | 'failed' | 'received';
  retryCount?: number;
  metadata?: Record<string, any>;
}

export interface ConversationState {
  threadId: string | null;
  messages: Message[];
  currentAgentRunId: string | null;
  isProcessing: boolean;
  lastActivity: number;
  uvsContext?: UVSContext;
}

export interface UVSContext {
  reportType: 'full' | 'partial' | 'guidance' | 'fallback';
  hasData: boolean;
  hasOptimizations: boolean;
  triageResult?: any;
  dataResult?: any;
  optimizationsResult?: any;
  explorationQuestions?: string[];
  nextSteps?: string[];
}

interface MessageQueueItem {
  message: Message;
  addedAt: number;
  attempts: number;
}

/**
 * Conversation Manager - Main class
 * Handles message queueing, race conditions, and state management
 */
export class ConversationManager {
  private userId: string;
  private state: ConversationState;
  private messageQueue: MessageQueueItem[] = [];
  private isProcessing = false;
  private processingPromise: Promise<void> | null = null;
  private wsClient: WebSocketBridgeClient;
  private recoveryManager: StateRecoveryManager;
  private disposed = false;
  
  // Configuration
  private readonly MAX_RETRY_ATTEMPTS = 3;
  private readonly MESSAGE_TIMEOUT = 30000; // 30 seconds
  private readonly QUEUE_PROCESS_INTERVAL = 100; // Process queue every 100ms
  
  // AbortController for cancellable operations
  private currentAbortController: AbortController | null = null;
  
  // Event handlers
  private stateChangeHandlers = new Set<(state: ConversationState) => void>();
  
  constructor(userId: string) {
    this.userId = userId;
    
    // Initialize state
    this.state = {
      threadId: null,
      messages: [],
      currentAgentRunId: null,
      isProcessing: false,
      lastActivity: Date.now()
    };
    
    // Get components from factory
    this.wsClient = FrontendComponentFactory.getWebSocketClient(userId);
    this.recoveryManager = FrontendComponentFactory.getStateRecoveryManager(userId);
    
    // Setup WebSocket event handlers
    this.setupEventHandlers();
    
    // Recover state if available
    this.recoverState();
    
    // Start queue processor
    this.startQueueProcessor();
    
    logger.info('ConversationManager created', { userId });
  }
  
  /**
   * Send a message (with queuing and race condition prevention)
   */
  async sendMessage(text: string): Promise<void> {
    if (this.disposed) {
      throw new Error('ConversationManager is disposed');
    }
    
    // Create message
    const message: Message = {
      id: this.generateMessageId(),
      text,
      timestamp: Date.now(),
      role: 'user',
      status: 'pending',
      retryCount: 0
    };
    
    // Add to state immediately (optimistic update)
    this.addMessageToState(message);
    
    // Queue the message
    this.messageQueue.push({
      message,
      addedAt: Date.now(),
      attempts: 0
    });
    
    logger.info('Message queued', { 
      messageId: message.id,
      queueLength: this.messageQueue.length 
    });
    
    // Process queue if not already processing
    if (!this.isProcessing) {
      await this.processMessageQueue();
    }
  }
  
  /**
   * Process message queue (prevents race conditions)
   */
  private async processMessageQueue(): Promise<void> {
    // Prevent concurrent processing
    if (this.isProcessing) {
      logger.debug('Already processing queue');
      return;
    }
    
    // Use promise to track processing state
    if (this.processingPromise) {
      return this.processingPromise;
    }
    
    this.processingPromise = this.doProcessQueue();
    
    try {
      await this.processingPromise;
    } finally {
      this.processingPromise = null;
    }
  }
  
  private async doProcessQueue(): Promise<void> {
    this.isProcessing = true;
    this.updateState({ isProcessing: true });
    
    try {
      while (this.messageQueue.length > 0 && !this.disposed) {
        const item = this.messageQueue[0]; // Peek first item
        
        try {
          // Update message status
          this.updateMessageStatus(item.message.id, 'sending');
          
          // Create abort controller for this message
          this.currentAbortController = new AbortController();
          
          // Send with timeout
          const sendPromise = this.wsClient.sendUserMessage(
            item.message.text,
            this.state.threadId || undefined
          );
          
          const timeoutPromise = new Promise<never>((_, reject) => {
            setTimeout(() => reject(new Error('Message timeout')), this.MESSAGE_TIMEOUT);
          });
          
          // Race between send and timeout
          await Promise.race([sendPromise, timeoutPromise]);
          
          // Success - remove from queue and update status
          this.messageQueue.shift();
          this.updateMessageStatus(item.message.id, 'sent');
          
          logger.info('Message sent successfully', { 
            messageId: item.message.id 
          });
          
          // Wait for response before processing next
          await this.waitForResponse(item.message.id);
          
        } catch (error) {
          logger.error('🚨 Message send failed', { 
            messageId: item.message.id,
            error,
            attempts: item.attempts 
          });
          
          item.attempts++;
          
          if (item.attempts >= this.MAX_RETRY_ATTEMPTS) {
            // Max retries reached - remove from queue and mark as failed
            this.messageQueue.shift();
            this.updateMessageStatus(item.message.id, 'failed');
            logger.error('🚨 Message failed after max retries', { 
              messageId: item.message.id 
            });
          } else {
            // Move to back of queue for retry
            this.messageQueue.shift();
            this.messageQueue.push(item);
            
            // Add delay before retry
            await this.delay(1000 * item.attempts);
          }
        } finally {
          this.currentAbortController = null;
        }
      }
    } finally {
      this.isProcessing = false;
      this.updateState({ isProcessing: false });
    }
  }
  
  /**
   * Wait for response to a message
   */
  private async waitForResponse(messageId: string, timeout = 60000): Promise<void> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      
      // Setup response handler
      const unsubscribe = this.wsClient.on('agent_completed', (event) => {
        // Check if this is the response we're waiting for
        if (event.data?.reply_to === messageId) {
          unsubscribe();
          resolve();
        }
      });
      
      // Setup timeout
      const timeoutId = setTimeout(() => {
        unsubscribe();
        logger.warn('Response timeout', { messageId });
        resolve(); // Resolve anyway to continue processing
      }, timeout);
      
      // Cleanup on resolution
      Promise.resolve().then(() => {
        clearTimeout(timeoutId);
      });
    });
  }
  
  /**
   * Cancel current message processing
   */
  cancelCurrentMessage(): void {
    if (this.currentAbortController) {
      this.currentAbortController.abort();
      this.currentAbortController = null;
      logger.info('Current message cancelled');
    }
  }
  
  /**
   * Clear message queue
   */
  clearQueue(): void {
    const queueLength = this.messageQueue.length;
    this.messageQueue = [];
    logger.info('Message queue cleared', { clearedCount: queueLength });
  }
  
  /**
   * Setup WebSocket event handlers
   */
  private setupEventHandlers(): void {
    // Handle agent started
    this.wsClient.on('agent_started', (event) => {
      this.updateState({ 
        currentAgentRunId: event.runId || null 
      });
      logger.info('Agent started', { runId: event.runId });
    });
    
    // Handle agent completed
    this.wsClient.on('agent_completed', (event) => {
      const message: Message = {
        id: this.generateMessageId(),
        text: event.data?.message || 'Agent completed',
        timestamp: Date.now(),
        role: 'assistant',
        status: 'received',
        metadata: event.data
      };
      
      this.addMessageToState(message);
      
      // Update UVS context if present
      if (event.data?.report_type) {
        this.updateUVSContext(event.data);
      }
      
      this.updateState({ 
        currentAgentRunId: null 
      });
    });
    
    // Handle agent thinking
    this.wsClient.on('agent_thinking', (event) => {
      logger.debug('Agent thinking', { data: event.data });
    });
    
    // Handle errors
    this.wsClient.on('agent_error', (event) => {
      logger.error('🚨 Agent error', { error: event.data });
      
      const errorMessage: Message = {
        id: this.generateMessageId(),
        text: `Error: ${event.data?.error || 'Unknown error occurred'}`,
        timestamp: Date.now(),
        role: 'system',
        status: 'received',
        metadata: { error: true, ...event.data }
      };
      
      this.addMessageToState(errorMessage);
    });
  }
  
  /**
   * Update UVS context from agent response
   */
  private updateUVSContext(data: any): void {
    const uvsContext: UVSContext = {
      reportType: data.report_type || 'fallback',
      hasData: data.has_data || false,
      hasOptimizations: data.has_optimizations || false,
      triageResult: data.triage_result,
      dataResult: data.data_result,
      optimizationsResult: data.optimizations_result,
      explorationQuestions: data.exploration_questions,
      nextSteps: data.next_steps
    };
    
    this.updateState({ uvsContext });
    
    logger.info('UVS context updated', { 
      reportType: uvsContext.reportType 
    });
  }
  
  /**
   * Start queue processor (runs periodically)
   */
  private startQueueProcessor(): void {
    const processInterval = setInterval(() => {
      if (this.disposed) {
        clearInterval(processInterval);
        return;
      }
      
      if (this.messageQueue.length > 0 && !this.isProcessing) {
        this.processMessageQueue().catch(error => {
          logger.error('🚨 Queue processing error', { error });
        });
      }
    }, this.QUEUE_PROCESS_INTERVAL);
  }
  
  /**
   * Add message to state
   */
  private addMessageToState(message: Message): void {
    const messages = [...this.state.messages, message];
    this.updateState({ messages });
  }
  
  /**
   * Update message status
   */
  private updateMessageStatus(messageId: string, status: Message['status']): void {
    const messages = this.state.messages.map(msg => 
      msg.id === messageId ? { ...msg, status } : msg
    );
    this.updateState({ messages });
  }
  
  /**
   * Update conversation state
   */
  private updateState(updates: Partial<ConversationState>): void {
    this.state = {
      ...this.state,
      ...updates,
      lastActivity: Date.now()
    };
    
    // Persist state
    this.recoveryManager.saveState(this.state);
    
    // Notify handlers
    for (const handler of this.stateChangeHandlers) {
      try {
        handler(this.state);
      } catch (error) {
        logger.error('🚨 State change handler error', { error });
      }
    }
  }
  
  /**
   * Subscribe to state changes
   */
  onStateChange(handler: (state: ConversationState) => void): () => void {
    this.stateChangeHandlers.add(handler);
    
    // Call immediately with current state
    handler(this.state);
    
    // Return unsubscribe function
    return () => {
      this.stateChangeHandlers.delete(handler);
    };
  }
  
  /**
   * Recover state from storage
   */
  private async recoverState(): Promise<void> {
    try {
      const recovered = await this.recoveryManager.recoverState();
      if (recovered) {
        this.state = recovered as ConversationState;
        logger.info('State recovered', { 
          messageCount: this.state.messages.length 
        });
      }
    } catch (error) {
      logger.error('🚨 State recovery failed', { error });
    }
  }
  
  /**
   * Get current state
   */
  getState(): ConversationState {
    return { ...this.state };
  }
  
  /**
   * Get queue status
   */
  getQueueStatus() {
    return {
      queueLength: this.messageQueue.length,
      isProcessing: this.isProcessing,
      messages: this.messageQueue.map(item => ({
        id: item.message.id,
        text: item.message.text.substring(0, 50) + '...',
        attempts: item.attempts,
        queuedFor: Date.now() - item.addedAt
      }))
    };
  }
  
  /**
   * Clear conversation
   */
  clearConversation(): void {
    this.state = {
      threadId: null,
      messages: [],
      currentAgentRunId: null,
      isProcessing: false,
      lastActivity: Date.now()
    };
    
    this.messageQueue = [];
    this.recoveryManager.clearState();
    
    logger.info('Conversation cleared');
  }
  
  /**
   * Generate unique message ID
   */
  private generateMessageId(): string {
    return `msg_${this.userId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
  
  /**
   * Delay helper
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  /**
   * Dispose and cleanup
   */
  dispose(): void {
    if (this.disposed) {
      return;
    }
    
    logger.info('Disposing ConversationManager', { userId: this.userId });
    
    // Cancel current message
    this.cancelCurrentMessage();
    
    // Clear queue
    this.clearQueue();
    
    // Clear state handlers
    this.stateChangeHandlers.clear();
    
    // Mark as disposed
    this.disposed = true;
    
    logger.info('✅ ConversationManager disposed', { userId: this.userId });
  }
}