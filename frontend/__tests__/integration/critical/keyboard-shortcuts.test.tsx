/**
 * Keyboard Shortcuts Integration Tests
 * Tests for global keyboard shortcuts and input field handling
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import test utilities
import { TestProviders } from '@/__tests__/setup/test-providers';

describe('Keyboard Shortcuts Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Global Shortcuts', () => {
    it('should handle global keyboard shortcuts', async () => {
      const shortcuts = new Map([
        ['cmd+k', 'openSearch'],
        ['cmd+enter', 'sendMessage'],
        ['esc', 'closeModal']
      ]);
      
      const TestComponent = () => {
        const [lastAction, setLastAction] = React.useState('');
        
        React.useEffect(() => {
          const handleKeydown = (e: KeyboardEvent) => {
            const key = `${e.metaKey ? 'cmd+' : ''}${e.key}`;
            const action = shortcuts.get(key);
            if (action) {
              e.preventDefault();
              setLastAction(action);
            }
          };
          
          window.addEventListener('keydown', handleKeydown);
          return () => window.removeEventListener('keydown', handleKeydown);
        }, []);
        
        return <div data-testid="action">{lastAction}</div>;
      };
      
      const { getByTestId } = render(<TestComponent />);
      
      // Simulate Cmd+K
      fireEvent.keyDown(window, { key: 'k', metaKey: true });
      
      expect(getByTestId('action')).toHaveTextContent('openSearch');
    });

    it('should prevent shortcut conflicts in input fields', async () => {
      let actionTriggered = false;
      
      const TestComponent = () => {
        React.useEffect(() => {
          const handleKeydown = (e: KeyboardEvent) => {
            if (e.target instanceof HTMLInputElement) {
              return; // Don't trigger shortcuts in input fields
            }
            if (e.key === 'Enter') {
              actionTriggered = true;
            }
          };
          
          window.addEventListener('keydown', handleKeydown);
          return () => window.removeEventListener('keydown', handleKeydown);
        }, []);
        
        return <input data-testid="input" />;
      };
      
      const { getByTestId } = render(<TestComponent />);
      
      const input = getByTestId('input');
      input.focus();
      
      fireEvent.keyDown(input, { key: 'Enter' });
      
      expect(actionTriggered).toBe(false);
    });
  });
});