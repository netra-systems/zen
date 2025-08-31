import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
r modularity
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
    jest.setTimeout(10000);
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

});