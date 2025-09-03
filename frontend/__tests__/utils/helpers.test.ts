// Helper functions for testing
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

export function groupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
  return array.reduce((result, item) => {
    const group = String(item[key]);
    if (!result[group]) result[group] = [];
    result[group].push(item);
    return result;
  }, {} as Record<string, T[]>);
}

export function sortBy<T>(array: T[], key: keyof T, order: 'asc' | 'desc' = 'asc'): T[] {
  return [...array].sort((a, b) => {
    const aVal = a[key];
    const bVal = b[key];
    
    if (aVal < bVal) return order === 'asc' ? -1 : 1;
    if (aVal > bVal) return order === 'asc' ? 1 : -1;
    return 0;
  });
}

export function unique<T>(array: T[]): T[] {
  return [...new Set(array)];
}

export function range(start: number, end: number, step = 1): number[] {
  const result = [];
  for (let i = start; i < end; i += step) {
    result.push(i);
  }
  return result;
}

describe('Helper Functions', () => {
  describe('truncateText', () => {
    it('truncates long text', () => {
      expect(truncateText('This is a very long text', 10)).toBe('This is...');
      expect(truncateText('Short', 10)).toBe('Short');
    });

    it('handles edge cases', () => {
      expect(truncateText('', 10)).toBe('');
      expect(truncateText('Exact', 5)).toBe('Exact');
      expect(truncateText('Longer', 5)).toBe('Lo...');
    });
  });

  describe('groupBy', () => {
    it('groups array by key', () => {
      const data = [
        { id: 1, category: 'A' },
        { id: 2, category: 'B' },
        { id: 3, category: 'A' },
      ];
      
      const grouped = groupBy(data, 'category');
      
      expect(grouped).toEqual({
        A: [{ id: 1, category: 'A' }, { id: 3, category: 'A' }],
        B: [{ id: 2, category: 'B' }],
      });
    });

    it('handles empty array', () => {
      expect(groupBy([], 'id')).toEqual({});
    });
  });

  describe('sortBy', () => {
    const data = [
      { id: 3, name: 'Charlie' },
      { id: 1, name: 'Alice' },
      { id: 2, name: 'Bob' },
    ];

    it('sorts ascending by default', () => {
      const sorted = sortBy(data, 'id');
      expect(sorted[0].id).toBe(1);
      expect(sorted[1].id).toBe(2);
      expect(sorted[2].id).toBe(3);
    });

    it('sorts descending', () => {
      const sorted = sortBy(data, 'name', 'desc');
      expect(sorted[0].name).toBe('Charlie');
      expect(sorted[1].name).toBe('Bob');
      expect(sorted[2].name).toBe('Alice');
    });

    it('does not mutate original array', () => {
      const original = [...data];
      sortBy(data, 'id');
      expect(data).toEqual(original);
    });
  });

  describe('unique', () => {
    it('removes duplicates', () => {
      expect(unique([1, 2, 2, 3, 3, 3])).toEqual([1, 2, 3]);
      expect(unique(['a', 'b', 'a', 'c'])).toEqual(['a', 'b', 'c']);
    });

    it('handles empty array', () => {
      expect(unique([])).toEqual([]);
    });

    it('preserves order', () => {
      expect(unique([3, 1, 2, 1, 3])).toEqual([3, 1, 2]);
    });
  });

  describe('range', () => {
    it('creates range with default step', () => {
      expect(range(0, 5)).toEqual([0, 1, 2, 3, 4]);
      expect(range(1, 4)).toEqual([1, 2, 3]);
    });

    it('creates range with custom step', () => {
      expect(range(0, 10, 2)).toEqual([0, 2, 4, 6, 8]);
      expect(range(5, 20, 5)).toEqual([5, 10, 15]);
    });

    it('handles negative ranges', () => {
      expect(range(-3, 2)).toEqual([-3, -2, -1, 0, 1]);
    });

    it('returns empty array for invalid range', () => {
      expect(range(5, 2)).toEqual([]);
    });
  });
});