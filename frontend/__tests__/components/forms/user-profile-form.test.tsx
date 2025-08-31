/**
 * User Profile Form Tests
 * Tests for user profile form validation and submission
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { UserProfileForm, UserProfile } from '../../../components/forms/UserProfileForm';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

describe('User Profile Form Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  it('should display validation errors for empty required fields', async () => {
    const mockSubmit = jest.fn();
    const user = userEvent.setup();

    render(<UserProfileForm onSubmit={mockSubmit} />);

    const submitButton = screen.getByTestId('submit-button');
    
    // Try to submit empty form
    await user.click(submitButton);

    // Should show validation errors
    await waitFor(() => {
      expect(screen.getByTestId('name-error')).toHaveTextContent('Name is required');
      expect(screen.getByTestId('email-error')).toHaveTextContent('Email is required');
    });

    // Should not call submit function
    expect(mockSubmit).not.toHaveBeenCalled();
  });

  it('should show all form fields', () => {
    render(<UserProfileForm />);

    // Should show all form fields
    expect(screen.getByTestId('name-input')).toBeInTheDocument();
    expect(screen.getByTestId('email-input')).toBeInTheDocument();
    expect(screen.getByTestId('bio-input')).toBeInTheDocument();
    expect(screen.getByTestId('submit-button')).toBeInTheDocument();
    expect(screen.getByTestId('bio-counter')).toBeInTheDocument();
  });

  it('should enforce minimum name length', async () => {
    render(<UserProfileForm />);

    const nameInput = screen.getByTestId('name-input');
    const submitButton = screen.getByTestId('submit-button');

    // Enter single character name using fireEvent
    fireEvent.change(nameInput, { target: { value: 'A' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByTestId('name-error')).toHaveTextContent('Name must be at least 2 characters');
    });
  });

  it('should enforce bio character limit', async () => {
    render(<UserProfileForm />);

    const bioInput = screen.getByTestId('bio-input') as HTMLTextAreaElement;
    const submitButton = screen.getByTestId('submit-button');

    // Enter bio that exceeds limit (501 characters) - use fireEvent for direct manipulation
    const longBio = 'A'.repeat(501);
    fireEvent.change(bioInput, { target: { value: longBio } });

    // Check character counter updates immediately
    expect(screen.getByTestId('bio-counter')).toHaveTextContent('501/500');

    // Submit form to trigger validation
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByTestId('bio-error')).toHaveTextContent('Bio must be 500 characters or less');
    });
  });

  it('should submit valid form data', async () => {
    const mockSubmit = jest.fn();

    render(<UserProfileForm onSubmit={mockSubmit} />);

    // Fill out form with valid data using fireEvent
    fireEvent.change(screen.getByTestId('name-input'), { target: { value: 'John Doe' } });
    fireEvent.change(screen.getByTestId('email-input'), { target: { value: 'john@example.com' } });
    fireEvent.change(screen.getByTestId('bio-input'), { target: { value: 'Software developer' } });

    fireEvent.click(screen.getByTestId('submit-button'));

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith({
        name: 'John Doe',
        email: 'john@example.com',
        bio: 'Software developer'
      });
    });

    // Should not show any errors
    expect(screen.queryByTestId('name-error')).not.toBeInTheDocument();
    expect(screen.queryByTestId('email-error')).not.toBeInTheDocument();
    expect(screen.queryByTestId('bio-error')).not.toBeInTheDocument();
  });

  it('should clear errors when user starts typing', async () => {
    render(<UserProfileForm />);

    const nameInput = screen.getByTestId('name-input');
    const submitButton = screen.getByTestId('submit-button');

    // Trigger validation error by submitting empty form
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByTestId('name-error')).toBeInTheDocument();
    });

    // Start typing in name field to clear the error
    fireEvent.change(nameInput, { target: { value: 'John' } });

    // Error should be cleared
    await waitFor(() => {
      expect(screen.queryByTestId('name-error')).not.toBeInTheDocument();
    });
  });

  it('should populate form with initial data', () => {
    const initialData = {
      name: 'Jane Smith',
      email: 'jane@example.com',
      bio: 'Designer and developer'
    };

    render(<UserProfileForm initialData={initialData} />);

    // Form should be populated with initial data
    expect(screen.getByTestId('name-input')).toHaveValue('Jane Smith');
    expect(screen.getByTestId('email-input')).toHaveValue('jane@example.com');
    expect(screen.getByTestId('bio-input')).toHaveValue('Designer and developer');

    // Character counter should reflect initial bio length
    expect(screen.getByTestId('bio-counter')).toHaveTextContent('22/500');
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});