/**
 * Privacy Section Component
 * Data export, account deletion, and privacy settings
 */

'use client';

import React, { useState } from 'react';

interface ExportStatus {
  export_id: string;
  status: 'processing' | 'completed' | 'failed';
  download_url?: string;
  expires_at?: string;
  message: string;
}

export default function PrivacySection() {
  const [exportStatus, setExportStatus] = useState<ExportStatus | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [message, setMessage] = useState('');

  const handleExportData = async () => {
    // Mock export request
    const newExport: ExportStatus = {
      export_id: 'export-123',
      status: 'processing',
      message: 'Your data export has been initiated. You will receive an email when it is ready.'
    };

    setExportStatus(newExport);
    setMessage(newExport.message);
    setTimeout(() => setMessage(''), 5000);

    // Mock completion after 3 seconds
    setTimeout(() => {
      setExportStatus({
        export_id: 'export-123',
        status: 'completed',
        download_url: '/api/users/export-data/export-123/download',
        expires_at: new Date(Date.now() + 86400000).toISOString(), // 24 hours from now
        message: 'Your data export is ready for download'
      });
    }, 3000);
  };

  const handleCheckExportStatus = () => {
    if (exportStatus?.status === 'completed') {
      setMessage('Your data export is ready for download');
    } else if (exportStatus?.status === 'processing') {
      setMessage('Your export is still processing. Please check again later.');
    } else {
      setMessage('No active exports found');
    }
    setTimeout(() => setMessage(''), 3000);
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmation !== 'DELETE') {
      setMessage('Please type DELETE to confirm account deletion');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    // Mock account deletion
    setMessage('Account scheduled for deletion. You will be logged out shortly.');
    setShowDeleteModal(false);
    
    // Mock logout after 2 seconds
    setTimeout(() => {
      window.location.href = '/login';
    }, 2000);
  };

  return (
    <div className="privacy-section">
      <h3 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '24px' }}>
        Privacy & Data
      </h3>

      {message && (
        <div 
          style={{ 
            padding: '12px', 
            marginBottom: '20px', 
            borderRadius: '8px',
            backgroundColor: message.includes('ready') || message.includes('initiated') ? '#d4edda' : '#f8d7da',
            color: message.includes('ready') || message.includes('initiated') ? '#155724' : '#721c24',
            border: `1px solid ${message.includes('ready') || message.includes('initiated') ? '#c3e6cb' : '#f5c6cb'}`
          }}
        >
          {message}
        </div>
      )}

      <div style={{ display: 'grid', gap: '32px' }}>
        {/* Data Export */}
        <div>
          <h4 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '16px' }}>
            Data Export
          </h4>
          <p style={{ color: '#6b7280', marginBottom: '20px' }}>
            Download a copy of all your data including profile information, conversations, 
            API keys (encrypted), and usage statistics.
          </p>

          <div style={{ marginBottom: '20px' }}>
            <button
              onClick={handleExportData}
              disabled={exportStatus?.status === 'processing'}
              style={{
                padding: '12px 24px',
                backgroundColor: exportStatus?.status === 'processing' ? '#6b7280' : '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: exportStatus?.status === 'processing' ? 'not-allowed' : 'pointer',
                fontWeight: '500',
                marginRight: '12px'
              }}
            >
              {exportStatus?.status === 'processing' ? 'Processing...' : 'Export My Data'}
            </button>

            {exportStatus && (
              <button
                onClick={handleCheckExportStatus}
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
                Check Export Status
              </button>
            )}
          </div>

          {exportStatus?.status === 'completed' && exportStatus.download_url && (
            <div style={{
              padding: '16px',
              backgroundColor: '#d4edda',
              border: '1px solid #c3e6cb',
              borderRadius: '8px',
              marginBottom: '20px'
            }}>
              <h5 style={{ color: '#155724', marginBottom: '8px', fontWeight: '600' }}>
                Export Ready
              </h5>
              <p style={{ color: '#155724', marginBottom: '12px' }}>
                Your data export is ready for download. The download link will expire in 24 hours.
              </p>
              <a
                href={exportStatus.download_url}
                style={{
                  display: 'inline-block',
                  padding: '8px 16px',
                  backgroundColor: '#155724',
                  color: 'white',
                  textDecoration: 'none',
                  borderRadius: '4px',
                  fontWeight: '500'
                }}
              >
                Download Export
              </a>
            </div>
          )}

          {exportStatus?.status === 'processing' && (
            <div style={{
              padding: '16px',
              backgroundColor: '#fff3cd',
              border: '1px solid #ffeaa7',
              borderRadius: '8px',
              color: '#856404'
            }}>
              <p>Your export is being processed. This may take a few minutes. We&apos;ll email you when it&apos;s ready.</p>
            </div>
          )}
        </div>

        {/* Data Retention */}
        <div>
          <h4 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '16px' }}>
            Data Retention
          </h4>
          <div style={{ color: '#6b7280' }}>
            <p style={{ marginBottom: '12px' }}>
              <strong>Conversations:</strong> Stored for 90 days after last activity, then archived
            </p>
            <p style={{ marginBottom: '12px' }}>
              <strong>Usage Analytics:</strong> Aggregated data kept for 2 years for billing and optimization
            </p>
            <p style={{ marginBottom: '12px' }}>
              <strong>Profile Data:</strong> Retained while your account is active
            </p>
            <p>
              <strong>API Keys:</strong> Encrypted and deleted when removed from your account
            </p>
          </div>
        </div>

        {/* Account Deletion */}
        <div style={{
          padding: '20px',
          border: '2px solid #fecaca',
          borderRadius: '8px',
          backgroundColor: '#fef2f2'
        }}>
          <h4 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '16px', color: '#dc2626' }}>
            Danger Zone
          </h4>
          <p style={{ color: '#6b7280', marginBottom: '20px' }}>
            Permanently delete your account and all associated data. This action cannot be undone.
          </p>

          <div style={{ marginBottom: '16px' }}>
            <h5 style={{ fontWeight: '500', marginBottom: '8px' }}>What gets deleted:</h5>
            <ul style={{ paddingLeft: '20px', color: '#6b7280' }}>
              <li>Your profile and account information</li>
              <li>All conversations and chat history</li>
              <li>API keys and integrations</li>
              <li>Usage statistics and billing history</li>
              <li>All settings and preferences</li>
            </ul>
          </div>

          <button
            onClick={() => setShowDeleteModal(true)}
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
            Delete My Account
          </button>
        </div>
      </div>

      {/* Delete Account Modal */}
      {showDeleteModal && (
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
            padding: '32px',
            borderRadius: '12px',
            maxWidth: '500px',
            width: '90%'
          }}>
            <h4 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '16px', color: '#dc2626' }}>
              Delete Account
            </h4>
            
            <div style={{ marginBottom: '24px' }}>
              <p style={{ marginBottom: '12px', color: '#374151' }}>
                <strong>This action cannot be undone.</strong>
              </p>
              <p style={{ marginBottom: '12px', color: '#6b7280' }}>
                All your data will be permanently deleted, including:
              </p>
              <ul style={{ paddingLeft: '20px', color: '#6b7280', marginBottom: '16px' }}>
                <li>Your profile, API keys, and all associated data</li>
                <li>All conversations and optimization history</li>
                <li>Usage statistics and preferences</li>
              </ul>
              <p style={{ color: '#dc2626', fontWeight: '500' }}>
                This includes your profile, API keys, and all associated data.
              </p>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                Type <code style={{ backgroundColor: '#f3f4f6', padding: '2px 4px', borderRadius: '4px' }}>DELETE</code> to confirm:
              </label>
              <input
                type="text"
                placeholder="Type DELETE to confirm"
                value={deleteConfirmation}
                onChange={(e) => setDeleteConfirmation(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '2px solid #fecaca',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteConfirmation('');
                }}
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
              <button
                onClick={handleDeleteAccount}
                disabled={deleteConfirmation !== 'DELETE'}
                style={{
                  padding: '12px 24px',
                  backgroundColor: deleteConfirmation === 'DELETE' ? '#dc2626' : '#9ca3af',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: deleteConfirmation === 'DELETE' ? 'pointer' : 'not-allowed',
                  fontWeight: '500'
                }}
              >
                Delete Account
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}