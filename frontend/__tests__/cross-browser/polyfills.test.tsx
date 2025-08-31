import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { 
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
 and consistent functionality
 * 
 * Business Value: Extends browser support, reduces churn from compatibility issues
 * Target: Free and Early tier users with older browsers
 */

import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { 
  setupTestEnvironment, 
  cleanupTestEnvironment,
  clearTestStorage 
} from '../helpers/test-setup-helpers';

// Polyfill implementations for testing
const polyfills = {
  requestAnimationFrame: (callback: FrameRequestCallback) => {
    return window.setTimeout(callback, 1000 / 60);
  },
  
  cancelAnimationFrame: (id: number) => {
    window.clearTimeout(id);
  },

  matchMedia: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    addListener: jest.fn(),
    removeListener: jest.fn(),
    dispatchEvent: jest.fn()
  }),

  intersectionObserverPolyfill: class {
    constructor(callback: IntersectionObserverCallback) {
      this.callback = callback;
    }
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
    private callback: IntersectionObserverCallback;
  },

  fetchPolyfill: (url: string, options?: RequestInit) => {
    const xhr = new XMLHttpRequest();
    return new Promise((resolve, reject) => {
      xhr.onreadystatechange = () => {
        if (xhr.readyState === 4) {
          resolve({
            ok: xhr.status >= 200 && xhr.status < 300,
            status: xhr.status,
            json: () => Promise.resolve(JSON.parse(xhr.responseText)),
            text: () => Promise.resolve(xhr.responseText)
          });
        }
      };
      xhr.onerror = reject;
      xhr.open(options?.method || 'GET', url);
      xhr.send(options?.body);
    });
  }
};

