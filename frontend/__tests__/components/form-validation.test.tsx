/**
 * Form Validation Test
 * Tests form validation logic and error handling
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

describe('Form Validation', () => {
  it('should validate required email field', async () => {
    const EmailValidationForm: React.FC = () => {
      const [email, setEmail] = React.useState('');
      const [errors, setErrors] = React.useState<{ email?: string }>({});
      
      const validateEmail = (value: string) => {
        if (!value.trim()) {
          return 'Email is required';
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
          return 'Please enter a valid email address';
        }
        return '';
      };
      
      const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        console.log('Submitting with email state:', email);
        const emailError = validateEmail(email);
        console.log('Validation result:', emailError);
        
        if (emailError) {
          setErrors({ email: emailError });
          return;
        }
        
        setErrors({});
      };
      
      const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        console.log('Email onChange called with:', e.target.value);
        setEmail(e.target.value);
      };
      
      return (
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            value={email}
            onChange={handleEmailChange}
            data-testid="email-input"
            placeholder="Enter email"
          />
          {errors.email && (
            <div data-testid="email-error" role="alert">
              {errors.email}
            </div>
          )}
          <button type="submit" data-testid="submit-button">
            Submit
          </button>
        </form>
      );
    };

    const user = userEvent.setup();
    render(<EmailValidationForm />);
    
    // Test empty email validation
    await user.click(screen.getByTestId('submit-button'));
    
    await waitFor(() => {
      expect(screen.getByTestId('email-error')).toHaveTextContent('Email is required');
    });
    
    // Clear error first, then test invalid email validation  
    const emailInput = screen.getByTestId('email-input');
    
    // Use userEvent for proper React state updates
    await user.clear(emailInput);
    await user.type(emailInput, 'invalid-email');
    
    // Wait for the DOM to reflect the change  
    await waitFor(() => {
      expect(emailInput).toHaveValue('invalid-email');
    });
    
    await user.click(screen.getByTestId('submit-button'));
    
    // Debug: check what the error shows after submit
    await waitFor(() => {
      const errorElement = screen.getByTestId('email-error');
      console.log('Email error after submit:', errorElement.textContent);
      console.log('Email input value after submit:', (emailInput as HTMLInputElement).value);
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('email-error')).toHaveTextContent('Please enter a valid email address');
    });
  });

  it('should validate password strength', async () => {
    const PasswordValidationForm: React.FC = () => {
      const [password, setPassword] = React.useState('');
      const [errors, setErrors] = React.useState<{ password?: string }>({});
      
      const validatePassword = (value: string) => {
        if (!value) {
          return 'Password is required';
        }
        if (value.length < 8) {
          return 'Password must be at least 8 characters';
        }
        if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(value)) {
          return 'Password must contain uppercase, lowercase, and number';
        }
        return '';
      };
      
      const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        console.log('Submitting with password state:', password);
        const passwordError = validatePassword(password);
        console.log('Password validation result:', passwordError);
        
        if (passwordError) {
          setErrors({ password: passwordError });
          return;
        }
        
        setErrors({});
      };
      
      const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        console.log('Password onChange called with:', e.target.value);
        setPassword(e.target.value);
      };
      
      return (
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={password}
            onChange={handlePasswordChange}
            data-testid="password-input"
            placeholder="Enter password"
          />
          {errors.password && (
            <div data-testid="password-error" role="alert">
              {errors.password}
            </div>
          )}
          <button type="submit" data-testid="submit-button">
            Submit
          </button>
        </form>
      );
    };

    const user = userEvent.setup();
    render(<PasswordValidationForm />);
    
    // Test weak password
    const passwordInput = screen.getByTestId('password-input');
    fireEvent.change(passwordInput, { target: { value: 'weak' } });
    
    // Debug: log the current value
    console.log('Password input value:', (passwordInput as HTMLInputElement).value);
    
    await user.click(screen.getByTestId('submit-button'));
    
    await waitFor(() => {
      expect(screen.getByTestId('password-error')).toHaveTextContent('Password must be at least 8 characters');
    });
  });

  it('should validate form with multiple fields', async () => {
    const MultiFieldForm: React.FC = () => {
      const [formData, setFormData] = React.useState({
        name: '',
        email: '',
        age: ''
      });
      const [errors, setErrors] = React.useState<Record<string, string>>({});
      
      const validateForm = () => {
        const newErrors: Record<string, string> = {};
        
        if (!formData.name.trim()) {
          newErrors.name = 'Name is required';
        }
        
        if (!formData.email.trim()) {
          newErrors.email = 'Email is required';
        }
        
        const ageNum = parseInt(formData.age);
        if (!formData.age || isNaN(ageNum) || ageNum < 0 || ageNum > 120) {
          newErrors.age = 'Please enter a valid age (0-120)';
        }
        
        return newErrors;
      };
      
      const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const validationErrors = validateForm();
        setErrors(validationErrors);
      };
      
      return (
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
            data-testid="name-input"
            placeholder="Name"
          />
          {errors.name && <div data-testid="name-error">{errors.name}</div>}
          
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
            data-testid="email-input"
            placeholder="Email"
          />
          {errors.email && <div data-testid="email-error">{errors.email}</div>}
          
          <input
            type="number"
            value={formData.age}
            onChange={(e) => setFormData(prev => ({ ...prev, age: e.target.value }))}
            data-testid="age-input"
            placeholder="Age"
          />
          {errors.age && <div data-testid="age-error">{errors.age}</div>}
          
          <button type="submit" data-testid="submit-button">
            Submit
          </button>
        </form>
      );
    };

    const user = userEvent.setup();
    render(<MultiFieldForm />);
    
    // Test all field validation
    await user.click(screen.getByTestId('submit-button'));
    
    await waitFor(() => {
      expect(screen.getByTestId('name-error')).toHaveTextContent('Name is required');
      expect(screen.getByTestId('email-error')).toHaveTextContent('Email is required');
      expect(screen.getByTestId('age-error')).toHaveTextContent('Please enter a valid age (0-120)');
    });
  });
});