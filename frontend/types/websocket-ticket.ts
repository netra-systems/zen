/**
 * Type definitions for WebSocket ticket authentication
 * 
 * These types correspond to the backend implementation from Issue #1296 Phase 2
 * and provide type safety for the frontend ticket authentication system.
 */

/**
 * Request payload for ticket generation
 */
export interface TicketGenerationRequest {
  /** Time to live in seconds (30-3600, defaults to 300) */
  ttl_seconds?: number;
  /** Whether ticket is single-use (defaults to true) */
  single_use?: boolean;
  /** Custom permissions for ticket (optional) */
  permissions?: string[];
  /** Additional metadata for ticket (optional) */
  metadata?: Record<string, any>;
}

/**
 * Response from backend ticket generation endpoint
 */
export interface TicketGenerationResponse {
  /** Generated ticket ID */
  ticket_id: string;
  /** Expiration timestamp (Unix timestamp in seconds) */
  expires_at: number;
  /** Creation timestamp (Unix timestamp in seconds) */
  created_at: number;
  /** Time to live in seconds */
  ttl_seconds: number;
  /** Whether ticket is single-use */
  single_use: boolean;
  /** WebSocket URL with ticket parameter */
  websocket_url: string;
}

/**
 * Frontend WebSocket ticket representation
 */
export interface WebSocketTicket {
  /** Ticket ID for authentication */
  ticket: string;
  /** Expiration timestamp (Unix timestamp in milliseconds) */
  expires_at: number;
  /** Creation timestamp (Unix timestamp in milliseconds) */
  created_at?: number;
  /** Pre-constructed WebSocket URL with ticket parameter */
  websocket_url?: string;
}

/**
 * Result of ticket request operation
 */
export interface TicketRequestResult {
  /** Whether the operation was successful */
  success: boolean;
  /** The acquired ticket if successful */
  ticket?: WebSocketTicket;
  /** Error message if unsuccessful */
  error?: string;
  /** Whether the error is recoverable (should retry) */
  recoverable?: boolean;
}

/**
 * Error information for ticket operations
 */
export interface TicketError {
  /** Human-readable error message */
  message: string;
  /** Error code for programmatic handling */
  code?: string;
  /** Whether this error is recoverable with retry */
  recoverable: boolean;
  /** Original error for debugging */
  originalError?: unknown;
}

/**
 * Configuration for ticket authentication
 */
export interface TicketAuthConfig {
  /** Whether ticket authentication is enabled */
  enabled: boolean;
  /** Default TTL for tickets in seconds */
  defaultTtl: number;
  /** Refresh threshold in milliseconds (refresh tickets before expiry) */
  refreshThreshold: number;
  /** Maximum retry attempts for ticket acquisition */
  maxRetries: number;
  /** Base delay for exponential backoff in milliseconds */
  retryDelay: number;
}

/**
 * Ticket validation response from backend
 */
export interface TicketValidationResponse {
  /** Whether ticket is valid */
  valid: boolean;
  /** User ID if valid */
  user_id?: string;
  /** User email if valid */
  email?: string;
  /** User permissions if valid */
  permissions?: string[];
  /** Expiration timestamp if valid */
  expires_at?: number;
  /** Error message if invalid */
  error?: string;
}

/**
 * Cache entry for storing tickets
 */
export interface TicketCacheEntry {
  /** The ticket data */
  ticket: WebSocketTicket;
  /** Cache timestamp for cleanup */
  cachedAt: number;
  /** User context for multi-user scenarios */
  userId?: string;
}