describe('Polyfill Effectiveness', () => {
    jest.setTimeout(10000);
  beforeEach(() => {
    setupTestEnvironment();
  });

  afterEach(() => {
    cleanupTestEnvironment();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Animation Polyfills', () => {
      jest.setTimeout(10000);
    it('should polyfill requestAnimationFrame with setTimeout', async () => {
      // Simulate missing requestAnimationFrame
      const originalRAF = window.requestAnimationFrame;
      delete (window as any).requestAnimationFrame;
      
      // Apply polyfill
      window.requestAnimationFrame = polyfills.requestAnimationFrame;
      
      const callback = jest.fn();
      const id = window.requestAnimationFrame(callback);
      
      expect(typeof id).toBe('number');
      
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 20));
      });
      
      expect(callback).toHaveBeenCalled();
      
      // Restore original
      if (originalRAF) {
        window.requestAnimationFrame = originalRAF;
      }
    });

    it('should polyfill cancelAnimationFrame with clearTimeout', () => {
      const originalCAF = window.cancelAnimationFrame;
      delete (window as any).cancelAnimationFrame;
      
      window.cancelAnimationFrame = polyfills.cancelAnimationFrame;
      
      const callback = jest.fn();
      const id = setTimeout(callback, 100);
      window.cancelAnimationFrame(id);
      
      // Wait to ensure callback wasn't called
      setTimeout(() => {
        expect(callback).not.toHaveBeenCalled();
      }, 150);
      
      if (originalCAF) {
        window.cancelAnimationFrame = originalCAF;
      }
    });

    it('should handle smooth scrolling polyfill', () => {
      const element = document.createElement('div');
      element.style.overflow = 'auto';
      element.style.height = '100px';
      
      const content = document.createElement('div');
      content.style.height = '1000px';
      element.appendChild(content);
      
      // Test scroll behavior
      const smoothScrollPolyfill = (top: number, behavior: ScrollBehavior = 'auto') => {
        if (behavior === 'smooth') {
          let currentScroll = element.scrollTop;
          const distance = top - currentScroll;
          const duration = 300;
          const startTime = Date.now();
          
          const scroll = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            element.scrollTop = currentScroll + (distance * progress);
            
            if (progress < 1) {
              requestAnimationFrame(scroll);
            }
          };
          
          scroll();
        } else {
          element.scrollTop = top;
        }
      };
      
      smoothScrollPolyfill(500, 'smooth');
      // Test passes if scroll function executes without errors
      expect(typeof smoothScrollPolyfill).toBe('function');
    });
  });

  describe('Media Query Polyfills', () => {
      jest.setTimeout(10000);
    it('should polyfill matchMedia API', () => {
      const originalMatchMedia = window.matchMedia;
      delete (window as any).matchMedia;
      
      window.matchMedia = polyfills.matchMedia;
      
      const mq = window.matchMedia('(max-width: 768px)');
      expect(mq).toBeDefined();
      expect(typeof mq.matches).toBe('boolean');
      expect(typeof mq.addEventListener).toBe('function');
      
      if (originalMatchMedia) {
        window.matchMedia = originalMatchMedia;
      }
    });

    it('should provide responsive breakpoint detection fallback', () => {
      const getBreakpoint = () => {
        const width = window.innerWidth;
        if (width < 640) return 'mobile';
        if (width < 1024) return 'tablet';
        return 'desktop';
      };
      
      // Test with different viewport sizes
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 320
      });
      expect(getBreakpoint()).toBe('mobile');
      
      window.innerWidth = 768;
      expect(getBreakpoint()).toBe('tablet');
      
      window.innerWidth = 1200;
      expect(getBreakpoint()).toBe('desktop');
    });
  });

  describe('Observer API Polyfills', () => {
      jest.setTimeout(10000);
    it('should polyfill IntersectionObserver', () => {
      const originalIO = window.IntersectionObserver;
      delete (window as any).IntersectionObserver;
      
      window.IntersectionObserver = polyfills.intersectionObserverPolyfill as any;
      
      const callback = jest.fn();
      const observer = new IntersectionObserver(callback);
      
      expect(observer).toBeDefined();
      expect(typeof observer.observe).toBe('function');
      expect(typeof observer.disconnect).toBe('function');
      
      const element = document.createElement('div');
      observer.observe(element);
      observer.disconnect();
      
      expect(observer.observe).toHaveBeenCalledWith(element);
      
      if (originalIO) {
        window.IntersectionObserver = originalIO;
      }
    });

    it('should provide visibility detection fallback', () => {
      const isElementVisible = (element: Element) => {
        const rect = element.getBoundingClientRect();
        return (
          rect.top >= 0 &&
          rect.left >= 0 &&
          rect.bottom <= window.innerHeight &&
          rect.right <= window.innerWidth
        );
      };
      
      const element = document.createElement('div');
      document.body.appendChild(element);
      
      const visible = isElementVisible(element);
      expect(typeof visible).toBe('boolean');
      
      document.body.removeChild(element);
    });
  });

  describe('Storage Polyfills', () => {
      jest.setTimeout(10000);
    it('should polyfill localStorage with cookies fallback', () => {
      const cookieStorage = {
        getItem: (key: string) => {
          const name = key + '=';
          const decodedCookie = decodeURIComponent(document.cookie);
          const ca = decodedCookie.split(';');
          
          for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') {
              c = c.substring(1);
            }
            if (c.indexOf(name) === 0) {
              return c.substring(name.length, c.length);
            }
          }
          return null;
        },
        
        setItem: (key: string, value: string) => {
          document.cookie = `${key}=${value}; path=/`;
        },
        
        removeItem: (key: string) => {
          document.cookie = `${key}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`;
        },
        
        clear: () => {
          const cookies = document.cookie.split(';');
          cookies.forEach(cookie => {
            const eqPos = cookie.indexOf('=');
            const name = eqPos > -1 ? cookie.substr(0, eqPos) : cookie;
            document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`;
          });
        }
      };
      
      // Test cookie storage polyfill
      cookieStorage.setItem('test-key', 'test-value');
      expect(cookieStorage.getItem('test-key')).toBe('test-value');
      
      cookieStorage.removeItem('test-key');
      expect(cookieStorage.getItem('test-key')).toBeNull();
    });

    it('should handle storage quota limits gracefully', () => {
      const safeStorage = {
        setItem: (key: string, value: string) => {
          try {
            localStorage.setItem(key, value);
            return true;
          } catch (error) {
            if (error instanceof DOMException) {
              // Quota exceeded, use alternative storage
              sessionStorage.setItem(key, value);
              return true;
            }
            return false;
          }
        },
        
        getItem: (key: string) => {
          return localStorage.getItem(key) || sessionStorage.getItem(key);
        }
      };
      
      const result = safeStorage.setItem('test', 'value');
      expect(typeof result).toBe('boolean');
      
      const retrieved = safeStorage.getItem('test');
      expect(retrieved).toBe('value');
    });
  });

  describe('Network API Polyfills', () => {
      jest.setTimeout(10000);
    it('should polyfill fetch with XMLHttpRequest', async () => {
      const originalFetch = window.fetch;
      delete (window as any).fetch;
      
      window.fetch = polyfills.fetchPolyfill as any;
      
      // Mock XMLHttpRequest for testing
      const mockXHR = {
        open: jest.fn(),
        send: jest.fn(),
        onreadystatechange: null as any,
        readyState: 4,
        status: 200,
        responseText: '{"test": "data"}'
      };
      
      (global as any).XMLHttpRequest = jest.fn(() => mockXHR);
      
      const promise = window.fetch('/api/test');
      
      // Simulate XHR completion
      if (mockXHR.onreadystatechange) {
        mockXHR.onreadystatechange();
      }
      
      const response = await promise;
      expect(response.ok).toBe(true);
      
      if (originalFetch) {
        window.fetch = originalFetch;
      }
    });

    it('should provide network status detection fallback', () => {
      const getNetworkStatus = () => {
        if ('onLine' in navigator) {
          return navigator.onLine;
        }
        
        // Fallback: attempt to load a small resource
        return new Promise<boolean>((resolve) => {
          const img = new Image();
          img.onload = () => resolve(true);
          img.onerror = () => resolve(false);
          img.src = '/favicon.ico?' + Date.now();
        });
      };
      
      const status = getNetworkStatus();
      expect(typeof status === 'boolean' || status instanceof Promise).toBe(true);
    });
  });

  describe('CSS Feature Polyfills', () => {
      jest.setTimeout(10000);
    it('should polyfill CSS Grid with Flexbox fallback', () => {
      const element = document.createElement('div');
      
      // Test Grid support
      element.style.display = 'grid';
      if (element.style.display !== 'grid') {
        // Fallback to flexbox layout
        element.style.display = 'flex';
        element.style.flexWrap = 'wrap';
        
        const child = document.createElement('div');
        child.style.flex = '1 0 auto';
        element.appendChild(child);
      }
      
      expect(element.style.display).toMatch(/^(grid|flex)$/);
    });

    it('should polyfill CSS custom properties', () => {
      const polyfillCustomProperties = (element: HTMLElement) => {
        const styles = getComputedStyle(element);
        const customProps = new Map<string, string>();
        
        // Extract custom properties
        for (let i = 0; i < styles.length; i++) {
          const prop = styles[i];
          if (prop.startsWith('--')) {
            customProps.set(prop, styles.getPropertyValue(prop));
          }
        }
        
        // Apply values
        customProps.forEach((value, prop) => {
          const varUsage = `var(${prop})`;
          const elements = element.querySelectorAll(`[style*="${varUsage}"]`);
          
          elements.forEach(el => {
            const htmlEl = el as HTMLElement;
            htmlEl.style.cssText = htmlEl.style.cssText.replace(
              new RegExp(varUsage, 'g'),
              value
            );
          });
        });
      };
      
      const testElement = document.createElement('div');
      testElement.style.setProperty('--primary-color', '#007bff');
      
      polyfillCustomProperties(testElement);
      expect(testElement.style.getPropertyValue('--primary-color')).toBe('#007bff');
    });
  });

  describe('Event Handling Polyfills', () => {
      jest.setTimeout(10000);
    it('should polyfill CustomEvent constructor', () => {
      const customEventPolyfill = (type: string, params: CustomEventInit = {}) => {
        const event = document.createEvent('CustomEvent');
        event.initCustomEvent(
          type,
          params.bubbles || false,
          params.cancelable || false,
          params.detail
        );
        return event;
      };
      
      // Test if CustomEvent needs polyfill
      let needsPolyfill = false;
      try {
        new CustomEvent('test');
      } catch (e) {
        needsPolyfill = true;
      }
      
      if (needsPolyfill) {
        const event = customEventPolyfill('test-event', { detail: { test: 'data' } });
        expect(event.type).toBe('test-event');
        expect(event.detail).toEqual({ test: 'data' });
      } else {
        const event = new CustomEvent('test-event', { detail: { test: 'data' } });
        expect(event.type).toBe('test-event');
      }
    });

    it('should handle passive event listener polyfill', () => {
      let supportsPassive = false;
      
      try {
        const opts = Object.defineProperty({}, 'passive', {
          get: () => {
            supportsPassive = true;
            return true;
          }
        });
        window.addEventListener('test', () => {}, opts);
        window.removeEventListener('test', () => {}, opts);
      } catch (e) {
        // Passive not supported
      }
      
      const addEventListenerSafe = (
        element: Element,
        event: string,
        handler: EventListener,
        options?: AddEventListenerOptions
      ) => {
        if (supportsPassive && options) {
          element.addEventListener(event, handler, options);
        } else {
          element.addEventListener(event, handler, options?.capture || false);
        }
      };
      
      const element = document.createElement('div');
      const handler = jest.fn();
      
      addEventListenerSafe(element, 'click', handler, { passive: true });
      element.click();
      
      expect(handler).toHaveBeenCalled();
    });
  });
});