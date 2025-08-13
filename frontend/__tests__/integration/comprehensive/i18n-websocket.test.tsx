/**
 * Internationalization and WebSocket Resilience Tests
 * 
 * Tests multi-language support, RTL languages, WebSocket message buffering,
 * exponential backoff reconnection, and WebSocket resilience patterns.
 */

import {
  React,
  render,
  waitFor,
  screen,
  fireEvent,
  act,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockWebSocketServer,
  createWebSocketMessage,
  simulateNetworkDelay,
  TEST_TIMEOUTS,
  WS
} from './test-utils';

// Apply Next.js navigation mock
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

describe('Internationalization and WebSocket Resilience Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
  });

  describe('Multi-language Support Integration', () => {
    it('should switch languages dynamically', async () => {
      const translations = {
        en: { 
          welcome: 'Welcome', 
          goodbye: 'Goodbye',
          loading: 'Loading...',
          error: 'An error occurred'
        },
        es: { 
          welcome: 'Bienvenido', 
          goodbye: 'Adiós',
          loading: 'Cargando...',
          error: 'Ha ocurrido un error'
        },
        fr: { 
          welcome: 'Bienvenue', 
          goodbye: 'Au revoir',
          loading: 'Chargement...',
          error: 'Une erreur s\'est produite'
        },
        zh: {
          welcome: '欢迎',
          goodbye: '再见',
          loading: '加载中...',
          error: '发生错误'
        }
      };
      
      const I18nComponent = () => {
        const [language, setLanguage] = React.useState<keyof typeof translations>('en');
        const [isLoading, setIsLoading] = React.useState(false);
        const [hasError, setHasError] = React.useState(false);
        
        const t = (key: string) => {
          const translation = translations[language]?.[key];
          return translation || key;
        };
        
        const simulateAction = async () => {
          setIsLoading(true);
          setHasError(false);
          
          await simulateNetworkDelay(200);
          
          // Randomly succeed or fail for testing
          const success = Math.random() > 0.5;
          if (!success) {
            setHasError(true);
          }
          
          setIsLoading(false);
        };
        
        React.useEffect(() => {
          // Save language preference
          localStorage.setItem('preferred_language', language);
          
          // Update document language
          document.documentElement.lang = language;
        }, [language]);
        
        return (
          <div>
            <select
              data-testid="language-selector"
              value={language}
              onChange={(e) => setLanguage(e.target.value as keyof typeof translations)}
            >
              <option value="en">English</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
              <option value="zh">中文</option>
            </select>
            
            <div data-testid="welcome-message">{t('welcome')}</div>
            <div data-testid="goodbye-message">{t('goodbye')}</div>
            
            <button onClick={simulateAction} disabled={isLoading}>
              Test Action
            </button>
            
            {isLoading && <div data-testid="loading-message">{t('loading')}</div>}
            {hasError && <div data-testid="error-message">{t('error')}</div>}
            
            <div data-testid="current-lang">{language}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<I18nComponent />);
      
      // Initial English state
      expect(getByTestId('welcome-message')).toHaveTextContent('Welcome');
      expect(getByTestId('goodbye-message')).toHaveTextContent('Goodbye');
      expect(getByTestId('current-lang')).toHaveTextContent('en');
      expect(document.documentElement.lang).toBe('en');
      
      // Switch to Spanish
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'es' } });
      
      await waitFor(() => {
        expect(getByTestId('welcome-message')).toHaveTextContent('Bienvenido');
        expect(getByTestId('goodbye-message')).toHaveTextContent('Adiós');
        expect(getByTestId('current-lang')).toHaveTextContent('es');
        expect(document.documentElement.lang).toBe('es');
      });
      
      // Switch to French
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'fr' } });
      
      await waitFor(() => {
        expect(getByTestId('welcome-message')).toHaveTextContent('Bienvenue');
        expect(getByTestId('goodbye-message')).toHaveTextContent('Au revoir');
        expect(localStorage.getItem('preferred_language')).toBe('fr');
      });
      
      // Switch to Chinese (test Unicode support)
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'zh' } });
      
      await waitFor(() => {
        expect(getByTestId('welcome-message')).toHaveTextContent('欢迎');
        expect(getByTestId('goodbye-message')).toHaveTextContent('再见');
      });
    });

    it('should handle RTL languages correctly', async () => {
      const RTLComponent = () => {
        const [language, setLanguage] = React.useState('en');
        const [direction, setDirection] = React.useState<'ltr' | 'rtl'>('ltr');
        const [textAlign, setTextAlign] = React.useState<'left' | 'right'>('left');
        
        const languageConfig = {
          en: { name: 'English', dir: 'ltr' as const, align: 'left' as const },
          ar: { name: 'العربية', dir: 'rtl' as const, align: 'right' as const },
          he: { name: 'עברית', dir: 'rtl' as const, align: 'right' as const },
          fa: { name: 'فارسی', dir: 'rtl' as const, align: 'right' as const },
          es: { name: 'Español', dir: 'ltr' as const, align: 'left' as const }
        };
        
        React.useEffect(() => {
          const config = languageConfig[language];
          if (config) {
            setDirection(config.dir);
            setTextAlign(config.align);
            document.documentElement.dir = config.dir;
            document.body.style.textAlign = config.align;
          }
        }, [language]);
        
        return (
          <div dir={direction} style={{ textAlign }}>
            <select
              data-testid="language-selector"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              {Object.entries(languageConfig).map(([code, config]) => (
                <option key={code} value={code}>
                  {config.name}
                </option>
              ))}
            </select>
            
            <div data-testid="direction-indicator">{direction}</div>
            <div data-testid="text-align">{textAlign}</div>
            <div data-testid="sample-text">
              This is sample text that should align correctly
            </div>
            <div data-testid="numbers">1234567890</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<RTLComponent />);
      
      // Initial LTR state
      expect(getByTestId('direction-indicator')).toHaveTextContent('ltr');
      expect(getByTestId('text-align')).toHaveTextContent('left');
      expect(document.documentElement.dir).toBe('ltr');
      
      // Switch to Arabic (RTL)
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'ar' } });
      
      await waitFor(() => {
        expect(getByTestId('direction-indicator')).toHaveTextContent('rtl');
        expect(getByTestId('text-align')).toHaveTextContent('right');
        expect(document.documentElement.dir).toBe('rtl');
      });
      
      // Switch to Hebrew (RTL)
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'he' } });
      
      await waitFor(() => {
        expect(getByTestId('direction-indicator')).toHaveTextContent('rtl');
        expect(document.documentElement.dir).toBe('rtl');
      });
      
      // Switch back to Spanish (LTR)
      fireEvent.change(getByTestId('language-selector'), { target: { value: 'es' } });
      
      await waitFor(() => {
        expect(getByTestId('direction-indicator')).toHaveTextContent('ltr');
        expect(getByTestId('text-align')).toHaveTextContent('left');
        expect(document.documentElement.dir).toBe('ltr');
      });
    });

    it('should format dates and numbers according to locale', async () => {
      const LocaleFormatComponent = () => {
        const [locale, setLocale] = React.useState('en-US');
        const [sampleDate] = React.useState(new Date('2024-01-15T10:30:00'));
        const [sampleNumber] = React.useState(1234567.89);
        const [sampleCurrency] = React.useState(1000.50);
        
        const formatDate = (date: Date) => {
          return new Intl.DateTimeFormat(locale).format(date);
        };
        
        const formatNumber = (num: number) => {
          return new Intl.NumberFormat(locale).format(num);
        };
        
        const formatCurrency = (amount: number) => {
          const currencyMap = {
            'en-US': 'USD',
            'es-ES': 'EUR',
            'ja-JP': 'JPY',
            'ar-SA': 'SAR'
          };
          
          const currency = currencyMap[locale] || 'USD';
          return new Intl.NumberFormat(locale, {
            style: 'currency',
            currency
          }).format(amount);
        };
        
        return (
          <div>
            <select
              data-testid="locale-selector"
              value={locale}
              onChange={(e) => setLocale(e.target.value)}
            >
              <option value="en-US">English (US)</option>
              <option value="es-ES">Español (ES)</option>
              <option value="ja-JP">日本語 (JP)</option>
              <option value="ar-SA">العربية (SA)</option>
            </select>
            
            <div data-testid="formatted-date">{formatDate(sampleDate)}</div>
            <div data-testid="formatted-number">{formatNumber(sampleNumber)}</div>
            <div data-testid="formatted-currency">{formatCurrency(sampleCurrency)}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<LocaleFormatComponent />);
      
      // Test US formatting
      expect(getByTestId('formatted-date')).toHaveTextContent('1/15/2024');
      expect(getByTestId('formatted-number')).toHaveTextContent('1,234,567.89');
      expect(getByTestId('formatted-currency')).toHaveTextContent('$1,000.50');
      
      // Test Spanish formatting
      fireEvent.change(getByTestId('locale-selector'), { target: { value: 'es-ES' } });
      
      await waitFor(() => {
        expect(getByTestId('formatted-date')).toHaveTextContent('15/1/2024');
        expect(getByTestId('formatted-currency')).toHaveTextContent('1000,50');
      });
    });
  });

  describe('WebSocket Resilience Integration', () => {
    it('should handle WebSocket message buffering during reconnection', async () => {
      let messageBuffer: any[] = [];
      
      const ResilientWebSocketComponent = () => {
        const [connectionState, setConnectionState] = React.useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
        const [messages, setMessages] = React.useState<any[]>([]);
        const [reconnectAttempts, setReconnectAttempts] = React.useState(0);
        const wsRef = React.useRef<WebSocket | null>(null);
        
        const sendMessage = (message: any) => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
            return true;
          } else {
            messageBuffer.push({ ...message, timestamp: Date.now() });
            return false;
          }
        };
        
        const connect = () => {
          setConnectionState('connecting');
          
          try {
            const ws = new WebSocket('ws://localhost:8000/ws');
            
            ws.onopen = () => {
              setConnectionState('connected');
              setReconnectAttempts(0);
              
              // Flush buffered messages
              const messagesToFlush = [...messageBuffer];
              messageBuffer = [];
              
              messagesToFlush.forEach(bufferedMessage => {
                ws.send(JSON.stringify(bufferedMessage));
              });
            };
            
            ws.onclose = () => {
              setConnectionState('disconnected');
              setReconnectAttempts(prev => prev + 1);
              
              // Attempt reconnection with delay
              setTimeout(() => {
                if (reconnectAttempts < 5) {
                  connect();
                }
              }, 1000 * Math.pow(2, reconnectAttempts));
            };
            
            ws.onerror = () => {
              setConnectionState('error');
            };
            
            ws.onmessage = (event) => {
              const message = JSON.parse(event.data);
              setMessages(prev => [...prev, message]);
            };
            
            wsRef.current = ws;
          } catch (error) {
            setConnectionState('error');
          }
        };
        
        React.useEffect(() => {
          connect();
          return () => {
            wsRef.current?.close();
          };
        }, []);
        
        return (
          <div>
            <div data-testid="connection-state">{connectionState}</div>
            <div data-testid="reconnect-attempts">{reconnectAttempts}</div>
            <div data-testid="buffer-size">{messageBuffer.length} buffered</div>
            <div data-testid="message-count">{messages.length} received</div>
            
            <button 
              onClick={() => sendMessage({ type: 'ping', data: 'test' })}
              data-testid="send-message"
            >
              Send Message
            </button>
            
            <button onClick={connect} data-testid="manual-connect">
              Connect
            </button>
          </div>
        );
      };
      
      const { getByTestId, getByText } = render(<ResilientWebSocketComponent />);
      
      // Wait for initial connection
      await server.connected;
      
      await waitFor(() => {
        expect(getByTestId('connection-state')).toHaveTextContent('connected');
      });
      
      // Send a message while connected
      fireEvent.click(getByTestId('send-message'));
      expect(getByTestId('buffer-size')).toHaveTextContent('0 buffered');
      
      // Simulate disconnection
      server.close();
      
      await waitFor(() => {
        expect(getByTestId('connection-state')).toHaveTextContent('disconnected');
      });
      
      // Send messages while disconnected - they should be buffered
      fireEvent.click(getByTestId('send-message'));
      fireEvent.click(getByTestId('send-message'));
      
      expect(messageBuffer.length).toBe(2);
      expect(getByTestId('buffer-size')).toHaveTextContent('2 buffered');
    });

    it('should implement exponential backoff for reconnection', async () => {
      const reconnectionDelays: number[] = [];
      
      const ExponentialBackoffComponent = () => {
        const [attempts, setAttempts] = React.useState(0);
        const [nextRetryIn, setNextRetryIn] = React.useState(0);
        const [connectionState, setConnectionState] = React.useState('disconnected');
        const [lastDelay, setLastDelay] = React.useState(0);
        
        const calculateBackoff = (attemptNumber: number) => {
          const baseDelay = 100; // Reduced for testing
          const maxDelay = 5000; // Reduced for testing
          const exponentialDelay = baseDelay * Math.pow(2, attemptNumber);
          const cappedDelay = Math.min(exponentialDelay, maxDelay);
          const jitteredDelay = cappedDelay + (Math.random() * 1000);
          
          return Math.round(jitteredDelay);
        };
        
        const attemptReconnect = async () => {
          const delay = calculateBackoff(attempts);
          reconnectionDelays.push(delay);
          
          setLastDelay(delay);
          setNextRetryIn(Math.round(delay / 1000));
          setConnectionState('waiting');
          setAttempts(prev => prev + 1);
          
          // Countdown timer
          const countdownInterval = setInterval(() => {
            setNextRetryIn(prev => {
              if (prev <= 1) {
                clearInterval(countdownInterval);
                return 0;
              }
              return prev - 1;
            });
          }, 1000);
          
          await new Promise(resolve => setTimeout(resolve, delay));
          
          // Simulate connection attempt failure for testing
          setConnectionState('failed');
          
          if (attempts < 3) {
            setTimeout(() => attemptReconnect(), 100);
          }
        };
        
        const resetAttempts = () => {
          setAttempts(0);
          setNextRetryIn(0);
          setConnectionState('disconnected');
          setLastDelay(0);
          reconnectionDelays.length = 0;
        };
        
        return (
          <div>
            <button onClick={attemptReconnect} data-testid="start-reconnect">
              Start Reconnection
            </button>
            <button onClick={resetAttempts} data-testid="reset">
              Reset
            </button>
            
            <div data-testid="attempts">Attempts: {attempts}</div>
            <div data-testid="connection-state">{connectionState}</div>
            <div data-testid="next-retry">Next retry in: {nextRetryIn}s</div>
            <div data-testid="last-delay">Last delay: {lastDelay}ms</div>
            <div data-testid="delay-history">
              Delays: {reconnectionDelays.join(', ')}ms
            </div>
          </div>
        );
      };
      
      const { getByTestId } = render(<ExponentialBackoffComponent />);
      
      fireEvent.click(getByTestId('start-reconnect'));
      
      await waitFor(() => {
        expect(getByTestId('attempts')).toHaveTextContent('Attempts: 1');
        expect(parseInt(getByTestId('last-delay').textContent?.split(': ')[1] || '0')).toBeGreaterThan(0);
      });
      
      // Wait for a few attempts and verify exponential growth
      await waitFor(() => {
        expect(parseInt(getByTestId('attempts').textContent?.split(': ')[1] || '0')).toBeGreaterThan(1);
      }, { timeout: TEST_TIMEOUTS.MEDIUM });
      
      // Verify exponential backoff pattern
      if (reconnectionDelays.length >= 2) {
        expect(reconnectionDelays[1]).toBeGreaterThanOrEqual(reconnectionDelays[0]);
      }
    });

    it('should handle WebSocket heartbeat and keep-alive', async () => {
      const HeartbeatComponent = () => {
        const [lastHeartbeat, setLastHeartbeat] = React.useState<number | null>(null);
        const [connectionHealth, setConnectionHealth] = React.useState<'healthy' | 'stale' | 'dead'>('healthy');
        const [heartbeatInterval, setHeartbeatInterval] = React.useState(1000);
        const wsRef = React.useRef<WebSocket | null>(null);
        const heartbeatTimerRef = React.useRef<NodeJS.Timeout | null>(null);
        const healthCheckRef = React.useRef<NodeJS.Timeout | null>(null);
        
        const sendHeartbeat = () => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'heartbeat', timestamp: Date.now() }));
            setLastHeartbeat(Date.now());
          }
        };
        
        const checkConnectionHealth = () => {
          const now = Date.now();
          if (lastHeartbeat) {
            const timeSinceLastHeartbeat = now - lastHeartbeat;
            if (timeSinceLastHeartbeat > heartbeatInterval * 3) {
              setConnectionHealth('dead');
            } else if (timeSinceLastHeartbeat > heartbeatInterval * 2) {
              setConnectionHealth('stale');
            } else {
              setConnectionHealth('healthy');
            }
          }
        };
        
        React.useEffect(() => {
          // Start heartbeat
          heartbeatTimerRef.current = setInterval(sendHeartbeat, heartbeatInterval);
          
          // Start health monitoring
          healthCheckRef.current = setInterval(checkConnectionHealth, heartbeatInterval / 2);
          
          return () => {
            if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
            if (healthCheckRef.current) clearInterval(healthCheckRef.current);
          };
        }, [heartbeatInterval, lastHeartbeat]);
        
        return (
          <div>
            <div data-testid="connection-health">{connectionHealth}</div>
            <div data-testid="last-heartbeat">
              {lastHeartbeat ? new Date(lastHeartbeat).toISOString() : 'None'}
            </div>
            <div data-testid="heartbeat-interval">{heartbeatInterval}ms</div>
            
            <button onClick={sendHeartbeat} data-testid="manual-heartbeat">
              Send Heartbeat
            </button>
            
            <button
              onClick={() => setHeartbeatInterval(500)}
              data-testid="faster-heartbeat"
            >
              Faster Heartbeat
            </button>
          </div>
        );
      };
      
      const { getByTestId } = render(<HeartbeatComponent />);
      
      // Manual heartbeat should work
      fireEvent.click(getByTestId('manual-heartbeat'));
      
      await waitFor(() => {
        expect(getByTestId('last-heartbeat')).not.toHaveTextContent('None');
        expect(getByTestId('connection-health')).toHaveTextContent('healthy');
      });
      
      // Test faster heartbeat
      fireEvent.click(getByTestId('faster-heartbeat'));
      
      await waitFor(() => {
        expect(getByTestId('heartbeat-interval')).toHaveTextContent('500ms');
      });
    });
  });
});