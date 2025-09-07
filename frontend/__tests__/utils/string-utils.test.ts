/**
 * String Utilities Test Suite
 * 30 comprehensive tests for string manipulation utilities
 */

// String utility functions
const stringUtils = {
  capitalize: (str: string): string => {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  },

  camelCase: (str: string): string => {
    return str
      .replace(/(?:^\w|[A-Z]|\b\w)/g, (word, index) => 
        index === 0 ? word.toLowerCase() : word.toUpperCase()
      )
      .replace(/\s+/g, '');
  },

  kebabCase: (str: string): string => {
    return str
      .replace(/([a-z])([A-Z])/g, '$1-$2')
      .replace(/\s+/g, '-')
      .toLowerCase();
  },

  snakeCase: (str: string): string => {
    return str
      .replace(/([a-z])([A-Z])/g, '$1_$2')
      .replace(/\s+/g, '_')
      .toLowerCase();
  },

  truncate: (str: string, length: number, suffix = '...'): string => {
    if (str.length <= length) return str;
    return str.substring(0, length - suffix.length) + suffix;
  },

  removeExtraSpaces: (str: string): string => {
    return str.replace(/\s+/g, ' ').trim();
  },

  countWords: (str: string): number => {
    return str.trim() === '' ? 0 : str.trim().split(/\s+/).length;
  },

  reverseWords: (str: string): string => {
    return str.split(' ').reverse().join(' ');
  },

  extractNumbers: (str: string): number[] => {
    const matches = str.match(/\d+/g);
    return matches ? matches.map(Number) : [];
  },

  removeNumbers: (str: string): string => {
    return str.replace(/\d+/g, '').replace(/\s+/g, ' ').trim();
  },

  isValidEmail: (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },

  maskEmail: (email: string): string => {
    const parts = email.split('@');
    if (parts.length !== 2) return email;
    const username = parts[0];
    const domain = parts[1];
    const maskedUsername = username.length > 2 
      ? username.substring(0, 2) + '*'.repeat(username.length - 2)
      : username;
    return `${maskedUsername}@${domain}`;
  },

  pluralize: (word: string, count: number): string => {
    if (count === 1) return word;
    if (word.endsWith('y')) return word.slice(0, -1) + 'ies';
    if (word.endsWith('s') || word.endsWith('x') || word.endsWith('z')) return word + 'es';
    return word + 's';
  },

  stripHtml: (html: string): string => {
    return html.replace(/<[^>]*>/g, '');
  },

  escapeHtml: (str: string): string => {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  },

  unescapeHtml: (str: string): string => {
    const div = document.createElement('div');
    div.innerHTML = str;
    return div.textContent || div.innerText || '';
  },

  padLeft: (str: string, length: number, padChar = ' '): string => {
    return str.padStart(length, padChar);
  },

  padRight: (str: string, length: number, padChar = ' '): string => {
    return str.padEnd(length, padChar);
  },

  containsOnlyNumbers: (str: string): boolean => {
    return /^\d+$/.test(str);
  },

  containsOnlyLetters: (str: string): boolean => {
    return /^[a-zA-Z]+$/.test(str);
  }
};

describe('String Utils - Capitalize', () => {
  test('should capitalize first letter and lowercase rest', () => {
    expect(stringUtils.capitalize('hello')).toBe('Hello');
  });

  test('should handle uppercase input', () => {
    expect(stringUtils.capitalize('HELLO')).toBe('Hello');
  });

  test('should handle empty string', () => {
    expect(stringUtils.capitalize('')).toBe('');
  });

  test('should handle single character', () => {
    expect(stringUtils.capitalize('a')).toBe('A');
  });
});

describe('String Utils - Case Conversion', () => {
  test('should convert to camelCase', () => {
    expect(stringUtils.camelCase('hello world')).toBe('helloWorld');
  });

  test('should convert to kebab-case', () => {
    expect(stringUtils.kebabCase('Hello World')).toBe('hello-world');
  });

  test('should convert to snake_case', () => {
    expect(stringUtils.snakeCase('Hello World')).toBe('hello_world');
  });

  test('should handle camelCase to kebab-case', () => {
    expect(stringUtils.kebabCase('helloWorld')).toBe('hello-world');
  });

  test('should handle camelCase to snake_case', () => {
    expect(stringUtils.snakeCase('helloWorld')).toBe('hello_world');
  });
});

