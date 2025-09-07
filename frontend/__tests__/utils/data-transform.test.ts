/**
 * Data Transformation Utilities Test Suite
 * 25 comprehensive tests for data transformation and manipulation utilities
 */

// Data transformation utility functions
const dataUtils = {
  deepClone: <T>(obj: T): T => {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj.getTime()) as unknown as T;
    if (obj instanceof Array) return obj.map(item => dataUtils.deepClone(item)) as unknown as T;
    if (typeof obj === 'object') {
      const copy = {} as { [key: string]: any };
      Object.keys(obj).forEach(key => {
        copy[key] = dataUtils.deepClone((obj as any)[key]);
      });
      return copy as T;
    }
    return obj;
  },

  flattenObject: (obj: Record<string, any>, prefix = ''): Record<string, any> => {
    const result: Record<string, any> = {};
    
    Object.keys(obj).forEach(key => {
      const newKey = prefix ? `${prefix}.${key}` : key;
      
      if (obj[key] !== null && typeof obj[key] === 'object' && !Array.isArray(obj[key])) {
        Object.assign(result, dataUtils.flattenObject(obj[key], newKey));
      } else {
        result[newKey] = obj[key];
      }
    });
    
    return result;
  },

  unflattenObject: (obj: Record<string, any>): Record<string, any> => {
    const result: Record<string, any> = {};
    
    Object.keys(obj).forEach(key => {
      const keys = key.split('.');
      let current = result;
      
      for (let i = 0; i < keys.length - 1; i++) {
        const k = keys[i];
        if (!(k in current)) {
          current[k] = {};
        }
        current = current[k];
      }
      
      current[keys[keys.length - 1]] = obj[key];
    });
    
    return result;
  },

  groupBy: <T>(array: T[], key: keyof T | ((item: T) => string)): Record<string, T[]> => {
    return array.reduce((groups, item) => {
      const groupKey = typeof key === 'function' ? key(item) : String(item[key]);
      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(item);
      return groups;
    }, {} as Record<string, T[]>);
  },

  sortBy: <T>(array: T[], key: keyof T | ((item: T) => any), order: 'asc' | 'desc' = 'asc'): T[] => {
    return [...array].sort((a, b) => {
      const aValue = typeof key === 'function' ? key(a) : a[key];
      const bValue = typeof key === 'function' ? key(b) : b[key];
      
      if (aValue < bValue) return order === 'asc' ? -1 : 1;
      if (aValue > bValue) return order === 'asc' ? 1 : -1;
      return 0;
    });
  },

  unique: <T>(array: T[], key?: keyof T | ((item: T) => any)): T[] => {
    if (!key) {
      return [...new Set(array)];
    }
    
    const seen = new Set();
    return array.filter(item => {
      const keyValue = typeof key === 'function' ? key(item) : item[key];
      if (seen.has(keyValue)) {
        return false;
      }
      seen.add(keyValue);
      return true;
    });
  },

  chunk: <T>(array: T[], size: number): T[][] => {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size));
    }
    return chunks;
  },

  partition: <T>(array: T[], predicate: (item: T) => boolean): [T[], T[]] => {
    const truthy: T[] = [];
    const falsy: T[] = [];
    
    array.forEach(item => {
      if (predicate(item)) {
        truthy.push(item);
      } else {
        falsy.push(item);
      }
    });
    
    return [truthy, falsy];
  },

  pick: <T extends Record<string, any>, K extends keyof T>(obj: T, keys: K[]): Pick<T, K> => {
    const result = {} as Pick<T, K>;
    keys.forEach(key => {
      if (key in obj) {
        result[key] = obj[key];
      }
    });
    return result;
  },

  omit: <T extends Record<string, any>, K extends keyof T>(obj: T, keys: K[]): Omit<T, K> => {
    const result = { ...obj };
    keys.forEach(key => {
      delete result[key];
    });
    return result;
  },

  merge: <T extends Record<string, any>>(target: T, ...sources: Partial<T>[]): T => {
    return sources.reduce((acc, source) => {
      Object.keys(source).forEach(key => {
        if (source[key] !== undefined) {
          (acc as any)[key] = source[key];
        }
      });
      return acc;
    }, { ...target });
  },

  isEmpty: (value: any): boolean => {
    if (value === null || value === undefined) return true;
    if (typeof value === 'string' || Array.isArray(value)) return value.length === 0;
    if (typeof value === 'object') return Object.keys(value).length === 0;
    return false;
  },

  isEqual: (a: any, b: any): boolean => {
    if (a === b) return true;
    if (a === null || b === null) return false;
    if (typeof a !== typeof b) return false;
    
    if (Array.isArray(a) && Array.isArray(b)) {
      if (a.length !== b.length) return false;
      return a.every((val, index) => dataUtils.isEqual(val, b[index]));
    }
    
    if (typeof a === 'object') {
      const aKeys = Object.keys(a);
      const bKeys = Object.keys(b);
      if (aKeys.length !== bKeys.length) return false;
      return aKeys.every(key => dataUtils.isEqual(a[key], b[key]));
    }
    
    return false;
  },

  sum: (array: number[]): number => array.reduce((acc, val) => acc + val, 0),
  average: (array: number[]): number => array.length ? dataUtils.sum(array) / array.length : 0,
  min: (array: number[]): number => Math.min(...array),
  max: (array: number[]): number => Math.max(...array),

  capitalize: (str: string): string => str.charAt(0).toUpperCase() + str.slice(1),

  mapObject: <T, R>(obj: Record<string, T>, fn: (value: T, key: string) => R): Record<string, R> => {
    const result: Record<string, R> = {};
    Object.keys(obj).forEach(key => {
      result[key] = fn(obj[key], key);
    });
    return result;
  },

  filterObject: <T>(obj: Record<string, T>, predicate: (value: T, key: string) => boolean): Record<string, T> => {
    const result: Record<string, T> = {};
    Object.keys(obj).forEach(key => {
      if (predicate(obj[key], key)) {
        result[key] = obj[key];
      }
    });
    return result;
  },

  arrayToObject: <T>(array: T[], keyFn: (item: T) => string): Record<string, T> => {
    return array.reduce((obj, item) => {
      obj[keyFn(item)] = item;
      return obj;
    }, {} as Record<string, T>);
  },

  objectToArray: <T>(obj: Record<string, T>): Array<{ key: string; value: T }> => {
    return Object.keys(obj).map(key => ({ key, value: obj[key] }));
  },

  transpose: <T>(matrix: T[][]): T[][] => {
    if (matrix.length === 0) return [];
    return matrix[0].map((_, colIndex) => matrix.map(row => row[colIndex]));
  }
};

