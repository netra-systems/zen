
'use client';

;
import { authService } from '@/auth';
import { Button } from '@/components/ui/button';

export default function LoginPage() {
  const { login, loading } = authService.useAuth();

  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-8">Netra</h1>
        <Button onClick={login} disabled={loading} size="lg">
          {loading ? 'Loading...' : 'Login with Google'}
        </Button>
      </div>
    </div>
  );
}
