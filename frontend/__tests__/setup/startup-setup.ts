/**
 * Global test setup for startup tests
 * Ensures proper mocking of browser APIs and global objects
 */

// Mock localStorage and sessionStorage
const mockStorage = () => {
  const storage: { [key: string]: string } = {};
  return {
    getItem: (key: string) => storage[key] || null,
    setItem: (key: string, value: string) => { storage[key] = value; },
    removeItem: (key: string) => { delete storage[key]; },
    clear: () => { Object.keys(storage).forEach(key => delete storage[key]); },
    length: Object.keys(storage).length,
    key: (index: number) => Object.keys(storage)[index] || null
  };
};

Object.defineProperty(window, 'localStorage', {
  value: mockStorage(),
  writable: true
});

Object.defineProperty(window, 'sessionStorage', {
  value: mockStorage(),
  writable: true
});

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
process.env.NODE_ENV = 'test';

// Mock global fetch
global.fetch = jest.fn();

// Mock WebSocket
global.WebSocket = jest.fn(() => ({
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN,
  url: 'ws://localhost:8000',
  protocol: '',
  bufferedAmount: 0,
  extensions: '',
  binaryType: 'blob' as BinaryType,
  onopen: null,
  onclose: null,
  onmessage: null,
  onerror: null,
  dispatchEvent: jest.fn()
})) as any;

// Mock navigator.serviceWorker
Object.defineProperty(navigator, 'serviceWorker', {
  value: {
    register: jest.fn(() => Promise.resolve({
      update: jest.fn(),
      unregister: jest.fn(),
      waiting: null,
      installing: null,
      active: null
    })),
    ready: Promise.resolve({
      update: jest.fn(),
      unregister: jest.fn(),
      waiting: null,
      installing: null,
      active: null
    })
  },
  writable: true
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  value: jest.fn().mockImplementation(query => ({
    matches: query === '(prefers-color-scheme: dark)',
    media: query,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    addListener: jest.fn(),
    removeListener: jest.fn(),
    onchange: null,
    dispatchEvent: jest.fn()
  })),
  writable: true
});

// Mock performance API
Object.defineProperty(performance, 'memory', {
  value: {
    usedJSHeapSize: 1000000,
    totalJSHeapSize: 2000000,
    jsHeapSizeLimit: 4000000
  },
  writable: true
});

// Mock performance marks
const mockMarks: PerformanceMark[] = [];
performance.mark = jest.fn((name: string) => {
  const mark = {
    name,
    entryType: 'mark' as const,
    startTime: performance.now(),
    duration: 0,
    toJSON: jest.fn()
  };
  mockMarks.push(mark);
  return mark;
});

performance.getEntriesByType = jest.fn((type: string) => {
  if (type === 'mark') return mockMarks;
  return [];
});

// Mock URL constructor for tests that validate URLs
global.URL = jest.fn().mockImplementation((url: string) => ({
  href: url,
  origin: 'http://localhost:8000',
  pathname: '/',
  search: '',
  hash: '',
  host: 'localhost:8000',
  hostname: 'localhost',
  port: '8000',
  protocol: 'http:',
  toString: () => url
})) as any;

// Mock console methods but preserve original for restoration
const originalConsole = {
  log: console.log,
  error: console.error,
  warn: console.warn,
  info: console.info
};

// Setup test cleanup
beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
});

afterEach(() => {
  jest.restoreAllMocks();
});

// Export original console for test restoration
export { originalConsole };