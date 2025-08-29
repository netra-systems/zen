/**
 * WebSocket Event Debugging and Validation Service
 * Provides comprehensive debugging capabilities for WebSocket event flow
 */

import { WebSocketMessage } from '@/types/unified';
import { UnifiedWebSocketEvent } from '@/types/unified-chat';
import { logger } from '@/lib/logger';

interface EventFlowStats {
  totalEvents: number;
  eventsByType: Record<string, number>;
  processingErrors: number;
  lastEventTime: number;
  averageProcessingTime: number;
  eventLatencies: number[];
}

interface EventValidationResult {
  isValid: boolean;
  issues: string[];
  severity: 'low' | 'medium' | 'high';
  suggestions: string[];
}

interface EventFlowTrace {
  eventId: string;
  eventType: string;
  receivedAt: number;
  processedAt?: number;
  processingTime?: number;
  layerUpdates: {
    fast?: boolean;
    medium?: boolean;
    slow?: boolean;
  };
  errors: string[];
  status: 'received' | 'processing' | 'completed' | 'failed';
}

class WebSocketDebugger {
  private stats: EventFlowStats = {
    totalEvents: 0,
    eventsByType: {},
    processingErrors: 0,
    lastEventTime: 0,
    averageProcessingTime: 0,
    eventLatencies: []
  };

  private eventTraces: Map<string, EventFlowTrace> = new Map();
  private maxTraceHistory = 100;
  private debugMode = false;
  private validationRules: Array<(event: any) => EventValidationResult> = [];

  constructor() {
    this.initializeValidationRules();
  }

  /**
   * Enable/disable debug mode
   */
  setDebugMode(enabled: boolean): void {
    this.debugMode = enabled;
    if (enabled) {
      logger.info('WebSocket debugger enabled', {
        component: 'WebSocketDebugger',
        action: 'debug_enabled'
      });
    }
  }

  /**
   * Validate and trace incoming WebSocket event
   */
  traceEvent(event: WebSocketMessage): EventValidationResult {
    // Defensive programming: handle undefined or malformed events
    if (!event) {
      return {
        isValid: false,
        issues: ['Event is undefined or null'],
        severity: 'critical',
        suggestions: ['Ensure event is properly passed to traceEvent']
      };
    }
    
    const eventId = this.generateEventId(event);
    const now = Date.now();
    
    // Update stats with safe event
    this.updateStats(event, now);
    
    // Validate event
    const validation = this.validateEvent(event);
    
    // Create trace
    const trace: EventFlowTrace = {
      eventId,
      eventType: event?.type || 'unknown',
      receivedAt: now,
      layerUpdates: {},
      errors: validation.isValid ? [] : validation.issues,
      status: validation.isValid ? 'received' : 'failed'
    };
    
    this.eventTraces.set(eventId, trace);
    this.trimTraceHistory();
    
    if (this.debugMode) {
      logger.debug('WebSocket event traced', {
        component: 'WebSocketDebugger',
        action: 'event_traced',
        metadata: {
          eventId,
          eventType: event.type,
          isValid: validation.isValid,
          issues: validation.issues
        }
      });
    }
    
    return validation;
  }

  /**
   * Mark event as processed and record processing time
   */
  markEventProcessed(eventId: string, layerUpdates: EventFlowTrace['layerUpdates']): void {
    const trace = this.eventTraces.get(eventId);
    if (trace) {
      const now = Date.now();
      trace.processedAt = now;
      trace.processingTime = now - trace.receivedAt;
      trace.layerUpdates = layerUpdates;
      trace.status = 'completed';
      
      // Update average processing time
      this.stats.eventLatencies.push(trace.processingTime);
      if (this.stats.eventLatencies.length > 100) {
        this.stats.eventLatencies = this.stats.eventLatencies.slice(-100);
      }
      this.stats.averageProcessingTime = 
        this.stats.eventLatencies.reduce((a, b) => a + b, 0) / this.stats.eventLatencies.length;
      
      if (this.debugMode) {
        logger.debug('WebSocket event processed', {
          component: 'WebSocketDebugger',
          action: 'event_processed',
          metadata: {
            eventId,
            processingTime: trace.processingTime,
            layerUpdates
          }
        });
      }
    }
  }

  /**
   * Mark event processing as failed
   */
  markEventFailed(eventId: string, error: string): void {
    const trace = this.eventTraces.get(eventId);
    if (trace) {
      trace.errors.push(error);
      trace.status = 'failed';
      this.stats.processingErrors++;
      
      logger.error('WebSocket event processing failed', new Error(error), {
        component: 'WebSocketDebugger',
        action: 'event_failed',
        metadata: { eventId, error }
      });
    }
  }

