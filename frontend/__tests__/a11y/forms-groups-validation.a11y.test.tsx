/**
 * Forms Groups Validation Accessibility Test Suite
 * Tests dynamic validation, collapsible sections, and field-specific features
 * Extracted from oversized forms-groups-dynamic.a11y.test.tsx for modularity
 * 
 * Business Value Justification (BVJ):
 * - Segment: Growth & Enterprise  
 * - Goal: Ensure accessible validation and interaction patterns
 * - Value Impact: Enables complex form workflows with validation
 * - Revenue Impact: +$8K MRR from accessible validation features
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Import form components
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

// Import shared accessibility helpers
import { 
  runAxeTest, 
  setupKeyboardTest
} from './shared-a11y-helpers';

describe('Form Groups - Validation and Interactive Features', () => {
  it('manages focus in collapsible form sections', async () => {
    const user = setupKeyboardTest();
    const CollapsibleForm = () => {
      const [openSections, setOpenSections] = React.useState<Record<string, boolean>>({});
      
      const toggleSection = (sectionId: string) => {
        setOpenSections(prev => ({
          ...prev,
          [sectionId]: !prev[sectionId]
        }));
      };
      
      return (
        <form>
          <div>
            <Button 
              type="button"
              onClick={() => toggleSection('personal')}
              aria-expanded={openSections.personal || false}
              aria-controls="personal-section"
            >
              Personal Information
            </Button>
            
            {openSections.personal && (
              <div id="personal-section">
                <div>
                  <Label htmlFor="coll-first-name">First Name</Label>
                  <Input id="coll-first-name" type="text" />
                </div>
                <div>
                  <Label htmlFor="coll-last-name">Last Name</Label>
                  <Input id="coll-last-name" type="text" />
                </div>
              </div>
            )}
          </div>
          
          <div>
            <Button 
              type="button"
              onClick={() => toggleSection('contact')}
              aria-expanded={openSections.contact || false}
              aria-controls="contact-section"
            >
              Contact Information
            </Button>
            
            {openSections.contact && (
              <div id="contact-section">
                <div>
                  <Label htmlFor="coll-email">Email</Label>
                  <Input id="coll-email" type="email" />
                </div>
                <div>
                  <Label htmlFor="coll-phone">Phone</Label>
                  <Input id="coll-phone" type="tel" />
                </div>
              </div>
            )}
          </div>
        </form>
      );
    };
    
    const { container } = render(<CollapsibleForm />);
    
    const personalButton = screen.getByRole('button', { name: 'Personal Information' });
    const contactButton = screen.getByRole('button', { name: 'Contact Information' });
    
    // Open personal section
    await user.click(personalButton);
    
    await waitFor(() => {
      expect(personalButton).toHaveAttribute('aria-expanded', 'true');
      expect(screen.getByLabelText('First Name')).toBeInTheDocument();
    });
    
    // Open contact section
    await user.click(contactButton);
    
    await waitFor(() => {
      expect(contactButton).toHaveAttribute('aria-expanded', 'true');
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });
    
    await runAxeTest(container);
  });

  it('handles dynamic field validation', async () => {
    const user = setupKeyboardTest();
    const DynamicValidationForm = () => {
      const [fieldType, setFieldType] = React.useState('text');
      const [value, setValue] = React.useState('');
      const [error, setError] = React.useState('');
      
      const validateField = (val: string, type: string) => {
        if (type === 'email' && val && !val.includes('@')) {
          setError('Please enter a valid email address');
        } else if (type === 'number' && val && isNaN(Number(val))) {
          setError('Please enter a valid number');
        } else {
          setError('');
        }
      };
      
      React.useEffect(() => {
        validateField(value, fieldType);
      }, [value, fieldType]);
      
      return (
        <form>
          <fieldset>
            <legend>Dynamic Field Type</legend>
            <div>
              <Label htmlFor="field-type">Field Type</Label>
              <select 
                id="field-type" 
                value={fieldType} 
                onChange={(e) => setFieldType(e.target.value)}
              >
                <option value="text">Text</option>
                <option value="email">Email</option>
                <option value="number">Number</option>
              </select>
            </div>
            
            <div>
              <Label htmlFor="dynamic-field">Value</Label>
              <Input 
                id="dynamic-field"
                type={fieldType}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                aria-describedby={error ? 'field-error' : undefined}
                aria-invalid={!!error}
              />
              {error && (
                <div id="field-error" role="alert" aria-live="polite">
                  {error}
                </div>
              )}
            </div>
          </fieldset>
        </form>
      );
    };
    
    const { container } = render(<DynamicValidationForm />);
    
    // Change to email type
    await user.selectOptions(screen.getByLabelText('Field Type'), 'email');
    
    // Enter invalid email
    await user.type(screen.getByLabelText('Value'), 'invalid-email');
    
    await waitFor(() => {
      expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument();
    });
    
    const valueInput = screen.getByLabelText('Value');
    expect(valueInput).toHaveAttribute('aria-invalid', 'true');
    expect(valueInput).toHaveAttribute('aria-describedby', 'field-error');
    
    await runAxeTest(container);
  });

  it('handles real-time validation feedback', async () => {
    const user = setupKeyboardTest();
    const RealtimeValidationForm = () => {
      const [password, setPassword] = React.useState('');
      const [confirmPassword, setConfirmPassword] = React.useState('');
      const [errors, setErrors] = React.useState<Record<string, string>>({});
      
      React.useEffect(() => {
        const newErrors: Record<string, string> = {};
        
        if (password && password.length < 8) {
          newErrors.password = 'Password must be at least 8 characters';
        }
        
        if (confirmPassword && password !== confirmPassword) {
          newErrors.confirmPassword = 'Passwords do not match';
        }
        
        setErrors(newErrors);
      }, [password, confirmPassword]);
      
      return (
        <form>
          <fieldset>
            <legend>Set Password</legend>
            <div>
              <Label htmlFor="val-password">Password</Label>
              <Input 
                id="val-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-describedby={errors.password ? 'password-error' : 'password-help'}
                aria-invalid={!!errors.password}
              />
              <div id="password-help">Must be at least 8 characters</div>
              {errors.password && (
                <div id="password-error" role="alert" aria-live="polite">
                  {errors.password}
                </div>
              )}
            </div>
            
            <div>
              <Label htmlFor="val-confirm-password">Confirm Password</Label>
              <Input 
                id="val-confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                aria-describedby={errors.confirmPassword ? 'confirm-password-error' : undefined}
                aria-invalid={!!errors.confirmPassword}
              />
              {errors.confirmPassword && (
                <div id="confirm-password-error" role="alert" aria-live="polite">
                  {errors.confirmPassword}
                </div>
              )}
            </div>
          </fieldset>
        </form>
      );
    };
    
    const { container } = render(<RealtimeValidationForm />);
    
    // Enter short password
    await user.type(screen.getByLabelText('Password'), 'short');
    
    await waitFor(() => {
      expect(screen.getByText('Password must be at least 8 characters')).toBeInTheDocument();
    });
    
    // Enter mismatched confirmation
    await user.type(screen.getByLabelText('Confirm Password'), 'different');
    
    await waitFor(() => {
      expect(screen.getByText('Passwords do not match')).toBeInTheDocument();
    });
    
    await runAxeTest(container);
  });

});