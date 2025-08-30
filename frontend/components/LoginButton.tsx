import { Button } from '@/components/ui/button';
import { authService } from '@/auth';
import Image from 'next/image';

export default function LoginButton() {
  const { user, login, logout } = authService.useAuth();

  if (user) {
    return (
      <div className="flex items-center gap-4" data-testid="auth-component">
        {user.picture && (
          <Image
            src={user.picture}
            alt={user.full_name || 'User avatar'}
            width={32}
            height={32}
            className="rounded-full"
          />
        )}
        <span data-testid="user-email">{user.full_name}</span>
        <Button onClick={logout} data-testid="logout-button">Logout</Button>
      </div>
    );
  }

  return <Button onClick={login} size="lg" data-testid="login-button">Login with Google</Button>;
}