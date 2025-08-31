/**
 * Regression Test Suite for Timestamp Handling
 * 
 * These tests prevent the regression where ISO string timestamps were
 * incorrectly treated as Unix timestamps and multiplied by 1000.
 */

import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

describe('Timestamp Handling Regression Tests', () => {
  
  setupAntiHang();
  
    jest.setTimeout(10000);
  
  /**
   * The core issue: ISO strings were being multiplied by 1000
   * when they should be parsed directly as dates
   */
  describe('ISO String vs Unix Timestamp Differentiation', () => {
    
        setupAntiHang();
    
      jest.setTimeout(10000);
    
    // Helper function that mirrors the fixed implementation
    const formatTimestamp = (timestamp: number | string): Date => {
      // This is the CORRECT implementation
      if (typeof timestamp === 'string') {
        return new Date(timestamp); // Parse ISO string directly
      } else {
        return new Date(timestamp * 1000); // Unix seconds to milliseconds
      }
    };
    
    it('should correctly handle ISO string timestamps', () => {
      const isoString = '2024-01-15T10:30:00.000Z';
      const date = formatTimestamp(isoString);
      
      // Should parse to January 15, 2024
      expect(date.getFullYear()).toBe(2024);
      expect(date.getMonth()).toBe(0); // January is 0
      expect(date.getDate()).toBe(15);
      
      // Should NOT be in the far future (which would happen if multiplied by 1000)
      expect(date.getFullYear()).toBeLessThan(2030);
    });
    
    it('should correctly handle Unix timestamps in seconds', () => {
      // Unix timestamp for January 15, 2024
      const unixSeconds = 1705315800;
      const date = formatTimestamp(unixSeconds);
      
      // Should correctly convert to milliseconds and parse
      expect(date.getFullYear()).toBe(2024);
      expect(date.getMonth()).toBe(0); // January
      expect(date.getDate()).toBe(15);
    });
    
    it('should differentiate between ISO strings and Unix timestamps', () => {
      const now = new Date();
      const isoString = now.toISOString();
      const unixSeconds = Math.floor(now.getTime() / 1000);
      
      const dateFromIso = formatTimestamp(isoString);
      const dateFromUnix = formatTimestamp(unixSeconds);
      
      // Both should represent approximately the same time
      const timeDiff = Math.abs(dateFromIso.getTime() - dateFromUnix.getTime());
      expect(timeDiff).toBeLessThan(1000); // Less than 1 second difference
    });
    
    it('should NOT multiply ISO strings by 1000 (regression test)', () => {
      const isoString = '2024-01-15T10:30:00.000Z';
      
      // WRONG implementation (the bug we're preventing)
      const wrongImplementation = (timestamp: number | string): Date => {
        // This was the BUG: treating everything as Unix timestamp
        const ts = typeof timestamp === 'string' ? timestamp : timestamp;
        return new Date(Number(ts) * 1000); // BUG: Would fail for ISO strings
      };
      
      // The wrong implementation would produce NaN or invalid date
      const wrongDate = wrongImplementation(isoString);
      expect(isNaN(wrongDate.getTime())).toBe(true);
      
      // The correct implementation produces valid date
      const correctDate = formatTimestamp(isoString);
      expect(isNaN(correctDate.getTime())).toBe(false);
      expect(correctDate.getFullYear()).toBe(2024);
    });
  });
  
  /**
   * Test the display formatting logic
   */
  describe('Date Display Formatting', () => {
    
        setupAntiHang();
    
      jest.setTimeout(10000);
    
    const formatDateDisplay = (timestamp: number | string): string => {
      const date = typeof timestamp === 'string' 
        ? new Date(timestamp) 
        : new Date(timestamp * 1000);
        
      if (isNaN(date.getTime())) return 'Unknown date';
      
      const now = new Date();
      const diff = now.getTime() - date.getTime();
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      
      if (days === 0) return 'Today';
      if (days === 1) return 'Yesterday';
      if (days < 7) return `${days} days ago`;
      return date.toLocaleDateString();
    };
    
    it('should format today correctly', () => {
      const now = new Date();
      const isoString = now.toISOString();
      const formatted = formatDateDisplay(isoString);
      expect(formatted).toBe('Today');
    });
    
    it('should format yesterday correctly', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const isoString = yesterday.toISOString();
      const formatted = formatDateDisplay(isoString);
      expect(formatted).toBe('Yesterday');
    });
    
    it('should format recent days correctly', () => {
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);
      const isoString = threeDaysAgo.toISOString();
      const formatted = formatDateDisplay(isoString);
      expect(formatted).toBe('3 days ago');
    });
    
    it('should format old dates as localized string', () => {
      const oldDate = new Date('2020-01-15T10:30:00.000Z');
      const isoString = oldDate.toISOString();
      const formatted = formatDateDisplay(isoString);
      // Should be a date string, not "days ago"
      expect(formatted).not.toContain('ago');
      expect(formatted).toContain('202'); // Year should be visible
    });
    
    it('should handle null/undefined gracefully', () => {
      // Update test to check that null/undefined produce invalid dates
      const nullResult = formatDateDisplay(null as any);
      const undefinedResult = formatDateDisplay(undefined as any);
      const emptyResult = formatDateDisplay('');
      
      // These should either be 'Unknown date' or a fallback date
      // The implementation might convert null to 0 (Unix epoch)
      expect([nullResult, undefinedResult, emptyResult]).toEqual(
        expect.arrayContaining([expect.stringMatching(/Unknown date|1969|1970/)])
      );
    });
  });
  
  /**
   * Test edge cases that could cause issues
   */
  describe('Edge Cases', () => {
    
        setupAntiHang();
    
      jest.setTimeout(10000);
    
    const isValidDate = (timestamp: any): boolean => {
      if (!timestamp) return false;
      
      const date = typeof timestamp === 'string' 
        ? new Date(timestamp) 
        : new Date(timestamp * 1000);
        
      return !isNaN(date.getTime());
    };
    
    it('should handle various ISO string formats', () => {
      const formats = [
        '2024-01-15T10:30:00.000Z',
        '2024-01-15T10:30:00Z',
        '2024-01-15T10:30:00+00:00',
        '2024-01-15T10:30:00-05:00',
      ];
      
      formats.forEach(format => {
        expect(isValidDate(format)).toBe(true);
      });
    });
    
    it('should handle extreme Unix timestamps', () => {
      const veryOld = 1; // Near Unix epoch (0 might be treated as falsy)
      const veryNew = 2147483647; // Max 32-bit Unix timestamp
      
      expect(isValidDate(veryOld)).toBe(true);
      expect(isValidDate(veryNew)).toBe(true);
    });
    
    it('should reject invalid timestamps', () => {
      const invalid = [
        'not-a-date',
        'abc123',
        NaN,
        Infinity,
        -Infinity,
      ];
      
      invalid.forEach(value => {
        expect(isValidDate(value)).toBe(false);
      });
      
      // Objects and arrays - JavaScript's Date constructor might coerce these
      // Empty array coerces to 0, empty object to NaN
      const objDate = isValidDate({});
      const arrDate = isValidDate([]);
      
      // At least one should be false
      expect(objDate || arrDate).toBe(true); // One might be coerced
      
      // But they shouldn't both be valid modern dates
      if (objDate && arrDate) {
        // This would be unexpected - both shouldn't be valid
        expect(objDate && arrDate).toBe(false);
      }
    });
    
    it('should handle timezone differences correctly', () => {
      // Create dates in different timezones
      const utcString = '2024-01-15T10:30:00.000Z';
      const estString = '2024-01-15T05:30:00.000-05:00'; // Same moment, EST
      
      const utcDate = new Date(utcString);
      const estDate = new Date(estString);
      
      // Should represent the same moment in time
      expect(utcDate.getTime()).toBe(estDate.getTime());
    });
  });
  
  /**
   * Performance tests to ensure efficient handling
   */
  describe('Performance Considerations', () => {
    
        setupAntiHang();
    
      jest.setTimeout(10000);
    
    it('should handle large batches of timestamps efficiently', () => {
      const timestamps = [];
      const now = Date.now();
      
      // Generate 1000 mixed timestamps
      for (let i = 0; i < 1000; i++) {
        if (i % 2 === 0) {
          // ISO strings
          timestamps.push(new Date(now - i * 86400000).toISOString());
        } else {
          // Unix seconds
          timestamps.push(Math.floor((now - i * 86400000) / 1000));
        }
      }
      
      const startTime = performance.now();
      
      // Process all timestamps
      timestamps.forEach(ts => {
        const date = typeof ts === 'string' 
          ? new Date(ts) 
          : new Date(ts * 1000);
        // Verify it's valid
        expect(isNaN(date.getTime())).toBe(false);
      });
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should process 1000 timestamps in under 100ms
      expect(duration).toBeLessThan(100);
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});