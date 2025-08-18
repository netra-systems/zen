import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';

// Ultra-fast polyfills
global.TextEncoder = TextEncoder as any;
global.TextDecoder = TextDecoder as any;

// High-performance fetch mock
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
    blob: () => Promise.resolve(new Blob()),
    headers: new Map(),
    clone: () => global.fetch(),
  })
) as jest.Mock;

// Ultra-fast DOM optimizations
if (typeof window !== 'undefined') {
  // Disable all animations and transitions globally
  const ultraFastStyles = document.createElement('style');
  ultraFastStyles.innerHTML = `
    *, *::before, *::after {
      animation-duration: 0s !important;
      animation-delay: 0s !important;
      transition-duration: 0s !important;
      transition-delay: 0s !important;
      animation-iteration-count: 1 !important;
      scroll-behavior: auto !important;
    }
    
    /* Disable expensive CSS features */
    * {
      background-attachment: scroll !important;
      backdrop-filter: none !important;
      filter: none !important;
      box-shadow: none !important;
      text-shadow: none !important;
    }
  `;
  document.head.appendChild(ultraFastStyles);
  
  // Ultra-fast observer mocks
  global.IntersectionObserver = jest.fn().mockImplementation(() => ({
    observe: jest.fn(),
    unobserve: jest.fn(),
    disconnect: jest.fn(),
    takeRecords: () => [],
  }));
  
  global.ResizeObserver = jest.fn().mockImplementation(() => ({
    observe: jest.fn(),
    unobserve: jest.fn(),
    disconnect: jest.fn(),
  }));
  
  global.MutationObserver = jest.fn().mockImplementation(() => ({
    observe: jest.fn(),
    disconnect: jest.fn(),
    takeRecords: () => [],
  }));
  
  // Mock requestAnimationFrame for speed
  global.requestAnimationFrame = jest.fn((cb) => {
    setTimeout(cb, 0);
    return 1;
  });
  
  global.cancelAnimationFrame = jest.fn();
  
  // Mock performance API
  if (!global.performance) {
    global.performance = {} as any;
  }
  global.performance.now = jest.fn(() => Date.now());
  global.performance.mark = jest.fn();
  global.performance.measure = jest.fn();
  global.performance.getEntriesByName = jest.fn(() => []);
  global.performance.getEntriesByType = jest.fn(() => []);
}

// Ultra-fast error handling
const originalError = console.error;
const originalWarn = console.warn;
const originalLog = console.log;

// Aggressive noise filtering for maximum speed
const filterNoise = (args: any[]) => {
  const message = args[0]?.toString?.() || '';
  return (
    message.includes('Not implemented') ||
    message.includes('WebSocket') ||
    message.includes('Failed to fetch') ||
    message.includes('Network request failed') ||
    message.includes('ReactDOM.render') ||
    message.includes('componentWill') ||
    message.includes('dev login') ||
    message.includes('connecting') ||
    message.includes('Warning:') ||
    message.includes('validateDOMNesting') ||
    message.includes('findDOMNode')
  );
};

console.error = (...args: any[]) => {
  if (!filterNoise(args)) originalError.call(console, ...args);
};

console.warn = (...args: any[]) => {
  if (!filterNoise(args)) originalWarn.call(console, ...args);
};

console.log = (...args: any[]) => {
  if (!filterNoise(args)) originalLog.call(console, ...args);
};

// Ultra-fast storage mocks with in-memory optimization
const createUltraFastStorage = () => {
  const store = new Map<string, string>();
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => store.set(key, value),
    removeItem: (key: string) => store.delete(key),
    clear: () => store.clear(),
    get length() { return store.size; },
    key: (index: number) => Array.from(store.keys())[index] ?? null,
  };
};

const ultraStorage = createUltraFastStorage();
Object.defineProperty(window, 'localStorage', { value: ultraStorage, writable: true });
Object.defineProperty(window, 'sessionStorage', { value: ultraStorage, writable: true });

