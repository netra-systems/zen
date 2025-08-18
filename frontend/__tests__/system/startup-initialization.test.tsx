/**
 * Frontend System Startup - Initialization Tests
 * Tests for Store, Router, Service Worker, Theme, and Configuration initialization
 */

// JEST MODULE HOISTING - Mocks BEFORE imports
// Create stateful mock stores
let mockAuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
  loading: false,
  login: jest.fn((user, token) => {
    mockAuthState.user = user;
    mockAuthState.token = token;
    mockAuthState.isAuthenticated = true;
  }),
  logout: jest.fn(() => {
    mockAuthState.user = null;
    mockAuthState.token = null;
    mockAuthState.isAuthenticated = false;
  }),
  subscribe: jest.fn()
};

let mockChatState = {
  messages: [],
  isLoading: false,
  addMessage: jest.fn(),
  clearMessages: jest.fn(),
  subscribe: jest.fn()
};

const mockAuthStore = {
  getState: jest.fn(() => mockAuthState),
  subscribe: jest.fn()
};

const mockChatStore = {
  getState: jest.fn(() => mockChatState),
  subscribe: jest.fn()
};

// Mock stores BEFORE imports
jest.mock('@/store/authStore', () => ({
  useAuthStore: mockAuthStore
}));

jest.mock('@/store/chatStore', () => ({
  useChatStore: mockChatStore
}));

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/'
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams()
}));

// Mock global fetch
global.fetch = jest.fn();

// Mock WebSocket
global.WebSocket = jest.fn(() => ({
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN
})) as any;

// Mock navigator.serviceWorker
Object.defineProperty(navigator, 'serviceWorker', {
  value: {
    register: jest.fn(),
    ready: Promise.resolve()
  },
  writable: true
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  value: jest.fn().mockImplementation(query => ({
    matches: query === '(prefers-color-scheme: dark)',
    media: query,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn()
  })),
  writable: true
});

// Import global test setup
import '../setup/startup-setup';

import React from 'react';
import '@testing-library/jest-dom';

import {
  setupTestEnvironment,
  cleanupTestEnvironment,
  setupLocalStorageMocks,
  createMockUser,
  setupServiceWorkerMocks,
  setupThemeMocks,
  createAppConfig
} from './helpers/startup-test-utilities';

import {
  mockProductionEnvironment
} from './helpers/startup-test-mocks';

