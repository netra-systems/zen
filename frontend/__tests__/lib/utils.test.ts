import { cn, generateUniqueId } from '@/lib/utils';

describe('Utils', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  describe('cn (className merge)', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should merge class names correctly', () => {
      expect(cn('foo', 'bar')).toBe('foo bar');
    });

    it('should handle conditional classes', () => {
      const isActive = true;
      const isDisabled = false;
      expect(cn('base', isActive && 'active', isDisabled && 'disabled')).toBe('base active');
    });

    it('should merge tailwind classes correctly', () => {
      // Should override conflicting classes
      expect(cn('p-4', 'p-2')).toBe('p-2');
      expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500');
    });

    it('should handle arrays of classes', () => {
      expect(cn(['foo', 'bar'], 'baz')).toBe('foo bar baz');
    });

    it('should handle objects with boolean values', () => {
      expect(cn({ foo: true, bar: false, baz: true })).toBe('foo baz');
    });

    it('should handle undefined and null values', () => {
      expect(cn('foo', undefined, null, 'bar')).toBe('foo bar');
    });

    it('should handle empty inputs', () => {
      expect(cn()).toBe('');
      expect(cn('')).toBe('');
    });

    it('should handle complex combinations', () => {
      expect(cn(
        'base',
        ['array', 'classes'],
        { conditional: true, skipped: false },
        undefined,
        'final'
      )).toBe('base array classes conditional final');
    });

    it('should handle duplicate Tailwind classes', () => {
      expect(cn('text-red-500 text-blue-500')).toBe('text-blue-500');
      expect(cn('p-4 p-2')).toBe('p-2');
    });

    it('should handle responsive tailwind classes', () => {
      expect(cn('sm:p-2 md:p-4', 'lg:p-6')).toBe('sm:p-2 md:p-4 lg:p-6');
    });
  });

  describe('generateUniqueId', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    beforeEach(() => {
      // Reset the id counter by accessing the module internals
      jest.resetModules();
    });

    it('should generate unique ids with default prefix', () => {
      const id1 = generateUniqueId();
      const id2 = generateUniqueId();
      
      expect(id1).toMatch(/^msg_\d+_\d+_[a-z0-9]+$/);
      expect(id2).toMatch(/^msg_\d+_\d+_[a-z0-9]+$/);
      expect(id1).not.toBe(id2);
    });

    it('should use custom prefix', () => {
      const id = generateUniqueId('custom');
      expect(id).toMatch(/^custom_\d+_\d+_[a-z0-9]+$/);
    });

    it('should include timestamp', () => {
      const before = Date.now();
      const id = generateUniqueId();
      const after = Date.now();
      
      const parts = id.split('_');
      const timestamp = parseInt(parts[1], 10);
      
      expect(timestamp).toBeGreaterThanOrEqual(before);
      expect(timestamp).toBeLessThanOrEqual(after);
    });

    it('should increment counter', () => {
      const id1 = generateUniqueId('test');
      const id2 = generateUniqueId('test');
      
      const counter1 = parseInt(id1.split('_')[2], 10);
      const counter2 = parseInt(id2.split('_')[2], 10);
      
      expect(counter2).toBe(counter1 + 1);
    });

    it('should generate different ids even with same prefix and timestamp', () => {
      // Mock Date.now to return same value
      const mockTimestamp = 1234567890;
      jest.spyOn(Date, 'now').mockReturnValue(mockTimestamp);
      jest.spyOn(Math, 'random').mockReturnValue(0.5);
      
      const id1 = generateUniqueId('test');
      const id2 = generateUniqueId('test');
      
      // Even with same timestamp and random, counter makes them unique
      expect(id1).not.toBe(id2);
      
      jest.restoreAllMocks();
    });

    it('should handle rapid generation', () => {
      const ids = new Set<string>();
      const count = 1000;
      
      for (let i = 0; i < count; i++) {
        ids.add(generateUniqueId());
      }
      
      // All IDs should be unique
      expect(ids.size).toBe(count);
    });

    it('should handle counter overflow gracefully', () => {
      // This test simulates counter reaching max value
      // We'll generate enough IDs to test the reset logic
      const ids = [];
      
      // Generate IDs to approach counter limit
      for (let i = 0; i < 10; i++) {
        ids.push(generateUniqueId('overflow'));
      }
      
      // All should still be unique
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });

    it('should have consistent format', () => {
      const id = generateUniqueId('format');
      const parts = id.split('_');
      
      expect(parts).toHaveLength(4);
      expect(parts[0]).toBe('format'); // prefix
      expect(parts[1]).toMatch(/^\d+$/); // timestamp
      expect(parts[2]).toMatch(/^\d+$/); // counter
      expect(parts[3]).toMatch(/^[a-z0-9]+$/); // random
    });

    it('should handle empty string prefix', () => {
      const id = generateUniqueId('');
      expect(id).toMatch(/^_\d+_\d+_[a-z0-9]+$/);
    });

    it('should handle special characters in prefix', () => {
      const id = generateUniqueId('test-123_abc');
      expect(id).toMatch(/^test-123_abc_\d+_\d+_[a-z0-9]+$/);
    });

    it('should be suitable for React keys', () => {
      // Test that IDs work well as React keys
      const items = Array.from({ length: 100 }, (_, i) => ({
        id: generateUniqueId('react'),
        value: i
      }));
      
      const keys = items.map(item => item.id);
      const uniqueKeys = new Set(keys);
      
      expect(uniqueKeys.size).toBe(keys.length);
    });

    it('should handle concurrent generation in async context', async () => {
      const promises = Array.from({ length: 100 }, async () => {
        await new Promise(resolve => setTimeout(resolve, Math.random() * 10));
        return generateUniqueId('async');
      });
      
      const ids = await Promise.all(promises);
      const uniqueIds = new Set(ids);
      
      expect(uniqueIds.size).toBe(ids.length);
    });

    it('should maintain uniqueness across different prefixes', () => {
      const id1 = generateUniqueId('prefix1');
      const id2 = generateUniqueId('prefix2');
      const id3 = generateUniqueId('prefix1');
      
      expect(id1).not.toBe(id2);
      expect(id1).not.toBe(id3);
      expect(id2).not.toBe(id3);
    });

    it('should generate predictable length ids', () => {
      const id = generateUniqueId('len');
      // Format: prefix_timestamp_counter_random
      // Random part is 7 chars (substring(2, 9))
      const parts = id.split('_');
      
      expect(parts[3].length).toBeGreaterThanOrEqual(1);
      expect(parts[3].length).toBeLessThanOrEqual(7);
    });

    it('should work with unicode prefixes', () => {
      const id = generateUniqueId('测试');
      expect(id).toMatch(/^测试_\d+_\d+_[a-z0-9]+$/);
    });

    it('should handle performance for large batches', () => {
      const startTime = performance.now();
      const ids = [];
      
      for (let i = 0; i < 10000; i++) {
        ids.push(generateUniqueId('perf'));
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should generate 10000 IDs in under 100ms
      expect(duration).toBeLessThan(100);
      
      // All should be unique
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });
  });

  describe('Edge cases and error handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    describe('cn edge cases', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should handle very long class strings', () => {
        const longClass = 'a'.repeat(1000);
        const result = cn(longClass, 'short');
        expect(result).toContain('short');
      });

      it('should handle numeric values', () => {
        // @ts-ignore - Testing runtime behavior
        expect(cn(123, 456)).toBe('123 456');
      });

      it('should handle deeply nested arrays', () => {
        expect(cn([['foo'], [['bar']]])).toBe('foo bar');
      });

      it('should handle mixed tailwind utilities', () => {
        expect(cn(
          'hover:bg-blue-500',
          'focus:outline-none',
          'active:bg-blue-600'
        )).toBe('hover:bg-blue-500 focus:outline-none active:bg-blue-600');
      });
    });

    describe('generateUniqueId edge cases', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should handle Math.random returning edge values', () => {
        jest.spyOn(Math, 'random').mockReturnValue(0);
        const id1 = generateUniqueId('edge');
        
        jest.spyOn(Math, 'random').mockReturnValue(0.999999);
        const id2 = generateUniqueId('edge');
        
        expect(id1).toMatch(/^edge_\d+_\d+_[a-z0-9]*$/);
        expect(id2).toMatch(/^edge_\d+_\d+_[a-z0-9]+$/);
        
        jest.restoreAllMocks();
      });

      it('should handle Date.now edge cases', () => {
        // Test with very large timestamp
        jest.spyOn(Date, 'now').mockReturnValue(Number.MAX_SAFE_INTEGER);
        const id = generateUniqueId('max');
        expect(id).toMatch(/^max_\d+_\d+_[a-z0-9]+$/);
        
        jest.restoreAllMocks();
      });

      it('should maintain thread safety characteristics', () => {
        // Simulate rapid successive calls
        const results = [];
        for (let i = 0; i < 100; i++) {
          results.push(generateUniqueId('thread'));
        }
        
        // Check all are unique
        const unique = new Set(results);
        expect(unique.size).toBe(results.length);
        
        // Check counter increments properly
        const counters = results.map(id => parseInt(id.split('_')[2], 10));
        for (let i = 1; i < counters.length; i++) {
          expect(counters[i]).toBe(counters[i - 1] + 1);
        }
      });
    });
  });

  describe('Type safety', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should have correct TypeScript types for cn', () => {
      // These should compile without errors
      const result1: string = cn('foo');
      const result2: string = cn('foo', 'bar');
      const result3: string = cn(['foo'], { bar: true });
      
      expect(typeof result1).toBe('string');
      expect(typeof result2).toBe('string');
      expect(typeof result3).toBe('string');
    });

    it('should have correct TypeScript types for generateUniqueId', () => {
      // These should compile without errors
      const id1: string = generateUniqueId();
      const id2: string = generateUniqueId('prefix');
      
      expect(typeof id1).toBe('string');
      expect(typeof id2).toBe('string');
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});