/**
 * Auth Flow Test Utilities
 * Helper functions for authentication flow testing
 */

import React from 'react';
import { render } from '@testing-library/react';
import { jest } from '@jest/globals';

export const createLoginComponent = () => {
  return () => <div data-testid="login-component">Login</div>;
};

export const createLogoutComponent = () => {
  return () => <div data-testid="logout-component">Logout</div>;
};

export const performLoginAction = jest.fn();
export const performLogoutAction = jest.fn();
export const verifyInitialUnauthenticatedState = jest.fn();
export const verifyInitialAuthenticatedState = jest.fn();
export const verifySuccessfulLogin = jest.fn();
export const verifySuccessfulLogout = jest.fn();
export const setupAuthenticatedState = jest.fn();
export const performLoginFlow = jest.fn();
export const verifyStatePersistence = jest.fn();
export const performPageRefresh = jest.fn();
export const verifyStateRestoration = jest.fn();
export const performOnboardingLogin = jest.fn();
export const verifyOnboardingAuthState = jest.fn();
export const simulateFirstThreadCreation = jest.fn();
export const expectOnboardingFlowComplete = jest.fn();
export const simulateSessionTimeout = jest.fn();
export const verifySessionTimeoutHandling = jest.fn();
export const performReauthentication = jest.fn();
export const expectContinuedOnboarding = jest.fn();
export const createMockAuthStore = jest.fn();
export const setupReactiveAuthStore = jest.fn();