'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useTicketAuth, TicketAuthData } from '../../auth/providers/ticket-auth-provider';

export interface WebSocketTicketAuthConfig {
  websocketUrl: string;
  userId: string;
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectDelay?: number;
  ticketRefreshThreshold?: number; // Minutes before expiry to refresh
}

export interface WebSocketTicketAuthState {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  lastConnectTime: Date | null;
  connectionAttempts: number;
  currentTicket: TicketAuthData | null;
}

export interface UseWebSocketTicketAuthReturn {
  // Connection state
  state: WebSocketTicketAuthState;
  
  // Connection controls
  connect: () => Promise<boolean>;
  disconnect: () => void;
  reconnect: () => Promise<boolean>;
  
  // Message handling
  sendMessage: (message: any) => boolean;
  
  // Event handlers
  onMessage: (callback: (data: any) => void) => () => void;
  onConnect: (callback: () => void) => () => void;
  onDisconnect: (callback: (reason: string) => void) => () => void;
  onError: (callback: (error: string) => void) => () => void;
  
  // Ticket management
  refreshTicketAndReconnect: () => Promise<boolean>;
  
  // Cleanup
  clearError: () => void;
}

export function useWebSocketTicketAuth(config: WebSocketTicketAuthConfig): UseWebSocketTicketAuthReturn {
  const {
    websocketUrl,
    userId,
    autoConnect = true,
    reconnectAttempts = 3,
    reconnectDelay = 1000,
    ticketRefreshThreshold = 5
  } = config;

  const {
    generateTicket,
    refreshTicket,
    currentTicket: contextTicket,
    isTicketValid: contextTicketValid,
    isLoading: ticketLoading
  } = useTicketAuth();

  // WebSocket state
  const [state, setState] = useState<WebSocketTicketAuthState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    lastConnectTime: null,
    connectionAttempts: 0,
    currentTicket: null
  });

  // Refs for persistent data
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const eventHandlersRef = useRef({
    onMessage: new Set<(data: any) => void>(),
    onConnect: new Set<() => void>(),
    onDisconnect: new Set<(reason: string) => void>(),
    onError: new Set<(error: string) => void>()
  });

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  const updateState = useCallback((updates: Partial<WebSocketTicketAuthState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  const emitEvent = useCallback((eventType: keyof typeof eventHandlersRef.current, ...args: any[]) => {
    eventHandlersRef.current[eventType].forEach(handler => {
      try {
        handler(...args);
      } catch (error) {
        console.error(`Error in ${eventType} handler:`, error);
      }
    });
  }, []);

  const generateNewTicket = useCallback(async (): Promise<TicketAuthData | null> => {
    if (!userId) {
      updateState({ error: 'User ID is required for ticket generation' });
      return null;
    }

    try {
      const ticket = await generateTicket(userId, ['websocket']);
      if (ticket) {
        updateState({ currentTicket: ticket, error: null });
        return ticket;
      } else {
        updateState({ error: 'Failed to generate authentication ticket' });
        return null;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error generating ticket';
      updateState({ error: errorMessage });
      return null;
    }
  }, [userId, generateTicket, updateState]);

  const getValidTicket = useCallback(async (): Promise<TicketAuthData | null> => {
    // Check if we have a valid ticket in context
    if (contextTicket && contextTicketValid) {
      updateState({ currentTicket: contextTicket });
      return contextTicket;
    }

    // Check if we have a valid ticket in local state
    if (state.currentTicket && new Date() < state.currentTicket.expires) {
      return state.currentTicket;
    }

    // Generate new ticket
    return await generateNewTicket();
  }, [contextTicket, contextTicketValid, state.currentTicket, generateNewTicket, updateState]);

  const connectWebSocket = useCallback(async (ticket: TicketAuthData): Promise<boolean> => {
    return new Promise((resolve) => {
      try {
        const wsUrl = `${websocketUrl}?ticket=${encodeURIComponent(ticket.ticketId)}&userId=${encodeURIComponent(ticket.userId)}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          wsRef.current = ws;
          updateState({
            isConnected: true,
            isConnecting: false,
            error: null,
            lastConnectTime: new Date(),
            connectionAttempts: 0
          });
          emitEvent('onConnect');
          resolve(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            emitEvent('onMessage', data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
            emitEvent('onMessage', { type: 'raw', data: event.data });
          }
        };

        ws.onclose = (event) => {
          wsRef.current = null;
          const reason = event.reason || `Connection closed (code: ${event.code})`;
          updateState({
            isConnected: false,
            isConnecting: false,
            error: reason
          });
          emitEvent('onDisconnect', reason);
          resolve(false);
        };

        ws.onerror = (error) => {
          const errorMessage = 'WebSocket connection error';
          updateState({
            isConnected: false,
            isConnecting: false,
            error: errorMessage
          });
          emitEvent('onError', errorMessage);
          resolve(false);
        };

        // Set connecting state
        updateState({ isConnecting: true, error: null });

      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to create WebSocket connection';
        updateState({
          isConnecting: false,
          error: errorMessage
        });
        emitEvent('onError', errorMessage);
        resolve(false);
      }
    });
  }, [websocketUrl, updateState, emitEvent]);

  const connect = useCallback(async (): Promise<boolean> => {
    if (state.isConnecting || state.isConnected) {
      return state.isConnected;
    }

    if (ticketLoading) {
      updateState({ error: 'Ticket generation in progress, please wait' });
      return false;
    }

    const ticket = await getValidTicket();
    if (!ticket) {
      updateState({ error: 'Unable to obtain valid authentication ticket' });
      return false;
    }

    const connected = await connectWebSocket(ticket);
    
    if (!connected && state.connectionAttempts < reconnectAttempts) {
      // Schedule reconnect
      updateState({ connectionAttempts: state.connectionAttempts + 1 });
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, reconnectDelay * Math.pow(2, state.connectionAttempts)); // Exponential backoff
    }

    return connected;
  }, [
    state.isConnecting,
    state.isConnected,
    state.connectionAttempts,
    ticketLoading,
    getValidTicket,
    connectWebSocket,
    reconnectAttempts,
    reconnectDelay,
    updateState
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'User requested disconnect');
      wsRef.current = null;
    }

    updateState({
      isConnected: false,
      isConnecting: false,
      connectionAttempts: 0
    });
  }, [updateState]);

  const reconnect = useCallback(async (): Promise<boolean> => {
    disconnect();
    return await connect();
  }, [disconnect, connect]);

  const sendMessage = useCallback((message: any): boolean => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      updateState({ error: 'WebSocket is not connected' });
      return false;
    }

    try {
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
      wsRef.current.send(messageStr);
      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      updateState({ error: errorMessage });
      emitEvent('onError', errorMessage);
      return false;
    }
  }, [updateState, emitEvent]);

  const refreshTicketAndReconnect = useCallback(async (): Promise<boolean> => {
    if (!state.currentTicket) {
      return await connect();
    }

    try {
      const refreshedTicket = await refreshTicket(state.currentTicket.ticketId);
      if (refreshedTicket) {
        updateState({ currentTicket: refreshedTicket });
        return await reconnect();
      } else {
        // Refresh failed, try generating new ticket
        return await connect();
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to refresh ticket';
      updateState({ error: errorMessage });
      return false;
    }
  }, [state.currentTicket, refreshTicket, updateState, reconnect, connect]);

  // Event handler registration functions
  const onMessage = useCallback((callback: (data: any) => void) => {
    eventHandlersRef.current.onMessage.add(callback);
    return () => eventHandlersRef.current.onMessage.delete(callback);
  }, []);

  const onConnect = useCallback((callback: () => void) => {
    eventHandlersRef.current.onConnect.add(callback);
    return () => eventHandlersRef.current.onConnect.delete(callback);
  }, []);

  const onDisconnect = useCallback((callback: (reason: string) => void) => {
    eventHandlersRef.current.onDisconnect.add(callback);
    return () => eventHandlersRef.current.onDisconnect.delete(callback);
  }, []);

  const onError = useCallback((callback: (error: string) => void) => {
    eventHandlersRef.current.onError.add(callback);
    return () => eventHandlersRef.current.onError.delete(callback);
  }, []);

  // Auto-connect effect
  useEffect(() => {
    if (autoConnect && userId && !state.isConnected && !state.isConnecting) {
      connect();
    }
  }, [autoConnect, userId, state.isConnected, state.isConnecting, connect]);

  // Cleanup effect
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Auto-refresh ticket before expiry
  useEffect(() => {
    if (!state.currentTicket) return;

    const checkTicketExpiry = () => {
      const now = new Date();
      const timeUntilExpiry = state.currentTicket!.expires.getTime() - now.getTime();
      const thresholdMs = ticketRefreshThreshold * 60 * 1000;

      if (timeUntilExpiry <= thresholdMs && timeUntilExpiry > 0) {
        refreshTicketAndReconnect();
      }
    };

    // Check immediately
    checkTicketExpiry();

    // Set up interval to check every minute
    const interval = setInterval(checkTicketExpiry, 60000);

    return () => clearInterval(interval);
  }, [state.currentTicket, ticketRefreshThreshold, refreshTicketAndReconnect]);

  return {
    state,
    connect,
    disconnect,
    reconnect,
    sendMessage,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    refreshTicketAndReconnect,
    clearError
  };
}