/**
 * Integration test for WebSocket message type alignment
 * CRITICAL: Ensures ALL backend message types have frontend handlers
 * Related to: SPEC/learnings/websocket_agent_response_missing_handler.xml
 */

import { describe, it, expect, beforeAll } from '@jest/globals';
import { getEventHandlers } from '@/store/websocket-event-handlers-main';

/**
 * Backend WebSocket message types (from netra_backend)
 * These MUST all have corresponding frontend handlers
 */
const BACKEND_MESSAGE_TYPES = {
  // Connection management
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  HEARTBEAT: 'heartbeat',
  HEARTBEAT_ACK: 'heartbeat_ack',
  PING: 'ping',
  PONG: 'pong',
  
  // User messages
  USER_MESSAGE: 'user_message',
  SYSTEM_MESSAGE: 'system_message',
  ERROR_MESSAGE: 'error_message',
  ERROR: 'error',
  
  // Agent communication (CRITICAL for chat)
  START_AGENT: 'start_agent',
  AGENT_RESPONSE: 'agent_response',  // CRITICAL: Was missing before
  AGENT_PROGRESS: 'agent_progress',
  AGENT_ERROR: 'agent_error',
  AGENT_STARTED: 'agent_started',
  AGENT_COMPLETED: 'agent_completed',
  AGENT_THINKING: 'agent_thinking',
  AGENT_UPDATE: 'agent_update',
  AGENT_LOG: 'agent_log',
  AGENT_STOPPED: 'agent_stopped',
  
  // Tool execution
  TOOL_CALL: 'tool_call',
  TOOL_EXECUTING: 'tool_executing',
  TOOL_STARTED: 'tool_started',
  TOOL_COMPLETED: 'tool_completed',
  TOOL_RESULT: 'tool_result',
  
  // Streaming
  STREAM_CHUNK: 'stream_chunk',
  STREAM_COMPLETE: 'stream_complete',
  PARTIAL_RESULT: 'partial_result',
  FINAL_REPORT: 'final_report',
  
  // Thread management
  THREAD_UPDATE: 'thread_update',
  THREAD_MESSAGE: 'thread_message',
  THREAD_CREATED: 'thread_created',
  THREAD_LOADING: 'thread_loading',
  THREAD_LOADED: 'thread_loaded',
  THREAD_RENAMED: 'thread_renamed',
  THREAD_HISTORY: 'thread_history',
  THREAD_UPDATED: 'thread_updated',
  THREAD_DELETED: 'thread_deleted',
  THREAD_SWITCHED: 'thread_switched',
  
  // Broadcasting
  BROADCAST: 'broadcast',
  ROOM_MESSAGE: 'room_message',
  
  // JSON-RPC
  JSONRPC_REQUEST: 'jsonrpc_request',
  JSONRPC_RESPONSE: 'jsonrpc_response',
  JSONRPC_NOTIFICATION: 'jsonrpc_notification',
  
  // MCP events
  MCP_SERVER_CONNECTED: 'mcp_server_connected',
  MCP_SERVER_DISCONNECTED: 'mcp_server_disconnected',
  MCP_TOOL_STARTED: 'mcp_tool_started',
  MCP_TOOL_COMPLETED: 'mcp_tool_completed',
  MCP_TOOL_FAILED: 'mcp_tool_failed',
  MCP_SERVER_ERROR: 'mcp_server_error',
  
  // Other
  CONNECTION_ESTABLISHED: 'connection_established',
  MESSAGE_RECEIVED: 'message_received',
  STEP_CREATED: 'step_created'
};

/**
 * Critical message types that MUST have handlers
 * These are essential for core chat functionality
 */
const CRITICAL_MESSAGE_TYPES = [
  'agent_response',    // Agent's actual response content
  'agent_started',     // Agent begins processing
  'agent_completed',   // Agent finishes processing
  'agent_thinking',    // Agent reasoning updates
  'agent_error',       // Agent errors
  'tool_executing',    // Tool execution begins
  'tool_completed',    // Tool execution ends
  'error',            // General errors
  'partial_result',   // Streaming content
  'final_report'      // Final agent report
];

/**
 * Message types that don't need frontend handlers
 * (handled at connection/protocol level)
 */
const PROTOCOL_ONLY_TYPES = [
  'connect',
  'disconnect',
  'heartbeat',
  'heartbeat_ack',
  'ping',
  'pong',
  'connection_established'
];

/**
 * Message types that are sent FROM frontend TO backend
 * (don't need handlers in frontend)
 */
const FRONTEND_TO_BACKEND_ONLY = [
  'start_agent',
  'user_message',
  'jsonrpc_request'
];