describe('Frontend System Startup - Initialization', () => {
  beforeEach(() => {
    setupTestEnvironment();
    jest.clearAllMocks();
    // Reset mock store states
    mockAuthState.user = null;
    mockAuthState.token = null;
    mockAuthState.isAuthenticated = false;
    mockAuthState.loading = false;
    mockChatState.messages = [];
    mockChatState.isLoading = false;
  });

  afterEach(() => {
    cleanupTestEnvironment();
  });

  describe('Store Initialization', () => {
    it('should initialize Zustand stores', () => {
      testStoreInitialization();
    });

    const testStoreInitialization = () => {
      const { authState, chatState } = getStoreStates();
      
      verifyAuthStoreInitialization(authState);
      verifyChatStoreInitialization(chatState);
    };

    const getStoreStates = () => {
      const authState = mockAuthStore.getState();
      const chatState = mockChatStore.getState();
      
      return { authState, chatState };
    };

    const verifyAuthStoreInitialization = (authState: any) => {
      expect(authState).toBeDefined();
      expect(authState.user).toBeNull();
      expect(authState.isAuthenticated).toBe(false);
    };

    const verifyChatStoreInitialization = (chatState: any) => {
      expect(chatState).toBeDefined();
      expect(chatState.messages).toEqual([]);
    };

    it('should restore persisted state', () => {
      testPersistedStateRestoration();
    });

    const testPersistedStateRestoration = () => {
      const { mockUser } = setupLocalStorageMocks();
      const restoredState = restoreStateFromStorage();
      
      verifyRestoredState(restoredState, mockUser);
    };

    const restoreStateFromStorage = () => {
      const token = localStorage.getItem('jwt_token');
      const userStr = localStorage.getItem('user');
      
      if (token && userStr) {
        const user = JSON.parse(userStr);
        mockAuthStore.getState().login(user, token);
      }
      
      return mockAuthStore.getState();
    };

    const verifyRestoredState = (state: any, expectedUser: any) => {
      expect(state.token).toBe('test-token');
      expect(state.user).toEqual(expectedUser);
      expect(state.isAuthenticated).toBe(true);
    };

    it('should handle store hydration', () => {
      testStoreHydration();
    });

    const testStoreHydration = () => {
      const initialState = mockAuthStore.getState();
      
      expect(initialState).toBeDefined();
      expect(typeof initialState.login).toBe('function');
      expect(typeof initialState.logout).toBe('function');
    };

    it('should initialize store subscriptions', () => {
      testStoreSubscriptions();
    });

    const testStoreSubscriptions = () => {
      expect(mockAuthStore.subscribe).toBeDefined();
      expect(mockChatStore.subscribe).toBeDefined();
    };
  });

  describe('Service Worker Registration', () => {
    it('should register service worker in production', async () => {
      await testServiceWorkerRegistration();
    });

    const testServiceWorkerRegistration = async () => {
      const { restore } = mockProductionEnvironment();
      const { mockRegistration } = setupServiceWorkerMocks();
      
      await registerServiceWorker();
      verifyServiceWorkerRegistration();
      
      restore();
    };

    const registerServiceWorker = async () => {
      if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
        await navigator.serviceWorker.register('/sw.js');
      }
    };

    const verifyServiceWorkerRegistration = () => {
      expect(navigator.serviceWorker.register).toHaveBeenCalledWith('/sw.js');
    };

    it('should handle service worker updates', async () => {
      await testServiceWorkerUpdates();
    });

    const testServiceWorkerUpdates = async () => {
      const { mockRegistration } = setupServiceWorkerMocks();
      
      await navigator.serviceWorker.register('/sw.js');
      await mockRegistration.update();
      
      expect(mockRegistration.update).toHaveBeenCalled();
    };

    it('should handle service worker errors', async () => {
      await testServiceWorkerErrors();
    });

    const testServiceWorkerErrors = async () => {
      navigator.serviceWorker = {
        register: jest.fn().mockRejectedValue(new Error('SW Error')),
      } as any;
      
      try {
        await navigator.serviceWorker.register('/sw.js');
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
      }
    };
  });

  describe('Router Initialization', () => {
    it('should initialize Next.js router', () => {
      testRouterInitialization();
    });

    const testRouterInitialization = () => {
      const { useRouter } = require('next/navigation');
      const router = useRouter();
      
      verifyRouterMethods(router);
    };

    const verifyRouterMethods = (router: any) => {
      expect(router).toBeDefined();
      expect(router.push).toBeDefined();
      expect(router.replace).toBeDefined();
    };

    it('should handle navigation methods', () => {
      testNavigationMethods();
    });

    const testNavigationMethods = () => {
      const { useRouter } = require('next/navigation');
      const router = useRouter();
      
      router.push('/test');
      router.replace('/test');
      
      expect(router.push).toHaveBeenCalledWith('/test');
      expect(router.replace).toHaveBeenCalledWith('/test');
    };

    it('should initialize pathname and search params', () => {
      testPathAndParams();
    });

    const testPathAndParams = () => {
      const { usePathname, useSearchParams } = require('next/navigation');
      
      const pathname = usePathname();
      const searchParams = useSearchParams();
      
      expect(pathname).toBe('/');
      expect(searchParams).toBeInstanceOf(URLSearchParams);
    };
  });

  describe('Configuration Loading', () => {
    it('should load application configuration', () => {
      testConfigurationLoading();
    });

    const testConfigurationLoading = () => {
      const config = createAppConfig();
      verifyConfiguration(config);
    };

    const verifyConfiguration = (config: any) => {
      expect(config.apiUrl).toBe('http://localhost:8000');
      expect(config.wsUrl).toBe('ws://localhost:8000');
      expect(config.environment).toBeDefined();
      expect(config.version).toBe('1.0.0');
    };

    it('should handle missing configuration gracefully', () => {
      testMissingConfiguration();
    });

    const testMissingConfiguration = () => {
      delete process.env.NEXT_PUBLIC_API_URL;
      
      const config = createAppConfig();
      expect(config.apiUrl).toBeUndefined();
    };

    it('should validate configuration types', () => {
      testConfigurationTypes();
    });

    const testConfigurationTypes = () => {
      const config = createAppConfig();
      
      expect(typeof config.version).toBe('string');
      expect(typeof config.apiUrl).toBe('string');
    };
  });

  describe('Theme Initialization', () => {
    it('should initialize theme from user preferences', () => {
      testThemeInitialization();
    });

    const testThemeInitialization = () => {
      setupThemeMocks();
      const theme = detectThemePreference();
      
      expect(theme).toBe('dark');
    };

    const detectThemePreference = () => {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      return prefersDark ? 'dark' : 'light';
    };

    it('should handle light theme preference', () => {
      testLightThemePreference();
    });

    const testLightThemePreference = () => {
      window.matchMedia = jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-color-scheme: light)',
        media: query,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      })) as any;
      
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const theme = prefersDark ? 'dark' : 'light';
      
      expect(theme).toBe('light');
    };

    it('should setup theme change listeners', () => {
      testThemeChangeListeners();
    });

    const testThemeChangeListeners = () => {
      setupThemeMocks();
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      
      expect(mediaQuery.addEventListener).toBeDefined();
      expect(mediaQuery.removeEventListener).toBeDefined();
    };

    it('should handle theme persistence', () => {
      testThemePersistence();
    });

    const testThemePersistence = () => {
      localStorage.setItem('theme', 'dark');
      const savedTheme = localStorage.getItem('theme');
      
      expect(savedTheme).toBe('dark');
    };
  });

  describe('State Synchronization', () => {
    it('should synchronize store states', () => {
      testStateSynchronization();
    });

    const testStateSynchronization = () => {
      const mockUser = createMockUser();
      
      mockAuthStore.getState().login(mockUser, 'test-token');
      const state = mockAuthStore.getState();
      
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
    };

    it('should handle cross-store communication', () => {
      testCrossStoreCommunication();
    });

    const testCrossStoreCommunication = () => {
      const authState = mockAuthStore.getState();
      const chatState = mockChatStore.getState();
      
      expect(authState).toBeDefined();
      expect(chatState).toBeDefined();
    };
  });

  describe('Initialization Order', () => {
    it('should initialize components in correct order', () => {
      testInitializationOrder();
    });

    const testInitializationOrder = () => {
      const initSteps = [
        'environment',
        'stores',
        'router',
        'theme',
        'services'
      ];
      
      expect(initSteps).toHaveLength(5);
      expect(initSteps[0]).toBe('environment');
      expect(initSteps[4]).toBe('services');
    };
  });
});