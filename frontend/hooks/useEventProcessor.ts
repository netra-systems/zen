/**
 * Hook for processing WebSocket events with race condition prevention
 * Replaces ref-based tracking with robust event queue system
 */

import { useEffect, useRef, useCallback } from 'react';
import { WebSocketMessage } from '@/types/backend_schema_auto_generated';
import { UnifiedWebSocketEvent } from '@/types/unified-chat';
import { EventQueue, ProcessableEvent, createWebSocketEventQueue } from '@/lib/event-queue';
import { logger } from '@/lib/logger';
import { generateUniqueId } from '@/lib/utils';
import { websocketDebugger } from '@/services/websocketDebugger';

interface WebSocketEventWithId extends ProcessableEvent {
  originalMessage: WebSocketMessage;
  processed?: boolean;
}

interface UseEventProcessorConfig {
  maxQueueSize?: number;
  duplicateWindowMs?: number;
  processingTimeoutMs?: number;
  enableDeduplication?: boolean;
}

interface UseEventProcessorReturn {
  processedCount: number;
  errorCount: number;
  queueSize: number;
  duplicatesDropped: number;
  getStats: () => any;
  clearQueue: () => void;
}

/**
 * Hook for processing WebSocket events with race condition prevention
 */
export function useEventProcessor(
  messages: WebSocketMessage[],
  eventHandler: (event: UnifiedWebSocketEvent) => void,
  config: UseEventProcessorConfig = {}
): UseEventProcessorReturn {
  const eventQueueRef = useRef<EventQueue<WebSocketEventWithId>>();
  const lastProcessedCountRef = useRef(0);
  const isInitializedRef = useRef(false);

  // Create stable event processor function
  const processEvent = useCallback(async (event: WebSocketEventWithId) => {
    try {
      // Ensure we have a unified event format
      const unifiedEvent = convertToUnifiedEvent(event.originalMessage);
      if (unifiedEvent) {
        // Process the event
        eventHandler(unifiedEvent);
        
        // Mark as processed in debugger with layer update detection
        const layerUpdates = detectLayerUpdates(unifiedEvent);
        websocketDebugger.markEventProcessed(event.id, layerUpdates);
        
        logger.debug('Event processed via queue', {
          component: 'useEventProcessor',
          eventId: event.id,
          eventType: event.type,
          timestamp: event.timestamp,
          layerUpdates
        });
      }
    } catch (error) {
      // Mark as failed in debugger
      websocketDebugger.markEventFailed(event.id, (error as Error).message);
      
      logger.error('Event processing failed in hook', error as Error, {
        component: 'useEventProcessor',
        eventId: event.id,
        eventType: event.type
      });
      throw error; // Re-throw to be caught by queue
    }
  }, [eventHandler]);

  // Initialize event queue
  useEffect(() => {
    if (!isInitializedRef.current) {
      eventQueueRef.current = createWebSocketEventQueue(
        processEvent,
        {
          maxQueueSize: 500,
          duplicateWindowMs: 3000,
          processingTimeoutMs: 5000,
          enableDeduplication: true,
          ...config
        }
      );
      isInitializedRef.current = true;
      
      logger.debug('Event processor initialized', {
        component: 'useEventProcessor',
        config
      });
    }

    return () => {
      if (eventQueueRef.current) {
        eventQueueRef.current.destroy();
        eventQueueRef.current = undefined;
        isInitializedRef.current = false;
      }
    };
  }, [processEvent, config]);

  // Process new messages
  useEffect(() => {
    if (!eventQueueRef.current || messages.length <= lastProcessedCountRef.current) {
      return;
    }

    const newMessages = messages.slice(lastProcessedCountRef.current);
    const queue = eventQueueRef.current;
    
    logger.debug('Processing new WebSocket messages', {
      component: 'useEventProcessor',
      newCount: newMessages.length,
      totalCount: messages.length,
      lastProcessed: lastProcessedCountRef.current
    });

    // Convert and enqueue new messages
    let enqueuedCount = 0;
    let duplicateCount = 0;
    
    newMessages.forEach((message, index) => {
      // Trace event in debugger for validation
      const validation = websocketDebugger.traceEvent(message);
      
      const eventWithId = convertMessageToEvent(message, lastProcessedCountRef.current + index);
      
      if (eventWithId) {
        const success = queue.enqueue(eventWithId);
        if (success) {
          enqueuedCount++;
        } else {
          duplicateCount++;
        }
      } else if (!validation.isValid) {
        logger.warn('Invalid WebSocket message skipped', {
          component: 'useEventProcessor',
          action: 'invalid_message_skipped',
          metadata: {
            eventType: message.type,
            issues: validation.issues,
            suggestions: validation.suggestions
          }
        });
      }
    });

    // Update processed count after successful enqueuing
    lastProcessedCountRef.current = messages.length;
    
    logger.debug('Messages enqueued for processing', {
      component: 'useEventProcessor',
      enqueuedCount,
      duplicateCount,
      totalMessages: messages.length
    });
    
  }, [messages]);

  // Get current statistics
  const getStats = useCallback(() => {
    return eventQueueRef.current?.getStats() || {
      totalProcessed: 0,
      totalDropped: 0,
      totalErrors: 0,
      queueSize: 0,
      duplicatesDropped: 0,
      lastProcessedTimestamp: 0
    };
  }, []);

  // Clear queue
  const clearQueue = useCallback(() => {
    if (eventQueueRef.current) {
      eventQueueRef.current.clear();
      lastProcessedCountRef.current = 0;
    }
  }, []);

  const stats = getStats();

  return {
    processedCount: stats.totalProcessed,
    errorCount: stats.totalErrors,
    queueSize: stats.queueSize,
    duplicatesDropped: stats.duplicatesDropped,
    getStats,
    clearQueue
  };
}

