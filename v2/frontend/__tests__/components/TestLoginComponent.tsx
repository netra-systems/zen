import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';

export const TestLoginComponent = () => {
  const { login, loading, user, logout } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (user) {
    return (
      <div>
        <span>{`Welcome, ${user.full_name}`}</span>
        <div data-testid="test-component-user-id">{user.id}</div>
        <Button onClick={logout}>Logout</Button>
      </div>
    );
  }

  return <Button onClick={login}>Login with Google</Button>;
};