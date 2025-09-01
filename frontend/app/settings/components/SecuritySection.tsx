/**
 * Security Section Component
 * Password changes, 2FA, and security settings
 */

'use client';

import React, { useState } from 'react';

interface PasswordFormData {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

interface TwoFAStatus {
  enabled: boolean;
  backup_codes_generated: boolean;
}

interface TwoFASetup {
  secret: string;
  qr_code: string;
  backup_codes: string[];
}

export default function SecuritySection() {
  const [activeTab, setActiveTab] = useState('password');
  const [passwordForm, setPasswordForm] = useState<PasswordFormData>({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [twoFAStatus, setTwoFAStatus] = useState<TwoFAStatus>({
    enabled: false,
    backup_codes_generated: false
  });
  const [twoFASetup, setTwoFASetup] = useState<TwoFASetup | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [message, setMessage] = useState('');
  const [showDisable2FA, setShowDisable2FA] = useState(false);

  const handlePasswordChange = async () => {
    // Validation
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setMessage('Passwords do not match');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    if (passwordForm.new_password.length < 8) {
      setMessage('Password must be at least 8 characters');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    // Mock password change
    setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
    setMessage('Password changed successfully');
    setTimeout(() => setMessage(''), 3000);
  };

  const handleEnable2FA = async () => {
    // Mock 2FA setup
    const mockSetup = {
      secret: 'JBSWY3DPEHPK3PXP',
      qr_code: 'data:image/png;base64,iVBORw0KGgoAAAANS...',
      backup_codes: [
        'backup-code-1',
        'backup-code-2',
        'backup-code-3',
        'backup-code-4',
        'backup-code-5'
      ]
    };
    setTwoFASetup(mockSetup);
  };

  const handleVerify2FA = async () => {
    if (verificationCode.length !== 6) {
      setMessage('Code must be 6 digits');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    if (!/^\d+$/.test(verificationCode)) {
      setMessage('Code must contain only numbers');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    // Mock verification success
    setTwoFAStatus({ enabled: true, backup_codes_generated: true });
    setTwoFASetup(null);
    setVerificationCode('');
    setMessage('Two-factor authentication enabled successfully');
    setTimeout(() => setMessage(''), 3000);
  };

  const handleDisable2FA = async () => {
    setTwoFAStatus({ enabled: false, backup_codes_generated: false });
    setShowDisable2FA(false);
    setMessage('Two-factor authentication disabled');
    setTimeout(() => setMessage(''), 3000);
  };

  const validatePassword = (password: string) => {
    const errors = [];
    if (password.length < 8) errors.push('Password must be at least 8 characters');
    if (!/[A-Z]/.test(password) || !/[a-z]/.test(password)) {
      errors.push('Password must contain uppercase and lowercase letters');
    }
    if (!/\d/.test(password)) errors.push('Password must contain at least one number');
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      errors.push('Password must contain at least one special character');
    }
    return errors;
  };

  const passwordErrors = passwordForm.new_password ? validatePassword(passwordForm.new_password) : [];

  return (
    <div className="security-section">
      <h3 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '24px' }}>
        Security Settings
      </h3>

      {message && (
        <div 
          style={{ 
            padding: '12px', 
            marginBottom: '20px', 
            borderRadius: '8px',
            backgroundColor: message.includes('successfully') || message.includes('disabled') ? '#d4edda' : '#f8d7da',
            color: message.includes('successfully') || message.includes('disabled') ? '#155724' : '#721c24',
            border: `1px solid ${message.includes('successfully') || message.includes('disabled') ? '#c3e6cb' : '#f5c6cb'}`
          }}
        >
          {message}
        </div>
      )}

      <div style={{ borderBottom: '1px solid #e5e7eb', marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '32px' }}>
          <button
            onClick={() => setActiveTab('password')}
            style={{
              padding: '12px 0',
              border: 'none',
              backgroundColor: 'transparent',
              borderBottom: activeTab === 'password' ? '2px solid #3b82f6' : '2px solid transparent',
              color: activeTab === 'password' ? '#3b82f6' : '#6b7280',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Password
          </button>
          <button
            onClick={() => setActiveTab('2fa')}
            style={{
              padding: '12px 0',
              border: 'none',
              backgroundColor: 'transparent',
              borderBottom: activeTab === '2fa' ? '2px solid #3b82f6' : '2px solid transparent',
              color: activeTab === '2fa' ? '#3b82f6' : '#6b7280',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Two-Factor Authentication
          </button>
          <button
            onClick={() => setActiveTab('sessions')}
            style={{
              padding: '12px 0',
              border: 'none',
              backgroundColor: 'transparent',
              borderBottom: activeTab === 'sessions' ? '2px solid #3b82f6' : '2px solid transparent',
              color: activeTab === 'sessions' ? '#3b82f6' : '#6b7280',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Active Sessions
          </button>
        </div>
      </div>

      {/* Password Tab */}
      {activeTab === 'password' && (
        <div>
          <h4 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '16px' }}>
            Change Password
          </h4>
          
          <div style={{ display: 'grid', gap: '20px', maxWidth: '400px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                Current Password
              </label>
              <input
                name="current_password"
                type="password"
                value={passwordForm.current_password}
                onChange={(e) => setPasswordForm(prev => ({ ...prev, current_password: e.target.value }))}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                New Password
              </label>
              <input
                name="new_password"
                type="password"
                value={passwordForm.new_password}
                onChange={(e) => setPasswordForm(prev => ({ ...prev, new_password: e.target.value }))}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px'
                }}
              />
              {passwordErrors.length > 0 && (
                <div style={{ marginTop: '8px' }}>
                  {passwordErrors.map((error, index) => (
                    <div key={index} style={{ color: '#dc2626', fontSize: '0.875rem' }}>
                      {error}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                Confirm New Password
              </label>
              <input
                name="confirm_password"
                type="password"
                value={passwordForm.confirm_password}
                onChange={(e) => setPasswordForm(prev => ({ ...prev, confirm_password: e.target.value }))}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px'
                }}
              />
            </div>

            <button
              onClick={handlePasswordChange}
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
              Change Password
            </button>
          </div>
        </div>
      )}

      {/* 2FA Tab */}
      {activeTab === '2fa' && (
        <div>
          <h4 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '16px' }}>
            Two-Factor Authentication
          </h4>
          
          <div style={{ marginBottom: '24px', padding: '16px', backgroundColor: '#f9fafb', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: '500' }}>
                Two-Factor Authentication: {twoFAStatus.enabled ? 'Enabled' : 'Disabled'}
              </span>
              <span 
                style={{ 
                  padding: '4px 12px', 
                  borderRadius: '20px', 
                  fontSize: '0.875rem',
                  backgroundColor: twoFAStatus.enabled ? '#d4edda' : '#f8d7da',
                  color: twoFAStatus.enabled ? '#155724' : '#721c24'
                }}
              >
                {twoFAStatus.enabled ? '✓ Enabled' : '✗ Disabled'}
              </span>
            </div>
          </div>

          {!twoFAStatus.enabled && !twoFASetup && (
            <div>
              <div style={{ marginBottom: '20px' }}>
                <h5 style={{ fontWeight: '500', marginBottom: '12px' }}>Requirements for 2FA</h5>
                <ul style={{ paddingLeft: '20px', color: '#6b7280' }}>
                  <li>Authenticator app (Google Authenticator, Authy, etc.)</li>
                  <li>Active email address for backup codes</li>
                  <li>Secure storage for backup codes</li>
                </ul>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input name="acknowledge_requirements" type="checkbox" />
                  <span>I understand the requirements and have an authenticator app ready</span>
                </label>
              </div>

              <button
                onClick={handleEnable2FA}
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
                Enable Two-Factor Authentication
              </button>
            </div>
          )}

          {twoFASetup && (
            <div>
              <h5 style={{ fontWeight: '500', marginBottom: '16px' }}>Setup Two-Factor Authentication</h5>
              
              <div style={{ display: 'grid', gap: '24px' }}>
                <div>
                  <h6 style={{ fontWeight: '500', marginBottom: '12px' }}>1. Scan QR Code</h6>
                  <div style={{ marginBottom: '12px' }}>
                    <img 
                      src={twoFASetup.qr_code} 
                      alt="2FA QR Code"
                      style={{ width: '200px', height: '200px', border: '1px solid #e5e7eb' }}
                    />
                  </div>
                  <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                    Secret key: <code style={{ backgroundColor: '#f3f4f6', padding: '2px 4px', borderRadius: '4px' }}>
                      {twoFASetup.secret}
                    </code>
                  </p>
                </div>

                <div>
                  <h6 style={{ fontWeight: '500', marginBottom: '12px' }}>2. Backup Codes</h6>
                  <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '12px' }}>
                    Save these backup codes in a secure location. You can use them to access your account if you lose your authenticator device.
                  </p>
                  <div style={{ backgroundColor: '#f9fafb', padding: '16px', borderRadius: '8px', fontFamily: 'monospace' }}>
                    {twoFASetup.backup_codes.map((code, index) => (
                      <div key={index} style={{ marginBottom: '4px' }}>{code}</div>
                    ))}
                  </div>
                </div>

                <div>
                  <h6 style={{ fontWeight: '500', marginBottom: '12px' }}>3. Verify Setup</h6>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                    Enter verification code from your authenticator app
                  </label>
                  <input
                    name="verification_code"
                    type="text"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value)}
                    maxLength={6}
                    placeholder="123456"
                    style={{
                      padding: '12px',
                      border: '1px solid #d1d5db',
                      borderRadius: '6px',
                      marginRight: '12px',
                      width: '120px'
                    }}
                  />
                  <button
                    onClick={handleVerify2FA}
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
                    Verify and Enable
                  </button>
                </div>
              </div>
            </div>
          )}

          {twoFAStatus.enabled && (
            <div>
              <p style={{ marginBottom: '20px', color: '#6b7280' }}>
                Two-factor authentication is protecting your account. You will need to enter a code from your authenticator app when signing in.
              </p>
              <button
                onClick={() => setShowDisable2FA(true)}
                style={{
                  padding: '12px 24px',
                  backgroundColor: '#dc2626',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: '500'
                }}
              >
                Disable Two-Factor Authentication
              </button>
            </div>
          )}

          {/* Disable 2FA Modal */}
          {showDisable2FA && (
            <div style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000
            }}>
              <div style={{
                backgroundColor: 'white',
                padding: '24px',
                borderRadius: '12px',
                maxWidth: '500px',
                width: '90%'
              }}>
                <h4 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '16px' }}>
                  Disable Two-Factor Authentication
                </h4>
                <p style={{ marginBottom: '12px' }}>
                  Are you sure you want to disable two-factor authentication?
                </p>
                <p style={{ marginBottom: '20px', color: '#dc2626' }}>
                  This will reduce your account security and invalidate your backup codes.
                </p>
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                  <button
                    onClick={() => setShowDisable2FA(false)}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#6b7280',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer'
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleDisable2FA}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#dc2626',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer'
                    }}
                  >
                    Disable
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Active Sessions Tab */}
      {activeTab === 'sessions' && (
        <div>
          <h4 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '16px' }}>
            Active Sessions
          </h4>
          <p style={{ color: '#6b7280', marginBottom: '20px' }}>
            Manage your active sessions and devices. You can revoke access for any device you don&apos;t recognize.
          </p>
          
          <div>
            <div style={{ padding: '16px', border: '1px solid #e5e7eb', borderRadius: '8px', marginBottom: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: '500' }}>Chrome on Windows</div>
                  <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                    192.168.1.100 • New York, US • Active now
                  </div>
                </div>
                <span style={{ 
                  padding: '4px 8px', 
                  backgroundColor: '#10b981', 
                  color: 'white', 
                  borderRadius: '4px',
                  fontSize: '0.75rem'
                }}>
                  Current Session
                </span>
              </div>
            </div>
            
            <button
              style={{
                padding: '12px 24px',
                backgroundColor: '#dc2626',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '500'
              }}
            >
              Revoke All Other Sessions
            </button>
          </div>
        </div>
      )}
    </div>
  );
}