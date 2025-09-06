/**
 * AgentServiceV2 - v2 Agent API Service with Request Scoping
 * 
 * CRITICAL: Multi-user safety through request-scoped isolation
 * - Each request gets unique request_id for proper isolation
 * - v2 API ensures no data leakage between concurrent users
 * - Supports gradual migration from v1 to v2 endpoints
 * 
 * BVJ: Enterprise segment - agent reliability critical for AI workload optimization
 */
'use client';

import { logger } from '@/lib/logger';
import { generateUniqueId } from '@/lib/utils';
import { getUnifiedApiConfig, shouldUseV2AgentApi, getAgentEndpoint, getV2MigrationMode } from '@/lib/unified-api-config';
import type { AgentResult } from '@/types/agent-types';

// ============================================================================
// V2 API REQUEST/RESPONSE TYPES
// ============================================================================

export interface V2AgentRequest {
  /** Unique request identifier for request scoping */
  request_id: string;
  /** Agent type to execute (data, optimization, triage) */
  agent_type: 'data' | 'optimization' | 'triage' | 'supervisor';
  /** User's request message */
  message: string;
  /** Optional thread ID for conversation continuity */
  thread_id?: string;
  /** User identifier for multi-user isolation */
  user_id?: string;
  /** Additional context for the agent */
  context?: Record<string, unknown>;
  /** Agent execution settings */
  settings?: {
    /** Timeout in milliseconds (default: 300000 = 5 minutes) */
    timeout_ms?: number;
    /** Enable streaming responses */
    stream?: boolean;
    /** Include detailed metrics in response */
    include_metrics?: boolean;
  };
  /** Testing and debugging options */
  debug?: {
    simulate_delay?: boolean;
    force_failure?: boolean;
    force_retry?: boolean;
  };
}

export interface V2AgentResponse {
  /** Request ID for tracking */
  request_id: string;
  /** Execution success status */
  success: boolean;
  /** Agent execution result */
  result?: AgentResult;
  /** Error message if execution failed */
  error?: string;
  /** Error code for specific error types */
  error_code?: string;
  /** Execution metrics */
  metrics?: {
    execution_time_ms: number;
    tokens_used?: number;
    api_calls?: number;
    tools_executed?: number;
  };
  /** Server-side warnings or notices */
  warnings?: string[];
  /** Response metadata */
  metadata?: Record<string, unknown>;
}

export interface V1AgentRequest {
  /** Agent type (for v1 backward compatibility) */
  type: string;
  /** User message */
  message: string;
  /** Additional context */
  context?: Record<string, unknown>;
  /** Debug options */
  simulate_delay?: boolean;
  force_failure?: boolean;
  force_retry?: boolean;
}

export interface V1AgentResponse {
  success: boolean;
  output?: string;
  error?: string;
  data?: unknown;
}

// ============================================================================
// MIGRATION AND ERROR HANDLING
// ============================================================================

export interface AgentRequestOptions {
  /** Timeout in milliseconds */
  timeout?: number;
  /** Retry attempts */
  retries?: number;
  /** Force v1 API usage */
  forceV1?: boolean;
  /** Include detailed metrics */
  includeMetrics?: boolean;
  /** Additional headers */
  headers?: Record<string, string>;
}

export interface AgentExecutionResult {
  success: boolean;
  result?: AgentResult;
  error?: string;
  error_code?: string;
  metrics?: Record<string, number>;
  warnings?: string[];
  api_version: 'v1' | 'v2';
  request_id: string;
}

export class AgentServiceV2Error extends Error {
  constructor(
    message: string,
    public readonly code?: string,
    public readonly statusCode?: number,
    public readonly apiVersion?: 'v1' | 'v2'
  ) {
    super(message);
    this.name = 'AgentServiceV2Error';
  }
}

// ============================================================================
// AGENT SERVICE V2 CLASS
// ============================================================================

class AgentServiceV2Class {
  private readonly DEFAULT_TIMEOUT = 300000; // 5 minutes
  private readonly DEFAULT_RETRIES = 3;
  private readonly RETRY_DELAY_BASE = 1000; // 1 second

  // ============================================
  // Core Execution Methods
  // ============================================

