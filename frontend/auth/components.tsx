'use client';

import { Button } from '@/components/ui/button';
import { authService } from '@/auth';
import { Badge } from '@/components/ui/badge';

export function LoginButton() {
  const { user, login, logout, loading, authConfig } = authService.useAuth();

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
            <Button onClick={logout} variant="outline" size="sm">Logout</Button>
            <Button onClick={login} variant="default" size="sm">OAuth Login</Button>
          </div>
        ) : (
          <Button onClick={logout}>Logout</Button>
        )}
      </div>
    );
  }

  return <Button onClick={login} size="lg">Login with Google</Button>;
}
