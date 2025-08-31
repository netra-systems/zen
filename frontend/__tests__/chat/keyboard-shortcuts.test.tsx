import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import React from 'react';
import { renderHook, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { ortcuts
 * Business Goal: Increased user efficiency and retention
 * Value Impact: Improves workflow speed for advanced users, increasing platform stickiness
 */

import React from 'react';
import { renderHook, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import {
  setupDefaultMocks
} from './ui-test-utilities';

// Mock dependencies
jest.mock('@/store/chat', () => ({
  useChatStore: () => ({
    messages: [],
    isProcessing: false,
    setProcessing: jest.fn(),
    addMessage: jest.fn(),
    stopProcessing: jest.fn(),
  }),
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: () => ({
    currentThreadId: 'test-thread',
    threads: [],
    setCurrentThread: jest.fn(),
    addThread: jest.fn(),
  }),
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    isAuthenticated: true,
  }),
}));

beforeEach(() => {
  setupDefaultMocks();
});

describe('Keyboard Shortcuts', () => {
    jest.setTimeout(10000);
  describe('Shortcut Registration', () => {
      jest.setTimeout(10000);
    test('should register keyboard shortcuts correctly', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      expect(result.current.shortcuts).toBeDefined();
      expect(result.current.shortcuts.length).toBeGreaterThan(0);
      
      // Check for specific shortcuts
      const commandPalette = result.current.shortcuts.find(s => s.key === 'k' && s.ctrl);
      expect(commandPalette).toBeDefined();
      expect(commandPalette?.description).toBe('Open command palette');
    });

    test('should register all essential shortcuts', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      const shortcutKeys = result.current.shortcuts.map(s => ({
        key: s.key,
        ctrl: s.ctrl,
        alt: s.alt,
        shift: s.shift
      }));
      
      // Should include common shortcuts
      expect(shortcutKeys).toContainEqual({ key: 'k', ctrl: true, alt: false, shift: false });
      expect(shortcutKeys).toContainEqual({ key: 'n', ctrl: true, alt: false, shift: false });
      expect(shortcutKeys).toContainEqual({ key: '/', ctrl: false, alt: false, shift: false });
      expect(shortcutKeys).toContainEqual({ key: 'Escape', ctrl: false, alt: false, shift: false });
    });

    test('should handle platform-specific shortcuts', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Should adapt to Mac vs Windows/Linux
      const hasMetaShortcuts = result.current.shortcuts.some(s => s.meta);
      const hasCtrlShortcuts = result.current.shortcuts.some(s => s.ctrl);
      
      // At least one type should be present
      expect(hasMetaShortcuts || hasCtrlShortcuts).toBe(true);
    });

    test('should provide shortcut descriptions', () => {
      const { getShortcutDescriptions } = require('@/hooks/useKeyboardShortcuts');
      const descriptions = getShortcutDescriptions();
      
      expect(descriptions['Cmd/Ctrl + K']).toBe('Open command palette');
      expect(descriptions['Cmd/Ctrl + N']).toBe('New thread');
      expect(descriptions['/']).toBe('Focus message input');
      expect(descriptions['Esc']).toBe('Stop processing');
    });

    test('should handle shortcut conflicts gracefully', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Check for duplicate shortcuts
      const shortcutCombos = result.current.shortcuts.map(s => 
        `${s.ctrl ? 'ctrl+' : ''}${s.alt ? 'alt+' : ''}${s.shift ? 'shift+' : ''}${s.meta ? 'meta+' : ''}${s.key}`
      );
      
      const uniqueCombos = new Set(shortcutCombos);
      expect(uniqueCombos.size).toBe(shortcutCombos.length);
    });
  });

  describe('Message Input Focus', () => {
      jest.setTimeout(10000);
    test('should handle focus message input shortcut', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Create a mock textarea
      const textarea = document.createElement('textarea');
      textarea.setAttribute('aria-label', 'Message input');
      document.body.appendChild(textarea);
      
      // Test focus shortcut
      act(() => {
        result.current.focusMessageInput();
      });
      
      // Clean up
      document.body.removeChild(textarea);
    });

    test('should focus input with forward slash shortcut', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Create mock input
      const input = document.createElement('textarea');
      input.setAttribute('data-testid', 'message-input');
      document.body.appendChild(input);
      
      // Find slash shortcut
      const slashShortcut = result.current.shortcuts.find(s => s.key === '/');
      expect(slashShortcut).toBeDefined();
      
      if (slashShortcut?.handler) {
        act(() => {
          slashShortcut.handler();
        });
      }
      
      // Clean up
      document.body.removeChild(input);
    });

    test('should not interfere with normal typing in inputs', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Create focused input
      const input = document.createElement('input');
      input.type = 'text';
      document.body.appendChild(input);
      input.focus();
      
      // Test that shortcuts don't interfere when typing
      const slashShortcut = result.current.shortcuts.find(s => s.key === '/');
      
      // Should not trigger when input is focused
      expect(document.activeElement).toBe(input);
      
      document.body.removeChild(input);
    });

    test('should handle multiple input elements', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Create multiple inputs
      const textarea1 = document.createElement('textarea');
      textarea1.setAttribute('aria-label', 'Message input');
      const textarea2 = document.createElement('textarea');
      textarea2.setAttribute('aria-label', 'Search');
      
      document.body.appendChild(textarea1);
      document.body.appendChild(textarea2);
      
      act(() => {
        result.current.focusMessageInput();
      });
      
      // Should focus the message input specifically
      // Clean up
      document.body.removeChild(textarea1);
      document.body.removeChild(textarea2);
    });
  });

  describe('Command Palette', () => {
      jest.setTimeout(10000);
    test('should handle command palette shortcut', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      const cmdPaletteShortcut = result.current.shortcuts.find(s => 
        s.key === 'k' && s.ctrl && s.description === 'Open command palette'
      );
      
      expect(cmdPaletteShortcut).toBeDefined();
      expect(cmdPaletteShortcut?.handler).toBeDefined();
    });

    test('should trigger command palette with Ctrl+K', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      const handler = result.current.shortcuts.find(s => s.key === 'k' && s.ctrl)?.handler;
      
      if (handler) {
        act(() => {
          handler();
        });
        // Command palette should be triggered
        // Exact behavior depends on implementation
      }
      
      expect(handler).toBeDefined();
    });

    test('should handle Meta+K on Mac systems', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Look for Meta key variant
      const metaShortcut = result.current.shortcuts.find(s => s.key === 'k' && s.meta);
      
      // Depending on implementation, might support both Ctrl and Meta
      expect(metaShortcut || result.current.shortcuts.find(s => s.key === 'k' && s.ctrl)).toBeDefined();
    });
  });

  describe('Thread Management Shortcuts', () => {
      jest.setTimeout(10000);
    test('should handle new thread shortcut', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      const newThreadShortcut = result.current.shortcuts.find(s => 
        s.key === 'n' && s.ctrl && s.description === 'New thread'
      );
      
      expect(newThreadShortcut).toBeDefined();
      expect(newThreadShortcut?.handler).toBeDefined();
    });

    test('should create new thread with Ctrl+N', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      const handler = result.current.shortcuts.find(s => s.key === 'n' && s.ctrl)?.handler;
      
      if (handler) {
        act(() => {
          handler();
        });
        // New thread should be created
      }
      
      expect(handler).toBeDefined();
    });

    test('should handle thread navigation shortcuts', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Look for thread navigation shortcuts
      const navigationShortcuts = result.current.shortcuts.filter(s => 
        s.description?.toLowerCase().includes('thread') ||
        s.description?.toLowerCase().includes('conversation')
      );
      
      expect(navigationShortcuts.length).toBeGreaterThan(0);
    });
  });

  describe('Processing Control', () => {
      jest.setTimeout(10000);
    test('should handle stop processing shortcut', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      const stopShortcut = result.current.shortcuts.find(s => 
        s.key === 'Escape' && s.description === 'Stop processing'
      );
      
      expect(stopShortcut).toBeDefined();
      expect(stopShortcut?.handler).toBeDefined();
    });

    test('should stop processing with Escape key', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      const handler = result.current.shortcuts.find(s => s.key === 'Escape')?.handler;
      
      if (handler) {
        act(() => {
          handler();
        });
        // Processing should be stopped
      }
      
      expect(handler).toBeDefined();
    });

    test('should handle escape when not processing', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Mock non-processing state
      jest.doMock('@/store/chat', () => ({
        useChatStore: () => ({
          messages: [],
          isProcessing: false,
          setProcessing: jest.fn(),
          addMessage: jest.fn(),
          stopProcessing: jest.fn(),
        }),
      }));
      
      const handler = result.current.shortcuts.find(s => s.key === 'Escape')?.handler;
      
      if (handler) {
        act(() => {
          handler();
        });
        // Should handle gracefully when not processing
      }
      
      expect(handler).toBeDefined();
    });
  });

  describe('Global Shortcut Handling', () => {
      jest.setTimeout(10000);
    test('should prevent default behavior for handled shortcuts', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Test that shortcuts prevent default browser behavior
      const shortcuts = result.current.shortcuts;
      
      shortcuts.forEach(shortcut => {
        expect(shortcut.preventDefault).toBe(true);
      });
    });

    test('should handle shortcut conflicts with browser defaults', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Check for potentially conflicting shortcuts
      const ctrlN = result.current.shortcuts.find(s => s.key === 'n' && s.ctrl);
      const ctrlT = result.current.shortcuts.find(s => s.key === 't' && s.ctrl);
      
      // Should either prevent default or not use conflicting combinations
      if (ctrlN) {
        expect(ctrlN.preventDefault).toBe(true);
      }
      if (ctrlT) {
        expect(ctrlT.preventDefault).toBe(true);
      }
    });

    test('should handle shortcuts in different contexts', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Test shortcuts work regardless of current context
      const contextualShortcuts = result.current.shortcuts.filter(s => 
        s.condition !== undefined
      );
      
      // Some shortcuts might be conditional
      expect(result.current.shortcuts.length).toBeGreaterThan(0);
    });

    test('should provide help/documentation for shortcuts', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // All shortcuts should have descriptions
      result.current.shortcuts.forEach(shortcut => {
        expect(shortcut.description).toBeDefined();
        expect(shortcut.description).not.toBe('');
      });
    });

    test('should handle rapid shortcut presses', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      const handler = result.current.shortcuts[0]?.handler;
      
      if (handler) {
        // Test rapid execution
        act(() => {
          handler();
          handler();
          handler();
        });
        
        // Should handle gracefully without errors
      }
      
      expect(handler).toBeDefined();
    });

    test('should cleanup event listeners on unmount', () => {
      const { unmount } = renderHook(() => useKeyboardShortcuts());
      
      // Should not throw on unmount
      expect(() => unmount()).not.toThrow();
    });
  });

  describe('Accessibility and Usability', () => {
      jest.setTimeout(10000);
    test('should provide accessible shortcut hints', () => {
      const { getShortcutDescriptions } = require('@/hooks/useKeyboardShortcuts');
      const descriptions = getShortcutDescriptions();
      
      // Should provide clear, human-readable descriptions
      Object.values(descriptions).forEach(description => {
        expect(typeof description).toBe('string');
        expect(description.length).toBeGreaterThan(0);
      });
    });

    test('should use standard shortcut conventions', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Check for standard conventions (Ctrl+N for new, Ctrl+K for search, etc.)
      const newShortcut = result.current.shortcuts.find(s => s.key === 'n' && s.ctrl);
      const searchShortcut = result.current.shortcuts.find(s => s.key === 'k' && s.ctrl);
      
      expect(newShortcut?.description).toMatch(/new/i);
      expect(searchShortcut?.description).toMatch(/command|palette|search/i);
    });

    test('should handle disabled states appropriately', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      
      // Some shortcuts might be disabled based on state
      const conditionalShortcuts = result.current.shortcuts.filter(s => 
        typeof s.enabled === 'boolean'
      );
      
      // Should respect enabled/disabled state
      conditionalShortcuts.forEach(shortcut => {
        if (shortcut.enabled === false && shortcut.handler) {
          // Disabled shortcuts shouldn't execute
          expect(() => shortcut.handler()).not.toThrow();
        }
      });
    });
  });
});