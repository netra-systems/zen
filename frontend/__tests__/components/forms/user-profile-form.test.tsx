/**
 * User Profile Form Tests
 * Tests for user profile form validation and submission
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

interface UserProfile {
  name: string;
  email: string;
  bio?: string;
}

// Mock user profile form component
const MockUserProfileForm: React.FC<{
  initialData?: UserProfile;
  onSubmit?: (data: UserProfile) => void;
  isLoading?: boolean;
}> = ({ initialData = { name: '', email: '', bio: '' }, onSubmit, isLoading = false }) => {
  const [formData, setFormData] = React.useState<UserProfile>(initialData);
  const [errors, setErrors] = React.useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    } else if (formData.name.length < 2) {
      newErrors.name = 'Name must be at least 2 characters';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email format';
    }

    if (formData.bio && formData.bio.length > 500) {
      newErrors.bio = 'Bio must be 500 characters or less';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validateForm()) {
      onSubmit?.(formData);
    }
  };

  const handleInputChange = (field: keyof UserProfile, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  return (
    <form onSubmit={handleSubmit} data-testid="user-profile-form">
      <div>
        <label htmlFor="name">Name *</label>
        <input
          id="name"
          data-testid="name-input"
          type="text"
          value={formData.name}
          onChange={(e) => handleInputChange('name', e.target.value)}
          disabled={isLoading}
        />
        {errors.name && (
          <div data-testid="name-error" role="alert">
            {errors.name}
          </div>
        )}
      </div>

      <div>
        <label htmlFor="email">Email *</label>
        <input
          id="email"
          data-testid="email-input"
          type="email"
          value={formData.email}
          onChange={(e) => handleInputChange('email', e.target.value)}
          disabled={isLoading}
        />
        {errors.email && (
          <div data-testid="email-error" role="alert">
            {errors.email}
          </div>
        )}
      </div>

      <div>
        <label htmlFor="bio">Bio</label>
        <textarea
          id="bio"
          data-testid="bio-input"
          value={formData.bio || ''}
          onChange={(e) => handleInputChange('bio', e.target.value)}
          disabled={isLoading}
          placeholder="Tell us about yourself..."
        />
        <div data-testid="bio-counter">
          {formData.bio?.length || 0}/500
        </div>
        {errors.bio && (
          <div data-testid="bio-error" role="alert">
            {errors.bio}
          </div>
        )}
      </div>

      <button 
        type="submit" 
        data-testid="submit-button"
        disabled={isLoading}
      >
        {isLoading ? 'Saving...' : 'Save Profile'}
      </button>
    </form>
  );
};

describe('User Profile Form Tests', () => {
  it('should display validation errors for empty required fields', async () => {
    const mockSubmit = jest.fn();
    const user = userEvent.setup();

    render(<MockUserProfileForm onSubmit={mockSubmit} />);

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
    render(<MockUserProfileForm />);

    // Should show all form fields
    expect(screen.getByTestId('name-input')).toBeInTheDocument();
    expect(screen.getByTestId('email-input')).toBeInTheDocument();
    expect(screen.getByTestId('bio-input')).toBeInTheDocument();
    expect(screen.getByTestId('submit-button')).toBeInTheDocument();
    expect(screen.getByTestId('bio-counter')).toBeInTheDocument();
  });

  it('should enforce minimum name length', async () => {
    const user = userEvent.setup();

    render(<MockUserProfileForm />);

    const nameInput = screen.getByTestId('name-input');
    const submitButton = screen.getByTestId('submit-button');

    // Enter single character name
    await user.type(nameInput, 'A');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByTestId('name-error')).toHaveTextContent('Name must be at least 2 characters');
    });
  });

  it('should enforce bio character limit', async () => {
    const user = userEvent.setup();

    render(<MockUserProfileForm />);

    const bioInput = screen.getByTestId('bio-input');
    const submitButton = screen.getByTestId('submit-button');

    // Enter bio that exceeds limit (501 characters)
    const longBio = 'A'.repeat(501);
    await user.type(bioInput, longBio);

    // Check character counter
    expect(screen.getByTestId('bio-counter')).toHaveTextContent('501/500');

    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByTestId('bio-error')).toHaveTextContent('Bio must be 500 characters or less');
    });
  });

  it('should submit valid form data', async () => {
    const mockSubmit = jest.fn();
    const user = userEvent.setup();

    render(<MockUserProfileForm onSubmit={mockSubmit} />);

    // Fill out form with valid data
    await user.type(screen.getByTestId('name-input'), 'John Doe');
    await user.type(screen.getByTestId('email-input'), 'john@example.com');
    await user.type(screen.getByTestId('bio-input'), 'Software developer');

    await user.click(screen.getByTestId('submit-button'));

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
    const user = userEvent.setup();

    render(<MockUserProfileForm />);

    const nameInput = screen.getByTestId('name-input');
    const submitButton = screen.getByTestId('submit-button');

    // Trigger validation error
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByTestId('name-error')).toBeInTheDocument();
    });

    // Start typing in name field
    await user.type(nameInput, 'John');

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

    render(<MockUserProfileForm initialData={initialData} />);

    // Form should be populated with initial data
    expect(screen.getByTestId('name-input')).toHaveValue('Jane Smith');
    expect(screen.getByTestId('email-input')).toHaveValue('jane@example.com');
    expect(screen.getByTestId('bio-input')).toHaveValue('Designer and developer');

    // Character counter should reflect initial bio length
    expect(screen.getByTestId('bio-counter')).toHaveTextContent('22/500');
  });
});