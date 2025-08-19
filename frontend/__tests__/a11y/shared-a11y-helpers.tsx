/**
 * Shared Accessibility Test Helpers
 * Reusable utilities for accessibility testing across all components
 * Follows 8-line function rule and 300-line file limit
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free → Enterprise)
 * - Goal: Standardized accessibility testing patterns
 * - Value Impact: Consistent test quality and faster test development
 * - Revenue Impact: Reduced development costs and better compliance
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// ============================================================================
// ACCESSIBILITY TEST UTILITIES
// ============================================================================

/**
 * Runs axe accessibility tests on a rendered component
 * @param container - The container element to test
 * @returns Promise that resolves when tests complete
 */
export const runAxeTest = async (container: HTMLElement): Promise<void> => {
  const results = await axe(container);
  expect(results).toHaveNoViolations();
};

/**
 * Sets up user event for keyboard testing
 * @returns Configured userEvent instance
 */
export const setupKeyboardTest = () => {
  return userEvent.setup();
};

/**
 * Tests tab navigation between elements
 * @param elements - Array of element names or roles to test
 * @param user - UserEvent instance
 */
export const testTabNavigation = async (
  elements: string[],
  user: ReturnType<typeof userEvent.setup>
): Promise<void> => {
  for (const elementName of elements) {
    await user.tab();
    const element = screen.getByRole('button', { name: elementName });
    expect(element).toHaveFocus();
  }
};

/**
 * Tests keyboard activation (Enter and Space)
 * @param buttonName - Name of button to test
 * @param mockFn - Jest mock function to verify calls
 * @param user - UserEvent instance
 */
export const testKeyboardActivation = async (
  buttonName: string,
  mockFn: jest.Mock,
  user: ReturnType<typeof userEvent.setup>
): Promise<void> => {
  const button = screen.getByRole('button', { name: buttonName });
  await user.tab();
  await user.keyboard('{Enter}');
  await user.keyboard(' ');
  expect(mockFn).toHaveBeenCalledTimes(2);
};

/**
 * Tests focus trap in modal dialogs
 * @param modalTrigger - Text of button that opens modal
 * @param user - UserEvent instance
 */
export const testFocusTrap = async (
  modalTrigger: string,
  user: ReturnType<typeof userEvent.setup>
): Promise<void> => {
  await user.click(screen.getByRole('button', { name: modalTrigger }));
  const dialog = screen.getByRole('dialog');
  expect(dialog).toBeInTheDocument();
};

/**
 * Creates a live region test component
 * @param message - Message to announce
 * @param level - Politeness level ('polite' | 'assertive')
 * @returns React component for testing
 */
export const createLiveRegionTest = (
  message: string,
  level: 'polite' | 'assertive' = 'polite'
) => {
  const LiveRegionTest = () => {
    const [announcement, setAnnouncement] = React.useState('');
    
    return (
      <div>
        <button onClick={() => setAnnouncement(message)}>
          Trigger Announcement
        </button>
        <div aria-live={level} data-testid="live-region">
          {announcement}
        </div>
      </div>
    );
  };
  return LiveRegionTest;
};

/**
 * Tests ARIA label association
 * @param labelText - Text of the label
 * @param expectedElement - Expected element type or role
 */
export const testAriaLabel = (labelText: string, expectedElement?: string): void => {
  const element = screen.getByLabelText(labelText);
  expect(element).toBeInTheDocument();
  if (expectedElement) {
    expect(element).toHaveAttribute('type', expectedElement);
  }
};

/**
 * Tests form validation error announcement
 * @param inputLabel - Label text of input to test
 * @param errorMessage - Expected error message
 * @param user - UserEvent instance
 */
export const testValidationError = async (
  inputLabel: string,
  errorMessage: string,
  user: ReturnType<typeof userEvent.setup>
): Promise<void> => {
  const input = screen.getByLabelText(inputLabel);
  await user.type(input, 'invalid');
  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent(errorMessage);
  });
};

/**
 * Tests focus restoration after modal close
 * @param triggerText - Text of button that opens modal
 * @param closeText - Text of button that closes modal
 * @param user - UserEvent instance
 */
export const testFocusRestoration = async (
  triggerText: string,
  closeText: string,
  user: ReturnType<typeof userEvent.setup>
): Promise<void> => {
  const trigger = screen.getByRole('button', { name: triggerText });
  await user.click(trigger);
  await user.click(screen.getByRole('button', { name: closeText }));
  
  await waitFor(() => {
    expect(trigger).toHaveFocus();
  });
};

/**
 * Creates a fieldset test component with legend
 * @param legend - Legend text for fieldset
 * @param fields - Array of field configurations
 * @returns React component for testing
 */
