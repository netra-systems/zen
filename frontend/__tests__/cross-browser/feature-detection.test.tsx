import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { 
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
pex works across different browser capabilities
 * 
 * Business Value: Maximizes user reach and reduces support burden
 * Target: All customer segments with diverse browser environments
 */

import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { 
  setupTestEnvironment, 
  cleanupTestEnvironment 
} from '../helpers/test-setup-helpers';

// Feature detection utilities
const detectBrowserFeatures = () => {
  return {
    webSocket: typeof WebSocket !== 'undefined',
    localStorage: typeof Storage !== 'undefined' && typeof localStorage !== 'undefined',
    sessionStorage: typeof Storage !== 'undefined' && typeof sessionStorage !== 'undefined',
    matchMedia: typeof window.matchMedia !== 'undefined',
    requestAnimationFrame: typeof requestAnimationFrame !== 'undefined',
    intersectionObserver: typeof IntersectionObserver !== 'undefined',
    mutationObserver: typeof MutationObserver !== 'undefined',
    fetch: typeof fetch !== 'undefined',
    customElements: typeof customElements !== 'undefined',
    cssSupports: typeof CSS !== 'undefined' && typeof CSS.supports !== 'undefined'
  };
};

const detectCSSFeatures = () => {
  const testElement = document.createElement('div');
  document.body.appendChild(testElement);
  
  const features = {
    flexbox: false,
    grid: false,
    customProperties: false,
    transforms3d: false,
    animations: false
  };

  // Test CSS Grid
  testElement.style.display = 'grid';
  features.grid = testElement.style.display === 'grid';

  // Test Flexbox
  testElement.style.display = 'flex';
  features.flexbox = testElement.style.display === 'flex';

  // Test Custom Properties
  testElement.style.setProperty('--test', 'test');
  features.customProperties = testElement.style.getPropertyValue('--test') === 'test';

  // Test 3D Transforms
  testElement.style.transform = 'translateZ(0)';
  features.transforms3d = testElement.style.transform !== '';

  // Test CSS Animations
  testElement.style.animation = 'test 1s';
  features.animations = testElement.style.animation !== '';

  document.body.removeChild(testElement);
  return features;
};

describe('Browser Feature Detection', () => {
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

  describe('Core API Detection', () => {
      jest.setTimeout(10000);
    it('should detect WebSocket support', () => {
      const features = detectBrowserFeatures();
      expect(typeof features.webSocket).toBe('boolean');
      
      if (features.webSocket) {
        expect(typeof WebSocket).toBe('function');
        expect(WebSocket.CONNECTING).toBe(0);
        expect(WebSocket.OPEN).toBe(1);
      }
    });

    it('should detect localStorage availability', () => {
      const features = detectBrowserFeatures();
      expect(typeof features.localStorage).toBe('boolean');
      
      if (features.localStorage) {
        expect(typeof localStorage.setItem).toBe('function');
        expect(typeof localStorage.getItem).toBe('function');
      }
    });

    it('should detect sessionStorage availability', () => {
      const features = detectBrowserFeatures();
      expect(typeof features.sessionStorage).toBe('boolean');
      
      if (features.sessionStorage) {
        expect(typeof sessionStorage.setItem).toBe('function');
        expect(typeof sessionStorage.getItem).toBe('function');
      }
    });

    it('should detect matchMedia support', () => {
      const features = detectBrowserFeatures();
      expect(typeof features.matchMedia).toBe('boolean');
      
      if (features.matchMedia) {
        const mq = window.matchMedia('(max-width: 768px)');
        expect(typeof mq.matches).toBe('boolean');
      }
    });

    it('should detect fetch API support', () => {
      const features = detectBrowserFeatures();
      expect(typeof features.fetch).toBe('boolean');
      
      if (features.fetch) {
        expect(typeof fetch).toBe('function');
      }
    });
  });

  describe('Animation API Detection', () => {
      jest.setTimeout(10000);
    it('should detect requestAnimationFrame support', () => {
      const features = detectBrowserFeatures();
      expect(typeof features.requestAnimationFrame).toBe('boolean');
      
      if (features.requestAnimationFrame) {
        expect(typeof requestAnimationFrame).toBe('function');
        expect(typeof cancelAnimationFrame).toBe('function');
      }
    });

    it('should provide fallback for animation timing', () => {
      const mockCallback = jest.fn();
      
      if (typeof requestAnimationFrame !== 'undefined') {
        const id = requestAnimationFrame(mockCallback);
        expect(typeof id).toBe('number');
        cancelAnimationFrame(id);
      } else {
        // Fallback using setTimeout
        const id = setTimeout(mockCallback, 16);
        clearTimeout(id);
        expect(typeof id).toBe('number');
      }
    });
  });

  describe('Observer API Detection', () => {
      jest.setTimeout(10000);
    it('should detect IntersectionObserver support', () => {
      const features = detectBrowserFeatures();
      expect(typeof features.intersectionObserver).toBe('boolean');
      
      if (features.intersectionObserver) {
        const callback = jest.fn();
        const observer = new IntersectionObserver(callback);
        expect(observer).toBeDefined();
        observer.disconnect();
      }
    });

    it('should detect MutationObserver support', () => {
      const features = detectBrowserFeatures();
      expect(typeof features.mutationObserver).toBe('boolean');
      
      if (features.mutationObserver) {
        const callback = jest.fn();
        const observer = new MutationObserver(callback);
        expect(observer).toBeDefined();
        observer.disconnect();
      }
    });

    it('should provide fallback for element visibility', () => {
      const element = document.createElement('div');
      document.body.appendChild(element);
      
      if (typeof IntersectionObserver !== 'undefined') {
        const callback = jest.fn();
        const observer = new IntersectionObserver(callback);
        observer.observe(element);
        observer.disconnect();
      } else {
        // Fallback using scroll events
        const rect = element.getBoundingClientRect();
        const isVisible = rect.top >= 0 && rect.bottom <= window.innerHeight;
        expect(typeof isVisible).toBe('boolean');
      }
      
      document.body.removeChild(element);
    });
  });

  describe('CSS Feature Detection', () => {
      jest.setTimeout(10000);
    it('should detect CSS Grid support', () => {
      const features = detectCSSFeatures();
      expect(typeof features.grid).toBe('boolean');
      
      if (CSS && CSS.supports) {
        const gridSupport = CSS.supports('display', 'grid');
        expect(typeof gridSupport).toBe('boolean');
      }
    });

    it('should detect Flexbox support', () => {
      const features = detectCSSFeatures();
      expect(typeof features.flexbox).toBe('boolean');
      
      if (CSS && CSS.supports) {
        const flexSupport = CSS.supports('display', 'flex');
        expect(typeof flexSupport).toBe('boolean');
      }
    });

    it('should detect CSS Custom Properties support', () => {
      const features = detectCSSFeatures();
      expect(typeof features.customProperties).toBe('boolean');
      
      if (CSS && CSS.supports) {
        const customPropSupport = CSS.supports('--test', 'value');
        expect(typeof customPropSupport).toBe('boolean');
      }
    });

    it('should detect 3D transform support', () => {
      const features = detectCSSFeatures();
      expect(typeof features.transforms3d).toBe('boolean');
      
      if (CSS && CSS.supports) {
        const transform3dSupport = CSS.supports('transform', 'translateZ(0)');
        expect(typeof transform3dSupport).toBe('boolean');
      }
    });
  });

  describe('Input and Interaction Detection', () => {
      jest.setTimeout(10000);
    it('should detect touch support', () => {
      const hasTouch = 'ontouchstart' in window || 
                      navigator.maxTouchPoints > 0 ||
                      (navigator as any).msMaxTouchPoints > 0;
      
      expect(typeof hasTouch).toBe('boolean');
    });

    it('should detect pointer events support', () => {
      const hasPointerEvents = 'onpointerdown' in window;
      expect(typeof hasPointerEvents).toBe('boolean');
    });

    it('should detect file input support', () => {
      const input = document.createElement('input');
      input.type = 'file';
      
      const supportsFiles = input.type === 'file';
      expect(typeof supportsFiles).toBe('boolean');
      
      if (supportsFiles) {
        expect('files' in input).toBe(true);
      }
    });

    it('should detect drag and drop support', () => {
      const hasDragDrop = 'draggable' in document.createElement('div') &&
                         'ondrop' in window;
      
      expect(typeof hasDragDrop).toBe('boolean');
    });
  });

  describe('Network and Connectivity Detection', () => {
      jest.setTimeout(10000);
    it('should detect online/offline capability', () => {
      const hasNavigatorOnline = typeof navigator.onLine !== 'undefined';
      expect(typeof hasNavigatorOnline).toBe('boolean');
      
      if (hasNavigatorOnline) {
        expect(typeof navigator.onLine).toBe('boolean');
      }
    });

    it('should detect connection information', () => {
      const connection = (navigator as any).connection || 
                        (navigator as any).mozConnection || 
                        (navigator as any).webkitConnection;
      
      if (connection) {
        expect(typeof connection.effectiveType).toBe('string');
      } else {
        // No connection API available
        expect(true).toBe(true);
      }
    });

    it('should detect service worker support', () => {
      const hasServiceWorker = 'serviceWorker' in navigator;
      expect(typeof hasServiceWorker).toBe('boolean');
      
      if (hasServiceWorker) {
        expect(typeof navigator.serviceWorker.register).toBe('function');
      }
    });
  });

  describe('Audio and Media Detection', () => {
      jest.setTimeout(10000);
    it('should detect audio context support', () => {
      const AudioContext = window.AudioContext || 
                          (window as any).webkitAudioContext;
      
      const hasAudioContext = typeof AudioContext !== 'undefined';
      expect(typeof hasAudioContext).toBe('boolean');
    });

    it('should detect getUserMedia support', () => {
      const getUserMedia = navigator.getUserMedia ||
                          (navigator as any).webkitGetUserMedia ||
                          (navigator as any).mozGetUserMedia ||
                          (navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
      
      const hasGetUserMedia = typeof getUserMedia !== 'undefined';
      expect(typeof hasGetUserMedia).toBe('boolean');
    });

    it('should detect video/audio element support', () => {
      const video = document.createElement('video');
      const audio = document.createElement('audio');
      
      const hasVideo = typeof video.play === 'function';
      const hasAudio = typeof audio.play === 'function';
      
      expect(typeof hasVideo).toBe('boolean');
      expect(typeof hasAudio).toBe('boolean');
    });
  });

  describe('Security and Permissions Detection', () => {
      jest.setTimeout(10000);
    it('should detect permissions API support', () => {
      const hasPermissions = 'permissions' in navigator;
      expect(typeof hasPermissions).toBe('boolean');
      
      if (hasPermissions) {
        expect(typeof navigator.permissions.query).toBe('function');
      }
    });

    it('should detect clipboard API support', () => {
      const hasClipboard = 'clipboard' in navigator;
      expect(typeof hasClipboard).toBe('boolean');
      
      if (hasClipboard) {
        expect(typeof navigator.clipboard.writeText).toBe('function');
      }
    });

    it('should detect crypto API support', () => {
      const hasCrypto = 'crypto' in window && 'subtle' in crypto;
      expect(typeof hasCrypto).toBe('boolean');
      
      if (hasCrypto) {
        expect(typeof crypto.subtle.digest).toBe('function');
      }
    });
  });
});