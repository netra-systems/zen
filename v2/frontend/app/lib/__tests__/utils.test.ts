
import { cn } from '../utils';

describe('cn', () => {
  it('should merge class names', () => {
    expect(cn('a', 'b')).toBe('a b');
  });

  it('should handle conditional class names', () => {
    expect(cn('a', { b: true, c: false })).toBe('a b');
  });

  it('should remove conflicting class names', () => {
    expect(cn('p-4', 'p-2')).toBe('p-2');
  });
});