export const createFieldsetTest = (
  legend: string,
  fields: Array<{ id: string; label: string; type?: string }>
) => {
  const FieldsetTest = () => (
    <fieldset>
      <legend>{legend}</legend>
      {fields.map(field => (
        <div key={field.id}>
          <label htmlFor={field.id}>{field.label}</label>
          <input 
            id={field.id} 
            type={field.type || 'text'} 
          />
        </div>
      ))}
    </fieldset>
  );
  return FieldsetTest;
};

/**
 * Tests skip link functionality
 * @param skipText - Text of skip link
 * @param targetId - ID of target element
 * @param user - UserEvent instance
 */
export const testSkipLink = async (
  skipText: string,
  targetId: string,
  user: ReturnType<typeof userEvent.setup>
): Promise<void> => {
  const skipLink = screen.getByRole('link', { name: skipText });
  await user.tab();
  expect(skipLink).toHaveFocus();
  expect(skipLink).toHaveAttribute('href', `#${targetId}`);
};

/**
 * Tests landmark navigation structure
 * @param landmarks - Array of landmark configurations
 */
export const testLandmarks = (
  landmarks: Array<{ role: string; name?: string }>
): void => {
  landmarks.forEach(landmark => {
    if (landmark.name) {
      const element = screen.getByRole(landmark.role as any, { name: landmark.name });
      expect(element).toBeInTheDocument();
    } else {
      const element = screen.getByRole(landmark.role as any);
      expect(element).toBeInTheDocument();
    }
  });
};

/**
 * Tests heading hierarchy
 * @param expectedLevels - Array of heading levels to verify
 */
export const testHeadingHierarchy = (expectedLevels: number[]): void => {
  expectedLevels.forEach(level => {
    const heading = screen.getByRole('heading', { level });
    expect(heading).toBeInTheDocument();
  });
};

/**
 * Tests color contrast by checking CSS classes
 * @param element - Element to test
 * @param expectedClasses - Array of expected CSS classes
 */
export const testColorContrast = (
  element: HTMLElement,
  expectedClasses: string[]
): void => {
  expectedClasses.forEach(className => {
    expect(element).toHaveClass(className);
  });
};

// ============================================================================
// MOCK HELPERS FOR TESTING
// ============================================================================

/**
 * Creates mock for reduced motion preference
 * @param prefersReducedMotion - Whether reduced motion is preferred
 */
export const mockReducedMotion = (prefersReducedMotion: boolean = true): void => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
      matches: prefersReducedMotion && query.includes('prefers-reduced-motion'),
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
    })),
  });
};

/**
 * Creates a keyboard event mock
 * @param key - Key to simulate
 * @param options - Additional event options
 */
export const createKeyboardEvent = (
  key: string,
  options: { ctrlKey?: boolean; metaKey?: boolean; shiftKey?: boolean } = {}
): KeyboardEvent => {
  return new KeyboardEvent('keydown', {
    key,
    ...options,
    bubbles: true,
    cancelable: true,
  });
};

// ============================================================================
// COMPONENT TEST BUILDERS
// ============================================================================

/**
 * Builds a form validation test component
 * @param fields - Array of field configurations
 * @returns React component for form testing
 */
export const buildFormValidationTest = (
  fields: Array<{ 
    name: string; 
    label: string; 
    type?: string; 
    required?: boolean; 
    validation?: (value: string) => string | null;
  }>
) => {
  const FormValidationTest = () => {
    const [values, setValues] = React.useState<Record<string, string>>({});
    const [errors, setErrors] = React.useState<Record<string, string>>({});
    
    const handleChange = (name: string, value: string) => {
      setValues(prev => ({ ...prev, [name]: value }));
      
      const field = fields.find(f => f.name === name);
      if (field?.validation) {
        const error = field.validation(value);
        setErrors(prev => ({ ...prev, [name]: error || '' }));
      }
    };
    
    return (
      <form>
        {fields.map(field => (
          <div key={field.name}>
            <label htmlFor={field.name}>{field.label}</label>
            <input
              id={field.name}
              name={field.name}
              type={field.type || 'text'}
              required={field.required}
              value={values[field.name] || ''}
              onChange={(e) => handleChange(field.name, e.target.value)}
              aria-invalid={!!errors[field.name]}
              aria-describedby={errors[field.name] ? `${field.name}-error` : undefined}
            />
            {errors[field.name] && (
              <div id={`${field.name}-error`} role="alert">
                {errors[field.name]}
              </div>
            )}
          </div>
        ))}
      </form>
    );
  };
  return FormValidationTest;
};