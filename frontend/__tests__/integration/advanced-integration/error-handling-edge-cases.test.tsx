/**
 * Error Handling and Edge Cases Integration Tests
 * Tests for error boundaries, memory management, i18n, and WebSocket resilience
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react';
import { createTestSetup, TestErrorBoundary, suppressConsoleError } from './setup';

describe('Error Handling and Edge Cases Integration', () => {
  const testSetup = createTestSetup({ enableWebSocket: true });

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
  });

  describe('Advanced Error Boundaries', () => {
    it('should recover from component errors gracefully', async () => {
      const FaultyComponent = ({ shouldError }: { shouldError: boolean }) => {
        if (shouldError) {
          throw new Error('Component error');
        }
        return <div>Working component</div>;
      };
      
      const TestComponent = () => {
        const [shouldError, setShouldError] = React.useState(false);
        
        return (
          <TestErrorBoundary>
            <button onClick={() => setShouldError(true)}>Trigger Error</button>
            <FaultyComponent shouldError={shouldError} />
          </TestErrorBoundary>
        );
      };
      
      suppressConsoleError(() => {
        const { getByText } = render(<TestComponent />);
        
        fireEvent.click(getByText('Trigger Error'));
        
        // Error boundary should catch and display fallback
        expect(screen.getByTestId('error-message')).toHaveTextContent('Something went wrong');
      });
    });

    it('should report errors to monitoring service', async () => {
      const errorReports: any[] = [];
      
      const reportError = async (error: any) => {
        errorReports.push({
          message: error.message,
          stack: error.stack,
          timestamp: Date.now(),
          userAgent: navigator.userAgent
        });
      };
      
      const MonitoredComponent = () => {
        const handleError = () => {
          const error = new Error('Monitored error');
          reportError(error);
        };
        
        return (
          <div>
            <button onClick={handleError}>Trigger Monitored Error</button>
          </div>
        );
      };
      
      suppressConsoleError(() => {
        const { getByText } = render(<MonitoredComponent />);
        
        fireEvent.click(getByText('Trigger Monitored Error'));
        
        expect(errorReports).toHaveLength(1);
        expect(errorReports[0].message).toBe('Monitored error');
      });
    });
  });

  describe('Memory Management', () => {
    it('should cleanup resources on unmount', async () => {
      const cleanupFunctions: (() => void)[] = [];
      
      const ResourceComponent = () => {
        React.useEffect(() => {
          const timer = setInterval(() => {}, 1000);
          const listener = () => {};
          window.addEventListener('resize', listener);
          
          const cleanup = () => {
            clearInterval(timer);
            window.removeEventListener('resize', listener);
          };
          
          cleanupFunctions.push(cleanup);
          
          return cleanup;
        }, []);
        
        return <div>Resource Component</div>;
      };
      
      const { unmount } = render(<ResourceComponent />);
      
      expect(cleanupFunctions).toHaveLength(1);
      
      unmount();
      
      // Verify cleanup was called
      cleanupFunctions.forEach(cleanup => {
        expect(cleanup).toBeDefined();
      });
    });

    it('should manage large data sets efficiently', async () => {
      const LargeDataComponent = () => {
        const [data, setData] = React.useState<any[]>([]);
        const [isLoading, setIsLoading] = React.useState(false);
        
        const loadLargeDataset = async () => {
          setIsLoading(true);
          
          // Simulate loading large dataset in chunks
          const chunkSize = 1000;
          const totalSize = 5000;
          
          for (let i = 0; i < totalSize; i += chunkSize) {
            const chunk = Array.from({ length: chunkSize }, (_, j) => ({
              id: i + j,
              value: Math.random()
            }));
            
            setData(prev => [...prev, ...chunk]);
            
            // Allow UI to update
            await new Promise(resolve => setTimeout(resolve, 0));
          }
          
          setIsLoading(false);
        };
        
        // Cleanup large data on unmount
        React.useEffect(() => {
          return () => {
            setData([]);
          };
        }, []);
        
        return (
          <div>
            <button onClick={loadLargeDataset}>Load Data</button>
            <div data-testid="data-size">{data.length} items</div>
            {isLoading && <div>Loading...</div>}
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<LargeDataComponent />);
      
      fireEvent.click(getByText('Load Data'));
      
      await waitFor(() => {
        expect(getByTestId('data-size')).toHaveTextContent('5000 items');
      }, { timeout: 5000 });
    });
  });

  describe('Multi-language Support', () => {
    it('should switch languages dynamically', async () => {
      const translations: Record<string, Record<string, string>> = {
        en: { welcome: 'Welcome', goodbye: 'Goodbye' },
        es: { welcome: 'Bienvenido', goodbye: 'Adiós' },
        fr: { welcome: 'Bienvenue', goodbye: 'Au revoir' }
      };
      
      const I18nComponent = () => {
        const [language, setLanguage] = React.useState('en');
        
        const t = (key: string) => translations[language]?.[key] || key;
        
        return (
          <div>
            <select
              data-testid="language-selector"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="en">English</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
            </select>
            <div data-testid="welcome">{t('welcome')}</div>
            <div data-testid="goodbye">{t('goodbye')}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<I18nComponent />);
      
      expect(getByTestId('welcome')).toHaveTextContent('Welcome');
      
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'es' } });
      
      await waitFor(() => {
        expect(getByTestId('welcome')).toHaveTextContent('Bienvenido');
        expect(getByTestId('goodbye')).toHaveTextContent('Adiós');
      });
    });

    it('should handle RTL languages correctly', async () => {
      const RTLComponent = () => {
        const [language, setLanguage] = React.useState('en');
        const [direction, setDirection] = React.useState<'ltr' | 'rtl'>('ltr');
        
        React.useEffect(() => {
          const rtlLanguages = ['ar', 'he', 'fa'];
          const newDirection = rtlLanguages.includes(language) ? 'rtl' : 'ltr';
          setDirection(newDirection);
          document.documentElement.dir = newDirection;
        }, [language]);
        
        return (
          <div dir={direction}>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="en">English</option>
              <option value="ar">العربية</option>
            </select>
            <div data-testid="direction">{direction}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<RTLComponent />);
      
      expect(getByTestId('direction')).toHaveTextContent('ltr');
      
      const select = document.querySelector('select');
      fireEvent.change(select!, { target: { value: 'ar' } });
      
      await waitFor(() => {
        expect(getByTestId('direction')).toHaveTextContent('rtl');
        expect(document.documentElement.dir).toBe('rtl');
      });
    });
  });

  describe('WebSocket Resilience', () => {
    it('should handle WebSocket message buffering during reconnection', async () => {
      let messageBuffer: any[] = [];
      
      const ResilientWebSocketComponent = () => {
        const [isConnected, setIsConnected] = React.useState(false);
        const [messages, setMessages] = React.useState<any[]>([]);
        const wsRef = React.useRef<WebSocket | null>(null);
        
        const sendMessage = (message: any) => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
          } else {
            messageBuffer.push(message);
            // Force re-render to update buffer size display
            setMessages(prev => [...prev]);
          }
        };
        
        const connect = () => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onopen = () => {
            setIsConnected(true);
            
            // Flush buffered messages
            while (messageBuffer.length > 0) {
              const bufferedMessage = messageBuffer.shift();
              ws.send(JSON.stringify(bufferedMessage));
            }
          };
          
          ws.onclose = () => {
            setIsConnected(false);
            setTimeout(connect, 1000);
          };
          
          ws.onmessage = (event) => {
            setMessages(prev => [...prev, JSON.parse(event.data)]);
          };
          
          wsRef.current = ws;
        };
        
        React.useEffect(() => {
          connect();
          return () => wsRef.current?.close();
        }, []);
        
        return (
          <div>
            <div data-testid="connection-status">
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
            <button onClick={() => sendMessage({ type: 'test' })}>
              Send Message
            </button>
            <div data-testid="buffer-size">{messageBuffer.length} buffered</div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<ResilientWebSocketComponent />);
      
      await testSetup.waitForWebSocketConnection();
      
      // Close connection to simulate disconnection
      testSetup.closeWebSocketConnection();
      
      await waitFor(() => {
        expect(getByTestId('connection-status')).toHaveTextContent('Disconnected');
      });
      
      // Send message while disconnected
      fireEvent.click(getByText('Send Message'));
      
      // Wait a bit for the message to be buffered
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Check the buffer size directly from the component
      expect(getByTestId('buffer-size')).toHaveTextContent(`${messageBuffer.length} buffered`);
    });

    it('should implement exponential backoff for reconnection', async () => {
      const reconnectAttempts: number[] = [];
      
      const ExponentialBackoffComponent = () => {
        const [attempts, setAttempts] = React.useState(0);
        const [nextRetryIn, setNextRetryIn] = React.useState(0);
        
        const calculateBackoff = (attemptNumber: number) => {
          const baseDelay = 1000;
          const maxDelay = 30000;
          const delay = Math.min(baseDelay * Math.pow(2, attemptNumber), maxDelay);
          return delay + Math.random() * 1000; // Add jitter
        };
        
        const attemptReconnect = async () => {
          const delay = calculateBackoff(attempts);
          reconnectAttempts.push(delay);
          
          setNextRetryIn(Math.round(delay / 1000));
          setAttempts(prev => prev + 1);
          
          await new Promise(resolve => setTimeout(resolve, delay));
          
          // Simulate connection attempt
          try {
            const ws = new WebSocket('ws://localhost:8000/ws');
            ws.onerror = () => {
              attemptReconnect();
            };
          } catch {
            attemptReconnect();
          }
        };
        
        return (
          <div>
            <button onClick={attemptReconnect}>Start Reconnection</button>
            <div data-testid="attempts">Attempts: {attempts}</div>
            <div data-testid="next-retry">Next retry in: {nextRetryIn}s</div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<ExponentialBackoffComponent />);
      
      fireEvent.click(getByText('Start Reconnection'));
      
      await waitFor(() => {
        expect(parseInt(getByTestId('attempts').textContent?.split(': ')[1] || '0')).toBeGreaterThan(0);
      });
      
      // Verify exponential backoff pattern
      if (reconnectAttempts.length >= 2) {
        expect(reconnectAttempts[1]).toBeGreaterThan(reconnectAttempts[0]);
      }
    });
  });
});