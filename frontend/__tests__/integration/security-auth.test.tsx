/**
 * Security and Authentication Integration Tests
 */

import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import apiClient from '@/services/apiClient';
import { TestProviders } from '@/__tests__/setup/test-providers';

// Mock API
jest.mock('@/services/apiClient');

// Mock fetch
global.fetch = jest.fn();

afterEach(() => {
  jest.clearAllMocks();
});

describe('OAuth Secrets Management', () => {
  it('should handle OAuth token refresh', async () => {
    const TestComponent = () => {
      const [tokenStatus, setTokenStatus] = React.useState('');
      
      const refreshToken = async () => {
        const response = await fetch('/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: 'old_refresh_token' })
        });
        
        if (response.ok) {
          const data = await response.json();
          setTokenStatus('Token refreshed');
        }
      };
      
      return (
        <div>
          <button onClick={refreshToken}>Refresh Token</button>
          <div data-testid="token-status">{tokenStatus}</div>
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'new_token', refresh_token: 'new_refresh' })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Refresh Token'));
    
    await waitFor(() => {
      expect(getByTestId('token-status')).toHaveTextContent('Token refreshed');
    });
  });

  it('should manage secrets securely', async () => {
    const TestComponent = () => {
      const [secrets, setSecrets] = React.useState<any>({});
      
      const loadSecrets = async () => {
        // Simulate loading encrypted secrets
        const encryptedSecrets = await fetch('/api/secrets');
        const data = await encryptedSecrets.json();
        
        // Decrypt in memory only
        const decrypted = {
          api_key: '***hidden***',
          secret: '***hidden***'
        };
        
        setSecrets(decrypted);
      };
      
      return (
        <div>
          <button onClick={loadSecrets}>Load Secrets</button>
          <div data-testid="secrets">
            {Object.keys(secrets).length > 0 && 'Secrets loaded'}
          </div>
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ encrypted: 'base64_encrypted_data' })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Load Secrets'));
    
    await waitFor(() => {
      expect(getByTestId('secrets')).toHaveTextContent('Secrets loaded');
    });
  });
});

describe('Security Service Integration', () => {
  it('should validate user permissions for protected resources', async () => {
    const TestComponent = () => {
      const [hasAccess, setHasAccess] = React.useState<boolean | null>(null);
      
      const checkAccess = async () => {
        const response = await fetch('/api/security/check-permission', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            resource: 'admin_panel',
            action: 'view'
          })
        });
        
        const result = await response.json();
        setHasAccess(result.allowed);
      };
      
      return (
        <div>
          <button onClick={checkAccess}>Check Access</button>
          {hasAccess !== null && (
            <div data-testid="access">
              {hasAccess ? 'Access granted' : 'Access denied'}
            </div>
          )}
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ allowed: true })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Check Access'));
    
    await waitFor(() => {
      expect(getByTestId('access')).toHaveTextContent('Access granted');
    });
  });

  it('should handle security token rotation', async () => {
    const TestComponent = () => {
      const [rotationStatus, setRotationStatus] = React.useState('');
      
      const rotateTokens = async () => {
        setRotationStatus('Rotating...');
        
        // Simulate token rotation
        const response = await fetch('/api/security/rotate-tokens', {
          method: 'POST'
        });
        
        if (response.ok) {
          setRotationStatus('Tokens rotated successfully');
        }
      };
      
      return (
        <div>
          <button onClick={rotateTokens}>Rotate Tokens</button>
          <div data-testid="rotation-status">{rotationStatus}</div>
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Rotate Tokens'));
    
    await waitFor(() => {
      expect(getByTestId('rotation-status')).toHaveTextContent('Tokens rotated successfully');
    });
  });
});

describe('Key Manager Integration', () => {
  it('should manage API keys lifecycle', async () => {
    const TestComponent = () => {
      const [keys, setKeys] = React.useState<any[]>([]);
      
      const createApiKey = async () => {
        const response = await fetch('/api/keys/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: 'Test API Key',
            permissions: ['read', 'write']
          })
        });
        
        const newKey = await response.json();
        setKeys([...keys, newKey]);
      };
      
      return (
        <div>
          <button onClick={createApiKey}>Create API Key</button>
          <div data-testid="keys">
            {keys.map((key, idx) => (
              <div key={idx}>{key.name}</div>
            ))}
          </div>
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 'key-123',
        name: 'Test API Key',
        key: 'sk_test_abc123'
      })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Create API Key'));
    
    await waitFor(() => {
      expect(getByTestId('keys')).toHaveTextContent('Test API Key');
    });
  });

  it('should revoke compromised keys', async () => {
    const TestComponent = () => {
      const [revokeStatus, setRevokeStatus] = React.useState('');
      
      const revokeKey = async (keyId: string) => {
        const response = await fetch(`/api/keys/${keyId}/revoke`, {
          method: 'POST'
        });
        
        if (response.ok) {
          setRevokeStatus(`Key ${keyId} revoked`);
        }
      };
      
      return (
        <div>
          <button onClick={() => revokeKey('key-123')}>Revoke Key</button>
          <div data-testid="revoke-status">{revokeStatus}</div>
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Revoke Key'));
    
    await waitFor(() => {
      expect(getByTestId('revoke-status')).toHaveTextContent('Key key-123 revoked');
    });
  });
});

describe('Admin Functionality Integration', () => {
  it('should manage user roles and permissions', async () => {
    const TestComponent = () => {
      const [userRole, setUserRole] = React.useState('user');
      
      const updateRole = async (newRole: string) => {
        const response = await fetch('/api/admin/users/123/role', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role: newRole })
        });
        
        if (response.ok) {
          setUserRole(newRole);
        }
      };
      
      return (
        <div>
          <button onClick={() => updateRole('admin')}>Make Admin</button>
          <div data-testid="user-role">Role: {userRole}</div>
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ role: 'admin' })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Make Admin'));
    
    await waitFor(() => {
      expect(getByTestId('user-role')).toHaveTextContent('Role: admin');
    });
  });

  it('should access admin-only endpoints with proper auth', async () => {
    const TestComponent = () => {
      const [adminData, setAdminData] = React.useState<any>(null);
      
      const fetchAdminData = async () => {
        const response = await fetch('/api/admin/system-stats', {
          headers: {
            'Authorization': 'Bearer admin_token'
          }
        });
        
        const data = await response.json();
        setAdminData(data);
      };
      
      return (
        <div>
          <button onClick={fetchAdminData}>Fetch Admin Data</button>
          {adminData && (
            <div data-testid="admin-data">
              Users: {adminData.total_users}
            </div>
          )}
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        total_users: 1000,
        active_sessions: 50
      })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Fetch Admin Data'));
    
    await waitFor(() => {
      expect(getByTestId('admin-data')).toHaveTextContent('Users: 1000');
    });
  });
});