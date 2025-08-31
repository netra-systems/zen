/**
 * Data Transformation Utility Test
 * Tests data transformation and formatting utilities
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

describe('Data Transformation Utilities', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  it('should format dates correctly', () => {
    const DateFormattingComponent: React.FC = () => {
      const formatDate = (date: Date | string | number): string => {
        try {
          let dateObj: Date;
          
          if (typeof date === 'string') {
            dateObj = new Date(date);
          } else if (typeof date === 'number') {
            dateObj = new Date(date);
          } else {
            dateObj = date;
          }
          
          if (isNaN(dateObj.getTime())) {
            return 'Invalid Date';
          }
          
          return dateObj.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
          });
        } catch {
          return 'Invalid Date';
        }
      };
      
      const testDates = [
        new Date('2023-12-25T12:00:00Z'), // Use explicit UTC time to avoid timezone issues
        '2023-06-15T10:30:00Z',
        1640995200000, // Unix timestamp
        'invalid-date'
      ];
      
      return (
        <div>
          {testDates.map((date, index) => (
            <div key={index} data-testid={`formatted-date-${index}`}>
              {formatDate(date)}
            </div>
          ))}
        </div>
      );
    };

    render(<DateFormattingComponent />);
    
    expect(screen.getByTestId('formatted-date-0')).toHaveTextContent('Dec 25, 2023');
    expect(screen.getByTestId('formatted-date-1')).toHaveTextContent('Jun 15, 2023');
    expect(screen.getByTestId('formatted-date-2')).toHaveTextContent('Dec 31, 2021');
    expect(screen.getByTestId('formatted-date-3')).toHaveTextContent('Invalid Date');
  });

  it('should transform array data structures', () => {
    const ArrayTransformComponent: React.FC = () => {
      const rawData = [
        { id: 1, name: 'Alice', age: 30, department: 'Engineering' },
        { id: 2, name: 'Bob', age: 25, department: 'Design' },
        { id: 3, name: 'Charlie', age: 35, department: 'Engineering' }
      ];
      
      // Group by department
      const groupByDepartment = (data: typeof rawData) => {
        return data.reduce((acc, person) => {
          const dept = person.department;
          if (!acc[dept]) {
            acc[dept] = [];
          }
          acc[dept].push(person);
          return acc;
        }, {} as Record<string, typeof rawData>);
      };
      
      // Calculate average age
      const calculateAverageAge = (data: typeof rawData) => {
        const total = data.reduce((sum, person) => sum + person.age, 0);
        return Math.round(total / data.length);
      };
      
      const groupedData = groupByDepartment(rawData);
      const averageAge = calculateAverageAge(rawData);
      
      return (
        <div>
          <div data-testid="average-age">Average Age: {averageAge}</div>
          
          {Object.entries(groupedData).map(([department, people]) => (
            <div key={department} data-testid={`department-${department.toLowerCase()}`}>
              <h3>{department}: {people.length} people</h3>
              {people.map(person => (
                <div key={person.id} data-testid={`person-${person.id}`}>
                  {person.name} ({person.age})
                </div>
              ))}
            </div>
          ))}
        </div>
      );
    };

    render(<ArrayTransformComponent />);
    
    expect(screen.getByTestId('average-age')).toHaveTextContent('Average Age: 30');
    expect(screen.getByTestId('department-engineering')).toHaveTextContent('Engineering: 2 people');
    expect(screen.getByTestId('department-design')).toHaveTextContent('Design: 1 people');
    expect(screen.getByTestId('person-1')).toHaveTextContent('Alice (30)');
  });

  it('should sanitize and validate input data', () => {
    const DataSanitizationComponent: React.FC = () => {
      const sanitizeHTML = (input: string): string => {
        return input
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#x27;')
          .replace(/\//g, '&#x2F;');
      };
      
      const validateEmail = (email: string): boolean => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
      };
      
      const validatePhoneNumber = (phone: string): boolean => {
        const phoneRegex = /^\+?[\d\s\-\(\)]+$/;
        return phoneRegex.test(phone.trim()) && phone.replace(/\D/g, '').length >= 10;
      };
      
      const testInputs = [
        { type: 'html', value: '<script>alert("xss")</script>Hello' },
        { type: 'email', value: 'user@example.com' },
        { type: 'email', value: 'invalid-email' },
        { type: 'phone', value: '+1 (555) 123-4567' },
        { type: 'phone', value: '123' }
      ];
      
      return (
        <div>
          {testInputs.map((input, index) => (
            <div key={index} data-testid={`validation-${index}`}>
              {input.type === 'html' && (
                <span>Sanitized: {sanitizeHTML(input.value)}</span>
              )}
              {input.type === 'email' && (
                <span>Email valid: {validateEmail(input.value) ? 'true' : 'false'}</span>
              )}
              {input.type === 'phone' && (
                <span>Phone valid: {validatePhoneNumber(input.value) ? 'true' : 'false'}</span>
              )}
            </div>
          ))}
        </div>
      );
    };

    render(<DataSanitizationComponent />);
    
    expect(screen.getByTestId('validation-0')).toHaveTextContent('Sanitized: &lt;script&gt;alert(&quot;xss&quot;)&lt;&#x2F;script&gt;Hello');
    expect(screen.getByTestId('validation-1')).toHaveTextContent('Email valid: true');
    expect(screen.getByTestId('validation-2')).toHaveTextContent('Email valid: false');
    expect(screen.getByTestId('validation-3')).toHaveTextContent('Phone valid: true');
    expect(screen.getByTestId('validation-4')).toHaveTextContent('Phone valid: false');
  });

  it('should handle currency and number formatting', () => {
    const NumberFormattingComponent: React.FC = () => {
      const formatCurrency = (amount: number, currency: string = 'USD'): string => {
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: currency
        }).format(amount);
      };
      
      const formatPercentage = (value: number): string => {
        return new Intl.NumberFormat('en-US', {
          style: 'percent',
          minimumFractionDigits: 1,
          maximumFractionDigits: 1
        }).format(value);
      };
      
      const formatNumber = (num: number): string => {
        return new Intl.NumberFormat('en-US').format(num);
      };
      
      const testNumbers = [
        { value: 1234.56, type: 'currency' },
        { value: 0.1234, type: 'percentage' },
        { value: 1234567, type: 'number' }
      ];
      
      return (
        <div>
          {testNumbers.map((item, index) => (
            <div key={index} data-testid={`formatted-${item.type}-${index}`}>
              {item.type === 'currency' && formatCurrency(item.value)}
              {item.type === 'percentage' && formatPercentage(item.value)}
              {item.type === 'number' && formatNumber(item.value)}
            </div>
          ))}
        </div>
      );
    };

    render(<NumberFormattingComponent />);
    
    expect(screen.getByTestId('formatted-currency-0')).toHaveTextContent('$1,234.56');
    expect(screen.getByTestId('formatted-percentage-1')).toHaveTextContent('12.3%');
    expect(screen.getByTestId('formatted-number-2')).toHaveTextContent('1,234,567');
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});