describe('String Utils - Text Manipulation', () => {
  test('should truncate long strings', () => {
    expect(stringUtils.truncate('Hello World', 5)).toBe('He...');
  });

  test('should not truncate short strings', () => {
    expect(stringUtils.truncate('Hi', 5)).toBe('Hi');
  });

  test('should use custom suffix', () => {
    expect(stringUtils.truncate('Hello World', 5, '***')).toBe('He***');
  });

  test('should remove extra spaces', () => {
    expect(stringUtils.removeExtraSpaces('  hello    world  ')).toBe('hello world');
  });

  test('should count words correctly', () => {
    expect(stringUtils.countWords('hello world test')).toBe(3);
  });

  test('should handle empty string word count', () => {
    expect(stringUtils.countWords('')).toBe(0);
  });

  test('should handle whitespace-only word count', () => {
    expect(stringUtils.countWords('   ')).toBe(0);
  });
});

describe('String Utils - Word Operations', () => {
  test('should reverse word order', () => {
    expect(stringUtils.reverseWords('hello world test')).toBe('test world hello');
  });

  test('should extract numbers from string', () => {
    expect(stringUtils.extractNumbers('abc123def456')).toEqual([123, 456]);
  });

  test('should return empty array when no numbers', () => {
    expect(stringUtils.extractNumbers('abcdef')).toEqual([]);
  });

  test('should remove numbers from string', () => {
    expect(stringUtils.removeNumbers('abc123def456')).toBe('abcdef');
  });
});

describe('String Utils - Email Operations', () => {
  test('should validate correct email', () => {
    expect(stringUtils.isValidEmail('test@example.com')).toBe(true);
  });

  test('should reject invalid email', () => {
    expect(stringUtils.isValidEmail('invalid-email')).toBe(false);
  });

  test('should mask email address', () => {
    expect(stringUtils.maskEmail('john@example.com')).toBe('jo**@example.com');
  });

  test('should handle short email usernames', () => {
    expect(stringUtils.maskEmail('ab@example.com')).toBe('ab@example.com');
  });
});

describe('String Utils - Pluralization', () => {
  test('should not pluralize singular count', () => {
    expect(stringUtils.pluralize('cat', 1)).toBe('cat');
  });

  test('should pluralize regular words', () => {
    expect(stringUtils.pluralize('cat', 2)).toBe('cats');
  });

  test('should handle words ending in y', () => {
    expect(stringUtils.pluralize('city', 2)).toBe('cities');
  });

  test('should handle words ending in s', () => {
    expect(stringUtils.pluralize('glass', 2)).toBe('glasses');
  });
});

describe('String Utils - HTML Operations', () => {
  test('should strip HTML tags', () => {
    expect(stringUtils.stripHtml('<p>Hello <strong>World</strong></p>')).toBe('Hello World');
  });

  test('should escape HTML entities', () => {
    expect(stringUtils.escapeHtml('<script>')).toBe('&lt;script&gt;');
  });

  test('should unescape HTML entities', () => {
    expect(stringUtils.unescapeHtml('&lt;script&gt;')).toBe('<script>');
  });
});

describe('String Utils - Padding', () => {
  test('should pad left with spaces', () => {
    expect(stringUtils.padLeft('test', 8)).toBe('    test');
  });

  test('should pad right with spaces', () => {
    expect(stringUtils.padRight('test', 8)).toBe('test    ');
  });

  test('should pad with custom character', () => {
    expect(stringUtils.padLeft('test', 8, '0')).toBe('0000test');
  });
});

describe('String Utils - Content Validation', () => {
  test('should detect numbers-only string', () => {
    expect(stringUtils.containsOnlyNumbers('12345')).toBe(true);
  });

  test('should reject mixed content as numbers-only', () => {
    expect(stringUtils.containsOnlyNumbers('123abc')).toBe(false);
  });

  test('should detect letters-only string', () => {
    expect(stringUtils.containsOnlyLetters('abcDEF')).toBe(true);
  });

  test('should reject mixed content as letters-only', () => {
    expect(stringUtils.containsOnlyLetters('abc123')).toBe(false);
  });
});