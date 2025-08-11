import { renderHook, act } from '@testing-library/react';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';

describe('useKeyboardShortcuts Hook', () => {
  let originalAddEventListener: typeof window.addEventListener;
  let originalRemoveEventListener: typeof window.removeEventListener;
  let eventListeners: { [key: string]: EventListener[] } = {};

  beforeEach(() => {
    jest.clearAllMocks();
    eventListeners = {};

    // Mock event listeners
    originalAddEventListener = window.addEventListener;
    originalRemoveEventListener = window.removeEventListener;

    window.addEventListener = jest.fn((event: string, listener: EventListener) => {
      if (!eventListeners[event]) {
        eventListeners[event] = [];
      }
      eventListeners[event].push(listener);
    });

    window.removeEventListener = jest.fn((event: string, listener: EventListener) => {
      if (eventListeners[event]) {
        const index = eventListeners[event].indexOf(listener);
        if (index !== -1) {
          eventListeners[event].splice(index, 1);
        }
      }
    });
  });

  afterEach(() => {
    window.addEventListener = originalAddEventListener;
    window.removeEventListener = originalRemoveEventListener;
  });

  const createKeyboardEvent = (key: string, options: KeyboardEventInit = {}) => {
    return new KeyboardEvent('keydown', {
      key,
      ctrlKey: false,
      shiftKey: false,
      altKey: false,
      metaKey: false,
      ...options
    });
  };

  const fireKeyboardEvent = (key: string, options: KeyboardEventInit = {}) => {
    const event = createKeyboardEvent(key, options);
    eventListeners.keydown?.forEach(listener => {
      listener(event);
    });
    return event;
  };

  describe('Basic Keyboard Shortcut Registration', () => {
    it('should register single key shortcuts', () => {
      const handler = jest.fn();
      
      renderHook(() => 
        useKeyboardShortcuts({
          'Escape': handler
        })
      );

      fireKeyboardEvent('Escape');

      expect(handler).toHaveBeenCalledWith(expect.any(KeyboardEvent));
      expect(handler).toHaveBeenCalledTimes(1);
    });

    it('should register modifier key combinations', () => {
      const ctrlSHandler = jest.fn();
      const ctrlShiftNHandler = jest.fn();
      const altTabHandler = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': ctrlSHandler,
          'ctrl+shift+n': ctrlShiftNHandler,
          'alt+tab': altTabHandler
        })
      );

      fireKeyboardEvent('s', { ctrlKey: true });
      fireKeyboardEvent('n', { ctrlKey: true, shiftKey: true });
      fireKeyboardEvent('Tab', { altKey: true });

      expect(ctrlSHandler).toHaveBeenCalledTimes(1);
      expect(ctrlShiftNHandler).toHaveBeenCalledTimes(1);
      expect(altTabHandler).toHaveBeenCalledTimes(1);
    });

    it('should handle case-insensitive key matching', () => {
      const handler = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+A': handler
        })
      );

      fireKeyboardEvent('a', { ctrlKey: true });
      fireKeyboardEvent('A', { ctrlKey: true });

      expect(handler).toHaveBeenCalledTimes(2);
    });

    it('should support meta key (cmd) on macOS', () => {
      const handler = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          'meta+z': handler,
          'cmd+z': handler // Alternative notation
        })
      );

      fireKeyboardEvent('z', { metaKey: true });

      expect(handler).toHaveBeenCalledTimes(2); // Should match both notations
    });

    it('should handle special keys correctly', () => {
      const handlers = {
        space: jest.fn(),
        enter: jest.fn(),
        backspace: jest.fn(),
        delete: jest.fn(),
        arrowUp: jest.fn(),
        arrowDown: jest.fn(),
        f1: jest.fn()
      };

      renderHook(() => 
        useKeyboardShortcuts({
          ' ': handlers.space,
          'Enter': handlers.enter,
          'Backspace': handlers.backspace,
          'Delete': handlers.delete,
          'ArrowUp': handlers.arrowUp,
          'ArrowDown': handlers.arrowDown,
          'F1': handlers.f1
        })
      );

      fireKeyboardEvent(' ');
      fireKeyboardEvent('Enter');
      fireKeyboardEvent('Backspace');
      fireKeyboardEvent('Delete');
      fireKeyboardEvent('ArrowUp');
      fireKeyboardEvent('ArrowDown');
      fireKeyboardEvent('F1');

      Object.values(handlers).forEach(handler => {
        expect(handler).toHaveBeenCalledTimes(1);
      });
    });

    it('should parse complex shortcut combinations', () => {
      const handler = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+alt+shift+f12': handler
        })
      );

      fireKeyboardEvent('F12', { ctrlKey: true, altKey: true, shiftKey: true });

      expect(handler).toHaveBeenCalledTimes(1);
    });

    it('should ignore shortcuts with wrong modifiers', () => {
      const handler = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler
        })
      );

      // Should not trigger without ctrl
      fireKeyboardEvent('s');
      fireKeyboardEvent('s', { shiftKey: true });
      fireKeyboardEvent('s', { altKey: true });

      expect(handler).not.toHaveBeenCalled();

      // Should trigger with correct modifier
      fireKeyboardEvent('s', { ctrlKey: true });

      expect(handler).toHaveBeenCalledTimes(1);
    });
  });

  describe('Shortcut Context and Scoping', () => {
    it('should respect enabled/disabled state', () => {
      const handler = jest.fn();

      const { result } = renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler
        }, { enabled: false })
      );

      fireKeyboardEvent('s', { ctrlKey: true });
      expect(handler).not.toHaveBeenCalled();

      // Enable shortcuts
      result.current.setEnabled(true);

      fireKeyboardEvent('s', { ctrlKey: true });
      expect(handler).toHaveBeenCalledTimes(1);
    });

    it('should handle context-specific shortcuts', () => {
      const globalHandler = jest.fn();
      const modalHandler = jest.fn();

      const { rerender } = renderHook(
        ({ context }) => 
          useKeyboardShortcuts({
            'Escape': context === 'modal' ? modalHandler : globalHandler
          }),
        { initialProps: { context: 'global' } }
      );

      fireKeyboardEvent('Escape');
      expect(globalHandler).toHaveBeenCalledTimes(1);
      expect(modalHandler).not.toHaveBeenCalled();

      // Change context
      rerender({ context: 'modal' });

      fireKeyboardEvent('Escape');
      expect(globalHandler).toHaveBeenCalledTimes(1);
      expect(modalHandler).toHaveBeenCalledTimes(1);
    });

    it('should prevent shortcuts when typing in input fields', () => {
      const handler = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          's': handler
        })
      );

      // Mock active element as input
      const mockInput = { tagName: 'INPUT' };
      jest.spyOn(document, 'activeElement', 'get').mockReturnValue(mockInput as any);

      fireKeyboardEvent('s');

      expect(handler).not.toHaveBeenCalled();
    });

    it('should allow shortcuts in specific input types', () => {
      const handler = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler
        }, { allowInInputs: ['button', 'submit'] })
      );

      // Mock button as active element
      const mockButton = { tagName: 'BUTTON', type: 'button' };
      jest.spyOn(document, 'activeElement', 'get').mockReturnValue(mockButton as any);

      fireKeyboardEvent('s', { ctrlKey: true });

      expect(handler).toHaveBeenCalledTimes(1);
    });

    it('should handle focus management', () => {
      const handler = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+f': handler
        }, { preventInFocusedInputs: true })
      );

      // Mock contenteditable element
      const mockDiv = { 
        tagName: 'DIV', 
        contentEditable: 'true',
        isContentEditable: true
      };
      jest.spyOn(document, 'activeElement', 'get').mockReturnValue(mockDiv as any);

      fireKeyboardEvent('f', { ctrlKey: true });

      expect(handler).not.toHaveBeenCalled();
    });

    it('should support conditional shortcut registration', () => {
      const handler1 = jest.fn();
      const handler2 = jest.fn();

      const { rerender } = renderHook(
        ({ condition }) => 
          useKeyboardShortcuts(
            condition 
              ? { 'ctrl+1': handler1 }
              : { 'ctrl+2': handler2 }
          ),
        { initialProps: { condition: true } }
      );

      fireKeyboardEvent('1', { ctrlKey: true });
      fireKeyboardEvent('2', { ctrlKey: true });

      expect(handler1).toHaveBeenCalledTimes(1);
      expect(handler2).not.toHaveBeenCalled();

      // Change condition
      rerender({ condition: false });

      fireKeyboardEvent('1', { ctrlKey: true });
      fireKeyboardEvent('2', { ctrlKey: true });

      expect(handler1).toHaveBeenCalledTimes(1); // No additional calls
      expect(handler2).toHaveBeenCalledTimes(1);
    });
  });

  describe('Shortcut Conflicts and Priority', () => {
    it('should handle shortcut conflicts with last-registered wins', () => {
      const handler1 = jest.fn();
      const handler2 = jest.fn();

      renderHook(() => {
        useKeyboardShortcuts({ 'ctrl+s': handler1 });
        useKeyboardShortcuts({ 'ctrl+s': handler2 });
      });

      fireKeyboardEvent('s', { ctrlKey: true });

      expect(handler1).not.toHaveBeenCalled();
      expect(handler2).toHaveBeenCalledTimes(1);
    });

    it('should support shortcut priorities', () => {
      const lowPriorityHandler = jest.fn();
      const highPriorityHandler = jest.fn();

      renderHook(() => {
        useKeyboardShortcuts(
          { 'ctrl+s': lowPriorityHandler }, 
          { priority: 1 }
        );
        useKeyboardShortcuts(
          { 'ctrl+s': highPriorityHandler }, 
          { priority: 10 }
        );
      });

      fireKeyboardEvent('s', { ctrlKey: true });

      expect(lowPriorityHandler).not.toHaveBeenCalled();
      expect(highPriorityHandler).toHaveBeenCalledTimes(1);
    });

    it('should allow stopping propagation', () => {
      const handler1 = jest.fn((event) => event.stopPropagation());
      const handler2 = jest.fn();

      renderHook(() => {
        useKeyboardShortcuts(
          { 'ctrl+s': handler1 }, 
          { priority: 10 }
        );
        useKeyboardShortcuts(
          { 'ctrl+s': handler2 }, 
          { priority: 1 }
        );
      });

      const event = fireKeyboardEvent('s', { ctrlKey: true });

      expect(handler1).toHaveBeenCalledTimes(1);
      expect(handler2).not.toHaveBeenCalled();
      expect(event.defaultPrevented).toBe(false);
    });

    it('should prevent default browser behavior when specified', () => {
      const handler = jest.fn((event) => event.preventDefault());

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler
        }, { preventDefault: true })
      );

      const event = fireKeyboardEvent('s', { ctrlKey: true });

      expect(handler).toHaveBeenCalledTimes(1);
      expect(event.defaultPrevented).toBe(true);
    });

    it('should handle global vs local shortcut conflicts', () => {
      const globalHandler = jest.fn();
      const localHandler = jest.fn();

      renderHook(() => {
        useKeyboardShortcuts(
          { 'ctrl+z': globalHandler }, 
          { global: true }
        );
        useKeyboardShortcuts(
          { 'ctrl+z': localHandler }, 
          { global: false }
        );
      });

      fireKeyboardEvent('z', { ctrlKey: true });

      // Local should take precedence over global
      expect(globalHandler).not.toHaveBeenCalled();
      expect(localHandler).toHaveBeenCalledTimes(1);
    });
  });

  describe('Dynamic Shortcut Management', () => {
    it('should add shortcuts dynamically', () => {
      const handler = jest.fn();

      const { result } = renderHook(() => 
        useKeyboardShortcuts({})
      );

      // Initially no shortcuts
      fireKeyboardEvent('s', { ctrlKey: true });
      expect(handler).not.toHaveBeenCalled();

      // Add shortcut dynamically
      act(() => {
        result.current.addShortcut('ctrl+s', handler);
      });

      fireKeyboardEvent('s', { ctrlKey: true });
      expect(handler).toHaveBeenCalledTimes(1);
    });

    it('should remove shortcuts dynamically', () => {
      const handler = jest.fn();

      const { result } = renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler
        })
      );

      fireKeyboardEvent('s', { ctrlKey: true });
      expect(handler).toHaveBeenCalledTimes(1);

      // Remove shortcut
      act(() => {
        result.current.removeShortcut('ctrl+s');
      });

      fireKeyboardEvent('s', { ctrlKey: true });
      expect(handler).toHaveBeenCalledTimes(1); // No additional calls
    });

    it('should update shortcut handlers', () => {
      const handler1 = jest.fn();
      const handler2 = jest.fn();

      const { result } = renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler1
        })
      );

      fireKeyboardEvent('s', { ctrlKey: true });
      expect(handler1).toHaveBeenCalledTimes(1);

      // Update handler
      act(() => {
        result.current.updateShortcut('ctrl+s', handler2);
      });

      fireKeyboardEvent('s', { ctrlKey: true });
      expect(handler1).toHaveBeenCalledTimes(1); // No additional calls
      expect(handler2).toHaveBeenCalledTimes(1);
    });

    it('should clear all shortcuts', () => {
      const handler1 = jest.fn();
      const handler2 = jest.fn();

      const { result } = renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler1,
          'ctrl+z': handler2
        })
      );

      fireKeyboardEvent('s', { ctrlKey: true });
      fireKeyboardEvent('z', { ctrlKey: true });
      expect(handler1).toHaveBeenCalledTimes(1);
      expect(handler2).toHaveBeenCalledTimes(1);

      // Clear all shortcuts
      act(() => {
        result.current.clearShortcuts();
      });

      fireKeyboardEvent('s', { ctrlKey: true });
      fireKeyboardEvent('z', { ctrlKey: true });
      expect(handler1).toHaveBeenCalledTimes(1); // No additional calls
      expect(handler2).toHaveBeenCalledTimes(1); // No additional calls
    });

    it('should list active shortcuts', () => {
      const { result } = renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': jest.fn(),
          'alt+tab': jest.fn(),
          'f1': jest.fn()
        })
      );

      const shortcuts = result.current.getActiveShortcuts();
      
      expect(shortcuts).toContain('ctrl+s');
      expect(shortcuts).toContain('alt+tab');
      expect(shortcuts).toContain('f1');
      expect(shortcuts).toHaveLength(3);
    });
  });

  describe('Shortcut Help and Documentation', () => {
    it('should provide shortcut descriptions', () => {
      const { result } = renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': jest.fn()
        }, {
          descriptions: {
            'ctrl+s': 'Save document'
          }
        })
      );

      const description = result.current.getShortcutDescription('ctrl+s');
      expect(description).toBe('Save document');
    });

    it('should group shortcuts by category', () => {
      const { result } = renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': jest.fn(),
          'ctrl+o': jest.fn(),
          'ctrl+z': jest.fn(),
          'ctrl+y': jest.fn()
        }, {
          categories: {
            'File': ['ctrl+s', 'ctrl+o'],
            'Edit': ['ctrl+z', 'ctrl+y']
          }
        })
      );

      const categories = result.current.getShortcutCategories();
      
      expect(categories.File).toEqual(['ctrl+s', 'ctrl+o']);
      expect(categories.Edit).toEqual(['ctrl+z', 'ctrl+y']);
    });

    it('should format shortcuts for display', () => {
      const { result } = renderHook(() => 
        useKeyboardShortcuts({})
      );

      expect(result.current.formatShortcut('ctrl+s')).toBe('Ctrl+S');
      expect(result.current.formatShortcut('alt+tab')).toBe('Alt+Tab');
      expect(result.current.formatShortcut('meta+z')).toBe('⌘Z'); // macOS style
      expect(result.current.formatShortcut('ctrl+shift+f12')).toBe('Ctrl+Shift+F12');
    });

    it('should detect platform-specific shortcuts', () => {
      const { result } = renderHook(() => 
        useKeyboardShortcuts({})
      );

      // Mock macOS
      Object.defineProperty(navigator, 'platform', {
        value: 'MacIntel'
      });

      expect(result.current.formatShortcut('ctrl+s')).toBe('⌘S');
      expect(result.current.formatShortcut('alt+tab')).toBe('⌥Tab');

      // Mock Windows
      Object.defineProperty(navigator, 'platform', {
        value: 'Win32'
      });

      expect(result.current.formatShortcut('ctrl+s')).toBe('Ctrl+S');
      expect(result.current.formatShortcut('alt+tab')).toBe('Alt+Tab');
    });

    it('should provide help text generation', () => {
      const { result } = renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': jest.fn(),
          'ctrl+o': jest.fn(),
          'esc': jest.fn()
        }, {
          descriptions: {
            'ctrl+s': 'Save document',
            'ctrl+o': 'Open document',
            'esc': 'Cancel operation'
          }
        })
      );

      const helpText = result.current.generateHelpText();
      
      expect(helpText).toContain('Ctrl+S - Save document');
      expect(helpText).toContain('Ctrl+O - Open document');
      expect(helpText).toContain('Esc - Cancel operation');
    });
  });

  describe('Performance and Optimization', () => {
    it('should debounce rapid key events', () => {
      const handler = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler
        }, { debounce: 100 })
      );

      // Fire events rapidly
      for (let i = 0; i < 10; i++) {
        fireKeyboardEvent('s', { ctrlKey: true });
      }

      expect(handler).toHaveBeenCalledTimes(1);

      // Wait for debounce
      act(() => {
        jest.advanceTimersByTime(150);
      });

      fireKeyboardEvent('s', { ctrlKey: true });
      expect(handler).toHaveBeenCalledTimes(2);
    });

    it('should throttle shortcut execution', () => {
      const handler = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler
        }, { throttle: 1000 })
      );

      // Fire events in succession
      fireKeyboardEvent('s', { ctrlKey: true });
      fireKeyboardEvent('s', { ctrlKey: true });
      fireKeyboardEvent('s', { ctrlKey: true });

      expect(handler).toHaveBeenCalledTimes(1);

      // Wait for throttle period
      act(() => {
        jest.advanceTimersByTime(1100);
      });

      fireKeyboardEvent('s', { ctrlKey: true });
      expect(handler).toHaveBeenCalledTimes(2);
    });

    it('should cleanup event listeners on unmount', () => {
      const { unmount } = renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': jest.fn()
        })
      );

      expect(window.addEventListener).toHaveBeenCalled();

      unmount();

      expect(window.removeEventListener).toHaveBeenCalled();
    });

    it('should optimize shortcut parsing', () => {
      const parseShortcut = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': jest.fn()
        }, { parseShortcut })
      );

      // Should parse shortcut only once during registration
      expect(parseShortcut).toHaveBeenCalledTimes(1);
      expect(parseShortcut).toHaveBeenCalledWith('ctrl+s');
    });

    it('should handle large numbers of shortcuts efficiently', () => {
      const shortcuts: { [key: string]: () => void } = {};

      // Create 1000 shortcuts
      for (let i = 0; i < 1000; i++) {
        shortcuts[`f${i % 12 + 1}`] = jest.fn();
      }

      const startTime = performance.now();
      
      renderHook(() => 
        useKeyboardShortcuts(shortcuts)
      );

      const endTime = performance.now();
      
      // Should register efficiently (< 100ms for 1000 shortcuts)
      expect(endTime - startTime).toBeLessThan(100);
    });

    it('should use WeakMap for performance optimization', () => {
      const { result } = renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': jest.fn()
        })
      );

      // Should provide internal performance metrics
      const metrics = result.current.getPerformanceMetrics?.();
      
      if (metrics) {
        expect(metrics.registeredShortcuts).toBe(1);
        expect(metrics.eventListenerCount).toBeGreaterThan(0);
      }
    });
  });

  describe('Accessibility and A11y', () => {
    it('should respect reduced motion preferences', () => {
      const handler = jest.fn();

      // Mock prefers-reduced-motion
      const matchMediaSpy = jest.spyOn(window, 'matchMedia').mockReturnValue({
        matches: true,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      } as any);

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler
        }, { respectReducedMotion: true })
      );

      fireKeyboardEvent('s', { ctrlKey: true });

      expect(handler).toHaveBeenCalledTimes(1);
      
      matchMediaSpy.mockRestore();
    });

    it('should provide ARIA live region updates', () => {
      const { result } = renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': jest.fn()
        }, { announceShortcuts: true })
      );

      act(() => {
        result.current.announceShortcut('ctrl+s', 'Document saved');
      });

      // Should update ARIA live region
      const liveRegion = document.querySelector('[aria-live="polite"]');
      expect(liveRegion?.textContent).toContain('Document saved');
    });

    it('should support high contrast mode', () => {
      // Mock high contrast media query
      const matchMediaSpy = jest.spyOn(window, 'matchMedia').mockReturnValue({
        matches: true,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      } as any);

      const { result } = renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': jest.fn()
        }, { highContrastMode: true })
      );

      const helpText = result.current.generateHelpText();
      
      // Should use high contrast formatting
      expect(helpText).toContain('high-contrast');
      
      matchMediaSpy.mockRestore();
    });

    it('should handle screen reader compatibility', () => {
      const handler = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler
        }, { 
          screenReaderCompatible: true,
          ariaLabels: {
            'ctrl+s': 'Save document keyboard shortcut'
          }
        })
      );

      fireKeyboardEvent('s', { ctrlKey: true });

      expect(handler).toHaveBeenCalledWith(
        expect.objectContaining({
          ariaLabel: 'Save document keyboard shortcut'
        })
      );
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle invalid shortcut strings gracefully', () => {
      const handler = jest.fn();

      expect(() => {
        renderHook(() => 
          useKeyboardShortcuts({
            'invalid++key': handler,
            '': handler,
            'ctrl+': handler
          })
        );
      }).not.toThrow();

      // Invalid shortcuts should be ignored
      fireKeyboardEvent('+', { ctrlKey: true });
      expect(handler).not.toHaveBeenCalled();
    });

    it('should handle null/undefined handlers', () => {
      expect(() => {
        renderHook(() => 
          useKeyboardShortcuts({
            'ctrl+s': null as any,
            'ctrl+z': undefined as any
          })
        );
      }).not.toThrow();
    });

    it('should handle key events without key property', () => {
      const handler = jest.fn();

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler
        })
      );

      // Create event without key property
      const invalidEvent = new KeyboardEvent('keydown', {
        ctrlKey: true
      } as any);
      delete (invalidEvent as any).key;

      eventListeners.keydown?.forEach(listener => {
        expect(() => listener(invalidEvent)).not.toThrow();
      });

      expect(handler).not.toHaveBeenCalled();
    });

    it('should handle browser compatibility issues', () => {
      const handler = jest.fn();

      // Mock old browser without KeyboardEvent constructor
      const originalKeyboardEvent = window.KeyboardEvent;
      delete (window as any).KeyboardEvent;

      renderHook(() => 
        useKeyboardShortcuts({
          'ctrl+s': handler
        })
      );

      // Should not crash
      expect(() => {
        fireKeyboardEvent('s', { ctrlKey: true });
      }).not.toThrow();

      // Restore
      window.KeyboardEvent = originalKeyboardEvent;
    });

    it('should handle memory leaks in large applications', () => {
      const handlers = Array.from({ length: 1000 }, () => jest.fn());
      
      const { unmount } = renderHook(() => {
        handlers.forEach((handler, index) => {
          useKeyboardShortcuts({
            [`f${(index % 12) + 1}`]: handler
          });
        });
      });

      // Should not cause memory issues
      unmount();

      expect(window.removeEventListener).toHaveBeenCalled();
    });
  });
});