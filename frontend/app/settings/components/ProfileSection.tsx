/**
 * Profile Section Component
 * User profile information and editing interface
 */

'use client';

import React, { useState, useEffect } from 'react';

interface UserProfile {
  id?: number;
  email: string;
  full_name: string;
  created_at: string;
  avatar_url?: string;
}

export default function ProfileSection() {
  const [profile, setProfile] = useState<UserProfile>({
    id: 1,
    email: 'test@netrasystems.ai',
    full_name: 'Test User',
    created_at: '2024-01-01T00:00:00Z',
    avatar_url: null
  });
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState(profile);
  const [message, setMessage] = useState('');

  useEffect(() => {
    setFormData(profile);
  }, [profile]);

  const handleSave = async () => {
    try {
      // Mock API call - in real implementation, this would call the API
      setProfile(formData);
      setIsEditing(false);
      setMessage('Profile updated successfully');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('Failed to update profile');
      setTimeout(() => setMessage(''), 3000);
    }
  };

  const handleCancel = () => {
    setFormData(profile);
    setIsEditing(false);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file size (5MB limit)
      if (file.size > 5 * 1024 * 1024) {
        setMessage('File size must be less than 5MB');
        setTimeout(() => setMessage(''), 3000);
        return;
      }

      // Validate file type
      if (!['image/jpeg', 'image/png', 'image/gif'].includes(file.type)) {
        setMessage('Only JPG, PNG, and GIF files are allowed');
        setTimeout(() => setMessage(''), 3000);
        return;
      }

      // Mock upload success
      const newAvatarUrl = 'https://cdn.example.com/avatars/user-123.jpg';
      setProfile(prev => ({ ...prev, avatar_url: newAvatarUrl }));
      setMessage('Profile picture updated');
      setTimeout(() => setMessage(''), 3000);
    }
  };

  return (
    <div className="profile-section">
      <h3 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '24px' }}>
        Profile Information
      </h3>

      {message && (
        <div 
          style={{ 
            padding: '12px', 
            marginBottom: '20px', 
            borderRadius: '8px',
            backgroundColor: message.includes('successfully') || message.includes('updated') ? '#d4edda' : '#f8d7da',
            color: message.includes('successfully') || message.includes('updated') ? '#155724' : '#721c24',
            border: `1px solid ${message.includes('successfully') || message.includes('updated') ? '#c3e6cb' : '#f5c6cb'}`
          }}
        >
          {message}
        </div>
      )}

      <div style={{ marginBottom: '24px' }}>
        <h4 style={{ marginBottom: '12px', fontWeight: '500' }}>Profile Picture</h4>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div 
            style={{
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              backgroundColor: '#f3f4f6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '2rem',
              color: '#6b7280'
            }}
          >
            {profile.avatar_url ? (
              <img 
                src={profile.avatar_url} 
                alt="Profile picture"
                style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }}
              />
            ) : (
              profile.full_name.charAt(0).toUpperCase()
            )}
          </div>
          <div>
            <input
              type="file"
              id="avatar-upload"
              accept="image/jpeg,image/png,image/gif"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
            <label
              htmlFor="avatar-upload"
              style={{
                display: 'inline-block',
                padding: '8px 16px',
                backgroundColor: '#3b82f6',
                color: 'white',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.875rem'
              }}
            >
              Upload
            </label>
            <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '4px' }}>
              Max 5MB. JPG, PNG, GIF only.
            </p>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gap: '20px' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
            Full Name
          </label>
          <input
            name="full_name"
            type="text"
            value={formData.full_name}
            onChange={(e) => setFormData(prev => ({ ...prev, full_name: e.target.value }))}
            disabled={!isEditing}
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              backgroundColor: isEditing ? 'white' : '#f9fafb'
            }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
            Email Address
          </label>
          <input
            name="email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
            disabled={!isEditing}
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              backgroundColor: isEditing ? 'white' : '#f9fafb'
            }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
            Member Since
          </label>
          <input
            type="text"
            value={`Member since ${formatDate(profile.created_at)}`}
            disabled
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              backgroundColor: '#f9fafb',
              color: '#6b7280'
            }}
          />
        </div>
      </div>

      <div style={{ marginTop: '32px', display: 'flex', gap: '12px' }}>
        {!isEditing ? (
          <button
            onClick={() => setIsEditing(true)}
            style={{
              padding: '12px 24px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '500'
            }}
          >
            Edit Profile
          </button>
        ) : (
          <>
            <button
              onClick={handleSave}
              style={{
                padding: '12px 24px',
                backgroundColor: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '500'
              }}
            >
              Save Profile
            </button>
            <button
              onClick={handleCancel}
              style={{
                padding: '12px 24px',
                backgroundColor: '#6b7280',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '500'
              }}
            >
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  );
}