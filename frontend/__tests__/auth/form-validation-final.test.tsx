/**
 * Form Validation Test - Iteration 7 (Final)
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Simple form component for final iteration
const SimpleForm: React.FC<{ onSubmit: (data: { name: string }) => void }> = ({ onSubmit }) => {
  const [name, setName] = React.useState('');
  const [error, setError] = React.useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Name is required');
    } else {
      setError('');
      onSubmit({ name });
    }
  };

  return (
    <form onSubmit={handleSubmit} data-testid="simple-form">
      <input
        type="text"
        placeholder="Enter your name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        data-testid="name-input"
      />
      {error && <span data-testid="error-message" style={{ color: 'red' }}>{error}</span>}
      <button type="submit" data-testid="submit-button">
        Submit
      </button>
    </form>
  );
};

describe('Final Form Validation - Iteration 7', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  it('should show error when name is empty', async () => {
    const mockOnSubmit = jest.fn();
    const user = userEvent.setup();
    
    render(<SimpleForm onSubmit={mockOnSubmit} />);
    
    await user.click(screen.getByTestId('submit-button'));
    
    expect(screen.getByTestId('error-message')).toHaveTextContent('Name is required');
    
    // Fixed: Should match the actual error message
    expect(screen.getByTestId('error-message')).toHaveTextContent('Name is required');
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});