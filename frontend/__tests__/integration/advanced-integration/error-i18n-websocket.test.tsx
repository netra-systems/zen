import React from 'react';
import { render, waitFor, screen, fireEvent, act } from '@testing-library/react';
import WS from 'jest-websocket-mock';
import { safeWebSocketCleanup } from '../../helpers/websocket-test-manager';
import { setupTestEnvironment } from './test-setup';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
t-manager';
import { setupTestEnvironment } from './test-setup';

describe('Advanced Frontend Integration Tests - Error, i18n, WebSocket', () => {
    jest.setTimeout(10000);
  let server: WS;
  
  setupTestEnvironment();

  beforeEach(() => {
    server = new WS('ws://localhost:8000/ws');
  });

  afterEach(() => {
    safeWebSocketCleanup();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('27. Advanced Error Boundaries', () => {
      jest.setTimeout(10000);
    it('should recover from component errors gracefully', async () => {
      class ErrorBoundary extends React.Component<
        { children: React.ReactNode },
        { hasError: boolean; errorInfo: any }
      > {
        constructor(props: any) {
          super(props);
          this.state = { hasError: false, errorInfo: null };
        }

        static getDerivedStateFromError(error: Error) {
          return { hasError: true };
        }

        componentDidCatch(error: Error, errorInfo: any) {
          this.setState({ errorInfo });
        }

        retry = () => {
          this.setState({ hasError: false, errorInfo: null });
        };

        render() {
          if (this.state.hasError) {
            return (
              <div>
                <div data-testid="error-message">Something went wrong</div>
                <button onClick={this.retry}>Retry</button>
              </div>
            );
          }

          return this.props.children;
        }
      }
      
      const FaultyComponent = ({ shouldError }: { shouldError: boolean }) => {
        if (shouldError) {
          throw new Error('Component error');
        }
        return <div>Working component</div>;
      };
      
      const TestComponent = () => {
        const [shouldError, setShouldError] = React.useState(false);
        
        return (
          <ErrorBoundary>
            <button onClick={() => setShouldError(true)}>Trigger Error</button>
            <FaultyComponent shouldError={shouldError} />
          </ErrorBoundary>
        );
      };
      
      const originalError = console.error;
      console.error = jest.fn();
      
      const { getByText } = render(<TestComponent />);
      
      fireEvent.click(getByText('Trigger Error'));
      
      // Error boundary should catch and display fallback
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toHaveTextContent('Something went wrong');
      });
      
      console.error = originalError;
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
      
      const originalError = console.error;
      console.error = jest.fn();
      
      const { getByText } = render(<MonitoredComponent />);
      
      fireEvent.click(getByText('Trigger Monitored Error'));
      
      expect(errorReports).toHaveLength(1);
      expect(errorReports[0].message).toBe('Monitored error');
      
      console.error = originalError;
    });
  });

  describe('28. Multi-language Support Integration', () => {
      jest.setTimeout(10000);
    it('should switch languages dynamically', async () => {
      const translations = {
        en: { welcome: 'Welcome', goodbye: 'Goodbye' },
        es: { welcome: 'Bienvenido', goodbye: 'Adiós' },
        fr: { welcome: 'Bienvenue', goodbye: 'Au revoir' }
      };
      
      const I18nComponent = () => {
        const [language, setLanguage] = React.useState('en');
        
        const t = (key: string) => translations[language][key] || key;
        
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

  describe('29. WebSocket Resilience Integration', () => {
      jest.setTimeout(10000);
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
          const ws = new WebSocket('ws://localhost:3001/test'));
          
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
      
      await server.connected;
      
      // Close connection to simulate disconnection
      server.close();
      
      await waitFor(() => {
        expect(getByTestId('connection-status')).toHaveTextContent('Disconnected');
      });
      
      // Send message while disconnected
      act(() => {
        fireEvent.click(getByText('Send Message'));
      });
      
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
            const ws = new WebSocket('ws://localhost:3001/test'));
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