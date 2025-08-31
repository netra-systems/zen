/**
 * Test using jest.setup.js existing mock system
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { jest } from '@jest/globals';

// Import the component
import HomePage from '@/app/page';

import { useAuth } from '@/auth/context';

describe('Landing Page - Using Setup Mocks', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should work with existing jest.setup.js mocks', async () => {
    console.log('Testing with existing jest.setup.js mocks');
    
    render(<HomePage />);
    
    // The jest.setup.js mock should make this component redirect to /chat
    // because it sets user: mockUser and loading: false
    
    screen.debug();
    
    // According to jest.setup.js, the component should redirect to chat
    // because user is set to mockUser (not null)
  });
  
  it('should test if we can access the mocked auth service', () => {
    // Try to import the auth service and see what we get
    const { authService } = require('@/auth');
    console.log('authService:', authService);
    console.log('authService.useAuth:', typeof authService.useAuth);
    
    if (typeof authService.useAuth === 'function') {
      const result = useAuth();
      console.log('useAuth() result:', result);
    }
  });
  
  it('should test auth service through different import methods', () => {
    // Test different import approaches
    try {
      const authModule = require('@/auth');
      console.log('authModule keys:', Object.keys(authModule));
    } catch (e) {
      console.log('Error importing @/auth:', e);
    }
    
    try {
      const authServiceModule = require('@/auth/service');
      console.log('authServiceModule keys:', Object.keys(authServiceModule));
    } catch (e) {
      console.log('Error importing @/auth/service:', e);
    }
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});