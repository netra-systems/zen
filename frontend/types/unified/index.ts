/**
 * UNIFIED TYPES - Central Export Hub
 * 
 * This is the SINGLE SOURCE OF TRUTH for ALL frontend types.
 * All components, hooks, stores, and services should import from here.
 * 
 * CRITICAL RULES:
 * - Import from '@/types/unified' ONLY
 * - Never import scattered type files directly
 * - Each type exists ONCE and ONLY ONCE
 * - Report any duplicate type discoveries immediately
 * 
 * USAGE:
 * ```typescript
 * import { WebSocketMessage, Token, ToolCompleted, AgentStatus } from '@/types/unified';
 * ```
 */

// ============================================================================
// WEBSOCKET TYPES
// ============================================================================
export * from './websocket.types';

// ============================================================================
// AUTHENTICATION TYPES  
// ============================================================================
export * from './auth.types';

// ============================================================================
// TOOL TYPES
// ============================================================================
export * from './tool.types';

// ============================================================================
// METRICS TYPES
// ============================================================================
export * from './metrics.types';

// ============================================================================
// AGENT TYPES
// ============================================================================
export * from './agent.types';