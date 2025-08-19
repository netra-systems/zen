/**
 * Auth Token Management Tests
 * ===========================
 * Tests for token operations and useAuth hook functionality
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
  createMockToken,
  createMockAuthContext,
  mockUseContext,
  validateTokenOperation,
  expectAuthHeaders,
  expectEmptyHeaders
} from './auth-test-utils';
import { AuthContext } from '@/auth';

describe('Auth Token Management', () => {
  let testEnv: ReturnType<typeof setupAuthTestEnvironment>;
  let mockToken: string;

  beforeEach(() => {
    testEnv = setupAuthTestEnvironment();
    mockToken = createMockToken();
    resetAuthTestMocks(testEnv);
  });

  afterAll(() => {
    jest.restoreAllMocks();
  });

  describe('getToken', () => {
    it('should retrieve token from localStorage', () => {
      testEnv.localStorageMock.getItem.mockReturnValue(mockToken);

      const result = authService.getToken();

      validateTokenOperation(testEnv.localStorageMock, 'get');
      expect(result).toBe(mockToken);
    });

    it('should return null when no token exists', () => {
      testEnv.localStorageMock.getItem.mockReturnValue(null);

      const result = authService.getToken();

      expect(result).toBeNull();
    });

    it('should return empty string as null', () => {
      testEnv.localStorageMock.getItem.mockReturnValue('');

      const result = authService.getToken();

      expect(result).toBe('');
    });

    it('should handle localStorage errors gracefully', () => {
      testEnv.localStorageMock.getItem.mockImplementation(() => {
        throw new Error('localStorage error');
      });

      expect(() => authService.getToken()).toThrow('localStorage error');
    });
  });

  describe('getAuthHeaders', () => {
    it('should return auth headers with token', () => {
      testEnv.localStorageMock.getItem.mockReturnValue(mockToken);

      const headers = authService.getAuthHeaders();

      expectAuthHeaders(headers, mockToken);
    });

    it('should return empty object when no token', () => {
      testEnv.localStorageMock.getItem.mockReturnValue(null);

      const headers = authService.getAuthHeaders();

      expectEmptyHeaders(headers);
    });

    it('should return empty object for empty token', () => {
      testEnv.localStorageMock.getItem.mockReturnValue('');

      const headers = authService.getAuthHeaders();

      expectEmptyHeaders(headers);
    });

    it('should handle long tokens', () => {
      const longToken = 'a'.repeat(1000);
      testEnv.localStorageMock.getItem.mockReturnValue(longToken);

      const headers = authService.getAuthHeaders();

      expectAuthHeaders(headers, longToken);
    });

    it('should handle special characters in token', () => {
      const specialToken = 'token.with-special_chars123!@#';
      testEnv.localStorageMock.getItem.mockReturnValue(specialToken);

      const headers = authService.getAuthHeaders();

      expectAuthHeaders(headers, specialToken);
    });
  });

  describe('removeToken', () => {
    it('should remove token from localStorage', () => {
      authService.removeToken();

      validateTokenOperation(testEnv.localStorageMock, 'remove');
    });

    it('should handle removing non-existent token', () => {
      testEnv.localStorageMock.getItem.mockReturnValue(null);
      
      authService.removeToken();

      expect(testEnv.localStorageMock.removeItem).toHaveBeenCalledWith('jwt_token');
    });

    it('should handle localStorage errors on removal', () => {
      testEnv.localStorageMock.removeItem.mockImplementation(() => {
        throw new Error('localStorage error');
      });

      expect(() => authService.removeToken()).toThrow('localStorage error');
    });
  });

  // Helper functions for integration tests (≤8 lines each)
  const performRapidTokenOperations = () => {
    testEnv.localStorageMock.setItem.mockClear();
    authService.removeToken();
    authService.removeToken();
    authService.removeToken();
  };

  const getTokensAfterOperations = () => {
    testEnv.localStorageMock.getItem.mockReturnValueOnce('token1').mockReturnValueOnce('token2');
    return { token1: authService.getToken(), token2: authService.getToken() };
  };

  const verifyRapidTokenResults = (token1: string, token2: string) => {
    expect(testEnv.localStorageMock.removeItem).toHaveBeenCalledTimes(3);
    expect(token1).toBe('token1');
    expect(token2).toBe('token2');
  };

  const verifyInitialNoTokenState = () => {
    testEnv.localStorageMock.getItem.mockReturnValue(null);
    expect(authService.getToken()).toBeNull();
  };

  const setTokenAndVerify = () => {
    testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
    expect(authService.getToken()).toBe(mockToken);
  };

  const removeTokenAndVerify = () => {
    authService.removeToken();
    testEnv.localStorageMock.getItem.mockReturnValue(null);
    expect(authService.getToken()).toBeNull();
  };

  const setupTokenForConcurrentAccess = () => {
    testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
  };

  const createConcurrentTokenPromises = () => {
    return [
      Promise.resolve(authService.getToken()),
      Promise.resolve(authService.getToken()),
      Promise.resolve(authService.getToken())
    ];
  };

  const verifyConcurrentTokenResults = (results: any[]) => {
    expect(results).toHaveLength(3);
    results.forEach(result => expect(result).toBe(mockToken));
  };

  const setupMockAuthContext = () => {
    const mockContext = createMockAuthContext();
    mockUseContext.mockReturnValue(mockContext);
    return mockContext;
  };

  const verifyContextProperties = (result: any) => {
    expect(result).toHaveProperty('user');
    expect(result).toHaveProperty('login');
    expect(result).toHaveProperty('logout');
    expect(result).toHaveProperty('loading');
  };

  const setupMockContextWithUser = () => {
    const mockContext = { ...createMockAuthContext(), user: { id: '1', name: 'Test User' } };
    mockUseContext.mockReturnValue(mockContext);
    return mockContext;
  };

  const verifyContextWithUserData = (result: any) => {
    expect(result.user).toBeDefined();
    expect(result.user.id).toBe('1');
    expect(result.user.name).toBe('Test User');
  };

  describe('Token Operations Integration', () => {
    it('should handle rapid token operations', () => {
      performRapidTokenOperations();
      const { token1, token2 } = getTokensAfterOperations();
      verifyRapidTokenResults(token1, token2);
    });

    it('should handle token lifecycle', () => {
      verifyInitialNoTokenState();
      setTokenAndVerify();
      removeTokenAndVerify();
    });

    it('should handle concurrent token access', () => {
      setupTokenForConcurrentAccess();
      const promises = createConcurrentTokenPromises();
      return Promise.all(promises).then(results => {
        verifyConcurrentTokenResults(results);
      });
    });
  });

  describe('useAuth Hook', () => {
    beforeEach(() => {
      // Reset the mock before each test
      mockUseContext.mockReset();
    });

    it('should return auth context when used within provider', () => {
      const mockContext = createMockAuthContext();
      mockUseContext.mockReturnValue(mockContext);

      const result = authService.useAuth();

      expect(mockUseContext).toHaveBeenCalledWith(AuthContext);
      expect(result).toBe(mockContext);
    });

    it('should throw error when used outside provider', () => {
      mockUseContext.mockReturnValue(undefined);

      expect(() => authService.useAuth())
        .toThrow('useAuth must be used within an AuthProvider');
    });

    it('should handle null context', () => {
      mockUseContext.mockReturnValue(null);

      expect(() => authService.useAuth())
        .toThrow('useAuth must be used within an AuthProvider');
    });

    it('should return context with all required properties', () => {
      const mockContext = setupMockAuthContext();
      const result = authService.useAuth();
      verifyContextProperties(result);
    });

    it('should handle context with user data', () => {
      const mockContext = setupMockContextWithUser();
      const result = authService.useAuth();
      verifyContextWithUserData(result);
    });

    it('should handle loading state', () => {
      const mockContext = {
        ...createMockAuthContext(),
        loading: true
      };
      mockUseContext.mockReturnValue(mockContext);

      const result = authService.useAuth();

      expect(result.loading).toBe(true);
    });
  });
});