  /**
   * Execute agent with automatic v1/v2 API selection
   */
  public async executeAgent(
    agentType: 'data' | 'optimization' | 'triage' | 'supervisor',
    message: string,
    threadId?: string,
    options: AgentRequestOptions = {}
  ): Promise<AgentExecutionResult> {
    const requestId = this.generateRequestId();
    const startTime = performance.now();

    try {
      // Determine API version based on configuration and options
      const useV2 = this.shouldUseV2Api(options.forceV1);
      
      logger.info('Executing agent request', {
        request_id: requestId,
        agent_type: agentType,
        api_version: useV2 ? 'v2' : 'v1',
        thread_id: threadId,
        message_length: message.length
      });

      const result = useV2 
        ? await this.executeV2Request(requestId, agentType, message, threadId, options)
        : await this.executeV1Request(agentType, message, options);

      const executionTime = performance.now() - startTime;
      
      logger.info('Agent request completed', {
        request_id: requestId,
        success: result.success,
        execution_time_ms: executionTime,
        api_version: result.api_version
      });

      return result;
    } catch (error) {
      const executionTime = performance.now() - startTime;
      
      logger.error('Agent request failed', error, {
        request_id: requestId,
        agent_type: agentType,
        execution_time_ms: executionTime
      });

      throw this.wrapError(error, requestId);
    }
  }

  /**
   * Execute optimization agent (convenience method)
   */
  public async executeOptimizationAgent(
    message: string,
    threadId?: string,
    options: AgentRequestOptions = {}
  ): Promise<AgentExecutionResult> {
    return this.executeAgent('optimization', message, threadId, options);
  }

  /**
   * Execute data agent (convenience method)
   */
  public async executeDataAgent(
    message: string,
    threadId?: string,
    options: AgentRequestOptions = {}
  ): Promise<AgentExecutionResult> {
    return this.executeAgent('data', message, threadId, options);
  }

  /**
   * Execute triage agent (convenience method)
   */
  public async executeTriageAgent(
    message: string,
    threadId?: string,
    options: AgentRequestOptions = {}
  ): Promise<AgentExecutionResult> {
    return this.executeAgent('triage', message, threadId, options);
  }

  // ============================================
  // V2 API Implementation
  // ============================================

