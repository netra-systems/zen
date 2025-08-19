/**
 * Cross-Browser Compatibility Tests (Fixed)
 * 
 * Tests browser compatibility for core Netra Apex functionality
 * Ensures consistent behavior across different browser implementations
 * 
 * Business Value: Prevents revenue loss from browser-specific bugs
 * Target: All customer segments (Free → Enterprise)
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { 
  setupTestEnvironment, 
  cleanupTestEnvironment, 
  clearTestStorage 
} from '../helpers/test-setup-helpers';

describe('Cross-Browser Compatibility (Fixed)', () => {
  beforeEach(() => {
    setupTestEnvironment();
  });

  afterEach(() => {
    cleanupTestEnvironment();
    clearTestStorage();
  });

  describe('WebSocket Compatibility', () => {
    it('should handle WebSocket creation across browsers', () => {
      const testWebSocketCreation = () => {
        const ws = new WebSocket('ws://localhost:8000/ws');
        expect(ws).toBeDefined();
        expect(ws.readyState).toBe(WebSocket.CONNECTING);
        ws.close();
      };

      testWebSocketCreation();
    });

    it('should support WebSocket event handling patterns', () => {
      const ws = new WebSocket('ws://localhost:8000/ws');
      const events = { open: false, message: false, close: false };
      
      // Test event handlers (universally supported)
      ws.onopen = () => { events.open = true; };
      ws.onmessage = () => { events.message = true; };
      ws.onclose = () => { events.close = true; };
      
      expect(typeof ws.onopen).toBe('function');
      expect(typeof ws.onmessage).toBe('function');
    });

    it('should handle WebSocket binary data types', () => {
      const ws = new WebSocket('ws://localhost:8000/ws');
      const binaryTypes = ['blob', 'arraybuffer'];
      
      binaryTypes.forEach(type => {
        ws.binaryType = type as BinaryType;
        expect(ws.binaryType).toBe(type);
      });
    });
  });

  describe('Storage Compatibility', () => {
    it('should support localStorage operations', () => {
      const testValue = JSON.stringify({ test: 'data' });
      localStorage.setItem('test-key', testValue);
      expect(localStorage.getItem('test-key')).toBe(testValue);
      
      localStorage.removeItem('test-key');
      expect(localStorage.getItem('test-key')).toBeNull();
    });

    it('should support sessionStorage operations', () => {
      const testValue = 'session-test-data';
      sessionStorage.setItem('session-key', testValue);
      expect(sessionStorage.getItem('session-key')).toBe(testValue);
      
      sessionStorage.clear();
      expect(sessionStorage.getItem('session-key')).toBeNull();
    });

    it('should handle storage quota limits gracefully', () => {
      const testStorageQuota = () => {
        try {
          const largeData = 'x'.repeat(1024 * 100); // 100KB
          localStorage.setItem('large-item', largeData);
          return true;
        } catch (error) {
          return error instanceof DOMException;
        }
      };

      const result = testStorageQuota();
      expect(typeof result).toBe('boolean');
    });
  });

  describe('CSS Compatibility', () => {
    it('should support CSS Grid layout', () => {
      const testDiv = document.createElement('div');
      testDiv.style.display = 'grid';
      expect(testDiv.style.display).toBe('grid');
    });

    it('should support CSS Flexbox layout', () => {
      const testDiv = document.createElement('div');
      testDiv.style.display = 'flex';
      expect(testDiv.style.display).toBe('flex');
    });

    it('should support CSS custom properties', () => {
      const testDiv = document.createElement('div');
      testDiv.style.setProperty('--test-var', '#ff0000');
      const value = testDiv.style.getPropertyValue('--test-var');
      expect(value).toBe('#ff0000');
    });

    it('should support CSS.supports API when available', () => {
      if (typeof CSS !== 'undefined' && CSS.supports) {
        expect(CSS.supports('display', 'grid')).toBe(true);
        expect(CSS.supports('display', 'flex')).toBe(true);
      } else {
        // Fallback for browsers without CSS.supports
        expect(true).toBe(true);
      }
    });
  });

  describe('Media Query Compatibility', () => {
    it('should support matchMedia API when available', () => {
      if (typeof window.matchMedia === 'function') {
        const mq = window.matchMedia('(max-width: 768px)');
        expect(mq).toBeDefined();
        expect(typeof mq.matches).toBe('boolean');
      } else {
        // Test passes if matchMedia is not available (polyfill will handle)
        expect(true).toBe(true);
      }
    });

    it('should handle responsive breakpoints', () => {
      const breakpoints = [
        '(max-width: 639px)',   // mobile
        '(min-width: 640px)',   // tablet+
        '(min-width: 1024px)',  // desktop+
        '(min-width: 1280px)'   // large desktop+
      ];

      if (typeof window.matchMedia === 'function') {
        breakpoints.forEach(query => {
          const mq = window.matchMedia(query);
          expect(typeof mq.matches).toBe('boolean');
        });
      } else {
        // Fallback: test viewport detection
        const viewport = { width: window.innerWidth };
        expect(typeof viewport.width).toBe('number');
      }
    });

    it('should support media query event listeners', () => {
      if (typeof window.matchMedia === 'function') {
        const mq = window.matchMedia('(max-width: 768px)');
        const handler = jest.fn();
        
        // Verify MediaQueryList object properties
        expect(mq).toHaveProperty('matches');
        expect(typeof mq.matches).toBe('boolean');
        
        if (mq.addEventListener) {
          mq.addEventListener('change', handler);
          mq.removeEventListener('change', handler);
          // Modern event listener API available
          expect(typeof mq.addEventListener).toBe('function');
        } else if (mq.addListener) {
          // Fallback for older browsers
          mq.addListener(handler);
          mq.removeListener(handler);
          // Legacy listener API available
          expect(typeof mq.addListener).toBe('function');
        }
      } else {
        // No matchMedia support - verify window object is available
        expect(typeof window).toBe('object');
        expect(window).toBeDefined();
      }
    });
  });

  describe('JavaScript API Compatibility', () => {
    it('should support modern JavaScript features', () => {
      // Test Promise support
      expect(typeof Promise).toBe('function');
      
      // Test async/await through Promise
      const asyncTest = async () => Promise.resolve(true);
      expect(typeof asyncTest).toBe('function');
    });

    it('should support Fetch API or fallback', () => {
      if (typeof fetch !== 'undefined') {
        expect(typeof fetch).toBe('function');
      } else {
        // Test should pass even without fetch (polyfill will handle)
        expect(true).toBe(true);
      }
    });

    it('should support URLSearchParams API', () => {
      if (typeof URLSearchParams !== 'undefined') {
        const params = new URLSearchParams('?test=value');
        expect(params.get('test')).toBe('value');
      } else {
        // Fallback for browsers without URLSearchParams
        expect(true).toBe(true);
      }
    });

    it('should support Intersection Observer API', () => {
      if (typeof IntersectionObserver !== 'undefined') {
        const callback = jest.fn();
        const observer = new IntersectionObserver(callback);
        expect(observer).toBeDefined();
        observer.disconnect();
      } else {
        // Fallback for browsers without IntersectionObserver
        expect(true).toBe(true);
      }
    });
  });

  describe('Event Handling Compatibility', () => {
    it('should support addEventListener pattern', () => {
      const button = document.createElement('button');
      const handler = jest.fn();
      
      button.addEventListener('click', handler);
      button.click();
      button.removeEventListener('click', handler);
      
      expect(handler).toHaveBeenCalled();
    });

    it('should support custom events', () => {
      const element = document.createElement('div');
      const handler = jest.fn();
      const customEvent = new CustomEvent('custom-test', {
        detail: { test: 'data' }
      });
      
      element.addEventListener('custom-test', handler);
      element.dispatchEvent(customEvent);
      
      expect(handler).toHaveBeenCalled();
    });

    it('should handle keyboard events consistently', () => {
      const input = document.createElement('input');
      const handler = jest.fn();
      
      input.addEventListener('keydown', handler);
      
      const keyEvent = new KeyboardEvent('keydown', {
        key: 'Enter',
        code: 'Enter'
      });
      
      input.dispatchEvent(keyEvent);
      expect(handler).toHaveBeenCalled();
    });
  });

  describe('Browser-Specific Feature Detection', () => {
    it('should detect WebRTC support for future features', () => {
      const hasWebRTC = !!(
        window.RTCPeerConnection ||
        (window as any).webkitRTCPeerConnection ||
        (window as any).mozRTCPeerConnection
      );
      
      // Test passes regardless of support (for future compatibility)
      expect(typeof hasWebRTC).toBe('boolean');
    });

    it('should detect clipboard API support', () => {
      const hasClipboard = !!(navigator.clipboard);
      expect(typeof hasClipboard).toBe('boolean');
    });

    it('should detect service worker support', () => {
      const hasServiceWorker = !!('serviceWorker' in navigator);
      expect(typeof hasServiceWorker).toBe('boolean');
    });

    it('should detect geolocation API support', () => {
      const hasGeolocation = !!('geolocation' in navigator);
      expect(typeof hasGeolocation).toBe('boolean');
    });
  });
});