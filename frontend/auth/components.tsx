'use client';

import { Button } from '@/components/ui/button';
import { authService } from '@/auth';
import { Badge } from '@/components/ui/badge';
import { useState } from 'react';
import { logger } from '@/lib/logger';

export function LoginButton() {
  const { user, login, logout, loading, authConfig } = authService.useAuth();
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    try {
      setError(null);
      // Wrap login in a try-catch if it might be async
      const result = login();
      if (result && typeof result.catch === 'function') {
        await result;
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setError(errorMessage);
      logger.error('Login button error', err as Error, {
        component: 'LoginButton',
        action: 'login_error'
      });
    }
  };

  const handleLogout = async () => {
    try {
      setError(null);
      await logout();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Logout failed';
      setError(errorMessage);
      logger.error('Logout button error', err as Error, {
        component: 'LoginButton',
        action: 'logout_error'
      });
    }
  };

  if (loading) {
    return <Button disabled>Loading...</Button>;
  }

  if (user) {
    return (
      <div className="flex items-center gap-4">
        {authConfig?.development_mode && (
          <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
            DEV MODE
          </Badge>
        )}
        <span className="text-sm font-medium">{user.full_name || user.email}</span>
        {authConfig?.development_mode ? (
          <div className="flex gap-2">
            <Button onClick={handleLogout} variant="outline" size="sm">Logout</Button>
            <Button onClick={handleLogin} variant="default" size="sm">OAuth Login</Button>
          </div>
        ) : (
          <Button onClick={handleLogout}>Logout</Button>
        )}
        {error && (
          <div className="text-red-500 text-sm" role="alert" aria-live="polite">
            {error}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <Button onClick={handleLogin} size="lg">Access Beta</Button>
      {error && (
        <div className="text-red-500 text-sm" role="alert" aria-live="polite">
          {error}
        </div>
      )}
    </div>
  );
}
