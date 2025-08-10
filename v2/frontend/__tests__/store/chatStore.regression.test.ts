/**
 * Regression tests for chat store to prevent issues with message IDs
 */

import { renderHook, act } from '@testing-library/react';
import { useChatStore } from '@/store/chat';

describe('ChatStore Regression Tests', () => {
  beforeEach(() => {
    // Reset the store before each test
    act(() => {
      useChatStore.getState().reset();
    });
  });

  describe('Message ID Generation', () => {
    it('should never have empty string IDs when adding messages', () => {
      const { result } = renderHook(() => useChatStore());
      
      act(() => {
        // Test with empty string ID
        result.current.addMessage({
          id: '',
          type: 'user',
          content: 'Test message',
          created_at: new Date().toISOString(),
          displayed_to_user: true
        });
      });

      expect(result.current.messages[0].id).toBeTruthy();
      expect(result.current.messages[0].id).not.toBe('');
      expect(result.current.messages[0].id).toMatch(/^msg_\d+_[a-z0-9]+$/);
    });

    it('should never have undefined or null IDs when adding messages', () => {
      const { result } = renderHook(() => useChatStore());
      
      act(() => {
        // Test with undefined ID
        result.current.addMessage({
          id: undefined as any,
          type: 'user',
          content: 'Test message 1',
          created_at: new Date().toISOString(),
          displayed_to_user: true
        });
        
        // Test with null ID
        result.current.addMessage({
          id: null as any,
          type: 'agent',
          content: 'Test message 2',
          created_at: new Date().toISOString(),
          displayed_to_user: true
        });
      });

      expect(result.current.messages).toHaveLength(2);
      result.current.messages.forEach(msg => {
        expect(msg.id).toBeTruthy();
        expect(msg.id).not.toBe('');
        expect(msg.id).not.toBeNull();
        expect(msg.id).not.toBeUndefined();
      });
    });

    it('should generate unique IDs for all messages', () => {
      const { result } = renderHook(() => useChatStore());
      
      act(() => {
        // Add multiple messages rapidly
        for (let i = 0; i < 10; i++) {
          result.current.addMessage({
            id: '', // Empty ID should trigger generation
            type: i % 2 === 0 ? 'user' : 'agent',
            content: `Message ${i}`,
            created_at: new Date().toISOString(),
            displayed_to_user: true
          });
        }
      });

      const ids = result.current.messages.map(m => m.id);
      const uniqueIds = new Set(ids);
      
      // All IDs should be unique
      expect(uniqueIds.size).toBe(ids.length);
      
      // No empty IDs
      ids.forEach(id => {
        expect(id).toBeTruthy();
        expect(id).not.toBe('');
      });
    });

    it('should handle loadMessages with empty or missing IDs', () => {
      const { result } = renderHook(() => useChatStore());
      
      const messagesWithBadIds = [
        { id: '', role: 'user', content: 'Message 1', created_at: new Date().toISOString() },
        { id: null, role: 'assistant', content: 'Message 2', created_at: new Date().toISOString() },
        { id: undefined, role: 'user', content: 'Message 3', created_at: new Date().toISOString() },
        { role: 'assistant', content: 'Message 4', created_at: new Date().toISOString() }, // No ID field
        { id: '   ', role: 'user', content: 'Message 5', created_at: new Date().toISOString() }, // Whitespace ID
      ];

      act(() => {
        result.current.loadMessages(messagesWithBadIds);
      });

      expect(result.current.messages).toHaveLength(5);
      
      const ids = result.current.messages.map(m => m.id);
      const uniqueIds = new Set(ids);
      
      // All IDs should be unique
      expect(uniqueIds.size).toBe(ids.length);
      
      // No empty or whitespace-only IDs
      ids.forEach(id => {
        expect(id).toBeTruthy();
        expect(id.trim()).not.toBe('');
      });
    });

    it('should handle loadThreadMessages with empty or missing IDs', () => {
      const { result } = renderHook(() => useChatStore());
      
      const threadMessages = [
        { id: '', type: 'user', content: 'Thread message 1', displayed_to_user: true },
        { id: '  ', type: 'agent', content: 'Thread message 2', displayed_to_user: true },
        { type: 'user', content: 'Thread message 3', displayed_to_user: true },
      ];

      act(() => {
        result.current.loadThreadMessages(threadMessages as any);
      });

      expect(result.current.messages).toHaveLength(3);
      
      const ids = result.current.messages.map(m => m.id);
      const uniqueIds = new Set(ids);
      
      // All IDs should be unique
      expect(uniqueIds.size).toBe(ids.length);
      
      // No empty IDs
      ids.forEach(id => {
        expect(id).toBeTruthy();
        expect(id.trim()).not.toBe('');
      });
    });

    it('should preserve valid IDs when loading messages', () => {
      const { result } = renderHook(() => useChatStore());
      
      const validId = 'valid_msg_123';
      const messages = [
        { id: validId, role: 'user', content: 'Message with valid ID', created_at: new Date().toISOString() },
        { id: '', role: 'assistant', content: 'Message with empty ID', created_at: new Date().toISOString() },
      ];

      act(() => {
        result.current.loadMessages(messages);
      });

      // Valid ID should be preserved
      expect(result.current.messages[0].id).toBe(validId);
      
      // Empty ID should be replaced
      expect(result.current.messages[1].id).not.toBe('');
      expect(result.current.messages[1].id).toBeTruthy();
    });
  });

  describe('React Key Warnings Prevention', () => {
    it('should ensure all messages can be used as React keys', () => {
      const { result } = renderHook(() => useChatStore());
      
      // Simulate various message additions that could cause key issues
      act(() => {
        result.current.addMessage({ id: '', type: 'user', content: 'Test 1', displayed_to_user: true } as any);
        result.current.addMessage({ id: null, type: 'agent', content: 'Test 2', displayed_to_user: true } as any);
        result.current.addMessage({ type: 'system', content: 'Test 3', displayed_to_user: true } as any);
      });

      // Simulate using messages as React keys
      const keys = result.current.messages.map(msg => msg.id);
      
      // All keys should be valid strings
      keys.forEach(key => {
        expect(typeof key).toBe('string');
        expect(key.length).toBeGreaterThan(0);
      });

      // No duplicate keys (would cause React warning)
      const uniqueKeys = new Set(keys);
      expect(uniqueKeys.size).toBe(keys.length);
    });
  });
});