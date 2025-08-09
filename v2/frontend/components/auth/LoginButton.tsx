
'use client';

import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';

export function LoginButton() {
  const { user, login, logout, loading } = authService.useAuth();

  if (loading) {
    return <Button disabled>Loading...</Button>;
  }

  if (user) {
    return (
      <div className="flex items-center gap-4">
        <span className="text-sm font-medium">{user.full_name || user.email}</span>
        <Button onClick={logout}>Logout</Button>
      </div>
    );
  }

  return <Button onClick={login} size="lg">Login with Google</Button>;
}
