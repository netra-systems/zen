'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export interface TicketAuthData {
  ticketId: string;
  userId: string;
  expires: Date;
  permissions: string[];
}

export interface TicketAuthError {
  code: string;
  message: string;
  timestamp: Date;
}

export interface TicketAuthContextType {
  // Core ticket operations
  generateTicket: (userId: string, permissions?: string[]) => Promise<TicketAuthData | null>;
  validateTicket: (ticketId: string) => Promise<boolean>;
  refreshTicket: (ticketId: string) => Promise<TicketAuthData | null>;
  revokeTicket: (ticketId: string) => Promise<boolean>;
  
  // State management
  currentTicket: TicketAuthData | null;
  isTicketValid: boolean;
  isLoading: boolean;
  error: TicketAuthError | null;
  
  // Utility functions
  clearError: () => void;
  clearTicket: () => void;
}

const TicketAuthContext = createContext<TicketAuthContextType | undefined>(undefined);

export interface TicketAuthProviderProps {
  children: React.ReactNode;
  apiBaseUrl?: string;
  enableAutoRefresh?: boolean;
  refreshThreshold?: number; // Minutes before expiry to auto-refresh
}

export function TicketAuthProvider({ 
  children, 
  apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  enableAutoRefresh = true,
  refreshThreshold = 5 
}: TicketAuthProviderProps) {
  const [currentTicket, setCurrentTicket] = useState<TicketAuthData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<TicketAuthError | null>(null);

  // Calculate if current ticket is valid (exists and not expired)
  const isTicketValid = currentTicket ? new Date() < currentTicket.expires : false;

  const createError = (code: string, message: string): TicketAuthError => ({
    code,
    message,
    timestamp: new Date()
  });

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const clearTicket = useCallback(() => {
    setCurrentTicket(null);
    setError(null);
  }, []);

  const generateTicket = useCallback(async (
    userId: string, 
    permissions: string[] = []
  ): Promise<TicketAuthData | null> => {
    if (!userId?.trim()) {
      const err = createError('INVALID_USER_ID', 'User ID is required');
      setError(err);
      return null;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/tickets/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ userId, permissions }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const ticketData: TicketAuthData = {
        ticketId: data.ticketId,
        userId: data.userId,
        expires: new Date(data.expires),
        permissions: data.permissions || permissions
      };

      setCurrentTicket(ticketData);
      return ticketData;

    } catch (err) {
      const error = createError(
        'GENERATION_FAILED', 
        err instanceof Error ? err.message : 'Failed to generate ticket'
      );
      setError(error);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl]);

  const validateTicket = useCallback(async (ticketId: string): Promise<boolean> => {
    if (!ticketId?.trim()) {
      setError(createError('INVALID_TICKET_ID', 'Ticket ID is required'));
      return false;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/tickets/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ticketId }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data.valid === true;

    } catch (err) {
      const error = createError(
        'VALIDATION_FAILED', 
        err instanceof Error ? err.message : 'Failed to validate ticket'
      );
      setError(error);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl]);

  const refreshTicket = useCallback(async (ticketId: string): Promise<TicketAuthData | null> => {
    if (!ticketId?.trim()) {
      setError(createError('INVALID_TICKET_ID', 'Ticket ID is required'));
      return null;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/tickets/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ticketId }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const refreshedTicket: TicketAuthData = {
        ticketId: data.ticketId,
        userId: data.userId,
        expires: new Date(data.expires),
        permissions: data.permissions || []
      };

      setCurrentTicket(refreshedTicket);
      return refreshedTicket;

    } catch (err) {
      const error = createError(
        'REFRESH_FAILED', 
        err instanceof Error ? err.message : 'Failed to refresh ticket'
      );
      setError(error);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl]);

  const revokeTicket = useCallback(async (ticketId: string): Promise<boolean> => {
    if (!ticketId?.trim()) {
      setError(createError('INVALID_TICKET_ID', 'Ticket ID is required'));
      return false;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/auth/tickets/revoke`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ticketId }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Clear current ticket if it matches the revoked one
      if (currentTicket?.ticketId === ticketId) {
        setCurrentTicket(null);
      }

      return true;

    } catch (err) {
      const error = createError(
        'REVOCATION_FAILED', 
        err instanceof Error ? err.message : 'Failed to revoke ticket'
      );
      setError(error);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl, currentTicket?.ticketId]);

  // Auto-refresh logic
  useEffect(() => {
    if (!enableAutoRefresh || !currentTicket || !isTicketValid) {
      return;
    }

    const checkRefresh = () => {
      const now = new Date();
      const timeUntilExpiry = currentTicket.expires.getTime() - now.getTime();
      const thresholdMs = refreshThreshold * 60 * 1000; // Convert minutes to ms

      if (timeUntilExpiry <= thresholdMs && timeUntilExpiry > 0) {
        // Ticket is within refresh threshold
        refreshTicket(currentTicket.ticketId);
      }
    };

    // Check immediately
    checkRefresh();

    // Set up interval to check every minute
    const interval = setInterval(checkRefresh, 60000);

    return () => clearInterval(interval);
  }, [currentTicket, enableAutoRefresh, refreshThreshold, refreshTicket, isTicketValid]);

  const contextValue: TicketAuthContextType = {
    generateTicket,
    validateTicket,
    refreshTicket,
    revokeTicket,
    currentTicket,
    isTicketValid,
    isLoading,
    error,
    clearError,
    clearTicket
  };

  return (
    <TicketAuthContext.Provider value={contextValue}>
      {children}
    </TicketAuthContext.Provider>
  );
}

export function useTicketAuth(): TicketAuthContextType {
  const context = useContext(TicketAuthContext);
  if (context === undefined) {
    throw new Error('useTicketAuth must be used within a TicketAuthProvider');
  }
  return context;
}

export default TicketAuthProvider;