  private async executeV2Request(
    requestId: string,
    agentType: 'data' | 'optimization' | 'triage' | 'supervisor',
    message: string,
    threadId?: string,
    options: AgentRequestOptions = {}
  ): Promise<AgentExecutionResult> {
    const config = getUnifiedApiConfig();
    const endpoint = config.endpoints.agentV2Execute;

    const requestPayload: V2AgentRequest = {
      request_id: requestId,
      agent_type: agentType,
      message,
      thread_id: threadId,
      context: {},
      settings: {
        timeout_ms: options.timeout || this.DEFAULT_TIMEOUT,
        stream: false,
        include_metrics: options.includeMetrics !== false
      }
    };

    const headers = {
      'Content-Type': 'application/json',
      ...this.getAuthHeaders(),
      ...options.headers
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || this.DEFAULT_TIMEOUT);

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestPayload),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await this.parseErrorResponse(response);
        throw new AgentServiceV2Error(
          errorData.message || `HTTP ${response.status}`,
          errorData.code,
          response.status,
          'v2'
        );
      }

      const data: V2AgentResponse = await response.json();

      return {
        success: data.success,
        result: data.result,
        error: data.error,
        error_code: data.error_code,
        metrics: data.metrics,
        warnings: data.warnings,
        api_version: 'v2',
        request_id: requestId
      };
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // ============================================
  // V1 API Implementation (Backward Compatibility)
  // ============================================

  private async executeV1Request(
    agentType: 'data' | 'optimization' | 'triage' | 'supervisor',
    message: string,
    options: AgentRequestOptions = {}
  ): Promise<AgentExecutionResult> {
    const endpoint = getAgentEndpoint(agentType);
    const requestId = this.generateRequestId();

    const requestPayload: V1AgentRequest = {
      type: agentType,
      message,
      context: {},
      simulate_delay: false,
      force_failure: false,
      force_retry: false
    };

    const headers = {
      'Content-Type': 'application/json',
      ...this.getAuthHeaders(),
      ...options.headers
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || this.DEFAULT_TIMEOUT);

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestPayload),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await this.parseErrorResponse(response);
        throw new AgentServiceV2Error(
          errorData.message || `HTTP ${response.status}`,
          errorData.code,
          response.status,
          'v1'
        );
      }

      const data: V1AgentResponse = await response.json();

      // Convert v1 response to v2 format
      return {
        success: data.success,
        result: {
          success: data.success,
          output: data.output,
          error: data.error,
          data: data.data
        },
        error: data.error,
        api_version: 'v1',
        request_id: requestId
      };
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // ============================================
  // Utility Methods
  // ============================================

  private shouldUseV2Api(forceV1?: boolean): boolean {
    if (forceV1) return false;
    return shouldUseV2AgentApi();
  }

  private generateRequestId(): string {
    return generateUniqueId('req');
  }

  private getAuthHeaders(): Record<string, string> {
    const token = this.getAuthToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  private getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('jwt_token');
  }

  private async parseErrorResponse(response: Response): Promise<{ message: string; code?: string }> {
    try {
      const errorData = await response.json();
      return {
        message: errorData.error || errorData.message || 'Unknown error',
        code: errorData.error_code || errorData.code
      };
    } catch {
      return { message: `HTTP ${response.status} ${response.statusText}` };
    }
  }

  private wrapError(error: unknown, requestId: string): AgentServiceV2Error {
    if (error instanceof AgentServiceV2Error) {
      return error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        return new AgentServiceV2Error('Request timeout', 'TIMEOUT');
      }
      return new AgentServiceV2Error(error.message, 'UNKNOWN_ERROR');
    }

    return new AgentServiceV2Error('Unknown error occurred', 'UNKNOWN_ERROR');
  }

  // ============================================
  // Configuration and Health Checks
  // ============================================

  /**
   * Get current API configuration status
   */
  public getConfigurationStatus(): {
    v2_enabled: boolean;
    migration_mode: string;
    environment: string;
    endpoints: {
      v1_optimization: string;
      v1_data: string;
      v1_triage: string;
      v2_execute: string;
    };
  } {
    const config = getUnifiedApiConfig();
    return {
      v2_enabled: config.features.enableV2AgentApi,
      migration_mode: config.features.v2MigrationMode,
      environment: config.environment,
      endpoints: {
        v1_optimization: config.endpoints.agentV1Optimization,
        v1_data: config.endpoints.agentV1Data,
        v1_triage: config.endpoints.agentV1Triage,
        v2_execute: config.endpoints.agentV2Execute
      }
    };
  }

  /**
   * Test connectivity to agent endpoints
   */
  public async testConnectivity(): Promise<{
    v1_reachable: boolean;
    v2_reachable: boolean;
    latency_ms: Record<string, number>;
    errors: Record<string, string>;
  }> {
    const config = getUnifiedApiConfig();
    const results = {
      v1_reachable: false,
      v2_reachable: false,
      latency_ms: {} as Record<string, number>,
      errors: {} as Record<string, string>
    };

    // Test v1 endpoint
    try {
      const start = performance.now();
      const response = await fetch(config.endpoints.agentV1Optimization, { method: 'HEAD' });
      results.latency_ms.v1 = performance.now() - start;
      results.v1_reachable = response.ok;
    } catch (error) {
      results.errors.v1 = error instanceof Error ? error.message : 'Unknown error';
    }

    // Test v2 endpoint
    try {
      const start = performance.now();
      const response = await fetch(config.endpoints.agentV2Execute, { method: 'HEAD' });
      results.latency_ms.v2 = performance.now() - start;
      results.v2_reachable = response.ok;
    } catch (error) {
      results.errors.v2 = error instanceof Error ? error.message : 'Unknown error';
    }

    return results;
  }
}

// ============================================================================
// SINGLETON EXPORT
// ============================================================================

export const AgentServiceV2 = new AgentServiceV2Class();
export default AgentServiceV2;

// Export types for external use
export type {
  V2AgentRequest,
  V2AgentResponse,
  V1AgentRequest,
  V1AgentResponse,
  AgentRequestOptions,
  AgentExecutionResult
};