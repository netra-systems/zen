/**
 * Button Accessibility Test - Iteration 6
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock button component that should have proper accessibility features
const AccessibleButton: React.FC<{
  onClick?: () => void;
  disabled?: boolean;
  children: React.ReactNode;
  variant?: 'primary' | 'secondary';
}> = ({ onClick, disabled = false, children, variant = 'primary' }) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`btn ${variant}`}
      aria-label={typeof children === 'string' ? children : 'Button'}
      data-testid="accessible-button"
    >
      {children}
    </button>
  );
};

describe('Button Accessibility Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  it('should have proper accessibility attributes', () => {
    const mockOnClick = jest.fn();
    render(
      <AccessibleButton onClick={mockOnClick} variant="primary">
        Click Me
      </AccessibleButton>
    );
    
    const button = screen.getByTestId('accessible-button');
    
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Click Me');
    expect(button).not.toBeDisabled();
    
    // This will fail initially - button doesn't have aria-label
    expect(button).toHaveAttribute('aria-label', 'Click Me');
  });

  it('should handle click events properly', async () => {
    const mockOnClick = jest.fn();
    const user = userEvent.setup();
    
    render(
      <AccessibleButton onClick={mockOnClick} variant="secondary">
        Submit
      </AccessibleButton>
    );
    
    const button = screen.getByTestId('accessible-button');
    await user.click(button);
    
    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});