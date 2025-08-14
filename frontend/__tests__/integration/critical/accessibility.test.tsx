/**
 * Accessibility Integration Tests
 * Tests for focus management and screen reader support
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import test utilities
import { TestProviders } from '../../test-utils/providers';

describe('Accessibility Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Focus Management', () => {
    it('should maintain focus management during navigation', async () => {
      const TestComponent = () => {
        const [currentView, setCurrentView] = React.useState('chat');
        const chatRef = React.useRef<HTMLDivElement>(null);
        const settingsRef = React.useRef<HTMLDivElement>(null);
        
        React.useEffect(() => {
          if (currentView === 'chat' && chatRef.current) {
            chatRef.current.focus();
          } else if (currentView === 'settings' && settingsRef.current) {
            settingsRef.current.focus();
          }
        }, [currentView]);
        
        return (
          <div>
            <button onClick={() => setCurrentView('chat')}>Chat</button>
            <button onClick={() => setCurrentView('settings')}>Settings</button>
            <div ref={chatRef} tabIndex={-1} data-testid="chat-view">
              Chat View
            </div>
            <div ref={settingsRef} tabIndex={-1} data-testid="settings-view">
              Settings View
            </div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Settings'));
      
      await waitFor(() => {
        expect(document.activeElement).toBe(getByTestId('settings-view'));
      });
    });

    it('should announce dynamic content updates to screen readers', async () => {
      const TestComponent = () => {
        const [message, setMessage] = React.useState('');
        
        return (
          <div>
            <button onClick={() => setMessage('New message received')}>
              Trigger Update
            </button>
            <div aria-live="polite" aria-atomic="true" data-testid="announcer">
              {message}
            </div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<TestComponent />);
      
      fireEvent.click(getByText('Trigger Update'));
      
      const announcer = getByTestId('announcer');
      expect(announcer).toHaveTextContent('New message received');
      expect(announcer).toHaveAttribute('aria-live', 'polite');
    });
  });
});