/**
 * Convert WebSocket message to processable event with unique ID
 */
function convertMessageToEvent(
  message: WebSocketMessage, 
  messageIndex: number
): WebSocketEventWithId | null {
  try {
    // Generate unique ID based on message content and timing
    const messageId = (message.payload as any)?.message_id;
    const timestamp = (message.payload as any)?.timestamp || Date.now();
    
    const eventId = messageId || 
      generateUniqueId(`ws-${message.type}-${messageIndex}-${timestamp}`);

    return {
      id: eventId,
      type: message.type,
      payload: message.payload,
      timestamp: typeof timestamp === 'number' ? timestamp : Date.now(),
      source: 'websocket',
      originalMessage: message
    };
  } catch (error) {
    logger.error('Failed to convert message to event', error as Error, {
      component: 'useEventProcessor',
      messageType: message.type
    });
    return null;
  }
}

/**
 * Convert WebSocket message to unified event format
 */
function convertToUnifiedEvent(message: WebSocketMessage): UnifiedWebSocketEvent | null {
  try {
    // Check if this is already a unified event type
    const unifiedEventTypes = [
      // Agent lifecycle events
      'agent_started', 'agent_completed', 'agent_stopped', 'agent_error',
      'agent_update', 'agent_thinking', 'agent_log',
      
      // Tool events  
      'tool_executing', 'tool_started', 'tool_completed', 'tool_call', 'tool_result',
      
      // Sub-agent events
      'subagent_started', 'subagent_completed', 'sub_agent_update',
      
      // Content streaming events
      'partial_result', 'stream_chunk', 'stream_complete',
      
      // Completion events
      'final_report', 'agent_finished',
      
      // Thread management events
      'thread_created', 'thread_loading', 'thread_loaded', 'thread_renamed', 
      'thread_updated', 'thread_deleted', 'thread_switched', 'thread_history',
      
      // Step events
      'step_created',
      
      // System events
      'error', 'connection_established', 'message_received'
    ];
    
    if (unifiedEventTypes.includes(message.type)) {
      return message as UnifiedWebSocketEvent;
    }
    
    logger.debug('Non-unified event skipped', {
      component: 'useEventProcessor',
      eventType: message.type
    });
    
    return null;
  } catch (error) {
    logger.error('Failed to convert to unified event', error as Error, {
      component: 'useEventProcessor',
      messageType: message.type
    });
    return null;
  }
}

/**
 * Detect which layers should be updated based on event type
 */
function detectLayerUpdates(event: UnifiedWebSocketEvent): {
  fast?: boolean;
  medium?: boolean;
  slow?: boolean;
} {
  const fastLayerEvents = [
    'agent_started', 'tool_executing', 'tool_started', 'tool_call', 
    'tool_completed', 'tool_result', 'agent_update'
  ];
  
  const mediumLayerEvents = [
    'agent_thinking', 'partial_result', 'stream_chunk', 'sub_agent_update'
  ];
  
  const slowLayerEvents = [
    'agent_completed', 'final_report', 'subagent_completed', 'stream_complete'
  ];
  
  return {
    fast: fastLayerEvents.includes(event.type),
    medium: mediumLayerEvents.includes(event.type),
    slow: slowLayerEvents.includes(event.type)
  };
}