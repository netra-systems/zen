
'use client';

import { Button } from '@/components/ui/button';
import { useUser }from '../providers/UserProvider';

export default function LoginButton() {
  const { user, isLoading } = useUser();

  const handleLogin = () => {
    window.location.href = 'http://localhost:8000/api/v3/auth/login';
  };

  const handleLogout = () => {
    window.location.href = 'http://localhost:8000/api/v3/auth/logout';
  };

  if (isLoading) {
    return <Button variant="outline">Loading...</Button>;
  }

  if (user) {
    return (
      <div className="flex items-center gap-4">
        <img src={user.picture} alt={user.name} className="w-8 h-8 rounded-full" />
        <span>{user.name}</span>
        <Button onClick={handleLogout}>Logout</Button>
      </div>
    );
  }

  return <Button onClick={handleLogin}>Login with Google</Button>;
}
