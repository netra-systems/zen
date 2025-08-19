/**
 * Auth Login Flow Tests
 * =====================
 * Tests for authentication login flows: config, standard login, dev login
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
  createMockDevConfig,
  createMockToken,
  createMockDevLoginResponse,
  createSuccessResponse,
  createErrorResponse,
  createNetworkError,
  mockConsoleMethod,
  restoreConsoleMock,
  expectFetchCall,
  validateTokenOperation,
  validateDevLoginCall,
  validateSecureTokenStorage,
  mockAuthServiceClient,
  mockLogger
} from './auth-test-utils';

describe('Auth Login Flow', () => {
  let testEnv: ReturnType<typeof setupAuthTestEnvironment>;
  let mockAuthConfig: ReturnType<typeof createMockAuthConfig>;
  let mockToken: string;
  let mockDevLoginResponse: ReturnType<typeof createMockDevLoginResponse>;

  beforeEach(() => {
    testEnv = setupAuthTestEnvironment();
    mockAuthConfig = createMockAuthConfig();
    mockToken = createMockToken();
    mockDevLoginResponse = createMockDevLoginResponse();
    resetAuthTestMocks(testEnv);
    
    // Reset logger mocks
    Object.values(mockLogger).forEach(mock => {
      if (jest.isMockFunction(mock)) {
        mock.mockReset();
      }
    });
  });

  afterAll(() => {
    jest.restoreAllMocks();
  });

  describe('getAuthConfig', () => {
    beforeEach(() => {
      // Setup mock for auth service client
      mockAuthServiceClient.getConfig.mockReset();
    });

    it('should fetch auth config successfully', async () => {
      setupSuccessfulAuthConfig();
      const result = await authService.getAuthConfig();
      verifyAuthConfigCall();
      verifyAuthConfigResult(result);
    });

    it('should throw error when fetch fails', async () => {
      mockAuthServiceClient.getConfig.mockRejectedValue(
        new Error('HTTP 500: Failed to fetch auth configuration')
      );

      await expect(authService.getAuthConfig())
        .rejects.toThrow();
    });

    it('should handle network errors', async () => {
      mockAuthServiceClient.getConfig.mockRejectedValue(
        createNetworkError('Network error')
      );

      await expect(authService.getAuthConfig())
        .rejects.toThrow('Network error');
    });

    it('should handle empty auth config response', async () => {
      mockAuthServiceClient.getConfig.mockResolvedValue({});

      const result = await authService.getAuthConfig();
      
      // The auth service transforms the config, so it won't be empty
      expect(result).toHaveProperty('development_mode');
      expect(result).toHaveProperty('endpoints');
    });

    it('should handle malformed JSON response', async () => {
      mockAuthServiceClient.getConfig.mockRejectedValue(
        new Error('Invalid JSON')
      );

      await expect(authService.getAuthConfig())
        .rejects.toThrow('Invalid JSON');
    });
  });

  describe('handleDevLogin', () => {
    it('should perform dev login successfully', async () => {
      setupSuccessfulDevLogin();
      const result = await authService.handleDevLogin(mockAuthConfig);
      verifySuccessfulDevLogin(result);
    });

    it('should handle dev login failure with non-ok response', async () => {
      setupFailedDevLogin();
      const result = await authService.handleDevLogin(mockAuthConfig);
      verifyFailedDevLogin(result);
    });

    it('should handle dev login network error', async () => {
      setupNetworkErrorDevLogin();
      const result = await authService.handleDevLogin(mockAuthConfig);
      verifyNetworkErrorDevLogin(result);
    });

    it('should handle localStorage quota exceeded', async () => {
      setupQuotaExceededScenario();
      const result = await authService.handleDevLogin(mockAuthConfig);
      verifyQuotaExceededHandling(result);
      cleanupQuotaExceededTest();
    });

    it('should sanitize email input in dev login', async () => {
      testEnv.fetchMock.mockResolvedValue(
        createSuccessResponse(mockDevLoginResponse)
      );

      await authService.handleDevLogin(mockAuthConfig);

      const callBody = JSON.parse(
        testEnv.fetchMock.mock.calls[0][1].body
      );
      expect(callBody.email).toBe('dev@example.com');
    });
  });

  describe('handleLogin', () => {
    beforeEach(() => {
      mockAuthServiceClient.initiateLogin.mockReset();
    });

    it('should call handleLogin with correct config', () => {
      authService.handleLogin(mockAuthConfig);

      expect(mockAuthServiceClient.initiateLogin).toHaveBeenCalledWith('google');
    });

    it('should handle login with development mode config', () => {
      const devConfig = createMockDevConfig();
      
      authService.handleLogin(devConfig);

      expect(mockAuthServiceClient.initiateLogin).toHaveBeenCalledWith('google');
    });

    it('should handle login with production config', () => {
      authService.handleLogin(mockAuthConfig);

      expect(mockAuthServiceClient.initiateLogin).toHaveBeenCalledWith('google');
      expect(mockAuthConfig.development_mode).toBe(false);
    });

    it('should handle login with missing config', () => {
      const incompleteConfig = { ...mockAuthConfig };
      delete (incompleteConfig as any).endpoints;
      
      authService.handleLogin(incompleteConfig as any);

      expect(mockAuthServiceClient.initiateLogin).toHaveBeenCalledWith('google');
    });
  });

  describe('Login Flow Integration', () => {
    it('should handle complete login flow', async () => {
      setupCompleteLoginFlow();
      const config = await authService.getAuthConfig();
      verifyConfigProperties(config);
      performAndVerifyLogin(config);
    });

    it('should handle dev login flow', async () => {
      const devConfig = setupDevLoginFlow();
      const config = await authService.getAuthConfig();
      verifyDevConfigProperties(config);
      const result = await performDevLogin(config);
      verifyDevLoginResult(result);
    });

    it('should handle concurrent config requests', async () => {
      setupConcurrentRequests();
      const promises = createConcurrentConfigRequests();
      const results = await Promise.all(promises);
      verifyConcurrentResults(results);
      verifyConcurrentCallCount();
    });
  });

  // Helper functions for test setup (≤8 lines each)
  function setupSuccessfulAuthConfig() {
    mockAuthServiceClient.getConfig.mockResolvedValue(mockAuthConfig);
  }

  function verifyAuthConfigCall() {
    expect(mockAuthServiceClient.getConfig).toHaveBeenCalled();
  }

  function verifyAuthConfigResult(result: any) {
    expect(result).toEqual({
      development_mode: false,
      google_client_id: 'mock-google-client-id',
      endpoints: getExpectedEndpoints(),
      authorized_javascript_origins: ['http://localhost:3000'],
      authorized_redirect_uris: ['http://localhost:3000/callback']
    });
  }

  function getExpectedEndpoints() {
    return {
      login: 'http://localhost:8081/auth/login',
      logout: 'http://localhost:8081/auth/logout',
      callback: 'http://localhost:8081/auth/callback',
      token: 'http://localhost:8081/auth/token',
      user: 'http://localhost:8081/auth/me',
      dev_login: 'http://localhost:8081/auth/dev/login'
    };
  }

  function setupSuccessfulDevLogin() {
    testEnv.fetchMock.mockResolvedValue(
      createSuccessResponse(mockDevLoginResponse)
    );
  }

  function verifySuccessfulDevLogin(result: any) {
    validateDevLoginCall(testEnv.fetchMock, mockAuthConfig);
    validateSecureTokenStorage(testEnv.localStorageMock, mockToken);
    expect(result).toEqual(mockDevLoginResponse);
    expect(mockLogger.info).toHaveBeenCalled();
  }

  function setupFailedDevLogin() {
    testEnv.fetchMock.mockResolvedValue(createErrorResponse(401));
  }

  function verifyFailedDevLogin(result: any) {
    expect(mockLogger.error).toHaveBeenCalled();
    expect(mockLogger.error.mock.calls[0][0])
      .toContain('Dev login failed');
    expect(testEnv.localStorageMock.setItem).not.toHaveBeenCalled();
    expect(result).toBeNull();
  }

  function setupNetworkErrorDevLogin() {
    testEnv.fetchMock.mockRejectedValue(
      createNetworkError('Network error')
    );
  }

  function verifyNetworkErrorDevLogin(result: any) {
    expect(mockLogger.error).toHaveBeenCalled();
    expect(mockLogger.error.mock.calls[0][0])
      .toContain('Error during dev login');
    expect(testEnv.localStorageMock.setItem).not.toHaveBeenCalled();
    expect(result).toBeNull();
  }

  function setupQuotaExceededScenario() {
    testEnv.fetchMock.mockResolvedValue(
      createSuccessResponse(mockDevLoginResponse)
    );
    testEnv.localStorageMock.setItem.mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
  }

  function verifyQuotaExceededHandling(result: any) {
    expect(result).toBeNull();
    expect(mockLogger.error).toHaveBeenCalled();
    expect(mockLogger.error.mock.calls[0][0])
      .toContain('Error during dev login');
  }

  function cleanupQuotaExceededTest() {
    testEnv.localStorageMock.setItem.mockClear();
  }

  function setupCompleteLoginFlow() {
    mockAuthServiceClient.getConfig.mockResolvedValue(mockAuthConfig);
  }

  function verifyConfigProperties(config: any) {
    expect(config).toHaveProperty('development_mode');
    expect(config).toHaveProperty('endpoints');
  }

  function performAndVerifyLogin(config: any) {
    authService.handleLogin(config);
    expect(mockAuthServiceClient.initiateLogin).toHaveBeenCalledWith('google');
  }

  function setupDevLoginFlow() {
    const devConfig = createMockDevConfig();
    mockAuthServiceClient.getConfig.mockResolvedValue(devConfig);
    testEnv.fetchMock.mockResolvedValue(
      createSuccessResponse(mockDevLoginResponse)
    );
    return devConfig;
  }

  function verifyDevConfigProperties(config: any) {
    expect(config).toHaveProperty('development_mode');
  }

  function performDevLogin(config: any) {
    return authService.handleDevLogin(config);
  }

  function verifyDevLoginResult(result: any) {
    expect(result).toEqual(mockDevLoginResponse);
  }

  function setupConcurrentRequests() {
    mockAuthServiceClient.getConfig.mockResolvedValue(mockAuthConfig);
  }

  function createConcurrentConfigRequests() {
    return [
      authService.getAuthConfig(),
      authService.getAuthConfig(),
      authService.getAuthConfig()
    ];
  }

  function verifyConcurrentResults(results: any[]) {
    results.forEach(result => {
      expect(result).toHaveProperty('development_mode');
      expect(result).toHaveProperty('endpoints');
    });
  }

  function verifyConcurrentCallCount() {
    expect(mockAuthServiceClient.getConfig).toHaveBeenCalledTimes(3);
  }
});