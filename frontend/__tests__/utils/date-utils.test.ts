/**
 * Date Utilities Test Suite
 * 25 comprehensive tests for date formatting and manipulation utilities
 */

// Date utility functions
const dateUtils = {
  formatDate: (date: Date, format: string): string => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    return format
      .replace('YYYY', String(year))
      .replace('MM', month)
      .replace('DD', day)
      .replace('HH', hours)
      .replace('mm', minutes)
      .replace('ss', seconds);
  },

  isToday: (date: Date): boolean => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  },

  isYesterday: (date: Date): boolean => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    return date.toDateString() === yesterday.toDateString();
  },

  addDays: (date: Date, days: number): Date => {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result;
  },

  addHours: (date: Date, hours: number): Date => {
    const result = new Date(date);
    result.setHours(result.getHours() + hours);
    return result;
  },

  addMinutes: (date: Date, minutes: number): Date => {
    const result = new Date(date);
    result.setMinutes(result.getMinutes() + minutes);
    return result;
  },

  getDaysDifference: (date1: Date, date2: Date): number => {
    const diffTime = Math.abs(date2.getTime() - date1.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  },

  getHoursDifference: (date1: Date, date2: Date): number => {
    const diffTime = Math.abs(date2.getTime() - date1.getTime());
    return Math.floor(diffTime / (1000 * 60 * 60));
  },

  getMinutesDifference: (date1: Date, date2: Date): number => {
    const diffTime = Math.abs(date2.getTime() - date1.getTime());
    return Math.floor(diffTime / (1000 * 60));
  },

  startOfDay: (date: Date): Date => {
    const result = new Date(date);
    result.setHours(0, 0, 0, 0);
    return result;
  },

  endOfDay: (date: Date): Date => {
    const result = new Date(date);
    result.setHours(23, 59, 59, 999);
    return result;
  },

  startOfWeek: (date: Date): Date => {
    const result = new Date(date);
    const day = result.getDay();
    const diff = result.getDate() - day;
    return new Date(result.setDate(diff));
  },

  endOfWeek: (date: Date): Date => {
    const result = new Date(date);
    const day = result.getDay();
    const diff = result.getDate() - day + 6;
    return new Date(result.setDate(diff));
  },

  startOfMonth: (date: Date): Date => {
    return new Date(date.getFullYear(), date.getMonth(), 1);
  },

  endOfMonth: (date: Date): Date => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0);
  },

  getWeekOfYear: (date: Date): number => {
    const firstDay = new Date(date.getFullYear(), 0, 1);
    const days = Math.floor((date.getTime() - firstDay.getTime()) / (24 * 60 * 60 * 1000));
    return Math.ceil((days + firstDay.getDay() + 1) / 7);
  },

  isWeekend: (date: Date): boolean => {
    const day = date.getDay();
    return day === 0 || day === 6;
  },

  isWeekday: (date: Date): boolean => {
    return !dateUtils.isWeekend(date);
  },

  getQuarter: (date: Date): number => {
    return Math.floor((date.getMonth() + 3) / 3);
  },

  isLeapYear: (year: number): boolean => {
    return (year % 4 === 0 && year % 100 !== 0) || (year % 400 === 0);
  },

  getDaysInMonth: (year: number, month: number): number => {
    return new Date(year, month + 1, 0).getDate();
  },

  getMonthName: (monthIndex: number): string => {
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    return months[monthIndex] || '';
  },

  getDayName: (dayIndex: number): string => {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return days[dayIndex] || '';
  },

  getAge: (birthDate: Date): number => {
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    
    return age;
  },

  isValidDate: (date: any): boolean => {
    return date instanceof Date && !isNaN(date.getTime());
  },

  parseISOString: (isoString: string): Date | null => {
    try {
      const date = new Date(isoString);
      return dateUtils.isValidDate(date) ? date : null;
    } catch {
      return null;
    }
  }
};

describe('Date Utils - Basic Formatting', () => {
  test('should format date with YYYY-MM-DD pattern', () => {
    const date = new Date(2024, 0, 15); // January 15, 2024
    expect(dateUtils.formatDate(date, 'YYYY-MM-DD')).toBe('2024-01-15');
  });

  test('should format date with DD/MM/YYYY pattern', () => {
    const date = new Date(2024, 0, 15);
    expect(dateUtils.formatDate(date, 'DD/MM/YYYY')).toBe('15/01/2024');
  });

  test('should format date with time HH:mm:ss', () => {
    const date = new Date(2024, 0, 15, 14, 30, 45);
    expect(dateUtils.formatDate(date, 'HH:mm:ss')).toBe('14:30:45');
  });

  test('should format complete datetime', () => {
    const date = new Date(2024, 0, 15, 14, 30, 45);
    expect(dateUtils.formatDate(date, 'YYYY-MM-DD HH:mm:ss')).toBe('2024-01-15 14:30:45');
  });
});

describe('Date Utils - Date Comparisons', () => {
  test('should identify today', () => {
    const today = new Date();
    expect(dateUtils.isToday(today)).toBe(true);
  });

  test('should identify yesterday', () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    expect(dateUtils.isYesterday(yesterday)).toBe(true);
  });

  test('should not identify tomorrow as today', () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    expect(dateUtils.isToday(tomorrow)).toBe(false);
  });

  test('should not identify today as yesterday', () => {
    const today = new Date();
    expect(dateUtils.isYesterday(today)).toBe(false);
  });
});

