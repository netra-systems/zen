/**
 * Test Utilities Integration Test
 * Verifies that all new test utilities work correctly together
 */

import { describe, it, expect } from '@jest/globals';
import {
  renderWithProviders,
  setupCustomMatchers
} from './index';
import { 
  createMockUser,
  createMockThread,
  createMockMessage,
  createAuthenticatedState
} from './mock-factories';

// Setup custom matchers for this test
setupCustomMatchers();

describe('Test Utilities Integration', () => {
  describe('Mock Factories', () => {
    it('creates valid mock user', () => {
      const user = createMockUser({ name: 'Test User', role: 'enterprise' });
      
      expect(user).toHaveProperty('id');
      expect(user).toHaveProperty('email');
      expect(user.name).toBe('Test User');
      expect(user.role).toBe('enterprise');
      expect(user.created_at).toBeTruthy();
    });

    it('creates valid mock thread', () => {
      const thread = createMockThread({ title: 'Test Thread' });
      
      expect(thread).toHaveProperty('id');
      expect(thread.title).toBe('Test Thread');
      expect(thread.user_id).toBeTruthy();
      expect(thread.created_at).toBeTruthy();
    });

    it('creates valid mock message', () => {
      const message = createMockMessage({ content: 'Test message', role: 'user' });
      
      expect(message).toHaveProperty('id');
      expect(message.content).toBe('Test message');
      expect(message.role).toBe('user');
      expect(message.created_at).toBeTruthy();
    });
  });

  describe('Store State Factories', () => {
    it('creates authenticated state', () => {
      const state = createAuthenticatedState();
      
      expect(state.auth.isAuthenticated).toBe(true);
      expect(state.auth.user).toBeTruthy();
      expect(state.auth.token).toBeTruthy();
      expect(state.chat.threads).toHaveLength(3);
      expect(state.connection.isConnected).toBe(true);
    });
  });

  describe('Custom Matchers', () => {
    it('validates messages with custom matchers', () => {
      const message = createMockMessage({ 
        content: 'Test', 
        role: 'user',
        metadata: { source: 'test' }
      });
      
      expect(message).toBeValidMessage('user');
      expect(message).toHaveMessageMetadata('source', 'test');
    });
  });
});