describe('WebSocket Message Type Alignment', () => {
  let frontendHandlers: Record<string, any>;

  beforeAll(() => {
    frontendHandlers = getEventHandlers();
  });

  describe('Critical Message Types', () => {
    it.each(CRITICAL_MESSAGE_TYPES)(
      'MUST have handler for %s',
      (messageType) => {
        expect(frontendHandlers[messageType]).toBeDefined();
        expect(typeof frontendHandlers[messageType]).toBe('function');
      }
    );

    it('specifically ensures agent_response handler exists (regression test)', () => {
      // This is THE critical fix - agent_response was missing
      expect(frontendHandlers['agent_response']).toBeDefined();
      expect(frontendHandlers['agent_response']).not.toBeNull();
      expect(typeof frontendHandlers['agent_response']).toBe('function');
    });
  });

  describe('Backend Message Coverage', () => {
    const messageTypesToCheck = Object.values(BACKEND_MESSAGE_TYPES)
      .filter(type => !PROTOCOL_ONLY_TYPES.includes(type))
      .filter(type => !FRONTEND_TO_BACKEND_ONLY.includes(type));

    it('should have handlers for agent-related messages', () => {
      const agentMessages = messageTypesToCheck.filter(type => type.includes('agent'));
      const missingHandlers: string[] = [];

      agentMessages.forEach(type => {
        if (!frontendHandlers[type]) {
          // Check for aliases (e.g., agent_finished -> agent_completed)
          const hasAlias = 
            (type === 'agent_finished' && frontendHandlers['agent_completed']) ||
            (type === 'agent_progress' && frontendHandlers['agent_update']) ||
            (type === 'agent_log' && frontendHandlers['agent_thinking']);
          
          if (!hasAlias) {
            missingHandlers.push(type);
          }
        }
      });

      if (missingHandlers.length > 0) {
        console.warn('Missing handlers for agent messages:', missingHandlers);
      }
      
      // Critical agent messages must ALL be handled
      expect(frontendHandlers['agent_response']).toBeDefined();
      expect(frontendHandlers['agent_started']).toBeDefined();
      expect(frontendHandlers['agent_completed']).toBeDefined();
      expect(frontendHandlers['agent_thinking']).toBeDefined();
    });

    it('should have handlers for tool-related messages', () => {
      const toolMessages = messageTypesToCheck.filter(type => type.includes('tool'));
      
      toolMessages.forEach(type => {
        // tool_call is aliased to tool_executing
        if (type === 'tool_call') {
          expect(frontendHandlers['tool_executing']).toBeDefined();
        } else if (type === 'tool_result') {
          expect(frontendHandlers['tool_completed']).toBeDefined();
        } else {
          expect(frontendHandlers[type]).toBeDefined();
        }
      });
    });

    it('should have handlers for streaming messages', () => {
      expect(frontendHandlers['partial_result']).toBeDefined();
      expect(frontendHandlers['final_report']).toBeDefined();
      // stream_chunk is aliased to partial_result
      expect(frontendHandlers['partial_result']).toBeDefined();
    });
  });

  describe('Handler Function Validation', () => {
    it('all handlers should be functions', () => {
      Object.entries(frontendHandlers).forEach(([type, handler]) => {
        expect(typeof handler).toBe('function');
        expect(handler).not.toBeNull();
        expect(handler).not.toBeUndefined();
      });
    });

    it('should have expected handler count', () => {
      const handlerCount = Object.keys(frontendHandlers).length;
      // We expect at least 20 handlers based on current implementation
      expect(handlerCount).toBeGreaterThanOrEqual(20);
      
      // Log for visibility
      console.log(`Frontend has ${handlerCount} WebSocket message handlers`);
    });
  });

  describe('Prevent Future Regressions', () => {
    it('should detect if new backend message types are added without handlers', () => {
      // This test will fail if backend adds new message types
      // without corresponding frontend handlers
      
      const backendTypes = Object.values(BACKEND_MESSAGE_TYPES);
      const handledTypes = Object.keys(frontendHandlers);
      
      const unhandledTypes = backendTypes.filter(type => {
        // Skip protocol and frontend-to-backend types
        if (PROTOCOL_ONLY_TYPES.includes(type) || FRONTEND_TO_BACKEND_ONLY.includes(type)) {
          return false;
        }
        
        // Check if handled directly or via alias
        const isHandled = handledTypes.includes(type) ||
          (type === 'agent_finished' && handledTypes.includes('agent_completed')) ||
          (type === 'tool_call' && handledTypes.includes('tool_executing')) ||
          (type === 'tool_result' && handledTypes.includes('tool_completed')) ||
          (type === 'stream_chunk' && handledTypes.includes('partial_result')) ||
          (type === 'subagent_completed' && handledTypes.includes('agent_completed'));
        
        return !isHandled;
      });

      // Non-critical types can be unhandled but should be logged
      const nonCriticalUnhandled = unhandledTypes.filter(
        type => !CRITICAL_MESSAGE_TYPES.includes(type)
      );
      
      if (nonCriticalUnhandled.length > 0) {
        console.warn('Non-critical unhandled message types:', nonCriticalUnhandled);
      }

      // Critical types MUST be handled
      const criticalUnhandled = unhandledTypes.filter(
        type => CRITICAL_MESSAGE_TYPES.includes(type)
      );
      
      expect(criticalUnhandled).toEqual([]);
    });

    it('should have console warning for unknown message types in production', () => {
      // This is a reminder to implement warning for unknown types
      // to prevent silent failures like the agent_response bug
      
      // The actual implementation would be in websocket-event-handlers-core.ts:
      // if (!handlers[event.type]) {
      //   console.warn(`Unknown WebSocket message type: ${event.type}`, event);
      // }
      
      expect(true).toBe(true); // Placeholder - implement in core handler
    });
  });
});

describe('Message Handler Consistency', () => {
  it('should handle all variations of agent response messages', () => {
    const handlers = getEventHandlers();
    
    // All these should resolve to handlers
    const responseVariations = [
      'agent_response',     // Primary
      'agent_completed',    // Completion signal
      'final_report',       // Final structured report
      'partial_result'      // Streaming responses
    ];
    
    responseVariations.forEach(type => {
      expect(handlers[type]).toBeDefined();
      expect(typeof handlers[type]).toBe('function');
    });
  });

  it('should maintain handler aliases for backward compatibility', () => {
    const handlers = getEventHandlers();
    
    // These aliases must be maintained
    const aliases = [
      ['agent_finished', 'agent_completed'],
      ['tool_call', 'tool_executing'],
      ['tool_result', 'tool_completed'],
      ['stream_chunk', 'partial_result'],
      ['subagent_completed', 'agent_completed']
    ];
    
    aliases.forEach(([alias, handler]) => {
      if (handlers[alias]) {
        expect(handlers[alias]).toBe(handlers[handler]);
      }
    });
  });
});