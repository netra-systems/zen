import { TicketAuthData, TicketAuthError } from '../providers/ticket-auth-provider';

/**
 * Utility functions for ticket-based authentication
 * Provides helper functions for ticket validation, formatting, and management
 */

export interface TicketValidationResult {
  isValid: boolean;
  reason?: string;
  timeUntilExpiry?: number; // milliseconds
}

export interface TicketPermissionCheck {
  hasPermission: boolean;
  missingPermissions: string[];
}

export interface TicketCacheEntry {
  ticket: TicketAuthData;
  cachedAt: Date;
  lastValidated: Date;
}

/**
 * Validates if a ticket is currently valid
 */
export function validateTicketLocally(ticket: TicketAuthData | null): TicketValidationResult {
  if (!ticket) {
    return {
      isValid: false,
      reason: 'No ticket provided'
    };
  }

  const now = new Date();
  const expiryTime = new Date(ticket.expires);

  if (now >= expiryTime) {
    return {
      isValid: false,
      reason: 'Ticket has expired',
      timeUntilExpiry: 0
    };
  }

  const timeUntilExpiry = expiryTime.getTime() - now.getTime();

  return {
    isValid: true,
    timeUntilExpiry
  };
}

/**
 * Checks if a ticket has specific permissions
 */
export function checkTicketPermissions(
  ticket: TicketAuthData | null,
  requiredPermissions: string[]
): TicketPermissionCheck {
  if (!ticket) {
    return {
      hasPermission: false,
      missingPermissions: requiredPermissions
    };
  }

  if (!requiredPermissions.length) {
    return {
      hasPermission: true,
      missingPermissions: []
    };
  }

  const ticketPermissions = ticket.permissions || [];
  const missingPermissions = requiredPermissions.filter(
    permission => !ticketPermissions.includes(permission)
  );

  return {
    hasPermission: missingPermissions.length === 0,
    missingPermissions
  };
}

/**
 * Formats time until ticket expiry in human-readable format
 */
export function formatTimeUntilExpiry(ticket: TicketAuthData | null): string {
  if (!ticket) {
    return 'No ticket';
  }

  const validation = validateTicketLocally(ticket);
  
  if (!validation.isValid) {
    return validation.reason || 'Invalid ticket';
  }

  const timeMs = validation.timeUntilExpiry || 0;
  const totalMinutes = Math.floor(timeMs / (1000 * 60));
  
  if (totalMinutes < 1) {
    return 'Less than 1 minute';
  }
  
  if (totalMinutes < 60) {
    return `${totalMinutes} minute${totalMinutes === 1 ? '' : 's'}`;
  }
  
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  
  if (hours < 24) {
    return minutes > 0 
      ? `${hours}h ${minutes}m`
      : `${hours} hour${hours === 1 ? '' : 's'}`;
  }
  
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;
  
  return remainingHours > 0
    ? `${days}d ${remainingHours}h`
    : `${days} day${days === 1 ? '' : 's'}`;
}

/**
 * Determines if a ticket should be refreshed based on time remaining
 */
export function shouldRefreshTicket(
  ticket: TicketAuthData | null,
  refreshThresholdMinutes: number = 5
): boolean {
  if (!ticket) {
    return true; // Should get a new ticket
  }

  const validation = validateTicketLocally(ticket);
  
  if (!validation.isValid) {
    return true; // Should refresh expired/invalid ticket
  }

  const timeUntilExpiryMs = validation.timeUntilExpiry || 0;
  const thresholdMs = refreshThresholdMinutes * 60 * 1000;

  return timeUntilExpiryMs <= thresholdMs;
}

/**
 * Creates a secure storage key for ticket caching
 */
export function createTicketStorageKey(userId: string): string {
  if (!userId?.trim()) {
    throw new Error('User ID is required for ticket storage key');
  }
  
  return `netra_ticket_${userId.replace(/[^a-zA-Z0-9]/g, '_')}`;
}

/**
 * Safely stores ticket data in session storage
 */
export function storeTicketSecurely(ticket: TicketAuthData): boolean {
  try {
    if (typeof window === 'undefined' || !window.sessionStorage) {
      return false; // Not in browser environment
    }

    const storageKey = createTicketStorageKey(ticket.userId);
    const cacheEntry: TicketCacheEntry = {
      ticket,
      cachedAt: new Date(),
      lastValidated: new Date()
    };

    sessionStorage.setItem(storageKey, JSON.stringify(cacheEntry));
    return true;
  } catch (error) {
    console.warn('Failed to store ticket securely:', error);
    return false;
  }
}

/**
 * Safely retrieves ticket data from session storage
 */