describe('Date Utils - Date Arithmetic', () => {
  test('should add days correctly', () => {
    const date = new Date(2024, 0, 15);
    const result = dateUtils.addDays(date, 5);
    expect(result.getDate()).toBe(20);
  });

  test('should add hours correctly', () => {
    const date = new Date(2024, 0, 15, 10, 0, 0);
    const result = dateUtils.addHours(date, 3);
    expect(result.getHours()).toBe(13);
  });

  test('should add minutes correctly', () => {
    const date = new Date(2024, 0, 15, 10, 30, 0);
    const result = dateUtils.addMinutes(date, 45);
    expect(result.getMinutes()).toBe(15);
    expect(result.getHours()).toBe(11);
  });

  test('should calculate days difference', () => {
    const date1 = new Date(2024, 0, 15);
    const date2 = new Date(2024, 0, 20);
    expect(dateUtils.getDaysDifference(date1, date2)).toBe(5);
  });

  test('should calculate hours difference', () => {
    const date1 = new Date(2024, 0, 15, 10, 0, 0);
    const date2 = new Date(2024, 0, 15, 15, 0, 0);
    expect(dateUtils.getHoursDifference(date1, date2)).toBe(5);
  });

  test('should calculate minutes difference', () => {
    const date1 = new Date(2024, 0, 15, 10, 30, 0);
    const date2 = new Date(2024, 0, 15, 11, 0, 0);
    expect(dateUtils.getMinutesDifference(date1, date2)).toBe(30);
  });
});

describe('Date Utils - Period Boundaries', () => {
  test('should get start of day', () => {
    const date = new Date(2024, 0, 15, 14, 30, 45);
    const start = dateUtils.startOfDay(date);
    expect(start.getHours()).toBe(0);
    expect(start.getMinutes()).toBe(0);
    expect(start.getSeconds()).toBe(0);
  });

  test('should get end of day', () => {
    const date = new Date(2024, 0, 15, 14, 30, 45);
    const end = dateUtils.endOfDay(date);
    expect(end.getHours()).toBe(23);
    expect(end.getMinutes()).toBe(59);
    expect(end.getSeconds()).toBe(59);
  });

  test('should get start of month', () => {
    const date = new Date(2024, 0, 15);
    const start = dateUtils.startOfMonth(date);
    expect(start.getDate()).toBe(1);
  });

  test('should get end of month', () => {
    const date = new Date(2024, 0, 15); // January 2024
    const end = dateUtils.endOfMonth(date);
    expect(end.getDate()).toBe(31);
  });
});

describe('Date Utils - Week Operations', () => {
  test('should identify weekend days', () => {
    const saturday = new Date(2024, 0, 6); // Saturday
    const sunday = new Date(2024, 0, 7); // Sunday
    expect(dateUtils.isWeekend(saturday)).toBe(true);
    expect(dateUtils.isWeekend(sunday)).toBe(true);
  });

  test('should identify weekdays', () => {
    const monday = new Date(2024, 0, 8); // Monday
    expect(dateUtils.isWeekday(monday)).toBe(true);
  });

  test('should get quarter correctly', () => {
    const q1 = new Date(2024, 1, 15); // February
    const q4 = new Date(2024, 11, 15); // December
    expect(dateUtils.getQuarter(q1)).toBe(1);
    expect(dateUtils.getQuarter(q4)).toBe(4);
  });
});

describe('Date Utils - Calendar Functions', () => {
  test('should detect leap year', () => {
    expect(dateUtils.isLeapYear(2024)).toBe(true);
    expect(dateUtils.isLeapYear(2023)).toBe(false);
  });

  test('should get days in month correctly', () => {
    expect(dateUtils.getDaysInMonth(2024, 1)).toBe(29); // February 2024 (leap year)
    expect(dateUtils.getDaysInMonth(2023, 1)).toBe(28); // February 2023
  });

  test('should get month names', () => {
    expect(dateUtils.getMonthName(0)).toBe('January');
    expect(dateUtils.getMonthName(11)).toBe('December');
  });

  test('should get day names', () => {
    expect(dateUtils.getDayName(0)).toBe('Sunday');
    expect(dateUtils.getDayName(6)).toBe('Saturday');
  });

  test('should calculate age correctly', () => {
    const birthDate = new Date(1990, 0, 1);
    const age = dateUtils.getAge(birthDate);
    expect(age).toBeGreaterThan(30);
  });
});

describe('Date Utils - Validation and Parsing', () => {
  test('should validate valid dates', () => {
    const validDate = new Date(2024, 0, 15);
    expect(dateUtils.isValidDate(validDate)).toBe(true);
  });

  test('should invalidate invalid dates', () => {
    const invalidDate = new Date('invalid');
    expect(dateUtils.isValidDate(invalidDate)).toBe(false);
  });

  test('should parse ISO string correctly', () => {
    const isoString = '2024-01-15T10:30:00.000Z';
    const parsed = dateUtils.parseISOString(isoString);
    expect(parsed).toBeInstanceOf(Date);
  });

  test('should return null for invalid ISO string', () => {
    const invalidIso = 'invalid-date';
    const parsed = dateUtils.parseISOString(invalidIso);
    expect(parsed).toBeNull();
  });
});