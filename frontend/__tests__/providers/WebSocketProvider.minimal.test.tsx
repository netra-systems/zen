/**
 * Minimal test to isolate useState WebSocketStatus behavior
 */

import React, { useState } from 'react';
import { render } from '@testing-library/react';

// Import the exact type used in WebSocketProvider
import { WebSocketStatus } from '../../services/webSocketService';

// Minimal component that just tests useState with WebSocketStatus
const MinimalStatusTest = () => {
  const [status, setStatus] = useState<WebSocketStatus>('CLOSED');
  console.log('🎯 useState WebSocketStatus initialized to:', status);
  
  return <div data-testid="status">{status}</div>;
};

// Even more minimal - hardcode the type
const HardcodedStatusTest = () => {
  const [status] = useState<'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED'>('CLOSED');
  console.log('🔥 Hardcoded type useState initialized to:', status);
  
  return <div data-testid="hardcoded-status">{status}</div>;
};

describe('WebSocketStatus useState Debugging', () => {
  beforeEach(() => {
    // Reset global auth mock to be safe
    (global as any).mockAuthState = {
      token: null,
      initialized: false,
      user: null,
      loading: false,
      error: null,
      isAuthenticated: false,
      authConfig: {},
      login: jest.fn(),
      logout: jest.fn()
    };
  });

  it('should test WebSocketStatus type in useState', () => {
    console.log('🧪 Testing WebSocketStatus type behavior...');
    
    const { container } = render(<MinimalStatusTest />);
    
    const statusElement = container.querySelector('[data-testid="status"]');
    console.log('📊 MinimalStatusTest result:', statusElement?.textContent);
    
    expect(statusElement?.textContent).toBe('CLOSED');
  });

  it('should test hardcoded union type in useState', () => {
    console.log('🔧 Testing hardcoded union type behavior...');
    
    const { container } = render(<HardcodedStatusTest />);
    
    const statusElement = container.querySelector('[data-testid="hardcoded-status"]');
    console.log('📈 HardcodedStatusTest result:', statusElement?.textContent);
    
    expect(statusElement?.textContent).toBe('CLOSED');
  });
});