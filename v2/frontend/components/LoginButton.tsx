
'use client';

import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';

export default function LoginButton() {
  const { user, login, logout } = useAuth();

  if (user) {
    return (
      <div className="flex items-center gap-4">
        <img src={user.picture} alt={user.full_name} className="w-8 h-8 rounded-full" />
        <span>{user.full_name}</span>
        <Button onClick={logout}>Logout</Button>
      </div>
    );
  }

  return <Button onClick={login}>Login with Google</Button>;
}
