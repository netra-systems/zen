/**
 * State Verification Utilities
 * Async operations and component state verification with 8-line function limit enforcement
 */

import { waitFor, screen } from '@testing-library/react';

// Types for state verification
export interface AuthStateExpectation {
  isAuthenticated: boolean;
  userEmail?: string;
  token?: string;
  hasError?: boolean;
}

export interface WebSocketStateExpectation {
  isConnected: boolean;
  connectionState?: string;
  messageCount?: number;
  hasError?: boolean;
}

export interface ChatStateExpectation {
  messageCount: number;
  threadCount?: number;
  isProcessing?: boolean;
  lastMessage?: string;
}

export interface ComponentStateExpectation {
  isLoading?: boolean;
  hasError?: boolean;
  errorMessage?: string;
  isVisible?: boolean;
}

// Authentication state verification
export const verifyAuthenticatedState = async (expectation: AuthStateExpectation) => {
  if (expectation.isAuthenticated) {
    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent(/logged in/i);
    });
  }
  
  if (expectation.userEmail) {
    await waitFor(() => {
      expect(screen.getByTestId('user-email')).toHaveTextContent(expectation.userEmail!);
    });
  }
};

export const verifyUnauthenticatedState = async () => {
  await waitFor(() => {
    expect(screen.getByTestId('auth-status')).toHaveTextContent(/not logged in/i);
  });
  
  await waitFor(() => {
    expect(screen.queryByTestId('user-email')).not.toBeInTheDocument();
  });
};

export const verifyAuthError = async (errorMessage?: string) => {
  await waitFor(() => {
    expect(screen.getByTestId('auth-error')).toBeInTheDocument();
  });
  
  if (errorMessage) {
    await waitFor(() => {
      expect(screen.getByTestId('auth-error')).toHaveTextContent(errorMessage);
    });
  }
};

export const verifyTokenPersistence = async (expectedToken: string) => {
  await waitFor(() => {
    expect(localStorage.getItem('jwt_token')).toBe(expectedToken);
  });
};

// WebSocket state verification
export const verifyWebSocketConnected = async () => {
  await waitFor(() => {
    expect(screen.getByTestId('ws-connected')).toHaveTextContent('true');
  });
  
  await waitFor(() => {
    expect(screen.getByTestId('ws-disconnected')).toHaveTextContent('false');
  });
};

export const verifyWebSocketDisconnected = async () => {
  await waitFor(() => {
    expect(screen.getByTestId('ws-connected')).toHaveTextContent('false');
  });
  
  await waitFor(() => {
    expect(screen.getByTestId('ws-disconnected')).toHaveTextContent('true');
  });
};

export const verifyWebSocketReconnecting = async () => {
  await waitFor(() => {
    expect(screen.getByTestId('ws-reconnecting')).toHaveTextContent('true');
  });
};

export const verifyWebSocketError = async () => {
  await waitFor(() => {
    expect(screen.getByTestId('ws-error')).toHaveTextContent('true');
  });
};

export const verifyWebSocketMetrics = async (expectation: WebSocketStateExpectation) => {
  if (expectation.messageCount !== undefined) {
    await waitFor(() => {
      expect(screen.getByTestId('metrics-sent')).toHaveTextContent(expectation.messageCount!.toString());
    });
  }
};

// Chat state verification
export const verifyChatMessageCount = async (expectedCount: number) => {
  await waitFor(() => {
    const messageElements = screen.getAllByTestId(/message-\d+/);
    expect(messageElements).toHaveLength(expectedCount);
  });
};

export const verifyLatestMessage = async (expectedText: string) => {
  await waitFor(() => {
    expect(screen.getByTestId('latest-message')).toHaveTextContent(expectedText);
  });
};

export const verifyThreadCreated = async (threadTitle: string) => {
  await waitFor(() => {
    expect(screen.getByTestId('thread-list')).toHaveTextContent(threadTitle);
  });
};

export const verifyCurrentThread = async (threadId: string) => {
  await waitFor(() => {
    expect(screen.getByTestId('current-thread-id')).toHaveTextContent(threadId);
  });
};

export const verifyChatProcessing = async (isProcessing: boolean) => {
  if (isProcessing) {
    await waitFor(() => {
      expect(screen.getByTestId('chat-processing')).toHaveTextContent('true');
    });
  } else {
    await waitFor(() => {
      expect(screen.getByTestId('chat-processing')).toHaveTextContent('false');
    });
  }
};

// Component state verification
export const verifyLoadingState = async (isLoading: boolean, testId: string = 'loading-indicator') => {
  if (isLoading) {
    await waitFor(() => {
      expect(screen.getByTestId(testId)).toBeInTheDocument();
    });
  } else {
    await waitFor(() => {
      expect(screen.queryByTestId(testId)).not.toBeInTheDocument();
    });
  }
};

export const verifyErrorState = async (hasError: boolean, errorMessage?: string, testId: string = 'error-message') => {
  if (hasError) {
    await waitFor(() => {
      expect(screen.getByTestId(testId)).toBeInTheDocument();
    });
    
    if (errorMessage) {
      await waitFor(() => {
        expect(screen.getByTestId(testId)).toHaveTextContent(errorMessage);
      });
    }
  }
};

export const verifyComponentVisibility = async (isVisible: boolean, testId: string) => {
  if (isVisible) {
    await waitFor(() => {
      expect(screen.getByTestId(testId)).toBeInTheDocument();
    });
  } else {
    await waitFor(() => {
      expect(screen.queryByTestId(testId)).not.toBeInTheDocument();
    });
  }
};

// Store state verification utilities
export const verifyStoreState = async (mockStore: any, key: string, expectedValue: any) => {
  await waitFor(() => {
    const state = mockStore.getState();
    expect(state[key]).toEqual(expectedValue);
  });
};

export const verifyStoreCall = async (mockFunction: jest.Mock, expectedArgs?: any[]) => {
  await waitFor(() => {
    expect(mockFunction).toHaveBeenCalled();
  });
  
  if (expectedArgs) {
    await waitFor(() => {
      expect(mockFunction).toHaveBeenCalledWith(...expectedArgs);
    });
  }
};