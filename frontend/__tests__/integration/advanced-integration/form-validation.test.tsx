/**
 * Complex Form Validation Integration Tests
 * Tests for multi-step forms, dependencies, and async validation
 */

import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react';
import { createTestSetup, waitForAnimation } from './setup';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

describe('Complex Form Validation Integration', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  it('should validate multi-step forms with dependencies', async () => {
    const FormComponent = () => {
      const [step, setStep] = React.useState(1);
      const [formData, setFormData] = React.useState({
        model: '',
        temperature: 0.7,
        maxTokens: 1000
      });
      const [errors, setErrors] = React.useState<Record<string, string>>({});
      
      const validateStep = (currentStep: number) => {
        const newErrors: Record<string, string> = {};
        
        if (currentStep === 1 && !formData.model) {
          newErrors.model = 'Model is required';
        }
        
        if (currentStep === 2) {
          if (formData.temperature < 0 || formData.temperature > 2) {
            newErrors.temperature = 'Temperature must be between 0 and 2';
          }
          if (formData.maxTokens < 1 || formData.maxTokens > 4000) {
            newErrors.maxTokens = 'Max tokens must be between 1 and 4000';
          }
        }
        
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
      };
      
      const handleNext = () => {
        if (validateStep(step)) {
          setStep(step + 1);
        }
      };
      
      return (
        <div>
          <div data-testid="step">{step}</div>
          {step === 1 && (
            <div>
              <input
                data-testid="model-input"
                value={formData.model}
                onChange={(e) => setFormData({ ...formData, model: e.target.value })}
              />
              {errors.model && <div data-testid="model-error">{errors.model}</div>}
            </div>
          )}
          {step === 2 && (
            <div>
              <input
                data-testid="temperature-input"
                type="number"
                value={formData.temperature}
                onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
              />
              {errors.temperature && <div data-testid="temperature-error">{errors.temperature}</div>}
            </div>
          )}
          <button onClick={handleNext}>Next</button>
        </div>
      );
    };
    
    const { getByTestId, getByText } = render(<FormComponent />);
    
    // Try to proceed without required field
    fireEvent.click(getByText('Next'));
    
    await waitFor(() => {
      expect(getByTestId('model-error')).toHaveTextContent('Model is required');
    });
    
    // Fill required field
    fireEvent.change(getByTestId('model-input'), { target: { value: 'gemini-2.5-flash' } });
    fireEvent.click(getByText('Next'));
    
    await waitFor(() => {
      expect(getByTestId('step')).toHaveTextContent('2');
    });
  });

  it('should handle async validation with debouncing', async () => {
    let validationCount = 0;
    
    const AsyncValidationComponent = () => {
      const [email, setEmail] = React.useState('');
      const [isValidating, setIsValidating] = React.useState(false);
      const [error, setError] = React.useState('');
      
      const validateEmail = React.useCallback(async (value: string) => {
        validationCount++;
        
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 100));
        
        await act(async () => {
          setIsValidating(true);
          
          if (!value.includes('@')) {
            setError('Invalid email');
          } else {
            setError('');
          }
          
          setIsValidating(false);
        });
      }, []);
      
      // Debounce validation
      React.useEffect(() => {
        const timer = setTimeout(() => {
          if (email) validateEmail(email);
        }, 300);
        
        return () => clearTimeout(timer);
      }, [email, validateEmail]);
      
      return (
        <div>
          <input
            data-testid="email-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          {isValidating && <div>Validating...</div>}
          {error && <div data-testid="error">{error}</div>}
        </div>
      );
    };
    
    const { getByTestId } = render(<AsyncValidationComponent />);
    
    // Type quickly
    const input = getByTestId('email-input');
    fireEvent.change(input, { target: { value: 't' } });
    fireEvent.change(input, { target: { value: 'te' } });
    fireEvent.change(input, { target: { value: 'test' } });
    
    // Wait for debounce
    await new Promise(resolve => setTimeout(resolve, 400));
    
    // Should only validate once due to debouncing
    expect(validationCount).toBe(1);
    
    await waitFor(() => {
      expect(getByTestId('error')).toHaveTextContent('Invalid email');
    });
  });

  it('should handle conditional field validation', async () => {
    const ConditionalForm = () => {
      const [formType, setFormType] = React.useState('basic');
      const [fields, setFields] = React.useState({
        name: '',
        email: '',
        advanced: ''
      });
      const [errors, setErrors] = React.useState<Record<string, string>>({});
      
      const validate = () => {
        const newErrors: Record<string, string> = {};
        
        if (!fields.name) newErrors.name = 'Name is required';
        if (!fields.email) newErrors.email = 'Email is required';
        
        if (formType === 'advanced' && !fields.advanced) {
          newErrors.advanced = 'Advanced field is required';
        }
        
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
      };
      
      return (
        <div>
          <select
            data-testid="form-type"
            value={formType}
            onChange={(e) => setFormType(e.target.value)}
          >
            <option value="basic">Basic</option>
            <option value="advanced">Advanced</option>
          </select>
          
          <input
            data-testid="name-input"
            value={fields.name}
            onChange={(e) => setFields({ ...fields, name: e.target.value })}
          />
          {errors.name && <div data-testid="name-error">{errors.name}</div>}
          
          <input
            data-testid="email-input"
            value={fields.email}
            onChange={(e) => setFields({ ...fields, email: e.target.value })}
          />
          {errors.email && <div data-testid="email-error">{errors.email}</div>}
          
          {formType === 'advanced' && (
            <div>
              <input
                data-testid="advanced-input"
                value={fields.advanced}
                onChange={(e) => setFields({ ...fields, advanced: e.target.value })}
              />
              {errors.advanced && <div data-testid="advanced-error">{errors.advanced}</div>}
            </div>
          )}
          
          <button onClick={validate}>Validate</button>
        </div>
      );
    };
    
    const { getByTestId, getByText } = render(<ConditionalForm />);
    
    // Switch to advanced mode
    fireEvent.change(getByTestId('form-type'), { target: { value: 'advanced' } });
    
    // Try to validate without filling advanced field
    fireEvent.click(getByText('Validate'));
    
    await waitFor(() => {
      expect(getByTestId('advanced-error')).toHaveTextContent('Advanced field is required');
    });
  });

  it('should validate forms with file uploads', async () => {
    const FileUploadForm = () => {
      const [file, setFile] = React.useState<File | null>(null);
      const [error, setError] = React.useState('');
      
      const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        
        if (selectedFile) {
          // Validate file type and size
          if (selectedFile.size > 1024 * 1024) {
            setError('File too large');
            return;
          }
          
          if (!selectedFile.type.startsWith('image/')) {
            setError('Must be an image file');
            return;
          }
          
          setError('');
          setFile(selectedFile);
        }
      };
      
      return (
        <div>
          <input
            data-testid="file-input"
            type="file"
            onChange={handleFileChange}
          />
          {error && <div data-testid="file-error">{error}</div>}
          {file && <div data-testid="file-name">{file.name}</div>}
        </div>
      );
    };
    
    const { getByTestId } = render(<FileUploadForm />);
    
    const largeFile = new File(['x'.repeat(2 * 1024 * 1024)], 'large.txt', { type: 'text/plain' });
    const input = getByTestId('file-input') as HTMLInputElement;
    
    Object.defineProperty(input, 'files', {
      value: [largeFile],
      writable: false
    });
    
    fireEvent.change(input);
    
    await waitFor(() => {
      expect(getByTestId('file-error')).toHaveTextContent('File too large');
    });
  });
});