/**
 * API Keys Section Component
 * API key management interface
 */

'use client';

import React, { useState } from 'react';

interface ApiKey {
  id: string;
  name: string;
  provider: string;
  last_used: string | null;
  created_at: string;
  masked_value: string;
  usage_stats?: {
    requests_this_month: number;
    cost_this_month: number;
    average_response_time: number;
  };
}

interface NewKeyForm {
  key_name: string;
  provider: string;
  api_key: string;
}

export default function ApiKeysSection() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([
    {
      id: 'key-1',
      name: 'Production Key',
      provider: 'openai',
      last_used: '2024-12-01T10:00:00Z',
      created_at: '2024-11-01T00:00:00Z',
      masked_value: 'sk-...abc123',
      usage_stats: {
        requests_this_month: 15000,
        cost_this_month: 45.67,
        average_response_time: 1.2
      }
    },
    {
      id: 'key-2',
      name: 'Development Key',
      provider: 'anthropic',
      last_used: null,
      created_at: '2024-11-15T00:00:00Z',
      masked_value: 'sk-ant-...xyz789'
    }
  ]);

  const [showAddForm, setShowAddForm] = useState(false);
  const [newKeyForm, setNewKeyForm] = useState<NewKeyForm>({
    key_name: '',
    provider: 'openai',
    api_key: ''
  });
  const [message, setMessage] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const providers = [
    { value: 'openai', label: 'OpenAI', keyFormat: 'sk-' },
    { value: 'anthropic', label: 'Anthropic', keyFormat: 'sk-ant-' },
    { value: 'cohere', label: 'Cohere', keyFormat: 'co-' },
    { value: 'huggingface', label: 'Hugging Face', keyFormat: 'hf_' }
  ];

  const getProviderLabel = (provider: string) => {
    return providers.find(p => p.value === provider)?.label || provider;
  };

  const getKeyFormatHint = (provider: string) => {
    return providers.find(p => p.value === provider)?.keyFormat || '';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const validateKeyFormat = (provider: string, key: string) => {
    const format = getKeyFormatHint(provider);
    return key.startsWith(format);
  };

  const handleAddKey = async () => {
    // Validation
    if (!newKeyForm.key_name.trim()) {
      setMessage('Key name is required');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    if (!validateKeyFormat(newKeyForm.provider, newKeyForm.api_key)) {
      setMessage('Invalid API key format');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    // Mock add key
    const newKey: ApiKey = {
      id: `key-${Date.now()}`,
      name: newKeyForm.key_name,
      provider: newKeyForm.provider,
      last_used: null,
      created_at: new Date().toISOString(),
      masked_value: `${newKeyForm.api_key.substring(0, 6)}...${newKeyForm.api_key.slice(-6)}`
    };

    setApiKeys(prev => [...prev, newKey]);
    setNewKeyForm({ key_name: '', provider: 'openai', api_key: '' });
    setShowAddForm(false);
    setMessage('API key added successfully');
    setTimeout(() => setMessage(''), 3000);
  };

  const handleDeleteKey = (keyId: string) => {
    setApiKeys(prev => prev.filter(key => key.id !== keyId));
    setDeleteConfirm(null);
    setMessage('API key deleted successfully');
    setTimeout(() => setMessage(''), 3000);
  };

  const handleTestKey = async (keyId: string) => {
    // Mock key validation
    const isValid = Math.random() > 0.3; // 70% success rate for demo
    
    if (isValid) {
      setMessage('Key is valid. Models: gpt-4, gpt-3.5-turbo. Rate limit: 10000 requests/day');
    } else {
      setMessage('Key validation failed. Invalid API key or insufficient permissions');
    }
    setTimeout(() => setMessage(''), 5000);
  };

  return (
    <div className="api-keys-section">
      <h3 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '24px' }}>
        API Keys
      </h3>

      {message && (
        <div 
          style={{ 
            padding: '12px', 
            marginBottom: '20px', 
            borderRadius: '8px',
            backgroundColor: message.includes('successfully') || message.includes('valid') ? '#d4edda' : '#f8d7da',
            color: message.includes('successfully') || message.includes('valid') ? '#155724' : '#721c24',
            border: `1px solid ${message.includes('successfully') || message.includes('valid') ? '#c3e6cb' : '#f5c6cb'}`
          }}
        >
          {message}
        </div>
      )}

      <div style={{ marginBottom: '24px' }}>
        <button
          onClick={() => setShowAddForm(true)}
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
          Add API Key
        </button>
      </div>

      {/* Add Key Form */}
      {showAddForm && (
        <div style={{
          padding: '24px',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          marginBottom: '24px',
          backgroundColor: '#f9fafb'
        }}>
          <h4 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '16px' }}>
            Add New API Key
          </h4>
          
          <div style={{ display: 'grid', gap: '16px', maxWidth: '500px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                Key Name
              </label>
              <input
                name="key_name"
                type="text"
                value={newKeyForm.key_name}
                onChange={(e) => setNewKeyForm(prev => ({ ...prev, key_name: e.target.value }))}
                placeholder="e.g., Production OpenAI Key"
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
                Provider
              </label>
              <select
                name="provider"
                value={newKeyForm.provider}
                onChange={(e) => setNewKeyForm(prev => ({ ...prev, provider: e.target.value }))}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px'
                }}
              >
                {providers.map(provider => (
                  <option key={provider.value} value={provider.value}>
                    {provider.label}
                  </option>
                ))}
              </select>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '4px' }}>
                Key should start with {getKeyFormatHint(newKeyForm.provider)}
              </p>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                API Key
              </label>
              <input
                name="api_key"
                type="password"
                value={newKeyForm.api_key}
                onChange={(e) => setNewKeyForm(prev => ({ ...prev, api_key: e.target.value }))}
                placeholder="Paste your API key here"
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px'
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={handleAddKey}
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
                Save Key
              </button>
              <button
                onClick={() => {
                  setShowAddForm(false);
                  setNewKeyForm({ key_name: '', provider: 'openai', api_key: '' });
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
            </div>
          </div>
        </div>
      )}

      {/* API Keys List */}
      <div style={{ display: 'grid', gap: '16px' }}>
        {apiKeys.map(key => (
          <div key={key.id} style={{
            padding: '20px',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            backgroundColor: 'white'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
              <div>
                <h5 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '4px' }}>
                  {key.name}
                </h5>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  {getProviderLabel(key.provider)} • {key.masked_value}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => handleTestKey(key.id)}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: '#3b82f6',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.875rem'
                  }}
                >
                  Test Key
                </button>
                <button
                  onClick={() => setDeleteConfirm(key.id)}
                  aria-label="Delete key"
                  style={{
                    padding: '6px 12px',
                    backgroundColor: '#dc2626',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.875rem'
                  }}
                >
                  Delete
                </button>
              </div>
            </div>

            <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
              {key.last_used ? (
                <>Last used: {formatDate(key.last_used)}</>
              ) : (
                'Never used'
              )}
              {' • '}Created: {formatDate(key.created_at)}
            </div>

            {key.usage_stats && (
              <div style={{ 
                marginTop: '12px', 
                padding: '12px', 
                backgroundColor: '#f9fafb', 
                borderRadius: '6px',
                fontSize: '0.875rem'
              }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                  <div>
                    <div style={{ color: '#6b7280' }}>Requests this month</div>
                    <div style={{ fontWeight: '600' }}>{key.usage_stats.requests_this_month.toLocaleString()}</div>
                  </div>
                  <div>
                    <div style={{ color: '#6b7280' }}>Cost this month</div>
                    <div style={{ fontWeight: '600' }}>${key.usage_stats.cost_this_month}</div>
                  </div>
                  <div>
                    <div style={{ color: '#6b7280' }}>Avg response time</div>
                    <div style={{ fontWeight: '600' }}>{key.usage_stats.average_response_time}s</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
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
            maxWidth: '400px',
            width: '90%'
          }}>
            <h4 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '16px' }}>
              Delete API Key
            </h4>
            <p style={{ marginBottom: '20px' }}>
              Are you sure you want to delete this API key? This action cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDeleteConfirm(null)}
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
                onClick={() => handleDeleteKey(deleteConfirm)}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#dc2626',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}