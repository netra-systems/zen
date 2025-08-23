/**
 * AgentUpdateStream - 100ms granularity continuous agent updates
 * Provides fluid UI updates during agent processing with RAF optimization
 */
'use client';

import { logger } from '@/lib/logger';
import type { UnifiedWebSocketEvent } from '@/types/unified-chat';
import type { WebSocketMessage } from '@/types/unified';

export interface AgentUpdate {
  agentId: string;
  status: 'thinking' | 'executing' | 'tool_running' | 'complete' | 'error';
  timestamp: number;
  progress?: number;
  metadata?: Record<string, any>;
  toolName?: string;
  result?: any;
}

export interface StreamBatch {
  updates: AgentUpdate[];
  timestamp: number;
  frameId: number;
}

interface StreamSubscriber {
  id: string;
  callback: (batch: StreamBatch) => void;
  filter?: (update: AgentUpdate) => boolean;
}

interface StreamMetrics {
  totalUpdates: number;
  batchesProcessed: number;
  averageBatchSize: number;
  lastProcessingTime: number;
}

class AgentUpdateStreamService {
  private updateQueue: AgentUpdate[] = [];
  private subscribers: StreamSubscriber[] = [];
  private batchTimer: NodeJS.Timeout | null = null;
  private rafId: number | null = null;
  private frameCounter = 0;
  private lastBatchTime = 0;
  private metrics: StreamMetrics = this.createInitialMetrics();
  private isActive = false;

  private readonly BATCH_INTERVAL = 100; // 100ms
  private readonly MAX_BATCH_SIZE = 50;
  private readonly PERFORMANCE_THRESHOLD = 16; // 60fps target

  // ============================================
  // Core Stream Management
  // ============================================

  public start(): void {
    if (this.isActive) return;
    this.isActive = true;
    this.startBatchProcessing();
    this.logStreamStart();
  }

  public stop(): void {
    this.isActive = false;
    this.clearTimers();
    this.clearQueue();
    this.logStreamStop();
  }

  private startBatchProcessing(): void {
    this.batchTimer = setInterval(() => {
      this.processBatchWithRAF();
    }, this.BATCH_INTERVAL);
  }

  private processBatchWithRAF(): void {
    if (this.updateQueue.length === 0) return;
    
    this.rafId = requestAnimationFrame(() => {
      this.processBatch();
    });
  }

  private processBatch(): void {
    const startTime = performance.now();
    const batch = this.createBatch();
    
    if (batch.updates.length === 0) return;
    
    this.notifySubscribers(batch);
    this.updateMetrics(batch, performance.now() - startTime);
  }

  // ============================================
  // Update Management
  // ============================================

  public addUpdate(update: AgentUpdate): void {
    const validatedUpdate = this.validateUpdate(update);
    if (!validatedUpdate) return;
    
    this.updateQueue.push({
      ...validatedUpdate,
      timestamp: Date.now()
    });
    
    this.enforceQueueSize();
  }

  public addWebSocketUpdate(event: UnifiedWebSocketEvent | WebSocketMessage): void {
    const update = this.convertWebSocketToUpdate(event);
    if (update) this.addUpdate(update);
  }

  private validateUpdate(update: AgentUpdate): AgentUpdate | null {
    if (!update.agentId || !update.status) return null;
    if (update.progress && (update.progress < 0 || update.progress > 100)) return null;
    return update;
  }

  private convertWebSocketToUpdate(event: UnifiedWebSocketEvent | WebSocketMessage): AgentUpdate | null {
    const agentEvents = ['agent_started', 'agent_thinking', 'tool_executing', 'agent_completed'];
    if (!agentEvents.includes(event.type)) return null;
    
    return this.createUpdateFromEvent(event);
  }

  private createUpdateFromEvent(event: UnifiedWebSocketEvent | WebSocketMessage): AgentUpdate {
    const payload = event.payload as any;
    
    return {
      agentId: payload.agent_id || payload.agentName || 'unknown',
      status: this.mapEventToStatus(event.type),
      timestamp: Date.now(),
      progress: payload.progress,
      metadata: payload.metadata,
      toolName: payload.tool_name,
      result: payload.result
    };
  }

  // ============================================
  // Batch Processing
  // ============================================

  private createBatch(): StreamBatch {
    const updates = this.updateQueue.splice(0, this.MAX_BATCH_SIZE);
    
    return {
      updates,
      timestamp: Date.now(),
      frameId: ++this.frameCounter
    };
  }

  private enforceQueueSize(): void {
    if (this.updateQueue.length > this.MAX_BATCH_SIZE * 2) {
      this.updateQueue = this.updateQueue.slice(-this.MAX_BATCH_SIZE);
    }
  }

  // ============================================
  // Subscription Management
  // ============================================

  public subscribe(callback: (batch: StreamBatch) => void, filter?: (update: AgentUpdate) => boolean): string {
    const id = this.generateSubscriberId();
    
    this.subscribers.push({
      id,
      callback,
      filter
    });
    
    return id;
  }

  public unsubscribe(id: string): void {
    this.subscribers = this.subscribers.filter(sub => sub.id !== id);
  }

  private notifySubscribers(batch: StreamBatch): void {
    this.subscribers.forEach(subscriber => {
      const filteredBatch = this.filterBatchForSubscriber(batch, subscriber);
      if (filteredBatch.updates.length > 0) {
        subscriber.callback(filteredBatch);
      }
    });
  }

  private filterBatchForSubscriber(batch: StreamBatch, subscriber: StreamSubscriber): StreamBatch {
    if (!subscriber.filter) return batch;
    
    return {
      ...batch,
      updates: batch.updates.filter(subscriber.filter)
    };
  }

  // ============================================
  // Utility Functions
  // ============================================

  private mapEventToStatus(eventType: string): AgentUpdate['status'] {
    const statusMap: Record<string, AgentUpdate['status']> = {
      'agent_started': 'thinking',
      'agent_thinking': 'thinking',
      'tool_executing': 'tool_running',
      'agent_completed': 'complete'
    };
    
    return statusMap[eventType] || 'thinking';
  }

  private createInitialMetrics(): StreamMetrics {
    return {
      totalUpdates: 0,
      batchesProcessed: 0,
      averageBatchSize: 0,
      lastProcessingTime: 0
    };
  }

  private updateMetrics(batch: StreamBatch, processingTime: number): void {
    this.metrics.totalUpdates += batch.updates.length;
    this.metrics.batchesProcessed++;
    this.metrics.averageBatchSize = this.metrics.totalUpdates / this.metrics.batchesProcessed;
    this.metrics.lastProcessingTime = processingTime;
  }

  private generateSubscriberId(): string {
    return `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private clearTimers(): void {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
      this.batchTimer = null;
    }
    
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }

  private clearQueue(): void {
    this.updateQueue = [];
  }

  private logStreamStart(): void {
    logger.debug('AgentUpdateStream started', undefined, {
      component: 'AgentUpdateStream',
      action: 'stream_start'
    });
  }

  private logStreamStop(): void {
    logger.debug('AgentUpdateStream stopped', undefined, {
      component: 'AgentUpdateStream',
      action: 'stream_stop',
      metadata: this.metrics
    });
  }

  // ============================================
  // Public Interface
  // ============================================

  public getMetrics(): StreamMetrics {
    return { ...this.metrics };
  }

  public isStreamActive(): boolean {
    return this.isActive;
  }

  public getQueueSize(): number {
    return this.updateQueue.length;
  }

  public getSubscriberCount(): number {
    return this.subscribers.length;
  }
}

export const agentUpdateStream = new AgentUpdateStreamService();