// Ultra-fast location mock
delete (window as any).location;
(window as any).location = {
  href: 'http://localhost:3000/',
  origin: 'http://localhost:3000',
  protocol: 'http:',
  host: 'localhost:3000',
  hostname: 'localhost',
  port: '3000',
  pathname: '/',
  search: '',
  hash: '',
  assign: jest.fn(),
  replace: jest.fn(),
  reload: jest.fn(),
};

// Ultra-fast media query mock
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(() => ({
    matches: false,
    media: '',
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Deterministic UUID for consistent snapshots
let uuidCounter = 0;
global.crypto = {
  ...global.crypto,
  randomUUID: (() => `test-uuid-${++uuidCounter}`) as any,
  getRandomValues: (arr: any) => {
    for (let i = 0; i < arr.length; i++) {
      arr[i] = Math.floor(Math.random() * 256);
    }
    return arr;
  },
} as any;

// Ultra-fast Date mock for consistent timing
const originalDate = Date;
let mockTimeOffset = 0;

global.Date = class extends originalDate {
  constructor(...args: any[]) {
    if (args.length === 0) {
      super(1640995200000 + mockTimeOffset); // Fixed timestamp: 2022-01-01
      mockTimeOffset += 1000; // Increment for deterministic ordering
    } else {
      super(...args);
    }
  }
  
  static now() {
    return 1640995200000 + mockTimeOffset;
  }
} as any;

// Environment optimization
process.env.NODE_ENV = 'test';
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';

// Fast fail for promise rejections
process.on('unhandledRejection', (reason) => {
  // console mocked: console.log('Unhandled Promise Rejection:', reason);
  process.exit(1);
});

// Ultra-fast cleanup after each test
afterEach(() => {
  jest.clearAllMocks();
  ultraStorage.clear();
  mockTimeOffset = 0;
  
  // Reset any global state modifications
  if (typeof window !== 'undefined') {
    // Clean up any dynamically added elements
    const dynamicElements = document.querySelectorAll('[data-test-dynamic]');
    dynamicElements.forEach(el => el.remove());
  }
});

// Global test timeout
jest.setTimeout(6000);

// Ultra-fast service mocks
jest.mock('@/services/apiClientWrapper', () => ({
  apiClientWrapper: {
    request: jest.fn().mockRejectedValue(new Error('API mocked')),
    retryRequest: jest.fn().mockRejectedValue(new Error('API mocked')),
    checkConnection: jest.fn().mockResolvedValue(false),
    isConnected: false,
  },
}));

jest.mock('@/services/webSocketService', () => ({
  webSocketService: {
    connect: jest.fn(),
    disconnect: jest.fn(),
    send: jest.fn(),
    isConnected: false,
    connectionState: 'disconnected',
  },
}));

// Mock heavy external libraries
jest.mock('react-syntax-highlighter', () => ({
  Prism: ({ children }: any) => children,
  __esModule: true,
  default: ({ children }: any) => children,
}));

jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children }: any) => children,
}));

jest.mock('framer-motion', () => ({
  motion: {
    div: 'div',
    span: 'span',
    p: 'p',
    h1: 'h1',
    h2: 'h2',
    h3: 'h3',
    button: 'button',
    form: 'form',
    input: 'input',
    textarea: 'textarea',
    select: 'select',
    img: 'img',
    svg: 'svg',
    path: 'path',
  },
  AnimatePresence: ({ children }: any) => children,
  useAnimation: () => ({ start: jest.fn(), stop: jest.fn() }),
  useMotionValue: () => ({ get: jest.fn(), set: jest.fn() }),
}));

// Console override for ultra speed
if (process.env.JEST_ULTRA_SILENT === 'true') {
  console.log = jest.fn();
  console.info = jest.fn();
  console.warn = jest.fn();
  console.error = jest.fn();
}

// console mocked: console.log('🚀 Ultra Jest Setup Loaded - Maximum Performance Mode');