describe('Data Utils - Deep Operations', () => {
  test('should deep clone simple objects', () => {
    const original = { a: 1, b: 'test' };
    const cloned = dataUtils.deepClone(original);
    
    expect(cloned).toEqual(original);
    expect(cloned).not.toBe(original);
  });

  test('should deep clone nested objects', () => {
    const original = { a: { b: { c: 1 } } };
    const cloned = dataUtils.deepClone(original);
    
    cloned.a.b.c = 2;
    expect(original.a.b.c).toBe(1);
  });

  test('should deep clone arrays', () => {
    const original = [1, [2, 3], { a: 4 }];
    const cloned = dataUtils.deepClone(original);
    
    expect(cloned).toEqual(original);
    expect(cloned).not.toBe(original);
  });

  test('should deep clone dates', () => {
    const original = new Date('2024-01-15');
    const cloned = dataUtils.deepClone(original);
    
    expect(cloned.getTime()).toBe(original.getTime());
    expect(cloned).not.toBe(original);
  });
});

describe('Data Utils - Object Flattening', () => {
  test('should flatten nested object', () => {
    const nested = { a: { b: { c: 1 } }, d: 2 };
    const flattened = dataUtils.flattenObject(nested);
    
    expect(flattened).toEqual({ 'a.b.c': 1, d: 2 });
  });

  test('should unflatten object', () => {
    const flattened = { 'a.b.c': 1, d: 2 };
    const unflattened = dataUtils.unflattenObject(flattened);
    
    expect(unflattened).toEqual({ a: { b: { c: 1 } }, d: 2 });
  });

  test('should handle empty object', () => {
    expect(dataUtils.flattenObject({})).toEqual({});
  });
});

describe('Data Utils - Array Grouping', () => {
  test('should group by property', () => {
    const data = [
      { type: 'fruit', name: 'apple' },
      { type: 'fruit', name: 'banana' },
      { type: 'vegetable', name: 'carrot' }
    ];
    
    const grouped = dataUtils.groupBy(data, 'type');
    
    expect(grouped.fruit).toHaveLength(2);
    expect(grouped.vegetable).toHaveLength(1);
  });

  test('should group by function', () => {
    const data = [1, 2, 3, 4, 5, 6];
    const grouped = dataUtils.groupBy(data, item => item % 2 === 0 ? 'even' : 'odd');
    
    expect(grouped.even).toEqual([2, 4, 6]);
    expect(grouped.odd).toEqual([1, 3, 5]);
  });
});

describe('Data Utils - Array Sorting', () => {
  test('should sort by property ascending', () => {
    const data = [{ age: 30 }, { age: 20 }, { age: 25 }];
    const sorted = dataUtils.sortBy(data, 'age');
    
    expect(sorted.map(item => item.age)).toEqual([20, 25, 30]);
  });

  test('should sort by property descending', () => {
    const data = [{ age: 30 }, { age: 20 }, { age: 25 }];
    const sorted = dataUtils.sortBy(data, 'age', 'desc');
    
    expect(sorted.map(item => item.age)).toEqual([30, 25, 20]);
  });

  test('should sort by function', () => {
    const data = ['apple', 'banana', 'cherry'];
    const sorted = dataUtils.sortBy(data, item => item.length);
    
    expect(sorted).toEqual(['apple', 'banana', 'cherry']);
  });
});

