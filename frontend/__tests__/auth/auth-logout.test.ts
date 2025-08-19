/**
 * Auth Logout Flow Tests
 * ======================
 * Tests for authentication logout flows and dev logout flag management
 * 
 * BVJ: Enterprise segment - ensures security compliance, prevents auth vulnerabilities
 * Modular design: ≤300 lines, functions ≤8 lines
 */

// Import test setup with mocks FIRST
import './auth-test-setup';
import { authService } from '@/auth';
import {
  setupAuthTestEnvironment,
  resetAuthTestMocks,
  createMockAuthConfig,
  createMockToken,
  createSuccessResponse,
  createErrorResponse,
  createNetworkError,
  mockConsoleMethod,
  restoreConsoleMock,
  validateLogoutCall,
  expectLocalStorageRemove,
  validateTokenOperation,
  validateSecureLogout,
  mockAuthServiceClient,
  mockLogger
} from './auth-test-utils';

describe('Auth Logout Flow', () => {
  let testEnv: ReturnType<typeof setupAuthTestEnvironment>;
  let mockAuthConfig: ReturnType<typeof createMockAuthConfig>;
  let mockToken: string;

  beforeEach(() => {
    testEnv = setupAuthTestEnvironment();
    mockAuthConfig = createMockAuthConfig();
    mockToken = createMockToken();
    resetAuthTestMocks(testEnv);
    
    // Reset mocks
    Object.values(mockAuthServiceClient).forEach(mock => {
      if (jest.isMockFunction(mock)) {
        mock.mockReset();
      }
    });
    Object.values(mockLogger).forEach(mock => {
      if (jest.isMockFunction(mock)) {
        mock.mockReset();
      }
    });
  });

  afterAll(() => {
    jest.restoreAllMocks();
  });

  describe('handleLogout', () => {
    it('should perform logout successfully with token', async () => {
      testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
      mockAuthServiceClient.logout.mockResolvedValue({});

      await authService.handleLogout(mockAuthConfig);

      expect(mockAuthServiceClient.logout).toHaveBeenCalled();
      validateSecureLogout(testEnv.localStorageMock);
    });

    it('should handle logout without token', async () => {
      testEnv.localStorageMock.getItem.mockReturnValue(null);
      mockAuthServiceClient.logout.mockResolvedValue({});

      await authService.handleLogout(mockAuthConfig);

      expect(mockAuthServiceClient.logout).toHaveBeenCalled();
      validateSecureLogout(testEnv.localStorageMock);
    });

    it('should handle logout failure and still clear token', async () => {
      testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
      mockAuthServiceClient.logout.mockRejectedValue(new Error('Failed to logout'));

      await authService.handleLogout(mockAuthConfig);

      expect(mockLogger.error).toHaveBeenCalled();
      expect(mockLogger.error.mock.calls[0][0]).toContain('Error during logout');
      validateSecureLogout(testEnv.localStorageMock);
    });

    it('should handle logout network error and still clear token', async () => {
      testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
      mockAuthServiceClient.logout.mockRejectedValue(createNetworkError('Network error'));

      await authService.handleLogout(mockAuthConfig);

      expect(mockLogger.error).toHaveBeenCalled();
      expect(mockLogger.error.mock.calls[0][0]).toContain('Error during logout');
      validateSecureLogout(testEnv.localStorageMock);
    });

    it('should handle concurrent logout operations', async () => {
      setupConcurrentLogout();
      const logoutPromises = createConcurrentLogoutPromises();
      await Promise.all(logoutPromises);
      verifyConcurrentLogoutResults();
    });
  });

  describe('Dev Logout Flag Management', () => {
    describe('getDevLogoutFlag', () => {
      it('should return true when flag is set', () => {
        setupTrueFlagValue();
        const result = authService.getDevLogoutFlag();
        validateFlagGet();
        expect(result).toBe(true);
      });

      it('should return false when flag is not set', () => {
        testEnv.localStorageMock.getItem.mockReturnValue(null);

        const result = authService.getDevLogoutFlag();

        expect(result).toBe(false);
      });

      it('should return false when flag is not "true"', () => {
        testEnv.localStorageMock.getItem.mockReturnValue('false');

        const result = authService.getDevLogoutFlag();

        expect(result).toBe(false);
      });

      it('should return false for other string values', () => {
        testEnv.localStorageMock.getItem.mockReturnValue('random-string');

        const result = authService.getDevLogoutFlag();

        expect(result).toBe(false);
      });
    });

    describe('setDevLogoutFlag', () => {
      it('should set dev logout flag', () => {
        authService.setDevLogoutFlag();

        validateTokenOperation(
          testEnv.localStorageMock,
          'set',
          'dev_logout_flag',
          'true'
        );
      });

      it('should handle multiple flag sets', () => {
        performMultipleFlagSets();
        verifyMultipleFlagSets();
      });
    });

    describe('clearDevLogoutFlag', () => {
      it('should clear dev logout flag', () => {
        authService.clearDevLogoutFlag();

        validateTokenOperation(
          testEnv.localStorageMock,
          'remove',
          'dev_logout_flag'
        );
      });

      it('should handle clearing non-existent flag', () => {
        setupNonExistentFlag();
        authService.clearDevLogoutFlag();
        verifyFlagRemoval();
      });
    });

    describe('Dev Flag Integration', () => {
      it('should handle complete dev flag cycle', () => {
        verifyInitialFlagState();
        performFlagSet();
        verifyFlagSetState();
        performFlagClear();
        verifyFlagClearState();
      });

      it('should handle rapid flag operations', () => {
        authService.setDevLogoutFlag();
        authService.clearDevLogoutFlag();
        authService.setDevLogoutFlag();

        expect(testEnv.localStorageMock.setItem).toHaveBeenCalledTimes(2);
        expect(testEnv.localStorageMock.removeItem).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Logout Flow Integration', () => {
    it('should handle logout with dev flag management', async () => {
      setupLogoutWithDevFlag();
      authService.setDevLogoutFlag();
      await authService.handleLogout(mockAuthConfig);
      verifyLogoutWithDevFlag();
    });

    it('should handle logout failure with dev flag management', async () => {
      setupFailedLogoutWithDevFlag();
      authService.setDevLogoutFlag();
      await authService.handleLogout(mockAuthConfig);
      verifyFailedLogoutCleanup();
    });
  });

  // Helper functions for test setup (≤8 lines each)
  function setupConcurrentLogout() {
    testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
    mockAuthServiceClient.logout.mockResolvedValue({});
  }

  function createConcurrentLogoutPromises() {
    return [
      authService.handleLogout(mockAuthConfig),
      authService.handleLogout(mockAuthConfig)
    ];
  }

  function verifyConcurrentLogoutResults() {
    expect(testEnv.localStorageMock.removeItem).toHaveBeenCalled();
    expect(mockAuthServiceClient.logout).toHaveBeenCalled();
  }

  function setupTrueFlagValue() {
    testEnv.localStorageMock.getItem.mockReturnValue('true');
  }

  function validateFlagGet() {
    validateTokenOperation(
      testEnv.localStorageMock,
      'get',
      'dev_logout_flag'
    );
  }

  function performMultipleFlagSets() {
    authService.setDevLogoutFlag();
    authService.setDevLogoutFlag();
  }

  function verifyMultipleFlagSets() {
    expect(testEnv.localStorageMock.setItem).toHaveBeenCalledTimes(2);
    expect(testEnv.localStorageMock.setItem).toHaveBeenCalledWith(
      'dev_logout_flag',
      'true'
    );
  }

  function setupNonExistentFlag() {
    testEnv.localStorageMock.getItem.mockReturnValue(null);
  }

  function verifyFlagRemoval() {
    expect(testEnv.localStorageMock.removeItem).toHaveBeenCalledWith(
      'dev_logout_flag'
    );
  }

  function verifyInitialFlagState() {
    testEnv.localStorageMock.getItem.mockReturnValue(null);
    expect(authService.getDevLogoutFlag()).toBe(false);
  }

  function performFlagSet() {
    authService.setDevLogoutFlag();
    testEnv.localStorageMock.getItem.mockReturnValue('true');
  }

  function verifyFlagSetState() {
    expect(authService.getDevLogoutFlag()).toBe(true);
  }

  function performFlagClear() {
    authService.clearDevLogoutFlag();
    testEnv.localStorageMock.getItem.mockReturnValue(null);
  }

  function verifyFlagClearState() {
    expect(authService.getDevLogoutFlag()).toBe(false);
  }

  function setupLogoutWithDevFlag() {
    testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
    testEnv.fetchMock.mockResolvedValue(createSuccessResponse({}));
  }

  function verifyLogoutWithDevFlag() {
    validateSecureLogout(testEnv.localStorageMock);
    expect(testEnv.localStorageMock.setItem).toHaveBeenCalledWith(
      'dev_logout_flag',
      'true'
    );
  }

  function setupFailedLogoutWithDevFlag() {
    testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
    mockAuthServiceClient.logout.mockRejectedValue(new Error('Failed to logout'));
  }

  function verifyFailedLogoutCleanup() {
    validateSecureLogout(testEnv.localStorageMock);
    expect(mockLogger.error).toHaveBeenCalled();
  }
});