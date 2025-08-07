'use client';

import { Button } from '@/components/ui/button';
import { useAuth } from '@/providers/auth';

export default function LoginPage() {
  const { login } = useAuth();

  return (
    <div className="flex items-center justify-center min-h-screen">
      <Button onClick={login}>Login with Google</Button>
    </div>
  );
}
