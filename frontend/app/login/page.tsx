
'use client';

import { authService } from '@/auth';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function LoginPage() {
  const { login, loading } = authService.useAuth();

  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-8">
          <h1 className="text-4xl font-bold">Netra</h1>
          <Badge variant="beta" className="text-sm px-3 py-1">BETA</Badge>
        </div>
        <p className="text-muted-foreground mb-6">Welcome to the Netra Beta Program</p>
        <Button onClick={login} disabled={loading} size="lg">
          {loading ? 'Loading...' : 'Access Beta'}
        </Button>
      </div>
    </div>
  );
}