  /**
   * Get comprehensive debugging statistics
   */
  getStats(): EventFlowStats & {
    recentTraces: EventFlowTrace[];
    failedEvents: EventFlowTrace[];
    healthScore: number;
  } {
    const recentTraces = Array.from(this.eventTraces.values())
      .sort((a, b) => b.receivedAt - a.receivedAt)
      .slice(0, 20);
    
    const failedEvents = Array.from(this.eventTraces.values())
      .filter(trace => trace.status === 'failed' || trace.errors.length > 0)
      .slice(0, 10);
    
    // Calculate health score (0-100)
    const totalEvents = this.stats.totalEvents;
    const errorRate = totalEvents > 0 ? this.stats.processingErrors / totalEvents : 0;
    const avgLatency = this.stats.averageProcessingTime;
    
    let healthScore = 100;
    healthScore -= Math.min(errorRate * 50, 40); // Max 40 points for errors
    healthScore -= Math.min(avgLatency / 100, 30); // Max 30 points for latency
    healthScore = Math.max(0, Math.round(healthScore));
    
    return {
      ...this.stats,
      recentTraces,
      failedEvents,
      healthScore
    };
  }

  /**
   * Generate a debug report for troubleshooting
   */
  generateDebugReport(): string {
    const stats = this.getStats();
    const now = new Date().toISOString();
    
    return `
=== WebSocket Event Flow Debug Report ===
Generated: ${now}
Debug Mode: ${this.debugMode ? 'ENABLED' : 'DISABLED'}

=== Overall Statistics ===
Total Events: ${stats.totalEvents}
Processing Errors: ${stats.processingErrors} (${((stats.processingErrors / stats.totalEvents) * 100).toFixed(1)}%)
Average Processing Time: ${stats.averageProcessingTime.toFixed(2)}ms
Health Score: ${stats.healthScore}/100
Last Event: ${stats.lastEventTime ? new Date(stats.lastEventTime).toISOString() : 'None'}

=== Event Types Distribution ===
${Object.entries(stats.eventsByType)
  .sort(([,a], [,b]) => b - a)
  .map(([type, count]) => `${type}: ${count}`)
  .join('\n')}

=== Recent Failed Events ===
${stats.failedEvents.length > 0 
  ? stats.failedEvents.map(trace => 
      `[${new Date(trace.receivedAt).toISOString()}] ${trace.eventType} - ${trace.errors.join(', ')}`
    ).join('\n')
  : 'No recent failures'
}

=== Recent Event Latencies ===
${stats.eventLatencies.slice(-10).map((latency, i) => `Event ${i + 1}: ${latency}ms`).join('\n')}

=== Layer Update Success Rate ===
Fast Layer Updates: ${this.calculateLayerUpdateRate('fast')}%
Medium Layer Updates: ${this.calculateLayerUpdateRate('medium')}%
Slow Layer Updates: ${this.calculateLayerUpdateRate('slow')}%

=== Recommendations ===
${this.generateRecommendations(stats)}
`;
  }

  /**
   * Reset all debugging data
   */
  reset(): void {
    this.stats = {
      totalEvents: 0,
      eventsByType: {},
      processingErrors: 0,
      lastEventTime: 0,
      averageProcessingTime: 0,
      eventLatencies: []
    };
    this.eventTraces.clear();
    
    logger.info('WebSocket debugger reset', {
      component: 'WebSocketDebugger',
      action: 'reset'
    });
  }

