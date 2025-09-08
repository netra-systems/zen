/**
 * Validation Utilities Test Suite
 * 20 comprehensive tests for validation utilities
 */

// Validation utility functions
const validationUtils = {
  isEmail: (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },

  isUrl: (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  },

  isPhoneNumber: (phone: string): boolean => {
    const phoneRegex = /^\+?[\d\s\-()]{10,}$/;
    return phoneRegex.test(phone);
  },

  isStrongPassword: (password: string): boolean => {
    // At least 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special char
    const strongPasswordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
    return strongPasswordRegex.test(password);
  },

  isCreditCard: (cardNumber: string): boolean => {
    // Remove spaces and dashes
    const cleanNumber = cardNumber.replace(/[\s-]/g, '');
    
    // Check if all characters are digits and length is valid
    if (!/^\d{13,19}$/.test(cleanNumber)) return false;
    
    // Luhn algorithm
    let sum = 0;
    let shouldDouble = false;
    
    for (let i = cleanNumber.length - 1; i >= 0; i--) {
      let digit = parseInt(cleanNumber.charAt(i), 10);
      
      if (shouldDouble) {
        digit *= 2;
        if (digit > 9) digit -= 9;
      }
      
      sum += digit;
      shouldDouble = !shouldDouble;
    }
    
    return sum % 10 === 0;
  },

  isIPAddress: (ip: string): boolean => {
    const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    return ipRegex.test(ip);
  },

  isUUID: (uuid: string): boolean => {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
  },

  isJSON: (str: string): boolean => {
    try {
      JSON.parse(str);
      return true;
    } catch {
      return false;
    }
  },

  isAlphanumeric: (str: string): boolean => {
    return /^[a-zA-Z0-9]+$/.test(str);
  },

  isNumeric: (str: string): boolean => {
    return /^\d+$/.test(str);
  },

  isAlpha: (str: string): boolean => {
    return /^[a-zA-Z]+$/.test(str);
  },

  isLength: (str: string, min: number, max?: number): boolean => {
    if (max !== undefined) {
      return str.length >= min && str.length <= max;
    }
    return str.length >= min;
  },

  isIn: <T>(value: T, validValues: T[]): boolean => {
    return validValues.includes(value);
  },

  isDateString: (dateStr: string): boolean => {
    const date = new Date(dateStr);
    return date instanceof Date && !isNaN(date.getTime()) && date.toISOString().startsWith(dateStr.split('T')[0]);
  },

  isHexColor: (color: string): boolean => {
    return /^#[0-9A-F]{6}$/i.test(color) || /^#[0-9A-F]{3}$/i.test(color);
  },

  isSlug: (str: string): boolean => {
    return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(str);
  },

  isEmpty: (value: any): boolean => {
    if (value === null || value === undefined) return true;
    if (typeof value === 'string') return value.trim().length === 0;
    if (Array.isArray(value)) return value.length === 0;
    if (typeof value === 'object') return Object.keys(value).length === 0;
    return false;
  },

  isRequired: (value: any): boolean => {
    return !validationUtils.isEmpty(value);
  },

  isPositiveInteger: (num: number): boolean => {
    return Number.isInteger(num) && num > 0;
  },

  isInRange: (num: number, min: number, max: number): boolean => {
    return num >= min && num <= max;
  }
};

describe('Validation Utils - Basic Format Validation', () => {
  test('should validate email addresses', () => {
    expect(validationUtils.isEmail('test@example.com')).toBe(true);
    expect(validationUtils.isEmail('user+tag@domain.co.uk')).toBe(true);
    expect(validationUtils.isEmail('invalid-email')).toBe(false);
    expect(validationUtils.isEmail('@example.com')).toBe(false);
  });

  test('should validate URLs', () => {
    expect(validationUtils.isUrl('https://example.com')).toBe(true);
    expect(validationUtils.isUrl('http://localhost:3000')).toBe(true);
    expect(validationUtils.isUrl('ftp://files.example.com')).toBe(true);
    expect(validationUtils.isUrl('not-a-url')).toBe(false);
  });

  test('should validate phone numbers', () => {
    expect(validationUtils.isPhoneNumber('+1-555-123-4567')).toBe(true);
    expect(validationUtils.isPhoneNumber('(555) 123-4567')).toBe(true);
    expect(validationUtils.isPhoneNumber('5551234567')).toBe(true);
    expect(validationUtils.isPhoneNumber('123')).toBe(false);
  });
});

