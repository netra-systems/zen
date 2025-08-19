/**
 * Auth Token Test Helper Functions
 * ===============================
 * Extracted helper functions for auth token tests (≤8 lines each)
 */

export function performRapidTokenOperations(authService: any, testEnv: any, mockToken: string) {
  authService.removeToken();
  testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
}

export function getTokensAfterOperations(authService: any, testEnv: any) {
  const token1 = authService.getToken();
  authService.removeToken();
  testEnv.localStorageMock.getItem.mockReturnValue(null);
  const token2 = authService.getToken();
  return { token1, token2 };
}

export function verifyRapidTokenResults(token1: any, token2: any, mockToken: string, testEnv: any) {
  expect(token1).toBe(mockToken);
  expect(token2).toBeNull();
  expect(testEnv.localStorageMock.removeItem).toHaveBeenCalledTimes(2);
}

export function verifyInitialNoTokenState(authService: any, testEnv: any, expectEmptyHeaders: any) {
  testEnv.localStorageMock.getItem.mockReturnValue(null);
  expect(authService.getToken()).toBeNull();
  expectEmptyHeaders(authService.getAuthHeaders());
}

export function setTokenAndVerify(authService: any, testEnv: any, mockToken: string, expectAuthHeaders: any) {
  testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
  expect(authService.getToken()).toBe(mockToken);
  expectAuthHeaders(authService.getAuthHeaders(), mockToken);
}

export function removeTokenAndVerify(authService: any, testEnv: any) {
  authService.removeToken();
  testEnv.localStorageMock.getItem.mockReturnValue(null);
  expect(authService.getToken()).toBeNull();
}

export function setupTokenForConcurrentAccess(testEnv: any, mockToken: string) {
  testEnv.localStorageMock.getItem.mockReturnValue(mockToken);
}

export function createConcurrentTokenPromises(authService: any) {
  return [
    Promise.resolve(authService.getToken()),
    Promise.resolve(authService.getAuthHeaders()),
    Promise.resolve(authService.getToken())
  ];
}

export function verifyConcurrentTokenResults(results: any[], mockToken: string, expectAuthHeaders: any) {
  expect(results[0]).toBe(mockToken);
  expectAuthHeaders(results[1], mockToken);
  expect(results[2]).toBe(mockToken);
}