export function retrieveStoredTicket(userId: string): TicketAuthData | null {
  try {
    if (typeof window === 'undefined' || !window.sessionStorage) {
      return null; // Not in browser environment
    }

    const storageKey = createTicketStorageKey(userId);
    const stored = sessionStorage.getItem(storageKey);
    
    if (!stored) {
      return null;
    }

    const cacheEntry: TicketCacheEntry = JSON.parse(stored);
    
    // Convert string dates back to Date objects
    const ticket: TicketAuthData = {
      ...cacheEntry.ticket,
      expires: new Date(cacheEntry.ticket.expires)
    };

    // Validate the stored ticket
    const validation = validateTicketLocally(ticket);
    if (!validation.isValid) {
      // Remove invalid ticket from storage
      clearStoredTicket(userId);
      return null;
    }

    return ticket;
  } catch (error) {
    console.warn('Failed to retrieve stored ticket:', error);
    return null;
  }
}

/**
 * Clears stored ticket from session storage
 */
export function clearStoredTicket(userId: string): boolean {
  try {
    if (typeof window === 'undefined' || !window.sessionStorage) {
      return false; // Not in browser environment
    }

    const storageKey = createTicketStorageKey(userId);
    sessionStorage.removeItem(storageKey);
    return true;
  } catch (error) {
    console.warn('Failed to clear stored ticket:', error);
    return false;
  }
}

/**
 * Clears all stored tickets (useful for logout)
 */
export function clearAllStoredTickets(): boolean {
  try {
    if (typeof window === 'undefined' || !window.sessionStorage) {
      return false; // Not in browser environment
    }

    const keysToRemove: string[] = [];
    
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key && key.startsWith('netra_ticket_')) {
        keysToRemove.push(key);
      }
    }

    keysToRemove.forEach(key => sessionStorage.removeItem(key));
    return true;
  } catch (error) {
    console.warn('Failed to clear all stored tickets:', error);
    return false;
  }
}

/**
 * Sanitizes error messages to remove sensitive information
 */
export function sanitizeTicketError(error: TicketAuthError | Error | string): string {
  let message: string;
  
  if (typeof error === 'string') {
    message = error;
  } else if (error instanceof Error) {
    message = error.message;
  } else {
    message = error.message;
  }

  // Remove potentially sensitive information
  const sanitized = message
    .replace(/ticketId=[^&\s]*/gi, 'ticketId=***')
    .replace(/userId=[^&\s]*/gi, 'userId=***')
    .replace(/token=[^&\s]*/gi, 'token=***')
    .replace(/secret=[^&\s]*/gi, 'secret=***')
    .replace(/password=[^&\s]*/gi, 'password=***');

  return sanitized;
}

/**
 * Creates a ticket authentication error with consistent structure
 */
export function createTicketAuthError(
  code: string,
  message: string,
  originalError?: Error
): TicketAuthError {
  return {
    code,
    message: sanitizeTicketError(message),
    timestamp: new Date(),
    ...(originalError && { originalError: originalError.message })
  };
}

/**
 * Validates WebSocket URL format for ticket authentication
 */
export function validateWebSocketUrl(url: string): { isValid: boolean; reason?: string } {
  if (!url?.trim()) {
    return { isValid: false, reason: 'WebSocket URL is required' };
  }

  try {
    const urlObj = new URL(url);
    
    if (!['ws:', 'wss:'].includes(urlObj.protocol)) {
      return { isValid: false, reason: 'WebSocket URL must use ws:// or wss:// protocol' };
    }

    return { isValid: true };
  } catch (error) {
    return { isValid: false, reason: 'Invalid WebSocket URL format' };
  }
}

/**
 * Builds WebSocket URL with ticket authentication parameters
 */
export function buildTicketWebSocketUrl(
  baseUrl: string,
  ticket: TicketAuthData,
  additionalParams?: Record<string, string>
): string {
  const validation = validateWebSocketUrl(baseUrl);
  if (!validation.isValid) {
    throw new Error(validation.reason);
  }

  const url = new URL(baseUrl);
  
  // Add ticket authentication parameters
  url.searchParams.set('ticket', ticket.ticketId);
  url.searchParams.set('userId', ticket.userId);
  
  // Add any additional parameters
  if (additionalParams) {
    Object.entries(additionalParams).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
  }

  return url.toString();
}

/**
 * Extracts ticket information from WebSocket URL
 */
export function extractTicketFromWebSocketUrl(url: string): { ticketId?: string; userId?: string } {
  try {
    const urlObj = new URL(url);
    return {
      ticketId: urlObj.searchParams.get('ticket') || undefined,
      userId: urlObj.searchParams.get('userId') || undefined
    };
  } catch (error) {
    return {};
  }
}