/**
 * Forms Groups Dynamic Accessibility Test Suite
 * Tests dynamic form sections, conditional forms, and focus management
 * Extracted from oversized forms-groups.a11y.test.tsx for modularity
 * 
 * Business Value Justification (BVJ):
 * - Segment: Growth & Enterprise  
 * - Goal: Ensure dynamic form accessibility for advanced features
 * - Value Impact: Enables complex workflows for power users
 * - Revenue Impact: +$15K MRR from advanced form capabilities
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
  setupKeyboardTest,
  testFocusRestoration
} from './shared-a11y-helpers';

describe('Form Groups - Dynamic Form Sections', () => {
  it('manages focus in dynamic form sections', async () => {
    const user = setupKeyboardTest();
    const DynamicForm = () => {
      const [showAddress, setShowAddress] = React.useState(false);
      const addressFieldRef = React.useRef<HTMLInputElement>(null);
      
      React.useEffect(() => {
        if (showAddress && addressFieldRef.current) {
          addressFieldRef.current.focus();
        }
      }, [showAddress]);
      
      return (
        <form>
          <div>
            <input 
              type="checkbox" 
              id="needs-address"
              checked={showAddress}
              onChange={(e) => setShowAddress(e.target.checked)}
            />
            <Label htmlFor="needs-address">Different billing address</Label>
          </div>
          
          {showAddress && (
            <div>
              <Label htmlFor="billing-address">Billing Address</Label>
              <Input 
                ref={addressFieldRef}
                id="billing-address" 
                type="text"
              />
            </div>
          )}
        </form>
      );
    };
    
    render(<DynamicForm />);
    await user.click(screen.getByLabelText('Different billing address'));
    
    await waitFor(() => {
      expect(screen.getByLabelText('Billing Address')).toHaveFocus();
    });
  });

  it('supports conditional form sections', async () => {
    const user = setupKeyboardTest();
    const ConditionalForm = () => {
      const [userType, setUserType] = React.useState('');
      
      return (
        <form>
          <fieldset>
            <legend>User Type Selection</legend>
            <div>
              <input 
                type="radio" 
                id="user-individual" 
                name="userType" 
                value="individual"
                onChange={(e) => setUserType(e.target.value)}
              />
              <Label htmlFor="user-individual">Individual</Label>
            </div>
            <div>
              <input 
                type="radio" 
                id="user-business" 
                name="userType" 
                value="business"
                onChange={(e) => setUserType(e.target.value)}
              />
              <Label htmlFor="user-business">Business</Label>
            </div>
          </fieldset>
          
          {userType === 'individual' && (
            <fieldset>
              <legend>Personal Information</legend>
              <div>
                <Label htmlFor="personal-ssn">Social Security Number</Label>
                <Input id="personal-ssn" type="text" />
              </div>
              <div>
                <Label htmlFor="personal-dob">Date of Birth</Label>
                <Input id="personal-dob" type="date" />
              </div>
            </fieldset>
          )}
          
          {userType === 'business' && (
            <fieldset>
              <legend>Business Information</legend>
              <div>
                <Label htmlFor="business-ein">EIN</Label>
                <Input id="business-ein" type="text" />
              </div>
              <div>
                <Label htmlFor="business-name">Business Name</Label>
                <Input id="business-name" type="text" />
              </div>
            </fieldset>
          )}
        </form>
      );
    };
    
    const { container } = render(<ConditionalForm />);
    
    // Select individual option
    await user.click(screen.getByLabelText('Individual'));
    
    await waitFor(() => {
      expect(screen.getByLabelText('Social Security Number')).toBeInTheDocument();
      expect(screen.getByLabelText('Date of Birth')).toBeInTheDocument();
    });
    
    // Select business option
    await user.click(screen.getByLabelText('Business'));
    
    await waitFor(() => {
      expect(screen.getByLabelText('EIN')).toBeInTheDocument();
      expect(screen.getByLabelText('Business Name')).toBeInTheDocument();
      expect(screen.queryByLabelText('Social Security Number')).not.toBeInTheDocument();
    });
    
    await runAxeTest(container);
  });

  it('handles progressive disclosure with proper announcements', async () => {
    const user = setupKeyboardTest();
    const ProgressiveForm = () => {
      const [showAdvanced, setShowAdvanced] = React.useState(false);
      const [announceText, setAnnounceText] = React.useState('');
      
      const toggleAdvanced = () => {
        setShowAdvanced(!showAdvanced);
        setAnnounceText(showAdvanced ? 'Advanced options hidden' : 'Advanced options shown');
      };
      
      return (
        <form>
          <fieldset>
            <legend>Basic Settings</legend>
            <div>
              <Label htmlFor="basic-name">Name</Label>
              <Input id="basic-name" type="text" />
            </div>
            <div>
              <Label htmlFor="basic-email">Email</Label>
              <Input id="basic-email" type="email" />
            </div>
          </fieldset>
          
          <Button 
            type="button" 
            onClick={toggleAdvanced}
            aria-expanded={showAdvanced}
            aria-controls="advanced-options"
          >
            {showAdvanced ? 'Hide' : 'Show'} Advanced Options
          </Button>
          
          <div 
            id="advanced-options" 
            style={{ display: showAdvanced ? 'block' : 'none' }}
          >
            <fieldset>
              <legend>Advanced Settings</legend>
              <div>
                <Label htmlFor="advanced-timezone">Timezone</Label>
                <select id="advanced-timezone">
                  <option value="">Select timezone</option>
                  <option value="EST">Eastern</option>
                  <option value="PST">Pacific</option>
                </select>
              </div>
              <div>
                <Label htmlFor="advanced-theme">Theme</Label>
                <select id="advanced-theme">
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                </select>
              </div>
            </fieldset>
          </div>
          
          <div aria-live="polite" aria-atomic="true" className="sr-only">
            {announceText}
          </div>
        </form>
      );
    };
    
    const { container } = render(<ProgressiveForm />);
    
    const toggleButton = screen.getByRole('button', { name: 'Show Advanced Options' });
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
    
    await user.click(toggleButton);
    
    await waitFor(() => {
      expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
      expect(screen.getByLabelText('Timezone')).toBeInTheDocument();
      expect(screen.getByLabelText('Theme')).toBeInTheDocument();
    });
    
    await runAxeTest(container);
  });

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
});