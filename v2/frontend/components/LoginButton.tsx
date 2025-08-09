import { Button } from '@/components/ui/button';
import { authService } from '@/auth';
import Image from 'next/image';

export default function LoginButton() {
  const { user, login, logout } = authService.useAuth();

  if (user) {
    return (
      <div className="flex items-center gap-4">
        {user.picture && (
          <Image
            src={user.picture}
            alt={user.full_name || 'User avatar'}
            width={32}
            height={32}
            className="rounded-full"
          />
        )}
        <span>{user.full_name}</span>
        <Button onClick={logout}>Logout</Button>
      </div>
    );
  }

  return <Button onClick={login} size="lg">Login with Google</Button>;
}