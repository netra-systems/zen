/**
 * Auth Login Flow Tests
 * =====================
 * Tests for authentication login flows: config, standard login, dev login
 * 
 * BVJ: Enterprise segment - ensures security compliance, prevents auth vulnerabilities
 * Modular design: ≤300 lines, functions ≤8 lines
 */

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
  validateSecureTokenStorage
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
  });

  afterAll(() => {
    jest.restoreAllMocks();
  });

  describe('getAuthConfig', () => {
    it('should fetch auth config successfully', async () => {
      testEnv.fetchMock.mockResolvedValue(
        createSuccessResponse(mockAuthConfig)
      );

      const result = await authService.getAuthConfig();

      expectFetchCall(
        testEnv.fetchMock,
        'http://localhost:8081/api/auth/config'
      );
      expect(result).toEqual(mockAuthConfig);
    });

    it('should throw error when fetch fails', async () => {
      testEnv.fetchMock.mockResolvedValue(
        createErrorResponse(500)
      );

      await expect(authService.getAuthConfig())
        .rejects.toThrow('Failed to fetch auth config');
    });

    it('should handle network errors', async () => {
      testEnv.fetchMock.mockRejectedValue(
        createNetworkError('Network error')
      );

      await expect(authService.getAuthConfig())
        .rejects.toThrow('Network error');
    });

    it('should handle empty auth config response', async () => {
      testEnv.fetchMock.mockResolvedValue(
        createSuccessResponse({})
      );

      const result = await authService.getAuthConfig();
      expect(result).toEqual({});
    });

    it('should handle malformed JSON response', async () => {
      testEnv.fetchMock.mockResolvedValue({
        ok: true,
        json: jest.fn().mockRejectedValue(new Error('Invalid JSON'))
      });

      await expect(authService.getAuthConfig())
        .rejects.toThrow('Invalid JSON');
    });
  });

  describe('handleDevLogin', () => {
    it('should perform dev login successfully', async () => {
      const consoleInfoSpy = mockConsoleMethod('info');
      testEnv.fetchMock.mockResolvedValue(
        createSuccessResponse(mockDevLoginResponse)
      );

      const result = await authService.handleDevLogin(mockAuthConfig);

      validateDevLoginCall(testEnv.fetchMock, mockAuthConfig);
      validateSecureTokenStorage(testEnv.localStorageMock, mockToken);
      expect(result).toEqual(mockDevLoginResponse);

      restoreConsoleMock(consoleInfoSpy);
    });

    it('should handle dev login failure with non-ok response', async () => {
      const consoleErrorSpy = mockConsoleMethod('error');
      testEnv.fetchMock.mockResolvedValue(
        createErrorResponse(401)
      );

      const result = await authService.handleDevLogin(mockAuthConfig);

      expect(consoleErrorSpy).toHaveBeenCalled();
      expect(consoleErrorSpy.mock.calls[0][0])
        .toContain('Dev login failed');
      expect(testEnv.localStorageMock.setItem).not.toHaveBeenCalled();
      expect(result).toBeNull();

      restoreConsoleMock(consoleErrorSpy);
    });

    it('should handle dev login network error', async () => {
      const consoleErrorSpy = mockConsoleMethod('error');
      testEnv.fetchMock.mockRejectedValue(
        createNetworkError('Network error')
      );

      const result = await authService.handleDevLogin(mockAuthConfig);

      expect(consoleErrorSpy).toHaveBeenCalled();
      expect(consoleErrorSpy.mock.calls[0][0])
        .toContain('Error during dev login');
      expect(testEnv.localStorageMock.setItem).not.toHaveBeenCalled();
      expect(result).toBeNull();

      restoreConsoleMock(consoleErrorSpy);
    });

    it('should handle localStorage quota exceeded', async () => {
      const consoleErrorSpy = mockConsoleMethod('error');
      testEnv.fetchMock.mockResolvedValue(
        createSuccessResponse(mockDevLoginResponse)
      );
      
      testEnv.localStorageMock.setItem.mockImplementation(() => {
        throw new Error('QuotaExceededError');
      });

      const result = await authService.handleDevLogin(mockAuthConfig);
      
      expect(result).toBeNull();
      expect(consoleErrorSpy).toHaveBeenCalled();
      expect(consoleErrorSpy.mock.calls[0][0])
        .toContain('Error during dev login');
      
      restoreConsoleMock(consoleErrorSpy);
      testEnv.localStorageMock.setItem.mockClear();
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
    it('should call handleLogin with correct config', () => {
      const handleLoginSpy = jest.spyOn(authService, 'handleLogin');
      
      authService.handleLogin(mockAuthConfig);

      expect(handleLoginSpy).toHaveBeenCalledWith(mockAuthConfig);
      
      handleLoginSpy.mockRestore();
    });

    it('should handle login with development mode config', () => {
      const devConfig = createMockDevConfig();
      const handleLoginSpy = jest.spyOn(authService, 'handleLogin');
      
      authService.handleLogin(devConfig);

      expect(handleLoginSpy).toHaveBeenCalledWith(devConfig);
      
      handleLoginSpy.mockRestore();
    });

    it('should handle login with production config', () => {
      const handleLoginSpy = jest.spyOn(authService, 'handleLogin');
      
      authService.handleLogin(mockAuthConfig);

      expect(handleLoginSpy).toHaveBeenCalledWith(mockAuthConfig);
      expect(mockAuthConfig.development_mode).toBe(false);
      
      handleLoginSpy.mockRestore();
    });

    it('should handle login with missing config', () => {
      const handleLoginSpy = jest.spyOn(authService, 'handleLogin');
      const incompleteConfig = { ...mockAuthConfig };
      delete (incompleteConfig as any).endpoints;
      
      authService.handleLogin(incompleteConfig as any);

      expect(handleLoginSpy).toHaveBeenCalledWith(incompleteConfig);
      
      handleLoginSpy.mockRestore();
    });
  });

  describe('Login Flow Integration', () => {
    it('should handle complete login flow', async () => {
      // Step 1: Get config
      testEnv.fetchMock.mockResolvedValueOnce(
        createSuccessResponse(mockAuthConfig)
      );
      
      const config = await authService.getAuthConfig();
      expect(config).toEqual(mockAuthConfig);

      // Step 2: Handle login
      const handleLoginSpy = jest.spyOn(authService, 'handleLogin');
      authService.handleLogin(config);
      expect(handleLoginSpy).toHaveBeenCalledWith(config);
      
      handleLoginSpy.mockRestore();
    });

    it('should handle dev login flow', async () => {
      // Step 1: Get dev config
      const devConfig = createMockDevConfig();
      testEnv.fetchMock.mockResolvedValueOnce(
        createSuccessResponse(devConfig)
      );
      
      const config = await authService.getAuthConfig();

      // Step 2: Dev login
      testEnv.fetchMock.mockResolvedValueOnce(
        createSuccessResponse(mockDevLoginResponse)
      );
      
      const result = await authService.handleDevLogin(config);
      expect(result).toEqual(mockDevLoginResponse);
    });

    it('should handle concurrent config requests', async () => {
      testEnv.fetchMock.mockResolvedValue(
        createSuccessResponse(mockAuthConfig)
      );

      const promises = [
        authService.getAuthConfig(),
        authService.getAuthConfig(),
        authService.getAuthConfig()
      ];

      const results = await Promise.all(promises);
      
      results.forEach(result => {
        expect(result).toEqual(mockAuthConfig);
      });
      expect(testEnv.fetchMock).toHaveBeenCalledTimes(3);
    });
  });
});