describe('Validation Utils - Password Strength', () => {
  test('should validate strong passwords', () => {
    expect(validationUtils.isStrongPassword('StrongPass123!')).toBe(true);
    expect(validationUtils.isStrongPassword('Complex@123')).toBe(true);
    expect(validationUtils.isStrongPassword('weakpass')).toBe(false);
    expect(validationUtils.isStrongPassword('NoSpecial123')).toBe(false);
  });
});

describe('Validation Utils - Financial Validation', () => {
  test('should validate credit card numbers', () => {
    // Valid test card numbers (Visa format)
    expect(validationUtils.isCreditCard('4111111111111111')).toBe(true);
    expect(validationUtils.isCreditCard('4111 1111 1111 1111')).toBe(true);
    expect(validationUtils.isCreditCard('4111-1111-1111-1111')).toBe(true);
    expect(validationUtils.isCreditCard('1234567890123456')).toBe(false);
  });
});

describe('Validation Utils - Technical Format Validation', () => {
  test('should validate IP addresses', () => {
    expect(validationUtils.isIPAddress('192.168.1.1')).toBe(true);
    expect(validationUtils.isIPAddress('127.0.0.1')).toBe(true);
    expect(validationUtils.isIPAddress('255.255.255.255')).toBe(true);
    expect(validationUtils.isIPAddress('256.1.1.1')).toBe(false);
    expect(validationUtils.isIPAddress('192.168.1')).toBe(false);
  });

  test('should validate UUIDs', () => {
    expect(validationUtils.isUUID('550e8400-e29b-41d4-a716-446655440000')).toBe(true);
    expect(validationUtils.isUUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')).toBe(true);
    expect(validationUtils.isUUID('not-a-uuid')).toBe(false);
    expect(validationUtils.isUUID('550e8400-e29b-41d4-a716')).toBe(false);
  });

  test('should validate JSON strings', () => {
    expect(validationUtils.isJSON('{"key": "value"}')).toBe(true);
    expect(validationUtils.isJSON('[1, 2, 3]')).toBe(true);
    expect(validationUtils.isJSON('"string"')).toBe(true);
    expect(validationUtils.isJSON('invalid json')).toBe(false);
  });
});

describe('Validation Utils - Character Set Validation', () => {
  test('should validate alphanumeric strings', () => {
    expect(validationUtils.isAlphanumeric('abc123')).toBe(true);
    expect(validationUtils.isAlphanumeric('ABC123')).toBe(true);
    expect(validationUtils.isAlphanumeric('abc-123')).toBe(false);
    expect(validationUtils.isAlphanumeric('abc 123')).toBe(false);
  });

  test('should validate numeric strings', () => {
    expect(validationUtils.isNumeric('12345')).toBe(true);
    expect(validationUtils.isNumeric('0')).toBe(true);
    expect(validationUtils.isNumeric('123.45')).toBe(false);
    expect(validationUtils.isNumeric('abc')).toBe(false);
  });

  test('should validate alphabetic strings', () => {
    expect(validationUtils.isAlpha('abcDEF')).toBe(true);
    expect(validationUtils.isAlpha('HelloWorld')).toBe(true);
    expect(validationUtils.isAlpha('abc123')).toBe(false);
    expect(validationUtils.isAlpha('hello world')).toBe(false);
  });
});

describe('Validation Utils - Length and Range Validation', () => {
  test('should validate string length', () => {
    expect(validationUtils.isLength('hello', 3)).toBe(true);
    expect(validationUtils.isLength('hello', 3, 10)).toBe(true);
    expect(validationUtils.isLength('hi', 3)).toBe(false);
    expect(validationUtils.isLength('verylongstring', 3, 10)).toBe(false);
  });

  test('should validate value inclusion', () => {
    expect(validationUtils.isIn('red', ['red', 'green', 'blue'])).toBe(true);
    expect(validationUtils.isIn(1, [1, 2, 3])).toBe(true);
    expect(validationUtils.isIn('yellow', ['red', 'green', 'blue'])).toBe(false);
  });
});

describe('Validation Utils - Date and Color Validation', () => {
  test('should validate date strings', () => {
    expect(validationUtils.isDateString('2024-01-15')).toBe(true);
    expect(validationUtils.isDateString('2024-01-15T10:30:00.000Z')).toBe(true);
    expect(validationUtils.isDateString('invalid-date')).toBe(false);
  });

  test('should validate hex colors', () => {
    expect(validationUtils.isHexColor('#FF0000')).toBe(true);
    expect(validationUtils.isHexColor('#f00')).toBe(true);
    expect(validationUtils.isHexColor('#123ABC')).toBe(true);
    expect(validationUtils.isHexColor('FF0000')).toBe(false);
    expect(validationUtils.isHexColor('#GG0000')).toBe(false);
  });

  test('should validate slugs', () => {
    expect(validationUtils.isSlug('hello-world')).toBe(true);
    expect(validationUtils.isSlug('my-blog-post-123')).toBe(true);
    expect(validationUtils.isSlug('simple')).toBe(true);
    expect(validationUtils.isSlug('Hello-World')).toBe(false);
    expect(validationUtils.isSlug('hello_world')).toBe(false);
  });
});

describe('Validation Utils - Emptiness and Requirements', () => {
  test('should detect empty values', () => {
    expect(validationUtils.isEmpty(null)).toBe(true);
    expect(validationUtils.isEmpty(undefined)).toBe(true);
    expect(validationUtils.isEmpty('')).toBe(true);
    expect(validationUtils.isEmpty('   ')).toBe(true);
    expect(validationUtils.isEmpty([])).toBe(true);
    expect(validationUtils.isEmpty({})).toBe(true);
    expect(validationUtils.isEmpty('hello')).toBe(false);
    expect(validationUtils.isEmpty([1])).toBe(false);
    expect(validationUtils.isEmpty({ a: 1 })).toBe(false);
  });

  test('should validate required values', () => {
    expect(validationUtils.isRequired('value')).toBe(true);
    expect(validationUtils.isRequired(0)).toBe(true);
    expect(validationUtils.isRequired(false)).toBe(true);
    expect(validationUtils.isRequired(null)).toBe(false);
    expect(validationUtils.isRequired('')).toBe(false);
  });
});

describe('Validation Utils - Number Validation', () => {
  test('should validate positive integers', () => {
    expect(validationUtils.isPositiveInteger(1)).toBe(true);
    expect(validationUtils.isPositiveInteger(100)).toBe(true);
    expect(validationUtils.isPositiveInteger(0)).toBe(false);
    expect(validationUtils.isPositiveInteger(-1)).toBe(false);
    expect(validationUtils.isPositiveInteger(1.5)).toBe(false);
  });

  test('should validate number ranges', () => {
    expect(validationUtils.isInRange(5, 1, 10)).toBe(true);
    expect(validationUtils.isInRange(1, 1, 10)).toBe(true);
    expect(validationUtils.isInRange(10, 1, 10)).toBe(true);
    expect(validationUtils.isInRange(0, 1, 10)).toBe(false);
    expect(validationUtils.isInRange(11, 1, 10)).toBe(false);
  });
});