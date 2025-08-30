/**
 * User Profile Form Component
 * Form for editing user profile information with validation
 */

import React from 'react';

export interface UserProfile {
  name: string;
  email: string;
  bio?: string;
}

interface UserProfileFormProps {
  initialData?: UserProfile;
  onSubmit?: (data: UserProfile) => void;
  isLoading?: boolean;
}

export const UserProfileForm: React.FC<UserProfileFormProps> = ({
  initialData = { name: '', email: '', bio: '' },
  onSubmit,
  isLoading = false
}) => {
  const [formData, setFormData] = React.useState<UserProfile>(initialData);
  const [errors, setErrors] = React.useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    // Name validation - check empty first, then length
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    } else if (formData.name.length < 2) {
      newErrors.name = 'Name must be at least 2 characters';
    }

    // Email validation
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email format';
    }

    // Bio validation
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

export default UserProfileForm;