  private initializeValidationRules(): void {
    // Rule: Event must have type
    this.validationRules.push((event) => {
      if (!event.type || typeof event.type !== 'string') {
        return {
          isValid: false,
          issues: ['Missing or invalid event type'],
          severity: 'high',
          suggestions: ['Ensure event has a valid string type field']
        };
      }
      return { isValid: true, issues: [], severity: 'low', suggestions: [] };
    });

    // Rule: Event must have payload
    this.validationRules.push((event) => {
      if (!event.payload || typeof event.payload !== 'object') {
        return {
          isValid: false,
          issues: ['Missing or invalid payload'],
          severity: 'high',
          suggestions: ['Ensure event has a valid payload object']
        };
      }
      return { isValid: true, issues: [], severity: 'low', suggestions: [] };
    });

    // Rule: Agent events should have agent identification
    this.validationRules.push((event) => {
      const agentEventTypes = ['agent_started', 'agent_completed', 'agent_thinking', 'agent_error'];
      if (agentEventTypes.includes(event.type)) {
        const payload = event.payload as any;
        if (!payload.agent_id && !payload.agent_type) {
          return {
            isValid: false,
            issues: ['Agent event missing agent identification'],
            severity: 'medium',
            suggestions: ['Add agent_id or agent_type to payload']
          };
        }
      }
      return { isValid: true, issues: [], severity: 'low', suggestions: [] };
    });

    // Rule: Tool events should have tool name
    this.validationRules.push((event) => {
      const toolEventTypes = ['tool_started', 'tool_completed', 'tool_executing', 'tool_call'];
      if (toolEventTypes.includes(event.type)) {
        const payload = event.payload as any;
        if (!payload.tool_name && !payload.name) {
          return {
            isValid: false,
            issues: ['Tool event missing tool name'],
            severity: 'medium',
            suggestions: ['Add tool_name or name to payload']
          };
        }
      }
      return { isValid: true, issues: [], severity: 'low', suggestions: [] };
    });
  }

  private generateEventId(event: WebSocketMessage): string {
    // Defensive programming: safely access nested properties
    const payload = event?.payload as any;
    
    // Check for message_id in various possible locations
    const messageId = payload?.message_id || 
                     payload?.messageId ||
                     payload?.id ||
                     null;
    
    // Generate fallback ID if no message_id found
    return messageId || 
           `${event?.type || 'unknown'}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private updateStats(event: WebSocketMessage, now: number): void {
    this.stats.totalEvents++;
    // Defensive programming: safely access event.type
    const eventType = event?.type || 'unknown';
    this.stats.eventsByType[eventType] = (this.stats.eventsByType[eventType] || 0) + 1;
    this.stats.lastEventTime = now;
  }

  private validateEvent(event: WebSocketMessage): EventValidationResult {
    const issues: string[] = [];
    const suggestions: string[] = [];
    let maxSeverity: 'low' | 'medium' | 'high' = 'low';

    // Defensive programming: handle undefined event
    if (!event) {
      return {
        isValid: false,
        issues: ['Event is undefined or null'],
        severity: 'high',
        suggestions: ['Ensure event object is properly initialized']
      };
    }

    for (const rule of this.validationRules) {
      const result = rule(event);
      if (!result.isValid) {
        issues.push(...result.issues);
        suggestions.push(...result.suggestions);
        if (result.severity === 'high' || (result.severity === 'medium' && maxSeverity === 'low')) {
          maxSeverity = result.severity;
        }
      }
    }

    return {
      isValid: issues.length === 0,
      issues,
      severity: maxSeverity,
      suggestions
    };
  }

  private trimTraceHistory(): void {
    if (this.eventTraces.size > this.maxTraceHistory) {
      const sortedEntries = Array.from(this.eventTraces.entries())
        .sort(([,a], [,b]) => b.receivedAt - a.receivedAt);
      
      this.eventTraces.clear();
      sortedEntries.slice(0, this.maxTraceHistory).forEach(([id, trace]) => {
        this.eventTraces.set(id, trace);
      });
    }
  }

  private calculateLayerUpdateRate(layer: 'fast' | 'medium' | 'slow'): number {
    const completedEvents = Array.from(this.eventTraces.values())
      .filter(trace => trace.status === 'completed');
    
    if (completedEvents.length === 0) return 0;
    
    const layerUpdates = completedEvents.filter(trace => trace.layerUpdates[layer]);
    return Math.round((layerUpdates.length / completedEvents.length) * 100);
  }

  private generateRecommendations(stats: any): string {
    const recommendations: string[] = [];
    
    if (stats.healthScore < 50) {
      recommendations.push('⚠️  Critical: Health score is low. Check for processing errors and high latency.');
    }
    
    if (stats.processingErrors / stats.totalEvents > 0.1) {
      recommendations.push('🔍 High error rate detected. Review event validation and error handling.');
    }
    
    if (stats.averageProcessingTime > 100) {
      recommendations.push('⏱️  High processing latency. Consider optimizing event handlers.');
    }
    
    const layerRates = ['fast', 'medium', 'slow'].map(layer => this.calculateLayerUpdateRate(layer as any));
    if (layerRates.some(rate => rate < 80)) {
      recommendations.push('📊 Some layers have low update rates. Check layer update logic.');
    }
    
    if (recommendations.length === 0) {
      recommendations.push('✅ System appears to be functioning normally.');
    }
    
    return recommendations.join('\n');
  }
}

// Export singleton instance
export const websocketDebugger = new WebSocketDebugger();