describe('Data Utils - Array Uniqueness', () => {
  test('should get unique primitive values', () => {
    const data = [1, 2, 2, 3, 3, 4];
    const unique = dataUtils.unique(data);
    
    expect(unique).toEqual([1, 2, 3, 4]);
  });

  test('should get unique by property', () => {
    const data = [{ id: 1 }, { id: 2 }, { id: 1 }, { id: 3 }];
    const unique = dataUtils.unique(data, 'id');
    
    expect(unique).toHaveLength(3);
    expect(unique.map(item => item.id)).toEqual([1, 2, 3]);
  });
});

describe('Data Utils - Array Manipulation', () => {
  test('should chunk array', () => {
    const data = [1, 2, 3, 4, 5, 6, 7];
    const chunks = dataUtils.chunk(data, 3);
    
    expect(chunks).toEqual([[1, 2, 3], [4, 5, 6], [7]]);
  });

  test('should partition array', () => {
    const data = [1, 2, 3, 4, 5, 6];
    const [evens, odds] = dataUtils.partition(data, n => n % 2 === 0);
    
    expect(evens).toEqual([2, 4, 6]);
    expect(odds).toEqual([1, 3, 5]);
  });
});

describe('Data Utils - Object Operations', () => {
  test('should pick specified properties', () => {
    const obj = { a: 1, b: 2, c: 3 };
    const picked = dataUtils.pick(obj, ['a', 'c']);
    
    expect(picked).toEqual({ a: 1, c: 3 });
  });

  test('should omit specified properties', () => {
    const obj = { a: 1, b: 2, c: 3 };
    const omitted = dataUtils.omit(obj, ['b']);
    
    expect(omitted).toEqual({ a: 1, c: 3 });
  });

  test('should merge objects', () => {
    const target = { a: 1, b: 2 };
    const source = { b: 3, c: 4 };
    const merged = dataUtils.merge(target, source);
    
    expect(merged).toEqual({ a: 1, b: 3, c: 4 });
  });
});

describe('Data Utils - Validation', () => {
  test('should detect empty values', () => {
    expect(dataUtils.isEmpty(null)).toBe(true);
    expect(dataUtils.isEmpty(undefined)).toBe(true);
    expect(dataUtils.isEmpty('')).toBe(true);
    expect(dataUtils.isEmpty([])).toBe(true);
    expect(dataUtils.isEmpty({})).toBe(true);
    expect(dataUtils.isEmpty('test')).toBe(false);
    expect(dataUtils.isEmpty([1])).toBe(false);
  });

  test('should compare equality correctly', () => {
    expect(dataUtils.isEqual({ a: 1 }, { a: 1 })).toBe(true);
    expect(dataUtils.isEqual([1, 2], [1, 2])).toBe(true);
    expect(dataUtils.isEqual({ a: 1 }, { a: 2 })).toBe(false);
  });
});

describe('Data Utils - Mathematical Operations', () => {
  test('should calculate sum', () => {
    expect(dataUtils.sum([1, 2, 3, 4])).toBe(10);
  });

  test('should calculate average', () => {
    expect(dataUtils.average([1, 2, 3, 4])).toBe(2.5);
  });

  test('should find min and max', () => {
    const data = [5, 1, 9, 3];
    expect(dataUtils.min(data)).toBe(1);
    expect(dataUtils.max(data)).toBe(9);
  });
});

describe('Data Utils - Advanced Operations', () => {
  test('should map object values', () => {
    const obj = { a: 1, b: 2, c: 3 };
    const mapped = dataUtils.mapObject(obj, val => val * 2);
    
    expect(mapped).toEqual({ a: 2, b: 4, c: 6 });
  });

  test('should filter object', () => {
    const obj = { a: 1, b: 2, c: 3 };
    const filtered = dataUtils.filterObject(obj, val => val > 1);
    
    expect(filtered).toEqual({ b: 2, c: 3 });
  });

  test('should convert array to object', () => {
    const data = [{ id: '1', name: 'Alice' }, { id: '2', name: 'Bob' }];
    const obj = dataUtils.arrayToObject(data, item => item.id);
    
    expect(obj['1']).toEqual({ id: '1', name: 'Alice' });
    expect(obj['2']).toEqual({ id: '2', name: 'Bob' });
  });

  test('should transpose matrix', () => {
    const matrix = [[1, 2], [3, 4], [5, 6]];
    const transposed = dataUtils.transpose(matrix);
    
    expect(transposed).toEqual([[1, 3, 5], [2, 4, 6]]);
  });
});