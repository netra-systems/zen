import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
r modularity
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free → Enterprise)
 * - Goal: Ensure basic form accessibility for compliance
 * - Value Impact: Enables users with disabilities to complete basic forms
 * - Revenue Impact: +$10K MRR from accessible form completion
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
  createFieldsetTest
} from './shared-a11y-helpers';

describe('Form Groups - Basic Form Structures', () => {
    jest.setTimeout(10000);
  it('passes axe tests for complex form with multiple groups', async () => {
    const { container } = render(
      <form>
        <fieldset>
          <legend>Personal Information</legend>
          <div>
            <Label htmlFor="first-name">First Name</Label>
            <Input id="first-name" type="text" required />
          </div>
          <div>
            <Label htmlFor="last-name">Last Name</Label>
            <Input id="last-name" type="text" required />
          </div>
        </fieldset>
        
        <fieldset>
          <legend>Contact Details</legend>
          <div>
            <Label htmlFor="contact-email">Email</Label>
            <Input id="contact-email" type="email" required />
          </div>
          <div>
            <Label htmlFor="contact-phone">Phone</Label>
            <Input id="contact-phone" type="tel" />
          </div>
        </fieldset>
        
        <Button type="submit">Submit Application</Button>
      </form>
    );
    await runAxeTest(container);
  });

  it('supports radio button groups with proper keyboard navigation', async () => {
    const user = setupKeyboardTest();
    render(
      <fieldset>
        <legend>Preferred Contact Method</legend>
        <div>
          <input type="radio" id="contact-email-radio" name="contact" value="email" />
          <Label htmlFor="contact-email-radio">Email</Label>
        </div>
        <div>
          <input type="radio" id="contact-phone-radio" name="contact" value="phone" />
          <Label htmlFor="contact-phone-radio">Phone</Label>
        </div>
        <div>
          <input type="radio" id="contact-mail-radio" name="contact" value="mail" />
          <Label htmlFor="contact-mail-radio">Mail</Label>
        </div>
      </fieldset>
    );
    
    const emailRadio = screen.getByLabelText('Email');
    await user.tab();
    expect(emailRadio).toHaveFocus();
    
    await user.keyboard('{ArrowDown}');
    expect(screen.getByLabelText('Phone')).toHaveFocus();
  });

  it('handles nested fieldsets with proper structure', async () => {
    const { container } = render(
      <form>
        <fieldset>
          <legend>Shipping Information</legend>
          <fieldset>
            <legend>Recipient Details</legend>
            <div>
              <Label htmlFor="recipient-name">Full Name</Label>
              <Input id="recipient-name" type="text" required />
            </div>
            <div>
              <Label htmlFor="recipient-company">Company</Label>
              <Input id="recipient-company" type="text" />
            </div>
          </fieldset>
          
          <fieldset>
            <legend>Delivery Address</legend>
            <div>
              <Label htmlFor="delivery-street">Street Address</Label>
              <Input id="delivery-street" type="text" required />
            </div>
            <div>
              <Label htmlFor="delivery-city">City</Label>
              <Input id="delivery-city" type="text" required />
            </div>
            <div>
              <Label htmlFor="delivery-zip">ZIP Code</Label>
              <Input id="delivery-zip" type="text" required />
            </div>
          </fieldset>
        </fieldset>
        
        <Button type="submit">Process Shipping</Button>
      </form>
    );
    
    await runAxeTest(container);
    
    // Verify proper heading hierarchy
    const shippingLegend = screen.getByText('Shipping Information');
    const recipientLegend = screen.getByText('Recipient Details');
    const addressLegend = screen.getByText('Delivery Address');
    
    expect(shippingLegend).toBeInTheDocument();
    expect(recipientLegend).toBeInTheDocument();
    expect(addressLegend).toBeInTheDocument();
  });

  it('provides proper labeling for checkbox groups', async () => {
    const { container } = render(
      <fieldset>
        <legend>Newsletter Preferences</legend>
        <div>
          <input type="checkbox" id="newsletter-tech" name="newsletters" value="tech" />
          <Label htmlFor="newsletter-tech">Technology Updates</Label>
        </div>
        <div>
          <input type="checkbox" id="newsletter-marketing" name="newsletters" value="marketing" />
          <Label htmlFor="newsletter-marketing">Marketing Offers</Label>
        </div>
        <div>
          <input type="checkbox" id="newsletter-events" name="newsletters" value="events" />
          <Label htmlFor="newsletter-events">Event Notifications</Label>
        </div>
      </fieldset>
    );
    
    await runAxeTest(container);
    
    // Verify all checkboxes are properly labeled
    expect(screen.getByLabelText('Technology Updates')).toBeInTheDocument();
    expect(screen.getByLabelText('Marketing Offers')).toBeInTheDocument();
    expect(screen.getByLabelText('Event Notifications')).toBeInTheDocument();
  });

  it('handles form validation with proper error associations', async () => {
    const FormWithValidation = () => {
      const [errors, setErrors] = React.useState<Record<string, string>>({});
      
      const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const formData = new FormData(e.target as HTMLFormElement);
        const newErrors: Record<string, string> = {};
        
        if (!formData.get('username')) {
          newErrors.username = 'Username is required';
        }
        if (!formData.get('password')) {
          newErrors.password = 'Password is required';
        }
        
        setErrors(newErrors);
      };
      
      return (
        <form onSubmit={handleSubmit}>
          <fieldset>
            <legend>Login Credentials</legend>
            <div>
              <Label htmlFor="login-username">Username</Label>
              <Input 
                id="login-username" 
                name="username"
                type="text" 
                aria-describedby={errors.username ? 'username-error' : undefined}
                aria-invalid={!!errors.username}
              />
              {errors.username && (
                <div id="username-error" role="alert" aria-live="polite">
                  {errors.username}
                </div>
              )}
            </div>
            <div>
              <Label htmlFor="login-password">Password</Label>
              <Input 
                id="login-password" 
                name="password"
                type="password" 
                aria-describedby={errors.password ? 'password-error' : undefined}
                aria-invalid={!!errors.password}
              />
              {errors.password && (
                <div id="password-error" role="alert" aria-live="polite">
                  {errors.password}
                </div>
              )}
            </div>
          </fieldset>
          <Button type="submit">Sign In</Button>
        </form>
      );
    };
    
    const user = setupKeyboardTest();
    const { container } = render(<FormWithValidation />);
    
    // Submit form to trigger validation
    await user.click(screen.getByRole('button', { name: 'Sign In' }));
    
    await waitFor(() => {
      expect(screen.getByText('Username is required')).toBeInTheDocument();
      expect(screen.getByText('Password is required')).toBeInTheDocument();
    });
    
    // Verify error associations
    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    
    expect(usernameInput).toHaveAttribute('aria-invalid', 'true');
    expect(passwordInput).toHaveAttribute('aria-invalid', 'true');
    expect(usernameInput).toHaveAttribute('aria-describedby', 'username-error');
    expect(passwordInput).toHaveAttribute('aria-describedby', 'password-error');
    
    await runAxeTest(container);
  });

  it('supports required field indicators', async () => {
    const { container } = render(
      <form>
        <fieldset>
          <legend>Account Registration</legend>
          <div>
            <Label htmlFor="reg-email">
              Email Address <span aria-label="required">*</span>
            </Label>
            <Input id="reg-email" type="email" required aria-required="true" />
          </div>
          <div>
            <Label htmlFor="reg-username">
              Username <span aria-label="required">*</span>
            </Label>
            <Input id="reg-username" type="text" required aria-required="true" />
          </div>
          <div>
            <Label htmlFor="reg-phone">Phone Number (optional)</Label>
            <Input id="reg-phone" type="tel" />
          </div>
        </fieldset>
        <Button type="submit">Create Account</Button>
      </form>
    );
    
    await runAxeTest(container);
    
    // Verify required indicators
    const emailInput = screen.getByLabelText(/Email Address/);
    const usernameInput = screen.getByLabelText(/Username/);
    const phoneInput = screen.getByLabelText('Phone Number (optional)');
    
    expect(emailInput).toHaveAttribute('required');
    expect(emailInput).toHaveAttribute('aria-required', 'true');
    expect(usernameInput).toHaveAttribute('required');
    expect(usernameInput).toHaveAttribute('aria-required', 'true');
    expect(phoneInput).not.toHaveAttribute('required');
  });
});